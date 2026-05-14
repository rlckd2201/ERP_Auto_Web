"""
SMILE EDI tax invoice crawler prototype.

This module is intentionally not registered in crawler_main.py yet.  It can be
tested directly, and approval is opt-in because SMILE EDI approval cannot be
rolled back to an unapproved state.
"""
import argparse
import html
import json
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_handler import BaseTaxInvoiceHandler


class SmileEdiHandler(BaseTaxInvoiceHandler):
    DOMAIN = "smileedi.com"
    PATH_HINT = "/DtiEmail.do"

    def __init__(
        self,
        config_path: Optional[Path] = None,
        approve_on_unapproved: bool = False,
        keep_browser_open: bool = False,
    ):
        super().__init__(config_path=config_path)
        self.approve_on_unapproved = approve_on_unapproved
        self.keep_browser_open = keep_browser_open

    @property
    def portal_name(self) -> str:
        return "smileedi"

    def supports(self, url: str) -> bool:
        parsed = urlparse(str(url or ""))
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        return self.DOMAIN in host and path.endswith(self.PATH_HINT.lower())

    def process(self, url: str, mail_text: str = "", mail_date: str = "", mail_subject: str = "") -> dict:
        if not mail_date:
            mail_date = time.strftime("%y%m%d")
        result = {
            "ok": False,
            "portal": self.portal_name,
            "pdf_path": None,
            "subject": "",
            "data": {},
            "approval": {},
            "error": None,
        }
        self._mail_subject = str(mail_subject or "")
        driver = self._build_driver()
        try:
            self._do_process(driver, url, mail_text, mail_date, result)
        except Exception as exc:
            result["error"] = str(exc)
        finally:
            if self.keep_browser_open:
                result["browser_left_open"] = True
            else:
                try:
                    driver.quit()
                except Exception:
                    pass
        return result

    def _do_process(self, driver: WebDriver, url: str, mail_text: str, mail_date: str, result: dict) -> None:
        dump_dir = self._make_debug_dir(mail_date)
        result["debug_dir"] = str(dump_dir)

        candidates = self.build_candidate_nos(mail_text)
        mail_summary = self._parse_mail_summary(mail_text)
        self._write_text(
            dump_dir / "00_input.json",
            json.dumps(
                {
                    "url": url,
                    "mail_date": mail_date,
                    "mail_subject": self._mail_subject,
                    "candidates": self._candidate_debug(candidates),
                    "mail_summary": mail_summary,
                    "approve_on_unapproved": self.approve_on_unapproved,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

        if not candidates:
            result["error"] = "SMILE EDI 메일 본문에서 대승/대승정밀/일강 등 법인 후보를 찾지 못했습니다."
            return

        driver.get(url)
        self._switch_to_latest_window(driver)
        self._wait_document_ready(driver, timeout=12)
        time.sleep(1.0)
        self._dump_state(driver, dump_dir, "01_before_auth")

        matched_key = self._auth_with_business_numbers(driver, candidates, dump_dir)
        if not matched_key:
            self._dump_state(driver, dump_dir, "02_auth_failed")
            result["error"] = "SMILE EDI 사업자번호 인증에 실패했습니다."
            return

        matched_biz_no = candidates.get(matched_key, "")
        time.sleep(1.0)
        self._switch_to_latest_window(driver)
        self._wait_document_ready(driver, timeout=12)
        self._dump_state(driver, dump_dir, "03_after_auth")

        page_summary = self._parse_invoice_page(driver)
        parsed = {**mail_summary, **{k: v for k, v in page_summary.items() if v not in ("", None, [])}}
        approval = self._handle_approval(driver, dump_dir)
        self._dump_state(driver, dump_dir, "04_after_approval_check")

        result.update(
            {
                "ok": True,
                "subject": self._build_subject(parsed),
                "data": self._build_data(parsed, matched_biz_no),
                "approval": approval,
                "matched_biz_key": matched_key,
                "matched_biz_no": matched_biz_no,
                "matched_site_name": self._site_name_from_biz_no(matched_biz_no),
            }
        )

    # ------------------------------------------------------------------
    # Auth / navigation
    # ------------------------------------------------------------------
    def _auth_with_business_numbers(
        self,
        driver: WebDriver,
        candidates: dict[str, str],
        dump_dir: Path,
    ) -> str | None:
        if self._find_business_no_input(driver) is None and self._is_invoice_view_ready(driver):
            return "already_open"

        for index, (key, biz_no) in enumerate(candidates.items(), start=1):
            try:
                self._write_text(
                    dump_dir / f"02_auth_try_{index}.txt",
                    f"{key} {biz_no} {self._site_name_from_biz_no(biz_no)}\n",
                )
                input_el = self._find_business_no_input(driver)
                if input_el is None:
                    if self._is_invoice_view_ready(driver):
                        return key
                    return None

                input_el.clear()
                input_el.send_keys(biz_no)
                time.sleep(0.2)

                if not self._click_confirm(driver):
                    input_el.send_keys(Keys.RETURN)
                time.sleep(1.2)
                self._accept_alerts(driver, timeout=1.0)
                self._switch_to_latest_window(driver)
                self._wait_document_ready(driver, timeout=8)

                if self._has_terminal_error_text(driver):
                    return None
                if self._is_invoice_view_ready(driver):
                    return key
                if self._find_business_no_input(driver) is None:
                    return key
                if self._has_auth_failure_text(driver):
                    self._accept_alerts(driver, timeout=1.0)
                    continue
            except Exception as exc:
                self._write_text(dump_dir / f"02_auth_try_{index}_error.txt", repr(exc))
                continue
        return None

    def _find_business_no_input(self, driver: WebDriver) -> WebElement | None:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

        selectors = (
            "form[name='LoginForm'] input[name='inpasswd']",
            "form[name='LoginForm'] input#input.passwd_input",
            "input[name='inpasswd']",
            "input#input.passwd_input",
        )
        for selector in selectors:
            for elem in driver.find_elements(By.CSS_SELECTOR, selector):
                if self._is_editable_visible(elem):
                    return elem

        text = self._visible_text(driver)
        auth_markers = (
            "사업자번호를 입력 후 전자(세금)계산서를 확인",
            "사업자번호를 입력하세요",
        )
        if not any(marker in text for marker in auth_markers):
            return None

        for elem in driver.find_elements(By.CSS_SELECTOR, "form[name='LoginForm'] input"):
            if self._is_editable_visible(elem):
                return elem
        return None

    def _click_confirm(self, driver: WebDriver) -> bool:
        xpaths = [
            "//*[self::a or self::button or self::input][contains(@href,'Login') or contains(@onclick,'Login')]",
            "//*[self::button or self::a or self::input][normalize-space(.)='확인']",
            "//*[self::button or self::a or self::input][contains(normalize-space(.),'확인')]",
            "//input[contains(@value,'확인')]",
            "//*[contains(@onclick,'submit') or contains(@onclick,'Submit')]",
        ]
        return self._click_first(driver, xpaths, timeout=4)

    def _is_invoice_view_ready(self, driver: WebDriver) -> bool:
        text = self._visible_text(driver)
        auth_markers = (
            "사업자번호를 입력 후 전자(세금)계산서를 확인",
            "사업자번호를 입력하세요",
            "담당자가 아닌 경우 본 이메일을 삭제",
            "신규회원 혜택서비스",
        )
        if any(marker in text for marker in auth_markers):
            return False
        if self._find_business_no_input(driver) is not None:
            return False
        if "전자세금계산서" not in text and "전자(세금)계산서" not in text:
            return False
        ready_markers = (
            "XML저장",
            "XML 저장",
            "반송사유",
            "승인번호",
            "일련번호",
            "미승인 전자",
            "공급받는자 담당자",
            "인쇄",
        )
        return any(marker in text for marker in ready_markers)

    def _has_auth_failure_text(self, driver: WebDriver) -> bool:
        text = self._visible_text(driver)
        failure_markers = (
            "일치하지",
            "올바르지",
            "확인할 수 없",
            "존재하지",
            "잘못",
            "사업자번호를 입력",
        )
        return any(marker in text for marker in failure_markers)

    def _has_terminal_error_text(self, driver: WebDriver) -> bool:
        text = self._visible_text(driver)
        fatal_markers = (
            "전송타입 오류",
            "문제가 계속될 경우 SmileEDI 담당 운영관리자",
        )
        return any(marker in text for marker in fatal_markers)

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------
    def _handle_approval(self, driver: WebDriver, dump_dir: Path) -> dict:
        before = self._approval_state(driver)
        info = {
            "initial_state": before,
            "needed": before == "unapproved",
            "attempted": False,
            "approved": before == "approved",
            "dry_run": not self.approve_on_unapproved,
        }
        self._write_text(dump_dir / "04_approval_before.json", json.dumps(info, ensure_ascii=False, indent=2))

        if before != "unapproved":
            return info
        if not self.approve_on_unapproved:
            info["message"] = "미승인 계산서 감지. 승인 버튼은 --approve 옵션이 있을 때만 클릭합니다."
            return info

        self._install_approval_confirm_policy(driver)
        if not self._click_approval_button(driver):
            info["message"] = "승인 버튼을 찾지 못했습니다."
            return info

        info["attempted"] = True
        time.sleep(2.5)
        alert_actions = self._handle_approval_alerts(driver, timeout=2.0, rounds=5)
        info["alert_actions"] = alert_actions
        info["confirm_actions"] = self._approval_confirm_actions(driver)
        self._click_confirm_dialogs(driver, rounds=3)
        time.sleep(2.0)
        after = self._approval_state(driver)
        info["final_state"] = after
        info["approved"] = after != "unapproved"
        self._write_text(dump_dir / "04_approval_after.json", json.dumps(info, ensure_ascii=False, indent=2))
        return info

    def _approval_state(self, driver: WebDriver) -> str:
        text = self._visible_text(driver)
        if "미승인" in text:
            return "unapproved"
        if "승인" in text and self._find_clickable_text(driver, "승인", exclude=("미승인", "반송")):
            return "unapproved"
        return "approved"

    def _click_approval_button(self, driver: WebDriver) -> bool:
        if self._execute_approval_script(driver):
            return True
        candidates = [
            "//a[contains(@href, \"approve('K')\")]",
            "//*[contains(@href,'approve') and contains(@href,'K')]",
            "//*[self::button or self::a or self::input][normalize-space(.)='승인']",
            "//*[self::button or self::a or self::input][contains(normalize-space(.),'승인') and not(contains(normalize-space(.),'미승인')) and not(contains(normalize-space(.),'반송'))]",
            "//input[contains(@value,'승인') and not(contains(@value,'미승인')) and not(contains(@value,'반송'))]",
            "//*[contains(@onclick,'approve') or contains(@onclick,'appr') or contains(@onclick,'Approval')]",
        ]
        if self._click_first(driver, candidates, timeout=5, exclude_text=("미승인", "반송")):
            return True
        try:
            return bool(
                driver.execute_script(
                    "if (typeof approve === 'function') { approve('K'); return true; } return false;"
                )
            )
        except Exception as exc:
            return "alert" in str(exc).lower()

    def _install_approval_confirm_policy(self, driver: WebDriver) -> None:
        driver.execute_script(
            """
            window.__smileediConfirmActions = [];
            window.__smileediOriginalConfirm = window.confirm;
            window.confirm = function(message) {
              var text = String(message || '');
              var action = text.indexOf('인쇄하시겠습니까') >= 0 ? 'dismiss' : 'accept';
              window.__smileediConfirmActions.push({text: text, action: action});
              return action === 'accept';
            };
            """
        )

    def _execute_approval_script(self, driver: WebDriver) -> bool:
        try:
            return bool(
                driver.execute_script(
                    """
                    if (typeof approve === 'function') {
                      approve('K');
                      return true;
                    }
                    var link = document.querySelector("a[href*=\\"approve('K')\\"]")
                      || document.querySelector("a[href*='approve'][href*='K']");
                    if (link) {
                      link.click();
                      return true;
                    }
                    return false;
                    """
                )
            )
        except Exception as exc:
            return "alert" in str(exc).lower()

    def _approval_confirm_actions(self, driver: WebDriver) -> list[dict]:
        try:
            actions = driver.execute_script("return window.__smileediConfirmActions || [];")
            return actions if isinstance(actions, list) else []
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def _parse_mail_summary(self, mail_text: str) -> dict:
        text = self._clean_text(mail_text)
        return {
            "supplier_name": self._field_after(text, ("공급자",)),
            "buyer_name": self._field_after(text, ("공급받는자",)),
            "issue_date": self._date_after(text, ("작성일", "작성일자")),
            "item_name": self._field_after(text, ("품목명", "품목")),
        }

    def _parse_invoice_page(self, driver: WebDriver) -> dict:
        text = self._visible_text(driver)
        html_source = driver.page_source or ""
        hidden = self._hidden_values(html_source)
        rows = self._font_rows(html_source)

        strict_biz_numbers = re.findall(r"\d{3}-\d{2}-\d{5}", text)
        supplier_biz_no = self._format_biz_no(hidden.get("s_compnum") or "")
        if not supplier_biz_no and strict_biz_numbers:
            supplier_biz_no = strict_biz_numbers[0]
        buyer_biz_no = self._format_biz_no(hidden.get("inpasswd") or "")
        if not buyer_biz_no and len(strict_biz_numbers) >= 2:
            buyer_biz_no = strict_biz_numbers[1]

        items = self._items_from_rows(rows)
        supply_amount = sum(item.get("supply_amount", 0) for item in items)
        tax_amount = sum(item.get("tax_amount", 0) for item in items)
        total_sum = self._total_from_rows(rows) or (supply_amount + tax_amount)

        return {
            "supplier_name": hidden.get("s_compname") or self._party_name_from_rows(rows, 0),
            "buyer_name": hidden.get("r_compname") or self._party_name_from_rows(rows, 1),
            "supplier_biz_no": supplier_biz_no,
            "buyer_biz_no": buyer_biz_no,
            "issue_date": self._invoice_date_from_rows(rows) or self._date_after(text, ("작성일자", "작성일")),
            "item_name": items[0]["name"] if items else "",
            "target_supply": supply_amount,
            "total_tax": tax_amount,
            "total_sum": total_sum,
            "items": items,
            "raw_text_head": text[:3000],
        }

    def _build_subject(self, parsed: dict) -> str:
        buyer = parsed.get("buyer_name") or "사업장"
        supplier = parsed.get("supplier_name") or "매입처"
        amount = self._to_int(parsed.get("total_sum"))
        if amount:
            return f"[{buyer}] {supplier} 세금계산서({amount:,}원)"
        return f"[{buyer}] {supplier} 세금계산서"

    def _build_data(self, parsed: dict, matched_biz_no: str) -> dict:
        buyer_biz_no = parsed.get("buyer_biz_no") or matched_biz_no
        site_name = self._site_name_from_biz_no(buyer_biz_no) or parsed.get("buyer_name") or ""
        total_sum = self._to_int(parsed.get("total_sum"))
        parsed_items = parsed.get("items") or []
        item_name = parsed.get("item_name") or (parsed_items[0].get("name") if parsed_items else "") or "세금계산서"
        items = [
            {
                "name": item.get("name") or item_name,
                "qty": item.get("qty") or 1,
                "inc_vat": item.get("inc_vat") or total_sum,
                "account": "소모품비",
            }
            for item in parsed_items
        ] or [
            {
                "name": item_name,
                "qty": 1,
                "inc_vat": total_sum,
                "account": "소모품비",
            }
        ]
        return {
            "vendor_name": parsed.get("supplier_name") or "",
            "site_name": site_name,
            "business_no": buyer_biz_no,
            "matched_biz_no": matched_biz_no,
            "invoice_date": parsed.get("issue_date") or "",
            "target_supply": self._to_int(parsed.get("target_supply")),
            "total_tax": self._to_int(parsed.get("total_tax")),
            "total_sum": total_sum,
            "items": items,
            "raw": {
                "smileedi": parsed,
            },
        }

    # ------------------------------------------------------------------
    # Generic browser helpers
    # ------------------------------------------------------------------
    def _click_first(
        self,
        driver: WebDriver,
        xpaths: list[str],
        timeout: int = 3,
        exclude_text: tuple[str, ...] = (),
    ) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            for context in self._contexts(driver):
                try:
                    for xpath in xpaths:
                        elems = context.find_elements(By.XPATH, xpath)
                        for elem in elems:
                            label = self._element_label(elem)
                            if exclude_text and any(word in label for word in exclude_text):
                                continue
                            if not elem.is_displayed() or not elem.is_enabled():
                                continue
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                            time.sleep(0.2)
                            driver.execute_script("arguments[0].click();", elem)
                            driver.switch_to.default_content()
                            return True
                except Exception:
                    continue
            time.sleep(0.3)
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        return False

    def _find_clickable_text(self, driver: WebDriver, text: str, exclude: tuple[str, ...] = ()) -> bool:
        xpaths = [
            f"//*[self::button or self::a or self::input][contains(normalize-space(.),'{text}')]",
            f"//input[contains(@value,'{text}')]",
        ]
        for context in self._contexts(driver):
            try:
                for xpath in xpaths:
                    for elem in context.find_elements(By.XPATH, xpath):
                        label = self._element_label(elem)
                        if any(word in label for word in exclude):
                            continue
                        if elem.is_displayed() and elem.is_enabled():
                            return True
            except Exception:
                continue
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        return False

    def _click_confirm_dialogs(self, driver: WebDriver, rounds: int = 2) -> None:
        for _ in range(rounds):
            clicked = self._click_first(
                driver,
                [
                    "//*[self::button or self::a or self::input][normalize-space(.)='확인']",
                    "//input[contains(@value,'확인')]",
                ],
                timeout=1,
            )
            if not clicked:
                break
            time.sleep(0.5)

    def _accept_alerts(self, driver: WebDriver, timeout: float = 1.0, rounds: int = 1) -> bool:
        accepted = False
        for _ in range(rounds):
            try:
                WebDriverWait(driver, timeout).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                alert.accept()
                accepted = True
                time.sleep(0.3)
            except Exception:
                break
        return accepted

    def _handle_approval_alerts(self, driver: WebDriver, timeout: float = 2.0, rounds: int = 5) -> list[dict]:
        actions: list[dict] = []
        for _ in range(rounds):
            try:
                WebDriverWait(driver, timeout).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                text = str(alert.text or "")
                if "인쇄하시겠습니까" in text:
                    alert.dismiss()
                    actions.append({"text": text, "action": "dismiss"})
                else:
                    alert.accept()
                    actions.append({"text": text, "action": "accept"})
                time.sleep(0.5)
            except Exception:
                break
        return actions

    def _switch_to_latest_window(self, driver: WebDriver) -> None:
        try:
            if driver.window_handles:
                driver.switch_to.window(driver.window_handles[-1])
        except Exception:
            pass

    def _wait_document_ready(self, driver: WebDriver, timeout: int = 10) -> None:
        end_at = time.time() + timeout
        while time.time() < end_at:
            try:
                if driver.execute_script("return document.readyState") == "complete":
                    return
            except Exception:
                return
            time.sleep(0.2)

    def _contexts(self, driver: WebDriver):
        try:
            driver.switch_to.default_content()
            yield driver
            frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            for frame in frames:
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                    yield driver
                except Exception:
                    continue
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

    @staticmethod
    def _is_editable_visible(elem: WebElement) -> bool:
        try:
            if not elem.is_displayed() or not elem.is_enabled():
                return False
            if elem.get_attribute("readonly") or elem.get_attribute("disabled"):
                return False
            return True
        except Exception:
            return False

    @staticmethod
    def _element_label(elem: WebElement) -> str:
        parts = [
            elem.text or "",
            elem.get_attribute("value") or "",
            elem.get_attribute("title") or "",
            elem.get_attribute("alt") or "",
            elem.get_attribute("onclick") or "",
        ]
        return " ".join(part.strip() for part in parts if part).strip()

    def _visible_text(self, driver: WebDriver) -> str:
        chunks: list[str] = []
        for context in self._contexts(driver):
            try:
                body = context.find_element(By.TAG_NAME, "body")
                text = body.text.strip()
                if text:
                    chunks.append(text)
            except Exception:
                continue
        return "\n".join(dict.fromkeys(chunks))

    # ------------------------------------------------------------------
    # Text helpers / debug
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_text(value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", str(value or ""))
        text = re.sub(r"&nbsp;?", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _field_after(text: str, labels: tuple[str, ...]) -> str:
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:：]?\s*([^\n\r|]+?)(?=\s+(?:공급자|공급받는자|작성일|품목명|품목)\s*[:：]?|$)"
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip(" :：")
        return ""

    @staticmethod
    def _date_after(text: str, labels: tuple[str, ...]) -> str:
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:：]?\s*(20\d{{2}}[-./년 ]+\d{{1,2}}[-./월 ]+\d{{1,2}})"
            match = re.search(pattern, text)
            if match:
                digits = re.sub(r"[^\d]", "", match.group(1))
                if len(digits) >= 8:
                    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        match = re.search(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
        if match:
            return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        return ""

    @staticmethod
    def _label_value_from_text(text: str, labels: tuple[str, ...]) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for index, line in enumerate(lines):
            if any(label in line for label in labels):
                if index + 1 < len(lines):
                    candidate = lines[index + 1].strip()
                    if candidate and not any(label in candidate for label in labels):
                        return candidate
        return ""

    @staticmethod
    def _to_int(value) -> int:
        digits = re.sub(r"[^\d]", "", str(value or ""))
        return int(digits) if digits else 0

    @staticmethod
    def _format_biz_no(value: str) -> str:
        digits = re.sub(r"[^\d]", "", str(value or ""))
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        return str(value or "").strip()

    @staticmethod
    def _hidden_values(html_source: str) -> dict[str, str]:
        values: dict[str, str] = {}
        for tag in re.findall(r"<input\b[^>]*>", str(html_source or ""), flags=re.I | re.S):
            name_match = re.search(r"\bname\s*=\s*(['\"])(.*?)\1", tag, flags=re.I | re.S)
            value_match = re.search(r"\bvalue\s*=\s*(['\"])(.*?)\1", tag, flags=re.I | re.S)
            if not name_match:
                continue
            name = html.unescape(name_match.group(2)).strip()
            value = html.unescape(value_match.group(2)).strip() if value_match else ""
            values[name] = value
        return values

    @classmethod
    def _font_rows(cls, html_source: str) -> list[list[str]]:
        rows: list[list[str]] = []
        for row_html in re.findall(r"<tr\b[^>]*>(.*?)</tr>", str(html_source or ""), flags=re.I | re.S):
            cells = [
                cls._clean_html_cell(cell)
                for cell in re.findall(
                    r"<p\b[^>]*class\s*=\s*(['\"])[^'\"]*FontForBlack[^'\"]*\1[^>]*>(.*?)</p>",
                    row_html,
                    flags=re.I | re.S,
                )
            ]
            if any(cells):
                rows.append(cells)
        return rows

    @staticmethod
    def _clean_html_cell(match_value) -> str:
        raw = match_value[1] if isinstance(match_value, tuple) else match_value
        text = re.sub(r"<[^>]+>", " ", str(raw or ""))
        text = html.unescape(text).replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _party_name_from_rows(rows: list[list[str]], side_index: int) -> str:
        for cells in rows:
            if len(cells) >= 8 and re.fullmatch(r"\d{3}-\d{2}-\d{5}", cells[0]) and re.fullmatch(r"\d{3}-\d{2}-\d{5}", cells[4]):
                continue
            if len(cells) >= 6 and not re.fullmatch(r"\d{3}-\d{2}-\d{5}", cells[0]):
                if side_index == 0 and cells[0]:
                    return cells[0]
                if side_index == 1 and len(cells) >= 5 and cells[4]:
                    return cells[4]
        return ""

    @staticmethod
    def _invoice_date_from_rows(rows: list[list[str]]) -> str:
        for cells in rows:
            if len(cells) < 3:
                continue
            year = re.sub(r"[^\d]", "", cells[0])
            month = re.sub(r"[^\d]", "", cells[1])
            day = re.sub(r"[^\d]", "", cells[2])
            if len(year) == 4 and year.startswith("20") and month and day:
                month_i = int(month)
                day_i = int(day)
                if 1 <= month_i <= 12 and 1 <= day_i <= 31:
                    return f"{year}-{month_i:02d}-{day_i:02d}"
        return ""

    def _items_from_rows(self, rows: list[list[str]]) -> list[dict]:
        items: list[dict] = []
        for cells in rows:
            if len(cells) < 8:
                continue
            month = re.sub(r"[^\d]", "", cells[0])
            day = re.sub(r"[^\d]", "", cells[1])
            name = cells[2].strip()
            if not month or not day or not name:
                continue
            if name in {"품목", "규격", "수량", "단가", "공급가액", "세액", "비고"}:
                continue
            supply_amount = self._to_int(cells[6] if len(cells) > 6 else "")
            tax_amount = self._to_int(cells[7] if len(cells) > 7 else "")
            if not supply_amount and not tax_amount:
                continue
            items.append(
                {
                    "name": name,
                    "qty": 1,
                    "supply_amount": supply_amount,
                    "tax_amount": tax_amount,
                    "inc_vat": supply_amount + tax_amount,
                }
            )
        return items

    def _total_from_rows(self, rows: list[list[str]]) -> int:
        for cells in rows:
            money_values = [self._to_int(cell) for cell in cells if "," in cell]
            money_values = [value for value in money_values if value > 0]
            if money_values and len(cells) <= 5:
                return money_values[0]
        return 0

    def _candidate_debug(self, candidates: dict[str, str]) -> list[dict]:
        return [
            {
                "key": key,
                "biz_no": biz_no,
                "site_name": self._site_name_from_biz_no(biz_no),
            }
            for key, biz_no in candidates.items()
        ]

    def _make_debug_dir(self, mail_date: str) -> Path:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        safe_date = re.sub(r"[^\d]", "", str(mail_date or "")) or time.strftime("%y%m%d")
        path = self.download_dir / "_debug" / f"smileedi_{safe_date}_{stamp}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _dump_state(self, driver: WebDriver, dump_dir: Path, label: str) -> None:
        try:
            self._write_text(dump_dir / f"{label}.url.txt", driver.current_url or "")
        except Exception:
            pass
        try:
            self._write_text(dump_dir / f"{label}.text.txt", self._visible_text(driver))
        except Exception:
            pass
        try:
            self._write_text(dump_dir / f"{label}.html", driver.page_source or "")
        except Exception:
            pass
        try:
            driver.save_screenshot(str(dump_dir / f"{label}.png"))
        except Exception:
            pass

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(text or ""), encoding="utf-8", errors="replace")


def extract_smileedi_links(mail_body: str) -> list[str]:
    links = re.findall(r'https?://[^\s"\'<>]+', str(mail_body or ""))
    valid: list[str] = []
    for link in links:
        cleaned = html.unescape(link).strip().strip("\"'<>").rstrip(".,;)")
        lower = cleaned.lower()
        if "smileedi.com" in lower and "/dtiemail.do" in lower:
            valid.append(cleaned)
    return list(dict.fromkeys(valid))


def main() -> int:
    parser = argparse.ArgumentParser(description="SMILE EDI crawler prototype")
    parser.add_argument("--url", required=True, help="SMILE EDI DtiEmail.do URL")
    parser.add_argument("--mail-text", default="", help="메일 본문 텍스트")
    parser.add_argument("--mail-text-file", default="", help="메일 본문 파일 경로")
    parser.add_argument("--mail-date", default="", help="메일 기준일. 예: 20260514 또는 260514")
    parser.add_argument("--mail-subject", default="", help="메일 제목")
    parser.add_argument("--approve", action="store_true", help="미승인 계산서 승인 버튼을 실제 클릭")
    parser.add_argument("--keep-browser-open", action="store_true", help="테스트 후 브라우저를 닫지 않음")
    args = parser.parse_args()

    mail_text = args.mail_text
    if args.mail_text_file:
        mail_text = Path(args.mail_text_file).read_text(encoding="utf-8", errors="replace")

    handler = SmileEdiHandler(
        approve_on_unapproved=args.approve,
        keep_browser_open=args.keep_browser_open,
    )
    result = handler.process(
        url=args.url,
        mail_text=mail_text,
        mail_date=args.mail_date,
        mail_subject=args.mail_subject,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
