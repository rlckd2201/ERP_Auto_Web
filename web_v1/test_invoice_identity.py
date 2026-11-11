import ast
import json
import re
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import fitz
from web_v1.backend import invoice_db, invoice_identity as identity

NUMBER = "2026111141000018DA100001"
OTHER = "2026111141000018DA100002"


class InvoiceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "fixture.db"
        self.addCleanup(patch.stopall)
        patch.object(invoice_db, "settings", SimpleNamespace(
            sqlite_db_path=self.db, download_dir=self.root)).start()
        with closing(invoice_db.get_conn()) as setup_conn:
            with patch.object(invoice_db, "get_conn", return_value=setup_conn):
                invoice_db.init_db()
        patch.object(invoice_db, "init_db", lambda: None).start()
        patch.object(invoice_db, "_repair_regular_fields", lambda result, path: result).start()
        identity._pdf_numbers.cache_clear()

    def conn(self):
        conn = sqlite3.connect(self.db, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def pdf(self, name, number=NUMBER):
        path = self.root / name
        with fitz.open() as document:
            page = document.new_page()
            page.insert_text((30, 45), "승인번호\n" + number, fontname="korea", fontsize=11)
            document.save(path)
        return str(path)

    def result(self, path):
        return {"ok": True, "portal": "csbill", "pdf_path": path,
                "data": {"vendor_name": "fixture", "total_sum": 3652000}}

    def insert(self, path):
        return invoice_db.insert_crawler_invoice("정기 세금계산서", self.result(path))

    def count(self):
        with closing(self.conn()) as conn:
            return conn.execute("SELECT count(*) FROM invoices").fetchone()[0]

    def test_labelled_alphanumeric_and_hyphenated_numbers(self):
        for text in ("승인번호\n2026111141000018da100001",
                     "승 인 번 호: 20261111-41000018-DA100001",
                     "승인번호 ２０２６１１１１４１００００１８ＤＡ１００００１"):
            self.assertEqual(identity.numbers_from_text(text), {NUMBER})
        self.assertEqual(identity.numbers_from_text("주문번호 " + NUMBER), set())
        self.assertEqual(identity.normalize_approval_number("2026130141000018DA100001"), "")
        self.assertEqual(identity.numbers_from_text("승인번호 " + NUMBER + "9"), set())

    def test_retry_with_different_pdf_name_inserts_once(self):
        self.assertTrue(self.insert(self.pdf("bill_1.pdf")))
        self.assertFalse(self.insert(self.pdf("bill_2.pdf")))
        self.assertEqual(self.count(), 1)
        with closing(self.conn()) as conn:
            row = conn.execute("SELECT json_data FROM invoices").fetchone()
            self.assertEqual(json.loads(row[0])["tax_approval_number"], NUMBER)

    def test_different_approval_same_price_is_not_merged(self):
        self.assertTrue(self.insert(self.pdf("first.pdf")))
        self.assertTrue(self.insert(self.pdf("different.pdf", OTHER)))
        self.assertEqual(self.count(), 2)

    def test_legacy_completed_row_is_preserved(self):
        path = self.pdf("legacy.pdf")
        with closing(self.conn()) as conn, conn:
            conn.execute(
                "INSERT INTO invoices (pdf_path,json_data,status,processor,erp_job_id,processed_at) VALUES (?,?,?,?,?,?)",
                (path, json.dumps(self.result(path)), invoice_db.DONE, "existing user", "existing-job", "2026-11-01"))
            before = tuple(conn.execute("SELECT * FROM invoices").fetchone())
        self.assertFalse(self.insert(self.pdf("resent.pdf")))
        with closing(self.conn()) as conn:
            self.assertEqual(tuple(conn.execute("SELECT * FROM invoices").fetchone()), before)

    def test_concurrent_collectors_insert_one_record(self):
        paths = [self.pdf(f"race-{i}.pdf") for i in range(4)]
        barrier = threading.Barrier(4)
        def collect(path):
            barrier.wait(timeout=5)
            return self.insert(path)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(collect, paths))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(self.count(), 1)

    def test_registration_log_failure_rolls_back_invoice(self):
        path = self.pdf("atomic.pdf")
        with closing(self.conn()) as conn, conn:
            conn.execute("CREATE TRIGGER fail_log BEFORE INSERT ON invoice_logs BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(path)
        self.assertEqual(self.count(), 0)
        with closing(self.conn()) as conn, conn:
            conn.execute("DROP TRIGGER fail_log")
        self.assertTrue(self.insert(path))
        self.assertFalse(self.insert(path))

    def test_conflicting_numbers_and_voucher_metadata_are_not_trusted(self):
        path = self.pdf("conflict.pdf")
        self.assertEqual(identity.tax_approval_number(
            {"pdf_path": path, "tax_approval_number": OTHER}), "")
        self.assertEqual(identity.tax_approval_number(
            {"output_docs": {"approval_no": NUMBER}}), "")
        self.assertEqual(identity.tax_approval_number(
            {"pdf_path": "missing.pdf", "raw": {"tax_approval_number": NUMBER}}), NUMBER)

    def test_transient_pdf_read_failure_can_recover(self):
        path = self.pdf("retry.pdf")
        with patch.object(fitz, "open", side_effect=OSError("temporarily busy")):
            self.assertEqual(identity.tax_approval_number({"pdf_path": path}), "")
        self.assertEqual(identity.tax_approval_number({"pdf_path": path}), NUMBER)

    def auto_candidates(self, invoices):
        source = (Path(__file__).parent / "backend/app.py").read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        names = {
            "_regular_auto_normalize_path", "_regular_auto_document_path",
            "_regular_auto_clean_number", "_regular_auto_is_number_key",
            "_regular_auto_xml_issue_id", "_regular_auto_number_values",
            "_regular_auto_path_values", "_regular_auto_dedupe_keys",
            "_regular_auto_candidate_invoices",
        }
        skipped = []
        by_id = {item["id"]: item for item in invoices}
        ns = {
            "__package__": "web_v1.backend", "Any": object, "Path": Path, "re": re,
            "WAITING": invoice_db.WAITING,
            "settings": SimpleNamespace(regular_auto_scan_limit=200, regular_auto_max_batch=20),
            "list_invoices": lambda **kw: sorted(invoices, key=lambda i: i["id"], reverse=True),
            "get_invoice": by_id.get, "_invoice_data": lambda i: {**i.get("raw", {}), **i.get("data", {})},
            "_regular_auto_output_ready": lambda i: False, "_invoice_is_zoom_billing": lambda i: False,
            "build_regular_erp_payload": lambda i: {},
            "_regular_auto_mark_skip": lambda i, reason, detail: skipped.append((i["id"], reason)),
        }
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "production-auto-selection", "exec"), ns)
        result = ns["_regular_auto_candidate_invoices"]()
        return [item["id"] for item, keys in result], skipped

    def invoice(self, rid, path, status=invoice_db.WAITING):
        return {"id": rid, "pdf_path": path, "invoice_type": "regular",
                "status": status, "raw": self.result(path)}

    def test_pending_legacy_duplicates_queue_only_oldest(self):
        invoices = [self.invoice(294, self.pdf("one.pdf")), self.invoice(295, self.pdf("two.pdf"))]
        selected, skipped = self.auto_candidates(invoices)
        self.assertEqual(selected, [294])
        self.assertEqual(skipped, [(295, "duplicate")])

    def test_completed_or_queued_invoice_blocks_duplicate(self):
        for status in (invoice_db.DONE, invoice_db.ERP_QUEUED, invoice_db.PROCESSING):
            invoices = [self.invoice(294, self.pdf(f"old-{status}.pdf"), status),
                        self.invoice(295, self.pdf(f"new-{status}.pdf"))]
            self.assertEqual(self.auto_candidates(invoices), ([], [(295, "duplicate")]))

    def test_auto_distinct_same_price_documents_both_queue(self):
        invoices = [self.invoice(1, self.pdf("same-price-one.pdf")),
                    self.invoice(2, self.pdf("same-price-two.pdf", OTHER))]
        self.assertEqual(self.auto_candidates(invoices), ([1, 2], []))

    def test_csbill_missing_or_ambiguous_identity_is_held(self):
        item = self.invoice(1, self.pdf("unreadable.pdf", "no approval"))
        self.assertEqual(self.auto_candidates([item]), ([], [(1, "tax_identity_unverified")]))
        item["raw"]["approval_no"] = NUMBER
        item["raw"]["data"]["approval_no"] = OTHER
        self.assertEqual(self.auto_candidates([item]), ([], [(1, "tax_identity_unverified")]))


if __name__ == "__main__":
    unittest.main()
