from unittest import TestCase

from support.uplus_handler import UplusEDocuHandler


class UplusInvoiceIdentityTests(TestCase):
    def test_different_mail_urls_get_different_pdf_paths(self):
        handler = UplusEDocuHandler.__new__(UplusEDocuHandler)
        xml_data = {
            "공급자": {"상호": "(주)컴퓨존"},
            "공급받는자": {"상호": "(주)대승"},
            "내용": {
                "작성일자": "20260813",
                "합계금액": "37040",
                "품목": [{"품목명": "부품"}],
            },
        }

        first_id = handler.build_source_document_id(
            "https://edocu.uplus.co.kr/view?invoice=first",
            xml_data,
        )
        second_id = handler.build_source_document_id(
            "https://edocu.uplus.co.kr/view?invoice=second",
            xml_data,
        )

        self.assertNotEqual(first_id, second_id)
        self.assertNotEqual(
            handler.build_pdf_filename_from_xml(xml_data, first_id),
            handler.build_pdf_filename_from_xml(xml_data, second_id),
        )

    def test_approval_number_is_preferred_over_url_hash(self):
        handler = UplusEDocuHandler.__new__(UplusEDocuHandler)
        source_id = handler.build_source_document_id(
            "https://edocu.uplus.co.kr/view?temporary=1",
            {"내용": {"승인번호": "20260813-12345678-87654321"}},
        )

        self.assertEqual("20260813-12345678-87654321", source_id)

