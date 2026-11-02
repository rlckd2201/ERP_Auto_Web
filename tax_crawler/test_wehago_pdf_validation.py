from pathlib import Path
import os
import time
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, call, patch

from portal_wehago import WehagoHandler


NATIVE_TEXT = """
전자세금계산서 (공급받는자 보관용)
승인번호 20260810-41000096-48917566
관리번호 TX2026083821631
작성일자 공급가액 세액
"""


class WehagoPdfValidationTests(TestCase):
    def test_default_export_requires_one_exact_native_management_id(self):
        cases = [
            ("Developer Express Inc.", NATIVE_TEXT, "TX2026083821631"),
            ("Skia/PDF", NATIVE_TEXT, ""),
            ("Developer Express Inc.", NATIVE_TEXT + "\n관리번호 TXOTHER123", ""),
            ("Developer Express Inc.", NATIVE_TEXT.replace("관리번호 TX2026083821631", "관리번호 없음"), ""),
        ]
        for producer, text, expected in cases:
            with self.subTest(producer=producer, text=text):
                pdf = Mock(metadata={"Producer": producer}, pages=[Mock()])
                pdf.pages[0].extract_text.return_value = text
                opener = Mock()
                opener.return_value.__enter__ = Mock(return_value=pdf)
                opener.return_value.__exit__ = Mock(return_value=False)
                with patch("pdfplumber.open", opener):
                    self.assertEqual(expected, WehagoHandler._native_pdf_document_id(Path("fixture.pdf")))

    def test_recovers_default_export_by_id_and_preserves_original(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        handler._is_stable = Mock(return_value=True)
        handler._native_pdf_document_id = Mock(return_value="TX2026083821631")
        handler._write_saveas_debug = Mock()
        with TemporaryDirectory() as tmp, patch("portal_wehago.Path.home", return_value=Path(tmp)):
            source = Path(tmp) / "Documents" / "TX2A_92.pdf"
            source.parent.mkdir()
            source.write_bytes(b"verified native invoice")
            final = Path(tmp) / "downloads" / "invoice__WEHAGO_TX2026083821631.pdf"
            self.assertEqual(final, handler._recover_misplaced_pdf(final, time.time()))
            self.assertEqual(source.read_bytes(), final.read_bytes())

    def test_default_export_rejects_wrong_id_stale_unstable_and_existing_target(self):
        for scenario in ("wrong", "longer_id", "stale", "unstable", "existing", "unknown_id"):
            with self.subTest(scenario=scenario), TemporaryDirectory() as tmp, patch(
                "portal_wehago.Path.home", return_value=Path(tmp)
            ):
                handler = WehagoHandler.__new__(WehagoHandler)
                handler._is_stable = Mock(return_value=scenario != "unstable")
                actual_id = {"wrong": "TXOTHER123", "longer_id": "TX20260838216310"}.get(scenario, "TX2026083821631")
                handler._native_pdf_document_id = Mock(return_value=actual_id)
                source = Path(tmp) / "Documents" / "TX2A_92.pdf"
                source.parent.mkdir()
                source.write_bytes(b"vendor output")
                started = time.time()
                if scenario == "stale":
                    os.utime(source, (started - 60, started - 60))
                final = Path(tmp) / "invoice__WEHAGO_TX2026083821631.pdf"
                if scenario == "unknown_id":
                    final = Path(tmp) / "invoice__WEHAGO_URLHASH.pdf"
                if scenario == "existing":
                    final.write_bytes(b"keep existing")
                self.assertIsNone(handler._recover_default_native_pdf(final, started))
                self.assertEqual(b"vendor output", source.read_bytes())
                if scenario == "existing":
                    self.assertEqual(b"keep existing", final.read_bytes())
                else:
                    self.assertFalse(final.exists())

    def test_accepts_native_developer_express_invoice(self):
        valid, reason = WehagoHandler._assess_native_wehago_pdf(
            {"Producer": "Developer Express Inc. DXperience (tm) v15.1.7"},
            NATIVE_TEXT,
        )
        self.assertTrue(valid, reason)

    def test_rejects_chrome_skia_web_page(self):
        valid, reason = WehagoHandler._assess_native_wehago_pdf(
            {
                "Producer": "Skia/PDF m151",
                "Creator": "Mozilla/5.0 Chrome/151.0.0.0 Safari/537.36",
            },
            NATIVE_TEXT + " 상태확인 국세청전송일자 신고상태 전송성공 [확인]버튼",
        )
        self.assertFalse(valid)
        self.assertIn("Chrome 웹 화면 PDF", reason)

    def test_browser_pdf_export_is_disabled(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        driver = Mock()
        result = handler._export_browser_pdf(driver, Path("ignored.pdf"))
        self.assertIsNone(result)
        driver.execute_cdp_cmd.assert_not_called()
        self.assertIn("비활성화", handler._last_browser_pdf_error)

    def test_native_retry_fails_without_browser_fallback(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        handler._close_all_print_dialogs = Mock()
        handler._terminate_stale_duzon_print_helpers = Mock()
        handler._ensure_wehago_print_runtime = Mock(
            return_value={"state": "runtime-running", "detail": "runtime ready"}
        )
        handler._click_print = Mock(return_value=False)
        handler._export_pdf_from_print_dialog = Mock()

        with TemporaryDirectory() as temp_dir:
            result, detail = handler._export_native_pdf_with_retry(
                driver=Mock(),
                final_path=Path(temp_dir) / "invoice.pdf",
                attempts=2,
            )

        self.assertIsNone(result)
        self.assertEqual(2, handler._click_print.call_count)
        handler._export_pdf_from_print_dialog.assert_not_called()
        handler._terminate_stale_duzon_print_helpers.assert_not_called()
        self.assertIn("Chrome 웹 화면 PDF 대체 저장은 차단", detail)

    def test_existing_browser_pdf_is_not_reused(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            browser_pdf = temp_path / "invoice.pdf"
            browser_pdf.write_bytes(b"%PDF fake browser page")
            handler.download_dir = temp_path
            handler._is_stable = Mock(return_value=True)
            handler._is_native_wehago_pdf = Mock(
                return_value=(False, "Chrome 웹 화면 PDF 감지")
            )

            existing = handler._existing_invoice_pdf(browser_pdf, browser_pdf)

        self.assertIsNone(existing)
        self.assertIn("Chrome 웹 화면 PDF 감지", handler._last_existing_pdf_rejection)

    def test_print_click_stops_when_local_agent_is_unreachable(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        handler._ensure_wehago_print_runtime = Mock(
            return_value={"state": "runtime-running", "detail": "runtime ready"}
        )
        handler._probe_local_print_agent = Mock(
            return_value={"reachable": False, "error": "TypeError: Failed to fetch"}
        )
        driver = Mock()

        self.assertFalse(handler._click_print(driver))
        driver.find_elements.assert_not_called()
        self.assertIn("local print agent unavailable", handler._last_print_click_detail)

    def test_native_dialog_click_uses_background_window_message(self):
        api = SimpleNamespace(MAKELONG=Mock(return_value=12345))
        constants = SimpleNamespace(
            WM_MOUSEMOVE=0x0200,
            WM_LBUTTONDOWN=0x0201,
            WM_LBUTTONUP=0x0202,
            MK_LBUTTON=1,
        )
        gui = SimpleNamespace(
            WindowFromPoint=Mock(return_value=456),
            IsChild=Mock(return_value=True),
            ScreenToClient=Mock(return_value=(11, 22)),
            PostMessage=Mock(),
        )
        dialog = Mock(handle=123)
        dialog.rectangle.return_value = SimpleNamespace(left=450, top=153)

        with patch.dict(
            "sys.modules",
            {"win32api": api, "win32con": constants, "win32gui": gui},
        ):
            clicked = WehagoHandler._post_dialog_click(dialog, 228, 202)

        self.assertTrue(clicked)
        gui.WindowFromPoint.assert_called_once_with((678, 355))
        self.assertEqual(3, gui.PostMessage.call_count)

    def test_pdf_button_uses_background_message_before_descendant_scan(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        handler._post_dialog_click = Mock(return_value=True)
        dialog = Mock()

        with patch("portal_wehago.time.sleep"):
            clicked = handler._click_pdf_button(dialog)

        self.assertTrue(clicked)
        handler._post_dialog_click.assert_called_once_with(dialog, 228, 202)
        dialog.descendants.assert_not_called()

    def test_pdf_button_skips_print_when_save_as_opens_directly(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        dialog = Mock()
        target = Path("invoice.pdf")
        handler._wait_print_dialog = Mock(return_value=dialog)
        handler._click_pdf_button = Mock(return_value=True)
        handler._find_save_as_dialog = Mock(return_value=Mock())
        handler._click_print_execute_button = Mock(return_value=True)
        handler._save_pdf_dialog = Mock(return_value=target)
        handler._close_print_dialog = Mock()
        handler._close_all_print_dialogs = Mock()
        handler._terminate_stale_duzon_print_helpers = Mock()

        saved = handler._export_pdf_from_print_dialog(target)

        self.assertEqual(target, saved)
        handler._click_print_execute_button.assert_not_called()

    def test_save_as_uses_win32_filename_and_save_button(self):
        written = {}

        def enum_children(_root, callback, extra):
            callback(200, extra)
            callback(201, extra)

        def send_message(handle, _message, _wparam, value):
            written[handle] = value

        constants = SimpleNamespace(
            WM_SETTEXT=0x000C, BM_CLICK=0x00F5,
            SMTO_ABORTIFHUNG=2, SMTO_BLOCK=1,
        )
        gui = SimpleNamespace(
            EnumChildWindows=enum_children,
            IsWindowVisible=Mock(return_value=True),
            GetClassName=Mock(return_value="Edit"),
            GetWindowRect=Mock(
                side_effect=lambda handle: (10, 100, 300, 120)
                if handle == 200
                else (10, 500, 300, 520)
            ),
            SendMessage=Mock(side_effect=send_message),
            SendMessageTimeout=Mock(),
            GetWindowText=Mock(
                side_effect=lambda handle: Path(written.get(handle, "")).name
            ),
            GetDlgItem=Mock(return_value=300),
            IsWindow=Mock(return_value=True),
            PostMessage=Mock(),
        )
        dialog = Mock(handle=100)
        filename = r"C:\ERP_DB\downloads\invoice.pdf"

        with patch.dict(
            "sys.modules", {"win32con": constants, "win32gui": gui}
        ):
            set_ok = WehagoHandler._set_save_as_filename_win32(dialog, filename)
            save_ok = WehagoHandler._click_save_as_save_button_win32(dialog)

        self.assertTrue(set_ok)
        self.assertTrue(save_ok)
        gui.SendMessage.assert_has_calls(
            [
                call(201, constants.WM_SETTEXT, 0, filename),
            ]
        )
        gui.SendMessageTimeout.assert_called_once_with(300, constants.BM_CLICK, 0, 0, 3, 2000)
        gui.PostMessage.assert_not_called()

    def test_save_timeout_does_not_fall_back_to_a_second_click(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        dialog = Mock(handle=100)
        constants = SimpleNamespace(BM_CLICK=0x00F5, SMTO_ABORTIFHUNG=2, SMTO_BLOCK=1)
        gui = SimpleNamespace(
            GetDlgItem=Mock(return_value=300), IsWindow=Mock(return_value=True),
            SendMessageTimeout=Mock(side_effect=OSError(1460, "timed out")),
        )
        with patch.dict("sys.modules", {"win32con": constants, "win32gui": gui}):
            self.assertTrue(handler._click_save_as_save_button(dialog))
        gui.SendMessageTimeout.assert_called_once()
        dialog.descendants.assert_not_called()

    def test_save_request_is_not_success_without_a_pdf_and_is_not_repeated(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        handler.snapshot = Mock(return_value=set())
        handler.wait_new_file = Mock(return_value=None)
        handler._find_save_as_dialog = Mock(return_value=Mock())
        handler._set_save_as_filename_text = Mock(return_value=True)
        handler._click_save_as_save_button = Mock(return_value=True)
        handler._confirm_overwrite_dialog = Mock()
        handler._recover_misplaced_pdf = Mock(return_value=None)
        handler._recover_pdf_from_saveas_new_folders = Mock(return_value=None)
        handler._cleanup_saveas_new_folders = Mock()
        handler._set_pdf_export_error = Mock()
        tick = iter(range(200))
        with TemporaryDirectory() as temp_dir, patch("portal_wehago.time.sleep"), patch(
            "portal_wehago.time.time", side_effect=lambda: next(tick)
        ):
            result = handler._save_pdf_dialog(Path(temp_dir) / "missing.pdf", timeout=40)
        self.assertIsNone(result)
        handler._click_save_as_save_button.assert_called_once()
        handler._set_save_as_filename_text.assert_called_once()
        handler._set_pdf_export_error.assert_called_once()

    def test_preview_detection_uses_title_without_scanning_window_tree(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        preview = Mock()
        preview.is_visible.return_value = True
        preview.window_text.return_value = (
            r"인쇄 기본 설정 / 미리보기 - C:\Douzone\Wehago\TX2A.drf"
        )
        desktop = Mock()
        desktop.windows.return_value = [preview]

        with patch("portal_wehago.Desktop", return_value=desktop):
            detected = handler._print_preview_is_open()

        self.assertTrue(detected)
        preview.wrapper_object.assert_not_called()
        preview.descendants.assert_not_called()

    def test_coordinate_permission_fallback_is_disabled(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        driver = Mock()

        self.assertFalse(handler._allow_chrome_permission_popup_by_xy(driver))
        driver.get_window_position.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()
