from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from web_v1.backend.expense_excel_export import (
    A4_HEIGHT_POINTS,
    A4_WIDTH_POINTS,
    EXPENSE_PRINT_AREA,
    XL_PAPER_A4,
    configure_page_setup,
    normalize_pdf_to_portrait_a4,
)
from web_v1.backend.zoom_retry import zoom_expense_retry_wait_seconds


class _FailingPaperSizePageSetup:
    def __init__(self) -> None:
        self._paper_size = 1

    @property
    def PaperSize(self) -> int:
        return self._paper_size

    @PaperSize.setter
    def PaperSize(self, value: int) -> None:
        raise RuntimeError("printer driver rejected PaperSize")


class ZoomExpenseResilienceTests(unittest.TestCase):
    def test_page_setup_continues_when_printer_rejects_a4(self) -> None:
        page_setup = _FailingPaperSizePageSetup()

        warnings = configure_page_setup(page_setup)

        self.assertEqual(page_setup.PrintArea, EXPENSE_PRINT_AREA)
        self.assertEqual(page_setup.Orientation, 1)
        self.assertFalse(page_setup.Zoom)
        self.assertEqual(page_setup.FitToPagesWide, 1)
        self.assertEqual(page_setup.FitToPagesTall, 1)
        self.assertTrue(warnings)
        self.assertIn("normalized to A4", warnings[0])

    def test_page_setup_keeps_existing_a4_without_setting_it_again(self) -> None:
        page_setup = _FailingPaperSizePageSetup()
        page_setup._paper_size = XL_PAPER_A4

        warnings = configure_page_setup(page_setup)

        self.assertEqual(warnings, [])
        self.assertEqual(page_setup.PaperSize, XL_PAPER_A4)

    def test_non_a4_pdf_is_normalized_to_one_portrait_a4_page(self) -> None:
        import fitz

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "expense.pdf"
            document = fitz.open()
            page = document.new_page(width=612, height=792)
            page.insert_text((72, 72), "Zoom expense report")
            document.save(str(path))
            document.close()

            changed = normalize_pdf_to_portrait_a4(path)

            self.assertTrue(changed)
            with fitz.open(str(path)) as normalized:
                self.assertEqual(normalized.page_count, 1)
                rect = normalized.load_page(0).rect
                self.assertAlmostEqual(rect.width, A4_WIDTH_POINTS, delta=1.0)
                self.assertAlmostEqual(rect.height, A4_HEIGHT_POINTS, delta=1.0)

    def test_recent_zoom_failure_is_rate_limited(self) -> None:
        wait_seconds = zoom_expense_retry_wait_seconds(
            {"zoom_expense_report_last_error_at": datetime.now().isoformat(timespec="seconds")},
            600,
        )
        self.assertGreaterEqual(wait_seconds, 59)

    def test_stale_zoom_failure_can_retry(self) -> None:
        wait_seconds = zoom_expense_retry_wait_seconds(
            {
                "zoom_expense_report_last_error_at": (
                    datetime.now() - timedelta(days=1)
                ).isoformat(timespec="seconds")
            },
            600,
        )
        self.assertEqual(wait_seconds, 0)


if __name__ == "__main__":
    unittest.main()
