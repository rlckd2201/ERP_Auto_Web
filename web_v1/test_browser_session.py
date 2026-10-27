import ast
import asyncio
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import HTTPException, Request

from web_v1.backend import browser_session as sessions


class ClosedConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class BrowserSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "test.sqlite"
        self.patch = patch.object(sessions, "get_conn", self.connect)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE users (id TEXT PRIMARY KEY, pw TEXT, is_initial INTEGER);
                CREATE TABLE agent_profiles (agent_id TEXT PRIMARY KEY, user_id TEXT, client_ip TEXT, last_seen TEXT);
                INSERT INTO users VALUES ('alice', 'test-alice', 0), ('bob', 'test-bob', 0), ('initial', 'test-initial', 1);
            """)
        self.agent("alice-pc", "alice", "172.17.30.13")
        self.agent("bob-pc", "bob", "172.17.30.15")
        names = {"client_ip", "_browser_identity", "_identity_setup", "_request_setup",
                 "_verified_login_result", "api_login", "api_setup_status", "require_setup_ready",
                 "_purchase_execution_setup", "api_setup_printers", "api_setup_install", "api_logout"}
        tree = ast.parse((Path(__file__).parent / "backend/app.py").read_text(encoding="utf-8-sig"))
        selected = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
        for n in selected:
            n.decorator_list = []
        self.ns = dict(Request=Request, Any=object, HTTPException=HTTPException,
                       Query=lambda **kw: kw.get("default"), SESSION_HEADER=sessions.SESSION_HEADER,
                       create_browser_session=sessions.create_browser_session,
                       resolve_browser_session=sessions.resolve_browser_session,
                       revoke_browser_session=sessions.revoke_browser_session,
                       latest_agent_profile=self.profile_at_ip, setup_status=self.setup_status,
                       authenticate_user=self.authenticate, save_printer_mapping=Mock(return_value={}),
                       create_install_job=Mock(return_value={}), resolve_purchase_execution=lambda x: x)
        exec(compile(ast.Module(body=selected, type_ignores=[]), "actual_app_handlers", "exec"), self.ns)

    def connect(self):
        conn = sqlite3.connect(self.db, factory=ClosedConnection)
        conn.row_factory = sqlite3.Row
        return conn

    def agent(self, agent_id, user, ip, seconds_ago=0):
        with self.connect() as conn:
            conn.execute("INSERT OR REPLACE INTO agent_profiles VALUES (?, ?, ?, ?)",
                         (agent_id, user, ip, (datetime.now() - timedelta(seconds=seconds_ago)).isoformat()))

    def profile_at_ip(self, client_ip):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM agent_profiles WHERE client_ip = ?", (client_ip,)).fetchone()
        return dict(row) if row else {}

    def setup_status(self, user_id="", agent_id="", client_ip=""):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM agent_profiles WHERE client_ip = ? AND (? = '' OR agent_id = ?)",
                               (client_ip, agent_id, agent_id)).fetchone()
            if row and user_id:
                conn.execute("UPDATE agent_profiles SET user_id = ? WHERE agent_id = ?", (user_id, row["agent_id"]))
        return {**(dict(row) if row else {}), "user_id": user_id or (row["user_id"] if row else ""),
                "ready": bool(row), "missing_items": []}

    def authenticate(self, user_id, password):
        with self.connect() as conn:
            row = conn.execute("SELECT id, is_initial FROM users WHERE id = ? AND pw = ?", (user_id, password)).fetchone()
        return dict(row) if row else None

    def request(self, token=None, ip="59.1.29.245", payload=None):
        headers = [(b"x-forwarded-for", ip.encode())]
        if token is not None:
            headers.append((sessions.SESSION_HEADER.encode(), token.encode()))
        req = Request({"type": "http", "method": "GET", "path": "/api/setup/status", "headers": headers,
                       "client": ("127.0.0.1", 12345), "query_string": b""})
        async def body():
            return payload or {}
        req.json = body
        return req

    def token(self, user="alice", ip=""):
        return sessions.create_browser_session(user, ip)

    def status(self, token=None, **kw):
        return self.ns["_request_setup"](self.request(token), **kw)

    def test_portal_login_preserves_password_check_and_finds_private_agent(self):
        req = self.request(payload={"user_id": "alice", "password": "test-alice"})
        result = asyncio.run(self.ns["api_login"](req))
        self.assertTrue(result["setup"]["ready"])
        self.assertEqual(result["setup"]["agent_id"], "alice-pc")
        self.assertEqual(result["setup"]["client_ip"], "172.17.30.13")
        self.assertEqual(self.status(result["session_token"])["user_id"], "alice")

    def test_wrong_password_never_creates_session(self):
        with self.assertRaises(HTTPException) as e:
            asyncio.run(self.ns["api_login"](self.request(payload={"user_id": "alice", "password": "wrong"})))
        self.assertEqual(e.exception.status_code, 401)

    def test_initial_password_requires_change_before_session(self):
        result = asyncio.run(self.ns["api_login"](self.request(payload={"user_id": "initial", "password": "test-initial"})))
        self.assertTrue(result["password_change_required"])
        self.assertNotIn("session_token", result)

    def test_user_query_alone_cannot_select_agent_from_nat(self):
        with self.assertRaises(HTTPException) as e:
            self.status(user_id="alice")
        self.assertEqual(e.exception.status_code, 401)

    def test_same_nat_users_resolve_separate_agents(self):
        self.assertEqual(self.status(self.token("alice"))["agent_id"], "alice-pc")
        self.assertEqual(self.status(self.token("bob"))["agent_id"], "bob-pc")

    def test_other_account_or_agent_parameters_are_rejected(self):
        token = self.token()
        for kw in ({"user_id": "bob"}, {"agent_id": "bob-pc"}):
            with self.subTest(kw=kw), self.assertRaises(HTTPException) as e:
                self.status(token, **kw)
            self.assertEqual(e.exception.status_code, 403)

    def test_expired_forged_and_empty_tokens_fail_closed(self):
        token = self.token()
        with self.connect() as conn:
            conn.execute("UPDATE browser_sessions SET expires_at = 0")
        for value in (token, "x" * 43, "", "bad"):
            with self.subTest(value_length=len(value)), self.assertRaises(HTTPException) as e:
                self.status(value)
            self.assertEqual(e.exception.status_code, 401)

    def test_password_reset_revokes_existing_session(self):
        token = self.token()
        with self.connect() as conn:
            conn.execute("UPDATE users SET pw = 'changed' WHERE id = 'alice'")
        with self.assertRaises(HTTPException):
            self.status(token)

    def test_logout_revokes_token(self):
        token = self.token()
        self.ns["api_logout"](self.request(token))
        with self.assertRaises(HTTPException):
            self.status(token)

    def test_raw_session_token_not_persisted(self):
        token = self.token()
        with self.connect() as conn:
            stored = conn.execute("SELECT token_hash, credential_tag FROM browser_sessions").fetchone()
        self.assertNotIn(token, stored)
        self.assertNotIn("test-alice", stored)

    def test_multiple_recent_agents_do_not_choose_most_recent(self):
        self.agent("alice-other", "alice", "172.17.30.77")
        status = self.status(self.token())
        self.assertFalse(status["ready"])
        self.assertFalse(status["agent_id"])
        self.assertIn("identity_message", status)

    def test_stale_other_agent_does_not_make_current_agent_ambiguous(self):
        self.agent("alice-old", "alice", "172.17.30.77", seconds_ago=600)
        self.assertEqual(self.status(self.token())["agent_id"], "alice-pc")

    def test_offline_agent_cannot_be_newly_selected(self):
        self.agent("alice-pc", "alice", "172.17.30.13", seconds_ago=600)
        self.assertFalse(self.status(self.token())["ready"])

    def test_session_can_bind_later_registered_owned_agent(self):
        self.agent("alice-pc", "alice", "172.17.30.13", seconds_ago=600)
        token = self.token()
        self.agent("alice-new", "alice", "172.17.30.88")
        self.assertEqual(self.status(token)["agent_id"], "alice-new")

    def test_session_remains_pinned_when_another_pc_connects(self):
        token = self.token()
        self.agent("alice-new", "alice", "172.17.30.88")
        self.assertEqual(self.status(token)["agent_id"], "alice-pc")

    def test_agent_owner_change_does_not_inherit_other_users_pc(self):
        token = self.token()
        self.agent("alice-pc", "bob", "172.17.30.13")
        self.assertFalse(self.status(token)["ready"])

    def test_same_agent_ip_change_is_followed_without_changing_owner(self):
        token = self.token()
        self.agent("alice-pc", "alice", "172.17.30.89")
        self.assertEqual(self.status(token)["client_ip"], "172.17.30.89")

    def test_direct_login_disambiguates_by_actual_private_ip(self):
        self.agent("alice-new", "alice", "172.17.30.88")
        self.assertEqual(self.status(self.token(ip="172.17.30.13"))["agent_id"], "alice-pc")

    def test_direct_pc_restart_does_not_redirect_to_other_online_pc(self):
        self.agent("alice-pc", "alice", "172.17.30.13", seconds_ago=600)
        self.agent("alice-other", "alice", "172.17.30.88")
        self.assertEqual(self.status(self.token(ip="172.17.30.13"))["agent_id"], "alice-pc")

    def test_direct_legacy_and_agent_transport_ip_are_preserved(self):
        req = self.request(ip="172.17.30.13")
        self.assertEqual(self.ns["_request_setup"](req)["agent_id"], "alice-pc")
        req = self.request(self.token(), ip="172.17.30.243")
        self.assertEqual(self.ns["client_ip"](req), "172.17.30.243")

    def test_portal_printer_save_routes_only_to_session_owner(self):
        req = self.request(self.token(), payload={"mapping": {"gimje": "selected printer"}})
        asyncio.run(self.ns["api_setup_printers"](req))
        self.ns["save_printer_mapping"].assert_called_once_with(
            {"gimje": "selected printer"}, agent_id="alice-pc", client_ip="172.17.30.13")

    def test_other_agent_printer_update_rejected_before_mutation(self):
        req = self.request(self.token(), payload={"agent_id": "bob-pc", "mapping": {}})
        with self.assertRaises(HTTPException):
            asyncio.run(self.ns["api_setup_printers"](req))
        self.ns["save_printer_mapping"].assert_not_called()

    def test_unresolved_session_cannot_dispatch_shared_purchase(self):
        self.agent("alice-pc", "alice", "172.17.30.13", seconds_ago=600)
        with self.assertRaises(HTTPException) as e:
            self.ns["_purchase_execution_setup"](self.request(self.token()))
        self.assertEqual(e.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
