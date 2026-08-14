import io
import sys
from unittest import TestCase, mock

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
