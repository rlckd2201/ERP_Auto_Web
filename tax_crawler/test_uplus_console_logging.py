import io
import sys
from unittest import TestCase, mock

from tax_crawler.base_handler import BaseTaxInvoiceHandler
from support.uplus_handler import UplusEDocuHandler


class UplusConsoleLoggingTests(TestCase):
    def test_legacy_console_encoding_cannot_abort_processing_log(self):
        raw = io.BytesIO()
        console = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
        handler = UplusEDocuHandler.__new__(UplusEDocuHandler)

        with mock.patch.object(sys, "stdout", console):
            handler.log("[분석] 법인 특정 완료: 대승 🚨")
            console.flush()

        output = raw.getvalue().decode("cp1252")
        self.assertIn("[202", output)
        self.assertIn("\\u", output)

    def test_base_crawler_console_is_safe_under_legacy_windows_encoding(self):
        raw = io.BytesIO()
        console = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")

        with mock.patch.object(sys, "stdout", console):
            BaseTaxInvoiceHandler._configure_unicode_safe_console()
            print("대신아이씨티 세금계산서")
            console.flush()

        self.assertEqual("backslashreplace", console.errors)
        output = raw.getvalue().decode("cp1252")
        self.assertIn("\\u", output)
