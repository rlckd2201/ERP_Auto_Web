import ast
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from contextlib import closing
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.testclient import TestClient

from web_v1.backend import browser_session, log_viewer
from web_v1.backend.job_store import JobStore
from web_v1.backend.models import JobCreateRequest


class LogViewerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "viewer.db"
        self.store = JobStore()
        self.addCleanup(patch.stopall)
        patch.object(log_viewer, "settings", SimpleNamespace(sqlite_db_path=self.db)).start()
        patch.object(log_viewer, "job_store", self.store).start()
        patch.object(browser_session, "get_conn", self.conn).start()
        with closing(self.conn()) as conn, conn:
            conn.executescript("""
                CREATE TABLE users (id TEXT PRIMARY KEY, pw TEXT, is_initial INTEGER);
                CREATE TABLE agent_profiles (agent_id TEXT, client_ip TEXT, user_id TEXT, last_seen TEXT);
                CREATE TABLE invoices (id INTEGER PRIMARY KEY, subject TEXT, json_data TEXT);
                CREATE TABLE invoice_logs (id INTEGER PRIMARY KEY, invoice_id INTEGER, job_id TEXT, level TEXT, message TEXT, created_at TEXT);
            """)
            self.users = ["rlckd9646", "hah4627", "tuy1120", "arci", "reum0009", "kimsanul"]
            conn.executemany("INSERT INTO users VALUES (?, 'fixture-only', 0)", [(x,) for x in self.users])
            conn.executemany("INSERT INTO invoices VALUES (?, ?, ?)", [
                (277, "구매 문서", json.dumps({"invoice_type": "purchase"})),
                (288, "정기 문서", json.dumps({"invoice_type": "regular"})),
                (289, "오래된 자료", "malformed"),
            ])
            conn.executemany("INSERT INTO invoice_logs VALUES (?, ?, 'job-fixture', ?, ?, '2026-11-10 09:00:00')", [
                (1, 277, "info", "저장 완료"), (2, 277, "error", "인쇄 오류"),
                (3, 288, "info", "정기 처리 완료"), (4, 289, "info", "이전 기록"),
                (5, 999, "info", "삭제된 전표 기록"),
            ])
        self.tokens = {user: browser_session.create_browser_session(user) for user in self.users}
        self.app = FastAPI()
        self.app.include_router(log_viewer.router)
        # Exercise the actual production DB route bodies and decorators without starting workers.
        names = {"_admin_db_conn", "_quote_identifier", "_admin_table_names", "api_admin_db_overview", "api_admin_db_table"}
        tree = ast.parse((Path(__file__).parent / "backend/app.py").read_text(encoding="utf-8-sig"))
        module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
        ns = {"app": self.app, "sqlite3": sqlite3, "Any": object, "Request": Request, "Query": Query,
              "HTTPException": HTTPException, "closing": closing, "readonly_db": log_viewer.readonly_db,
              "require_db_viewer": log_viewer.require_db_viewer, "settings": SimpleNamespace(sqlite_db_path=self.db)}
        exec(compile(module, "production_db_routes", "exec"), ns)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def conn(self):
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, path, user="hah4627", **kwargs):
        return self.client.get(path, headers={"X-Accounting-Session": self.tokens[user]}, **kwargs)

    def test_anonymous_and_invalid_sessions_cannot_read_either_viewer(self):
        for url in ("/api/logs/overview", "/api/logs/table", "/api/admin/db/overview", "/api/admin/db/table?table=users"):
            for headers in ({}, {"X-Accounting-Session": "invalid"}, {"X-Accounting-Session": "x" * 43}):
                self.assertEqual(self.client.get(url, headers=headers).status_code, 401)

    def test_all_six_users_can_read_logs_only_owner_can_read_db(self):
        for user in self.users:
            self.assertEqual(self.get("/api/logs/overview", user).status_code, 200)
            self.assertEqual(self.get("/api/logs/table", user).status_code, 200)
            expected = 200 if user == "rlckd9646" else 403
            self.assertEqual(self.get("/api/admin/db/overview", user).status_code, expected)
            self.assertEqual(self.get("/api/admin/db/table?table=users", user).status_code, expected)

    def test_claimed_admin_name_or_shared_ip_does_not_authorize_db(self):
        for token in (self.tokens["hah4627"], ""):
            response = self.client.get("/api/admin/db/table?table=users&user_id=rlckd9646", headers={
                "X-Accounting-Session": token, "X-Forwarded-For": "172.16.10.15", "X-User-Id": "rlckd9646"})
            self.assertEqual(response.status_code, 403 if token else 401)

    def test_verified_portal_identity_uses_same_permissions_as_browser_sessions(self):
        # Model the trusted native host's ASGI hand-off, not a browser header.
        for user in self.users:
            async def native_host(scope, receive, send, user=user):
                scope = {**scope, "state": {"accounting_identity": {
                    "user_id": user, "agent_id": "fixture-agent", "client_ip": "127.0.0.1"}}}
                await self.app(scope, receive, send)
            with TestClient(native_host) as client, patch.object(log_viewer, "resolve_browser_session", side_effect=AssertionError("Native identity must not be parsed as a session token")):
                self.assertEqual(client.get("/api/logs/overview").status_code, 200)
                self.assertEqual(client.get("/api/logs/table").status_code, 200)
                expected = 200 if user == "rlckd9646" else 403
                self.assertEqual(client.get("/api/admin/db/overview").status_code, expected)
                self.assertEqual(client.get("/api/admin/db/table?table=invoices").status_code, expected)

    def test_native_marker_or_identity_headers_do_not_grant_access(self):
        for url in ("/api/logs/overview", "/api/admin/db/overview"):
            response = self.client.get(url, headers={
                "X-Accounting-Session": "native-portal", "X-Accounting-Identity": "rlckd9646",
                "accounting_identity": '{"user_id":"rlckd9646"}', "X-User-Id": "rlckd9646"})
            self.assertEqual(response.status_code, 401)

    def test_malformed_server_identity_is_rejected(self):
        for identity in ({}, {"user_id": ""}, {"user_id": 123}, "rlckd9646"):
            async def native_host(scope, receive, send, identity=identity):
                await self.app({**scope, "state": {"accounting_identity": identity}}, receive, send)
            with TestClient(native_host) as client:
                self.assertEqual(client.get("/api/logs/overview").status_code, 401)

    def test_expired_and_revoked_sessions_are_denied(self):
        token = self.tokens["rlckd9646"]
        with closing(self.conn()) as conn, conn:
            conn.execute("UPDATE browser_sessions SET expires_at=0 WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
        self.assertEqual(self.get("/api/admin/db/overview", "rlckd9646").status_code, 401)
        browser_session.revoke_browser_session(self.tokens["hah4627"])
        self.assertEqual(self.get("/api/logs/overview").status_code, 401)

    def test_log_projection_cannot_select_users_or_raw_invoice_data(self):
        self.assertEqual(self.get("/api/logs/table?table=users").status_code, 422)
        data = self.get("/api/logs/table").json()
        self.assertEqual(data["total"], 5)
        for row in data["rows"]:
            self.assertEqual(set(row), set(log_viewer._LOG_COLUMNS))
        self.assertNotIn("fixture-only", json.dumps(data))

    def test_source_filters_counts_and_malformed_json(self):
        counts = {x["name"]: x["count"] for x in self.get("/api/logs/overview").json()["tables"]}
        self.assertEqual(counts, {"all": 5, "purchase": 2, "regular": 1, "jobs": 0})
        self.assertEqual(self.get("/api/logs/table?table=purchase").json()["total"], 2)
        self.assertEqual(self.get("/api/logs/table?table=regular").json()["rows"][0]["invoice_id"], 288)

    def test_exact_invoice_search_keyword_and_paging(self):
        self.assertEqual(self.get("/api/logs/table", params={"q": "#277"}).json()["total"], 2)
        self.assertEqual(self.get("/api/logs/table", params={"q": "오류"}).json()["total"], 1)
        page = self.get("/api/logs/table?limit=2&offset=2").json()
        self.assertEqual([row["invoice_id"] for row in page["rows"]], [288, 277])
        self.assertEqual(page["total"], 5)
        self.assertEqual(self.get("/api/logs/table", params={"q": "' OR 1=1 --"}).json()["total"], 0)

    def test_job_logs_exclude_payload_and_support_job_search(self):
        job = self.store.create(JobCreateRequest(job_type="purchase", title="구매 테스트", payload={"secret": "never-return"}))
        self.store.add_event(job.id, "error", 10, "작업 실패")
        data = self.get("/api/logs/table", params={"table": "jobs", "q": job.id}).json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["rows"][0]["message"], "작업 실패")
        self.assertNotIn("never-return", json.dumps(data))

    def test_reads_leave_business_data_unchanged_and_db_is_readonly(self):
        before = self.db.read_bytes()
        self.get("/api/logs/table")
        self.get("/api/admin/db/overview", "rlckd9646")
        self.get("/api/admin/db/table?table=invoices", "rlckd9646")
        self.assertEqual(self.db.read_bytes(), before)
        with closing(log_viewer.readonly_db()) as conn:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("DELETE FROM invoices")

    def test_invalid_query_limits_and_unknown_db_table(self):
        for query in ("limit=501", "offset=-1", "q=" + "x" * 201):
            self.assertEqual(self.get("/api/logs/table?" + query).status_code, 422)
        self.assertEqual(self.get("/api/admin/db/table?table=missing", "rlckd9646").status_code, 404)


if __name__ == "__main__":
    unittest.main()
