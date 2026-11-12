from __future__ import annotations

import ast
import datetime
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from web_v1.backend.purchase_analysis import _extract_date


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "manager_server" / "전표 자동화 프로그램(담당자용)_v6.2.py"


class PurchaseDateRegressionTests(unittest.TestCase):
    def test_all_calendar_days_keep_complete_compact_filename(self):
        day = datetime.date(2026, 1, 1)
        while day.year == 2026:
            with self.subTest(day=day):
                self.assertEqual(_extract_date("", f"{day:%Y%m%d}_컴퓨존.pdf"), day.isoformat())
            day += datetime.timedelta(days=1)

    def test_original_292_layout_and_filename(self):
        body = "작성일자\n169,545\n세액\n2026/11/10\n2026111041000115g81davyo"
        self.assertEqual(_extract_date(body, "20261110_컴퓨존_186500원.pdf"), "2026-11-10")
        self.assertEqual(_extract_date(body, "tax.pdf"), "2026-11-10")

    def test_labeled_dates_and_valid_leap_day(self):
        for value in ("20261110", "2026/11/10", "2026-11-10", "2026 11 10", "2026년 11월 10일"):
            with self.subTest(value=value):
                self.assertEqual(_extract_date("작성일자 " + value), "2026-11-10")
        self.assertEqual(_extract_date("작성일자 2024/02/29"), "2024-02-29")

    def test_invalid_dates_and_identifier_substrings_are_rejected(self):
        for value in ("20261100", "20260229", "20260431", "20261311", "2026/11/31", "2026/11/111", "2026111041000115g81davyo"):
            with self.subTest(value=value):
                self.assertEqual(_extract_date("", value + ".pdf"), "")
                self.assertEqual(_extract_date("작성일자 " + value), "")

    def test_precedence_legal_date_and_approval_fallback(self):
        self.assertEqual(_extract_date("작성일자 2026/11/10", "20261111_tax.pdf"), "2026-11-11")
        self.assertEqual(_extract_date("법령 2002-02-06\n작성일자 2026/11/10"), "2026-11-10")
        self.assertEqual(_extract_date("법령 2002-02-06"), "")
        self.assertEqual(_extract_date("승인번호 2026111041000115g81davyo"), "2026-11-10")
        self.assertEqual(_extract_date("승인번호 2026023041000115g81davyo"), "")


def element(text, *, pid=243, handle=2, visible=True):
    return SimpleNamespace(
        window_text=lambda: text, is_visible=lambda: visible,
        element_info=SimpleNamespace(process_id=pid), handle=handle,
        descendants=lambda **kw: [],
    )


class SaveRejectionRegressionTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(LEGACY.read_text(encoding="utf-8-sig"))
        names = {"_dialog_text_blob", "_raise_erp_save_rejection", "_save_and_open_print_dialog", "_wait_rd_viewer_ready"}
        nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
        self.assertEqual(len(nodes), len(names))
        self.main = element("ERP", handle=1)
        self.main.descendants = Mock(return_value=[])
        self.desktop = Mock()
        self.desktop.windows.return_value = []
        self.gui = Mock()
        self.clock = Mock()
        self.clock.time.side_effect = range(100)
        self.ns = {
            "main_win": self.main, "Desktop": Mock(return_value=self.desktop),
            "pyautogui": self.gui, "time": self.clock, "os": os, "re": re,
            "psutil": Mock(), "self": SimpleNamespace(logger=Mock()),
            "ERP_CLICK_WAIT": 0, "ERP_SETTLE_WAIT": 0, "ERP_PRINT_SAVE_WAIT": 0,
            "ERP_PRINT_VIEWER_WAIT": 0, "ERP_BLOCK_WAIT": 0,
            "_click_print_button": Mock(), "_ask_print_target": Mock(return_value={"kind": "pdf_merge"}),
            "_select_printer_in_dialog": Mock(return_value=True), "_close_rd_viewer": Mock(),
        }
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(LEGACY), "exec"), self.ns)

    def test_rejected_save_stops_before_enter_and_print_keeps_retry_guard(self):
        self.main.descendants.return_value = [element("해당 회계일은 마감되었습니다.")]
        with self.assertRaisesRegex(RuntimeError, r"ERP_SAVE_CONFIRM_REQUIRED.*마감되었습니다"):
            self.ns["_save_and_open_print_dialog"]()
        self.gui.press.assert_not_called()
        self.ns["_click_print_button"].assert_not_called()
        self.gui.hotkey.assert_called_once_with("ctrl", "s")

    def test_save_first_popup_is_not_reported_as_viewer_timeout(self):
        self.desktop.windows.return_value = [element("저장 후 출력해 주십시오.")]
        with self.assertRaisesRegex(RuntimeError, "ERP 저장/출력 거부: 저장 후 출력"):
            self.ns["_wait_rd_viewer_ready"]()

    def test_hidden_and_other_process_errors_do_not_block(self):
        self.main.descendants.return_value = [element("회계일 마감", visible=False)]
        self.desktop.windows.return_value = [element("저장 후 출력해 주십시오.", pid=999), element("회계일 마감", visible=False)]
        self.ns["_raise_erp_save_rejection"]()

    def test_normal_success_keeps_existing_save_print_flow(self):
        self.main.descendants.return_value = [element("저장되었습니다.")]
        self.ns["_wait_rd_viewer_ready"] = Mock(return_value=True)
        self.assertTrue(self.ns["_save_and_open_print_dialog"]())
        self.ns["_click_print_button"].assert_called_once()
        self.ns["_select_printer_in_dialog"].assert_called_once()
        self.ns["_close_rd_viewer"].assert_called_once()

    def test_error_after_first_print_does_not_retry_or_select_printer(self):
        self.ns["_wait_rd_viewer_ready"] = Mock(side_effect=RuntimeError("ERP 저장/출력 거부: 저장 후 출력해 주십시오."))
        with self.assertRaisesRegex(RuntimeError, "ERP_SAVE_CONFIRM_REQUIRED"):
            self.ns["_save_and_open_print_dialog"]()
        self.ns["_click_print_button"].assert_called_once()
        self.ns["_select_printer_in_dialog"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
