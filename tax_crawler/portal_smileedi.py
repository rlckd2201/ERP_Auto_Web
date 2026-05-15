"""
SMILE EDI tax invoice crawler.

Approval is opt-in because SMILE EDI approval cannot be rolled back to an
unapproved state.  Automatic mail collection only stores invoices that are
already approved and can be saved as PDF/XML.
"""
import argparse
import base64
import html
import json
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_handler import BaseTaxInvoiceHandler
from xml_parser import parse_tax_invoice_xml


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
            "xml_path": None,
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
        pdf_path = None
        pdf_error = None
        xml_path = None
        xml_error = None
        approved = bool(approval.get("approved") or self._approval_state(driver) == "approved")
        if approved:
            xml_path, xml_parsed, xml_error = self._download_and_parse_xml(driver, parsed, dump_dir)
            if xml_parsed:
                parsed = {**parsed, **xml_parsed}
            pdf_path, pdf_error = self._save_invoice_pdf(driver, parsed, dump_dir)
        else:
            result.update(
                {
                    "ok": False,
                    "subject": self._build_subject(parsed),
                    "data": self._build_data(parsed, matched_biz_no),
                    "approval": approval,
                    "matched_biz_key": matched_key,
                    "matched_biz_no": matched_biz_no,
                    "matched_site_name": self._site_name_from_biz_no(matched_biz_no),
                    "error": approval.get("message")
                    or "SMILE EDI 미승인 계산서는 --approve 옵션 없이 자동 저장하지 않습니다.",
                }
            )
            return

        data = self._build_data(parsed, matched_biz_no)
        if pdf_path:
            data["pdf_path"] = str(pdf_path)
        if xml_path:
            data["xml_path"] = str(xml_path)

        result.update(
            {
                "ok": bool(pdf_path),
                "invoice_type": "regular",
                "pdf_path": str(pdf_path) if pdf_path else None,
                "xml_path": str(xml_path) if xml_path else None,
                "subject": self._build_subject(parsed),
                "data": data,
                "approval": approval,
                "matched_biz_key": matched_key,
                "matched_biz_no": matched_biz_no,
                "matched_site_name": self._site_name_from_biz_no(matched_biz_no),
            }
        )
        if not pdf_path:
            result["error"] = pdf_error or "SMILE EDI PDF 저장 파일을 만들지 못했습니다."
        if xml_error:
            result["xml_error"] = xml_error
        if pdf_error:
            result["pdf_error"] = pdf_error

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
    # XML output
    # ------------------------------------------------------------------
    def _download_and_parse_xml(
        self,
        driver: WebDriver,
        parsed: dict,
        dump_dir: Path,
    ) -> tuple[Path | None, dict | None, str | None]:
        xml_path = self._download_invoice_xml(driver, dump_dir)
        if not xml_path:
            return None, None, "SMILE EDI XML download failed"

        try:
            supplier, buyer, content = parse_tax_invoice_xml(str(xml_path))
            xml_parsed = self._xml_to_parsed(xml_path, supplier, buyer, content)
            normalized_path = self._normalize_xml_path(xml_path, {**parsed, **xml_parsed}, dump_dir)
            xml_parsed["xml_path"] = str(normalized_path)
            self._write_text(
                dump_dir / "05_xml_parse_result.json",
                json.dumps(xml_parsed, ensure_ascii=False, indent=2),
            )
            return normalized_path, xml_parsed, None
        except Exception as exc:
            self._write_text(dump_dir / "05_xml_parse_error.txt", repr(exc))
            return xml_path, {"xml_path": str(xml_path)}, str(exc)

    def _download_invoice_xml(self, driver: WebDriver, dump_dir: Path) -> Path | None:
        before_state = self._snapshot_xml_state()
        attempts: list[object] = []

        try:
            click_result = driver.execute_script(
                """
                return (function () {
                  const actions = [];
                  const originalConfirm = window.confirm;
                  window.__smileediXmlConfirms = [];
                  window.confirm = function (message) {
                    window.__smileediXmlConfirms.push(String(message || ''));
                    return true;
                  };
                  function labelOf(el) {
                    return [
                      el.innerText, el.value, el.title, el.alt,
                      el.getAttribute && el.getAttribute('href'),
                      el.getAttribute && el.getAttribute('onclick')
                    ].join(' ');
                  }
                  function ensureField(form, name, value) {
                    let field = form.elements[name];
                    if (!field) {
                      field = document.createElement('input');
                      field.type = 'hidden';
                      field.name = name;
                      form.appendChild(field);
                    }
                    field.value = value;
                  }
                  try {
                    if (typeof print_viewer_save === 'function') {
                      print_viewer_save();
                      actions.push('print_viewer_save()');
                      return {ok: true, actions: actions, confirms: window.__smileediXmlConfirms};
                    }

                    const direct = Array.from(document.querySelectorAll(
                      "a[href*='print_viewer_save'], a[onclick*='print_viewer_save']"
                    ))[0];
                    if (direct) {
                      direct.click();
                      actions.push('click print_viewer_save link');
                      return {ok: true, actions: actions, confirms: window.__smileediXmlConfirms};
                    }

                    const xmlLink = Array.from(document.querySelectorAll('a, button, input')).find(function (el) {
                      return labelOf(el).toUpperCase().includes('XML');
                    });
                    if (xmlLink) {
                      xmlLink.click();
                      actions.push('click XML element');
                      return {ok: true, actions: actions, confirms: window.__smileediXmlConfirms};
                    }

                    const form = document.forms.eform || document.eform;
                    if (form) {
                      let frame = document.querySelector("iframe[name='hiddenFrame'], frame[name='hiddenFrame']");
                      if (!frame) {
                        frame = document.createElement('iframe');
                        frame.name = 'hiddenFrame';
                        frame.style.display = 'none';
                        document.body.appendChild(frame);
                      }
                      ensureField(form, 'submitType', 'viewer');
                      form.action = '/DtiTaxSign.do';
                      form.target = 'hiddenFrame';
                      form.submit();
                      actions.push('submit eform viewer');
                      return {ok: true, actions: actions, confirms: window.__smileediXmlConfirms};
                    }

                    return {ok: false, actions: actions, confirms: window.__smileediXmlConfirms};
                  } finally {
                    window.confirm = originalConfirm;
                  }
                })();
                """
            )
            attempts.append(click_result)
        except Exception as exc:
            attempts.append(f"execute_script failed: {exc!r}")

        self._accept_alerts(driver, timeout=1.0, rounds=3)
        downloaded = self._wait_xml_change(before_state, timeout=15)
        if downloaded:
            self._write_text(
                dump_dir / "05_xml_download_success.txt",
                f"download={downloaded}\nattempts={json.dumps(attempts, ensure_ascii=False, indent=2)}",
            )
            return downloaded

        frame_xml = self._save_xml_from_frames(driver, dump_dir)
        if frame_xml:
            self._write_text(
                dump_dir / "05_xml_download_success.txt",
                f"frame={frame_xml}\nattempts={json.dumps(attempts, ensure_ascii=False, indent=2)}",
            )
            return frame_xml

        self._write_text(
            dump_dir / "05_xml_download_failed.json",
            json.dumps({"attempts": attempts}, ensure_ascii=False, indent=2),
        )
        return None

    def _xml_to_parsed(self, xml_path: Path, supplier: dict, buyer: dict, content: dict) -> dict:
        xml_items = content.get("항목") or content.get("품목") or []
        items = []
        for item in xml_items:
            supply_amount = self._to_int(item.get("공급가액"))
            tax_amount = self._to_int(item.get("세액"))
            name = item.get("품목") or ""
            if not name and not supply_amount and not tax_amount:
                continue
            items.append(
                {
                    "name": name or content.get("비고") or "세금계산서",
                    "qty": 1,
                    "supply_amount": supply_amount,
                    "tax_amount": tax_amount,
                    "inc_vat": supply_amount + tax_amount,
                }
            )

        first_item = items[0] if items else {}
        target_supply = self._to_int(content.get("공급가액")) or sum(item["supply_amount"] for item in items)
        total_tax = self._to_int(content.get("세액")) or sum(item["tax_amount"] for item in items)
        total_sum = self._to_int(content.get("합계금액")) or (target_supply + total_tax)

        return {
            "xml_path": str(xml_path),
            "supplier_name": supplier.get("상호") or "",
            "buyer_name": buyer.get("상호") or "",
            "supplier_biz_no": supplier.get("등록번호") or "",
            "buyer_biz_no": buyer.get("등록번호") or "",
            "issue_date": self._normalize_date(content.get("작성일자") or ""),
            "item_name": first_item.get("name") or content.get("비고") or "",
            "target_supply": target_supply,
            "total_tax": total_tax,
            "total_sum": total_sum,
            "items": items,
            "source": "xml_download",
            "raw_xml": {
                "supplier": supplier,
                "buyer": buyer,
                "content": content,
            },
        }

    def _normalize_xml_path(self, xml_path: Path, parsed: dict, dump_dir: Path) -> Path:
        final_pdf_name = self.build_pdf_filename(
            issue_date=parsed.get("issue_date") or "",
            buyer=parsed.get("buyer_name") or "사업장",
            supplier=parsed.get("supplier_name") or "매입처",
            item=parsed.get("item_name") or "세금계산서",
            extra="",
            amount=str(parsed.get("total_sum") or 0),
            buyer_biz_no=parsed.get("buyer_biz_no") or "",
        )
        target = self.dedupe_path(self.download_dir / f"{Path(final_pdf_name).stem}.xml")
        try:
            if xml_path.resolve() == target.resolve():
                return xml_path
        except Exception:
            pass
        try:
            xml_path.replace(target)
            self._write_text(dump_dir / "05_xml_renamed.txt", f"{xml_path} -> {target}")
            return target
        except Exception as exc:
            self._write_text(dump_dir / "05_xml_rename_error.txt", repr(exc))
            return xml_path

    def _snapshot_xml_state(self) -> dict[str, tuple[int, int]]:
        state: dict[str, tuple[int, int]] = {}
        for path in self.download_dir.glob("*.xml"):
            try:
                stat = path.stat()
                state[str(path.resolve())] = (stat.st_mtime_ns, stat.st_size)
            except Exception:
                continue
        return state

    def _wait_xml_change(self, before_state: dict[str, tuple[int, int]], timeout: int = 15) -> Path | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            for path in self.download_dir.glob("*.xml"):
                try:
                    stat = path.stat()
                    current = (stat.st_mtime_ns, stat.st_size)
                    key = str(path.resolve())
                except Exception:
                    continue
                if key not in before_state or before_state.get(key) != current:
                    if not path.name.endswith(".crdownload") and self._is_stable(path):
                        return path
            time.sleep(0.5)
        return None

    def _save_xml_from_frames(self, driver: WebDriver, dump_dir: Path) -> Path | None:
        try:
            driver.switch_to.default_content()
            frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        except Exception:
            return None

        for index, frame in enumerate(frames):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                body_text = ""
                try:
                    body_text = driver.find_element(By.TAG_NAME, "body").text
                except Exception:
                    pass
                source = driver.page_source or ""
                xml_text = body_text if self._looks_like_xml(body_text) else source
                if not self._looks_like_xml(xml_text):
                    continue
                target = self.dedupe_path(self.download_dir / f"smileedi_hidden_frame_{int(time.time())}.xml")
                target.write_text(xml_text.strip(), encoding="utf-8", errors="replace")
                return target
            except Exception as exc:
                self._write_text(dump_dir / f"05_xml_frame_{index}_error.txt", repr(exc))
                continue
            finally:
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
        return None

    @staticmethod
    def _looks_like_xml(value: str) -> bool:
        text = str(value or "").lstrip()
        return text.startswith("<?xml") or "<TaxInvoice" in text or "TaxInvoiceDocument" in text

    # ------------------------------------------------------------------
    # PDF output
    # ------------------------------------------------------------------
    def _save_invoice_pdf(self, driver: WebDriver, parsed: dict, dump_dir: Path) -> tuple[Path | None, str | None]:
        original_handle = None
        opened_handle = None
        try:
            original_handle = driver.current_window_handle
        except Exception:
            pass

        try:
            before_handles = list(driver.window_handles)
            if not self._open_print_view(driver, before_handles):
                return None, "SMILE EDI 인쇄 화면을 열지 못했습니다."

            self._wait_document_ready(driver, timeout=12)
            time.sleep(2.0)
            try:
                if original_handle and driver.current_window_handle != original_handle:
                    opened_handle = driver.current_window_handle
            except Exception:
                pass
            self._dump_state(driver, dump_dir, "05_print_view")

            final_name = self.build_pdf_filename(
                issue_date=parsed.get("issue_date") or "",
                buyer=parsed.get("buyer_name") or "사업장",
                supplier=parsed.get("supplier_name") or "매입처",
                item=parsed.get("item_name") or "세금계산서",
                extra="",
                amount=str(parsed.get("total_sum") or 0),
                buyer_biz_no=parsed.get("buyer_biz_no") or "",
            )
            final_path = self.dedupe_path(self.download_dir / final_name)
            payload = driver.execute_cdp_cmd(
                "Page.printToPDF",
                {
                    "printBackground": True,
                    "preferCSSPageSize": True,
                    "landscape": False,
                    "marginTop": 0.2,
                    "marginBottom": 0.2,
                    "marginLeft": 0.2,
                    "marginRight": 0.2,
                },
            )
            pdf_bytes = base64.b64decode(payload["data"])
            final_path.write_bytes(pdf_bytes)
            self._write_text(
                dump_dir / "05_pdf_saved.json",
                json.dumps(
                    {"pdf_path": str(final_path), "size": len(pdf_bytes), "url": driver.current_url},
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            if not final_path.exists() or final_path.stat().st_size <= 0:
                return None, f"SMILE EDI PDF 저장 파일이 비어 있습니다: {final_path}"
            return final_path, None
        except Exception as exc:
            self._write_text(dump_dir / "05_pdf_error.txt", repr(exc))
            return None, str(exc)
        finally:
            if opened_handle:
                try:
                    driver.close()
                except Exception:
                    pass
                if original_handle:
                    try:
                        driver.switch_to.window(original_handle)
                    except Exception:
                        pass

    def _open_print_view(self, driver: WebDriver, before_handles: list[str]) -> bool:
        try:
            opened = bool(
                driver.execute_script(
                    """
                    if (typeof print_tax === 'function') {
                      print_tax('Y');
                      return true;
                    }
                    var link = document.querySelector("a[href*='print_tax']");
                    if (link) {
                      link.click();
                      return true;
                    }
                    return false;
                    """
                )
            )
        except Exception:
            opened = False

        deadline = time.time() + 8
        while time.time() < deadline:
            handles = list(driver.window_handles)
            if len(handles) > len(before_handles):
                new_handle = [handle for handle in handles if handle not in before_handles][-1]
                driver.switch_to.window(new_handle)
                return True
            time.sleep(0.4)

        if "submitType=print" in (driver.current_url or ""):
            return True
        if opened:
            return True

        print_url = self._build_print_url(driver)
        if not print_url:
            return False
        driver.get(print_url)
        return True

    def _build_print_url(self, driver: WebDriver) -> str:
        hidden = self._hidden_values(driver.page_source or "")
        taxid = hidden.get("taxid") or hidden.get("docid") or ""
        if not taxid:
            return ""
        current = urlparse(driver.current_url or "https://www.smileedi.com/DtiEmail.do")
        origin = f"{current.scheme or 'https'}://{current.netloc or 'www.smileedi.com'}"
        params = {
            "submitType": "print",
            "selectType": hidden.get("selectType") or "r",
            "taxid": taxid,
            "pubtype": hidden.get("pubtype") or "N",
            "beforeState": "K",
            "r_a_id": hidden.get("r_a_id") or "",
            "s_a_id": hidden.get("s_a_id") or "",
            "couple_taxid": hidden.get("couple_taxid") or "",
            "addTax": hidden.get("addTax") or "",
        }
        return f"{origin}/DtiEmail.do?{urlencode(params)}"

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
        supplier_biz_no = parsed.get("supplier_biz_no") or ""
        site_name = self._site_name_from_biz_no(buyer_biz_no) or parsed.get("buyer_name") or ""
        total_sum = self._to_int(parsed.get("total_sum"))
        parsed_items = parsed.get("items") or []
        item_name = parsed.get("item_name") or (parsed_items[0].get("name") if parsed_items else "") or "세금계산서"

        def item_inc_vat(item: dict) -> int:
            supply = self._to_int(item.get("supply") or item.get("supply_amount"))
            tax = self._to_int(item.get("tax") or item.get("tax_amount"))
            return self._to_int(item.get("inc_vat")) or (supply + tax) or total_sum

        items = [
            {
                "name": item.get("name") or item_name,
                "qty": item.get("qty") or 1,
                "supply": self._to_int(item.get("supply") or item.get("supply_amount")),
                "tax": self._to_int(item.get("tax") or item.get("tax_amount")),
                "inc_vat": item_inc_vat(item),
                "account": "지급수수료",
                "is_a": False,
                "dept": "",
            }
            for item in parsed_items
        ] or [
            {
                "name": item_name,
                "qty": 1,
                "supply": self._to_int(parsed.get("target_supply")),
                "tax": self._to_int(parsed.get("total_tax")),
                "inc_vat": total_sum,
                "account": "지급수수료",
                "is_a": False,
                "dept": "",
            }
        ]
        return {
            "invoice_type": "regular",
            "portal": "smileedi",
            "source": "smileedi",
            "vendor_name": parsed.get("supplier_name") or "",
            "supplier_name": parsed.get("supplier_name") or "",
            "supplier_biz_no": supplier_biz_no,
            "vendor_biz_no": supplier_biz_no,
            "site_name": site_name,
            "business_no": buyer_biz_no,
            "buyer_biz_no": buyer_biz_no,
            "matched_biz_no": matched_biz_no,
            "invoice_date": parsed.get("issue_date") or "",
            "item_name": item_name,
            "target_supply": self._to_int(parsed.get("target_supply")),
            "total_tax": self._to_int(parsed.get("total_tax")),
            "total_sum": total_sum,
            "items": items,
            "erp_ready": True,
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
    def _normalize_date(value: str) -> str:
        digits = re.sub(r"[^\d]", "", str(value or ""))
        if len(digits) >= 8:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return str(value or "").strip()

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
