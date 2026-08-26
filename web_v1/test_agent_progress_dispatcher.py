from __future__ import annotations

import threading
import time
import unittest
from unittest import mock

from web_v1.agent.erp_agent import _ProgressEventDispatcher


class ProgressEventDispatcherTests(unittest.TestCase):
    def test_submit_does_not_wait_for_slow_http(self) -> None:
        entered = threading.Event()

        def slow_post(*args, **kwargs):
            entered.set()
            time.sleep(0.25)
            return object()

        with mock.patch("web_v1.agent.erp_agent._post", side_effect=slow_post):
            dispatcher = _ProgressEventDispatcher(
                "https://server", "job-1", "agent-1", False, request_timeout=1
            )
            started = time.perf_counter()
            dispatcher.submit({"status": "erp", "message": "step"})
            elapsed = time.perf_counter() - started
            self.assertLess(elapsed, 0.05)
            self.assertTrue(entered.wait(0.5))
            dispatcher.close(timeout=1.0)

    def test_http_failure_isolated_from_submitter(self) -> None:
        attempted = threading.Event()

        def failed_post(*args, **kwargs):
            attempted.set()
            raise TimeoutError("slow log endpoint")

        with mock.patch("web_v1.agent.erp_agent._post", side_effect=failed_post):
            dispatcher = _ProgressEventDispatcher(
                "https://server", "job-2", "agent-2", False, request_timeout=1
            )
            dispatcher.submit({"status": "erp", "message": "step"})
            self.assertTrue(attempted.wait(0.5))
            dispatcher.close(timeout=1.0)

    def test_close_rejects_late_progress(self) -> None:
        calls: list[dict] = []

        def recorded_post(server, path, payload, **kwargs):
            calls.append(dict(payload))
            return object()

        with mock.patch("web_v1.agent.erp_agent._post", side_effect=recorded_post):
            dispatcher = _ProgressEventDispatcher("https://server", "job-3", "agent-3", False)
            dispatcher.close(timeout=1.0)
            dispatcher.submit({"status": "erp", "message": "late"})
            time.sleep(0.05)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
