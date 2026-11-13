"""Offline mail identity/collector regressions; no IMAP, invoices or ERP writes."""
import copy
import email
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from email.message import EmailMessage
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from web_v1.backend import mail_collector as collector
from web_v1.backend.mail_content import MailCollectionBusy, MailContentStore, content_fingerprint


def make_mail(message_id="first", *, body="Amount 186,500; https://invoice.example/123",
              attachment=b"invoice-123", filename="invoice.pdf", cte="base64"):
    msg = EmailMessage()
    msg["From"] = "Billing <billing@example.com>"
    msg["To"] = "accounts@example.net"
    msg["Subject"] = "Tax invoice"
    msg["Date"] = "Thu, 12 Nov 2026 15:00:00 +0900"
    msg["Message-ID"] = f"<{message_id}@example.com>"
    msg.set_content(body, cte=cte)
    if attachment is not None:
        msg.add_attachment(attachment, maintype="application", subtype="pdf", filename=filename)
    return msg


def fp(msg):
    return content_fingerprint(email.message_from_bytes(msg.as_bytes()))


class ContentIdentityTests(unittest.TestCase):
    def test_relay_id_boundaries_encoding_and_filename_are_not_content(self):
        a = make_mail()
        b = make_mail("relay-second", filename="invoice_1.pdf", cte="quoted-printable")
        b["Received"] = "from another relay"
        b["X-Spam-Status"] = "No"
        a.set_boundary("first-boundary")
        b.set_boundary("second-boundary")
        self.assertTrue(fp(a))
        self.assertEqual(fp(a), fp(b))
        self.assertNotEqual(a.as_bytes(), b.as_bytes())

    def test_distinct_business_content_is_never_merged_by_price_or_subject(self):
        base = make_mail()
        variants = [make_mail(body="Amount 186,500; https://invoice.example/124"),
                    make_mail(body="Amount 186,501; https://invoice.example/123"),
                    make_mail(attachment=b"invoice-124")]
        for header, value in [("Date", "Fri, 13 Nov 2026 15:00:00 +0900"),
                              ("From", "other@example.com"), ("To", "other@example.net"),
                              ("Subject", "Corrected tax invoice")]:
            other = copy.deepcopy(base)
            other.replace_header(header, value)
            variants.append(other)
        for other in variants:
            with self.subTest(other=other.get("Subject")):
                self.assertTrue(fp(other))
                self.assertNotEqual(fp(base), fp(other))

    def test_encoded_display_name_is_not_parsed_as_address_syntax(self):
        raw = make_mail().as_bytes().replace(
            b"From: Billing <billing@example.com>",
            b"From: =?utf-8?b?W0xHIFUrXQ==?= <billing@example.com>")
        self.assertEqual(content_fingerprint(email.message_from_bytes(raw)), fp(make_mail()))

    def test_attachment_count_and_inline_content_id_are_preserved(self):
        base = make_mail()
        duplicate = copy.deepcopy(base)
        duplicate.add_attachment(b"invoice-123", maintype="application", subtype="pdf", filename="copy.pdf")
        self.assertNotEqual(fp(base), fp(duplicate))
        changed = copy.deepcopy(base)
        changed.get_payload()[1]["Content-ID"] = "<another>"
        self.assertNotEqual(fp(base), fp(changed))

    def test_attachment_order_is_irrelevant_but_body_whitespace_is_not(self):
        a = make_mail()
        a.add_attachment(b"second", maintype="application", subtype="pdf", filename="second.pdf")
        b = copy.deepcopy(a)
        b.set_payload([b.get_payload()[0], b.get_payload()[2], b.get_payload()[1]])
        self.assertEqual(fp(a), fp(b))
        self.assertNotEqual(fp(make_mail(body="a b")), fp(make_mail(body="a  b")))

    def test_original_date_timezone_representation_can_change(self):
        a, b = make_mail(), make_mail()
        b.replace_header("Date", "Thu, 12 Nov 2026 06:00:00 +0000")
        self.assertEqual(fp(a), fp(b))

    def test_uncertain_headers_or_mime_leave_normal_collection_available(self):
        for header in ("From", "Date"):
            msg = make_mail()
            del msg[header]
            self.assertEqual(fp(msg), "")
        raw = (b"From: a@example.com\nTo: b@example.com\nDate: Thu, 12 Nov 2026 06:00:00 +0000\n"
               b"Content-Type: text/plain; charset=utf-8\n\n\xff\xfe")
        self.assertEqual(content_fingerprint(email.message_from_bytes(raw)), "")
        broken = raw.split(b"Content-Type:")[0] + b"Content-Type: multipart/mixed; boundary=missing\n\nabc"
        self.assertEqual(content_fingerprint(email.message_from_bytes(broken)), "")

    def test_embedded_mail_headers_are_preserved(self):
        a, b = make_mail(), make_mail()
        a.add_attachment(make_mail("nested-first"))
        b.add_attachment(make_mail("nested-second"))
        self.assertNotEqual(fp(a), fp(b))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "content.sqlite3"

    def test_only_complete_success_is_durable_and_scoped(self):
        with MailContentStore(self.path, "mailbox-a") as store:
            for reason in ("failed", "ignored", "processed", "no supported tax invoice target"):
                store.remember(reason, "first", reason)
                self.assertIsNone(store.find(reason))
            store.remember("saved-content", "first", "saved")
            store.remember("duplicate-content", "existing-invoice", "duplicate")
        with MailContentStore(self.path, "mailbox-a") as store:
            self.assertEqual(store.find("saved-content")["first_message_key"], "first")
            self.assertIsNotNone(store.find("duplicate-content"))
        with MailContentStore(self.path, "mailbox-b") as store:
            self.assertIsNone(store.find("saved-content"))

    def test_duplicate_keeps_original_receipt_and_records_count(self):
        with MailContentStore(self.path, "mailbox") as store:
            store.remember("content", "first", "saved")
            store.note_duplicate("content")
            store.remember("content", "second", "duplicate")
            row = store.connection.execute("select * from collected_content").fetchone()
            self.assertEqual(row["first_message_key"], "first")
            self.assertEqual(row["duplicate_count"], 1)

    def test_overlapping_process_is_rejected_and_crash_releases_lock(self):
        code = ("import os,sys; from pathlib import Path; "
                "from web_v1.backend.mail_content import MailContentStore; "
                "s=MailContentStore(Path(sys.argv[1]),'box'); s.__enter__(); "
                "s.remember('first','message','saved'); os._exit(0)")
        completed = subprocess.run([sys.executable, "-B", "-c", code, str(self.path)],
                                   capture_output=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))
        with MailContentStore(self.path, "box") as store:
            self.assertIsNotNone(store.find("first"))
            blocked = subprocess.run([sys.executable, "-B", "-c", code, str(self.path)],
                                     capture_output=True, timeout=15)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn(b"MailCollectionBusy", blocked.stderr)
            with self.assertRaises(MailCollectionBusy):
                with MailContentStore(self.path, "box"):
                    self.fail("overlap acquired lock")


class FakeImap:
    def __init__(self, messages):
        self.messages = messages
        self.flags = []
        self.fetch_count = 0
        self.login = Mock()
        self.select = Mock()
        self.logout = Mock()

    def uid(self, operation, *args):
        if operation == "search":
            ids = [str(i).encode() for i in range(1, len(self.messages) + 1)]
            return "OK", [b" ".join(ids)]
        if operation == "fetch":
            assert args[1] == "(BODY.PEEK[])"
            self.fetch_count += 1
            return "OK", [(b"RFC822", self.messages[int(args[0]) - 1])]
        if operation == "store":
            self.flags.append((int(args[0]), args[1]))
            return "OK", []
        raise AssertionError(operation)


class CollectorHarness:
    """Real collector/state/identity; all network/document/business effects mocked."""
    def __init__(self, root, messages, invoice_type="regular"):
        self.root = Path(root)
        self.mail = FakeImap(messages)
        self.imap = Mock(return_value=self.mail)
        self.api = {"decode_mime_header": lambda value: str(value),
                    "parse_mail_date": lambda msg: "261112",
                    "extract_links_from_mail": Mock(return_value=["https://invoice.example/123"]),
                    "extract_hometax_attachment": Mock(return_value=None),
                    "extract_kt_attachments": Mock(return_value=[]),
                    "extract_xml_attachments": Mock(return_value=[])}
        self.crawl = Mock(return_value={"ok": True, "invoice_type": invoice_type,
                                        "pdf_path": str(self.root / "test.pdf")})
        self.insert = Mock(return_value=True)
        self.quote = Mock(return_value={"ok": True, "skipped": True})
        self.get_invoice = Mock(return_value={"id": 1})
        self.zoom = Mock(return_value=False)
        self.extract_zoom = Mock(return_value={"pdf_path": "zoom-test.pdf"})
        self.events = []
        self.settings = SimpleNamespace(email_id="accounts@example.net", email_pw="test-only",
                                        imap_server="test.invalid", erp_db_dir=self.root,
                                        download_dir=self.root / "downloads")

    @property
    def state_path(self):
        return self.root / "purchase_mail_collect_state.json"

    def collect(self, *, force=False):
        with ExitStack() as stack:
            for name, value in {"settings": self.settings, "_crawler_api": lambda: self.api,
                                "_crawl_invoice_with_retry": self.crawl,
                                "insert_crawler_invoice": self.insert,
                                "get_invoice_by_pdf_path": self.get_invoice,
                                "auto_attach_compuzone_quote": self.quote,
                                "is_zoom_billing_mail": self.zoom,
                                "extract_zoom_billing_invoice": self.extract_zoom}.items():
                stack.enter_context(patch.object(collector, name, value))
            stack.enter_context(patch.object(collector.imaplib, "IMAP4_SSL", self.imap))
            return collector.collect_mail_once(lambda *event: self.events.append(event), force_recent_scan=force)


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def harness(self, messages=None, kind="regular"):
        messages = messages or [make_mail(), make_mail("relay-copy")]
        return CollectorHarness(self.root, [m.as_bytes() for m in messages], kind)

    def test_regular_duplicate_skips_attachment_write_crawl_and_invoice_insert(self):
        h = self.harness()
        result = h.collect()
        self.assertEqual((result["saved_count"], result["content_duplicate_count"]), (1, 1))
        h.crawl.assert_called_once()
        h.insert.assert_called_once()
        h.api["extract_kt_attachments"].assert_called_once()
        self.assertEqual(h.mail.flags, [(1, "+FLAGS"), (2, "+FLAGS")])
        state = json.loads(h.state_path.read_text(encoding="utf8"))
        self.assertEqual(state["processed"]["message-id:<relay-copy@example.com>"]["duplicate_source"],
                         "message-id:<first@example.com>")

    def test_purchase_uses_same_early_check_before_quote_and_analysis(self):
        h = self.harness(kind="purchase")
        result = h.collect()
        self.assertEqual(result["saved_invoice_ids"], [1])
        self.assertEqual(result["content_duplicate_count"], 1)
        h.quote.assert_called_once()
        h.insert.assert_called_once()

    def test_changed_content_with_same_message_id_is_collected(self):
        h = self.harness([make_mail(), make_mail(body="Different approval 124, same price 186,500")])
        self.assertEqual(h.collect()["saved_count"], 2)
        self.assertEqual(h.insert.call_count, 2)

    def test_failed_attempt_does_not_block_relay_copy(self):
        h = self.harness()
        h.crawl.side_effect = [{"ok": False, "error": "download interrupted"}, h.crawl.return_value]
        result = h.collect()
        self.assertEqual((result["failed_count"], result["saved_count"], result["content_duplicate_count"]), (1, 1, 0))
        self.assertEqual(h.mail.flags, [(1, "-FLAGS"), (2, "+FLAGS")])

    def test_partial_success_retains_retry_for_all_targets(self):
        h = self.harness([make_mail()])
        h.api["extract_links_from_mail"].return_value = ["https://invoice.example/1", "https://invoice.example/2"]
        h.crawl.side_effect = [h.crawl.return_value, {"ok": False, "error": "not ready"}]
        first = h.collect()
        self.assertEqual((first["saved_count"], first["failed_count"]), (1, 1))
        h.crawl.side_effect = None
        h.insert.side_effect = [False, True]
        second = h.collect(force=True)
        self.assertEqual((second["content_duplicate_count"], second["saved_count"]), (0, 1))
        third = h.collect(force=True)
        self.assertEqual(third["content_duplicate_count"], 1)
        self.assertEqual(h.crawl.call_count, 4)

    def test_restart_and_expired_message_id_history_keep_success_receipt(self):
        h = self.harness([make_mail()])
        h.collect()
        h.state_path.write_text("{}", encoding="utf8")
        later = self.harness([make_mail("relay-after-restart")])
        self.assertEqual(later.collect()["content_duplicate_count"], 1)
        later.crawl.assert_not_called()

    def test_known_successful_message_id_seeds_content_without_recrawling(self):
        h = self.harness()
        state = {}
        collector._remember_processed(state, "message-id:<first@example.com>", "Tax invoice", "saved")
        h.state_path.write_text(json.dumps(state), encoding="utf8")
        result = h.collect()
        self.assertEqual((result["duplicate_count"], result["content_duplicate_count"]), (2, 1))
        h.crawl.assert_not_called()

    def test_invoice_identity_duplicate_also_creates_success_receipt(self):
        h = self.harness()
        h.insert.return_value = False
        result = h.collect()
        self.assertEqual((result["duplicate_count"], result["content_duplicate_count"]), (2, 1))
        h.crawl.assert_called_once()

    def test_unsupported_mail_does_not_mark_content_success(self):
        h = self.harness()
        h.api["extract_links_from_mail"].return_value = []
        self.assertEqual(h.collect()["content_duplicate_count"], 0)
        self.assertEqual(h.api["extract_kt_attachments"].call_count, 2)
        h.insert.assert_not_called()

    def test_ignored_target_alongside_success_does_not_certify_entire_mail(self):
        h = self.harness()
        h.api["extract_links_from_mail"].return_value = ["https://invoice.example/ignore", "https://invoice.example/save"]
        with patch.object(collector, "_skip_auto_collect_target", side_effect=lambda s, b, n, t: "excluded" if t.endswith("ignore") else ""):
            result = h.collect()
        self.assertEqual(result["content_duplicate_count"], 0)
        self.assertEqual(h.crawl.call_count, 2)

    def test_uncertain_fingerprint_preserves_normal_collection(self):
        messages = [make_mail(), make_mail("second")]
        for msg in messages:
            del msg["Date"]
        h = self.harness(messages)
        self.assertEqual(h.collect()["saved_count"], 2)

    def test_zoom_success_and_failure_follow_same_receipt_rules(self):
        h = self.harness()
        h.zoom.return_value = True
        h.extract_zoom.side_effect = [RuntimeError("PDF extraction failed"), h.extract_zoom.return_value]
        result = h.collect()
        self.assertEqual((result["failed_count"], result["saved_count"]), (1, 1))
        h.extract_zoom.side_effect = None
        result = h.collect(force=True)
        self.assertEqual(result["content_duplicate_count"], 2)
        self.assertEqual(h.extract_zoom.call_count, 2)

    def test_concurrent_collection_stops_before_imap_or_business_effects(self):
        h = self.harness()
        with MailContentStore(self.root / "mail_content_state.sqlite3", "other"):
            with self.assertRaises(MailCollectionBusy):
                h.collect()
        h.imap.assert_not_called()
        h.insert.assert_not_called()


if __name__ == "__main__":
    unittest.main()
