from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

import fitz

from portal_smartbill import SmartBillHandler, _normalize_smartbill_pdf_layout


class SmartBillPdfLayoutTests(TestCase):
    def test_invoice_content_is_fitted_to_landscape_a4(self):
        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "smartbill.pdf"
            source = fitz.open()
            page = source.new_page(width=612, height=792)
            page.draw_rect(fitz.Rect(30, 55, 515, 350), color=(0, 0, 0))
            page.insert_text((45, 90), "SMARTBILL TAX INVOICE")
            page.insert_text((45, 330), "TOTAL 275000")
            source.save(pdf_path)
            source.close()

            result = _normalize_smartbill_pdf_layout(pdf_path)

            self.assertEqual(pdf_path, result)
            normalized = fitz.open(pdf_path)
            try:
                self.assertEqual(1, normalized.page_count)
                page = normalized[0]
                self.assertGreater(page.rect.width, page.rect.height)
                self.assertAlmostEqual(841.89, page.rect.width, delta=1.0)
                self.assertAlmostEqual(595.28, page.rect.height, delta=1.0)
                self.assertIn("SMARTBILL TAX INVOICE", page.get_text())

                content_rects = [fitz.Rect(word[:4]) for word in page.get_text("words")]
                content_rects.extend(
                    fitz.Rect(drawing["rect"])
                    for drawing in page.get_drawings()
                    if drawing.get("rect")
                )
                content = fitz.Rect(content_rects[0])
                for rect in content_rects[1:]:
                    content |= rect
                self.assertGreater(content.width, 750)
                self.assertLess(content.y0, 80)
                self.assertGreater(content.y1, 500)
            finally:
                normalized.close()

    def test_empty_pdf_keeps_original_file_readable(self):
        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "empty.pdf"
            source = fitz.open()
            source.new_page(width=612, height=792)
            source.save(pdf_path)
            source.close()

            _normalize_smartbill_pdf_layout(pdf_path)

            normalized = fitz.open(pdf_path)
            self.assertEqual(1, normalized.page_count)
            self.assertGreater(normalized[0].rect.width, normalized[0].rect.height)
            normalized.close()


class SmartBillReceiptApprovalTests(TestCase):
    def _handler(self):
        handler = SmartBillHandler.__new__(SmartBillHandler)
        handler._is_print_button_present = Mock(return_value=True)
        handler._click_smartbill_receipt_approval = Mock(return_value=True)
        handler._click_smartbill_approval_modal_action = Mock(return_value=True)
        handler._close_smartbill_approval_modal = Mock()
        handler._dismiss_verified_approval_stale_alert = Mock(return_value=False)
        return handler

    def test_unapproved_invoice_must_transition_before_success(self):
        handler = self._handler()
        handler._smartbill_receipt_status = Mock(side_effect=["I", "C", "C"])
        driver = Mock()

        with patch("portal_smartbill.time.sleep"):
            approved = handler._handle_approval(driver)

        self.assertTrue(approved)
        handler._click_smartbill_receipt_approval.assert_called_once_with(driver)

    def test_print_button_does_not_make_status_i_approved(self):
        handler = self._handler()
        handler._smartbill_receipt_status = Mock(return_value="I")

        with patch("portal_smartbill.time.sleep"):
            approved = handler._handle_approval(Mock())

        self.assertFalse(approved)
        self.assertTrue(handler._is_print_button_present.return_value)

    def test_already_approved_status_can_continue_to_print(self):
        handler = self._handler()
        handler._smartbill_receipt_status = Mock(return_value="C")

        approved = handler._handle_approval(Mock())

        self.assertTrue(approved)
        handler._click_smartbill_receipt_approval.assert_not_called()
