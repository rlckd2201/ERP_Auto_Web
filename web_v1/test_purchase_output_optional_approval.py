"""Output regression fixtures; no live database, ERP, Agent or printer is used."""
from __future__ import annotations

import ast
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import fitz


ROOT = Path(__file__).resolve().parents[1]


def load_output_functions(namespace):
    # Avoid importing the production settings and database in isolated fixtures.
    path = ROOT / "web_v1/backend/output_set.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) or (
        isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        and node.target.id == "OUTPUT_DOCS") or (
        isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "STATUS_LABELS"
                                            for t in node.targets))]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)


class PurchaseOutputTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.data = {}
        self.invoice = {"id": 277, "invoice_type": "purchase", "data": self.data}
        self.log = Mock()
        self.ns = {
            "Path": Path, "os": os, "shutil": shutil,
            "settings": SimpleNamespace(erp_db_dir=self.root, erp_output_dir=self.root / "erp_outputs"),
            "get_invoice": lambda _: self.invoice,
            "update_invoice_json": lambda _, updates, **kw: self.data.update(updates),
            "add_invoice_log": self.log,
        }
        load_output_functions(self.ns)
        self.generate = Mock(side_effect=AssertionError("Unexpected expense generation"))
        self.ns["generate_expense_report_pdf"] = self.generate
        self.ns["_print_pdf"] = Mock(side_effect=AssertionError("Must not print from fixture"))
        self.paths = {}
        for key, data_key in (("erp_voucher", "erp_pdf_path"), ("tax_invoice", "pdf_path"),
                              ("expense_report", "expense_report_pdf_path")):
            path = self.make_pdf(key)
            self.paths[key] = path
            self.data[data_key] = str(path)

    def make_pdf(self, label):
        path = self.root / (label + ".pdf")
        with fitz.open() as doc:
            doc.new_page().insert_text((40, 40), label)
            doc.save(path)
        return path

    def prepare(self, **kwargs):
        return self.ns["prepare_output_documents"](self.invoice, **kwargs)

    def labels(self, paths):
        texts = []
        for path in paths:
            with fitz.open(path) as doc:
                texts.append([page.get_text().strip() for page in doc])
        return texts

    def test_missing_approval_prints_three_existing_pdfs_in_order(self):
        result = self.prepare(existing_only=True)
        self.assertTrue(result["ready"])
        self.assertTrue(result["can_output"])
        self.assertEqual(result["blockers"], [])
        self.assertEqual(self.labels(result["individual_files"]),
                         [["erp_voucher"], ["tax_invoice"], ["expense_report"]])
        self.assertEqual([d["key"] for d in result["skipped_docs"]], ["approval_docs"])
        approval = next(d for d in result["docs"] if d["key"] == "approval_docs")
        self.assertEqual(approval["status"], "missing")
        self.generate.assert_not_called()

    def test_available_approval_attachments_are_included_and_merged(self):
        self.data["approval_pdf_paths"] = [str(self.make_pdf("approval1")), str(self.make_pdf("approval2"))]
        result = self.prepare(existing_only=True)
        self.assertEqual(self.labels(result["individual_files"]),
                         [["erp_voucher"], ["tax_invoice"], ["approval1", "approval2"], ["expense_report"]])
        self.assertEqual(result["skipped_docs"], [])

    def test_missing_each_required_pdf_still_blocks_existing_only(self):
        for key, path in self.paths.items():
            with self.subTest(key=key):
                content = path.read_bytes()
                path.unlink()
                try:
                    with self.assertRaisesRegex(RuntimeError, "필수 문서"):
                        self.prepare(existing_only=True)
                    self.assertFalse((self.root / "output_sets").exists())
                finally:
                    path.write_bytes(content)
        self.generate.assert_not_called()

    def test_missing_approval_explicitly_selected_still_fails(self):
        with self.assertRaisesRegex(RuntimeError, "선택한 문서가 준비되지"):
            self.prepare(existing_only=True, selected_doc_keys=["approval_docs"])

    def test_explicit_selection_does_not_add_unselected_documents(self):
        result = self.prepare(existing_only=True, selected_doc_keys=["tax_invoice"])
        self.assertEqual(self.labels(result["individual_files"]), [["tax_invoice"]])
        self.assertEqual(result["skipped_docs"], [])

    def test_failed_expense_report_still_blocks(self):
        self.paths["expense_report"].unlink()
        self.data["output_docs"] = {"docs": [{"key": "expense_report", "status": "failed", "message": "Excel failed"}]}
        with self.assertRaisesRegex(RuntimeError, "필수 문서"):
            self.prepare()
        self.generate.assert_not_called()

    def test_regular_output_unchanged(self):
        self.invoice["invoice_type"] = "regular"
        result = self.prepare(existing_only=True)
        self.assertEqual(self.labels(result["individual_files"]), [["erp_voucher"], ["tax_invoice"]])
        self.assertEqual(result["skipped_docs"], [])
        self.paths["erp_voucher"].unlink()
        for path in (self.root / "output_sets").rglob("01_*.pdf"):
            path.unlink()
        with self.assertRaisesRegex(RuntimeError, "필수 문서"):
            self.prepare(existing_only=True)

    def test_zoom_still_requires_agent_generated_expense(self):
        if "zoom_billing" not in self.ns["OUTPUT_DOCS"]:
            self.skipTest("Zoom support is not present in this source revision")
        self.data["zoom_billing"] = True
        self.paths["expense_report"].unlink()
        with self.assertRaisesRegex(RuntimeError, "필수 문서"):
            self.prepare(existing_only=True)
        with self.assertRaisesRegex(RuntimeError, "user PC Agent"):
            self.prepare()

    def test_repeat_preparation_does_not_duplicate_pages(self):
        self.prepare(existing_only=True)
        result = self.prepare(existing_only=True)
        self.assertEqual(self.labels(result["individual_files"]),
                         [["erp_voucher"], ["tax_invoice"], ["expense_report"]])

    def test_job_records_missing_approval_warning_without_stopping(self):
        result = self.ns["run_output_set_job"]([277], action="individual_pdf", existing_only=True, job_id="fixture")
        self.assertEqual(len(result["results"][0]["individual_files"]), 3)
        self.assertEqual(result["results"][0]["skipped_docs"][0]["key"], "approval_docs")
        warnings = [c for c in self.log.call_args_list if c.kwargs.get("level") == "warning"]
        self.assertEqual(len(warnings), 1)
        self.assertIn("전자결재 품의", warnings[0].args[1])
        self.ns["_print_pdf"].assert_not_called()

    def test_worker_queues_three_files_to_selected_requester_printer(self):
        source = ROOT / "web_v1/backend/worker.py"
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "JobWorker")
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_run_output_set")
        queue = Mock(return_value=self.root / "fixture_queue.json")
        self.ns["write_output_print_queue"] = queue
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), self.ns)
        job = SimpleNamespace(id="fixture", payload={"invoice_ids": [277], "action": "print_individual",
            "existing_only": True, "printer_name": "Selected Samsung", "printer_key": "pyeongtaek",
            "target_agent_id": "requesting-user-pc", "target_client_ip": "192.0.2.18"})
        worker = SimpleNamespace(store=SimpleNamespace(add_event=Mock()))
        result = self.ns["_run_output_set"](worker, job)
        self.assertTrue(result["defer_completion"])
        queue.assert_called_once()
        self.assertEqual(len(queue.call_args.args[1][0]["individual_files"]), 3)
        self.assertEqual(queue.call_args.kwargs["target_agent_id"], "requesting-user-pc")
        self.assertEqual(queue.call_args.kwargs["printer_name"], "Selected Samsung")
        self.generate.assert_not_called()
        self.ns["_print_pdf"].assert_not_called()

    def test_one_click_reuses_saved_documents_without_reentering_erp(self):
        source = ROOT / "web_v1/backend/app.py"
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        names = {"_invoice_output_set_ready", "create_purchase_one_click_job"}
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            node.decorator_list = []
        caller = {"agent_id": "requesting-user-pc", "client_ip": "192.0.2.18"}
        executor = {"agent_id": "shared-erp-pc", "client_ip": "192.0.2.243"}
        job = SimpleNamespace(to_response=lambda: "queued")
        create = Mock(return_value=job)
        submit = Mock()
        self.ns.update({
            "_purchase_execution_setup": lambda _: (caller, executor),
            "_request_processor_name": lambda *args: "requesting author",
            "_one_click_output_payload": lambda *args: {"action": "print_individual",
                "printer_key": "pyeongtaek", "printer_name": "Selected Samsung"},
            "requires_erp_save_confirmation": lambda _: False,
            "_require_purchase_departments": Mock(),
            "JobCreateRequest": lambda **kwargs: SimpleNamespace(**kwargs),
            "job_store": SimpleNamespace(create=create), "worker": SimpleNamespace(submit=submit),
        })
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), self.ns)
        body = SimpleNamespace(invoice_ids=[277], processor="requesting author", output_target="pyeongtaek", analysis=None)
        self.assertEqual(self.ns["create_purchase_one_click_job"](body, object()), "queued")
        request = create.call_args.args[0]
        self.assertEqual(request.job_type, "output_set")
        self.assertTrue(request.payload["existing_only"])
        self.assertEqual(request.payload["target_agent_id"], caller["agent_id"])
        submit.assert_called_once_with(job)


if __name__ == "__main__":
    unittest.main()
