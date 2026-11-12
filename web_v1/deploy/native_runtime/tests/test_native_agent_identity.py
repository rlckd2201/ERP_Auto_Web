"""Test the operating resolver with isolated SQLite; never create signed identities."""
import argparse
import ast
import hashlib
import runpy
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote


HOST = None
BROWSER_SESSION = None


class NativeAgentIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = runpy.run_path(str(HOST), run_name="native_identity_fixture")
        tree = ast.parse(Path(BROWSER_SESSION).read_text(encoding="utf-8-sig"))
        selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_owned_agent"]
        assert len(selected) == 1
        ns = {"datetime": datetime, "RECENT_HEARTBEAT_SECONDS": 20}
        exec(compile(ast.Module(body=selected, type_ignores=[]), "actual_owned_agent", "exec"), ns)
        cls.select_owned = staticmethod(ns["_owned_agent"])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "fixture.sqlite"
        with closing(sqlite3.connect(self.db)) as con, con:
            con.executescript("""
                CREATE TABLE users (id TEXT PRIMARY KEY, is_initial INTEGER);
                CREATE TABLE agent_profiles (agent_id TEXT PRIMARY KEY, user_id TEXT, client_ip TEXT, last_seen TEXT);
                INSERT INTO users VALUES ('alice', 0), ('bob', 0);
            """)
        self.clock = 1000
        self.user = {"id": "alice", "is_initial": False}
        self.claims = {"sub": "fixture-alice", "portalSessionHash": "a" * 64}
        self.resolver = self.make_resolver()

    def make_resolver(self, selector=None):
        return self.native["NativeIdentityResolver"](
            self.db, selector or self.select_owned, now=lambda: self.clock,
        )

    def agent(self, name, owner="alice", ip="172.17.30.15", age=0):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("INSERT OR REPLACE INTO agent_profiles VALUES (?, ?, ?, ?)",
                        (name, owner, ip, (datetime.now() - timedelta(seconds=age)).isoformat()))

    def resolve(self, **kwargs):
        return self.resolver(self.claims, self.user, **kwargs)

    def test_korean_windows_user_with_internal_space(self):
        self.agent("송명학-전산 송명학")
        self.assertEqual(self.resolve(), {"user_id": "alice", "agent_id": "송명학-전산 송명학",
                                          "client_ip": "172.17.30.15"})

    def test_ascii_windows_user_with_internal_spaces(self):
        self.agent("DESKTOP-Jane Doe")
        self.assertEqual(self.resolve()["agent_id"], "DESKTOP-Jane Doe")

    def test_existing_ascii_agent_identity_unchanged(self):
        self.agent("DESKTOP-55LQ6BN-TEST")
        self.assertEqual(self.resolve()["agent_id"], "DESKTOP-55LQ6BN-TEST")

    def test_control_whitespace_and_overlong_agent_names_rejected(self):
        for name in ["", " leading", "trailing ", "tabs\tname", "lines\nname", "cr\rname",
                     "nul\x00name", "del\x7fname", "a" * 161]:
            with self.subTest(name=repr(name)):
                resolver = self.make_resolver(lambda *args: {"agent_id": name})
                with self.assertRaises(self.native["Rejected"]):
                    resolver(self.claims, self.user)

    def test_token_and_account_identifiers_still_reject_spaces(self):
        self.assertFalse(self.native["text"]("login name"))
        for claims, user in [({**self.claims, "sub": "subject name"}, self.user),
                             (self.claims, {"id": "alice name", "is_initial": False})]:
            with self.assertRaises(self.native["Rejected"]):
                self.resolver(claims, user)

    def test_unowned_and_other_users_agents_never_selected(self):
        self.agent("Unowned PC", owner="")
        self.agent("Bob PC", owner="bob")
        self.assertEqual(self.resolve()["agent_id"], "")

    def test_selector_cannot_return_another_owners_agent(self):
        self.agent("Bob PC", owner="bob")
        resolver = self.make_resolver(lambda *args: {"agent_id": "Bob PC"})
        with self.assertRaises(self.native["Rejected"]):
            resolver(self.claims, self.user)

    def test_multiple_live_agents_remain_ambiguous(self):
        self.agent("First PC")
        self.agent("Second PC", ip="172.17.30.16")
        self.assertEqual(self.resolve()["agent_id"], "")

    def test_stale_profile_does_not_hide_the_new_windows_identity(self):
        self.agent("송명학-송명학", age=600)
        self.agent("송명학-전산 송명학")
        self.assertEqual(self.resolve()["agent_id"], "송명학-전산 송명학")

    def test_offline_agent_is_not_newly_selected(self):
        self.agent("Offline PC", age=600)
        self.assertEqual(self.resolve()["agent_id"], "")

    def test_empty_session_can_bind_later_owned_agent(self):
        self.assertEqual(self.resolve()["agent_id"], "")
        self.agent("Later PC")
        self.assertEqual(self.resolve()["agent_id"], "Later PC")

    def test_existing_session_keeps_exact_agent(self):
        self.agent("Original PC")
        self.assertEqual(self.resolve()["agent_id"], "Original PC")
        self.agent("Another PC", ip="172.17.30.16")
        self.assertEqual(self.resolve()["agent_id"], "Original PC")

    def test_ownership_change_does_not_inherit_other_users_pc(self):
        self.agent("Original PC")
        self.resolve()
        self.agent("Original PC", owner="bob")
        self.assertEqual(self.resolve()["agent_id"], "")

    def test_expired_session_is_not_revived(self):
        self.agent("Original PC")
        self.resolve()
        self.clock += 12 * 60 * 60
        with self.assertRaises(self.native["Rejected"]):
            self.resolve()

    def test_agent_query_and_body_must_match_exact_resolved_identity(self):
        identity = {"user_id": "alice", "agent_id": "송명학-전산 송명학", "client_ip": "172.17.30.15"}
        check = self.native["NativeGuard"].check_agent
        target = "/api/setup/status?agent_id=" + quote(identity["agent_id"])
        check(None, target, identity)
        check(None, "/api/setup/printers", identity, {"agent_id": identity["agent_id"]})
        for value in ["Bob PC", "송명학-전산송명학", "송명학-송명학"]:
            with self.assertRaises(self.native["Rejected"]):
                check(None, "/api/setup/status?agent_id=" + quote(value), identity)
            with self.assertRaises(self.native["Rejected"]):
                check(None, "/api/setup/printers", identity, {"agent_id": value})

    def test_resolving_identity_does_not_write_database(self):
        self.agent("Read Only PC")
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.resolve()
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-host", required=True)
    parser.add_argument("--browser-session", required=True)
    args, remaining = parser.parse_known_args()
    HOST, BROWSER_SESSION = args.native_host, args.browser_session
    unittest.main(argv=[__file__] + remaining)
