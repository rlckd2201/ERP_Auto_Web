import os
import re
import time
import configparser
import unicodedata
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from biz_groups import BIZ_GROUPS, FACTORY_MAP

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "config.ini"
DEFAULT_DOWNLOAD = Path(r"C:\ERP_DB\downloads")
DEFAULT_CHROME_PROFILE = Path(r"C:\ERP_DB\chrome_profile")


class BaseTaxInvoiceHandler(ABC):
    """
    세금계산서 포털별 핸들러 공통 베이스.
    각 포털 핸들러는 이 클래스를 상속하고 supports() / _do_process() 를 구현한다.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config = configparser.ConfigParser()
        cfg = config_path or DEFAULT_CONFIG
        if cfg.exists():
            self.config.read(cfg, encoding="utf-8")
        self.download_dir = Path(
            self.config.get("PATH", "download_dir", fallback=str(DEFAULT_DOWNLOAD))
        ).resolve()
        self.wait_sec = self.config.getint("SELENIUM", "wait_sec", fallback=15)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 공개 인터페이스 (서버에서 호출하는 유일한 메서드)
    # ------------------------------------------------------------------
    @abstractmethod
    def supports(self, url: str) -> bool:
        """이 핸들러가 처리 가능한 URL인지 반환."""

    def process(self, url: str, mail_text: str = "", mail_date: str = "", mail_subject: str = "") -> dict:
        """
        통일 반환값:
        {
            "ok": bool,
            "portal": str,
            "pdf_path": str | None,
            "subject": str,
            "data": { vendor_name, site_name, total_sum, items:[...] },
            "error": str | None,
        }
        """
        if not mail_date:
            mail_date = time.strftime("%y%m%d")
        result = {
            "ok": False, "portal": self.portal_name,
            "pdf_path": None, "subject": "", "data": {}, "error": None,
        }
        self._mail_subject = str(mail_subject or "")
        driver = self._build_driver()
        try:
            self._do_process(driver, url, mail_text, mail_date, result)
        except Exception as e:
            result["error"] = str(e)
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        return result

    # ------------------------------------------------------------------
    # 하위 클래스 구현 대상
    # ------------------------------------------------------------------
    @property
    @abstractmethod
    def portal_name(self) -> str:
        """포털 식별자 (로그/반환값용)"""

    @abstractmethod
    def _do_process(self, driver, url, mail_text, mail_date, result: dict) -> None:
        """실제 크롤링 로직. result dict를 직접 채운다."""

    # ------------------------------------------------------------------
    # 공통 유틸: 사업자번호 후보 조합
    # ------------------------------------------------------------------
    def build_candidate_nos(self, mail_text: str = "") -> dict[str, str]:
        """메일 본문에서 법인 키워드를 찾아 사업자번호 후보 dict 반환."""
        clean = re.sub(r"\s+", "", str(mail_text or ""))
        for grp, info in sorted(
            BIZ_GROUPS.items(),
            key=lambda x: max(len(k) for k in x[1]["키워드"]),
            reverse=True,
        ):
            if any(re.sub(r"\s+", "", kw) in clean for kw in info["키워드"]):
                return {f"{grp}_{i}": no for i, no in enumerate(info["번호"])}
        return {}

    def _build_driver(self) -> webdriver.Chrome:
        options = Options()
        profile_dir = Path(
            self.config.get("PATH", "chrome_profile_dir", fallback=str(DEFAULT_CHROME_PROFILE))
        )
        profile_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--kiosk-printing")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_experimental_option("prefs", {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "profile.default_content_settings.popups": 0,
        })
        driver = webdriver.Chrome(service=self._get_chromedriver_service(), options=options)
        try:
            driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": str(self.download_dir)},
            )
        except Exception:
            pass
        return driver

    @staticmethod
    def _get_chromedriver_service() -> Service:
        """캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치."""
        # 1. WDM 캐시 경로 탐색 (이미 설치된 경우 빠르게 재사용)
        try:
            wdm_base = Path.home() / ".wdm" / "drivers" / "chromedriver" / "win64"
            if wdm_base.exists():
                candidates = sorted(wdm_base.rglob("chromedriver.exe"), reverse=True)
                if candidates:
                    return Service(str(candidates[0]))
        except Exception:
            pass
        # 2. ChromeDriverManager 자동 설치/다운로드
        from webdriver_manager.chrome import ChromeDriverManager
        return Service(ChromeDriverManager().install())

    # ------------------------------------------------------------------
    # 공통 유틸: 파일 대기
    # ------------------------------------------------------------------
    def wait_new_file(self, ext: str, before_files: set, timeout: int = 15) -> Optional[Path]:
        ext = ext.lower()
        deadline = time.time() + timeout
        while time.time() < deadline:
            for p in self.download_dir.iterdir():
                if p.suffix.lower() == ext and str(p.resolve()) not in before_files:
                    if not p.name.endswith(".crdownload") and self._is_stable(p):
                        return p
            time.sleep(0.5)
        return None

    def snapshot(self, ext: str) -> set:
        return {str(p.resolve()) for p in self.download_dir.glob(f"*{ext}")}

    @staticmethod
    def _is_stable(path: Path, interval: float = 1.0) -> bool:
        try:
            s1 = path.stat().st_size
            time.sleep(interval)
            s2 = path.stat().st_size
            return s1 == s2 and s2 > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 공통 유틸: 파일명 생성
    # ------------------------------------------------------------------
    @staticmethod
    def safe_name(text: str, limit: int = 30) -> str:
        text = unicodedata.normalize("NFKC", str(text or "")).strip()
        text = text.replace("㈜", "(주)")
        text = re.sub(r'[\\/:*?"<>|]+', " ", text)
        text = re.sub(r'\s+', " ", text)
        text = re.sub(r'[^0-9A-Za-z가-힣()&._ -]+', "", text)
        text = text.strip(" ._-")
        return (text[:limit].strip() or "미상")

    @staticmethod
    def digits_only(value) -> str:
        return re.sub(r"[^\d]", "", str(value or ""))

    def build_pdf_filename(self, issue_date: str, buyer: str, supplier: str,
                           item: str, extra: str, amount: str,
                           buyer_biz_no: str = "", buyer_site: str = "") -> str:
        supplier_name = self.safe_name(supplier or "업체명", 30)
        system_name = self.safe_name(item or "시스템명", 30)
        buyer_name = self._buyer_label(buyer, buyer_biz_no, buyer_site)
        period_label = self._period_label(issue_date, supplier_name, system_name)
        return f"세금계산서 - {supplier_name}({system_name})_{buyer_name}_{period_label}.pdf"

    def _buyer_label(self, buyer: str, buyer_biz_no: str = "", buyer_site: str = "") -> str:
        buyer_name = self.safe_name(buyer or "법인명", 30)
        site_name = buyer_site or self._site_name_from_biz_no(buyer_biz_no)
        if site_name:
            return f"{buyer_name}({self.safe_name(site_name, 20)})"
        return buyer_name

    def _period_label(self, issue_date: str, supplier: str = "", item: str = "") -> str:
        year, month = self._year_month(issue_date)
        key = self._period_rule_key(supplier, item)
        if key == "previous_month":
            year, month = self._add_months(year, month, -1)
            return f"{year:04d}년 {month:02d}월"
        if key == "dlp_round":
            return self._dlp_period_label(year, month)
        return f"{year:04d}년 {month:02d}월"

    @staticmethod
    def _year_month(value: str) -> tuple[int, int]:
        digits = re.sub(r"[^\d]", "", str(value or ""))
        if len(digits) == 6:
            digits = "20" + digits
        if len(digits) >= 6:
            year = int(digits[:4])
            month = int(digits[4:6])
            if 1 <= month <= 12:
                return year, month
        now = time.localtime()
        return now.tm_year, now.tm_mon

    @staticmethod
    def _period_rule_key(supplier: str, item: str) -> str:
        item_key = re.sub(r"\s+", "", str(item or "").lower())
        supplier_key = re.sub(r"\s+", "", str(supplier or "").lower())
        joined_key = f"{item_key} {supplier_key}"

        if "dlp" in item_key or "dlp" in supplier_key:
            return "dlp_round"
        previous_markers = [
            "kt",
            "고객사vpn",
            "customervpn",
            "sdwan",
            "watching-on",
            "watchingon",
            "acronis",
        ]
        if any(marker in item_key for marker in previous_markers):
            return "previous_month"
        if any(marker in supplier_key for marker in previous_markers):
            return "previous_month"
        current_markers = [
            "그룹웨어",
            "다우오피스",
            "daouoffice",
            "daou",
            "nac",
        ]
        if any(marker in item_key for marker in current_markers):
            return "current_month"
        if any(marker in supplier_key for marker in current_markers):
            return "current_month"
        return "current_month"

    @staticmethod
    def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
        total = year * 12 + (month - 1) + delta
        return total // 12, total % 12 + 1

    def _dlp_period_label(self, year: int, month: int) -> str:
        if 3 <= month <= 5:
            return f"{year:04d}년 03~05월 1차"
        if 6 <= month <= 8:
            return f"{year:04d}년 06~08월 2차"
        if 9 <= month <= 11:
            return f"{year:04d}년 09~11월 3차"
        start_year = year if month == 12 else year - 1
        end_year = start_year + 1
        if start_year == end_year:
            return f"{start_year:04d}년 12~02월 4차"
        return f"{start_year:04d}년 12~{end_year:04d}년 02월 4차"

    @staticmethod
    def _site_name_from_biz_no(value: str) -> str:
        digits = re.sub(r"[^\d]", "", str(value or ""))
        if len(digits) != 10:
            return ""
        formatted = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        return FACTORY_MAP.get(formatted, "")

    def dedupe_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        stem, suffix, idx = path.stem, path.suffix, 1
        while True:
            candidate = path.with_name(f"{stem}_{idx}{suffix}")
            if not candidate.exists():
                return candidate
            idx += 1
