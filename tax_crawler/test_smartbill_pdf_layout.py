from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import fitz

from portal_smartbill import _normalize_smartbill_pdf_layout


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
