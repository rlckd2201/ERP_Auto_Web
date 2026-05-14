"""
WEHAGO (더존비즈온) 세금계산서 핸들러
대상: www.wehago.com/invoice/#/eTaxMail/...
메일 수신 업체: Acronis, Watching-On

인증 방식:
  - URL의 Base64 토큰에 사업자번호가 인코딩됨 → 디코딩하면 1번 트라이로 인증 완료
    예: VFgyMDI2MDQ2OTQ5MjI3JjEyNTgxMDU2MTk= → TX2026046949227&1258105619
  - 페이지 로드 후 visible text input 중 마지막이 사업자번호 모달 입력창
  - 확인 버튼 클릭 후 visible inputs 수가 줄면 인증 성공
인증 후 버튼:
  - [XML]  → XML 다운로드 (공급자/수신자/금액 정확히 파싱 가능)
  - [인쇄] → PDF 자동 다운로드 (class=WSC_LUXButton)
"""
import base64
import re
import shutil
import time
from pathlib import Path

import pyautogui
from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_handler import BaseTaxInvoiceHandler
from xml_parser import parse_tax_invoice_xml


class WehagoHandler(BaseTaxInvoiceHandler):

    DOMAIN = "wehago.com"
    INVOICE_PREFIX = "https://www.wehago.com/invoice/"

    @property
    def portal_name(self) -> str:
        return "wehago"

    def supports(self, url: str) -> bool:
        return str(url or "").lower().startswith(self.INVOICE_PREFIX)

    def _do_process(self, driver, url, mail_text, mail_date, result):
        # URL Base64 디코딩 우선 → 실패 시 메일 본문 키워드 매칭
        candidates = self._candidates_from_url(url) or self.build_candidate_nos(mail_text)
        if not candidates:
            result["error"] = "WEHAGO 법인명 식별 실패 (mail_text에 법인명 포함 필요)"
            return

        driver.get(url)
        time.sleep(5)  # SPA 렌더링 대기

        matched = self._auth_modal(driver, candidates)
        if not matched:
            result["error"] = "WEHAGO 사업자번호 인증 실패"
            return

        time.sleep(2)
        self._dismiss_notice_dialog(driver)

        # XML 다운로드 → 정확한 거래처/금액 파싱
        supplier_name, buyer_name, buyer_biz_no = "", "", ""
        issue_date = mail_date
        total_amount = 0
        tax_amount = 0
        supply_amount = 0
        items_raw = []
        xml_snap = self.snapshot(".xml")
        if self._click_xml(driver):
            xml_file = self.wait_new_file(".xml", xml_snap, timeout=10)
            if xml_file:
                try:
                    supplier, buyer, content = parse_tax_invoice_xml(str(xml_file))
                    supplier_name = supplier.get("상호", "")
                    buyer_name    = buyer.get("상호", "")
                    buyer_biz_no  = buyer.get("등록번호", "")
                    issue_date    = content.get("작성일자") or mail_date
                    supply_amount = self._to_int(content.get("공급가액", "0"))
                    tax_amount    = self._to_int(content.get("세액", "0"))
                    total_amount  = self._to_int(content.get("합계금액", "0"))
                    items_raw     = content.get("항목", [])
                    xml_file.unlink()
                except Exception:
                    xml_file.unlink() if xml_file.exists() else None

        # XML 실패 시 페이지 소스에서 추출
        if not supplier_name:
            src = driver.page_source
            supplier_name = self._parse_field(src, ["공급자", "발급업무대행사"])
            buyer_name    = self._parse_field(src, ["공급받는자"])
            total_amount  = self._parse_amount(src)
            items_raw     = []

        items = [
            {
                "name": it.get("품목", ""),
                "qty": 1,
                "inc_vat": self._to_int(it.get("공급가액", "0")) + self._to_int(it.get("세액", "0")),
                "account": "소모품비",
            }
            for it in items_raw
        ] or [{"name": "세금계산서", "qty": 1, "inc_vat": total_amount, "account": "소모품비"}]

        first_item = items_raw[0].get("품목", "세금계산서") if items_raw else "세금계산서"
        extra = f"_외{len(items_raw)-1}건" if len(items_raw) > 1 else ""

        final_name = self.build_pdf_filename(
            issue_date=issue_date,
            buyer=buyer_name or "사업장미상",
            supplier=supplier_name or "매입처",
            item=first_item,
            extra=extra,
            amount=str(total_amount),
            buyer_biz_no=buyer_biz_no,
        )
        final_path = self.dedupe_path(self.download_dir / final_name)

        # 인쇄 버튼 → 더존 미리보기 → PDF 저장
        if not self._click_print(driver):
            result["error"] = "WEHAGO 인쇄 버튼 없음"
            return

        pdf_file = self._export_pdf_from_print_dialog(final_path, timeout=30)
        if not pdf_file:
            result["error"] = "WEHAGO PDF 다운로드 실패"
            return

        result.update({
            "ok": True,
            "pdf_path": str(pdf_file),
            "subject": f"[{buyer_name or '사업장미상'}] {supplier_name or '매입처'} 세금계산서 ({total_amount:,}원)",
            "data": {
                "vendor_name": supplier_name or "",
                "site_name":   buyer_name or "",
                "total_tax":   tax_amount,
                "total_sum":   total_amount,
                "items":       items,
            },
        })

    # ------------------------------------------------------------------
    @staticmethod
    def _candidates_from_url(url: str) -> dict[str, str] | None:
        """
        WEHAGO URL의 Base64 토큰에서 사업자번호(10자리) 추출.
        예: .../eTaxMail/VFgyMDI2MDQ2OTQ5MjI3JjEyNTgxMDU2MTk=
            → TX2026046949227&1258105619 → {"url_0": "1258105619"}
        성공하면 1번만 트라이하면 됨.
        """
        try:
            token = url.rstrip("/").split("/")[-1]
            padded = token + "=" * (-len(token) % 4)
            decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
            parts = [p.strip() for p in decoded.split("&") if p.strip()]
            if parts:
                tail = parts[-1]
                m = re.search(r"(\d{10})$", tail)
                if m:
                    return {"url_0": m.group(1)}
            nos = re.findall(r"\d{10}", decoded)
            if nos:
                return {"url_0": nos[-1]}
        except Exception:
            pass
        return None

    def _auth_modal(self, driver, candidates: dict) -> str | None:
        """
        visible text input 중 마지막 = 모달 입력창.
        확인 클릭 후 visible inputs 수가 줄면 인증 성공.
        """
        visible = [i for i in driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                   if i.is_displayed()]
        if not visible:
            return "no_modal"

        modal_inp = visible[-1]
        before_count = len(visible)

        for name, no in candidates.items():
            try:
                modal_inp.clear()
                modal_inp.send_keys(no)
                time.sleep(0.3)

                confirm = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='확인']"))
                )
                driver.execute_script("arguments[0].click();", confirm)
                time.sleep(2)
                if self._is_invoice_view_ready(driver):
                    return name

                after = [i for i in driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                         if i.is_displayed()]
                if len(after) < before_count:
                    return name  # 모달 사라짐 = 인증 성공

                if self._is_invoice_view_ready(driver):
                    return name

                # 실패: 다음 번호를 위해 입력창 갱신
                modal_inp = after[-1] if after else modal_inp

            except Exception:
                continue

        return None

    def _is_invoice_view_ready(self, driver) -> bool:
        try:
            elems = driver.find_elements(By.XPATH, "//*[self::button or self::a or self::span]")
            texts = [(elem.text or "").strip() for elem in elems if elem.is_displayed()]
            if any("XML" in text.upper() for text in texts):
                return True
            if any("인쇄" in text or "출력" in text or "전자세금계산서" in text for text in texts):
                return True
            return False
        except Exception:
            return False

    def _dismiss_notice_dialog(self, driver) -> None:
        for _ in range(4):
            accepted = self._accept_alert(driver, timeout=1)
            clicked = self._click_confirm_button(driver, timeout=2, reverse=True)
            if not accepted and not clicked:
                break
            time.sleep(1.0)

    def _accept_alert(self, driver, timeout: int = 1) -> bool:
        try:
            WebDriverWait(driver, timeout).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
            return True
        except Exception:
            return False

    def _click_confirm_button(self, driver, timeout: int = 3, reverse: bool = True) -> bool:
        selectors = [
            (By.CSS_SELECTOR, "button#confirm"),
            (By.XPATH, "//button[normalize-space()='확인' or contains(normalize-space(.),'확인')]"),
            (By.XPATH, "//a[normalize-space()='확인' or contains(normalize-space(.),'확인')]"),
            (By.XPATH, "//*[self::button or self::a or self::span or self::div][contains(@value,'확인') or contains(@title,'확인')]"),
        ]
        deadline = time.time() + timeout

        def try_current_context() -> bool:
            for by, sel in selectors:
                try:
                    elems = driver.find_elements(by, sel)
                    if reverse:
                        elems = list(reversed(elems))
                    for elem in elems:
                        try:
                            if not elem.is_displayed():
                                continue
                            driver.execute_script("arguments[0].click();", elem)
                            return True
                        except Exception:
                            continue
                except Exception:
                    continue
            return False

        while time.time() < deadline:
            try:
                driver.switch_to.default_content()
                if try_current_context():
                    return True
                frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
                for frame in frames:
                    try:
                        driver.switch_to.default_content()
                        driver.switch_to.frame(frame)
                        if try_current_context():
                            driver.switch_to.default_content()
                            return True
                    except Exception:
                        driver.switch_to.default_content()
                driver.switch_to.default_content()
            except Exception:
                pass
            time.sleep(0.3)
        return False

    def _click_xml(self, driver) -> bool:
        try:
            btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='XML']"))
            )
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
            return True
        except Exception:
            return False

    def _click_print(self, driver) -> bool:
        selectors_print = [
            "//button[normalize-space()='인쇄']",
            "//button[contains(.,'인쇄')]",
            "//button[contains(.,'출력')]",
            "//a[contains(.,'인쇄')]",
            "//a[contains(.,'출력')]",
            "//span[contains(.,'인쇄')]",
            "//*[contains(@title, '인쇄')]",
            "//*[contains(@alt, '인쇄')]",
            "//*[contains(@value, '인쇄')]",
            "//button[contains(.,'PDF')]",
            "//*[contains(@class, 'print')]",
        ]
        selectors_confirm = [
            "//button[contains(.,'확인')]",
            "//a[contains(.,'확인')]",
            "//span[contains(.,'확인')]",
            "//*[contains(@value, '확인')]",
        ]
        windows_before = len(driver.window_handles)

        def search_and_click(selectors, timeout=10, reverse=False):
            import time
            deadline = time.time() + timeout
            while time.time() < deadline:
                for sel in selectors:
                    try:
                        elems = driver.find_elements(By.XPATH, sel)
                        if reverse:
                            elems = list(reversed(elems))
                        for elem in elems:
                            if elem.is_displayed():
                                driver.execute_script("arguments[0].click();", elem)
                                return True
                    except Exception:
                        pass
                
                try:
                    frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
                    for frame in frames:
                        try:
                            driver.switch_to.frame(frame)
                            for sel in selectors:
                                elems = driver.find_elements(By.XPATH, sel)
                                if reverse:
                                    elems = list(reversed(elems))
                                for elem in elems:
                                    if elem.is_displayed():
                                        driver.execute_script("arguments[0].click();", elem)
                                        driver.switch_to.default_content()
                                        return True
                            driver.switch_to.default_content()
                        except Exception:
                            driver.switch_to.default_content()
                except Exception:
                    pass
                time.sleep(0.5)
            return False

        if not search_and_click(selectors_print, timeout=5):
            if self._click_confirm_button(driver, timeout=5, reverse=True) or search_and_click(selectors_confirm, timeout=2):
                import time
                time.sleep(1.5)
                self._accept_alert(driver, timeout=1)
                self._dismiss_notice_dialog(driver)
                 
                # 추가: 두 번째 모달 '확인' 버튼 클릭 (DOM의 마지막에 생성되는 모달 우선 클릭)
                self._click_confirm_button(driver, timeout=3, reverse=True) or search_and_click(selectors_confirm, timeout=3, reverse=True)
                
                if not search_and_click(selectors_print, timeout=15):
                    return False
            else:
                return False

        import time
        time.sleep(1)
        self._allow_chrome_permission_popup(driver, timeout=12)
        if len(driver.window_handles) > windows_before:
            driver.switch_to.window(driver.window_handles[-1])
        return True

    def _allow_chrome_permission_popup(self, driver, timeout: int = 8) -> bool:
        """
        Chrome 외부 앱 실행 권한 팝업에서 '허용' 버튼을 자동 클릭.
        WEHAGO 인쇄 버튼 이후 1회성 팝업이 뜨는 구조라, 브라우저 DOM이 아닌
        Chrome UI Automation 트리에서 탐색해야 한다.
        """
        prompt_hints = ("wehago.com", "다른 앱", "서비스에 액세스", "권한")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                desktop = Desktop(backend="uia")
                for win in desktop.windows():
                    try:
                        if not win.is_visible():
                            continue
                        wrapper = win.wrapper_object()
                        texts = []
                        for node in [wrapper, *wrapper.descendants()]:
                            try:
                                txt = (node.window_text() or "").strip()
                                if txt:
                                    texts.append(txt)
                            except Exception:
                                continue
                        merged = " ".join(texts).lower()
                        if not any(h.lower() in merged for h in prompt_hints):
                            continue

                        for btn in wrapper.descendants(control_type="Button"):
                            try:
                                caption = (btn.window_text() or "").strip()
                                if caption not in ("허용", "Allow", "열기", "Open"):
                                    continue
                                try:
                                    btn.set_focus()
                                    btn.click_input()
                                except Exception:
                                    btn.invoke()
                                time.sleep(1)
                                return True
                            except Exception:
                                continue
                    except Exception:
                        continue
            except Exception:
                pass
            time.sleep(0.4)
        return self._allow_chrome_permission_popup_by_xy(driver)

    def _allow_chrome_permission_popup_by_xy(self, driver, timeout: int = 8) -> bool:
        """UIA? ? ?? ?? Chrome ?? ??? ?? ??? ??? ??."""
        try:
            pos = driver.get_window_position()
            size = driver.get_window_size()
        except Exception:
            pos = {"x": 0, "y": 0}
            size = {"width": 1920, "height": 1080}

        origin_x = int(pos.get("x", 0))
        origin_y = int(pos.get("y", 0))
        width = int(size.get("width", 1920))
        # Chrome 권한 버블은 주소창 아래 좌측에 뜨며, 버튼 중심은 대략
        # 창 좌상단 기준 (400, 280)이다. 기존 좌표는 본문/체크박스 영역을 눌렀다.
        candidates = [
            (400, 280),
            (395, 278),
            (410, 280),
            (386, 278),
        ]
        if width < 1000:
            candidates = [(int(width * 0.42), 280), (int(width * 0.38), 278)] + candidates

        for dx, dy in candidates:
            try:
                pyautogui.click(origin_x + dx, origin_y + dy)
                time.sleep(0.8)
                return True
            except Exception:
                pass
        return False

    def _export_pdf_from_print_dialog(self, final_path, timeout: int = 30):
        dlg = self._wait_print_dialog(timeout=timeout)
        if not dlg:
            return None

        saved = None
        try:
            if not self._click_pdf_button(dlg):
                return None
            if not self._click_print_execute_button(dlg):
                return None

            saved = self._save_pdf_dialog(final_path, timeout=timeout)
            return saved
        finally:
            # The Duzon/WEHAGO preview is a separate Windows program. Close it
            # even when saving fails, otherwise the next crawl keeps reusing a
            # stale preview window.
            self._close_print_dialog(dlg)
            self._close_all_print_dialogs()

    def _wait_print_dialog(self, timeout: int = 20):
        deadline = time.time() + timeout
        title_patterns = (
            r".*인쇄 기본 설정 / 미리보기.*",
            r".*Duzon - PrintDialog.*",
        )

        while time.time() < deadline:
            for backend in ("uia", "win32"):
                for title_re in title_patterns:
                    try:
                        win = Desktop(backend=backend).window(title_re=title_re)
                        if win.exists(timeout=0.5):
                            wrap = win.wrapper_object()
                            try:
                                wrap.set_focus()
                            except Exception:
                                pass
                            return wrap
                    except Exception:
                        continue
            time.sleep(0.4)
        return None

    def _click_pdf_button(self, dlg) -> bool:
        try:
            for node in dlg.descendants():
                try:
                    txt = (node.window_text() or "").strip()
                    if txt != "PDF":
                        continue
                    try:
                        node.click_input()
                    except Exception:
                        try:
                            node.invoke()
                        except Exception:
                            pass
                    time.sleep(1)
                    return True
                except Exception:
                    continue
        except Exception:
            pass

        # Duzon/WEHAGO 미리보기는 서버 환경에서 PDF 버튼이 UIA 텍스트로
        # 노출되지 않는 경우가 있어, 마지막 수단으로 창 기준 상대좌표를 쓴다.
        try:
            rect = dlg.rectangle()
            candidates = [
                (280, 252),
                (292, 252),
                (270, 252),
                (280, 242),
                (292, 242),
                (280, 264),
            ]
            for dx, dy in candidates:
                pyautogui.click(rect.left + dx, rect.top + dy)
                time.sleep(0.5)
                return True
        except Exception:
            pass
        return False

    def _click_print_execute_button(self, dlg) -> bool:
        try:
            for node in dlg.descendants():
                try:
                    txt = (node.window_text() or "").strip()
                    if txt != "인쇄하기":
                        continue
                    try:
                        node.click_input()
                    except Exception:
                        try:
                            node.invoke()
                        except Exception:
                            pass
                    time.sleep(1)
                    return True
                except Exception:
                    continue
        except Exception:
            pass

        try:
            rect = dlg.rectangle()
            candidates = [
                (110, 114),
                (105, 110),
                (120, 115),
                (95, 112),
            ]
            for dx, dy in candidates:
                pyautogui.click(rect.left + dx, rect.top + dy)
                time.sleep(0.8)
                return True
        except Exception:
            pass
        return False

    def _save_pdf_dialog(self, final_path, timeout: int = 30):
        started_at = time.time()
        before_files = self.snapshot(".pdf")
        final_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + timeout

        while time.time() < deadline:
            direct = self.wait_new_file(".pdf", before_files, timeout=1)
            if direct:
                try:
                    if direct.resolve() != final_path.resolve():
                        direct.rename(final_path)
                    self._cleanup_saveas_new_folders(final_path, started_at)
                    return final_path
                except Exception:
                    self._cleanup_saveas_new_folders(final_path, started_at)
                    return direct

            try:
                dlg = Desktop(backend="win32").window(title="다른 이름으로 저장")
                if dlg.exists(timeout=0.5):
                    wrap = dlg.wrapper_object()
                    try:
                        wrap.set_focus()
                    except Exception:
                        pass
                    
                    import pyautogui
                    for key in ('alt', 'ctrl', 'shift', 'win'):
                        pyautogui.keyUp(key)
                    time.sleep(0.3)

                    success = self._set_save_as_filename_text(wrap, str(final_path))
                    if not success:
                        self._cleanup_saveas_new_folders(final_path, started_at)
                        self._write_saveas_debug(final_path, "saveas_filename_set_failed")
                        return None

                    if not self._click_save_as_save_button(wrap):
                        # Do not press Enter here. If the file list has focus,
                        # Enter can open/create the selected "새 폴더" item.
                        self._cleanup_saveas_new_folders(final_path, started_at)
                        self._write_saveas_debug(final_path, "saveas_save_button_not_clicked")
                        return None
                    time.sleep(0.5)

                    self._confirm_overwrite_dialog()

                    stable_deadline = time.time() + 15
                    while time.time() < stable_deadline:
                        if final_path.exists() and self._is_stable(final_path, interval=0.5):
                            self._cleanup_saveas_new_folders(final_path, started_at)
                            return final_path
                        recovered = self._recover_misplaced_pdf(final_path, started_at)
                        if recovered:
                            self._cleanup_saveas_new_folders(final_path, started_at)
                            return recovered
                        time.sleep(0.4)
            except Exception:
                pass
            time.sleep(0.3)

        fallback = self.wait_new_file(".pdf", before_files, timeout=2)
        if fallback:
            try:
                if fallback.resolve() != final_path.resolve():
                    fallback.rename(final_path)
                self._cleanup_saveas_new_folders(final_path, started_at)
                return final_path
            except Exception:
                self._cleanup_saveas_new_folders(final_path, started_at)
                return fallback
        recovered = self._recover_misplaced_pdf(final_path, started_at)
        if recovered:
            self._cleanup_saveas_new_folders(final_path, started_at)
            return recovered
        recovered = self._recover_pdf_from_saveas_new_folders(final_path, started_at)
        self._cleanup_saveas_new_folders(final_path, started_at)
        if recovered:
            return recovered
        return None

    def _recover_pdf_from_saveas_new_folders(self, final_path: Path, started_at: float):
        try:
            roots = [final_path.parent, Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Desktop"]
            candidates = []
            for root in roots:
                if not root.exists():
                    continue
                for folder in root.glob("새 폴더*"):
                    try:
                        if not folder.is_dir() or folder.stat().st_mtime < started_at - 10:
                            continue
                        for pdf in folder.glob("*.pdf"):
                            if pdf.stat().st_mtime >= started_at - 10 and self._is_stable(pdf, interval=0.5):
                                candidates.append(pdf)
                    except Exception:
                        continue
            for pdf in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    final_path.parent.mkdir(parents=True, exist_ok=True)
                    if final_path.exists():
                        final_path.unlink()
                    pdf.replace(final_path)
                    self._write_saveas_debug(final_path, f"recovered_from_new_folder={pdf}")
                    return final_path
                except Exception as exc:
                    self._write_saveas_debug(final_path, f"recover_failed={pdf} | {exc!r}")
        except Exception as exc:
            self._write_saveas_debug(final_path, f"recover_scan_failed={exc!r}")
        return None

    def _cleanup_saveas_new_folders(self, final_path: Path, started_at: float) -> None:
        roots = [final_path.parent, Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Desktop"]
        removed = []
        skipped = []
        for root in roots:
            try:
                if not root.exists():
                    continue
                for folder in root.glob("새 폴더*"):
                    try:
                        if not folder.is_dir() or folder.stat().st_mtime < started_at - 10:
                            continue
                        descendants = [p for p in folder.rglob("*")]
                        if any(p.is_file() and p.stat().st_mtime < started_at - 10 for p in descendants):
                            skipped.append(str(folder))
                            continue
                        shutil.rmtree(folder)
                        removed.append(str(folder))
                    except Exception as exc:
                        skipped.append(f"{folder} | {exc!r}")
            except Exception:
                continue
        if removed or skipped:
            self._write_saveas_debug(final_path, f"new_folder_cleanup removed={removed} skipped={skipped}")

    def _write_saveas_debug(self, final_path: Path, text: str) -> None:
        try:
            debug_path = final_path.parent / "_debug_wehago_saveas.txt"
            with open(debug_path, "a", encoding="utf-8") as f:
                f.write(time.strftime("[%Y-%m-%d %H:%M:%S] "))
                f.write(str(text))
                f.write("\n")
        except Exception:
            pass

    def _recover_misplaced_pdf(self, final_path: Path, started_at: float):
        """Microsoft Print to PDF sometimes ignores the target folder.
        If the correct filename was saved under Documents/Downloads/Desktop, move it back.
        """
        try:
            target_name = final_path.name
            roots = [
                final_path.parent,
                Path.home() / "Documents",
                Path.home() / "Downloads",
                Path.home() / "Desktop",
            ]
            seen = set()
            for root in roots:
                try:
                    root = root.resolve()
                except Exception:
                    continue
                if root in seen or not root.exists():
                    continue
                seen.add(root)
                candidates = []
                try:
                    candidates.extend(root.glob(target_name))
                    candidates.extend(root.glob(f"**/{target_name}"))
                except Exception:
                    continue
                for path in sorted(set(candidates), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
                    try:
                        if path.resolve() == final_path.resolve():
                            continue
                        if path.suffix.lower() != ".pdf" or path.name != target_name:
                            continue
                        if path.stat().st_mtime < started_at - 10:
                            continue
                        if not self._is_stable(path, interval=0.5):
                            continue
                        final_path.parent.mkdir(parents=True, exist_ok=True)
                        if final_path.exists():
                            final_path.unlink()
                        path.replace(final_path)
                        return final_path
                    except Exception:
                        continue
        except Exception:
            pass
        return None

    def _set_save_as_filename_text(self, dlg, text: str) -> bool:
        try:
            dlg_rect = dlg.rectangle()
            edits = []
            for node in dlg.descendants():
                try:
                    class_name = node.class_name() or ""
                    if class_name != "Edit":
                        continue
                    rect = node.rectangle()
                    if rect.top < dlg_rect.top + int(dlg_rect.height() * 0.50):
                        continue
                    edits.append((rect.top, rect.left, node))
                except Exception:
                    continue
            for _, _, node in sorted(edits, reverse=True):
                try:
                    node.set_focus()
                    node.set_edit_text(str(text))
                    time.sleep(0.2)
                    return True
                except Exception:
                    try:
                        node.set_focus()
                        node.type_keys("^a{BACKSPACE}", set_foreground=False)
                        node.type_keys(str(text), with_spaces=True, set_foreground=False)
                        time.sleep(0.2)
                        return True
                    except Exception:
                        continue
        except Exception:
            pass
        return False

    def _click_save_as_save_button(self, dlg) -> bool:
        save_markers = ("저장", "Save")
        blocked_markers = ("열기", "Open", "새 폴더", "New Folder")

        for _ in range(8):
            try:
                dlg_rect = dlg.rectangle()
                min_top = dlg_rect.bottom - 90
                min_left = dlg_rect.left + int(dlg_rect.width() * 0.55)
                for node in dlg.descendants():
                    try:
                        txt = (node.window_text() or "").strip()
                        class_name = node.class_name() or ""
                        if "Button" not in class_name and class_name not in ("Button",):
                            continue
                        rect = node.rectangle()
                        if rect.top < min_top or rect.left < min_left:
                            continue
                        if any(b in txt for b in blocked_markers):
                            continue
                        if not any(s in txt for s in save_markers):
                            continue
                        try:
                            node.set_focus()
                        except Exception:
                            pass
                        node.click_input()
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
            time.sleep(0.25)
        return False

    def _focus_save_as_filename_field(self, dlg) -> bool:
        try:
            dlg_rect = dlg.rectangle()
            edits = []
            for node in dlg.descendants():
                try:
                    if (node.class_name() or "") != "Edit":
                        continue
                    rect = node.rectangle()
                    edits.append((rect.top, rect.left, node))
                except Exception:
                    continue
            # Filename edit is the lower Edit control. Search/address edits are near the top.
            for _, _, node in sorted(edits, reverse=True):
                try:
                    rect = node.rectangle()
                    if rect.top < dlg_rect.top + int((dlg_rect.height()) * 0.55):
                        continue
                    node.click_input()
                    time.sleep(0.15)
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def _confirm_overwrite_dialog(self) -> None:
        for _ in range(8):
            for backend in ("win32", "uia"):
                try:
                    dlg = Desktop(backend=backend).window(title_re=r".*(확인|Confirm|바꾸기).*")
                    if not dlg.exists(timeout=0.2):
                        continue
                    wrap = dlg.wrapper_object()
                    title = (wrap.window_text() or "").strip()
                    if "다른 이름으로 저장" in title:
                        continue
                    try:
                        wrap.set_focus()
                    except Exception:
                        pass
                    saw_overwrite_text = False
                    for node in wrap.descendants():
                        try:
                            txt = (node.window_text() or "").strip()
                            if any(marker in txt for marker in ("이미", "존재", "바꾸", "덮어", "overwrite", "replace")):
                                saw_overwrite_text = True
                            if txt in ("예", "Yes", "확인", "저장", "바꾸기"):
                                node.click_input()
                                time.sleep(0.3)
                                return
                        except Exception:
                            continue
                    if saw_overwrite_text:
                        pyautogui.press("enter")
                        time.sleep(0.3)
                        return
                except Exception:
                    continue
            time.sleep(0.2)

    def _close_print_dialog(self, dlg) -> None:
        try:
            dlg.set_focus()
        except Exception:
            pass

        try:
            dlg.close()
            time.sleep(0.8)
            return
        except Exception:
            pass

        try:
            rect = dlg.rectangle()
            pyautogui.click(rect.right - 18, rect.top + 16)
            time.sleep(0.8)
            return
        except Exception:
            pass

        try:
            pyautogui.hotkey("alt", "f4")
            time.sleep(0.8)
        except Exception:
            pass

    def _close_all_print_dialogs(self) -> None:
        title_patterns = (
            r".*인쇄 기본 설정 / 미리보기.*",
            r".*Duzon.*Print.*",
            r".*WehagoPrint.*",
            r".*TX2A\.drf.*",
        )
        for _ in range(2):
            closed_any = False
            for backend in ("uia", "win32"):
                try:
                    for win in Desktop(backend=backend).windows():
                        title = (win.window_text() or "").strip()
                        if not any(re.search(pat, title, re.I) for pat in title_patterns):
                            continue
                        try:
                            win.close()
                            closed_any = True
                            time.sleep(0.3)
                            continue
                        except Exception:
                            pass
                        try:
                            rect = win.rectangle()
                            pyautogui.click(rect.right - 18, rect.top + 16)
                            closed_any = True
                            time.sleep(0.3)
                        except Exception:
                            pass
                except Exception:
                    pass
            if not closed_any:
                break

    @staticmethod
    def _paste_text(text: str) -> None:
        try:
            import win32clipboard
            import win32con
            import pyautogui
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, str(text))
            win32clipboard.CloseClipboard()
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                root.clipboard_clear()
                root.clipboard_append(str(text))
                root.update()
                root.destroy()
                import pyautogui
                pyautogui.hotkey("ctrl", "v")
            except Exception:
                pass

    @staticmethod
    def _parse_field(html: str, keywords: list[str]) -> str:
        for kw in keywords:
            m = re.search(rf'{kw}[^가-힣A-Za-z()]*([가-힣A-Za-z(주)㈜]+)', html)
            if m:
                return m.group(1).strip()
        return ""

    @staticmethod
    def _parse_amount(html: str) -> int:
        nums = [int(n.replace(",", "")) for n in re.findall(r"[\d,]{6,15}", html)
                if int(n.replace(",", "")) > 10000]
        return max(nums) if nums else 0

    @staticmethod
    def _to_int(value) -> int:
        return int(re.sub(r"[^\d]", "", str(value or "0")) or "0")


if __name__ == "__main__":
    print("[WEHAGO 단독 테스트]")
    print("메일에서 wehago.com 링크를 복사해서 붙여넣으세요.")
    url = input("URL: ").strip()
    mail_text = input("메일 키워드 (예: Acronis, Watching-On) [엔터=대승]: ").strip() or "대승"
    handler = WehagoHandler()
    res = handler.process(url=url, mail_text=mail_text, mail_date=time.strftime("%y%m%d"))
    print(f"\nok={res['ok']} | pdf={res.get('pdf_path')} | error={res.get('error')}")
    print(f"subject={res.get('subject')}")
