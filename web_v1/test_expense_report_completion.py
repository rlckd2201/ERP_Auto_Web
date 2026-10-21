import ast
import re
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


def load_functions(relative, names, namespace):
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8-sig"))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if len(nodes) != len(names):
        raise AssertionError("Missing source functions")
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), relative, "exec"), namespace)


class FakeClock:
    def __init__(self):
        self.elapsed = 0
        self.after_sleep = lambda: None

    def monotonic(self):
        return self.elapsed

    def sleep(self, seconds):
        self.elapsed += seconds
        self.after_sleep()


class HandlerError(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


class ExpenseCompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf = Path(self.temp.name) / "report.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\n")
        self.clock = FakeClock()
        self.invoice = {"id": 272, "invoice_type": "purchase", "data": {
            "expense_report_pdf_path": str(self.pdf), "expense_report_upload_job_id": "current-job"}}
        self.job = SimpleNamespace(id="current-job", status="done", error=None, message="generated")
        self.log = Mock()
        self.update = Mock()
        self.namespace = {
            "Any": Any, "Request": object, "Path": Path, "time": self.clock,
            "HTTPException": HandlerError, "get_invoice": lambda _: self.invoice,
            "require_setup_ready": lambda _: {"agent_id": "agent", "client_ip": "127.0.0.1"},
            "_request_processor_name": lambda *args: "author", "client_ip": lambda _: "127.0.0.1",
            "_set_expense_report_author": lambda invoice, _: invoice,
            "job_store": SimpleNamespace(create=lambda _: self.job, get=lambda _: self.job,
                                         add_event=Mock()),
            "JobCreateRequest": lambda **kwargs: kwargs,
            "write_expense_report_queue": Mock(return_value="queue.json"),
            "add_invoice_log": self.log, "update_invoice_json": self.update,
            "build_output_set_status": Mock(return_value={"docs": [{"key": "expense_report", "status": "exists"}]}),
        }
        load_functions("web_v1/backend/app.py", {"_invoice_data", "api_generate_expense_report"}, self.namespace)

    def run_handler(self):
        return self.namespace["api_generate_expense_report"](272, object())

    def test_completed_upload_uses_nested_path_without_false_timeout(self):
        result = self.run_handler()
        self.assertEqual(result["data"]["expense_report_upload_job_id"], "current-job")
        self.assertEqual(self.clock.elapsed, 0)
        self.update.assert_not_called()
        self.assertFalse(any(call.kwargs.get("level") == "error" for call in self.log.call_args_list))

    def test_existing_pdf_is_not_accepted_until_this_generation_finishes(self):
        self.job.status = "erp"
        self.invoice["data"]["expense_report_upload_job_id"] = "older-job"

        def complete():
            if self.clock.elapsed >= 2:
                self.job.status = "done"
                self.invoice["data"]["expense_report_upload_job_id"] = "current-job"

        self.clock.after_sleep = complete
        self.run_handler()
        self.assertEqual(self.clock.elapsed, 2)

    def test_done_job_cannot_claim_an_older_uploaded_file(self):
        self.invoice["data"]["expense_report_upload_job_id"] = "older-job"
        with self.assertRaises(HandlerError) as caught:
            self.run_handler()
        self.assertIn("이번 요청", caught.exception.detail)
        self.assertEqual(self.clock.elapsed, 0)

    def test_done_job_without_file_fails_immediately(self):
        self.pdf.unlink()
        with self.assertRaises(HandlerError) as caught:
            self.run_handler()
        self.assertIn("PDF 파일", caught.exception.detail)
        self.assertEqual(self.clock.elapsed, 0)

    def test_directory_cannot_count_as_the_generated_pdf(self):
        self.invoice["data"]["expense_report_pdf_path"] = self.temp.name
        with self.assertRaises(HandlerError):
            self.run_handler()

    def test_agent_error_is_preserved_even_if_an_old_pdf_exists(self):
        self.job.status = "error"
        self.job.error = "Excel export failed"
        with self.assertRaises(HandlerError) as caught:
            self.run_handler()
        self.assertIn("Excel export failed", caught.exception.detail)
        self.assertEqual(self.clock.elapsed, 0)

    def test_still_pending_job_retains_real_timeout(self):
        self.job.status = "erp"
        with self.assertRaises(HandlerError) as caught:
            self.run_handler()
        self.assertEqual(caught.exception.status_code, 408)
        self.assertEqual(self.clock.elapsed, 120)


class ExpenseDateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.namespace = {"Any": Any, "Path": Path, "date": date, "re": re, "time": time,
                         "_extract_pdf_text_for_date": lambda _: ""}
        load_functions("web_v1/backend/erp_runner.py", {
            "_format_invoice_date", "_extract_invoice_date_from_text", "_extract_invoice_date"}, cls.namespace)
        load_functions("web_v1/backend/output_set.py", {"_display_date", "_expense_report_date"}, cls.namespace)

    def display(self, value):
        return self.namespace["_display_date"](value)

    def test_every_month_preserves_the_complete_date(self):
        for month in range(1, 13):
            with self.subTest(month=month):
                self.assertEqual(self.display(f"2026-{month:02d}-20"), f"2026. {month:02d}. 20")

    def test_supported_separators_and_compact_dates(self):
        for value in ["20261020", "2026/10/20", "2026. 10. 20", "2026년 10월 20일"]:
            with self.subTest(value=value):
                self.assertEqual(self.display(value), "2026. 10. 20")

    def test_calendar_invalid_dates_are_rejected(self):
        for value in ["2026-01-00", "2026-02-29", "2026-04-31", "2026-13-20", "not a date"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.display(value)

    def test_leap_day_is_supported(self):
        self.assertEqual(self.display("2024-02-29"), "2024. 02. 29")

    def test_report_keeps_its_invoice_date_rather_than_today(self):
        report_date = self.namespace["_expense_report_date"]
        self.assertEqual(report_date({}, {"invoice_date": "2026-10-20"}), "2026. 10. 20")

    def test_blank_date_keeps_existing_today_default(self):
        self.assertEqual(self.display(""), time.strftime("%Y. %m. %d"))


if __name__ == "__main__":
    unittest.main()
