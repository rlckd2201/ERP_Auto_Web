from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from web_v1.backend import regular_due_monitor


class RegularDueSenderGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        regular_due_monitor._scheduler_started = False
        regular_due_monitor._release_scheduler_process_lock()

    def tearDown(self) -> None:
        regular_due_monitor._scheduler_started = False
        regular_due_monitor._release_scheduler_process_lock()

    def test_alert_is_disabled_unless_explicitly_enabled(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REGULAR_DUE_ALERT_ENABLED", None)
            self.assertFalse(regular_due_monitor._enabled())

    def test_alert_is_blocked_on_noncanonical_host(self) -> None:
        with patch.dict(os.environ, {"REGULAR_DUE_ALERT_ENABLED": "1", "REGULAR_DUE_SENDER_HOST": "SERVER-121"}, clear=False):
            with patch.object(regular_due_monitor.socket, "gethostname", return_value="STALE-PC"):
                self.assertFalse(regular_due_monitor._enabled())

    def test_alert_is_enabled_on_canonical_host(self) -> None:
        with patch.dict(os.environ, {"REGULAR_DUE_ALERT_ENABLED": "1", "REGULAR_DUE_SENDER_HOST": "SERVER-121"}, clear=False):
            with patch.object(regular_due_monitor.socket, "gethostname", return_value="server-121"):
                self.assertTrue(regular_due_monitor._enabled())

    def test_scheduler_does_not_start_when_process_lock_is_held(self) -> None:
        with (
            patch.object(regular_due_monitor, "_enabled", return_value=True),
            patch.object(regular_due_monitor, "_acquire_scheduler_process_lock", return_value=False),
            patch.object(regular_due_monitor.threading, "Thread") as thread_class,
        ):
            regular_due_monitor.start_regular_due_scheduler()
        self.assertFalse(regular_due_monitor._scheduler_started)
        thread_class.assert_not_called()

    def test_scheduler_starts_after_process_lock_is_acquired(self) -> None:
        thread = MagicMock()
        with (
            patch.object(regular_due_monitor, "_enabled", return_value=True),
            patch.object(regular_due_monitor, "_acquire_scheduler_process_lock", return_value=True),
            patch.object(regular_due_monitor.threading, "Thread", return_value=thread),
        ):
            regular_due_monitor.start_regular_due_scheduler()
        self.assertTrue(regular_due_monitor._scheduler_started)
        thread.start.assert_called_once_with()

    def test_mail_headers_include_sender_host_and_pid(self) -> None:
        smtp = MagicMock()
        smtp.has_extn.return_value = False
        smtp_context = MagicMock()
        smtp_context.__enter__.return_value = smtp
        with (
            patch.object(regular_due_monitor.smtplib, "SMTP", return_value=smtp_context),
            patch.object(regular_due_monitor.socket, "gethostname", return_value="SERVER-121"),
            patch.object(regular_due_monitor.os, "getpid", return_value=4242),
        ):
            regular_due_monitor._send_html_mail("recipient@example.com", "subject", "plain", "<p>html</p>")
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["X-Accounting-Sender-Host"], "SERVER-121")
        self.assertEqual(message["X-Accounting-Sender-Pid"], "4242")


if __name__ == "__main__":
    unittest.main()
