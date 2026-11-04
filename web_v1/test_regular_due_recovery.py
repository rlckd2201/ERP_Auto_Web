"""Scheduled report recovery against real SQLite/files; SMTP is always mocked."""
from __future__ import annotations

import copy
import json
import os
import smtplib
import socket
import sqlite3
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from web_v1.backend import regular_due_monitor as monitor


class RecoveryCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = self.root / "invoices.db"
        settings = SimpleNamespace(**vars(monitor.settings))
        settings.sqlite_db_path = self.database
        settings.erp_db_dir = self.root
        settings.regular_auto_result_email = "internal@example.com"
        settings.regular_auto_result_smtp_user = ""
        settings.regular_auto_result_smtp_pw = ""
        for patcher in (
            patch.object(monitor, "settings", settings),
            patch.dict(os.environ, {
                "REGULAR_DUE_ALERT_ENABLED": "1",
                "REGULAR_DUE_SENDER_HOST": socket.gethostname(),
                "REGULAR_DUE_ALERT_EMAIL": "internal@example.com",
                "REGULAR_DUE_VENDOR_ALERT_CC": "internal@example.com",
                "REGULAR_DUE_VENDOR_ALERT_ENABLED": "1",
                "REGULAR_DUE_ALERT_START_DATE": "2026-10-01",
                "REGULAR_DUE_ALERT_SCAN_LIMIT": "200",
            }),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def create_database(self):
        connection = sqlite3.connect(self.database)
        connection.execute("""CREATE TABLE invoices (
            id INTEGER PRIMARY KEY, subject TEXT, pdf_path TEXT, json_data TEXT,
            status TEXT, processor TEXT, received_at TEXT, processed_at TEXT,
            last_error TEXT, erp_job_id TEXT)""")
        connection.commit()
        connection.close()

    def insert(self, invoice_id, data, *, subject="시큐어포인트", raw_json=None):
        connection = sqlite3.connect(self.database)
        connection.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?)", (
            invoice_id, subject, "invoice.pdf",
            raw_json if raw_json is not None else json.dumps(data, ensure_ascii=False),
            "처리완료", "담당자", "2026-11-02 17:59:32", "2026-11-02 18:02:10", "", "job-existing",
        ))
        connection.commit()
        connection.close()

    def report(self, *, missing=True):
        items = []
        for key, expected in (("securepoint", date(2026, 10, 31)), ("ahnlab", date(2026, 10, 7))):
            rule = monitor._rule_by_key(key)
            item = monitor._evaluate_rule(rule, expected, expected, date(2026, 11, 4), [], set())
            if not missing:
                item.update(severity="pending", status="수신예정")
            items.append(item)
        return dict(enabled=True, recipient="internal@example.com", alert_hour=12,
                    reference_date="2026-11-04", item_count=2, trigger_count=0,
                    missing_count=2 if missing else 0, warning_count=0,
                    pending_count=0 if missing else 2, ok_count=0, items=items)

    def dispatch_fixtures(self, *, missing=True, side_effect=None):
        report = self.report(missing=missing)
        build = patch.object(monitor, "build_regular_due_report", side_effect=lambda *a: copy.deepcopy(report))
        smtp = patch.object(monitor, "_send_html_mail", side_effect=side_effect)
        build_mock, smtp_mock = build.start(), smtp.start()
        self.addCleanup(build.stop)
        self.addCleanup(smtp.stop)
        return report, build_mock, smtp_mock


class SnapshotTests(RecoveryCase):
    def test_reads_while_another_writer_holds_reservation_and_does_not_write(self):
        self.create_database()
        self.insert(1, {"invoice_type": "regular", "supplier_name": "시큐어포인트", "invoice_date": "2026-10-31"})
        before = self.database.read_bytes()
        writer = sqlite3.connect(self.database)
        self.addCleanup(writer.close)
        writer.execute("BEGIN IMMEDIATE")
        with patch("web_v1.backend.invoice_db.init_db", side_effect=AssertionError("schema initialization forbidden")):
            rows = monitor._load_regular_invoices()
        self.assertEqual([row["id"] for row in rows], [1])
        self.assertEqual(monitor._invoice_issue_date(rows[0]), date(2026, 10, 31))
        writer.rollback()
        self.assertEqual(self.database.read_bytes(), before)

    def test_nested_and_flat_invoice_metadata_survive(self):
        self.create_database()
        self.insert(1, {"invoice_type": "regular", "supplier_name": "시큐어포인트", "invoice_date": "2026-10-31", "total_sum": 1039390})
        self.insert(2, {"invoice_type": "regular", "data": {"supplier_name": "시큐어포인트", "invoice_date": "2026-09-30", "total_sum": 1234}})
        rows = monitor._load_regular_invoices()
        self.assertEqual([monitor._amount(row) for row in rows], ["1,234", "1,039,390"])
        self.assertEqual([monitor._invoice_issue_date(row) for row in rows], [date(2026, 9, 30), date(2026, 10, 31)])
        self.assertTrue(all(monitor._rule_matches_invoice(monitor._rule_by_key("securepoint"), row) for row in rows))
        self.assertEqual(rows[0]["erp_job_id"], "job-existing")

    def test_preserves_latest_row_limit_and_excludes_purchase(self):
        self.create_database()
        self.insert(1, {"invoice_type": "regular"})
        self.insert(2, {"invoice_type": "purchase"}, subject="컴퓨존")
        self.assertEqual(monitor._load_regular_invoices(limit=1), [])
        self.assertEqual([row["id"] for row in monitor._load_regular_invoices(limit=2)], [1])

    def test_missing_database_is_not_created(self):
        with self.assertRaises(sqlite3.OperationalError):
            monitor._load_regular_invoices()
        self.assertFalse(self.database.exists())

    def test_corrupt_invoice_aborts_without_a_false_missing_reminder(self):
        self.create_database()
        self.insert(1, {}, raw_json="{broken")
        with patch.object(monitor, "_send_html_mail") as smtp:
            with self.assertRaisesRegex(ValueError, "#1"):
                monitor.send_regular_due_report("2026-11-04")
        smtp.assert_not_called()
        self.assertFalse(monitor._state_path().exists())

    def test_non_object_invoice_aborts(self):
        self.create_database()
        self.insert(1, {}, raw_json="[]")
        with self.assertRaisesRegex(ValueError, "#1"):
            monitor._load_regular_invoices()

    def test_lock_failure_then_next_attempt_recovers_without_marking_failed_send(self):
        self.create_database()
        self.insert(1, {"invoice_type": "regular", "invoice_date": "2026-09-30", "supplier_name": "시큐어포인트"})
        writer = sqlite3.connect(self.database)
        self.addCleanup(writer.close)
        writer.execute("BEGIN EXCLUSIVE")
        with patch.object(monitor, "_send_html_mail") as smtp, patch.object(monitor, "_send_regular_vendor_alerts", return_value=[]):
            started = time.monotonic()
            with self.assertRaises(sqlite3.OperationalError):
                monitor.send_regular_due_report("2026-11-04")
            self.assertLess(time.monotonic() - started, 8)
            smtp.assert_not_called()
            self.assertFalse(monitor._state_path().exists())
            writer.rollback()
            result = monitor.send_regular_due_report("2026-11-04")
        self.assertTrue(result["sent"])
        smtp.assert_called_once()

    def test_history_uses_read_only_snapshot(self):
        self.create_database()
        self.insert(1, {"invoice_type": "regular", "invoice_date": "2026-10-31", "total_sum": 100})
        with patch("web_v1.backend.invoice_db.init_db", side_effect=AssertionError("no writes")):
            result = monitor.regular_due_history()
        self.assertEqual(result["items"][0]["invoice_id"], 1)
        self.assertEqual(result["items"][0]["amount"], "100")


class CycleTests(RecoveryCase):
    def test_dates_cover_every_month_without_partial_month_matches(self):
        for month in range(1, 13):
            expected = date(2026, month, 14)
            for text in (expected.isoformat(), f"2026/{month}/14", f"2026년 {month}월 14일", expected.strftime("%Y%m%d")):
                with self.subTest(text=text):
                    self.assertEqual(monitor._parse_date(text), expected)

    def test_date_objects_short_dates_timestamps_and_filenames(self):
        for value, expected in (
            (date(2026, 11, 4), date(2026, 11, 4)),
            ("2026-11-04T12:00:00", date(2026, 11, 4)),
            ("261104", date(2026, 11, 4)),
            ("세금계산서_시큐어포인트_2026-12-31.pdf", date(2026, 12, 31)),
            ("invoice_20261104.pdf", date(2026, 11, 4)),
        ):
            with self.subTest(value=value):
                self.assertEqual(monitor._parse_date(value), expected)

    def test_invalid_dates_are_not_truncated_into_valid_ones(self):
        for text in ("2026-11-31", "2026-13-01", "2026-11-041", "202611041", "2026-00-01", "2026-11-00", "2026-02-29"):
            with self.subTest(text=text):
                self.assertIsNone(monitor._parse_date(text))

    def invoice(self, issued):
        return {"id": 1, "subject": "시큐어포인트", "data": {"invoice_date": issued, "supplier_name": "시큐어포인트"}}

    def test_month_boundary_preserves_overdue_and_received_cycle_choices(self):
        rule = monitor._rule_by_key("securepoint")
        previous = self.invoice("2026-09-30")
        received = self.invoice("2026-10-31")
        for today, invoices, expected in (
            (date(2026, 10, 31), [previous], date(2026, 10, 31)),
            (date(2026, 11, 1), [previous], date(2026, 10, 31)),
            (date(2026, 11, 1), [previous, received], date(2026, 10, 31)),
            (date(2026, 11, 4), [previous], date(2026, 10, 31)),
            (date(2026, 11, 4), [previous, received], date(2026, 11, 30)),
        ):
            with self.subTest(today=today, received=len(invoices)):
                self.assertEqual(monitor._cycle_for_report(rule, today, invoices)[1], expected)

    def test_supplier_matching_does_not_repeat_for_every_historical_month(self):
        invoices = [self.invoice(f"2026-{month:02d}-15") for month in range(1, 11)]
        match = monitor._rule_matches_invoice
        with patch.object(monitor, "_rule_matches_invoice", wraps=match) as calls:
            monitor._cycle_for_report(monitor._rule_by_key("securepoint"), date(2026, 11, 4), invoices)
        self.assertLessEqual(calls.call_count, len(invoices) * 2)

    def test_required_and_excluded_product_tokens_are_preserved(self):
        rule = monitor._rule_by_key("pplus_dlp")
        dlp = {"supplier_name": "피플러스", "item_name": "GRADIUS DLP", "invoice_date": "2026-08-31"}
        cloudoc = {**dlp, "item_name": "Cloudoc 문서중앙화"}
        self.assertTrue(monitor._cycle_has_invoice(rule, date(2026, 8, 31), [dlp]))
        self.assertFalse(monitor._cycle_has_invoice(rule, date(2026, 8, 31), [cloudoc]))


class DispatchTests(RecoveryCase):
    def test_internal_report_and_each_vendor_are_sent_once(self):
        _, _, smtp = self.dispatch_fixtures()
        self.assertTrue(monitor.send_regular_due_report("2026-11-04")["sent"])
        self.assertEqual(monitor.send_regular_due_report("2026-11-04")["reason"], "already_sent")
        self.assertEqual(smtp.call_count, 3)
        state = monitor._load_state()
        self.assertEqual(len(state["sent"]), 1)
        self.assertEqual(len(state["vendor_alert_sent"]), 2)

    def test_failed_vendor_retries_without_resending_internal_or_successful_vendor(self):
        attempts = []
        def send(to, *args, **kwargs):
            attempts.append(to)
            if to == "jykim@securepoint.co.kr" and attempts.count(to) == 1:
                raise smtplib.SMTPRecipientsRefused({to: (450, b"temporary refusal")})
        self.dispatch_fixtures(side_effect=send)
        monitor.send_regular_due_report("2026-11-04")
        self.assertEqual(len(monitor._load_state()["vendor_alert_sent"]), 1)
        monitor.send_regular_due_report("2026-11-04")
        monitor.send_regular_due_report("2026-11-04")
        self.assertEqual(attempts.count("internal@example.com"), 1)
        self.assertEqual(attempts.count("jykim@securepoint.co.kr"), 2)
        self.assertEqual(attempts.count("sijun.park@ahnlab.com"), 1)
        self.assertEqual(len(monitor._load_state()["vendor_alert_sent"]), 2)

    def test_received_invoice_cancels_previously_failed_vendor_retry(self):
        def send(to, *args, **kwargs):
            if to == "jykim@securepoint.co.kr":
                raise smtplib.SMTPRecipientsRefused({to: (450, b"temporary refusal")})
        report, _, smtp = self.dispatch_fixtures(side_effect=send)
        monitor.send_regular_due_report("2026-11-04")
        report["items"][0].update(severity="ok", status="수신완료")
        count = smtp.call_count
        monitor.send_regular_due_report("2026-11-04")
        self.assertEqual(smtp.call_count, count)

    def test_internal_failure_retries_on_next_call(self):
        attempts = []
        def send(to, *args, **kwargs):
            attempts.append(to)
            if len(attempts) == 1:
                raise smtplib.SMTPConnectError(421, b"unavailable")
        self.dispatch_fixtures(missing=False, side_effect=send)
        self.assertIn("error", monitor.send_regular_due_report("2026-11-04"))
        self.assertFalse(monitor._load_state().get("sent"))
        self.assertTrue(monitor.send_regular_due_report("2026-11-04")["sent"])
        self.assertEqual(len(attempts), 2)

    def test_internal_success_is_persisted_before_vendor_dispatch(self):
        def send(to, *args, **kwargs):
            if to != "internal@example.com":
                self.assertTrue(monitor._load_state()["sent"])
        self.dispatch_fixtures(side_effect=send)
        monitor.send_regular_due_report("2026-11-04")

    def test_existing_legacy_daily_key_deduplicates_changed_report_items(self):
        monitor._save_state({"sent": {"2026-11-04:old-items": "2026-11-04T12:00:00"}})
        _, _, smtp = self.dispatch_fixtures(missing=False)
        self.assertEqual(monitor.send_regular_due_report("2026-11-04")["reason"], "already_sent")
        smtp.assert_not_called()

    def test_explicit_force_keeps_existing_resend_behavior(self):
        _, _, smtp = self.dispatch_fixtures(missing=False)
        monitor.send_regular_due_report("2026-11-04")
        self.assertTrue(monitor.send_regular_due_report("2026-11-04", force=True)["sent"])
        self.assertEqual(smtp.call_count, 2)

    def test_corrupt_ledger_stops_before_sending(self):
        monitor._state_path().write_text("{corrupt", encoding="utf-8")
        _, build, smtp = self.dispatch_fixtures()
        with self.assertRaises(ValueError):
            monitor.send_regular_due_report("2026-11-04")
        build.assert_not_called()
        smtp.assert_not_called()

    def test_invalid_success_ledger_shape_stops_before_sending(self):
        monitor._state_path().write_text('{"sent": []}', encoding="utf-8")
        _, _, smtp = self.dispatch_fixtures()
        with self.assertRaises(ValueError):
            monitor.send_regular_due_report("2026-11-04")
        smtp.assert_not_called()

    def test_unwritable_state_stops_before_smtp(self):
        _, _, smtp = self.dispatch_fixtures()
        with patch.object(monitor, "_save_state", side_effect=PermissionError("blocked")):
            with self.assertRaises(PermissionError):
                monitor.send_regular_due_report("2026-11-04")
        smtp.assert_not_called()

    def test_concurrent_callers_share_one_daily_send(self):
        def delayed_send(*args, **kwargs):
            time.sleep(0.03)
        _, _, smtp = self.dispatch_fixtures(missing=False, side_effect=delayed_send)
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: monitor.send_regular_due_report("2026-11-04"), range(5)))
        self.assertEqual(sum(bool(result["sent"]) for result in results), 1)
        smtp.assert_called_once()

    def test_another_dispatch_file_lock_skips_without_sending(self):
        _, build, smtp = self.dispatch_fixtures()
        path = self.root / "regular_due_dispatch.lock"
        path.write_bytes(b"0")
        with path.open("r+b") as handle:
            monitor._lock_file_handle(handle)
            try:
                result = monitor.send_regular_due_report("2026-11-04")
            finally:
                monitor._unlock_file_handle(handle)
        self.assertEqual(result["reason"], "dispatch_busy")
        build.assert_not_called()
        smtp.assert_not_called()

    def test_disabled_or_before_start_does_not_send(self):
        _, _, smtp = self.dispatch_fixtures()
        with patch.dict(os.environ, {"REGULAR_DUE_ALERT_ENABLED": "0"}):
            self.assertEqual(monitor.send_regular_due_report("2026-11-04")["reason"], "disabled")
        with patch.dict(os.environ, {"REGULAR_DUE_ALERT_START_DATE": "2026-12-01"}):
            self.assertEqual(monitor.send_regular_due_report("2026-11-04")["reason"], "before_start_date")
        smtp.assert_not_called()


class SMTPReceiptTests(RecoveryCase):
    def transport(self, *, refused=None, close_error=None):
        smtp = MagicMock()
        smtp.has_extn.return_value = False
        smtp.send_message.return_value = refused or {}
        context = MagicMock()
        context.__enter__.return_value = smtp
        context.__exit__.return_value = False
        if close_error:
            context.__exit__.side_effect = close_error
        patcher = patch.object(monitor.smtplib, "SMTP", return_value=context)
        patcher.start()
        self.addCleanup(patcher.stop)
        return smtp

    def test_primary_refused_is_not_success_even_when_cc_was_accepted(self):
        self.transport(refused={"vendor@example.com": (450, b"try later")})
        with self.assertRaises(smtplib.SMTPRecipientsRefused):
            monitor._send_html_mail("vendor@example.com", "test", "test", "test", cc_addr="internal@example.com")

    def test_cc_refused_does_not_resend_accepted_vendor_mail(self):
        smtp = self.transport(refused={"internal@example.com": (450, b"try later")})
        monitor._send_html_mail("vendor@example.com", "test", "test", "test", cc_addr="internal@example.com")
        smtp.send_message.assert_called_once()

    def test_quit_failure_after_data_acceptance_is_not_a_send_failure(self):
        smtp = self.transport(close_error=smtplib.SMTPServerDisconnected("closed after DATA"))
        monitor._send_html_mail("internal@example.com", "test", "test", "test")
        smtp.send_message.assert_called_once()

    def test_data_failure_still_propagates(self):
        smtp = self.transport()
        smtp.send_message.side_effect = smtplib.SMTPDataError(451, b"temporarily unavailable")
        with self.assertRaises(smtplib.SMTPDataError):
            monitor._send_html_mail("internal@example.com", "test", "test", "test")


if __name__ == "__main__":
    unittest.main()
