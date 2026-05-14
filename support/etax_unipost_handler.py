import os
import re
import time
import configparser
import xml.etree.ElementTree as ET
from dataclasses import asdict
from typing import Optional, Dict, Tuple
from urllib.parse import urlparse

import pyautogui
import pyperclip

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager

from uplus_handler import BIZ_GROUPS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")

class EtaxUnipostHandler:
    XML_NS = {"ns": "urn:kr:or:kec:standard:Tax:ReusableAggregateBusinessInformationEntitySchemaModule:1:0"}
    DOMAIN = "etax.unipost.co.kr"

    def __init__(self, config_file: str = CONFIG_FILE):
        self.config = configparser.ConfigParser()
        self.config.read(config_file, encoding="utf-8")
        self.download_dir = self.config.get("PATH", "download_dir", fallback=r"C:\ERP_DB\downloads")
        self.wait_sec = self.config.getint("SELENIUM", "wait_sec", fallback=15)
        self.print_wait_sec = self.config.getfloat("SELENIUM", "print_wait_sec", fallback=4.5)
        os.makedirs(self.download_dir, exist_ok=True)

    def supports(self, url: str) -> bool:
        return (urlparse(url).hostname or "").lower() == self.DOMAIN

    def create_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--kiosk-printing")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    @staticmethod
    def safe_filename(text: str, limit: int = 40) -> str:
        text = re.sub(r"[^a-zA-Z0-9가-힣._-]", "", text or "")
        return text[:limit] if text else "미상"

    def build_candidate_nums(self, hint_text: str = "") -> Dict[str, str]:
        candidates: Dict[str, str] = {}
        hint_text = hint_text or ""
        sorted_groups = sorted(BIZ_GROUPS.items(), key=lambda x: max(len(k) for k in x[1]["키워드"]), reverse=True)
        for group_name, info in sorted_groups:
            if any(keyword in hint_text for keyword in info["키워드"]):
                for i, no in enumerate(info["번호"]):
                    candidates[f"{group_name}_{i}"] = no
        if not candidates:
            for group_name, info in BIZ_GROUPS.items():
                for i, no in enumerate(info["번호"]):
                    candidates[f"{group_name}_{i}"] = no
        return candidates

    @staticmethod
    def text_or_none(elem):
        if elem is None or elem.text is None: return None
        return elem.text.strip() or None

    def find_text(self, parent, path: str):
        if parent is None: return None
        return self.text_or_none(parent.find(path, self.XML_NS))

    @staticmethod
    def format_biz_no(raw: Optional[str]) -> Optional[str]:
        if not raw: return None
        digits = "".join(ch for ch in str(raw) if ch.isdigit())
        if len(digits) == 10: return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        return raw

    @staticmethod
    def format_date_yyyymmdd(raw: Optional[str]) -> Optional[str]:
        if not raw: return None
        digits = "".join(ch for ch in str(raw) if ch.isdigit())
        if len(digits) >= 8: return f"{digits[:4]}/{digits[4:6]}/{digits[6:8]}"
        return raw

    @staticmethod
    def split_classification(value: Optional[str]) -> list:
        if not value: return []
        return [x.strip() for x in str(value).split(",") if x.strip()]

    def parse_tax_invoice_xml(self, xml_path: str):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        doc = root.find("ns:TaxInvoiceDocument", self.XML_NS)
        settlement = root.find("ns:TaxInvoiceTradeSettlement", self.XML_NS)
        exchanged_document = root.find("ns:ExchangedDocument", self.XML_NS)

        invoicer = settlement.find("ns:InvoicerParty", self.XML_NS) if settlement is not None else None
        invoicee = settlement.find("ns:InvoiceeParty", self.XML_NS) if settlement is not None else None
        money = settlement.find("ns:SpecifiedMonetarySummation", self.XML_NS) if settlement is not None else None

        supplier_dict = {
            "등록번호": self.format_biz_no(self.find_text(invoicer, "ns:ID")),
            "상호": self.find_text(invoicer, "ns:NameText"),
            "대표자명": self.find_text(invoicer, "ns:SpecifiedPerson/ns:NameText"),
            "사업장주소": self.find_text(invoicer, "ns:SpecifiedAddress/ns:LineOneText"),
            "업태": self.find_text(invoicer, "ns:TypeCode"),
            "종목": self.split_classification(self.find_text(invoicer, "ns:ClassificationCode")),
        }

        buyer_dict = {
            "등록번호": self.format_biz_no(self.find_text(invoicee, "ns:ID")),
            "상호": self.find_text(invoicee, "ns:NameText"),
            "대표자명": self.find_text(invoicee, "ns:SpecifiedPerson/ns:NameText"),
            "사업장주소": self.find_text(invoicee, "ns:SpecifiedAddress/ns:LineOneText"),
            "업태": self.find_text(invoicee, "ns:TypeCode"),
            "종목": self.split_classification(self.find_text(invoicee, "ns:ClassificationCode")),
        }

        items = []
        for item in root.findall("ns:TaxInvoiceTradeLineItem", self.XML_NS):
            purchase_date = self.find_text(item, "ns:PurchaseExpiryDateTime")
            items.append({
                "월": purchase_date[4:6] if purchase_date and len(purchase_date) >= 8 else None,
                "일": purchase_date[6:8] if purchase_date and len(purchase_date) >= 8 else None,
                "적요": self.find_text(item, "ns:NameText"),
                "규격": None, "수량": None, "단가": None,
                "공급가액": self.find_text(item, "ns:InvoiceAmount"),
                "세액": self.find_text(item, "ns:TotalTax/ns:CalculatedAmount"),
                "비고": None,
            })

        content_dict = {
            "작성일자": self.format_date_yyyymmdd(self.find_text(doc, "ns:IssueDateTime")),
            "공급가액": self.find_text(money, "ns:ChargeTotalAmount"),
            "세액": self.find_text(money, "ns:TaxTotalAmount"),
            "품목": items,
            "합계금액": self.find_text(money, "ns:GrandTotalAmount"),
            "비고": self.find_text(doc, "ns:DescriptionText"),
            "승인번호": self.find_text(doc, "ns:IssueID"),
            "일련번호": self.find_text(exchanged_document.find("ns:ReferencedDocument", self.XML_NS) if exchanged_document is not None else None, "ns:ID"),
        }
        return supplier_dict, buyer_dict, content_dict

    def open_url_and_follow_new_window(self, driver: webdriver.Chrome, url: str) -> None:
        old_handles = driver.window_handles[:]
        driver.get(url)
        time.sleep(2)
        if len(driver.window_handles) > len(old_handles):
            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(old_handles))
            new_handles = [h for h in driver.window_handles if h not in old_handles]
            if new_handles:
                driver.switch_to.window(new_handles[-1])

    def unlock_document(self, driver: webdriver.Chrome, candidate_nums: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        for biz_name, biz_no in candidate_nums.items():
            try:
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='number'], input[type='tel'], input[type='password']")
                visible_inputs = [inp for inp in inputs if inp.is_displayed() and not inp.get_attribute("readonly")]
                if not visible_inputs: continue

                if len(visible_inputs) >= 3:
                    visible_inputs[0].clear()
                    visible_inputs[0].send_keys(biz_no[:3])
                    visible_inputs[1].clear()
                    visible_inputs[1].send_keys(biz_no[3:5])
                    visible_inputs[2].clear()
                    visible_inputs[2].send_keys(biz_no[5:])
                    time.sleep(0.5)
                    visible_inputs[2].send_keys(Keys.RETURN)
                else:
                    visible_inputs[0].clear()
                    visible_inputs[0].send_keys(biz_no)
                    time.sleep(0.5)
                    visible_inputs[0].send_keys(Keys.RETURN)
                
                time.sleep(1.5)

                page_text = driver.page_source
                if "올바르지 않습니다" in page_text or "일치하지 않습니다" in page_text:
                    print(f"❌ [오답] {biz_name}({biz_no}) 튕김. 다음 번호 시도.")
                    try:
                        driver.find_element(By.XPATH, "//button[contains(text(), '확인')] | //button[contains(@class, 'close')]").click()
                        time.sleep(0.5)
                    except: pass
                    continue
                
                try:
                    driver.switch_to.alert.accept()
                    continue
                except: pass

                print(f"✅ [정답] {biz_name}({biz_no}) 해제 성공!")
                return biz_name, biz_no
            except Exception:
                continue
        return None, None

    def ensure_approval_checked(self, driver: webdriver.Chrome) -> bool:
        for selector in ["input[type='checkbox']", "#agreeYn", "#consentYn", "input[name='agreeYn']", "input[name='consentYn']"]:
            try:
                for elem in driver.find_elements(By.CSS_SELECTOR, selector):
                    if elem.is_displayed() and not elem.is_selected():
                        driver.execute_script("arguments[0].click();", elem)
                        time.sleep(0.5)
                        return True
            except: pass
        return False

    def click_confirm_or_next(self, driver: webdriver.Chrome) -> bool:
        for xpath in ["//button[contains(., '확인')]", "//button[contains(., '승인')]", "//button[contains(., '조회')]", "//a[contains(., '확인')]", "//a[contains(., '승인')]", "//input[@type='button' and contains(@value, '확인')]"]:
            try:
                elem = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                driver.execute_script("arguments[0].click();", elem)
                time.sleep(1)
                return True
            except: pass
        return False

    def click_xml_download(self, driver: webdriver.Chrome) -> bool:
        for xpath in ["//a[contains(., 'XML')]", "//button[contains(., 'XML')]", "//a[contains(., '원본')]", "//button[contains(., '원본')]", "//a[contains(., '다운로드')]", "//button[contains(., '다운로드')]"]:
            try:
                elem = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                driver.execute_script("arguments[0].click();", elem)
                time.sleep(2)
                return True
            except: pass
        return False

    def click_pdf_or_print_entry(self, driver: webdriver.Chrome) -> bool:
        for by, selector in [(By.ID, "previewPrint"), (By.XPATH, "//button[contains(., '인쇄')]"), (By.XPATH, "//a[contains(., '인쇄')]"), (By.XPATH, "//button[contains(., '출력')]"), (By.XPATH, "//a[contains(., '출력')]"), (By.XPATH, "//button[contains(., 'PDF')]"), (By.XPATH, "//a[contains(., 'PDF')]")]:
            try:
                elem = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, selector)))
                windows_before = len(driver.window_handles)
                driver.execute_script("arguments[0].click();", elem)
                time.sleep(1)
                if len(driver.window_handles) > windows_before:
                    driver.switch_to.window(driver.window_handles[-1])
                return True
            except: pass
        return False

    def get_latest_downloaded_file(self, ext: str, wait_sec: int = 10) -> Optional[str]:
        deadline = time.time() + wait_sec
        ext = ext.lower()
        while time.time() < deadline:
            files = [os.path.join(self.download_dir, n) for n in os.listdir(self.download_dir) if n.lower().endswith(ext)]
            files = sorted([f for f in files if os.path.isfile(f)], key=os.path.getmtime, reverse=True)
            if files and not files[0].endswith(".crdownload"): return files[0]
            time.sleep(1)
        return None

    def save_current_page_as_pdf(self, driver: webdriver.Chrome, save_path: str) -> bool:
        pyautogui.click(x=pyautogui.size().width / 2, y=100)
        time.sleep(0.5)
        driver.execute_script("window.print();")
        time.sleep(1)
        pyautogui.hotkey("ctrl", "s")
        time.sleep(3.5)
        pyautogui.hotkey("alt", "d")
        time.sleep(0.5)
        pyperclip.copy(os.path.dirname(save_path))
        pyautogui.hotkey("ctrl", "v")
        pyautogui.press("enter")
        time.sleep(1.0)
        pyautogui.hotkey("alt", "n")
        time.sleep(0.5)
        pyperclip.copy(os.path.basename(save_path))
        pyautogui.hotkey("ctrl", "v")
        pyautogui.press("enter")
        time.sleep(self.print_wait_sec)
        return os.path.exists(save_path)

    def rename_file_by_xml(self, xml_info: dict, pdf_path: str, mail_date: str) -> str:
        supplier = xml_info.get("supplier", {})
        buyer = xml_info.get("buyer", {})
        content = xml_info.get("content", {})
        items = content.get("품목", [])
        issue_date = re.sub(r"[^0-9]", "", str(content.get("작성일자") or mail_date or ""))
        if len(issue_date) == 6:
            issue_date = "20" + issue_date
        if len(issue_date) < 8:
            issue_date = time.strftime("%Y%m%d")
        supplier_name = self.safe_filename(supplier.get("상호") or "공급자미상", 20)
        buyer_name = self.safe_filename(buyer.get("상호") or "사업장미상", 20)
        amount = self.safe_filename(str(content.get("합계금액") or content.get("공급가액") or "0"), 20)
        item_name = self.safe_filename(items[0].get("적요") or "품목미상", 24) if items else "품목미상"
        suffix = f"_외{len(items) - 1}건" if len(items) > 1 else ""
        final_name = f"{issue_date}_{buyer_name}_{supplier_name}_{item_name}{suffix}_{amount}원.pdf"
        final_path = os.path.join(self.download_dir, final_name)
        if os.path.abspath(pdf_path) != os.path.abspath(final_path):
            if os.path.exists(final_path): os.remove(final_path)
            os.rename(pdf_path, final_path)
        return final_path

    def process(self, payload) -> dict:
        if hasattr(payload, "__dict__"): payload = asdict(payload)
        url = payload["url"]
        mail_text = payload.get("mail_text", "")
        mail_date = payload.get("mail_date", time.strftime("%y%m%d"))
        candidates = self.build_candidate_nums(mail_text)
        driver = self.create_driver()
        result = {
            "success": False, "site": self.DOMAIN, "url": url, "matched_biz_name": None,
            "matched_biz_no": None, "xml_path": None, "pdf_path": None, "final_pdf_path": None,
            "xml_analysis": None, "error": None,
        }
        try:
            self.open_url_and_follow_new_window(driver, url)
            biz_name, biz_no = self.unlock_document(driver, candidates)
            if not biz_no:
                print("💡 [경고] 예상 번호 실패! 전체 사업자번호로 무차별 대입을 시작합니다.")
                biz_name, biz_no = self.unlock_document(driver, self.build_candidate_nums(""))
                if not biz_no:
                    result["error"] = "사업자번호 전체 대입 실패"
                    return result

            result["matched_biz_name"] = biz_name
            result["matched_biz_no"] = biz_no
            self.ensure_approval_checked(driver)
            self.click_confirm_or_next(driver)
            self.click_xml_download(driver)
            xml_path = self.get_latest_downloaded_file(".xml", wait_sec=10)
            if not xml_path:
                result["error"] = "XML 다운로드 실패"
                return result
            result["xml_path"] = xml_path
            supplier_dict, buyer_dict, content_dict = self.parse_tax_invoice_xml(xml_path)
            result["xml_analysis"] = {"supplier": supplier_dict, "buyer": buyer_dict, "content": content_dict}
            self.click_pdf_or_print_entry(driver)
            temp_pdf = os.path.join(self.download_dir, f"temp_{int(time.time())}.pdf")
            saved = self.save_current_page_as_pdf(driver, temp_pdf)
            if not saved:
                result["error"] = "PDF 저장 실패"
                return result
            result["pdf_path"] = temp_pdf
            result["final_pdf_path"] = self.rename_file_by_xml(result["xml_analysis"], temp_pdf, mail_date)
            result["success"] = True
            return result
        except Exception as e:
            result["error"] = str(e)
            return result
        finally:
            try: driver.quit()
            except: pass
