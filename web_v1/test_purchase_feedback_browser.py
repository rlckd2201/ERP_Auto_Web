"""Isolated Chromium UI tests. No business API, ERP, login or printer is contacted."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
FIXTURE = """<!doctype html><html lang="ko"><head><meta charset="utf-8"></head><body>
<style>body {font-family:Arial,sans-serif;padding:28px;background:#f4f7fa} .admin-only {display:none} button{padding:10px 20px} input,select{padding:8px} .button.primary{background:#087b6c;color:white;border:0;border-radius:6px}</style>
<h1 id="pageTitle">구매 처리</h1><button id="erpQueueButton">원클릭 처리</button>
<table><tbody id="invoicesTable"><tr data-invoice-id="278"><td><input class="invoice-check" type="checkbox" checked></td><td>컴퓨존</td></tr></tbody></table>
<h2 id="purchaseDetailTitle">#278 컴퓨존</h2><div id="purchaseDetailBody">
<section id="outputSetPanel"><button data-output-action="saved_output" disabled>기존 문서 출력</button></section>
<table><tbody><tr data-analysis-index="0"><td><select data-item-field="account"><option>컴퓨터소프트웨어</option><option>소모품비</option></select></td><td><input data-item-field="name" value="Windows 11"></td><td><input data-item-field="dept" value=""></td></tr></tbody></table>
</div></body></html>"""


class FeedbackBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        self.page.route("http://fixture.local/**", lambda route: route.fulfill(body=FIXTURE, content_type="text/html"))
        self.page.goto("http://fixture.local/accounting-automation/")
        self.page.add_style_tag(path=str(ROOT / "frontend/purchase-feedback.css"))
        self.page.evaluate("""() => {
          window.started = 0; window.sent = []; window.nativeAlerts = []; window.fixtureData = [];
          window.alert = message => window.nativeAlerts.push(message);
          window.fetch = async (...args) => { window.sent.push(args); return new Response(JSON.stringify(window.fixtureData), {headers:{'Content-Type':'application/json'}}); };
        }""")
        # Exercise the existing response guard together with the new observer.
        self.page.add_script_tag(path=str(ROOT / "frontend/api-response-guard.js"))
        self.page.add_script_tag(path=str(ROOT / "frontend/purchase-feedback.js"))
        self.page.evaluate("document.getElementById('erpQueueButton').addEventListener('click', () => window.started++)")

    def tearDown(self):
        self.page.close()

    def publish(self, **changes):
        record = {"id": 278, "invoice_type": "purchase", "approval_fetch_status": "error", "approval_fetch_error": "ERROR:RuntimeError: (12345678) 로 검색된 결재완료 품의 문서가 없습니다.", **changes}
        self.page.evaluate("data => {window.fixtureData = data; return fetch('/accounting-automation/api/invoices?mode=purchase', {headers:{'X-Accounting-Session':'fixture-only'}});}", [record])

    def test_empty_department_stops_handler_and_centers_modal_then_focuses_field(self):
        self.page.locator("#erpQueueButton").click()
        modal = self.page.locator("#purchaseFeedbackModal")
        self.assertTrue(modal.is_visible())
        self.assertIn("Windows 11", modal.inner_text())
        self.assertEqual(self.page.evaluate("window.started"), 0)
        self.assertEqual(self.page.evaluate("window.sent.length"), 0)
        box = modal.bounding_box()
        self.assertAlmostEqual(box["x"] + box["width"] / 2, 640, delta=2)
        self.assertAlmostEqual(box["y"] + box["height"] / 2, 450, delta=2)
        if os.getenv("PURCHASE_FEEDBACK_SCREENSHOT_DIR"):
            folder = Path(os.environ["PURCHASE_FEEDBACK_SCREENSHOT_DIR"])
            folder.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(folder / "department-modal.png"))
        modal.get_by_role("button", name="확인").click()
        self.assertEqual(self.page.evaluate("document.activeElement.dataset.itemField"), "dept")
        self.page.locator('[data-item-field="dept"]').fill("전산")
        self.page.locator("#erpQueueButton").click()
        self.assertEqual(self.page.evaluate("window.started"), 1)

    def test_consumables_and_existing_document_printing_remain_available(self):
        self.page.locator('[data-item-field="account"]').select_option(label="소모품비")
        self.page.locator("#erpQueueButton").click()
        self.page.locator('[data-item-field="account"]').select_option(label="컴퓨터소프트웨어")
        self.page.locator('[data-output-action="saved_output"]').evaluate("button => button.disabled = false")
        self.page.locator("#erpQueueButton").click()
        self.assertEqual(self.page.evaluate("window.started"), 2)

    def test_batch_server_error_uses_modal_and_other_alerts_are_unchanged(self):
        self.page.evaluate("alert('부서 입력 필요\\n#901 Windows 11')")
        self.assertIn("#901", self.page.locator("#purchaseFeedbackModal").inner_text())
        self.page.evaluate("alert('원래 오류')")
        self.assertEqual(self.page.evaluate("window.nativeAlerts"), ["원래 오류"])

    def test_approval_failure_visible_to_ordinary_user_only_once_and_recovers(self):
        self.publish()
        modal = self.page.locator("#purchaseFeedbackModal")
        modal.wait_for(state="visible")
        self.assertIn("(12345678)", modal.inner_text())
        self.assertIn("단정할 수는 없습니다", modal.inner_text())
        self.assertIn("전표·세금계산서·현금출금결의서", modal.inner_text())
        if os.getenv("PURCHASE_FEEDBACK_SCREENSHOT_DIR"):
            self.page.screenshot(path=str(Path(os.environ["PURCHASE_FEEDBACK_SCREENSHOT_DIR"]) / "approval-modal.png"))
        modal.get_by_role("button", name="확인").click()
        self.assertTrue(self.page.locator("#purchaseApprovalFeedback").is_visible())
        self.publish()
        self.page.wait_for_timeout(80)
        self.assertFalse(modal.is_visible())
        self.assertEqual(self.page.evaluate("window.sent[0][1].headers['X-Accounting-Session']"), "fixture-only")
        self.assertEqual(self.page.evaluate("window.sent.length"), 2)
        self.publish(approval_fetch_status="done", approval_fetch_error="", approval_pdf_paths=["approval.pdf"])
        self.page.locator("#purchaseApprovalFeedback").wait_for(state="detached")

    def test_failed_background_poll_after_running_surfaces_without_detail_reload(self):
        self.publish(approval_fetch_status="running", approval_fetch_error="")
        self.page.wait_for_timeout(50)
        self.assertEqual(self.page.locator("#purchaseFeedbackModal").count(), 0)
        self.publish()
        self.page.locator("#purchaseFeedbackModal").wait_for(state="visible")

    def test_unselected_errors_do_not_interrupt_and_error_content_is_text(self):
        self.publish(id=277)
        self.page.wait_for_timeout(50)
        self.assertEqual(self.page.locator("#purchaseFeedbackModal").count(), 0)
        self.publish(approval_fetch_error='<img src=x onerror="window.injected=true">')
        self.page.locator("#purchaseFeedbackModal").wait_for(state="visible")
        self.assertEqual(self.page.locator("#purchaseFeedbackModal img").count(), 0)
        self.assertFalse(self.page.evaluate("Boolean(window.injected)"))

    def test_regular_processing_is_unaffected(self):
        self.page.locator("#pageTitle").evaluate("node => node.textContent='정기 처리'")
        self.page.locator("#erpQueueButton").click()
        self.publish(invoice_type="regular")
        self.page.wait_for_timeout(50)
        self.assertEqual(self.page.evaluate("window.started"), 1)
        self.assertEqual(self.page.locator("#purchaseFeedbackModal").count(), 0)

    def test_duplicate_candidates_need_explicit_choice_and_escape_titles(self):
        candidates = [{"doc_id": str(i), "title": '<img src=x onerror="window.injected=true">', "doc_no": f"기안-{i}",
            "form_name": "일강 기안", "drafter_name": "김산울", "drafter_account": "kimsanul", "approved_date": "2026-10-22", "warnings": []} for i in (180287,180288)]
        self.publish(approval_fetch_status="review", approval_fetch_error="조건에 맞는 품의가 여러 건입니다.", approval_search_id="a"*32, approval_candidates=candidates)
        modal=self.page.locator("#purchaseFeedbackModal");modal.wait_for(state="visible")
        self.assertEqual(modal.get_by_role("button",name="이 품의 연결").count(),2)
        self.assertEqual(modal.locator("img").count(),0)
        self.assertEqual(self.page.evaluate("window.sent.length"),1)
        self.page.evaluate("""() => { window.actions=[]; window.requestJson=async (url,options) => {
          window.actions.push({url,options}); if(options?.method==='POST') return {ok:true};
          return {id:278,invoice_type:'purchase',approval_fetch_status:'done',approval_pdf_paths:['verified.pdf']};
        }; }""")
        modal.get_by_role("button",name="이 품의 연결").nth(1).click()
        self.page.get_by_text("#278 품의 연결 완료", exact=True).wait_for(timeout=7000)
        actions=self.page.evaluate("window.actions")
        self.assertEqual(actions[0]["url"],"/api/invoices/278/approval-choice")
        import json
        self.assertEqual(json.loads(actions[0]["options"]["body"]),{"doc_id":"180288","search_id":"a"*32})
        self.assertEqual(self.page.evaluate("window.started"),0)

    def test_truncated_candidates_cannot_be_selected(self):
        self.publish(approval_fetch_status="review", approval_fetch_error="전체 후보 미확인", approval_search_truncated=True,
            approval_candidates=[{"doc_id":"1","title":"후보","warnings":[]}])
        button=self.page.get_by_role("button",name="이 품의 연결");button.wait_for(state="visible")
        self.assertFalse(button.is_enabled())

    def test_missing_approval_without_historical_error_offers_retry(self):
        self.publish(approval_fetch_status="", approval_fetch_error="")
        retry=self.page.get_by_role("button",name="품의 다시 찾기");retry.wait_for(state="visible")
        self.assertTrue(retry.is_enabled())
        self.assertEqual(self.page.locator("#purchaseFeedbackModal").count(),0)


if __name__ == "__main__":
    unittest.main()
