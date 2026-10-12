from __future__ import annotations
import unittest
from unittest.mock import patch
from web_v1.backend.erp_runner import _extract_invoice_date, _extract_invoice_date_from_text
from web_v1.backend.invoice_db import _repair_regular_fields

CSBILL_TEXT = '전자 세금계산서\n승인번호\n2026101141000018da100001\n작성일자\n공급가액\n세액\n수정사유\n\u00a02026 \u00a010\n\u00a011\n3,320,000\n332,000\n'

class InvoiceDateValidationTests(unittest.TestCase):
    def test_real_csbill_october_layout(self):
        self.assertEqual(_extract_invoice_date_from_text(CSBILL_TEXT), '2026-10-11')

    def test_all_months_keep_complete_month_and_day(self):
        for month in range(1, 13):
            for day in (1, 9, 10, 11, 21, 28):
                with self.subTest(month=month, day=day):
                    self.assertEqual(_extract_invoice_date_from_text(f'작성일자 공급가액 세액\n2026 {month:02d}\n{day:02d}'), f'2026-{month:02d}-{day:02d}')

    def test_compact_labeled_dates_keep_two_digit_months(self):
        for month in (10, 11, 12):
            with self.subTest(month=month):
                self.assertEqual(_extract_invoice_date_from_text(f'발행일자 2026{month:02d}28'), f'2026-{month:02d}-28')

    def test_supported_source_date_formats(self):
        for text in ('2026-10-11', '2026/10/11', '2026.10.11', '2026 10 11', '20261011', '2026년 10월 11일', '2026-10-11T09:00:00'):
            with self.subTest(text=text):
                self.assertEqual(_extract_invoice_date_from_text(text), '2026-10-11')

    def test_invalid_calendar_dates_are_not_accepted(self):
        for text in ('2026-01-00', '2026-02-29', '2026-02-30', '2026-04-31', '2026-11-31', '2026-13-11', '20261000', '2026-10-111'):
            for prefix in ('', '작성일자 '):
                with self.subTest(text=text, prefix=prefix):
                    self.assertEqual(_extract_invoice_date_from_text(prefix + text), '')

    def test_valid_leap_day(self):
        self.assertEqual(_extract_invoice_date_from_text('작성일자 2024 02 29'), '2024-02-29')

    def test_approval_number_is_not_an_invoice_date(self):
        for text in ('2026101141000018da100001', '승인번호 2026101141000018da100001', '작성일자 승인번호 2026101141000018da100001'):
            with self.subTest(text=text):
                self.assertEqual(_extract_invoice_date_from_text(text), '')

    def test_invalid_metadata_recovers_from_pdf(self):
        with patch('web_v1.backend.erp_runner._extract_pdf_text_for_date', return_value=CSBILL_TEXT):
            self.assertEqual(_extract_invoice_date({'invoice_date': '2026-01-00'}, 'invoice.pdf'), '2026-10-11')

    def test_valid_metadata_does_not_read_pdf(self):
        with patch('web_v1.backend.erp_runner._extract_pdf_text_for_date') as read_pdf:
            self.assertEqual(_extract_invoice_date({'invoice_date': '2026-10-11'}, 'invoice.pdf'), '2026-10-11')
            read_pdf.assert_not_called()

    def test_next_valid_metadata_candidate_is_used(self):
        self.assertEqual(_extract_invoice_date({'invoice_date': '2026-01-00', 'issue_date': '2026-10-11'}), '2026-10-11')

    def test_filename_dates_are_validated_and_not_truncated(self):
        with patch('web_v1.backend.erp_runner._extract_pdf_text_for_date', return_value=''):
            for filename in ('invoice_2026-02-30.pdf', 'invoice_2026101141000018.pdf', 'invoice_2026년 10월.pdf'):
                with self.subTest(filename=filename):
                    self.assertEqual(_extract_invoice_date({}, filename), '')
            self.assertEqual(_extract_invoice_date({}, 'invoice_20261011.pdf'), '2026-10-11')
            self.assertEqual(_extract_invoice_date({}, 'invoice_2026년 10월 11일.pdf'), '2026-10-11')

    def test_regular_registration_repairs_nonempty_invalid_date(self):
        raw = {'invoice_date': '2026-01-00', 'data': {'invoice_date': '2026-01-00'}}
        with patch('web_v1.backend.erp_runner._extract_pdf_text_for_date', return_value=CSBILL_TEXT), patch('web_v1.backend.invoice_db._regular_site_name', return_value='D1공장'):
            fixed = _repair_regular_fields(raw, 'invoice.pdf')
        self.assertEqual(fixed['invoice_date'], '2026-10-11')
        self.assertEqual(fixed['data']['invoice_date'], '2026-10-11')
        self.assertEqual(raw['invoice_date'], '2026-01-00')

if __name__ == '__main__':
    unittest.main()
