import json
import os
import re
import sqlite3
import time
import unicodedata
from pathlib import Path

BASE_DIR = Path(r"C:\ERP_DB")
DOWNLOAD_DIR = BASE_DIR / "downloads"
DB_PATH = BASE_DIR / "learned_data.db"
CRAWLER_FILE = Path(r"C:\Users\Administrator\Desktop\전표 자동화 프로그램\세금계산서 크롤링\portal_smartbill.py")

FACTORY_MAP = {
    "125-81-05619": "D1공장",
    "403-85-07607": "D2공장",
    "403-85-23311": "D3공장",
    "125-81-32697": "P1공장",
    "403-85-15640": "P2공장",
    "844-85-00770": "P3공장",
    "118-85-07029": "P4공장",
    "125-81-51622": "일강1공장",
    "403-85-20895": "일강2공장",
    "421-86-02723": "유원",
    "125-81-54876": "세이프",
}


def clean_token(value):
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)
    return "" if text.lower() in {"br", "nbsp", "&nbsp;"} else text


def to_int(value):
    digits = re.sub(r"[^\d-]", "", str(value or ""))
    try:
        return int(digits or "0")
    except Exception:
        return 0


def safe_name(text, limit=30):
    text = unicodedata.normalize("NFKC", str(text or "")).strip()
    text = text.replace("㈜", "(주)")
    text = re.sub(r'[\\/:*?"<>|]+', " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^0-9A-Za-z가-힣()&._ -]+", "", text)
    text = text.strip(" ._-")
    return (text[:limit].strip() or "미상")


def site_from_biz_no(value):
    digits = re.sub(r"[^\d]", "", str(value or ""))
    if len(digits) != 10:
        return ""
    formatted = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    return FACTORY_MAP.get(formatted, "")


def dedupe_path(path):
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    idx = 1
    while True:
        candidate = path.with_name(f"{stem}_{idx}{suffix}")
        if not candidate.exists():
            return candidate
        idx += 1


def parse_pdf(pdf_path):
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        text = "\n".join(page.get_text() for page in doc)
    except Exception:
        text = ""
    if not text.strip():
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as pdf:
                text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        except Exception:
            text = ""

    text = unicodedata.normalize("NFKC", str(text or "")).replace("\xa0", " ")
    lines = [clean_token(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    joined = "\n".join(lines)
    flat = " ".join(lines)

    company_pattern = (
        r"(?:\(주\)|㈜|\(유\)|주식회사|유한회사)\s*[가-힣A-Za-z0-9&._-]{2,30}"
        r"|[가-힣A-Za-z0-9&._-]{2,30}\s*(?:\(주\)|㈜|\(유\))"
    )
    names = []
    for match in re.finditer(company_pattern, joined):
        name = clean_token(match.group(0))
        if name and name not in names:
            names.append(name)

    biz_nos = []
    for match in re.findall(r"\d{3}[-\s]?\d{2}[-\s]?\d{5}", flat):
        digits = re.sub(r"[^\d]", "", match)
        if digits and digits not in biz_nos:
            biz_nos.append(digits)

    buyer_biz_no = ""
    buyer_site = ""
    for digits in biz_nos:
        site = site_from_biz_no(digits)
        if site:
            buyer_biz_no = digits
            buyer_site = site
            break
    if not buyer_biz_no and len(biz_nos) >= 2:
        buyer_biz_no = biz_nos[1]

    issue_date = ""
    supply_amount = 0
    tax_amount = 0
    total_amount = 0
    amount_match = re.search(
        r"작성일자\s+공급가액\s+세\s*액.*?(20\d{2})[./년\s-]*(\d{1,2})[./월\s-]*(\d{1,2})\s+([0-9,]+)\s+([0-9,]+)",
        flat,
    )
    if amount_match:
        issue_date = f"{int(amount_match.group(1)):04d}{int(amount_match.group(2)):02d}{int(amount_match.group(3)):02d}"
        supply_amount = to_int(amount_match.group(4))
        tax_amount = to_int(amount_match.group(5))
        total_amount = supply_amount + tax_amount
    if not issue_date:
        m_date = re.search(r"작성일자.*?(20\d{2})[./년\s-]*(\d{1,2})[./월\s-]*(\d{1,2})", flat)
        if m_date:
            issue_date = f"{int(m_date.group(1)):04d}{int(m_date.group(2)):02d}{int(m_date.group(3)):02d}"
    total_match = re.search(r"합계금액.*?([0-9,]{4,})", flat)
    if total_match:
        total_amount = to_int(total_match.group(1)) or total_amount

    item_name = "세금계산서"
    for line in lines:
        if re.search(r"\d{1,2}\s+\d{1,2}\s+", line) and not line.startswith("20"):
            item_part = re.sub(r"^\d{1,2}\s+\d{1,2}\s+", "", line).strip()
            item_part = re.split(r"\s+[0-9,]{4,}", item_part)[0].strip()
            if item_part:
                item_name = item_part
                break

    return {
        "supplier_name": names[0] if len(names) >= 1 else "",
        "buyer_name": names[1] if len(names) >= 2 else "",
        "buyer_biz_no": buyer_biz_no,
        "buyer_site": buyer_site,
        "issue_date": issue_date,
        "total_amount": total_amount,
        "supply_amount": supply_amount,
        "tax_amount": tax_amount,
        "items": [{"name": item_name, "qty": 1, "inc_vat": total_amount, "account": "소모품비"}],
    }


def build_pdf_filename(parsed):
    year = parsed["issue_date"][:4] or time.strftime("%Y")
    month = parsed["issue_date"][4:6] or time.strftime("%m")
    buyer = safe_name(parsed["buyer_name"] or "법인명", 30)
    site = parsed.get("buyer_site") or site_from_biz_no(parsed.get("buyer_biz_no"))
    if site:
        buyer = f"{buyer}({safe_name(site, 20)})"
    supplier = safe_name(parsed["supplier_name"] or "업체명", 30)
    item = safe_name((parsed.get("items") or [{}])[0].get("name") or "세금계산서", 30)
    return f"세금계산서 - {supplier}({item})_{buyer}_{year}년 {month}월.pdf"


def patch_crawler_file():
    if not CRAWLER_FILE.exists():
        print(f"[PATCH] crawler not found: {CRAWLER_FILE}")
        return False
    text = CRAWLER_FILE.read_text(encoding="utf-8")
    approval_block = '''    def _handle_approval(self, driver) -> bool:
        """
        수신미승인 상태면 승인 처리를 진행하고,
        최종적으로 '인쇄' 버튼이 렌더링되었는지 확인합니다.
        """
        print(f"[{self.portal_name}] 수신승인 상태 확인")

        self._accept_smartbill_dialogs(driver, rounds=2)
        for _ in range(4):
            if self._is_print_button_present(driver):
                return True
            if self._click_smartbill_text(driver, "수신승인", exclude=("수신거부",)):
                print(f"[{self.portal_name}] 수신승인 버튼 클릭")
                time.sleep(0.8)
                # SmartBill shows two consecutive confirmations after approval.
                self._accept_smartbill_dialogs(driver, rounds=2, force_enter=True)
                time.sleep(1.0)
                self._accept_smartbill_dialogs(driver, rounds=2, force_enter=True)
                time.sleep(1.0)
                self._accept_smartbill_dialogs(driver, rounds=4, force_enter=True)
                time.sleep(1.0)
                continue
            time.sleep(1)

        for _ in range(15):
            if self._is_print_button_present(driver):
                return True
            self._accept_smartbill_dialogs(driver, rounds=1)
            time.sleep(0.5)
        return False

    def _click_smartbill_text(self, driver, text: str, exclude=()) -> bool:
        xpaths = [
            f"//*[normalize-space()='{text}']",
            f"//*[contains(normalize-space(),'{text}')]",
            f"//*[contains(@title,'{text}') or contains(@alt,'{text}') or contains(@value,'{text}')]",
        ]

        def scan_current_context():
            for xpath in xpaths:
                try:
                    elems = driver.find_elements(By.XPATH, xpath)
                except Exception:
                    continue
                for elem in elems:
                    try:
                        label = " ".join(
                            [
                                elem.text or "",
                                elem.get_attribute("title") or "",
                                elem.get_attribute("alt") or "",
                                elem.get_attribute("value") or "",
                            ]
                        )
                        if any(x in label for x in exclude):
                            continue
                        if not elem.is_displayed():
                            continue
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", elem)
                        return True
                    except Exception:
                        continue
            return False

        try:
            driver.switch_to.default_content()
            if scan_current_context():
                return True
            frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
            for frame in frames:
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                    if scan_current_context():
                        driver.switch_to.default_content()
                        return True
                except Exception:
                    continue
            driver.switch_to.default_content()
        except Exception:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
        return False

    def _accept_smartbill_dialogs(self, driver, rounds: int = 3, force_enter: bool = False) -> None:
        for _ in range(rounds):
            handled = False
            try:
                WebDriverWait(driver, 2).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                print(f"[{self.portal_name}] Alert 확인: {alert.text}")
                alert.accept()
                handled = True
                time.sleep(0.5)
            except Exception:
                pass
            if self._click_smartbill_text(driver, "확인"):
                handled = True
                time.sleep(0.5)
            if force_enter or not handled:
                try:
                    pyautogui.press("enter")
                    handled = True
                    time.sleep(1.0)
                except Exception:
                    pass
            if not handled:
                break

    def _is_print_button_present'''
    text, approval_count = re.subn(
        r"    def _handle_approval\(self, driver\) -> bool:.*?\n    def _is_print_button_present",
        lambda _m: approval_block,
        text,
        flags=re.S,
    )
    if approval_count != 1:
        print("[PATCH] approval block not replaced")

    new_block = '''    def _names_from_invoice_lines(self, lines: list[str]) -> list[str]:
        joined = "\\n".join(lines)
        corp_matches = []
        company_pattern = (
            r"(?:\\(주\\)|㈜|\\(유\\)|주식회사|유한회사)\\s*[가-힣A-Za-z0-9&._-]{2,30}"
            r"|[가-힣A-Za-z0-9&._-]{2,30}\\s*(?:\\(주\\)|㈜|\\(유\\))"
        )
        for match in re.finditer(company_pattern, joined):
            name = self._clean_token(match.group(0))
            name = re.sub(r"^(?:공|급|받|는|자)\\s+", "", name).strip()
            if self._is_bad_value(name):
                continue
            if name in {"(주)", "㈜", "(유)"}:
                continue
            if name not in corp_matches:
                corp_matches.append(name)
        if len(corp_matches) >= 2:
            return corp_matches[:2]

        names = []
        skip = {
            "상호", "상 호", "법인명", "(법인명)", "상호 (법인명)", "성명", "등록번호",
            "사업장", "주소", "업태", "종목", "종사업", "장번호", "공급자", "공급받는자",
        }
        for i, line in enumerate(lines):
            key = line.replace(" ", "")
            if key not in {"상호", "상호(법인명)"}:
                continue
            for candidate in lines[i + 1:i + 7]:
                ckey = candidate.replace(" ", "")
                if ckey in {s.replace(" ", "") for s in skip}:
                    continue
                if self._is_bad_value(candidate):
                    continue
                if candidate not in names:
                    names.append(candidate)
                    break
        return names

    @staticmethod
    def _is_better_parse'''
    patched, count = re.subn(
        r"    def _names_from_invoice_lines\(self, lines: list\[str\]\) -> list\[str\]:.*?\n    @staticmethod\n    def _is_better_parse",
        lambda _m: new_block,
        text,
        flags=re.S,
    )
    if count != 1:
        print("[PATCH] crawler block not replaced")
        return False
    backup = CRAWLER_FILE.with_suffix(f".backup_hotfix_{time.strftime('%Y%m%d_%H%M%S')}.py")
    CRAWLER_FILE.replace(backup)
    CRAWLER_FILE.write_text(patched, encoding="utf-8")
    print(f"[PATCH] crawler patched; backup={backup}")
    try:
        import py_compile
        py_compile.compile(str(CRAWLER_FILE), doraise=True)
        print("[PATCH] crawler py_compile OK")
    except Exception as exc:
        print(f"[PATCH] crawler py_compile FAILED: {exc!r}")
    return True


def repair_db_rows():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT id, subject, pdf_path, json_data FROM invoices ORDER BY id DESC LIMIT 100")
    rows = cur.fetchall()
    repaired = 0
    for row_id, subject, pdf_path, json_text in rows:
        try:
            payload = json.loads(json_text or "{}")
        except Exception:
            payload = {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        bad = (
            "공급자미상" in str(subject or "")
            or "사업장미상" in str(subject or "")
            or "공급자미상" in os.path.basename(str(pdf_path or ""))
            or not data.get("vendor_name")
            or not data.get("site_name")
            or not to_int(data.get("total_sum") or data.get("total_amount"))
        )
        if not bad:
            continue
        path = Path(pdf_path or "")
        if not path.exists():
            candidate = DOWNLOAD_DIR / os.path.basename(str(pdf_path or ""))
            path = candidate if candidate.exists() else path
        if not path.exists() or path.suffix.lower() != ".pdf":
            continue
        parsed = parse_pdf(path)
        if not (parsed["supplier_name"] and parsed["buyer_name"] and parsed["total_amount"]):
            print(f"[DB] skip id={row_id}: parse failed {parsed}")
            continue
        new_path = dedupe_path(path.with_name(build_pdf_filename(parsed)))
        if path.resolve() != new_path.resolve():
            path.replace(new_path)
        new_subject = f"[{parsed['buyer_name']}] {parsed['supplier_name']} 세금계산서 ({parsed['total_amount']:,}원)"
        payload["ok"] = True
        payload["portal"] = payload.get("portal") or "smartbill"
        payload["pdf_path"] = str(new_path)
        payload["subject"] = new_subject
        payload["invoice_type"] = "regular"
        fixed_data = dict(data)
        fixed_data.update({
            "vendor_name": parsed["supplier_name"],
            "supplier_name": parsed["supplier_name"],
            "site_name": parsed["buyer_site"] or parsed["buyer_name"],
            "buyer_name": parsed["buyer_name"],
            "buyer_biz_no": parsed["buyer_biz_no"],
            "business_no": parsed["buyer_biz_no"],
            "matched_biz_no": parsed["buyer_biz_no"],
            "target_supply": parsed["supply_amount"],
            "total_tax": parsed["tax_amount"],
            "total_sum": parsed["total_amount"],
            "total_amount": parsed["total_amount"],
            "invoice_date": parsed["issue_date"],
            "items": parsed["items"],
        })
        payload["data"] = fixed_data
        payload["_hotfix_repaired_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "UPDATE invoices SET subject=?, pdf_path=?, json_data=? WHERE id=?",
            (new_subject, str(new_path), json.dumps(payload, ensure_ascii=False), row_id),
        )
        conn.commit()
        repaired += 1
        print(f"[DB] repaired id={row_id}: {new_path.name}")
    conn.close()
    print(f"[DB] repaired rows={repaired}")


if __name__ == "__main__":
    patch_crawler_file()
    repair_db_rows()
    print("[DONE] Refresh manager list. Restart the server process once for future SmartBill mails.")
