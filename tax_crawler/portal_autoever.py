import json
import re
import time
import base64
import html as html_lib
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_handler import BaseTaxInvoiceHandler


class AutoEverHandler(BaseTaxInvoiceHandler):
    DOMAIN = "etax.autoever.com"

    @property
    def portal_name(self) -> str:
        return "autoever"

    def supports(self, url: str) -> bool:
        u = (url or "").lower()
        return self.DOMAIN in u or "autoever.com" in u

    def _do_process(self, driver, url, mail_text, mail_date, result):
        dump_dir = self._make_debug_dir(mail_date)
        result["debug_dir"] = str(dump_dir)
        self._write_text(
            dump_dir / "00_input.json",
            json.dumps({"url": url, "mail_text": mail_text, "mail_date": mail_date}, ensure_ascii=False, indent=2),
        )

        password = self._extract_password(mail_text)
        if not password:
            result["error"] = "오토에버 메일 본문에서 비밀번호를 찾지 못했습니다."
            return
        self._write_text(dump_dir / "00_password.txt", password)

        driver.get(url)
        time.sleep(2)
        self._dump_state(driver, dump_dir, "01_login_page")

        self._ensure_non_member_tab(driver)
        pwd_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#TEMP_PASS"))
        )
        pwd_input.clear()
        pwd_input.send_keys(password)

        before_handles = list(driver.window_handles)
        confirm = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn-login.ty2"))
        )
        driver.execute_script("arguments[0].click();", confirm)
        time.sleep(2)

        popup = self._switch_invoice_window(driver, before_handles)
        if not popup:
            self._dump_state(driver, dump_dir, "02_popup_not_found")
            result["error"] = "오토에버 세금계산서 팝업을 찾지 못했습니다."
            return

        self._dump_state(driver, dump_dir, "03_invoice_popup")

        parsed = self._parse_popup(driver)
        self._write_text(dump_dir / "04_parse.json", json.dumps(parsed, ensure_ascii=False, indent=2))

        temp_pdf = dump_dir / "05_rendered_invoice.pdf"
        if not self._save_popup_pdf(driver, temp_pdf, dump_dir):
            self._dump_state(driver, dump_dir, "05_pdf_failed")
            result["error"] = "오토에버 PDF 저장에 실패했습니다."
            return

        final_name = self.build_pdf_filename(
            issue_date=parsed.get("issue_date") or mail_date,
            buyer=parsed.get("buyer_name") or "사업장",
            supplier=parsed.get("supplier_name") or "매입처",
            item=parsed.get("item_name") or "세금계산서",
            extra="",
            amount=str(parsed.get("total_sum") or 0),
            buyer_biz_no=parsed.get("buyer_biz_no") or "",
        )
        final_path = self.dedupe_path(self.download_dir / final_name)
        time.sleep(1)
        temp_pdf.rename(final_path)
        self._write_text(dump_dir / "06_saved_path.txt", str(final_path))

        result.update(
            {
                "ok": True,
                "pdf_path": str(final_path),
                "subject": f"[{parsed.get('buyer_name') or '사업장'}] {parsed.get('supplier_name') or '매입처'} 세금계산서({int(parsed.get('total_sum') or 0):,}원)",
                "data": {
                    "vendor_name": parsed.get("supplier_name") or "",
                    "site_name": parsed.get("buyer_name") or "",
                    "total_tax": int(parsed.get("tax_amount") or 0),
                    "total_sum": int(parsed.get("total_sum") or 0),
                    "items": [
                        {
                            "name": parsed.get("item_name") or "세금계산서",
                            "qty": 1,
                            "inc_vat": int(parsed.get("total_sum") or 0),
                            "account": "소모품비",
                        }
                    ],
                },
            }
        )

    def _extract_password(self, mail_text: str) -> str:
        parts = [getattr(self, "_mail_subject", ""), mail_text]
        text = html_lib.unescape("\n".join(str(part or "") for part in parts))
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""

        label_patterns = [
            r"(?:비밀번호|임시비밀번호|암호|password|pass\s*word|pwd)\s*(?:는|은|입니다|:|：|=|-)?\s*([0-9A-Za-z!@#$%^&*._~+\-]{10,40})",
            r"(?:로그인\s*시|로그인시)\s*(?:사용하는\s*)?(?:비밀번호|암호)[^0-9A-Za-z!@#$%^&*._~+\-]{0,40}([0-9A-Za-z!@#$%^&*._~+\-]{10,40})",
        ]
        for pat in label_patterns:
            for match in re.finditer(pat, text, re.I):
                candidate = self._clean_password_candidate(match.group(1))
                if self._valid_password_candidate(candidate):
                    return candidate

        for label in ("비밀번호", "임시비밀번호", "암호", "password", "pass word", "pwd"):
            for match in re.finditer(label, text, re.I):
                window = text[match.end():match.end() + 120]
                for token in re.findall(r"[0-9A-Za-z!@#$%^&*._~+\-]{10,40}", window):
                    candidate = self._clean_password_candidate(token)
                    if self._valid_password_candidate(candidate):
                        return candidate

        return ""

    @staticmethod
    def _clean_password_candidate(value: str) -> str:
        return re.sub(r"[^0-9A-Za-z!@#$%^&*._~+\-]", "", str(value or "")).strip()

    @staticmethod
    def _valid_password_candidate(value: str) -> bool:
        if not value or not (10 <= len(value) <= 40):
            return False
        lower = value.lower()
        if lower.startswith(("http", "https")):
            return False
        if value.isdigit():
            return False
        return bool(re.search(r"[A-Za-z]", value) and re.search(r"\d", value))

    def _ensure_non_member_tab(self, driver) -> None:
        xpaths = [
            "//button[contains(normalize-space(.),'비회원')]",
            "//a[contains(normalize-space(.),'비회원')]",
            "//*[contains(@class,'tab') and contains(normalize-space(.),'비회원')]",
        ]
        for xp in xpaths:
            try:
                elem = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp)))
                driver.execute_script("arguments[0].click();", elem)
                time.sleep(0.5)
                return
            except Exception:
                pass

    def _switch_invoice_window(self, driver, before_handles: list[str]) -> bool:
        deadline = time.time() + 10
        while time.time() < deadline:
            handles = list(driver.window_handles)
            if len(handles) > len(before_handles):
                new_handle = [h for h in handles if h not in before_handles][-1]
                driver.switch_to.window(new_handle)
                return True
            if "noMbrTaxInvoiceViewPop.do" in (driver.current_url or ""):
                return True
            time.sleep(0.5)
        return "noMbrTaxInvoiceViewPop.do" in (driver.current_url or "")

    def _parse_popup(self, driver) -> dict:
        cells = self._table_cells(driver.page_source)

        supplier_name = self._value_after(cells, "상호 (법인명)", 1) or self._label_value(driver, "상호(법인명)", 1)
        buyer_name = self._value_after(cells, "상호 (법인명)", 2) or self._label_value(driver, "상호(법인명)", 2)
        supplier_biz_no = self._value_after(cells, "등록번호", 1)
        buyer_biz_no = self._value_after(cells, "등록번호", 2)

        issue_date = ""
        supply_amount = 0
        tax_amount = 0
        header_idx = self._find_sequence(cells, ["작성일자", "공급가액", "세액", "수정사유", "비고"])
        if header_idx >= 0 and len(cells) > header_idx + 7:
            issue_date = cells[header_idx + 5]
            supply_amount = self._to_int(cells[header_idx + 6])
            tax_amount = self._to_int(cells[header_idx + 7])

        item_name = ""
        item_supply = 0
        item_tax = 0
        item_idx = self._find_sequence(cells, ["월", "일", "품목", "규격", "수량", "단가", "공급가액", "세액", "비고"])
        if item_idx >= 0 and len(cells) > item_idx + 15:
            item_name = cells[item_idx + 11]
            item_supply = self._to_int(cells[item_idx + 14])
            item_tax = self._to_int(cells[item_idx + 15])

        total_sum = 0
        total_idx = self._find_sequence(cells, ["합계금액", "현금", "수표", "어음", "외상미수금"])
        if total_idx >= 0 and len(cells) > total_idx + 6:
            total_sum = self._to_int(cells[total_idx + 6])

        supply_amount = supply_amount or item_supply
        tax_amount = tax_amount or item_tax
        total_sum = total_sum or (supply_amount + tax_amount)

        return {
            "supplier_name": supplier_name,
            "supplier_biz_no": supplier_biz_no,
            "buyer_name": buyer_name,
            "buyer_biz_no": buyer_biz_no,
            "issue_date": issue_date or self._label_value(driver, "작성일자", 1),
            "supply_amount": supply_amount,
            "tax_amount": tax_amount,
            "item_name": item_name or self._table_item_name(driver),
            "total_sum": total_sum or self._to_int(self._table_total(driver)),
        }

    def _save_popup_pdf(self, driver, output_path: Path, dump_dir: Path) -> bool:
        try:
            payload = driver.execute_cdp_cmd(
                "Page.printToPDF",
                {
                    "printBackground": True,
                    "paperWidth": 8.27,
                    "paperHeight": 11.69,
                    "marginTop": 0.2,
                    "marginBottom": 0.2,
                    "marginLeft": 0.2,
                    "marginRight": 0.2,
                    "preferCSSPageSize": True,
                },
            )
            pdf_bytes = base64.b64decode(payload["data"])
            output_path.write_bytes(pdf_bytes)
            self._write_text(
                dump_dir / "05_pdf_success.json",
                json.dumps({"output_path": str(output_path), "size": len(pdf_bytes), "url": driver.current_url}, ensure_ascii=False, indent=2),
            )
            return output_path.exists() and output_path.stat().st_size > 0
        except Exception as exc:
            self._write_text(dump_dir / "05_pdf_error.txt", repr(exc))
            return False

    def _label_value(self, driver, label: str, occurrence: int = 1) -> str:
        xpaths = [
            f"(//*[normalize-space()='{label}'])[{occurrence}]/following-sibling::*[1]",
            f"((//*[normalize-space()='{label}'])[{occurrence}]/parent::*/*[2])",
            f"((//*[normalize-space()='{label}'])[{occurrence}]/parent::*/*[4])",
        ]
        for xp in xpaths:
            try:
                elem = driver.find_element(By.XPATH, xp)
                text = " ".join((elem.text or "").split())
                if text:
                    return text
            except Exception:
                pass
        return ""

    def _table_item_name(self, driver) -> str:
        xpaths = [
            "(//table//tr[td[normalize-space()='월']]/following-sibling::tr[1]/td)[3]",
            "(//tr[td[normalize-space()='월'] and td[normalize-space()='일'] and td[normalize-space()='품목']]/following-sibling::tr[1]/td)[3]",
        ]
        for xp in xpaths:
            try:
                elem = driver.find_element(By.XPATH, xp)
                text = " ".join((elem.text or "").split())
                if text:
                    return text
            except Exception:
                pass
        return ""

    def _table_total(self, driver) -> str:
        xpaths = [
            "(//*[normalize-space()='합계금액']/following-sibling::*[1])[1]",
            "(//tr[td[contains(normalize-space(),'합계금액')]]/td[2])[1]",
        ]
        for xp in xpaths:
            try:
                elem = driver.find_element(By.XPATH, xp)
                text = " ".join((elem.text or "").split())
                if text:
                    return text
            except Exception:
                pass
        return ""

    @staticmethod
    def _table_cells(source: str) -> list[str]:
        source = re.sub(r"<br\s*/?>", "", str(source or ""), flags=re.I)
        cells = []
        for match in re.finditer(r"<t[hd][^>]*>(.*?)</t[hd]>", source, flags=re.I | re.S):
            text = re.sub(r"<[^>]+>", "", match.group(1))
            text = html_lib.unescape(text).replace("\xa0", " ")
            text = " ".join(text.split())
            if text:
                cells.append(text)
        return cells

    @staticmethod
    def _normalize_cell(value: str) -> str:
        return re.sub(r"\s+", "", str(value or ""))

    def _value_after(self, cells: list[str], label: str, occurrence: int = 1) -> str:
        target = self._normalize_cell(label)
        count = 0
        for idx, cell in enumerate(cells):
            if self._normalize_cell(cell) != target:
                continue
            count += 1
            if count == occurrence and len(cells) > idx + 1:
                return cells[idx + 1]
        return ""

    def _find_sequence(self, cells: list[str], labels: list[str]) -> int:
        targets = [self._normalize_cell(label) for label in labels]
        normalized = [self._normalize_cell(cell) for cell in cells]
        width = len(targets)
        for idx in range(0, len(normalized) - width + 1):
            if normalized[idx:idx + width] == targets:
                return idx
        return -1

    def _make_debug_dir(self, mail_date: str) -> Path:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dump_dir = self.download_dir / "_debug_autoever" / f"{mail_date or 'nodate'}_{stamp}"
        dump_dir.mkdir(parents=True, exist_ok=True)
        return dump_dir

    def _dump_state(self, driver, dump_dir: Path, label: str) -> None:
        try:
            driver.save_screenshot(str(dump_dir / f"{label}.png"))
        except Exception:
            pass
        try:
            self._write_text(dump_dir / f"{label}.html", driver.page_source)
        except Exception:
            pass
        try:
            summary = {
                "title": driver.title,
                "url": driver.current_url,
                "buttons": [],
                "window_handles": list(driver.window_handles),
            }
            for btn in driver.find_elements(By.CSS_SELECTOR, "button, a, input[type='button'], input[type='submit']"):
                try:
                    if not btn.is_displayed():
                        continue
                    txt = " ".join(filter(None, [(btn.text or "").strip(), (btn.get_attribute("value") or "").strip()]))
                    if txt:
                        summary["buttons"].append(txt)
                except Exception:
                    continue
            self._write_text(dump_dir / f"{label}_summary.json", json.dumps(summary, ensure_ascii=False, indent=2))
        except Exception:
            pass

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8", errors="replace")

    @staticmethod
    def _to_int(v) -> int:
        try:
            return int(re.sub(r"[^\d]", "", str(v or "0")) or "0")
        except Exception:
            return 0


if __name__ == "__main__":
    handler = AutoEverHandler()
    sample_url = "https://etax.autoever.com/?flag=noMbr"
    sample_mail = "비밀번호 2026042098s6hv0m399p"
    res = handler.process(url=sample_url, mail_text=sample_mail, mail_date=time.strftime("%y%m%d"))
    print(json.dumps(res, ensure_ascii=False, indent=2))
