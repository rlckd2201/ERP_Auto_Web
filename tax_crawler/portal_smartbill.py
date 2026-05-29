import base64
import re
import time
import unicodedata
from pathlib import Path
from typing import Optional

import pyautogui
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_handler import BaseTaxInvoiceHandler

class SmartBillHandler(BaseTaxInvoiceHandler):

    DOMAIN = "smartbill.co.kr"
    
    @property
    def portal_name(self) -> str:
        return "smartbill"

    def supports(self, url: str) -> bool:
        return "smartbill.co.kr/xdti/n_mem" in str(url or "").lower()

    def _do_process(self, driver, url, mail_text, mail_date, result):
        print(f"[{self.portal_name}] URL 접속: {url}")
        self._write_debug(None, f"handler_file={__file__}")
        driver.get(url)
        time.sleep(4)

        # 1. 팝업/광고 닫기 시도
        self._close_ads(driver)

        # 2. 수신승인 상태 확인 및 처리
        approved = self._handle_approval(driver)
        if not approved:
            result["error"] = "스마트빌 수신승인 처리 실패 및 인쇄 버튼을 찾을 수 없습니다."
            return
            
        time.sleep(2)
        
        # 3. 데이터 파싱
        try:
            parsed = self._parse_invoice_data(driver)
            supplier_name = parsed["supplier_name"]
            buyer_name = parsed["buyer_name"]
            buyer_biz_no = parsed["buyer_biz_no"]
            buyer_site = parsed["buyer_site"]
            issue_date = parsed["issue_date"] or mail_date
            total_amount = parsed["total_amount"]
            supply_amount = parsed.get("supply_amount", 0)
            tax_amount = parsed.get("tax_amount", 0)
            items = parsed["items"]
        except Exception as e:
            print(f"[{self.portal_name}] 데이터 파싱 실패: {e}")
            supplier_name = "공급자미상"
            buyer_name = "사업장미상"
            buyer_biz_no = ""
            buyer_site = ""
            issue_date = mail_date
            total_amount = 0
            supply_amount = 0
            tax_amount = 0
            items = []

        # 4. 파일명 생성
        first_item = items[0]["name"] if items else "세금계산서"
        extra = f"_외{len(items)-1}건" if len(items) > 1 else ""
        
        final_name = self.build_pdf_filename(
            issue_date=issue_date,
            buyer=buyer_name,
            supplier=supplier_name,
            item=first_item,
            extra=extra,
            amount=str(total_amount),
            buyer_biz_no=buyer_biz_no,
            buyer_site=buyer_site,
        )
        final_path = self.dedupe_path(self.download_dir / final_name)
        
        # 5. 인쇄창 호출 및 PDF 저장
        pdf_path = self._save_pdf(driver, final_path)
        if not pdf_path:
            result["error"] = "스마트빌 PDF 저장에 실패했습니다."
            return

        pdf_parsed = self._parse_pdf_invoice_data(pdf_path)
        self._write_debug(pdf_path, f"html_parse supplier={supplier_name} buyer={buyer_name} site={buyer_site} total={total_amount} item={(items[0]['name'] if items else '')}")
        self._write_debug(pdf_path, f"pdf_parse={pdf_parsed}")
        if self._is_better_parse(pdf_parsed, supplier_name, buyer_name, total_amount):
            supplier_name = pdf_parsed["supplier_name"] or supplier_name
            buyer_name = pdf_parsed["buyer_name"] or buyer_name
            buyer_biz_no = pdf_parsed["buyer_biz_no"] or buyer_biz_no
            buyer_site = pdf_parsed["buyer_site"] or buyer_site
            issue_date = pdf_parsed["issue_date"] or issue_date
            total_amount = pdf_parsed["total_amount"] or total_amount
            supply_amount = pdf_parsed.get("supply_amount", 0) or supply_amount
            tax_amount = pdf_parsed.get("tax_amount", 0) or tax_amount
            items = pdf_parsed["items"] or items

            fixed_name = self.build_pdf_filename(
                issue_date=issue_date,
                buyer=buyer_name,
                supplier=supplier_name,
                item=items[0]["name"] if items else "세금계산서",
                extra=f"_외{len(items)-1}건" if len(items) > 1 else "",
                amount=str(total_amount),
                buyer_biz_no=buyer_biz_no,
                buyer_site=buyer_site,
            )
            fixed_path = self.dedupe_path(self.download_dir / fixed_name)
            try:
                current_path = Path(pdf_path)
                if current_path.resolve() != fixed_path.resolve():
                    current_path.replace(fixed_path)
                    pdf_path = fixed_path
                    self._write_debug(pdf_path, f"renamed_to={fixed_path}")
            except Exception as e:
                print(f"[{self.portal_name}] PDF 이름 보정 실패: {e}")
                self._write_debug(pdf_path, f"rename_failed={e!r}")

        # 6. 최종 결과 반환
        result.update({
            "ok": True,
            "pdf_path": str(pdf_path),
            "subject": f"[{buyer_name}] {supplier_name} 세금계산서 ({total_amount:,}원)",
            "data": {
                "vendor_name": supplier_name,
                "site_name": buyer_site or self._site_name_from_biz_no(buyer_biz_no) or buyer_name,
                "business_no": buyer_biz_no,
                "matched_biz_no": buyer_biz_no,
                "target_supply": supply_amount,
                "total_tax": tax_amount,
                "total_sum": total_amount,
                "invoice_date": issue_date,
                "items": items,
            },
        })

    def _close_ads(self, driver):
        """화면을 가리는 광고(크레포트 등)를 닫습니다."""
        print(f"[{self.portal_name}] 광고 레이어 닫기 시도")
        try:
            # 보통 닫기 버튼은 특정 클래스나 텍스트를 가짐
            close_selectors = [
                ".btn_close", ".close", "[alt='닫기']", "[title='닫기']",
                "//*[contains(text(), '오늘 하루 보지 않기')]",
                "//*[contains(text(), '닫기')]"
            ]
            for sel in close_selectors:
                try:
                    if sel.startswith("//"):
                        elems = driver.find_elements(By.XPATH, sel)
                    else:
                        elems = driver.find_elements(By.CSS_SELECTOR, sel)
                    for elem in elems:
                        if elem.is_displayed():
                            driver.execute_script("arguments[0].click();", elem)
                            time.sleep(0.5)
                except Exception:
                    pass
        except Exception as e:
            print(f"[{self.portal_name}] 광고 닫기 중 오류 무시: {e}")

    def _handle_approval(self, driver) -> bool:
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

    def _is_print_button_present(self, driver) -> bool:
        selectors = [
            "//button[contains(.,'인쇄')]",
            "//a[contains(.,'인쇄')]",
            "//span[contains(.,'인쇄')]",
            "//*[contains(@title, '인쇄')]",
            "//*[contains(@alt, '인쇄')]",
            "//*[contains(@value, '인쇄')]"
        ]
        def check():
            for sel in selectors:
                try:
                    elems = driver.find_elements(By.XPATH, sel)
                    if any(e.is_displayed() for e in elems):
                        return True
                except Exception:
                    pass
            return False
            
        if check(): return True
        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
            for frame in frames:
                try:
                    driver.switch_to.frame(frame)
                    if check():
                        driver.switch_to.default_content()
                        return True
                    driver.switch_to.default_content()
                except Exception:
                    driver.switch_to.default_content()
        except Exception:
            pass
        return False

    def _parse_invoice_data(self, driver):
        """스마트빌 화면에서 공급자/공급받는자/사업자번호/금액을 추출합니다."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(driver.page_source, "html.parser")
        raw_tokens = list(soup.stripped_strings)
        tokens = [self._clean_token(t) for t in raw_tokens]
        tokens = [t for t in tokens if t]
        clean_text = " ".join(tokens)

        labels = {
            "상호", "상호(법인명)", "법인명", "성명", "대표자", "등록번호", "사업자등록번호",
            "사업장주소", "업태", "종목", "부서명", "담당자", "연락처", "휴대폰",
            "E-mail", "Email", "공급자", "공급받는자", "합계금액", "총금액", "품목",
        }
        name_labels = {"상호", "상호(법인명)", "법인명"}
        amount_labels = {"합계금액", "총금액"}
        item_labels = {"품목", "품목명"}

        names = []
        for i, token in enumerate(tokens):
            if token.replace(" ", "") not in {x.replace(" ", "") for x in name_labels}:
                continue
            value = self._next_value(tokens, i, labels)
            if value and value not in names:
                names.append(value)

        supplier_name = names[0] if len(names) >= 1 else "공급자미상"
        buyer_name = names[1] if len(names) >= 2 else "사업장미상"

        biz_nos = []
        for match in re.findall(r"\d{3}[-\s]?\d{2}[-\s]?\d{5}", clean_text):
            digits = self.digits_only(match)
            if digits and digits not in biz_nos:
                biz_nos.append(digits)

        buyer_biz_no = ""
        buyer_site = ""
        for digits in biz_nos:
            site = self._site_name_from_biz_no(digits)
            if site:
                buyer_biz_no = digits
                buyer_site = site
                break
        if not buyer_biz_no and len(biz_nos) >= 2:
            buyer_biz_no = biz_nos[1]

        total_amount = 0
        for i, token in enumerate(tokens):
            if token.replace(" ", "") not in {x.replace(" ", "") for x in amount_labels}:
                continue
            value = self._next_amount(tokens, i)
            if value:
                total_amount = value
                break
        if not total_amount:
            amounts = []
            for token in tokens:
                if "," not in token and len(self.digits_only(token)) == 10:
                    continue
                n = self._to_int(token)
                if 1000 <= n <= 999999999:
                    amounts.append(n)
            total_amount = max(amounts) if amounts else 0

        issue_date = ""
        m_date = re.search(r"(20\d{2})[.\-/년\s]*(\d{1,2})[.\-/월\s]*(\d{1,2})", clean_text)
        if m_date:
            issue_date = f"{int(m_date.group(1)):04d}{int(m_date.group(2)):02d}{int(m_date.group(3)):02d}"

        item_name = "세금계산서"
        for i, token in enumerate(tokens):
            if token.replace(" ", "") in item_labels:
                value = self._next_value(tokens, i, labels)
                if value:
                    item_name = value
                    break

        items = [{"name": item_name, "qty": 1, "inc_vat": total_amount, "account": "소모품비"}]
        return {
            "supplier_name": supplier_name,
            "buyer_name": buyer_name,
            "buyer_biz_no": buyer_biz_no,
            "buyer_site": buyer_site,
            "issue_date": issue_date,
            "total_amount": total_amount,
            "supply_amount": 0,
            "tax_amount": 0,
            "items": items,
        }

    def _parse_pdf_invoice_data(self, pdf_path) -> dict:
        text = ""
        errors = []
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            text = "\n".join(page.get_text() for page in doc)
        except Exception as e:
            errors.append(f"fitz={e!r}")
        if not text.strip():
            try:
                import pdfplumber
                with pdfplumber.open(str(pdf_path)) as pdf:
                    text = "\n".join((page.extract_text() or "") for page in pdf.pages)
            except Exception as e:
                errors.append(f"pdfplumber={e!r}")
        if not text.strip():
            print(f"[{self.portal_name}] PDF 텍스트 파싱 실패: {' | '.join(errors)}")
            self._write_debug(pdf_path, f"pdf_text_extract_failed errors={errors}")
            return {}
        self._write_debug(pdf_path, f"pdf_text_head={text[:1000]!r}")
        return self._parse_invoice_text(text)

    def _parse_invoice_text(self, text: str) -> dict:
        text = unicodedata.normalize("NFKC", str(text or "")).replace("\xa0", " ")
        lines = [self._clean_token(line) for line in text.splitlines()]
        lines = [line for line in lines if line]
        joined = "\n".join(lines)
        flat = " ".join(lines)

        biz_nos = []
        for match in re.findall(r"\d{3}[-\s]?\d{2}[-\s]?\d{5}", flat):
            digits = self.digits_only(match)
            if digits and digits not in biz_nos:
                biz_nos.append(digits)

        buyer_biz_no = ""
        buyer_site = ""
        for digits in biz_nos:
            site = self._site_name_from_biz_no(digits)
            if site:
                buyer_biz_no = digits
                buyer_site = site
                break
        if not buyer_biz_no and len(biz_nos) >= 2:
            buyer_biz_no = biz_nos[1]

        names = self._names_from_invoice_lines(lines)
        supplier_name = names[0] if len(names) >= 1 else ""
        buyer_name = names[1] if len(names) >= 2 else ""

        supply_amount = 0
        tax_amount = 0
        total_amount = 0
        amount_match = re.search(
            r"작성일자\s+공급가액\s+세\s*액.*?(20\d{2})[./년\s-]*(\d{1,2})[./월\s-]*(\d{1,2})\s+([0-9,]+)\s+([0-9,]+)",
            flat,
        )
        issue_date = ""
        if amount_match:
            issue_date = f"{int(amount_match.group(1)):04d}{int(amount_match.group(2)):02d}{int(amount_match.group(3)):02d}"
            supply_amount = self._to_int(amount_match.group(4))
            tax_amount = self._to_int(amount_match.group(5))
            total_amount = supply_amount + tax_amount
        if not issue_date:
            m_date = re.search(r"작성일자.*?(20\d{2})[./년\s-]*(\d{1,2})[./월\s-]*(\d{1,2})", flat)
            if m_date:
                issue_date = f"{int(m_date.group(1)):04d}{int(m_date.group(2)):02d}{int(m_date.group(3)):02d}"
        total_match = re.search(r"합계금액.*?([0-9,]{4,})", flat)
        if total_match:
            total_amount = self._to_int(total_match.group(1)) or total_amount
        if not total_amount:
            amounts = [self._to_int(v) for v in re.findall(r"[0-9][0-9,]{3,}", flat)]
            amounts = [v for v in amounts if 1000 <= v <= 999999999 and len(str(v)) != 10]
            total_amount = max(amounts) if amounts else 0

        item_name = "세금계산서"
        for line in lines:
            if re.search(r"\d{1,2}\s+\d{1,2}\s+", line) and not line.startswith("20"):
                item_part = re.sub(r"^\d{1,2}\s+\d{1,2}\s+", "", line).strip()
                item_part = re.split(r"\s+[0-9,]{4,}", item_part)[0].strip()
                if item_part:
                    item_name = item_part
                    break

        items = [{"name": item_name, "qty": 1, "inc_vat": total_amount, "account": "소모품비"}]
        return {
            "supplier_name": supplier_name,
            "buyer_name": buyer_name,
            "buyer_biz_no": buyer_biz_no,
            "buyer_site": buyer_site,
            "issue_date": issue_date,
            "total_amount": total_amount,
            "supply_amount": supply_amount,
            "tax_amount": tax_amount,
            "items": items,
        }

    def _names_from_invoice_lines(self, lines: list[str]) -> list[str]:
        joined = "\n".join(lines)
        corp_matches = []
        company_pattern = (
            r"(?:\(주\)|㈜|\(유\)|주식회사|유한회사)\s*[가-힣A-Za-z0-9&._-]{2,30}"
            r"|[가-힣A-Za-z0-9&._-]{2,30}\s*(?:\(주\)|㈜|\(유\))"
        )
        for match in re.finditer(company_pattern, joined):
            name = self._clean_token(match.group(0))
            name = re.sub(r"^(?:공|급|받|는|자)\s+", "", name).strip()
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
    def _is_better_parse(parsed: dict, supplier_name: str, buyer_name: str, total_amount: int) -> bool:
        if not parsed:
            return False
        parsed_good = bool(parsed.get("supplier_name") and parsed.get("buyer_name") and parsed.get("total_amount"))
        return parsed_good

    def _write_debug(self, pdf_path, text: str) -> None:
        try:
            base = Path(pdf_path).parent if pdf_path else self.download_dir
            debug_path = base / "_debug_smartbill_parse.txt"
            with open(debug_path, "a", encoding="utf-8") as f:
                f.write(time.strftime("[%Y-%m-%d %H:%M:%S] "))
                f.write(str(text))
                f.write("\n")
        except Exception:
            pass

    @staticmethod
    def _clean_token(value: str) -> str:
        text = unicodedata.normalize("NFKC", str(value or "")).strip()
        text = re.sub(r"\s+", " ", text)
        if text.lower() in {"br", "nbsp", "&nbsp;"}:
            return ""
        return text

    def _next_value(self, tokens: list[str], index: int, labels: set[str]) -> str:
        label_keys = {x.replace(" ", "") for x in labels}
        for candidate in tokens[index + 1:index + 9]:
            key = candidate.replace(" ", "")
            if key in label_keys:
                continue
            if self._is_bad_value(candidate):
                continue
            return candidate
        return ""

    def _next_amount(self, tokens: list[str], index: int) -> int:
        for candidate in tokens[index + 1:index + 8]:
            n = self._to_int(candidate)
            if n >= 1000:
                return n
        return 0

    def _is_bad_value(self, value: str) -> bool:
        text = str(value or "").strip()
        if not text or text.lower() == "br":
            return True
        if re.fullmatch(r"[\d,\-.\s]+", text):
            return True
        if "@" in text or "주소" in text or "연락처" in text:
            return True
        if len(text) > 50:
            return True
        return False

    @staticmethod
    def _to_int(value) -> int:
        digits = re.sub(r"[^\d-]", "", str(value or ""))
        try:
            return int(digits or "0")
        except Exception:
            return 0

    def _save_pdf(self, driver, final_path: Path) -> Optional[Path]:
        """
        인쇄 버튼을 누른 후, 새 창으로 뜨는 인쇄 미리보기 페이지에서
        크롬 네이티브 인쇄 다이얼로그를 우회하여 driver.print_page()로 직접 PDF를 생성합니다.
        (프린터 설정 무관, 가장 빠르고 안정적인 최신 방식)
        """
        print(f"[{self.portal_name}] 인쇄 버튼 클릭")
        windows_before = len(driver.window_handles)
        
        selectors = [
            "//button[contains(.,'인쇄')]",
            "//a[contains(.,'인쇄')]",
            "//span[contains(.,'인쇄')]",
            "//*[contains(@title, '인쇄')]",
            "//*[contains(@alt, '인쇄')]",
            "//*[contains(@value, '인쇄')]"
        ]
        
        clicked = False
        def attempt_click():
            for sel in selectors:
                try:
                    elems = driver.find_elements(By.XPATH, sel)
                    for elem in elems:
                        if elem.is_displayed():
                            driver.execute_script("arguments[0].click();", elem)
                            return True
                except Exception:
                    pass
            return False

        if attempt_click():
            clicked = True
        else:
            try:
                frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
                for frame in frames:
                    try:
                        driver.switch_to.frame(frame)
                        if attempt_click():
                            clicked = True
                            driver.switch_to.default_content()
                            break
                        driver.switch_to.default_content()
                    except Exception:
                        driver.switch_to.default_content()
            except Exception:
                pass
                
        if not clicked:
            print(f"[{self.portal_name}] 인쇄 버튼 클릭 실패")
            return None
        
        # 새 창(팝업) 대기
        try:
            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > windows_before)
        except Exception as e:
            print(f"[{self.portal_name}] 인쇄 팝업 창을 기다리다 시간 초과: {e}")
            return None
            
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(3) # 미리보기 로딩 대기
        
        # 페이지 로딩과 동시에 window.print()가 호출되어 크롬 인쇄 다이얼로그가 떠 있을 수 있습니다.
        # 인쇄 다이얼로그가 열려 있으면 driver.print_page()가 블록되므로 ESC를 눌러 닫아줍니다.
        print(f"[{self.portal_name}] 크롬 인쇄 다이얼로그 닫기 (ESC)")
        for _ in range(3):
            pyautogui.press('esc')
            time.sleep(0.5)
            
        print(f"[{self.portal_name}] 내부 print_page() 호출하여 PDF 생성 중...")
        try:
            pdf_base64 = driver.print_page()
            final_path.parent.mkdir(parents=True, exist_ok=True)
            with open(final_path, "wb") as f:
                f.write(base64.b64decode(pdf_base64))
            print(f"[{self.portal_name}] PDF 저장 완료: {final_path}")
            
            # 팝업 닫고 원래 창으로 복귀
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            return final_path
        except Exception as e:
            print(f"[{self.portal_name}] print_page() 실패: {e}")
            return None
def _smartbill_bottom_print_save_pdf(self, driver, final_path):
    """SmartBill: open preview URL, scroll to the bottom, click the actual bottom print button."""
    preview_url = "https://www2.smartbill.co.kr/xDti/n_mem/dti_prev.aspx?Caller=N_MEM_02"
    print(f"[{self.portal_name}] SMARTBILL_BOTTOM_PRINT_V1")
    print(f"[{self.portal_name}] 미리보기 URL 접속: {preview_url}")

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    try:
        WebDriverWait(driver, 1).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        print(f"[{self.portal_name}] 기존 Alert 닫기: {alert.text}")
        alert.accept()
        time.sleep(0.5)
    except Exception:
        pass

    driver.get(preview_url)
    try:
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    time.sleep(2)

    def scroll_to_bottom():
        last_y = -1
        for _ in range(18):
            y = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop || 0")
            if y == last_y:
                break
            last_y = y
            driver.execute_script("window.scrollBy(0, Math.max(window.innerHeight * 0.85, 700));")
            time.sleep(0.25)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.7)

    def find_print_candidates():
        script = """
        const nodes = Array.from(document.querySelectorAll('input,button,a,span,img,div'));
        const rows = [];
        for (const el of nodes) {
          const label = [
            el.innerText || '',
            el.value || '',
            el.title || '',
            el.alt || '',
            el.getAttribute('onclick') || ''
          ].join(' ').replace(/\\s+/g, ' ').trim();
          if (!label.includes('인쇄')) continue;
          if (label.includes('스마트') || label.toUpperCase().includes('XML') || label.includes('목록')) continue;
          const style = window.getComputedStyle(el);
          if (style.display === 'none' || style.visibility === 'hidden') continue;
          const rect = el.getBoundingClientRect();
          if (rect.width <= 0 || rect.height <= 0) continue;
          rows.push({ el, y: rect.top + window.pageYOffset, label });
        }
        rows.sort((a, b) => b.y - a.y);
        return rows.map(r => r.el);
        """
        try:
            return driver.execute_script(script) or []
        except Exception:
            return []

    def click_bottom_print_button():
        scroll_to_bottom()
        candidates = find_print_candidates()
        print(f"[{self.portal_name}] 인쇄 버튼 후보 수: {len(candidates)}")
        for elem in candidates[:8]:
            try:
                label = " ".join([
                    elem.text or "",
                    elem.get_attribute("value") or "",
                    elem.get_attribute("title") or "",
                    elem.get_attribute("alt") or "",
                    elem.get_attribute("onclick") or "",
                ]).strip()
                print(f"[{self.portal_name}] 인쇄 후보 클릭 시도: {label[:80]}")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                time.sleep(0.3)
                try:
                    elem.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", elem)
                return True
            except Exception as e:
                print(f"[{self.portal_name}] 인쇄 후보 클릭 실패: {e}")
        return False

    if not click_bottom_print_button():
        print(f"[{self.portal_name}] 하단 인쇄 버튼을 찾지 못했습니다.")
        return None

    time.sleep(1.5)
    print(f"[{self.portal_name}] 크롬 인쇄 다이얼로그 닫기 (ESC)")
    for _ in range(3):
        try:
            pyautogui.press("esc")
        except Exception:
            pass
        time.sleep(0.5)

    print(f"[{self.portal_name}] 내부 print_page() 호출하여 PDF 생성 중...")
    try:
        pdf_base64 = driver.print_page()
        final_path.parent.mkdir(parents=True, exist_ok=True)
        with open(final_path, "wb") as f:
            f.write(base64.b64decode(pdf_base64))
        print(f"[{self.portal_name}] PDF 저장 완료: {final_path}")
        return final_path
    except Exception as e:
        print(f"[{self.portal_name}] print_page() 실패: {e}")
        return None


SmartBillHandler._save_pdf = _smartbill_bottom_print_save_pdf


def _smartbill_ibtn_print_save_pdf(self, driver, final_path):
    """SmartBill preview print flow using the confirmed ibtnPrint element."""
    preview_url = "https://www2.smartbill.co.kr/xDti/n_mem/dti_prev.aspx?Caller=N_MEM_02"
    print(f"[{self.portal_name}] SMARTBILL_IBTN_PRINT_V1")
    print(f"[{self.portal_name}] 미리보기 URL 접속: {preview_url}")

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    try:
        WebDriverWait(driver, 1).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        print(f"[{self.portal_name}] 기존 Alert 닫기: {alert.text}")
        alert.accept()
        time.sleep(0.5)
    except Exception:
        pass

    driver.get(preview_url)
    try:
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    time.sleep(2)

    print(f"[{self.portal_name}] ibtnPrint 버튼 클릭")
    btn = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, "ibtnPrint"))
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", btn)
    time.sleep(1.5)

    print(f"[{self.portal_name}] 크롬 인쇄 다이얼로그 닫기 (ESC)")
    for _ in range(3):
        try:
            pyautogui.press("esc")
        except Exception:
            pass
        time.sleep(0.5)

    print(f"[{self.portal_name}] 내부 print_page() 호출하여 PDF 생성 중...")
    try:
        pdf_base64 = driver.print_page()
        final_path.parent.mkdir(parents=True, exist_ok=True)
        with open(final_path, "wb") as f:
            f.write(base64.b64decode(pdf_base64))
        print(f"[{self.portal_name}] PDF 저장 완료: {final_path}")
        return final_path
    except Exception as e:
        print(f"[{self.portal_name}] print_page() 실패: {e}")
        return None


SmartBillHandler._save_pdf = _smartbill_ibtn_print_save_pdf


def _smartbill_prt_prev_save_pdf(self, driver, final_path):
    """SmartBill print flow fixed to the confirmed fnPrint/prt_prev.aspx path."""
    dti_prev_url = "https://www2.smartbill.co.kr/xDti/n_mem/dti_prev.aspx?Caller=N_MEM_02"
    prt_prev_url = "https://www2.smartbill.co.kr/xDTI/arap_repo/common/prt_prev.aspx"

    def wait_ready(seconds=15):
        try:
            WebDriverWait(driver, seconds).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

    def close_alert_by_dismiss():
        try:
            WebDriverWait(driver, 1).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            print(f"[{self.portal_name}] alert dismiss: {alert.text[:120]}")
            alert.dismiss()
            time.sleep(0.5)
            return True
        except Exception:
            try:
                pyautogui.press("esc")
            except Exception:
                pass
            return False

    def print_current_page():
        print(f"[{self.portal_name}] print_page() pdf create")
        pdf_base64 = driver.print_page()
        final_path.parent.mkdir(parents=True, exist_ok=True)
        with open(final_path, "wb") as f:
            f.write(base64.b64decode(pdf_base64))
        print(f"[{self.portal_name}] PDF saved: {final_path}")
        return final_path

    print(f"[{self.portal_name}] SMARTBILL_PRT_PREV_V2")
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    close_alert_by_dismiss()
    print(f"[{self.portal_name}] dti_prev open: {dti_prev_url}")
    driver.get(dti_prev_url)
    wait_ready(20)
    time.sleep(1.5)
    close_alert_by_dismiss()

    current_url = (driver.current_url or "")
    print(f"[{self.portal_name}] current after dti_prev: {current_url}")

    if "dti_prev.aspx" in current_url.lower():
        try:
            has_fn_print = driver.execute_script("return typeof fnPrint === 'function';")
        except Exception:
            has_fn_print = False

        if has_fn_print:
            before_handles = list(driver.window_handles)
            print(f"[{self.portal_name}] fnPrint() call")
            driver.execute_script("fnPrint();")
            time.sleep(1.5)
            close_alert_by_dismiss()

            try:
                WebDriverWait(driver, 6).until(
                    lambda d: "prt_prev.aspx" in (d.current_url or "").lower()
                    or len(d.window_handles) > len(before_handles)
                )
            except Exception:
                pass

            try:
                handles = list(driver.window_handles)
                if len(handles) > len(before_handles):
                    driver.switch_to.window(handles[-1])
                    wait_ready(10)
                    print(f"[{self.portal_name}] switched print window: {driver.current_url}")
            except Exception:
                pass
        else:
            print(f"[{self.portal_name}] fnPrint not found on dti_prev")

    current_url = (driver.current_url or "")
    if "prt_prev.aspx" not in current_url.lower():
        print(f"[{self.portal_name}] prt_prev direct open: {prt_prev_url}")
        driver.get(prt_prev_url)
        wait_ready(20)
        time.sleep(1.5)
        close_alert_by_dismiss()

    current_url = (driver.current_url or "")
    print(f"[{self.portal_name}] current before pdf: {current_url}")
    if "prt_prev.aspx" not in current_url.lower():
        print(f"[{self.portal_name}] SmartBill print page not reached")
        return None

    for _ in range(3):
        try:
            pyautogui.press("esc")
        except Exception:
            pass
        time.sleep(0.3)

    try:
        return print_current_page()
    except Exception as e:
        print(f"[{self.portal_name}] print_page failed: {e}")
        return None


SmartBillHandler._save_pdf = _smartbill_prt_prev_save_pdf


def _smartbill_current_ibtn_window_save_pdf(self, driver, final_path):
    """Click the real SmartBill print button on the current invoice page.

    SmartBill opens /xDTI/arap_repo/common/prt_prev.aspx in a new window from
    ibtnPrint/fnPrint(). Do not navigate to dti_prev.aspx here.
    """

    def wait_ready(seconds=12):
        try:
            WebDriverWait(driver, seconds).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

    def dismiss_js_alert():
        try:
            WebDriverWait(driver, 1).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            print(f"[{self.portal_name}] alert dismiss: {alert.text[:120]}")
            alert.dismiss()
            time.sleep(0.5)
            return True
        except Exception:
            return False

    def click_print_in_current_context():
        selectors = [
            (By.ID, "ibtnPrint"),
            (By.CSS_SELECTOR, "#ibtnPrint"),
            (By.CSS_SELECTOR, "img#ibtnPrint"),
            (By.CSS_SELECTOR, "img[onclick*='fnPrint']"),
            (By.CSS_SELECTOR, "*[onclick*='fnPrint']"),
            (By.CSS_SELECTOR, "img[src*='btn_print']"),
            (By.XPATH, "//*[@id='ibtnPrint' or contains(@onclick,'fnPrint') or contains(@src,'btn_print') or @alt='인쇄']"),
        ]
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        except Exception:
            pass

        for by, value in selectors:
            try:
                elems = driver.find_elements(by, value)
            except Exception:
                continue
            for elem in elems:
                try:
                    tag = elem.tag_name
                    elem_id = elem.get_attribute("id") or ""
                    onclick = elem.get_attribute("onclick") or ""
                    src = elem.get_attribute("src") or ""
                    alt = elem.get_attribute("alt") or ""
                    print(f"[{self.portal_name}] print candidate: tag={tag} id={elem_id} alt={alt} onclick={onclick[:80]} src={src[-80:]}")
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", elem)
                    return True
                except Exception as e:
                    print(f"[{self.portal_name}] print candidate click failed: {e}")
                    continue
        return False

    def click_print_button():
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

        if click_print_in_current_context():
            return True

        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
        except Exception:
            frames = []

        for idx, frame in enumerate(frames):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                print(f"[{self.portal_name}] scan frame for ibtnPrint: {idx}")
                if click_print_in_current_context():
                    driver.switch_to.default_content()
                    return True
            except Exception as e:
                print(f"[{self.portal_name}] frame scan failed: {idx} {e}")
            finally:
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
        return False

    print(f"[{self.portal_name}] SMARTBILL_CURRENT_IBTN_WINDOW_V3")
    wait_ready(15)
    time.sleep(1)
    dismiss_js_alert()

    try:
        main_handle = driver.current_window_handle
    except Exception:
        main_handle = None
    before_handles = list(driver.window_handles)
    print(f"[{self.portal_name}] current before print click: {driver.current_url}")
    print(f"[{self.portal_name}] window handles before: {len(before_handles)}")

    if not click_print_button():
        print(f"[{self.portal_name}] ibtnPrint/fnPrint button not found on current page")
        return None

    print(f"[{self.portal_name}] ibtnPrint clicked, wait new print window")
    time.sleep(1)
    dismiss_js_alert()

    try:
        WebDriverWait(driver, 15).until(
            lambda d: len(d.window_handles) > len(before_handles)
            or "prt_prev.aspx" in (d.current_url or "").lower()
        )
    except Exception as e:
        print(f"[{self.portal_name}] print window wait timeout: {e}")

    try:
        handles = list(driver.window_handles)
        print(f"[{self.portal_name}] window handles after: {len(handles)}")
        new_handles = [h for h in handles if h not in before_handles]
        if new_handles:
            driver.switch_to.window(new_handles[-1])
            wait_ready(15)
            time.sleep(2)
            print(f"[{self.portal_name}] switched to print window: {driver.current_url}")
        elif "prt_prev.aspx" not in (driver.current_url or "").lower():
            print(f"[{self.portal_name}] print preview window did not open")
            return None
    except Exception as e:
        print(f"[{self.portal_name}] switch print window failed: {e}")
        return None

    if "prt_prev.aspx" not in (driver.current_url or "").lower():
        print(f"[{self.portal_name}] current window is not prt_prev.aspx: {driver.current_url}")
        return None

    print(f"[{self.portal_name}] close Chrome print dialog if opened")
    for _ in range(3):
        try:
            pyautogui.press("esc")
        except Exception:
            pass
        time.sleep(0.5)

    try:
        print(f"[{self.portal_name}] print_page() pdf create")
        pdf_base64 = driver.print_page()
        final_path.parent.mkdir(parents=True, exist_ok=True)
        with open(final_path, "wb") as f:
            f.write(base64.b64decode(pdf_base64))
        print(f"[{self.portal_name}] PDF saved: {final_path}")

        try:
            if main_handle and driver.current_window_handle != main_handle:
                driver.close()
                driver.switch_to.window(main_handle)
        except Exception:
            pass
        return final_path
    except Exception as e:
        print(f"[{self.portal_name}] print_page failed: {e}")
        return None


SmartBillHandler._save_pdf = _smartbill_current_ibtn_window_save_pdf


def _smartbill_form_post_print_save_pdf(self, driver, final_path):
    """SmartBill print flow based on the actual HTML fnPrint() logic.

    The print button does not just open a URL. It sets hdnCheckedIds and posts
    document.forms[0] to /xDTI/arap_repo/common/prt_prev.aspx in a new DTIPrint
    window. Keep that behavior intact.
    """

    def wait_ready(seconds=15):
        try:
            WebDriverWait(driver, seconds).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

    def close_alert():
        try:
            WebDriverWait(driver, 1).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            print(f"[{self.portal_name}] alert dismiss: {alert.text[:120]}")
            alert.dismiss()
            time.sleep(0.5)
            return True
        except Exception:
            return False

    def wait_and_switch_print_window(before_handles):
        try:
            WebDriverWait(driver, 20).until(
                lambda d: len(d.window_handles) > len(before_handles)
                or "prt_prev.aspx" in (d.current_url or "").lower()
            )
        except Exception as e:
            print(f"[{self.portal_name}] DTIPrint window wait timeout: {e}")

        handles = list(driver.window_handles)
        new_handles = [h for h in handles if h not in before_handles]
        if new_handles:
            driver.switch_to.window(new_handles[-1])
        wait_ready(20)
        time.sleep(2)
        print(f"[{self.portal_name}] print window url: {driver.current_url}")
        return "prt_prev.aspx" in (driver.current_url or "").lower()

    def click_ibtn_print():
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

        for selector in ("#ibtnPrint", "img#ibtnPrint", "img[onclick*='fnPrint']", "*[onclick*='fnPrint']"):
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, selector)
            except Exception:
                continue
            for elem in elems:
                try:
                    print(f"[{self.portal_name}] click ibtnPrint selector={selector} onclick={(elem.get_attribute('onclick') or '')[:80]}")
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                    time.sleep(0.3)
                    try:
                        elem.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", elem)
                    return True
                except Exception as e:
                    print(f"[{self.portal_name}] ibtnPrint click failed: {e}")
        return False

    def submit_print_form_exactly():
        script = r"""
        const form = document.forms[0];
        if (!form) return {ok:false, reason:"form not found"};

        const scriptText = Array.from(document.scripts).map(s => s.textContent || "").join("\n");
        const pick = (name, fallback) => {
          const re = new RegExp("var\\s+" + name + "\\s*=\\s*'([^']*)'", "i");
          const m = scriptText.match(re);
          return m ? m[1] : fallback;
        };

        const dtiid = pick("dtiid", "");
        const arap = pick("arap", "AP");
        const statusNode = document.getElementById("hdndtistatus");
        const status = statusNode ? statusNode.value : pick("status", "C");
        const dtiType = pick("dtiType", "T");
        const dtiDocType = pick("dtiDocType", "");
        const dtiWday = pick("dtiWday", "");
        const BrkDtiYn = pick("BrkDtiYn", "N");

        if (!dtiid || !dtiWday) {
          return {ok:false, reason:"dtiid/dtiWday not found", dtiid, dtiWday};
        }

        let checked = document.getElementById("hdnCheckedIds") || form.elements["hdnCheckedIds"];
        if (!checked) {
          checked = document.createElement("input");
          checked.type = "hidden";
          checked.name = "hdnCheckedIds";
          checked.id = "hdnCheckedIds";
          form.appendChild(checked);
        }
        checked.value = dtiid + ";" + dtiWday + ";" + status + ";" + dtiType + ";" + arap + ";" + dtiDocType + ";" + BrkDtiYn + ";";

        const action = "/xDTI/arap_repo/common/prt_prev.aspx";
        window.open("", "DTIPrint", "width=675,height=640,scrollbars=yes,resizable=yes");
        form.target = "DTIPrint";
        form.action = action;
        form.method = "post";
        form.submit();
        return {ok:true, checked:checked.value, action};
        """
        try:
            result = driver.execute_script(script)
            print(f"[{self.portal_name}] exact form submit result: {result}")
            return bool(result and result.get("ok"))
        except Exception as e:
            print(f"[{self.portal_name}] exact form submit failed: {e}")
            return False

    print(f"[{self.portal_name}] SMARTBILL_FORM_POST_PRINT_V4")
    wait_ready(20)
    time.sleep(1)
    close_alert()

    try:
        main_handle = driver.current_window_handle
    except Exception:
        main_handle = None

    print(f"[{self.portal_name}] current before SmartBill print: {driver.current_url}")
    before_handles = list(driver.window_handles)

    clicked = click_ibtn_print()
    if clicked:
        print(f"[{self.portal_name}] ibtnPrint clicked")
        time.sleep(1)
        close_alert()
        if not wait_and_switch_print_window(before_handles):
            print(f"[{self.portal_name}] click did not reach prt_prev, fallback to exact form POST")
            try:
                if main_handle:
                    driver.switch_to.window(main_handle)
            except Exception:
                pass
            before_handles = list(driver.window_handles)
            if not submit_print_form_exactly():
                return None
            if not wait_and_switch_print_window(before_handles):
                return None
    else:
        print(f"[{self.portal_name}] ibtnPrint not clicked, exact form POST")
        if not submit_print_form_exactly():
            return None
        if not wait_and_switch_print_window(before_handles):
            return None

    if "prt_prev.aspx" not in (driver.current_url or "").lower():
        print(f"[{self.portal_name}] not on SmartBill print preview: {driver.current_url}")
        return None

    print(f"[{self.portal_name}] close Chrome print dialog if opened")
    for _ in range(3):
        try:
            pyautogui.press("esc")
        except Exception:
            pass
        time.sleep(0.5)

    try:
        print(f"[{self.portal_name}] print_page() pdf create")
        pdf_base64 = driver.print_page()
        final_path.parent.mkdir(parents=True, exist_ok=True)
        with open(final_path, "wb") as f:
            f.write(base64.b64decode(pdf_base64))
        print(f"[{self.portal_name}] PDF saved: {final_path}")
        try:
            if main_handle and driver.current_window_handle != main_handle:
                driver.close()
                driver.switch_to.window(main_handle)
        except Exception:
            pass
        return final_path
    except Exception as e:
        print(f"[{self.portal_name}] print_page failed: {e}")
        return None


SmartBillHandler._save_pdf = _smartbill_form_post_print_save_pdf
