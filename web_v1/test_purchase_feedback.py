"""Pre-dispatch validation and actionable approval errors, with no live ERP or mail."""
import re
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from web_v1.test_purchase_shared_execution import load, RequestError
from web_v1 import test_purchase_shared_execution as routing_tests


def department_namespace():
    return load("web_v1/backend/erp_runner.py", {
        "_clean_text", "_purchase_account", "_purchase_dept_from_context", "purchase_department_issues",
    }, {"re": re})


class DepartmentTests(unittest.TestCase):
    def setUp(self):
        self.check = department_namespace()["purchase_department_issues"]

    def invoice(self, **changes):
        item = {"account": "컴퓨터소프트웨어", "name": "Windows 11", "dept": "", **changes}
        return {"id": 278, "data": {"items": [item]}}

    def test_assets_need_department_but_consumables_do_not(self):
        for account in ("집기비품", "컴퓨터소프트웨어", "컴퓨터SW", "전산비품"):
            with self.subTest(account=account):
                self.assertEqual(len(self.check(self.invoice(account=account, dept=" \t"))), 1)
        self.assertEqual(self.check(self.invoice(account="소모품비")), [])
        self.assertEqual(self.check(self.invoice(is_a=False)), [])
        self.assertEqual(self.check(self.invoice(dept="전산")), [])
        self.assertEqual(len(self.check(self.invoice(dept="소모품"))), 1)

    def test_explicit_blank_cannot_be_silently_inferred(self):
        self.assertTrue(self.check(self.invoice(name="노트북 (전산팀)")))
        invoice = self.invoice(name="노트북 (전산팀)")
        del invoice["data"]["items"][0]["dept"]
        self.assertEqual(self.check(invoice), [])  # Legacy inference is preserved.

    def test_current_analysis_overrides_legacy_raw(self):
        invoice = self.invoice()
        invoice["raw"] = {"data": {"items": [{"account": "집기비품", "dept": "인사"}]}}
        self.assertTrue(self.check(invoice))
        invoice["data"]["items"][0]["dept"] = "구매"
        self.assertEqual(self.check(invoice), [])

    def test_raw_only_and_multiple_items_keep_row_numbers(self):
        items = [{"account": "소모품비"}, {"account": "집기비품", "name": "모니터"}, {"account": "컴퓨터소프트웨어", "dept": ""}]
        issues = self.check({"raw": {"data": {"items": items}}})
        self.assertEqual(len(issues), 2)
        self.assertTrue(issues[0].startswith("2행"))
        self.assertTrue(issues[1].startswith("3행"))


class BeforeQueueTests(unittest.TestCase):
    def setUp(self):
        harness = routing_tests.PipelineTests()
        harness.setUp()
        self.h = harness
        self.items = {
            900: {"id": 900, "data": {"items": [{"account": "집기비품", "name": "노트북", "dept": "인사"}]}},
            901: {"id": 901, "data": {"items": [{"account": "컴퓨터소프트웨어", "name": "Windows 11", "dept": ""}]}},
        }
        harness.ns["get_invoice"] = self.items.get
        harness.ns["purchase_department_issues"] = department_namespace()["purchase_department_issues"]
        load("web_v1/backend/app.py", {"_require_purchase_departments"}, harness.ns)

    def test_single_and_batch_reject_before_job_creation(self):
        for endpoint in ("create_purchase_one_click_job", "create_purchase_erp_input_job"):
            for ids in ([901], [900, 901]):
                with self.subTest(endpoint=endpoint, ids=ids):
                    self.h.body.invoice_ids = ids
                    with self.assertRaises(RequestError) as caught:
                        self.h.ns[endpoint](self.h.body, object())
                    self.assertEqual(caught.exception.status_code, 422)
                    self.assertIn("#901", caught.exception.detail)
                    self.assertIn("Windows 11", caught.exception.detail)
                    self.assertEqual(self.h.jobs, [])
                    self.h.ns["worker"].submit.assert_not_called()

    def test_corrected_analysis_is_checked_and_routes_to_243(self):
        def save(invoice_id, analysis, **kwargs):
            self.items[invoice_id]["data"] = analysis
        self.h.ns["_apply_purchase_analysis_payload"] = save
        self.h.body.invoice_ids = [901]
        self.h.body.analysis = {"items": [{"account": "컴퓨터소프트웨어", "dept": "전산"}]}
        result = self.h.ns["create_purchase_one_click_job"](self.h.body, object())
        self.assertEqual(result["payload"]["target_agent_id"], "shared243")
        self.assertEqual(result["payload"]["printer_name"], "Song chosen printer")

    def test_existing_documents_can_print_without_new_department_validation(self):
        self.h.body.invoice_ids = [901]
        self.h.ns["_invoice_output_set_ready"].return_value = True
        result = self.h.ns["create_purchase_one_click_job"](self.h.body, object())
        self.assertEqual(result["job_type"], "output_set")
        self.assertEqual(result["payload"]["target_agent_id"], "song")

    def test_batch_error_is_bounded_for_safe_api_guard(self):
        self.items[901]["data"]["items"] *= 30
        with self.assertRaises(RequestError) as caught:
            self.h.ns["_require_purchase_departments"]([901])
        self.assertLess(len(caught.exception.detail), 600)
        self.assertIn("외 26개", caught.exception.detail)

    def test_save_confirmation_guard_still_runs_before_analysis_mutation(self):
        self.h.ns["requires_erp_save_confirmation"] = lambda _: True
        self.h.body.invoice_ids = [901]
        self.h.body.analysis = {"items": [{"account": "집기비품", "dept": "전산"}]}
        with self.assertRaises(RequestError) as caught:
            self.h.ns["create_purchase_one_click_job"](self.h.body, object())
        self.assertEqual(caught.exception.status_code, 409)
        self.h.ns["_apply_purchase_analysis_payload"].assert_not_called()


class ApprovalReasonTests(unittest.TestCase):
    def setUp(self):
        self.message = load("web_v1/backend/approval_fetcher.py", {"_approval_failure_message"}, {"re": re})["_approval_failure_message"]

    def test_attachment_search_no_match_is_not_claimed_as_proven_missing_filename(self):
        text = self.message(["ERROR:RuntimeError: (12345678) 로 검색된 결재완료 품의 문서가 없습니다."])
        self.assertIn("첨부파일명 '(12345678)'", text)
        self.assertIn("괄호까지", text)
        self.assertIn("결재가 완료", text)
        self.assertIn("단정할 수는 없습니다", text)
        self.assertNotIn("Traceback", text)

    def test_missing_order_and_timeout_have_different_actions(self):
        self.assertIn("주문번호를 읽지 못", self.message(["ERROR:RuntimeError: 견적서에서 주문번호를 찾지 못했습니다."]))
        self.assertIn("시간이 초과", self.message(["ERROR:TimeoutError: Page.goto Timeout 30000ms"]))

    def test_unknown_failure_does_not_expose_arguments_or_traceback(self):
        text = self.message(["Traceback: /server/path", "ERROR:Error: command --password secret"])
        self.assertNotIn("secret", text)
        self.assertNotIn("/server/path", text)
        self.assertIn("로그 확인", text)


if __name__ == "__main__":
    unittest.main()
