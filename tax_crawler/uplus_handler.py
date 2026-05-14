import time
import os
import re
import configparser
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import test_xml

BIZ_GROUPS = {
    "대승정밀": {"키워드": ["대승정밀", "(주)대승정밀", "대승정밀(주)", "주식회사 대승정밀"], "번호": ["1258132697", "4038515640", "8448500770", "1188507029"]},
    "대승": {"키워드": ["(주)대승", "대승", "대승(주)", "주식회사 대승"], "번호": ["1258105619", "4038507607", "4038523311"]},
    "일강": {"키워드": ["(주)일강", "일강", "일강(주)", "주식회사 일강"], "번호": ["1258151622", "4038520895"]},
    "더원": {"키워드": ["(주)더원", "더원", "더원(주)", "주식회사 더원"], "번호": ["4218602723"]},
    "제이엠": {"키워드": ["(주)제이엠", "제이엠", "제이엠(주)", "주식회사 제이엠"], "번호": ["1258154876"]},
}

class UplusEDocuHandler:
    def __init__(self, config_file: str = "config.ini"):
        self.config = configparser.ConfigParser()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = config_file if os.path.isabs(config_file) else os.path.join(self.base_dir, config_file)
        self.download_dir = r"C:\ERP_DB\downloads"
        self.load_config()
        os.makedirs(self.download_dir, exist_ok=True)

    def load_config(self):
        self.config.read(self.config_path, encoding="utf-8")
        self.download_dir = self.config.get("PATH", "download_dir", fallback=self.download_dir)

    def log(self, message: str):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

    def infer_and_build_nos(self, mail_text):
        clean_text = re.sub(r"\s+", "", mail_text)
        matched_corp = None
        
        for corp in sorted(BIZ_GROUPS.keys(), key=len, reverse=True):
            if corp in clean_text:
                matched_corp = corp
                break
                
        if not matched_corp:
            for corp in sorted(BIZ_GROUPS.keys(), key=len, reverse=True):
                for kw in BIZ_GROUPS[corp]["키워드"]:
                    if re.sub(r"\s+", "", kw) in clean_text:
                        matched_corp = corp
                        break
                if matched_corp: break

        prefixes = [h.replace('-', '') for h in re.findall(r'(\d{3}-\d{2})', mail_text)]
        
        if matched_corp:
            self.log(f"[분석] 법인 특정 완료: {matched_corp}")
            nos = BIZ_GROUPS[matched_corp]["번호"]
            if prefixes:
                matched, unmatched = [], []
                for n in nos:
                    if any(n.startswith(p) for p in prefixes): matched.append(n)
                    else: unmatched.append(n)
                return matched + unmatched
            return nos
        else:
            self.log("[분석] 법인 특정 실패. 전체 번호 중 마스킹 일치 검사")
            if prefixes:
                return [n for info in BIZ_GROUPS.values() for n in info["번호"] if any(n.startswith(p) for p in prefixes)]
            return []

    def get_latest_downloaded_file(self, ext: str, start_time: float, timeout: int = 15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            files = [os.path.join(self.download_dir, f) for f in os.listdir(self.download_dir) if f.lower().endswith(ext)]
            files = [f for f in files if os.path.isfile(f) and os.path.getmtime(f) >= start_time]
            files.sort(key=os.path.getmtime, reverse=True)
            if files and not files[0].endswith('.crdownload'):
                return files[0]
            time.sleep(0.5)
        return None

    # 🚨 [신규 추가] 승인 버튼 선행 클릭 로직
    def click_approve_button(self, driver):
        xpaths = [
            "//img[@alt='승인']", 
            "//img[contains(@src, 'btn_ok')]", 
            "//img[contains(@src, 'btn_app')]", 
            "//a[contains(text(), '승인')]",
            "//input[@value='승인']"
        ]
        
        def attempt_click():
            for xpath in xpaths:
                try:
                    elem = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    driver.execute_script("arguments[0].click();", elem)
                    time.sleep(1)
                    # 승인 누른 후 나오는 확인창(Alert) 방어막
                    try:
                        alert = driver.switch_to.alert
                        alert.accept()
                        time.sleep(1)
                    except: pass
                    return True
                except: pass
            return False

        if attempt_click():
            self.log("[승인처리] 메인 프레임에서 '승인' 버튼 클릭 완료")
            time.sleep(2)
            return True
            
        frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
        for frame in frames:
            try:
                driver.switch_to.frame(frame)
                if attempt_click():
                    self.log("[승인처리] 하위 프레임에서 '승인' 버튼 클릭 완료")
                    driver.switch_to.default_content()
                    time.sleep(2)
                    return True
                driver.switch_to.default_content()
            except:
                driver.switch_to.default_content()
                
        self.log("[승인처리] 승인 버튼 없음 (이미 승인된 문서로 간주하고 진행)")
        return False

    def click_xml_button(self, driver):
        xpaths = ["//input[@value='xml파일받기']", "//a[contains(@href,'getXmlFile')]", "//img[contains(@src,'xml') or contains(@src,'XML')]", "//*[contains(text(),'xml파일받기')]"]
        for xpath in xpaths:
            try:
                elem = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                driver.execute_script("arguments[0].click();", elem)
                return True
            except: pass
            
        frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
        for frame in frames:
            try:
                driver.switch_to.frame(frame)
                for xpath in xpaths:
                    try:
                        elem = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                        driver.execute_script("arguments[0].click();", elem)
                        driver.switch_to.default_content()
                        return True
                    except: pass
                driver.switch_to.default_content()
            except: driver.switch_to.default_content()
        return False

    def click_preview_print_button(self, driver):
        xpaths = ["//img[@id='previewPrint']", "//img[@alt='출력']", "//div[contains(@class,'print_view')]//img", "//img[contains(@src,'btn_popup_print')]"]
        for xpath in xpaths:
            try:
                elem = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                driver.execute_script("arguments[0].click();", elem)
                self.log("[PDF작업] 출력 버튼 1회 클릭 완료 (다운로드 트리거)")
                return True
            except: pass
        return False

    def build_pdf_filename_from_xml(self, xml_dict: dict) -> str:
        def clean_text(text: str, max_len: int = 20) -> str:
            text = re.sub(r"[\r\n\t\f\v]+", "", str(text or ""))
            text = re.sub(r"\s+", "", text)
            text = re.sub(r"[^0-9A-Za-z가-힣_-]", "", text)
            return text[:max_len] if text else "미상"

        supplier = xml_dict.get("공급자", {}) if isinstance(xml_dict, dict) else {}
        buyer = xml_dict.get("공급받는자", {}) if isinstance(xml_dict, dict) else {}
        content_dict = xml_dict.get("내용", {}) if isinstance(xml_dict, dict) else {}

        issue_date = re.sub(r"[^0-9]", "", str(content_dict.get("작성일자", "")))
        if len(issue_date) == 6:
            issue_date = "20" + issue_date
        if len(issue_date) < 8:
            issue_date = time.strftime("%Y%m%d")

        items = content_dict.get("품목", []) or []
        first_item = items[0] if items and isinstance(items[0], dict) else {}
        item_name = clean_text(first_item.get("적요") or first_item.get("품목명") or "품목미상", 24)
        extra = f"_외{len(items) - 1}건" if len(items) > 1 else ""
        supplier_name = clean_text(supplier.get("상호") or "공급자미상", 20)
        buyer_name = clean_text(buyer.get("상호") or "사업장미상", 20)
        total_amount = re.sub(r"[^0-9]", "", str(content_dict.get("합계금액") or content_dict.get("공급가액") or "0")) or "0"

        return f"{issue_date}_{buyer_name}_{supplier_name}_{item_name}{extra}_{total_amount}원.pdf"

    def process(self, payload):
        url, mail_text = payload.url, getattr(payload, "mail_text", "")
        all_nos = self.infer_and_build_nos(mail_text)
        
        corp_name = getattr(payload, "corp_name", None)
        if not corp_name:
            clean_text = re.sub(r"\s+", "", mail_text)
            for corp in sorted(BIZ_GROUPS.keys(), key=len, reverse=True):
                if corp in clean_text:
                    corp_name = corp
                    break

        options = Options()
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True, 
            "profile.default_content_setting_values.automatic_downloads": 1,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", prefs)
        options.add_argument("--start-maximized")
        options.add_argument("--kiosk-printing")
        options.add_argument("--safebrowsing-disable-download-protection")
        options.add_argument("--safebrowsing-disable-extension-blacklist")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            driver.get(url)
            time.sleep(3)
            auth_ok, matched_biz_no = False, None

            for no in all_nos:
                self.log(f"[암호해제] 사업자번호 대입 시도: {no}")
                inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.get_attribute("type") in ["text", "password", "number", "tel"]]
                if not inputs: 
                    auth_ok = True
                    break
                try:
                    inputs[0].clear()
                    inputs[0].send_keys(no)
                    time.sleep(0.5)
                    inputs[0].send_keys(Keys.RETURN)
                    time.sleep(2.0)
                    try:
                        alert = driver.switch_to.alert
                        alert.accept()
                        self.log(f"[암호해제] 실패: {no}")
                    except:
                        if "올바르지 않습니다" in driver.page_source or "일치하지 않습니다" in driver.page_source: 
                            self.log(f"[암호해제] 실패: {no}")
                            continue
                        auth_ok, matched_biz_no = True, no
                        self.log(f"[암호해제] 성공: {no}")
                        break
                except Exception: continue

            if not auth_ok: return {"ok": False, "message": "모든 번호 해제 실패"}
            time.sleep(2)
            if len(driver.window_handles) > 1: driver.switch_to.window(driver.window_handles[-1])

            # 🚨 [신규 추가] 다운로드 시도 전에 무조건 승인 버튼부터 찾아서 누릅니다.
            self.click_approve_button(driver)

            start_time = time.time()
            if not self.click_xml_button(driver): return {"ok": False, "message": "XML 버튼 없음"}

            xml_path = self.get_latest_downloaded_file('.xml', start_time)
            if not xml_path: return {"ok": False, "message": "XML 파일 다운로드 실패"}
            
            try:
                WebDriverWait(driver, 2).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
            except: pass

            xml_data = test_xml.parse_tax_invoice_xml(xml_path)
            xml_dict = {"공급자": xml_data[0], "공급받는자": xml_data[1], "내용": xml_data[2]} if isinstance(xml_data, tuple) else xml_data
            
            pdf_start_time = time.time()
            if not self.click_preview_print_button(driver): return {"ok": False, "message": "출력 창 진입 실패"}
            
            self.log("[PDF작업] 순정 원본 1개 다운로드 대기 중...")
            
            raw_pdf_path = self.get_latest_downloaded_file('.pdf', pdf_start_time, timeout=15)
            if not raw_pdf_path:
                return {"ok": False, "message": "순정 PDF 다운로드 시간 초과"}

            final_pdf_name = self.build_pdf_filename_from_xml(xml_dict)
            final_pdf_path = os.path.join(self.download_dir, final_pdf_name)
            
            time.sleep(2) 
            
            try:
                if os.path.exists(final_pdf_path): 
                    os.remove(final_pdf_path)
                os.rename(raw_pdf_path, final_pdf_path)
                self.log(f"[PDF작업] 파일명 변경 완벽 성공: {final_pdf_path}")
            except Exception as e:
                self.log(f"[PDF작업] 경고: 이름 변경 실패 ({e}). 원본 유지: {raw_pdf_path}")
                final_pdf_path = raw_pdf_path

            try:
                supplier = xml_dict.get("공급자", {})
                receiver = xml_dict.get("공급받는자", {})
                content = xml_dict.get("내용", {})

                vendor_name = supplier.get("상호", "") or "매입처"
                site_name = receiver.get("상호", "") or corp_name or "사업장미상"
                
                def clean_num(val):
                    try: return int(re.sub(r'[^0-9]', '', str(val)))
                    except: return 0
                    
                total_tax = clean_num(content.get("세액", 0))
                total_sum = clean_num(content.get("합계액", 0))

                raw_items = content.get("품목", [])
                if not isinstance(raw_items, list): raw_items = [raw_items]
                
                formatted_items = []
                for it in raw_items:
                    qty = clean_num(it.get("수량", 1))
                    val = clean_num(it.get("공급가액", 0))
                    name = it.get("적요", "") or it.get("품목명", "") or "품목"
                    formatted_items.append({
                        "account": "소모품비", 
                        "inc_vat": val,
                        "qty": qty if qty > 0 else 1,
                        "name": name
                    })

                client_data = {
                    "vendor_name": vendor_name,
                    "site_name": site_name,
                    "total_tax": total_tax,
                    "total_sum": total_sum,
                    "items": formatted_items
                }
                
                subject_text = f"[{site_name}] {vendor_name} 세금계산서 ({total_sum:,}원)"

            except Exception as e:
                self.log(f"[데이터 가공 실패] {e}")
                client_data = xml_dict
                subject_text = f"[{corp_name}] 새 세금계산서 수신"

            return {
                "ok": True,
                "corp_name": corp_name,
                "matched_biz_no": matched_biz_no,
                "mail_date": getattr(payload, "mail_date", ""),
                "subject": subject_text,
                "data": client_data,
                "url": url,
                "xml_path": xml_path,
                "pdf_path": final_pdf_path,
                "xml_data": xml_dict
            }

        except Exception as e: 
            return {"ok": False, "message": str(e)}
        finally: 
            try: driver.quit()
            except: pass
