"""Isolated browser tests: all traffic is fulfilled with fixtures; no ERP/server calls."""
import json
import mimetypes
import os
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright, expect

FRONTEND = Path(__file__).parent / "frontend"
ORIGIN = "https://accounting.test"
ENTRY = ORIGIN + "/accounting-automation/"


class ViewerTabsBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000}, locale="ko-KR", service_workers="block")
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.page.set_default_timeout(7000)
        self.errors, self.calls = [], []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.failure = None
        self.user = "hah4627"
        self.context.route("**/*", self.route)

    def tearDown(self):
        self.assertEqual(self.errors, [])

    def open(self, user="hah4627", path=ENTRY):
        self.user = user
        if user:
            self.context.add_init_script("localStorage.setItem('accountingWebUser', JSON.stringify(" + json.dumps({"id": user, "name": "테스트 담당자"}) + ")); sessionStorage.setItem('accountingWebSession', 'fixture-session');")
        self.page.goto(path)
        expect(self.page.locator("#appShell" if user else "#loginView")).to_be_visible()

    def route(self, route):
        request = route.request
        parsed = urlparse(request.url)
        if parsed.hostname != "accounting.test":
            route.abort()
            return
        path, params = parsed.path, parse_qs(parsed.query)
        if path.endswith("/admin-db") or path.endswith("/assets/admin_db.html"):
            route.fulfill(path=str(FRONTEND / "admin_db.html"), content_type="text/html")
            return
        if path in ("/", "/accounting-automation/"):
            route.fulfill(path=str(FRONTEND / "index.html"), content_type="text/html")
            return
        if path.startswith("/assets/"):
            file = FRONTEND / path.rsplit("/", 1)[1]
            route.fulfill(path=str(file), content_type=mimetypes.guess_type(str(file))[0] or "text/plain")
            return
        self.calls.append({"path": path, "params": params, "method": request.method, "headers": request.headers})
        if self.failure and path == self.failure[0]:
            status = self.failure[1]
            self.failure = None
            route.fulfill(status=status, content_type="text/html", body="<!doctype html><html>private proxy details</html>")
            return
        status, data = 200, {}
        invoice = {"id": 277, "invoice_type": "purchase", "status": "처리완료", "vendor_name": "컴퓨존", "site_name": "D1공장", "total_sum": 413120, "received_at": "2026-11-10 09:00:00", "processor": "테스트 담당자", "raw": {"invoice_type": "purchase", "items": []}}
        if path == "/api/setup/status":
            data = {"ready": True, "user_id": self.user, "agent_id": "fixture-agent", "checks": [{"key": "agent", "ok": True}], "capabilities": {}, "printer_mapping": {}}
        elif path == "/health":
            data = {"status": "ok", "version": "fixture", "app_name": "회계업무"}
        elif path == "/api/jobs":
            data = []
        elif path == "/api/invoices":
            data = [invoice] if params.get("mode", [""])[0] == "purchase" else []
        elif path == "/api/invoices/277":
            data = invoice
        elif path.endswith("/277/logs"):
            data = []
        elif path == "/api/logs/overview":
            data = {"tables": [{"name": name, "label": label, "count": 123} for name, label in [("all", "전체 처리 로그"), ("purchase", "구매 처리"), ("regular", "정기 처리"), ("jobs", "최근 작업")]]}
        elif path == "/api/logs/table":
            table = params.get("table", ["all"])[0]
            rows = [{"invoice_id": 277, "message": "<img src=x onerror=alert(1)> 인쇄 완료", "level": "info", "invoice_type": "purchase", "created_at": "2026-11-10 09:00:00"} for _ in range(123)]
            offset, limit = int(params.get("offset", [0])[0]), int(params.get("limit", [100])[0])
            data = {"table": table, "columns": ["created_at", "invoice_id", "invoice_type", "level", "message"], "column_labels": {"created_at": "일시", "invoice_id": "전표 번호", "invoice_type": "처리 구분", "level": "상태", "message": "내용"}, "rows": rows[offset:offset + limit], "total": len(rows)}
        elif path.startswith("/api/admin/db/"):
            if self.user != "rlckd9646":
                status, data = 403, {"detail": "DB 보기는 지정된 관리자 계정만 사용할 수 있습니다."}
            elif path.endswith("/overview"):
                data = {"tables": [{"name": "invoices", "count": 1}, {"name": "users", "count": 6}]}
            else:
                data = {"table": params.get("table", ["invoices"])[0], "columns": ["id", "message"], "rows": [{"id": 277, "message": "private-database-value"}], "total": 1}
        route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

    def shot(self, name):
        target = os.environ.get("VIEWER_SCREENSHOT_DIR")
        if target:
            Path(target).mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(Path(target) / (name + ".png")), full_page=True)

    def test_members_navigate_without_new_window_and_cannot_see_db(self):
        self.open()
        expect(self.page.locator("#dbNavButton")).to_be_hidden()
        self.page.locator("#regularNavButton").click()
        expect(self.page.locator("#pageTitle")).to_have_text("정기 처리")
        self.page.locator("#logsNavButton").click()
        expect(self.page.locator("#logDataTable tbody tr")).to_have_count(100)
        expect(self.page.locator("#processingView")).to_be_hidden()
        expect(self.page.locator("#logsNavButton")).to_have_attribute("aria-current", "page")
        self.assertEqual(len(self.context.pages), 1)
        self.assertFalse(any(call["path"].startswith("/api/admin/db") for call in self.calls))
        self.assertEqual(self.page.locator("#logDataTable img").count(), 0)
        self.shot("member-logs")
        self.page.locator("#purchaseNavButton").click()
        expect(self.page.locator("#pageTitle")).to_have_text("구매 처리")
        expect(self.page.locator("#logsView")).to_be_hidden()

    def test_owner_db_and_logs_use_verified_session_header(self):
        self.open("rlckd9646")
        self.page.locator("#dbNavButton").click()
        expect(self.page.locator("#dbDataTable")).to_contain_text("private-database-value")
        self.shot("owner-db")
        self.page.locator("#logsNavButton").click()
        expect(self.page.locator("#logDataTable tbody tr")).to_have_count(100)
        self.assertTrue(all(call["headers"].get("x-accounting-session") == "fixture-session" for call in self.calls if call["path"].startswith(("/api/logs", "/api/admin/db"))))

    def test_search_paging_refresh_and_filters(self):
        self.open(path=ENTRY + "#logs")
        expect(self.page.locator("#logDataTable tbody tr")).to_have_count(100)
        self.page.locator("#logNextButton").click()
        expect(self.page.locator("#logDataTable tbody tr")).to_have_count(23)
        self.page.locator("#logSearchInput").fill("#277")
        self.page.locator("#logSearchInput").press("Enter")
        expect(self.page.locator("#logTableSummary")).to_contain_text("1–100")
        self.page.locator('#logTableList [data-table="regular"]').click()
        expect(self.page.locator("#logTableTitle")).to_have_text("정기 처리")
        self.page.locator("#logRefreshButton").click()
        expect(self.page.locator("#logDataTable tbody tr")).to_have_count(100)
        self.assertTrue(any(call["params"].get("q") == ["#277"] and call["params"].get("table") == ["regular"] for call in self.calls))

    def test_legacy_db_url_preserves_portal_prefix(self):
        self.open("rlckd9646", ENTRY + "admin-db")
        expect(self.page.locator("#dbDataTable")).to_contain_text("private-database-value")
        self.assertEqual(self.page.url, ENTRY + "#db")
        self.assertEqual(len(self.context.pages), 1)

    def test_member_legacy_db_link_falls_back_to_logs(self):
        self.open(path=ENTRY + "admin-db")
        expect(self.page.locator("#logDataTable tbody tr")).to_have_count(100)
        expect(self.page.locator("#dbNavButton")).to_be_hidden()
        self.assertEqual(self.page.url, ENTRY + "#logs")

    def test_unauthenticated_deep_link_requires_login(self):
        self.open(None, ENTRY + "#db")
        expect(self.page.locator("#appShell")).to_be_hidden()
        self.assertFalse(any(call["path"].startswith(("/api/logs", "/api/admin/db")) for call in self.calls))

    def test_gateway_failure_is_readable_and_refresh_recovers(self):
        self.failure = ("/api/logs/overview", 502)
        self.open(path=ENTRY + "#logs")
        expect(self.page.locator("#logErrorBox")).to_contain_text("HTTP 502")
        self.assertNotIn("private proxy", self.page.locator("#logErrorBox").inner_text())
        self.page.locator("#logRefreshButton").click()
        expect(self.page.locator("#logDataTable tbody tr")).to_have_count(100)
        expect(self.page.locator("#logErrorBox")).to_be_hidden()

    def test_session_expiry_clears_db_results_and_returns_to_login(self):
        self.open("rlckd9646", ENTRY + "#db")
        expect(self.page.locator("#dbDataTable")).to_contain_text("private-database-value")
        self.failure = ("/api/admin/db/table", 401)
        self.page.locator("#dbSearchInput").fill("expired")
        self.page.locator("#dbSearchInput").press("Enter")
        expect(self.page.locator("#loginView")).to_be_visible()
        self.assertNotIn("private-database-value", self.page.locator("#dbDataTable").text_content())
        expect(self.page.locator("#dbNavButton")).to_be_hidden()

    def test_narrow_viewport_has_no_document_overflow(self):
        self.open(path=ENTRY + "#logs")
        expect(self.page.locator("#logDataTable tbody tr")).to_have_count(100)
        self.page.set_viewport_size({"width": 420, "height": 900})
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        self.shot("member-logs-narrow")


if __name__ == "__main__":
    unittest.main()
