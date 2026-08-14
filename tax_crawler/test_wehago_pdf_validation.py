from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock

from portal_wehago import WehagoHandler


NATIVE_TEXT = """
전자세금계산서 (공급받는자 보관용)
승인번호 20260810-41000096-48917566
관리번호 TX2026083821631
작성일자 공급가액 세액
"""


class WehagoPdfValidationTests(TestCase):
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
        handler._probe_local_print_agent = Mock(
            return_value={"reachable": False, "error": "TypeError: Failed to fetch"}
        )
        driver = Mock()

        self.assertFalse(handler._click_print(driver))
        driver.find_elements.assert_not_called()
        self.assertIn("local print agent unavailable", handler._last_print_click_detail)

    def test_coordinate_permission_fallback_is_disabled(self):
        handler = WehagoHandler.__new__(WehagoHandler)
        driver = Mock()

        self.assertFalse(handler._allow_chrome_permission_popup_by_xy(driver))
        driver.get_window_position.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()
