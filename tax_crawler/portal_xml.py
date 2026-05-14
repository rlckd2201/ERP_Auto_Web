import json
import re
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from base_handler import BaseTaxInvoiceHandler
from xml_parser import parse_tax_invoice_xml


class XmlAttachmentHandler(BaseTaxInvoiceHandler):
    @property
    def portal_name(self) -> str:
        return "xml"

    def supports(self, url: str) -> bool:
        raw = unquote(str(url or ""))
        return raw.lower().startswith("file:") and raw.lower().endswith(".xml")

    def process(self, url: str, mail_text: str = "", mail_date: str = "", mail_subject: str = "") -> dict:
        if not mail_date:
            mail_date = time.strftime("%y%m%d")
        result = {
            "ok": False,
            "portal": self.portal_name,
            "pdf_path": None,
            "subject": "",
            "data": {},
            "error": None,
        }
        try:
            self._do_process(None, url, mail_text, mail_date, result, mail_subject=mail_subject)
        except Exception as exc:
            result["error"] = str(exc)
        return result

    def _do_process(self, driver, url, mail_text, mail_date, result: dict, mail_subject: str = "") -> None:
        xml_path = self._file_uri_to_path(url)
        if not xml_path.exists():
            result["error"] = f"XML attachment not found: {xml_path}"
            return

        supplier, buyer, content = parse_tax_invoice_xml(str(xml_path))
        supplier_name = (supplier.get("상호") or "매입처").strip()
        buyer_name = (buyer.get("상호") or "공급받는자").strip()
        supplier_biz_no = supplier.get("등록번호") or ""
        buyer_biz_no = buyer.get("등록번호") or ""
        issue_date = content.get("작성일자") or self._normalize_mail_date(mail_date)
        supply = self._to_int(content.get("공급가액"))
        tax = self._to_int(content.get("세액"))
        total = self._to_int(content.get("합계금액")) or supply + tax

        items = []
        for row in content.get("항목") or []:
            name = (row.get("품목") or "").strip()
            row_supply = self._to_int(row.get("공급가액"))
            row_tax = self._to_int(row.get("세액"))
            row_total = row_supply + row_tax if row_supply or row_tax else total
            if name or row_total:
                items.append(
                    {
                        "name": name or "세금계산서",
                        "qty": 1,
                        "inc_vat": row_total,
                        "supply": row_supply,
                        "account": self._guess_account(name, supplier_name),
                    }
                )
        if not items:
            items = [{"name": "세금계산서", "qty": 1, "inc_vat": total, "supply": supply}]

        buyer_site = self._site_name_from_biz_no(buyer_biz_no)
        buyer_display = self._buyer_label(buyer_name, buyer_biz_no, buyer_site)
        item_name = items[0].get("name") or "세금계산서"
        final_name = self.build_pdf_filename(
            issue_date=issue_date,
            buyer=buyer_name,
            supplier=supplier_name,
            item=item_name,
            extra="",
            amount=str(total),
            buyer_biz_no=buyer_biz_no,
            buyer_site=buyer_site,
        )
        final_path = self.dedupe_path(self.download_dir / final_name)
        self._render_pdf(final_path, supplier, buyer, content, items)

        invoice_type = "purchase" if "컴퓨존" in f"{mail_subject} {mail_text} {supplier_name}" else "regular"
        data = {
            "vendor_name": supplier_name,
            "supplier_name": supplier_name,
            "supplier_biz_no": supplier_biz_no,
            "site_name": buyer_site or buyer_display,
            "buyer_name": buyer_name,
            "buyer_biz_no": buyer_biz_no,
            "buyer_site": buyer_site,
            "invoice_date": issue_date,
            "target_supply": supply,
            "total_tax": tax,
            "total_sum": total,
            "items": items,
            "raw": {"supplier": supplier, "buyer": buyer, "content": content},
        }
        result.update(
            {
                "ok": True,
                "pdf_path": str(final_path),
                "subject": f"[{buyer_display}] {supplier_name} 세금계산서({total:,}원)",
                "data": data,
                "invoice_type": invoice_type,
            }
        )

    def _render_pdf(self, out_path: Path, supplier: dict, buyer: dict, content: dict, items: list[dict]) -> None:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as exc:
            raise RuntimeError(f"Pillow PDF renderer unavailable: {exc}") from exc

        width, height = 1240, 1754
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        font_regular = self._font(34)
        font_bold = self._font(42)
        font_small = self._font(28)

        y = 90
        draw.text((width // 2, y), "전자세금계산서", fill="black", font=font_bold, anchor="ma")
        y += 90
        self._line(draw, 80, y, width - 80, y)

        rows = [
            ("공급자", supplier.get("상호"), supplier.get("등록번호")),
            ("공급받는자", buyer.get("상호"), buyer.get("등록번호")),
            ("작성일자", content.get("작성일자"), ""),
            ("공급가액", self._money(content.get("공급가액")), "세액 " + self._money(content.get("세액"))),
            ("합계금액", self._money(content.get("합계금액")), ""),
            ("승인번호", content.get("승인번호"), ""),
        ]
        for label, value, value2 in rows:
            y += 58
            draw.text((100, y), str(label or ""), fill="black", font=font_regular)
            draw.text((300, y), str(value or ""), fill="black", font=font_regular)
            if value2:
                draw.text((780, y), str(value2), fill="black", font=font_regular)

        y += 90
        self._line(draw, 80, y, width - 80, y)
        y += 40
        draw.text((100, y), "품목", fill="black", font=font_regular)
        draw.text((760, y), "공급가액", fill="black", font=font_regular)
        draw.text((980, y), "세액", fill="black", font=font_regular)
        y += 55
        self._line(draw, 80, y, width - 80, y)

        for item in content.get("항목") or []:
            y += 52
            name = str(item.get("품목") or "")[:34]
            draw.text((100, y), name, fill="black", font=font_small)
            draw.text((760, y), self._money(item.get("공급가액")), fill="black", font=font_small)
            draw.text((980, y), self._money(item.get("세액")), fill="black", font=font_small)

        y = height - 160
        self._line(draw, 80, y, width - 80, y)
        y += 45
        draw.text((100, y), "원본 XML 첨부를 전표 처리용 PDF로 변환했습니다.", fill="gray", font=font_small)
        image.save(str(out_path), "PDF", resolution=144)

    @staticmethod
    def _file_uri_to_path(url: str) -> Path:
        parsed = urlparse(url)
        path = url2pathname(unquote(parsed.path))
        if path.startswith("/") and re.match(r"^/[A-Za-z]:", path):
            path = path[1:]
        return Path(path)

    @staticmethod
    def _to_int(value) -> int:
        digits = re.sub(r"[^\d-]", "", str(value or ""))
        try:
            return int(digits) if digits not in ("", "-") else 0
        except Exception:
            return 0

    @staticmethod
    def _money(value) -> str:
        digits = re.sub(r"[^\d-]", "", str(value or ""))
        try:
            return f"{int(digits):,}원" if digits not in ("", "-") else ""
        except Exception:
            return str(value or "")

    @staticmethod
    def _normalize_mail_date(mail_date: str) -> str:
        digits = re.sub(r"[^\d]", "", str(mail_date or ""))
        if len(digits) == 6:
            digits = "20" + digits
        if len(digits) >= 8:
            return f"{digits[:4]}/{digits[4:6]}/{digits[6:8]}"
        return time.strftime("%Y/%m/%d")

    @staticmethod
    def _guess_account(item_name: str, supplier_name: str) -> str:
        text = f"{item_name} {supplier_name}".lower()
        if any(key in text for key in ("kt", "케이티", "통신", "vpn", "sdwan", "오토에버")):
            return "통신비"
        return "지급수수료"

    @staticmethod
    def _line(draw, x1, y1, x2, y2):
        draw.line((x1, y1, x2, y2), fill="black", width=2)

    @staticmethod
    def _font(size: int):
        try:
            from PIL import ImageFont

            for path in (
                r"C:\Windows\Fonts\malgun.ttf",
                r"C:\Windows\Fonts\malgunbd.ttf",
                r"C:\Windows\Fonts\gulim.ttc",
            ):
                if Path(path).exists():
                    return ImageFont.truetype(path, size)
            return ImageFont.load_default()
        except Exception:
            return None
