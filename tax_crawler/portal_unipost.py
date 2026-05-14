"""
유니포스트 etax 세금계산서 핸들러
대상: etax.unipost.co.kr
"""
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_handler import BaseTaxInvoiceHandler
from xml_parser import parse_tax_invoice_xml


class UnipostHandler(BaseTaxInvoiceHandler):

    DOMAIN = "etax.unipost.co.kr"

    @property
    def portal_name(self) -> str:
        return "unipost"

    def supports(self, url: str) -> bool:
        return self.DOMAIN in url

    def _do_process(self, driver, url, mail_text, mail_date, result):
        candidates = self.build_candidate_nos(mail_text)
        if not candidates:
            result["error"] = "유니포스트 법인명 식별 실패 (mail_text에 법인명 포함 필요)"
            return

        # 일부 링크는 클릭 시 새 창을 열기도 함
        old_handles = driver.window_handles[:]
        driver.get(url)
        time.sleep(2)
        new_handles = [h for h in driver.window_handles if h not in old_handles]
        if new_handles:
            driver.switch_to.window(new_handles[-1])

        matched = self._auth(driver, candidates)
        if not matched:
            result["error"] = "사업자번호 인증 실패"
            return

        self._ensure_checkbox(driver)
        self._click_confirm(driver)

        # XML 다운로드
        xml_snap = self.snapshot(".xml")
        self._click_xml(driver)
        xml_file = self.wait_new_file(".xml", xml_snap, timeout=10)
        if not xml_file:
            result["error"] = "XML 다운로드 실패"
            return

        supplier, buyer, content = parse_tax_invoice_xml(str(xml_file))
        try:
            xml_file.unlink()
        except Exception:
            pass

        # PDF 출력/다운로드
        pdf_snap = self.snapshot(".pdf")
        self._click_print(driver)
        pdf_file = self.wait_new_file(".pdf", pdf_snap, timeout=20)
        if not pdf_file:
            result["error"] = "PDF 다운로드 실패"
            return

        items = content.get("항목", [])
        final_name = self.build_pdf_filename(
            issue_date=content.get("작성일자", mail_date),
            buyer=buyer.get("상호", ""),
            supplier=supplier.get("상호", ""),
            item=items[0].get("품목", "품목미상") if items else "품목미상",
            extra=f"_외{len(items)-1}건" if len(items) > 1 else "",
            amount=content.get("합계금액", "0"),
            buyer_biz_no=buyer.get("등록번호", ""),
        )
        final_path = self.dedupe_path(self.download_dir / final_name)
        time.sleep(1)
        pdf_file.rename(final_path)

        result.update({
            "ok": True,
            "pdf_path": str(final_path),
            "subject": self._build_subject(buyer, supplier, content),
            "data": self._build_data(supplier, buyer, content),
        })

    # ------------------------------------------------------------------
    def _auth(self, driver, candidates: dict) -> str | None:
        for name, no in candidates.items():
            try:
                inputs = driver.find_elements(By.CSS_SELECTOR,
                    "input[type='text'], input[type='number'], input[type='tel'], input[type='password']")
                visible = [i for i in inputs if i.is_displayed() and not i.get_attribute("readonly")]
                if not visible:
                    return "already_open"

                if len(visible) >= 3:
                    # 사업자번호 3칸 분리 입력 (xxx-xx-xxxxx)
                    visible[0].clear(); visible[0].send_keys(no[:3])
                    visible[1].clear(); visible[1].send_keys(no[3:5])
                    visible[2].clear(); visible[2].send_keys(no[5:])
                    time.sleep(0.5)
                    visible[2].send_keys(Keys.RETURN)
                else:
                    visible[0].clear()
                    visible[0].send_keys(no)
                    time.sleep(0.5)
                    visible[0].send_keys(Keys.RETURN)

                time.sleep(1.5)
                src = driver.page_source
                if "올바르지 않" in src or "일치하지 않" in src:
                    try:
                        driver.find_element(By.XPATH,
                            "//button[contains(text(),'확인')] | //button[contains(@class,'close')]").click()
                        time.sleep(0.5)
                    except Exception:
                        pass
                    continue

                try:
                    driver.switch_to.alert.accept()
                    continue
                except Exception:
                    pass

                return name
            except Exception:
                continue
        return None

    def _ensure_checkbox(self, driver) -> bool:
        for sel in ["input[type='checkbox']", "#agreeYn", "#consentYn",
                    "input[name='agreeYn']", "input[name='consentYn']"]:
            try:
                for elem in driver.find_elements(By.CSS_SELECTOR, sel):
                    if elem.is_displayed() and not elem.is_selected():
                        driver.execute_script("arguments[0].click();", elem)
                        time.sleep(0.5)
                        return True
            except Exception:
                pass
        return False

    def _click_confirm(self, driver) -> bool:
        for xp in ["//button[contains(.,'확인')]", "//button[contains(.,'승인')]",
                   "//button[contains(.,'조회')]", "//a[contains(.,'확인')]",
                   "//input[@type='button' and contains(@value,'확인')]"]:
            try:
                elem = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp)))
                driver.execute_script("arguments[0].click();", elem)
                time.sleep(1)
                return True
            except Exception:
                pass
        return False

    def _click_xml(self, driver) -> bool:
        for xp in ["//a[contains(.,'XML')]", "//button[contains(.,'XML')]",
                   "//a[contains(.,'원본')]", "//button[contains(.,'원본')]",
                   "//a[contains(.,'다운로드')]", "//button[contains(.,'다운로드')]"]:
            try:
                elem = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xp)))
                driver.execute_script("arguments[0].click();", elem)
                time.sleep(2)
                return True
            except Exception:
                pass
        return False

    def _click_print(self, driver) -> bool:
        for by, sel in [
            (By.ID, "previewPrint"),
            (By.XPATH, "//button[contains(.,'인쇄')]"),
            (By.XPATH, "//a[contains(.,'인쇄')]"),
            (By.XPATH, "//button[contains(.,'출력')]"),
            (By.XPATH, "//a[contains(.,'출력')]"),
            (By.XPATH, "//button[contains(.,'PDF')]"),
            (By.XPATH, "//a[contains(.,'PDF')]"),
        ]:
            try:
                windows_before = len(driver.window_handles)
                elem = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, sel)))
                driver.execute_script("arguments[0].click();", elem)
                time.sleep(1)
                if len(driver.window_handles) > windows_before:
                    driver.switch_to.window(driver.window_handles[-1])
                return True
            except Exception:
                pass
        return False

    @staticmethod
    def _build_subject(buyer, supplier, content) -> str:
        site   = buyer.get("상호", "사업장미상")
        vendor = supplier.get("상호", "매입처")
        amount = re.sub(r"[^\d]", "", str(content.get("합계금액", "0"))) or "0"
        return f"[{site}] {vendor} 세금계산서 ({int(amount):,}원)"

    @staticmethod
    def _build_data(supplier, buyer, content) -> dict:
        def to_int(v):
            try:
                return int(re.sub(r"[^\d]", "", str(v or "0")))
            except Exception:
                return 0
        items = [
            {"name": it.get("품목", ""), "qty": 1,
             "inc_vat": to_int(it.get("공급가액")), "account": "소모품비"}
            for it in content.get("항목", [])
        ]
        return {
            "vendor_name": supplier.get("상호", ""),
            "site_name":   buyer.get("상호", ""),
            "total_tax":   to_int(content.get("세액")),
            "total_sum":   to_int(content.get("합계금액")),
            "items":       items,
        }


if __name__ == "__main__":
    print("[유니포스트 etax 단독 테스트]")
    url = input("etax.unipost.co.kr 링크 붙여넣기: ").strip()
    mail_text = input("메일 키워드 (예: 대승, 일강) [엔터=대승]: ").strip() or "대승"
    handler = UnipostHandler()
    res = handler.process(url=url, mail_text=mail_text, mail_date=time.strftime("%y%m%d"))
    print(f"\nok={res['ok']} | pdf={res.get('pdf_path')} | error={res.get('error')}")
