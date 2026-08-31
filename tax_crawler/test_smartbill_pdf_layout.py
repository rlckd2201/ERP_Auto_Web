from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

import fitz

from portal_smartbill import (
    SmartBillHandler,
    _normalize_smartbill_pdf_layout,
    _smartbill_print_full_a4_pdf_base64,
)


class SmartBillPdfLayoutTests(TestCase):
    def test_original_portrait_page_is_not_rewritten_or_cropped(self):
        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "smartbill.pdf"
            source = fitz.open()
            page = source.new_page(width=595.44, height=841.68)
            page.insert_text((30, 20), "PRINT DATE / BUSINESS IS ON")
            page.draw_rect(fitz.Rect(30, 55, 515, 350), color=(0, 0, 0))
            page.insert_text((45, 90), "SMARTBILL TAX INVOICE")
            page.insert_text((45, 330), "TOTAL 275000")
            page.insert_text((30, 820), "SOURCE URL / 1 OF 1")
            source.save(pdf_path)
            source.close()
            original_bytes = pdf_path.read_bytes()

            result = _normalize_smartbill_pdf_layout(pdf_path)

            self.assertEqual(pdf_path, result)
            self.assertEqual(original_bytes, pdf_path.read_bytes())
            preserved = fitz.open(pdf_path)
            try:
                self.assertEqual(1, preserved.page_count)
                page = preserved[0]
                self.assertLess(page.rect.width, page.rect.height)
                self.assertAlmostEqual(595.44, page.rect.width, delta=0.1)
                self.assertAlmostEqual(841.68, page.rect.height, delta=0.1)
                self.assertIn("SMARTBILL TAX INVOICE", page.get_text())
                self.assertIn("SOURCE URL / 1 OF 1", page.get_text())
            finally:
                preserved.close()

    def test_chrome_print_uses_full_a4_portrait_with_header_and_footer(self):
        driver = Mock()
        driver.execute_cdp_cmd.return_value = {"data": "encoded-pdf"}

        result = _smartbill_print_full_a4_pdf_base64(driver)

        self.assertEqual("encoded-pdf", result)
        command, options = driver.execute_cdp_cmd.call_args.args
        self.assertEqual("Page.printToPDF", command)
        self.assertFalse(options["landscape"])
        self.assertTrue(options["displayHeaderFooter"])
        self.assertAlmostEqual(8.27, options["paperWidth"])
        self.assertAlmostEqual(11.69, options["paperHeight"])
        self.assertIn('class="date"', options["headerTemplate"])
        self.assertIn('class="title"', options["headerTemplate"])
        self.assertIn('class="url"', options["footerTemplate"])
        self.assertIn('class="pageNumber"', options["footerTemplate"])


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
