import json
import re
import shutil
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from base_handler import BaseTaxInvoiceHandler


class KtAttachmentHandler(BaseTaxInvoiceHandler):
    @property
    def portal_name(self) -> str:
        return "kt"

    def supports(self, url: str) -> bool:
        raw = unquote(str(url or ""))
        lower = raw.lower()
        return lower.startswith("file:") and lower.endswith(".pdf") and "kt email 명세서" in lower

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
        self._mail_subject = str(mail_subject or "")
        try:
            self._do_process(None, url, mail_text, mail_date, result)
        except Exception as exc:
            result["error"] = str(exc)
        return result

    def _do_process(self, driver, url, mail_text, mail_date, result: dict) -> None:
        debug_dir = self._make_debug_dir(mail_date)
        result["debug_dir"] = str(debug_dir)

        src_path = self._file_uri_to_path(url)
        if not src_path.exists():
            result["error"] = f"KT 첨부 PDF를 찾지 못했습니다: {src_path}"
            return

        mail_subject = getattr(self, "_mail_subject", "") or ""
        self._write_text(
            debug_dir / "00_input.json",
            json.dumps(
                {
                    "url": url,
                    "src_path": str(src_path),
                    "mail_subject": mail_subject,
                    "mail_text": mail_text,
                    "mail_date": mail_date,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

        token = self._extract_token(mail_subject, mail_text, src_path.name)
        if not token:
            result["error"] = "KT 메일 제목/본문에서 암호 규칙 토큰을 찾지 못했습니다."
            return
        self._write_text(debug_dir / "01_token.txt", token)

        if token.startswith("W00127"):
            result["error"] = "KT W00127 메일은 수동 처리 대상으로 자동 처리하지 않습니다."
            return

        candidates = self._build_password_candidates(token)
        self._write_text(debug_dir / "02_candidates.json", json.dumps(candidates, ensure_ascii=False, indent=2))
        if not candidates:
            result["error"] = f"KT 암호 규칙을 해석하지 못했습니다: {token}"
            return

        decrypted_path = debug_dir / "03_decrypted.pdf"
        winner = None
        for cand in candidates:
            ok, reason = self._try_decrypt(src_path, decrypted_path, cand["password"])
            cand["ok"] = ok
            cand["reason"] = reason
            if ok:
                winner = cand
                break
        self._write_text(debug_dir / "03_decrypt_attempts.json", json.dumps(candidates, ensure_ascii=False, indent=2))

        if not winner:
            result["error"] = "KT 첨부 PDF 복호화에 실패했습니다."
            return

        text = self._extract_text_pdfium(src_path, winner["password"]) or self._extract_text(decrypted_path)
        self._write_text(debug_dir / "04_text.txt", text)
        parsed = self._parse_text(text)
        parsed["site_name"] = parsed.get("site_name") or winner.get("site_name") or ""
        parsed["vendor_name"] = parsed.get("vendor_name") or "KT"
        parsed["item_name"] = parsed.get("item_name") or "KT 명세서"
        self._write_text(debug_dir / "05_parse.json", json.dumps(parsed, ensure_ascii=False, indent=2))

        issue_date = parsed.get("issue_date") or self._normalize_mail_date(mail_date)
        total_sum = int(parsed.get("total_sum") or 0)
        buyer_name = parsed.get("site_name") or "사업장"
        buyer_biz_no = parsed.get("buyer_biz_no") or ""
        buyer_site = "" if buyer_biz_no else winner.get("site_name", "")
        buyer_display = self._buyer_label(buyer_name, buyer_biz_no, buyer_site)
        final_name = self.build_pdf_filename(
            issue_date=issue_date,
            buyer=buyer_name,
            supplier=parsed.get("vendor_name") or "KT",
            item=parsed.get("item_name") or "KT 명세서",
            extra="",
            amount=str(total_sum),
            buyer_biz_no=buyer_biz_no,
            buyer_site=buyer_site,
        )
        final_path = self.dedupe_path(self.download_dir / final_name)
        shutil.copyfile(decrypted_path, final_path)
        self._write_text(debug_dir / "06_saved_path.txt", str(final_path))

        result.update(
            {
                "ok": True,
                "pdf_path": str(final_path),
                "subject": f"[{buyer_display}] KT 세금계산서({total_sum:,}원)",
                "data": {
                    "vendor_name": parsed.get("vendor_name") or "KT",
                    "site_name": buyer_display,
                    "invoice_date": issue_date,
                    "buyer_biz_no": buyer_biz_no,
                    "total_tax": int(parsed.get("tax_amount") or 0),
                    "total_sum": total_sum,
                    "items": [
                        {
                            "name": parsed.get("item_name") or "KT 명세서",
                            "qty": 1,
                            "inc_vat": total_sum,
                            "account": "통신비",
                        }
                    ],
                },
            }
        )

    def _extract_token(self, mail_subject: str, mail_text: str, filename: str) -> str:
        joined = "\n".join([mail_subject or "", mail_text or "", filename or ""])
        m = re.search(r"\(([A-Za-z0-9!]+)\*{3}\)", joined)
        return m.group(1).strip() if m else ""

    def _build_password_candidates(self, token: str) -> list[dict]:
        token = token.strip()
        candidates: list[dict] = []
        if token.startswith("704100003"):
            candidates.append({"password": "32697", "site_name": "P1공장", "reason": "대승정밀 P1 사업자번호 뒤 5자리"})
            candidates.append({"password": "07029", "site_name": "P4공장", "reason": "대승정밀 P4 사업자번호 뒤 5자리"})
        elif token.startswith("W00115"):
            candidates.append({"password": "51622", "site_name": "일강1공장", "reason": "일강1 사업자번호 뒤 5자리"})
        elif token.startswith("z!23820968"):
            candidates.append({"password": "0003577", "site_name": "대승 법인", "reason": "대승 법인등록번호 뒤 7자리"})
        return candidates

    def _try_decrypt(self, src_path: Path, out_path: Path, password: str) -> tuple[bool, str]:
        try:
            fitz = self._fitz()
            doc = fitz.open(str(src_path))
            if doc.needs_pass:
                ok = doc.authenticate(password)
                if not ok:
                    doc.close()
                    return False, "authenticate returned False"
            doc.save(str(out_path), garbage=4, deflate=True)
            doc.close()
            if out_path.exists() and out_path.stat().st_size > 0:
                return True, "pymupdf decrypted pdf ok"
            return False, "empty output"
        except Exception as exc:
            pymupdf_reason = repr(exc)

        ok, reason = self._try_decrypt_pdfium(src_path, out_path, password)
        if ok:
            return True, f"pypdfium image fallback ok after pymupdf={pymupdf_reason}"
        return False, f"pymupdf={pymupdf_reason}; pdfium={reason}"

    def _try_decrypt_pdfium(self, src_path: Path, out_path: Path, password: str) -> tuple[bool, str]:
        try:
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(src_path), password=password)
            images = []
            try:
                for idx in range(len(doc)):
                    page = doc[idx]
                    bitmap = page.render(scale=2)
                    images.append(bitmap.to_pil().convert("RGB"))
                    page.close()
                if not images:
                    return False, "pdfium no pages"
                images[0].save(
                    str(out_path),
                    "PDF",
                    save_all=True,
                    append_images=images[1:],
                    resolution=144,
                )
            finally:
                for image in images:
                    try:
                        image.close()
                    except Exception:
                        pass
            doc.close()
            if out_path.exists() and out_path.stat().st_size > 0:
                return True, "pdfium rendered pdf ok"
            return False, "pdfium empty output"
        except Exception as exc:
            return False, repr(exc)

    def _extract_text(self, pdf_path: Path) -> str:
        text = self._extract_text_pdfium(pdf_path)
        if text.strip():
            return text

        try:
            fitz = self._fitz()
            doc = fitz.open(str(pdf_path))
            parts = []
            for page in doc[: min(3, len(doc))]:
                parts.append(page.get_text("text") or "")
            doc.close()
            return "\n".join(parts)
        except Exception:
            return ""

    def _extract_text_pdfium(self, pdf_path: Path, password: str | None = None) -> str:
        try:
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(pdf_path), password=password)
            parts = []
            for idx in range(min(3, len(doc))):
                page = doc[idx]
                textpage = page.get_textpage()
                parts.append(textpage.get_text_range() or "")
                textpage.close()
                page.close()
            doc.close()
            return "\n".join(parts)
        except Exception:
            return ""

    @staticmethod
    def _fitz():
        errors = []
        try:
            import fitz
            return fitz
        except Exception as exc:
            errors.append(f"fitz: {exc}")
        try:
            import pymupdf
            return pymupdf
        except Exception as exc:
            errors.append(f"pymupdf: {exc}")
        raise RuntimeError("PyMuPDF 로드 실패: " + " | ".join(errors))

    def _parse_text(self, text: str) -> dict:
        lines = [re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines()]
        lines = [line for line in lines if line]
        clean = "\n".join(lines)
        kt_statement_date = self._extract_kt_statement_date(clean)
        issue = self._search_korean_date(
            clean,
            ["명세서 작성일자", "작성일자", "발송일자", "발행일자"],
        ) or self._search(clean, [r"작성일자\s*([0-9./-]{8,12})", r"발송일자\s*([0-9./-]{8,12})"])
        supply = self._to_int(self._search(clean, [r"공급가액\s*([0-9,]+)", r"공급 금액\s*([0-9,]+)"]))
        tax = self._to_int(self._search(clean, [r"세액\s*([0-9,]+)"]))
        total = self._to_int(self._search(clean, [r"합계금액\s*([0-9,]+)"]))
        invoice_fields = self._tax_invoice_fields_from_lines(lines)
        if invoice_fields:
            issue = invoice_fields.get("issue_date") or issue
            supply = invoice_fields.get("supply_amount") or supply
            tax = invoice_fields.get("tax_amount") or tax
        issue = kt_statement_date or issue
        if not total:
            total = self._amount_after_label(lines, "총납부금액")
        if not total:
            total = supply + tax

        site_name = self._customer_name_from_lines(lines)

        item = self._representative_product_from_lines(lines)
        for line in lines:
            if item:
                break
            if "KT email 명세서" in line:
                continue
            if "요금구성표" in line:
                continue
            if "공급가액" in line or "세액" in line:
                continue
            if "사업자등록번호" in line or "법인번호" in line:
                continue
            if re.search(r"SDWAN|인터넷|회선|서비스|요금|명세서", line, re.I):
                item = line
                break
        if not item:
            item = "KT 명세서"

        return {
            "vendor_name": "KT",
            "site_name": site_name,
            "issue_date": self._normalize_issue(issue),
            "supplier_biz_no": invoice_fields.get("supplier_biz_no", ""),
            "buyer_biz_no": invoice_fields.get("buyer_biz_no", ""),
            "supply_amount": supply,
            "tax_amount": tax,
            "total_sum": total,
            "item_name": item,
        }

    def _tax_invoice_fields_from_lines(self, lines: list[str]) -> dict:
        labels = [
            "명세서 작성일자",
            "공급자 등록번호",
            "공급받는자 등록번호",
            "세금계산서 공급가액",
            "부가가치세",
            "부가가치세 제외요금",
            "계산서 공급가액",
            "10원미만할인요금",
            "전자승인번호",
        ]
        header_idx = self._find_sequence(lines, labels)
        if header_idx < 0:
            return {}

        values_start = -1
        for idx in range(header_idx + len(labels), min(len(lines), header_idx + len(labels) + 40)):
            if re.search(r"\d{4}년\s*\d{1,2}월\s*\d{1,2}일", lines[idx]):
                values_start = idx
                break
        if values_start < 0 or len(lines) <= values_start + 8:
            return {}

        return {
            "issue_date": lines[values_start],
            "supplier_biz_no": lines[values_start + 1],
            "buyer_biz_no": lines[values_start + 2],
            "supply_amount": self._to_int(lines[values_start + 3]),
            "tax_amount": self._to_int(lines[values_start + 4]),
            "vat_exempt_amount": self._to_int(lines[values_start + 5]),
            "invoice_supply_amount": self._to_int(lines[values_start + 6]),
            "rounding_discount": self._to_int(lines[values_start + 7]),
            "approval_no": lines[values_start + 8],
        }

    def _search(self, text: str, patterns: list[str]) -> str:
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                return (m.group(1) if m.lastindex else m.group(0)).strip()
        return ""

    @staticmethod
    def _search_korean_date(text: str, labels: list[str]) -> str:
        compact = re.sub(r"\s+", " ", str(text or ""))
        for label in labels:
            pattern = (
                re.escape(label).replace(r"\ ", r"\s*")
                + r"\D{0,40}(20\d{2})\D{0,8}(\d{1,2})\D{0,8}(\d{1,2})"
            )
            m = re.search(pattern, compact)
            if m:
                return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        return ""

    @staticmethod
    def _extract_kt_statement_date(text: str) -> str:
        compact = re.sub(r"\s+", " ", str(text or ""))
        patterns = [
            r"명\s*세\s*서\s*작\s*성\s*일\s*자\D{0,80}(20\d{2})\D{0,8}(\d{1,2})\D{0,8}(\d{1,2})",
            r"작\s*성\s*일\s*자\D{0,80}(20\d{2})\D{0,8}(\d{1,2})\D{0,8}(\d{1,2})",
            r"과세\s+(20\d{2})(\d{2})(\d{2})[-\s]",
        ]
        for pattern in patterns:
            m = re.search(pattern, compact)
            if m:
                return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        return ""

    @staticmethod
    def _representative_product_from_lines(lines: list[str]) -> str:
        service_re = re.compile(
            r"(biz\s*Managed|Managed\s*보안|인터넷|전용선|SDWAN|VPN|시큐어넷|보안|서비스)",
            re.I,
        )

        def is_service_line(value: str) -> bool:
            text = re.sub(r"\s+", " ", str(value or "")).strip()
            if not text:
                return False
            if re.fullmatch(r"[0-9,\s원]+", text):
                return False
            if "KT email" in text or "명세서" in text:
                return False
            if "대표상품명" in text or "고객명" in text:
                return False
            return bool(service_re.search(text))

        for line in lines:
            m = re.search(r"님\s+(.+)$", line)
            if m and is_service_line(m.group(1)):
                return re.sub(r"\s+", " ", m.group(1)).strip()

        for idx, line in enumerate(lines):
            if not is_service_line(line):
                continue
            if idx > 0 and "대표상품명" in lines[idx - 1]:
                return re.sub(r"\s+", " ", line).strip()
            if "요금" not in line and "납부" not in line:
                return re.sub(r"\s+", " ", line).strip()

        token_re = re.compile(r"^(704100003\*{3}|W00115\*{3}|z!23820968\d*)$")
        for idx, line in enumerate(lines):
            if not token_re.match(line):
                continue
            for candidate in lines[idx + 1: idx + 8]:
                if is_service_line(candidate):
                    return re.sub(r"\s+", " ", candidate).strip()
        return ""

    def _amount_after_label(self, lines: list[str], label: str) -> int:
        for idx, line in enumerate(lines):
            if label not in line:
                continue
            for nxt in lines[idx + 1: idx + 8]:
                amount = self._to_int(nxt)
                if amount >= 10000 and "원" in nxt:
                    return amount
        return 0

    @staticmethod
    def _find_sequence(lines: list[str], labels: list[str]) -> int:
        normalized = [re.sub(r"\s+", "", str(line or "")) for line in lines]
        targets = [re.sub(r"\s+", "", label) for label in labels]
        width = len(targets)
        for idx in range(0, len(normalized) - width + 1):
            if normalized[idx:idx + width] == targets:
                return idx
        return -1

    @staticmethod
    def _customer_name_from_lines(lines: list[str]) -> str:
        for idx, line in enumerate(lines):
            if "명세서번호는" not in line or idx <= 0:
                continue
            name = lines[idx - 1].strip()
            return re.sub(r"\s*님$", "", name).strip()
        for line in lines:
            if line.endswith(" 님"):
                return line[:-2].strip()
        return ""

    def _make_debug_dir(self, mail_date: str) -> Path:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dump_dir = self.download_dir / "_debug_kt" / f"{mail_date or 'nodate'}_{stamp}"
        dump_dir.mkdir(parents=True, exist_ok=True)
        return dump_dir

    @staticmethod
    def _normalize_issue(raw: str) -> str:
        digits = re.sub(r"[^\d]", "", str(raw or ""))
        if len(digits) >= 8:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return ""

    @staticmethod
    def _normalize_mail_date(mail_date: str) -> str:
        digits = re.sub(r"[^\d]", "", str(mail_date or ""))
        if len(digits) == 6:
            digits = "20" + digits
        if len(digits) >= 8:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return time.strftime("%Y-%m-%d")

    @staticmethod
    def _file_uri_to_path(url: str) -> Path:
        parsed = urlparse(url)
        path = url2pathname(unquote(parsed.path))
        if path.startswith("/") and re.match(r"^/[A-Za-z]:", path):
            path = path[1:]
        return Path(path)

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8", errors="replace")

    @staticmethod
    def _to_int(v) -> int:
        digits = re.sub(r"[^\d]", "", str(v or ""))
        return int(digits or "0")
