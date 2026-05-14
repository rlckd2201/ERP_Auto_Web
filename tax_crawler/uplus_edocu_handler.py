import configparser
import os
import re
import time
from pathlib import Path
from typing import Optional

import pyautogui
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from test_xml import parse_tax_invoice_xml


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_FILE = BASE_DIR / "config.ini"


class UplusEdocuHandler:
    """
    LG U+ eDocu 전용 처리기.

    기준 원칙
    - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름을 우선 사용
    - XML은 'xml파일받기' 버튼을 우선 클릭
    - XML은 다운로드 후 test_xml.parse_tax_invoice_xml()로 분석
    - XML은 분석 후 삭제 가능
    - 다운로드 경로는 config.ini 의 PATH.download_dir 와 동일하게 사용 가능
    """

    def __init__(
        self,
        download_dir: Optional[str] = None,
        wait_timeout: int = 15,
        config_path: Optional[str] = None,
        delete_xml_after_parse: bool = True,
    ):
        self.wait_timeout = wait_timeout
        self.delete_xml_after_parse = delete_xml_after_parse
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_FILE
        self.config = configparser.ConfigParser()
        self.download_dir = self._resolve_download_dir(download_dir)
        self._prepare_download_dir()

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    def process(
        self,
        url: str,
        candidate_nums: dict[str, str],
        mail_date: str,
        buyer_name: Optional[str] = None,
    ) -> dict:
        driver = None
        result = {
            "ok": False,
            "matched_biz_name": None,
            "xml_path": None,
            "xml_data": None,
            "xml_deleted": False,
            "pdf_path": None,
            "error": None,
        }

        print("=" * 80)
        print("[UPLUS] 처리 시작")
        print(f"[UPLUS] URL: {url}")
        print(f"[UPLUS] 다운로드 경로: {self.download_dir}")
        print(f"[UPLUS] 메일일자: {mail_date}")
        if buyer_name:
            print(f"[UPLUS] 공급받는자 후보: {buyer_name}")
        print(f"[UPLUS] 사업자번호 후보 수: {len(candidate_nums)}")

        try:
            self._prepare_download_dir()
            driver = self._build_driver()

            print("[STEP 1] 대상 URL 접속")
            driver.get(url)
            time.sleep(2)
            self._switch_to_latest_window(driver)
            print(f"[STEP 1] 현재 창 수: {len(driver.window_handles)}")

            print("[STEP 2] 사업자번호 인증 시도")
            matched_biz_name = self._unlock_with_business_no(driver, candidate_nums)
            if not matched_biz_name:
                raise RuntimeError("사업자번호 인증 실패")

            result["matched_biz_name"] = matched_biz_name
            print(f"[STEP 2] 인증 성공 법인: {matched_biz_name}")

            print("[STEP 3] 인증 후 최신 창 재확인")
            time.sleep(2)
            self._switch_to_latest_window(driver)
            print(f"[STEP 3] 현재 URL: {driver.current_url}")

            print("[STEP 4] XML 다운로드 및 분석")
            xml_path, xml_data, xml_deleted = self._download_and_parse_xml(
                driver=driver,
                mail_date=mail_date,
                matched_biz_name=matched_biz_name,
                buyer_name=buyer_name,
            )
            result["xml_path"] = xml_path
            result["xml_data"] = xml_data
            result["xml_deleted"] = xml_deleted

            print("[STEP 5] PDF 저장 시작")
            pdf_path = self._save_pdf_via_print(driver, mail_date, matched_biz_name, xml_data)
            result["pdf_path"] = pdf_path
            result["ok"] = True
            print("[UPLUS] 처리 완료")
            print("=" * 80)
            return result

        except Exception as e:
            result["error"] = str(e)
            print(f"[UPLUS][오류] {e}")
            print("=" * 80)
            return result
        finally:
            if driver is not None:
                try:
                    driver.quit()
                    print("[UPLUS] 브라우저 종료 완료")
                except Exception as e:
                    print(f"[UPLUS] 브라우저 종료 중 예외: {e}")

    # ------------------------------------------------------------------
    # config / path
    # ------------------------------------------------------------------
    def _resolve_download_dir(self, download_dir: Optional[str]) -> Path:
        if download_dir:
            print(f"[CONFIG] 인자로 받은 다운로드 경로 사용: {download_dir}")
            return Path(download_dir).expanduser().resolve()

        if self.config_path.exists():
            print(f"[CONFIG] 설정 파일 로드: {self.config_path}")
            self.config.read(self.config_path, encoding="utf-8")
            ini_dir = self.config.get("PATH", "download_dir", fallback=r"Z:\계산서")
            print(f"[CONFIG] config.ini PATH.download_dir 사용: {ini_dir}")
            return Path(ini_dir).expanduser().resolve()

        print(f"[CONFIG] 설정 파일 없음, 기본 경로 사용: Z:/계산서")
        return Path(r"Z:\계산서").expanduser().resolve()

    def _prepare_download_dir(self):
        print(f"[PATH] 다운로드 경로 점검 시작: {self.download_dir}")
        self.download_dir.mkdir(parents=True, exist_ok=True)

        if not self.download_dir.exists() or not self.download_dir.is_dir():
            raise RuntimeError(f"다운로드 경로 생성 실패: {self.download_dir}")

        # 사전 권한 점검: XML/PDF 다운로드 전에 쓰기 가능 여부 확인
        probe = self.download_dir / f".__write_test_{int(time.time() * 1000)}.tmp"
        try:
            with open(probe, "w", encoding="utf-8") as fp:
                fp.write("write_test")
            probe.unlink(missing_ok=True)
            print("[PATH] 쓰기 권한 확인 완료")
        except Exception as e:
            raise RuntimeError(
                f"다운로드 경로 쓰기 권한 없음: {self.download_dir} / {e}"
            )

        self._cleanup_stale_downloads()

    def _cleanup_stale_downloads(self):
        stale_patterns = ["*.crdownload", "*.tmp"]
        removed = 0
        for pattern in stale_patterns:
            for path in self.download_dir.glob(pattern):
                try:
                    path.unlink()
                    removed += 1
                except Exception:
                    pass
        print(f"[PATH] 잔여 임시 다운로드 파일 정리: {removed}건")

    # ------------------------------------------------------------------
    # driver / window
    # ------------------------------------------------------------------
    def _build_driver(self):
        print("[BROWSER] Chrome 드라이버 생성 시작")
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--kiosk-printing")
        options.add_argument("--disable-popup-blocking")
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": str(self.download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "plugins.always_open_pdf_externally": True,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.default_content_settings.popups": 0,
            },
        )
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # 다운로드 경로를 CDP 에도 강제 지정해 XML 권한/경로 이슈를 줄임
        try:
            driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": str(self.download_dir)},
            )
            print("[BROWSER] Page.setDownloadBehavior 적용 완료")
        except Exception as e:
            print(f"[BROWSER] Page.setDownloadBehavior 실패: {e}")
            try:
                driver.execute_cdp_cmd(
                    "Browser.setDownloadBehavior",
                    {
                        "behavior": "allow",
                        "downloadPath": str(self.download_dir),
                        "eventsEnabled": False,
                    },
                )
                print("[BROWSER] Browser.setDownloadBehavior 적용 완료")
            except Exception as e2:
                print(f"[BROWSER] Browser.setDownloadBehavior 실패: {e2}")

        print("[BROWSER] Chrome 드라이버 생성 완료")
        return driver

    def _switch_to_latest_window(self, driver):
        if driver.window_handles:
            current = driver.current_window_handle
            latest = driver.window_handles[-1]
            if current != latest:
                print(f"[WINDOW] 최신 창으로 전환: {latest}")
            driver.switch_to.window(latest)

    # ------------------------------------------------------------------
    # auth
    # ------------------------------------------------------------------
    def _unlock_with_business_no(self, driver, candidate_nums: dict[str, str]) -> Optional[str]:
        for idx, (name, biz_no) in enumerate(candidate_nums.items(), start=1):
            try:
                print(f"[AUTH] ({idx}/{len(candidate_nums)}) {name} 사업자번호 입력 시도")
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password'], input[type='text']")
                target_input = next((inp for inp in inputs if inp.is_displayed()), None)
                if not target_input:
                    print("[AUTH] 표시된 입력창을 찾지 못함")
                    return None

                target_input.clear()
                target_input.send_keys(biz_no)
                target_input.send_keys(Keys.RETURN)
                time.sleep(1.5)

                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    alert.accept()
                    print(f"[AUTH] 실패 - {name}: {alert_text}")
                    continue
                except Exception:
                    print(f"[AUTH] 성공 - {name}")
                    return name
            except Exception as e:
                print(f"[AUTH] 입력 오류 - {name}: {e}")
                continue
        return None

    # ------------------------------------------------------------------
    # xml
    # ------------------------------------------------------------------
    def _download_and_parse_xml(
        self,
        driver,
        mail_date: str,
        matched_biz_name: str,
        buyer_name: Optional[str],
    ) -> tuple[Optional[str], Optional[dict], bool]:
        xml_deleted = False
        xml_path_str: Optional[str] = None
        parsed: Optional[dict] = None

        print("[XML] 다운로드 전 다운로드 폴더 재점검")
        self._prepare_download_dir()
        before_files = self._snapshot_files("*.xml")
        print(f"[XML] 다운로드 전 XML 파일 수: {len(before_files)}")

        clicked = self._try_click_xml(driver)
        if not clicked:
            print("[XML] xml파일받기 버튼/링크를 찾지 못함")
            return None, None, False

        self._handle_post_click_alert(driver)

        xml_file = self._wait_new_file("*.xml", before_files, timeout=15)
        if not xml_file:
            print("[XML] 클릭 후 XML 파일 생성 확인 실패")
            return None, None, False

        print(f"[XML] 다운로드 감지: {xml_file.name}")
        xml_file = self._normalize_xml_filename(xml_file, mail_date, matched_biz_name, buyer_name)
        xml_path_str = str(xml_file)
        print(f"[XML] 파일명 정리 완료: {xml_file.name}")

        try:
            print(f"[XML] 분석 시작: {xml_file}")
            supplier_dict, buyer_dict, content_dict = parse_tax_invoice_xml(str(xml_file))
            parsed = {
                "supplier": supplier_dict,
                "buyer": buyer_dict,
                "content": content_dict,
            }
            print(
                "[XML] 분석 완료 "
                f"공급자={supplier_dict.get('상호')} / "
                f"공급받는자={buyer_dict.get('상호')} / "
                f"공급가액={content_dict.get('공급가액')}"
            )
        except Exception as e:
            print(f"[XML] 분석 실패: {e}")
        finally:
            if self.delete_xml_after_parse and xml_file.exists():
                try:
                    xml_file.unlink()
                    xml_deleted = True
                    print(f"[XML] 분석 후 XML 삭제 완료: {xml_file.name}")
                except Exception as e:
                    print(f"[XML] XML 삭제 실패: {e}")

        return xml_path_str, parsed, xml_deleted

    def _handle_post_click_alert(self, driver):
        time.sleep(1.0)
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            print(f"[XML] 클릭 후 alert 감지: {alert_text}")
        except Exception:
            print("[XML] 클릭 후 alert 없음")

    def _try_click_xml(self, driver) -> bool:
        print("[XML] 'xml파일받기' 버튼 우선 탐색")

        exact_css = [
            "input[value='xml파일받기']",
            "button[value='xml파일받기']",
            "button[title='xml파일받기']",
            "a[title='xml파일받기']",
            "input[value='XML파일받기']",
            "button[value='XML파일받기']",
        ]
        for css in exact_css:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, css)
                for elem in elems:
                    if elem.is_displayed():
                        print(f"[XML] exact css 클릭 성공: {css}")
                        driver.execute_script("arguments[0].click();", elem)
                        return True
            except Exception as e:
                print(f"[XML] exact css 탐색 예외: {css} / {e}")

        exact_xpaths = [
            "//input[@value='xml파일받기']",
            "//input[@value='XML파일받기']",
            "//button[normalize-space()='xml파일받기']",
            "//button[normalize-space()='XML파일받기']",
            "//a[normalize-space()='xml파일받기']",
            "//a[normalize-space()='XML파일받기']",
            "//*[(@value='출력' or normalize-space()='출력')]/following-sibling::*[1][@value='xml파일받기' or normalize-space()='xml파일받기' or @value='XML파일받기' or normalize-space()='XML파일받기']",
        ]
        for xp in exact_xpaths:
            try:
                elems = driver.find_elements(By.XPATH, xp)
                for elem in elems:
                    if elem.is_displayed():
                        print(f"[XML] exact xpath 클릭 성공: {xp}")
                        driver.execute_script("arguments[0].click();", elem)
                        return True
            except Exception as e:
                print(f"[XML] exact xpath 탐색 예외: {xp} / {e}")

        print("[XML] exact 탐색 실패, 일반 XML 관련 셀렉터 탐색")
        general_selectors = [
            "a[href$='.xml']",
            "a[href*='xml']",
            "button[data-type*='xml']",
            "a[data-type*='xml']",
            "img[alt*='xml']",
        ]
        for css in general_selectors:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, css)
                for elem in elems:
                    if elem.is_displayed():
                        print(f"[XML] general css 클릭 성공: {css}")
                        driver.execute_script("arguments[0].click();", elem)
                        return True
            except Exception:
                pass

        text_candidates = [
            "xml파일받기",
            "XML파일받기",
            "XML",
            "xml",
            "원본",
            "원문",
            "전자세금계산서",
            "다운로드",
            "내려받기",
            "저장",
        ]
        for txt in text_candidates:
            xpaths = [
                f"//a[contains(normalize-space(.), '{txt}')]",
                f"//button[contains(normalize-space(.), '{txt}')]",
                f"//span[contains(normalize-space(.), '{txt}')]",
                f"//input[contains(@value, '{txt}')]",
                f"//*[contains(@title, '{txt}')]",
                f"//*[contains(@alt, '{txt}')]",
            ]
            for xp in xpaths:
                try:
                    elems = driver.find_elements(By.XPATH, xp)
                    for elem in elems:
                        if elem.is_displayed():
                            print(f"[XML] text xpath 클릭 성공: {xp}")
                            driver.execute_script("arguments[0].click();", elem)
                            return True
                except Exception:
                    pass

        print("[XML] 메인 문서 탐색 실패, iframe 내부 탐색 시작")
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for idx, frame in enumerate(iframes, start=1):
                try:
                    driver.switch_to.frame(frame)
                    print(f"[XML] iframe 탐색: {idx}/{len(iframes)}")
                    clicked = self._try_click_xml_in_current_context(driver)
                    driver.switch_to.default_content()
                    if clicked:
                        return True
                except Exception as e:
                    print(f"[XML] iframe 탐색 실패: {idx} / {e}")
                    driver.switch_to.default_content()
                    continue
        except Exception as e:
            print(f"[XML] iframe 목록 조회 실패: {e}")
            driver.switch_to.default_content()

        return False

    def _try_click_xml_in_current_context(self, driver) -> bool:
        local_xpaths = [
            "//input[contains(@value, 'xml파일받기')]",
            "//button[contains(normalize-space(.), 'xml파일받기')]",
            "//a[contains(normalize-space(.), 'xml파일받기')]",
            "//input[contains(@value, 'XML')]",
            "//a[contains(., 'XML')]",
            "//button[contains(., 'XML')]",
            "//a[contains(., '다운로드')]",
            "//button[contains(., '다운로드')]",
            "//a[contains(@href, 'xml')]",
        ]
        for xp in local_xpaths:
            try:
                elems = driver.find_elements(By.XPATH, xp)
                for elem in elems:
                    if elem.is_displayed():
                        print(f"[XML] iframe xpath 클릭 성공: {xp}")
                        driver.execute_script("arguments[0].click();", elem)
                        return True
            except Exception:
                pass
        return False

    # ------------------------------------------------------------------
    # pdf
    # ------------------------------------------------------------------
    def _save_pdf_via_print(self, driver, mail_date: str, matched_biz_name: str, xml_data: Optional[dict]) -> str:
        temp_filename = f"temp_{int(time.time())}.pdf"
        temp_path = self.download_dir / temp_filename

        print(f"[PDF] 임시 파일명: {temp_filename}")
        print("[PDF] 인쇄창 호출 전 포커스 이동")
        pyautogui.click(x=pyautogui.size().width / 2, y=100)
        time.sleep(0.5)

        print("[PDF] window.print() 실행")
        driver.execute_script("window.print();")
        time.sleep(1)

        print("[PDF] Ctrl+S 저장창 호출")
        pyautogui.hotkey("ctrl", "s")
        time.sleep(3.5)

        print(f"[PDF] 절대경로 저장 로직 실행: {temp_path}")
        try:
            from pywinauto import Desktop
            dlg = Desktop(backend="win32").window(title="다른 이름으로 저장")
            if dlg.exists(timeout=2):
                wrap = dlg.wrapper_object()
                try:
                    wrap.set_focus()
                except:
                    pass
                
                # Release stuck keys
                for key in ('alt', 'ctrl', 'shift', 'win'):
                    pyautogui.keyUp(key)
                time.sleep(0.3)

                success = False
                try:
                    dlg_rect = wrap.rectangle()
                    edits = []
                    for node in wrap.descendants():
                        try:
                            if (node.class_name() or "") == "Edit":
                                rect = node.rectangle()
                                if rect.top > dlg_rect.top + int(dlg_rect.height() * 0.5):
                                    edits.append((rect.top, node))
                        except:
                            pass
                    if edits:
                        edits.sort(key=lambda x: x[0], reverse=True)
                        for _, edit in edits:
                            try:
                                edit.set_focus()
                                edit.set_edit_text(str(temp_path))
                                time.sleep(0.1)
                                edit.type_keys("{ENTER}", set_foreground=False)
                                success = True
                                time.sleep(0.5)
                                break
                            except:
                                pass
                except:
                    pass

                if not success:
                    # Fallback if pywinauto fails
                    pyautogui.hotkey("ctrl", "a")
                    time.sleep(0.1)
                    pyperclip.copy(str(temp_path))
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.3)
                    
                    try:
                        save_btn = wrap.child_window(title_re=".*저장.*", control_type="Button")
                        save_btn.click_input()
                    except:
                        pyautogui.press("enter")
                    time.sleep(0.5)
        except Exception as e:
            print(f"[PDF] 저장 다이얼로그 제어 실패: {e}")

        time.sleep(4.5)

        if not temp_path.exists():
            raise RuntimeError(f"PDF 저장 실패: {temp_path}")

        final_name = self._build_pdf_filename(mail_date, matched_biz_name, xml_data)
        final_path = self._dedupe_path(self.download_dir / final_name)
        print(f"[PDF] 최종 파일명: {final_path.name}")
        temp_path.rename(final_path)
        print(f"[PDF] 저장 완료: {final_path}")
        return str(final_path)

    def _build_pdf_filename(self, mail_date: str, matched_biz_name: str, xml_data: Optional[dict]) -> str:
        if xml_data:
            supplier = xml_data.get("supplier", {})
            buyer = xml_data.get("buyer", {})
            content = xml_data.get("content", {})
            items = content.get("품목") or []
            item_name = self._safe_name((items[0].get("적요") if items else None) or "품목미상", limit=24)
            extra = f"_외{len(items) - 1}건" if len(items) > 1 else ""
            issue_date = self._digits_only(content.get("작성일자"))
            if len(issue_date) == 6:
                issue_date = "20" + issue_date
            if len(issue_date) < 8:
                issue_date = self._digits_only(mail_date)
                if len(issue_date) == 6:
                    issue_date = "20" + issue_date
            if len(issue_date) < 8:
                issue_date = time.strftime("%Y%m%d")
            buyer_name = self._safe_name(buyer.get("상호") or matched_biz_name or "사업장미상", limit=20)
            supplier_name = self._safe_name(supplier.get("상호") or "공급자미상", limit=20)
            amount = self._digits_only(content.get("합계금액") or content.get("공급가액")) or "0"
            return f"{issue_date}_{buyer_name}_{supplier_name}_{item_name}{extra}_{amount}원.pdf"

        issue_date = self._digits_only(mail_date)
        if len(issue_date) == 6:
            issue_date = "20" + issue_date
        if len(issue_date) < 8:
            issue_date = time.strftime("%Y%m%d")
        return f"{issue_date}_{self._safe_name(matched_biz_name or '사업장미상', limit=20)}_공급자미상_품목미상_0원.pdf"

    # ------------------------------------------------------------------
    # file utils
    # ------------------------------------------------------------------
    def _snapshot_files(self, pattern: str) -> set[str]:
        return {str(p.resolve()) for p in self.download_dir.glob(pattern)}

    def _wait_new_file(self, pattern: str, before_files: set[str], timeout: int = 10) -> Optional[Path]:
        end_time = time.time() + timeout
        while time.time() < end_time:
            current_files = [p for p in self.download_dir.glob(pattern) if p.is_file()]
            for path in current_files:
                resolved = str(path.resolve())
                if resolved not in before_files:
                    if self._is_file_stable(path):
                        return path
            time.sleep(0.5)
        return None

    def _is_file_stable(self, path: Path, interval: float = 1.0) -> bool:
        try:
            size1 = path.stat().st_size
            time.sleep(interval)
            size2 = path.stat().st_size
            stable = size1 == size2 and size2 > 0
            print(f"[FILE] 안정화 확인: {path.name} / {size1} -> {size2} / stable={stable}")
            return stable
        except Exception as e:
            print(f"[FILE] 파일 안정화 확인 실패: {path} / {e}")
            return False

    def _normalize_xml_filename(
        self,
        xml_path: Path,
        mail_date: str,
        matched_biz_name: str,
        buyer_name: Optional[str],
    ) -> Path:
        buyer = self._safe_name(buyer_name or matched_biz_name)
        target = self._dedupe_path(self.download_dir / f"{buyer}_{mail_date}.xml")
        if xml_path.resolve() != target.resolve():
            print(f"[XML] 파일명 변경: {xml_path.name} -> {target.name}")
            xml_path.rename(target)
        return target

    def _dedupe_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        idx = 1
        while True:
            candidate = path.with_name(f"{stem}_{idx}{suffix}")
            if not candidate.exists():
                print(f"[FILE] 중복 파일명 조정: {candidate.name}")
                return candidate
            idx += 1

    @staticmethod
    def _digits_only(value) -> str:
        if value is None:
            return ""
        return re.sub(r"[^\d]", "", str(value))

    @staticmethod
    def _safe_name(value: str, limit: int = 30) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9가-힣_\-]", "", str(value or ""))
        return cleaned[:limit] if cleaned else "미상"


if __name__ == "__main__":
    SAMPLE_CANDIDATES = {
        "대승_1공장": "1258105619",
        "대승_2공장": "4038507607",
        "대승_5공장": "4038523311",
    }

    handler = UplusEdocuHandler()
    result = handler.process(
        url="https://edocu.uplus.co.kr/",
        candidate_nums=SAMPLE_CANDIDATES,
        mail_date=time.strftime("%y%m%d"),
        buyer_name="주식회사 대승",
    )
    print(result)
