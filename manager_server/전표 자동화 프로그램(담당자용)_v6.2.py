import os
import ctypes


def _set_process_dpi_awareness_early():
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


_set_process_dpi_awareness_early()
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import pyperclip
import threading
import urllib.request
import urllib.parse
import json
import subprocess
import sys
import shutil
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import random
import string
import requests
import re
import tempfile
from pathlib import Path
import psutil
import logging
import configparser
import warnings
import pyautogui
import pythoncom
import win32com.client as win32
import win32print
import fitz
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys
from pywinauto.win32structures import RECT as UiaRect


# 🚨 버전 V6.1 고정
CURRENT_VERSION = "6.2"
SERVER_BASE = "http://172.17.39.121:8080"
DEV_SERVER_URL = f"{SERVER_BASE}/api/learn"
LOGIN_URL = f"{SERVER_BASE}/api/login"
UPDATE_PW_URL = f"{SERVER_BASE}/api/update_pw"
CHECK_USER_URL = f"{SERVER_BASE}/api/check_user"
ANALYZE_DB_URL = f"{SERVER_BASE}/api/analyze_db"
ANALYZE_AI_URL = f"{SERVER_BASE}/api/analyze_ai"

DATA_FILE = "app_data.json"
if getattr(sys, 'frozen', False): BASE_EXE_DIR = os.path.dirname(sys.executable)
else: BASE_EXE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_EXE_DIR, "config.ini")

FACTORY_MAP = {"125-81-05619": "D1공장", "403-85-07607": "D2공장", "125-81-32697": "P1공장", "403-85-15640": "P2공장", "403-85-23311": "D3공장", "844-85-00770": "P3공장", "125-81-51622": "일강1공장", "403-85-20895": "일강2공장", "125-81-54876": "제이엠", "118-85-07029": "P4공장", "421-86-02723": "더원"}
CORP_MAP = {"D1공장": "㈜대승", "D2공장": "㈜대승", "D3공장": "㈜대승", "P1공장": "대승정밀㈜", "P2공장": "대승정밀㈜", "P3공장": "대승정밀㈜", "P4공장": "대승정밀㈜", "일강1공장": "㈜일강", "일강2공장": "㈜일강", "더원": "㈜더원", "제이엠": "㈜제이엠"}
EXPENSE_FOOTER_MAP = {
    "DAESEUNG": "DSSP-CO2-09 Rev.4('13. 01. 07)                   ㈜대승                            (200X143)",
    "DSJM": "DSSP-CO2-09 Rev.4('13. 01. 07)               대승정밀㈜                            (200X143)",
    "ILGANG": "DSSP-CO2-09 Rev.4('13. 01. 07)                   ㈜일강                            (200X143)",
}
EXPENSE_XLSX_PATH = r"Y:\관리총괄\경영지원본부\전산팀\2파트\2파트 개인 자료\김기창\현금출금결의서 양식\양식_현금출금정산서.xlsx"
EXPENSE_FORM_SLOTS = [
    {
        "name": "상단",
        "cells": {
            "date": "D5",
            "dept": "D6",
            "author": "G6",
            "title": "D7",
            "basis": "D8",
            "amount": "D9",
            "body": "C11",
            "footer": "B19",
        },
    },
    {
        "name": "하단",
        "cells": {
            "date": "D27",
            "dept": "D28",
            "author": "G28",
            "title": "D29",
            "basis": "D30",
            "amount": "D31",
            "body": "C33",
            "footer": "B41",
        },
    },
]
ERP_BOOT_WAIT = 3.0
ERP_POLL_WAIT = 0.25
ERP_CLICK_WAIT = 0.08
ERP_SETTLE_WAIT = 0.18
ERP_BLOCK_WAIT = 0.30
ERP_FORM_WAIT = 0.12
ERP_PRINT_SAVE_WAIT = 3.0
ERP_PRINT_VIEWER_WAIT = 1.5
ERP_GUI_MUTEX_NAME = os.getenv("ERP_GUI_MUTEX_NAME", r"Global\DSS_ERP_GUI_AUTOMATION_LOCK")
ERP_GUI_LOCK_INFO_PATH = os.getenv("ERP_GUI_LOCK_INFO_PATH", r"C:\ERP_DB\erp_gui_automation.lock.json")
APPROVAL_GW_URL = "https://gw.dae-seung.co.kr"
APPROVAL_DEFAULT_USER = "admpdm"
APPROVAL_DEFAULT_PASSWORD = "eotmd12#$"
PRINT_TARGET_OPTIONS = [
    {"label": "평택 프린터", "match": "172.16.10.172", "kind": "printer"},
    {"label": "김제 프린터", "match": "172.17.30.162", "kind": "printer"},
    {"label": "PDF 저장(병합본)", "match": "Microsoft Print To PDF", "kind": "pdf_merge"},
]


class _ErpGuiAutomationLock:
    WAIT_OBJECT_0 = 0
    WAIT_ABANDONED = 0x80
    WAIT_TIMEOUT = 0x102

    def __init__(self, logger: logging.Logger, owner: str):
        self.logger = logger
        self.owner = owner
        self.handle = None
        self.acquired = False

    def _read_owner(self) -> str:
        try:
            with open(ERP_GUI_LOCK_INFO_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return str(data.get("owner") or data.get("pid") or "").strip()
        except Exception:
            return ""

    def _write_owner(self) -> None:
        try:
            path = Path(ERP_GUI_LOCK_INFO_PATH)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "owner": self.owner,
                "pid": os.getpid(),
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "mutex": ERP_GUI_MUTEX_NAME,
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            self.logger.warning(f"[ERP-LOCK] lock info write failed: {exc}")

    def acquire(self) -> None:
        if os.name != "nt" or str(os.getenv("ERP_GUI_LOCK_DISABLED", "")).lower() in {"1", "true", "yes", "y"}:
            return
        timeout_seconds = max(1.0, float(os.getenv("ERP_GUI_LOCK_TIMEOUT_SECONDS", "7200") or "7200"))
        log_seconds = max(5.0, float(os.getenv("ERP_GUI_LOCK_LOG_SECONDS", "30") or "30"))
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel32.ReleaseMutex.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        self.handle = kernel32.CreateMutexW(None, False, ERP_GUI_MUTEX_NAME)
        if not self.handle:
            self.logger.warning("[ERP-LOCK] CreateMutex failed; continuing without lock")
            return
        started = time.time()
        self.logger.info(f"[ERP-LOCK] waiting for shared ERP GUI lock: owner={self.owner}")
        while True:
            elapsed = time.time() - started
            remaining = timeout_seconds - elapsed
            if remaining <= 0:
                waiting_owner = self._read_owner() or "unknown"
                raise RuntimeError(
                    f"ERP GUI automation lock timeout after {timeout_seconds:.0f}s. "
                    f"current owner={waiting_owner}"
                )
            wait_ms = int(min(log_seconds, remaining) * 1000)
            result = kernel32.WaitForSingleObject(self.handle, wait_ms)
            if result in (self.WAIT_OBJECT_0, self.WAIT_ABANDONED):
                self.acquired = True
                self._write_owner()
                self.logger.info(
                    f"[ERP-LOCK] acquired shared ERP GUI lock after {elapsed:.1f}s: owner={self.owner}"
                )
                return
            if result == self.WAIT_TIMEOUT:
                waiting_owner = self._read_owner() or "unknown"
                self.logger.warning(
                    f"[ERP-LOCK] waiting {elapsed:.1f}s/{timeout_seconds:.0f}s; current owner={waiting_owner}"
                )
                continue
            raise RuntimeError(f"ERP GUI automation lock wait failed: result={result}")

    def release(self) -> None:
        if os.name != "nt" or not self.handle:
            return
        kernel32 = ctypes.windll.kernel32
        try:
            if self.acquired:
                try:
                    Path(ERP_GUI_LOCK_INFO_PATH).unlink(missing_ok=True)
                except Exception:
                    pass
                kernel32.ReleaseMutex(self.handle)
                self.logger.info(f"[ERP-LOCK] released shared ERP GUI lock: owner={self.owner}")
        finally:
            kernel32.CloseHandle(self.handle)
            self.handle = None
            self.acquired = False


APPROVAL_HELPER_SOURCE = r'''
import asyncio
import json
import logging
import re
import sys
import traceback
import warnings
from pathlib import Path
import pdfplumber
from playwright.async_api import async_playwright

WAIT = "domcontentloaded"
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def log(msg):
    print(f"LOG:{msg}", flush=True)

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '_', str(name or '').strip()) or "approval_document"

def wrap_order_number(raw):
    num = str(raw or "").strip().strip("()")
    return f"({num})" if num else ""

def extract_doc_id_text(*values):
    blob = "\n".join(str(v or "") for v in values if v)
    patterns = [
        r"^\s*(\d{4,})\s*$",
        r"/approval/document/(\d+)",
        r"\bdocId['\"]?\s*[:=]\s*['\"]?(\d+)",
        r"\bdocumentId['\"]?\s*[:=]\s*['\"]?(\d+)",
        r"\bdata-id['\"]?\s*[:=]\s*['\"]?(\d+)",
        r"\bdata-doc-id['\"]?\s*[:=]\s*['\"]?(\d+)",
        r"\bapproval/document/(\d+)/popup/print",
        r"\bopen\w*\((\d+)\)",
        r"\bview\w*\((\d+)\)",
    ]
    for pattern in patterns:
        m = re.search(pattern, blob, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""

def extract_order_number(quote_path):
    text = ""
    with pdfplumber.open(quote_path) as pdf:
        for page in pdf.pages[:2]:
            text += (page.extract_text() or "") + "\n"
    filename_text = Path(quote_path).stem
    patterns = [
        r'견\s*적\s*번\s*호\s*[:：#\-]?\s*([0-9]{8})',
        r'견적번호\s*[:：#\-]?\s*([0-9]{8})',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1)

    nums = re.findall(r'\(([0-9]{8})\)', filename_text)
    if nums:
        return nums[0]
    return ""

async def run(config):
    quote_path = config["quote_path"]
    output_dir = config["output_dir"]
    username = config["username"]
    password = config["password"]
    headless = bool(config.get("headless", True))
    result_path = config.get("result_path", "")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    order_number = extract_order_number(quote_path)
    if not order_number:
        raise RuntimeError("견적서에서 주문번호를 찾지 못했습니다.")
    wrapped_order = wrap_order_number(order_number)
    print(f"ORDER:{order_number}", flush=True)
    log(f"주문번호 추출 완료: {wrapped_order}")

    saved = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--start-maximized"])
        context = await browser.new_context(viewport={"width": 1920, "height": 1080}, accept_downloads=True)
        page = await context.new_page()
        try:
            log("그룹웨어 로그인 시작")
            await page.goto("https://gw.dae-seung.co.kr/login", wait_until=WAIT)
            await page.wait_for_selector("input#username", timeout=15000)
            await page.fill("input#username", username)
            await page.fill("input#password", password)
            await page.click("a#login_submit")
            await page.wait_for_selector("nav#menu-container, li[data-menu='approval']", timeout=20000)
            log("그룹웨어 로그인 완료")

            log("전자결재 상세검색 진입")
            await page.goto("https://gw.dae-seung.co.kr/app/approval", wait_until=WAIT)
            await page.wait_for_selector("a#btn_DetailSearch", timeout=20000)
            await page.wait_for_timeout(500)
            await page.click("a#btn_DetailSearch")
            await page.wait_for_timeout(800)

            found_cb = False
            cbs = page.locator("input[type='checkbox']")
            cb_count = await cbs.count()
            for i in range(cb_count):
                cb = cbs.nth(i)
                handle = await cb.element_handle()
                label_text = await page.evaluate("""(el) => {
                    let n = el.nextSibling;
                    if (n && n.nodeType === 3) return n.textContent.trim();
                    if (el.id) {
                        const lbl = document.querySelector('label[for="' + el.id + '"]');
                        if (lbl) return lbl.textContent.trim();
                    }
                    const parent = el.closest('label');
                    if (parent) return parent.textContent.trim();
                    return '';
                }""", handle)
                if "첨부파일명" in (label_text or ""):
                    if not await cb.is_checked():
                        await cb.check()
                    for j in range(cb_count):
                        if j != i:
                            try:
                                other = cbs.nth(j)
                                if await other.is_checked():
                                    await other.uncheck()
                            except Exception:
                                pass
                    found_cb = True
                    break
            if not found_cb:
                cb_direct = page.locator("input[name='attachFileNames']")
                if await cb_direct.count() > 0 and not await cb_direct.is_checked():
                    await cb_direct.check()

            search_input = page.locator(
                "input[name='keyword'], .layer_normal input[type='text']:last-of-type"
            ).last
            await search_input.fill(wrapped_order)
            await page.wait_for_timeout(300)
            search_btn = page.locator(
                "div.layer_normal a:has-text('검색'), "
                "div.layer_normal button:has-text('검색'), "
                "div.layer_normal input[value='검색']"
            ).first
            await search_btn.click()
            await page.wait_for_selector("table.type_normal tbody tr, p.data_null", timeout=15000)
            await page.wait_for_timeout(600)
            log(f"상세검색 완료: {wrapped_order}")

            rows = page.locator("table.type_normal tbody tr")
            count = await rows.count()
            completed = []
            for i in range(count):
                row = rows.nth(i)
                finish = row.locator("span.state.finish, span.finish, td:last-child span:has-text('완료')")
                if await finish.count() == 0:
                    continue
                title_el = row.locator("td.subject a span.txt, td.subject a").first
                title = (await title_el.inner_text()).strip() if await title_el.count() > 0 else f"문서_{i+1}"
                cb_el = row.locator("input.doclist_item_checkbox")
                raw_doc_id = await cb_el.get_attribute("data-id") if await cb_el.count() > 0 else ""
                doc_id = (str(raw_doc_id or "").strip() if str(raw_doc_id or "").strip().isdigit() else "")
                completed.append({"title": title, "doc_id": doc_id})

            if not completed:
                raise RuntimeError(f"{wrapped_order} 로 검색된 결재완료 품의 문서가 없습니다.")

            log(f"결재완료 문서 {len(completed)}건 발견")
            search_result_url = page.url
            for idx, doc in enumerate(completed, start=1):
                title = doc["title"]
                doc_id = doc["doc_id"]
                if not doc_id:
                    log("doc_id 없음 감지")
                    await page.goto(search_result_url, wait_until=WAIT)
                    await page.wait_for_timeout(500)
                    log("검색결과 페이지로 복귀")
                    rows_now = page.locator("table.type_normal tbody tr")
                    target_link = None
                    for ri in range(await rows_now.count()):
                        row_now = rows_now.nth(ri)
                        title_now = row_now.locator("td.subject a span.txt, td.subject a").first
                        link_now = row_now.locator("td.subject a").first
                        if await title_now.count() > 0:
                            t = (await title_now.inner_text()).strip()
                            if t == title:
                                target_link = link_now if await link_now.count() > 0 else title_now
                                break
                    if target_link is None:
                        log(f"검색 결과에서 제목 링크를 다시 찾지 못했습니다: {title}")
                        continue
                    log(f"해당 제목 클릭: {title}")
                    await target_link.click()
                    await page.wait_for_url(r"**/approval/document/**", timeout=10000)
                    m = re.search(r"/approval/document/(\d+)", page.url)
                    if m:
                        doc_id = m.group(1)
                        log(f"이동 URL에서 doc_id 추출 완료: {title} -> {doc_id}")

                    if not doc_id:
                        log(f"doc_id 추출 실패: {title}")
                        continue

                print_url = f"https://gw.dae-seung.co.kr/app/approval/document/{doc_id}/popup/print"
                await page.goto(print_url, wait_until=WAIT)
                await page.wait_for_selector("body, form#document_content, div.approval_import", timeout=15000)
                await page.wait_for_timeout(2000)
                filename = f"{order_number}_{idx:02d}_{sanitize_filename(title)}.pdf"
                out_path = str(Path(output_dir) / filename)
                await page.pdf(
                    path=out_path,
                    format="A4",
                    page_ranges="1",
                    print_background=True,
                    margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"},
                )
                saved.append(out_path)
                print(f"FILE:{out_path}", flush=True)
                log(f"품의 PDF 저장 완료: {filename}")
        finally:
            await browser.close()

    payload = {"order_number": order_number, "saved": saved}
    if result_path:
        Path(result_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print("RESULT_JSON:" + json.dumps(payload, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    try:
        config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        asyncio.run(run(config))
    except Exception as exc:
        print(f"ERROR:{type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
        sys.exit(1)
'''

class ERPConfig:
    def __init__(self, ini_path: str = CONFIG_FILE):
        self.ini_path = Path(ini_path); self.config = configparser.ConfigParser(); self.config.optionxform = str
        if self.ini_path.exists(): self.config.read(self.ini_path, encoding="utf-8")
    def get_install_info(self, install_key: str):
        section = f"INSTALL_{install_key.upper()}"
        return {
            "exe_path": self.config.get(section, "exe_path", fallback="").strip(), 
            "process_name": self.config.get(section, "process_name", fallback="Angkor.Ylw.Main.MainWin45.exe").strip(), 
            "startup_wait_sec": self.config.get(section, "startup_wait_sec", fallback="3").strip(), 
            "login_window_title": self.config.get(section, "login_window_title", fallback="FrmMainSplash").strip(),
            "splash_name": self.config.get(section, "splash_name", fallback="FrmMainSplash").strip(),
            "main_window_title": self.config.get(section, "main_window_title", fallback="").strip(),
        }
    def get_corp_info(self, corp_code: str):
        section = f"CORP_{corp_code.upper()}"
        return {"user_id": self.config.get(section, "user_id", fallback="").strip(), "password": self.config.get(section, "password", fallback="").strip()}
    def set_common_value(self, key: str, value: str):
        if not self.config.has_section("COMMON"):
            self.config.add_section("COMMON")
        self.config.set("COMMON", key, str(value))
        with open(self.ini_path, "w", encoding="utf-8") as f:
            self.config.write(f)

def setup_logger():
    logger = logging.getLogger("ERP_V6"); logger.setLevel(logging.INFO)
    if not logger.handlers:
        fmt = logging.Formatter("[%(asctime)s] %(message)s", "%H:%M:%S")
        h = logging.StreamHandler()
        h.setFormatter(fmt)
        logger.addHandler(h)
        try:
            fh = logging.FileHandler(os.path.join(BASE_EXE_DIR, "erp_debug.log"), mode="a", encoding="utf-8")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        except Exception:
            pass
    return logger


_ERP_TARGET_MONITOR_CACHE = None


def _set_process_dpi_aware_for_erp_windowing():
    _set_process_dpi_awareness_early()


def _monitor_summary(monitors):
    if not monitors:
        return "none"
    parts = []
    for item in monitors:
        parts.append(
            f"{item.get('device','?')} {item.get('width')}x{item.get('height')} "
            f"scale={item.get('scale')} rect=({item.get('left')},{item.get('top')})-({item.get('right')},{item.get('bottom')})"
        )
    return "; ".join(parts)


def _detect_erp_target_monitor(logger=None):
    global _ERP_TARGET_MONITOR_CACHE
    if _ERP_TARGET_MONITOR_CACHE:
        return _ERP_TARGET_MONITOR_CACHE
    if os.name != "nt":
        return None

    import ctypes
    from ctypes import wintypes

    _set_process_dpi_aware_for_erp_windowing()
    user32 = ctypes.windll.user32
    shcore = getattr(ctypes.windll, "shcore", None)

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    class MONITORINFOEX(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", ctypes.c_ulong),
            ("szDevice", ctypes.c_wchar * 32),
        ]

    monitors = []
    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)

    def callback(hmonitor, hdc, lprc, lparam):
        info = MONITORINFOEX()
        info.cbSize = ctypes.sizeof(MONITORINFOEX)
        if not user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            return 1
        width = int(info.rcMonitor.right - info.rcMonitor.left)
        height = int(info.rcMonitor.bottom - info.rcMonitor.top)
        dpi_x = dpi_y = 96
        if shcore:
            try:
                x = ctypes.c_uint()
                y = ctypes.c_uint()
                if shcore.GetDpiForMonitor(hmonitor, 0, ctypes.byref(x), ctypes.byref(y)) == 0:
                    dpi_x, dpi_y = int(x.value), int(y.value)
            except Exception:
                pass
        scale = round(dpi_x / 96 * 100)
        monitors.append({
            "device": info.szDevice,
            "left": int(info.rcMonitor.left),
            "top": int(info.rcMonitor.top),
            "right": int(info.rcMonitor.right),
            "bottom": int(info.rcMonitor.bottom),
            "work_left": int(info.rcWork.left),
            "work_top": int(info.rcWork.top),
            "work_right": int(info.rcWork.right),
            "work_bottom": int(info.rcWork.bottom),
            "width": width,
            "height": height,
            "scale": scale,
            "primary": bool(info.dwFlags & 1),
        })
        return 1

    user32.EnumDisplayMonitors(0, 0, MONITORENUMPROC(callback), 0)
    recommended = [m for m in monitors if m["width"] >= 1920 and m["height"] >= 1080 and 95 <= m["scale"] <= 105]
    if not recommended:
        message = "ERP automation requires a 1920x1080 display at 100% scale. detected=" + _monitor_summary(monitors)
        if logger:
            logger.error(message)
        raise RuntimeError(message)
    recommended.sort(key=lambda m: (not m["primary"], m["left"], m["top"]))
    _ERP_TARGET_MONITOR_CACHE = recommended[0]
    if logger:
        logger.info("ERP target display selected: " + _monitor_summary([_ERP_TARGET_MONITOR_CACHE]))
    return _ERP_TARGET_MONITOR_CACHE


def _move_window_to_erp_monitor(win, logger=None, label="ERP window"):
    if not win or os.name != "nt":
        return None
    target = _detect_erp_target_monitor(logger)
    left = int(target.get("work_left", target["left"]))
    top = int(target.get("work_top", target["top"]))
    right = int(target.get("work_right", target["right"]))
    bottom = int(target.get("work_bottom", target["bottom"]))
    width = max(800, right - left)
    height = max(600, bottom - top)
    try:
        if hasattr(win, "is_minimized") and win.is_minimized():
            win.restore()
            time.sleep(0.15)
    except Exception:
        pass
    try:
        win.move_window(left, top, width, height, True)
    except Exception:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.MoveWindow.argtypes = [
                ctypes.wintypes.HWND,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.wintypes.BOOL,
            ]
            user32.MoveWindow.restype = ctypes.wintypes.BOOL
            user32.MoveWindow(ctypes.wintypes.HWND(int(win.handle)), left, top, width, height, True)
        except Exception as exc:
            if logger:
                logger.warning(f"{label} move to ERP target display failed: {exc}")
            raise
    try:
        win.set_focus()
    except Exception:
        pass
    time.sleep(0.20)
    if logger:
        logger.info(f"{label} moved to ERP target display: {target.get('device')} rect=({left},{top}) size={width}x{height} scale={target.get('scale')}")
    return target


def _window_center_in_monitor(win, monitor):
    try:
        rect = win.rectangle()
        cx = (rect.left + rect.right) // 2
        cy = (rect.top + rect.bottom) // 2
        return monitor["left"] <= cx < monitor["right"] and monitor["top"] <= cy < monitor["bottom"]
    except Exception:
        return False


def _find_existing_erp_top_level_window(
    main_keywords,
    excluded_keywords=(),
    logger=None,
):
    """Find an already-open ERP frame without walking its GDI/UIA descendants.

    Recovery can run after the Agent has restarted and lost its in-memory PID.  The
    configured executable name is not a reliable identity on every ERP install, so
    inspect current-desktop *top-level* windows and return only a large, visible
    frame whose own MainWindow id and current-corporation title identify ERP.
    """
    keywords = [str(value or "").strip() for value in main_keywords]
    keywords = [value for value in keywords if value]
    exclusions = [str(value or "").strip() for value in excluded_keywords]
    exclusions = [value for value in exclusions if value]
    matches = []
    try:
        windows = Desktop(backend="uia").windows()
    except Exception as exc:
        if logger:
            logger.warning(
                f"  [RECOVERY-PREFLIGHT] 전체 데스크톱 최상위 창 열거 실패: {exc}"
            )
        return None

    for win in windows:
        try:
            if not win.is_visible():
                continue
            title = str(win.window_text() or "").strip()
            auto_id = str(win.element_info.automation_id or "").strip()
            # Global Desktop enumeration is broader than ``self.app.windows``.
            # Require both ERP's own MainWindow id and the *current corporation*
            # title.  A generic MainWindow (browser/mail) or another corporation's
            # ERP must never be selected for save/print recovery.
            if auto_id.lower() != "mainwindow":
                continue
            if not keywords or not any(keyword in title for keyword in keywords):
                continue
            if any(keyword in title for keyword in exclusions):
                continue
            rect = win.rectangle()
            width = max(0, int(rect.right) - int(rect.left))
            height = max(0, int(rect.bottom) - int(rect.top))
            if width < 640 or height < 400:
                continue
            try:
                process_id = int(win.process_id() or 0)
            except Exception:
                process_id = int(getattr(win.element_info, "process_id", 0) or 0)
            if process_id <= 0:
                continue
            matches.append(
                (width * height, width, height, process_id, win, title, auto_id)
            )
        except Exception:
            continue

    if not matches:
        return None
    _, width, height, process_id, win, title, auto_id = max(
        matches,
        key=lambda item: (item[0], item[1], item[2]),
    )
    if logger:
        logger.info(
            "  [RECOVERY-PREFLIGHT] 설정 프로세스명 대신 ERP 최상위 창 발견: "
            f"pid={process_id}, title={title!r}, auto_id={auto_id!r}, "
            f"size={width}x{height}, candidates={len(matches)}"
        )
    return {
        "pid": process_id,
        "window": win,
        "title": title,
        "automation_id": auto_id,
        "width": width,
        "height": height,
    }


class ERPLoginBot:
    def __init__(self, install_info: dict, corp_info: dict, corp_code: str, manager, logger: logging.Logger):
        self.install_info = install_info
        self.corp_info = corp_info
        self.corp_code = corp_code
        self.manager = manager
        self.logger = logger
        self.app = None
        self.login_win = None
        self.erp_process_pid = 0
        
    def _force_erp_window_maximized(self, win, label="ERP 메인 창"):
        if not win:
            return False
        try:
            win.set_focus()
            time.sleep(0.15)
        except Exception as e:
            self.logger.warning(f"[{self.corp_code}] {label} 포커스 실패: {e}")
        target_monitor = _detect_erp_target_monitor(self.logger)
        ok = False
        try:
            try:
                if hasattr(win, "is_minimized") and win.is_minimized():
                    win.restore()
                    time.sleep(0.15)
            except Exception:
                pass
            _move_window_to_erp_monitor(win, self.logger, f"[{self.corp_code}] {label}")
        except Exception:
            raise
        try:
            win.maximize()
            time.sleep(max(ERP_BLOCK_WAIT, 0.35))
            ok = True
        except Exception as e:
            self.logger.warning(f"[{self.corp_code}] {label} maximize ??, Win+Up fallback ??: {e}")
            try:
                pyautogui.hotkey("win", "up")
                time.sleep(0.18)
                pyautogui.hotkey("win", "up")
                time.sleep(max(ERP_BLOCK_WAIT, 0.35))
                ok = True
            except Exception as hotkey_exc:
                self.logger.warning(f"[{self.corp_code}] {label} Win+Up fallback ??: {hotkey_exc}")
        try:
            rect = win.rectangle()
            screen_w, screen_h = pyautogui.size()
            width = rect.width()
            height = rect.height()
            self.logger.info(
                f"[{self.corp_code}] {label} 최대화 확인: rect=({rect.left},{rect.top})-({rect.right},{rect.bottom}) "
                f"size={width}x{height}, screen={screen_w}x{screen_h}"
            )
            if target_monitor and not _window_center_in_monitor(win, target_monitor):
                self.logger.warning(f"[{self.corp_code}] {label} is not on ERP target display after maximize; retry move/maximize")
                _move_window_to_erp_monitor(win, self.logger, f"[{self.corp_code}] {label} retry")
                win.maximize()
                time.sleep(max(ERP_BLOCK_WAIT, 0.35))
                if not _window_center_in_monitor(win, target_monitor):
                    raise RuntimeError(f"{label} failed to stay on the 1920x1080 100% ERP display")
            if width < min(1600, screen_w - 80) or height < min(850, screen_h - 120):
                self.logger.warning(f"[{self.corp_code}] {label} 창 크기가 좌표 자동입력 기준보다 작습니다. 좌표 오입력 위험이 있습니다.")
        except Exception as e:
            self.logger.warning(f"[{self.corp_code}] {label} 크기 확인 실패: {e}")
        return ok

    def _close_erp_after_success(self, main_win=None):
        enabled = str(os.getenv("ERP_CLOSE_AFTER_SUCCESS", "1")).strip().lower()
        if enabled in ("0", "false", "no", "off", ""):
            self.logger.info("[CLEANUP] ERP close after success disabled")
            return

        def _terminate_pid(pid, label, timeout=5):
            if not pid:
                return False
            try:
                pid = int(pid)
            except Exception:
                return False
            try:
                if not psutil.pid_exists(pid):
                    return False
                proc = psutil.Process(pid)
                name = proc.name()
                self.logger.info(f"[CLEANUP] closing {label}: pid={pid} name={name}")
                proc.terminate()
                try:
                    proc.wait(timeout=timeout)
                except psutil.TimeoutExpired:
                    self.logger.warning(f"[CLEANUP] {label} did not exit; killing pid={pid}")
                    proc.kill()
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        pass
                return True
            except Exception as exc:
                self.logger.warning(f"[CLEANUP] failed to close {label} pid={pid}: {exc}")
                return False

        try:
            rd_procs = []
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if "rdviewer" in name:
                        proc.terminate()
                        rd_procs.append(proc)
                except Exception:
                    pass
            if rd_procs:
                try:
                    gone, alive = psutil.wait_procs(rd_procs, timeout=3)
                except Exception:
                    alive = []
                for proc in alive:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                self.logger.info(f"[CLEANUP] RD Viewer closed after successful automation: count={len(rd_procs)}")
        except Exception as exc:
            self.logger.warning(f"[CLEANUP] RD Viewer cleanup failed: {exc}")

        try:
            if main_win:
                main_win.close()
                time.sleep(0.7)
                self.logger.info("[CLEANUP] ERP main window close requested after successful automation")
        except Exception as exc:
            self.logger.warning(f"[CLEANUP] ERP window close request failed: {exc}")

        try:
            if self.app:
                for win in self.app.windows():
                    try:
                        if main_win and getattr(win, "handle", None) == getattr(main_win, "handle", None):
                            continue
                        win.close()
                    except Exception:
                        pass
                time.sleep(0.5)
        except Exception as exc:
            self.logger.warning(f"[CLEANUP] ERP app window cleanup failed: {exc}")

        pid = self.erp_process_pid
        if not pid and main_win:
            try:
                pid = int(getattr(main_win.element_info, "process_id", 0) or 0)
            except Exception:
                pid = 0
        if not pid:
            try:
                pid = int(self.manager.erp_pids.get(self.corp_code, 0) or 0)
            except Exception:
                pid = 0
        closed = _terminate_pid(pid, "ERP")

        if not closed:
            process_name = str(self.install_info.get("process_name") or "").lower()
            if process_name:
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        if (proc.info.get("name") or "").lower() == process_name:
                            _terminate_pid(proc.info.get("pid"), "ERP fallback")
                    except Exception:
                        pass

        try:
            self.manager.erp_pids[self.corp_code] = 0
        except Exception:
            pass
        self.app = None
        self.login_win = None
        self.erp_process_pid = 0
        self.logger.info("[CLEANUP] ERP closed after successful automation")

    def run(self):
        owner = f"corp={self.corp_code} pid={os.getpid()}"
        lock = _ErpGuiAutomationLock(self.logger, owner)
        lock.acquire()
        try:
            return self._run_unlocked()
        finally:
            lock.release()

    def _run_unlocked(self):
        try:
            process_exe = self.install_info["process_name"].lower().replace('.exe', '')
            confirmed_pid = 0
            resume_print_only_requested = (
                str(os.getenv("ERP_RESUME_PRINT_ONLY", "0"))
                .strip()
                .lower()
                in {"1", "true", "yes", "y", "on"}
            )
            resume_management_save_print = (
                str(os.getenv("ERP_RESUME_MANAGEMENT_SAVE_PRINT", "0"))
                .strip()
                .lower()
                in {"1", "true", "yes", "y", "on"}
            )
            if resume_print_only_requested and resume_management_save_print:
                return "출력 전용 복구와 관리항목·저장·출력 복구를 동시에 실행할 수 없습니다."
            # Both recovery modes must attach to the voucher that is already open.
            # The management recovery is distinguished later inside the form so it can
            # rerun only management-item input before saving and printing.
            resume_existing_voucher = resume_print_only_requested or resume_management_save_print

            fresh_start = os.getenv("ERP_AGENT_FRESH_START", "0").strip().lower() in {"1", "true", "yes", "y"}
            if resume_existing_voucher:
                # A recovery run must attach to the voucher that is already open.
                # Starting a fresh ERP process could print or save the wrong form.
                fresh_start = False
            if fresh_start:
                closed_pids = []
                alive = []
                for proc in psutil.process_iter(["name", "pid"]):
                    try:
                        name = (proc.info.get("name") or "").lower()
                        if process_exe and process_exe in name:
                            proc.terminate()
                            closed_pids.append(proc.info.get("pid"))
                            alive.append(proc)
                    except Exception:
                        pass
                if alive:
                    try:
                        gone, alive = psutil.wait_procs(alive, timeout=5)
                    except Exception:
                        pass
                    for proc in alive:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                if closed_pids:
                    self.logger.info(f"[{self.corp_code}] Agent fresh start: 기존 ERP 프로세스 종료 요청 pids={closed_pids}")
                self.manager.erp_pids[self.corp_code] = 0
             
            # 1. 메모리에 매핑된 PID 검사 및 활성화
            target_pid = self.manager.erp_pids.get(self.corp_code, 0)
            if target_pid > 0 and psutil.pid_exists(target_pid):
                try:
                    proc = psutil.Process(target_pid)
                    if process_exe in proc.name().lower():
                        self.logger.info(f"[{self.corp_code}] 메모리에 매핑된 ERP(PID:{target_pid})가 실행 중입니다. 최상단 창을 활성화합니다.")
                        self.app = Application(backend="uia").connect(process=target_pid)
                        self.app.top_window().set_focus()
                        confirmed_pid = target_pid
                except Exception as e:
                    self.logger.warning(f"PID 활성화 중 오류 발생, 재탐색을 시도합니다: {e}")

            if confirmed_pid == 0:
                # 2. 현재 실행 중인 프로세스 목록 저장 (실행 전 상태)
                existing_pids = set()
                for proc in psutil.process_iter(["name", "pid"]):
                    if proc.info.get("name") and process_exe in proc.info.get("name").lower():
                        existing_pids.add(proc.info.get("pid"))

                candidates = [
                    self.install_info.get("splash_name", "FrmMainSplash"),
                    self.install_info.get("login_window_title", ""),
                    self.install_info.get("main_window_title", ""),
                    "FrmMainSplash", "K-System", "대승", "일강", "제이엠", "더원"
                ]
                if resume_existing_voucher:
                    self.logger.info(
                        "  [PRINT-RESUME] 기존 ERP 재연결 탐색: "
                        f"pids={sorted(existing_pids)}, titles={[title for title in candidates if title]}"
                    )

                # 메모리가 날아갔으나 이미 프로세스가 켜져있는 경우 (재시작 복구 방어막)
                if existing_pids and not confirmed_pid and not resume_existing_voucher:
                    recovered = False
                    for pid in existing_pids:
                        try:
                            temp_app = Application(backend="uia").connect(process=pid)
                            for keyword in candidates:
                                if not keyword: continue
                                try:
                                    for win in temp_app.windows(title_re=f".*{keyword}.*"):
                                        if win.is_visible():
                                            self.manager.erp_pids[self.corp_code] = pid
                                            self.logger.info(f"[{self.corp_code}] 실행 중인 ERP(PID:{pid}) 발견. 메모리 복구 및 활성화.")
                                            win.set_focus()
                                            recovered = True
                                            confirmed_pid = pid
                                            self.app = temp_app
                                            break
                                except: pass
                                if recovered: break
                        except: pass
                        if recovered: break

                if resume_existing_voucher and not confirmed_pid:
                    recovery_company_titles = {
                        "DS": ("대승",),
                        "DSJM": ("대승정밀",),
                        "ILGANG": ("일강",),
                        "JM": ("제이엠",),
                        "TO": ("더원",),
                    }.get(str(self.corp_code or "").upper(), ())
                    recovery_title_exclusions = {
                        # "대승" is a substring of "대승정밀"; never attach the
                        # DAESEUNG recovery job to the DSJM ERP frame.
                        "DS": ("대승정밀",),
                    }.get(str(self.corp_code or "").upper(), ())
                    top_level_match = _find_existing_erp_top_level_window(
                        recovery_company_titles,
                        excluded_keywords=recovery_title_exclusions,
                        logger=self.logger,
                    )
                    if top_level_match:
                        fallback_pid = int(top_level_match["pid"])
                        try:
                            fallback_app = Application(backend="uia").connect(
                                process=fallback_pid
                            )
                        except Exception as exc:
                            self.logger.warning(
                                "  [RECOVERY-PREFLIGHT] 발견한 ERP 최상위 창 PID 연결 실패: "
                                f"pid={fallback_pid}, error={exc}"
                            )
                        else:
                            confirmed_pid = fallback_pid
                            existing_pids.add(fallback_pid)
                            self.app = fallback_app
                            self.manager.erp_pids[self.corp_code] = fallback_pid
                            self.logger.info(
                                f"[{self.corp_code}] ERP 최상위 창 PID:{fallback_pid}로 "
                                "메모리 매핑을 복구했습니다."
                            )

                if resume_existing_voucher and not confirmed_pid:
                    return "ERP 전표 복구 실패: 현재 열린 ERP 전표 화면에 연결하지 못했습니다."

                if not confirmed_pid:
                    # 3. 켜져있는 프로세스가 아예 없다면 새로 실행
                    exe_path = self.install_info["exe_path"]
                    if not exe_path or not os.path.exists(exe_path): 
                        return f"실행 파일이 없습니다:\n{exe_path}"
                    
                    work_dir = os.path.dirname(exe_path)
                    try: 
                        os.chdir(work_dir)
                        os.startfile(exe_path)
                    except Exception as e: 
                        return f"ERP 실행 불가:\n{e}"
                    
                    self.logger.info("ERP 실행 중... 런처 종료 및 메인 프로세스 안착 대기 (3초)")
                    time.sleep(ERP_BOOT_WAIT)
                    
                    new_pids = []
                    end_time = time.time() + 30
                    while time.time() < end_time:
                        for proc in psutil.process_iter(["name", "pid"]):
                            if proc.info.get("name") and process_exe in proc.info.get("name").lower():
                                pid = proc.info.get("pid")
                                if pid not in existing_pids and pid not in new_pids:
                                    new_pids.append(pid)
                        if new_pids:
                            break
                        time.sleep(ERP_POLL_WAIT)
                        
                    if not new_pids: 
                        return "새로운 프로세스가 생성되지 않았습니다."
                    
                    self.logger.info(f"발견된 새 PID 목록: {new_pids}. 진짜 창 탐색 시작...")
                    verify_end_time = time.time() + 30
                    while time.time() < verify_end_time:
                        current_pids = [p.info.get("pid") for p in psutil.process_iter(["name", "pid"]) if p.info.get("name") and process_exe in p.info.get("name").lower()]
                        for pid in current_pids:
                            if pid in existing_pids: continue
                            try:
                                temp_app = Application(backend="uia").connect(process=pid)
                                for keyword in candidates:
                                    if not keyword: continue
                                    try:
                                        for win in temp_app.windows(title_re=f".*{keyword}.*"):
                                            if win.is_visible():
                                                confirmed_pid = pid
                                                self.login_win = win
                                                break
                                    except: pass
                                    if confirmed_pid > 0: break
                            except: pass
                            if confirmed_pid > 0: break
                        if confirmed_pid > 0: break
                        time.sleep(ERP_POLL_WAIT)

                    if confirmed_pid == 0:
                        return f"로그인 창을 가진 진짜 프로세스를 찾지 못했습니다.\n(탐색 키워드: {candidates[0]})"

                    # 진짜 PID 메모리에 확정 매핑
                    self.manager.erp_pids[self.corp_code] = confirmed_pid
                    self.app = Application(backend="uia").connect(process=confirmed_pid)
                    self.logger.info(f"[{self.corp_code}] 메인 ERP(PID:{confirmed_pid}) 확정 및 메모리 매핑 완료.")
                    
                    _move_window_to_erp_monitor(self.login_win, self.logger, f"[{self.corp_code}] login window")
                    self.login_win.set_focus()
                    time.sleep(ERP_BLOCK_WAIT)

                    # 4. 아이디 및 패스워드 타이핑
                    try:
                        edits = [c for c in self.login_win.descendants(control_type="Edit") if c.is_visible() and c.is_enabled()]
                        try:
                            edits.sort(key=lambda c: (c.rectangle().top, c.rectangle().left))
                        except Exception:
                            pass
                        self.logger.info(f"[{self.corp_code}] 로그인 Edit 컨트롤 감지 수: {len(edits)}")

                        if len(edits) >= 2:
                            current_id = ""
                            try:
                                current_id = (edits[0].window_text() or "").strip()
                            except Exception:
                                pass

                            edits[0].click_input()
                            if not (self.corp_code == "ILGANG" and current_id):
                                edits[0].type_keys("^a{BACKSPACE}")
                                edits[0].type_keys(self.corp_info["user_id"], with_spaces=True)
                            else:
                                self.logger.info(f"[{self.corp_code}] 로그인창에 기존 아이디가 있어 유지합니다: {current_id}")
                            
                            edits[1].click_input()
                            edits[1].type_keys("^a{BACKSPACE}")
                            edits[1].type_keys(self.corp_info["password"], with_spaces=True)
                            
                            self.login_win.type_keys("{ENTER}")
                            time.sleep(1.5)  # 로그인 후 로딩 대기
                        elif self.corp_code == "ILGANG" and len(edits) == 1:
                            self.logger.warning("[ILGANG] Edit 1개만 감지되어 탭 이동 fallback으로 비밀번호 입력을 시도합니다.")
                            current_id = ""
                            try:
                                current_id = (edits[0].window_text() or "").strip()
                            except Exception:
                                pass
                            edits[0].click_input()
                            time.sleep(0.15)
                            if not current_id:
                                pyautogui.hotkey("ctrl", "a")
                                time.sleep(0.05)
                                pyautogui.write(self.corp_info["user_id"], interval=0.02)
                            pyautogui.press("tab")
                            time.sleep(0.1)
                            pyautogui.write(self.corp_info["password"], interval=0.02)
                            pyautogui.press("enter")
                            time.sleep(1.5)
                        elif self.corp_code == "ILGANG" and len(edits) == 0:
                            self.logger.warning("[ILGANG] Edit를 못 찾아 좌표 fallback으로 비밀번호 입력을 시도합니다.")
                            r = self.login_win.rectangle()
                            pwd_x = r.left + int((r.right - r.left) * 0.72)
                            pwd_y = r.top + int((r.bottom - r.top) * 0.63)
                            pyautogui.click(pwd_x, pwd_y)
                            time.sleep(0.1)
                            pyautogui.write(self.corp_info["password"], interval=0.02)
                            pyautogui.press("enter")
                            time.sleep(1.5)
                        else:
                            self.logger.warning("입력칸을 인식하지 못하여 로그인을 스킵합니다.")
                    except Exception as e: 
                        self.logger.warning(f"자동 입력 중 에러 발생 (스킵): {e}")

            # ── [중요] 기존 v6.0에서는 여기서 return True를 해서 내비게이션을 안했음 ──
            # 로그인 창이 닫히고 메인 화면이 뜰 때까지 대기 및 강력한 팝업 블라인드 킬러
            def _window_text_blob(win):
                parts = []
                try:
                    parts.append(win.window_text() or "")
                except:
                    pass
                try:
                    for ctrl in win.descendants():
                        try:
                            text = ctrl.window_text() or ""
                            if text:
                                parts.append(text)
                        except:
                            pass
                except:
                    pass
                return " ".join(parts)

            def _is_password_change_blocker(win):
                blob = _window_text_blob(win)
                compact = re.sub(r"\s+", "", blob).lower()
                if not compact:
                    return False
                password_words = ("비밀번호", "암호", "password", "패스워드")
                change_words = ("변경", "만료", "기간", "90", "초기화", "재설정", "change", "expired", "expire")
                return any(word.lower() in compact for word in password_words) and any(
                    word.lower() in compact for word in change_words
                )

            def _is_login_failure_blocker(win):
                blob = _window_text_blob(win)
                compact = re.sub(r"\s+", "", blob).lower()
                if not compact:
                    return False
                login_words = ("로그인", "사용자", "아이디", "id", "user", "비밀번호", "password")
                fail_words = ("실패", "오류", "오입력", "불일치", "확인", "잘못", "invalid", "incorrect", "fail", "error")
                return any(word.lower() in compact for word in login_words) and any(
                    word.lower() in compact for word in fail_words
                )

            def _fast_recovery_main_window():
                """Pick the existing ERP frame from top-level windows only.

                A populated GDI voucher can make ``descendants()`` block for minutes.
                Recovery therefore accepts only a large, visible top-level ERP frame
                whose own title/automation id identifies the ERP application.
                """
                main_keywords = [
                    self.corp_info.get("name", ""),
                    self.install_info.get("main_window_title", ""),
                    "K-System",
                    "대승",
                    "일강",
                    "제이엠",
                    "더원",
                ]
                candidates = []
                try:
                    # Application.windows()는 ``visible`` 키워드를 지원하지 않는다.
                    # 아래 루프의 win.is_visible() 필터로 가시성을 판정한다.
                    windows = self.app.windows()
                except Exception as exc:
                    self.logger.warning(
                        f"  [RECOVERY-PREFLIGHT] ERP 최상위 창 열거 실패: {exc}"
                    )
                    return None
                for win in windows:
                    try:
                        title = str(win.window_text() or "").strip()
                        auto_id = str(win.element_info.automation_id or "").strip()
                        if not win.is_visible():
                            continue
                        identity_match = auto_id.lower() == "mainwindow" or any(
                            keyword and keyword in title for keyword in main_keywords
                        )
                        if not identity_match:
                            continue
                        rect = win.rectangle()
                        width = max(0, int(rect.right) - int(rect.left))
                        height = max(0, int(rect.bottom) - int(rect.top))
                        if width < 640 or height < 400:
                            continue
                        candidates.append((width * height, width, height, win, title, auto_id))
                    except Exception:
                        continue
                if not candidates:
                    return None
                _, width, height, win, title, auto_id = max(
                    candidates,
                    key=lambda item: (item[0], item[1], item[2]),
                )
                self.logger.info(
                    "  [RECOVERY-PREFLIGHT] descendants 없이 ERP 최상위 메인 창 선택: "
                    f"title={title!r}, auto_id={auto_id!r}, size={width}x{height}, "
                    f"candidates={len(candidates)}"
                )
                try:
                    win.set_focus()
                except Exception:
                    pass
                return win

            main_win = None
            if resume_existing_voucher:
                main_win = _fast_recovery_main_window()
            try:
                login_wait_deadline = time.time() + float(os.getenv("ERP_LOGIN_MAIN_WAIT_SECONDS", "10") or "10")
                while not resume_existing_voucher and time.time() < login_wait_deadline:
                    try:
                        # 무조건 최상단 창을 가져와서 메인 ERP인지 먼저 판별합니다.
                        top = self.app.top_window()
                        top_text = top.window_text() or ""
                        top_auto = top.element_info.automation_id or ""
                        main_keywords = [self.corp_info.get("name", ""), "K-System", "대승", "일강", "제이엠", "더원"]

                        if top.is_visible() and _is_password_change_blocker(top):
                            msg = (
                                "ERP 로그인 실패: 비밀번호 변경 또는 만료 창이 표시되었습니다. "
                                "대승 ERP 계정 비밀번호를 변경한 뒤 243 Agent의 ERP 비밀번호 설정을 갱신하세요."
                            )
                            self.logger.error(msg)
                            return msg
                        if top.is_visible() and _is_login_failure_blocker(top):
                            msg = (
                                "ERP 로그인 실패: ID 또는 비밀번호가 맞지 않거나 로그인 확인 창이 표시되었습니다. "
                                "업로드 시 ERP 계정 정보를 다시 입력해 주세요."
                            )
                            self.logger.error(msg)
                            return msg

                        if top.is_visible() and (top_auto == "mainwindow" or any(k and k in top_text for k in main_keywords)):
                            # 메인 화면이 확실하게 로드된 경우
                            main_win = top
                            self.logger.info(f"메인 창 확인: title='{top_text}', auto_id='{top_auto}'")
                            break
                        
                        # Splash/로그인 화면이 아니면 팝업일 확률이 높으므로 짧게만 처리
                        if "Splash" not in top_text:
                            try:
                                top.set_focus()
                                time.sleep(0.1)
                                # 메인창에 N/ESC를 난사하지 않도록 팝업성 제목일 때만 fallback 키를 보냅니다.
                                if _is_password_change_blocker(top):
                                    msg = (
                                        "ERP 로그인 실패: 비밀번호 변경 또는 만료 창이 표시되었습니다. "
                                        "대승 ERP 계정 비밀번호를 변경한 뒤 243 Agent의 ERP 비밀번호 설정을 갱신하세요."
                                    )
                                    self.logger.error(msg)
                                    return msg
                                if _is_login_failure_blocker(top):
                                    msg = (
                                        "ERP 로그인 실패: ID 또는 비밀번호가 맞지 않거나 로그인 확인 창이 표시되었습니다. "
                                        "업로드 시 ERP 계정 정보를 다시 입력해 주세요."
                                    )
                                    self.logger.error(msg)
                                    return msg
                                if any(k in top_text for k in ("비밀번호", "변경", "알림", "Message", "확인")):
                                    pyautogui.press("n")       # '아니오' 단축키
                                    pyautogui.press("escape")  # 취소 단축키
                                    self.logger.info(f"팝업성 최상단 창('{top_text}')에 N과 ESC 전송 완료")
                            except: pass
                            
                        # 추가로 전체 윈도우 중 '아니요' 버튼이 있는 창을 찾아서 직접 클릭 시도 (더블 체크)
                        for w in self.app.windows():
                            try:
                                if w == main_win: continue
                                for btn in w.descendants(control_type="Button"):
                                    btn_name = btn.window_text() or ""
                                    btn_auto = btn.element_info.automation_id or ""
                                    if "아니" in btn_name or "다음에" in btn_name or btn_auto == "btnNo":
                                        btn.click_input()
                                        self.logger.info(f"'{btn_name}' 버튼 직접 클릭 완료")
                                        break
                            except: pass

                    except: pass
                    time.sleep(ERP_POLL_WAIT)
            except Exception as e:
                self.logger.warning(f"메인 창 탐색 에러: {e}")

            if not main_win and not resume_existing_voucher:
                try:
                    top = self.app.top_window()
                    if _is_password_change_blocker(top):
                        msg = (
                            "ERP 로그인 실패: 비밀번호 변경 또는 만료 창이 표시되었습니다. "
                            "대승 ERP 계정 비밀번호를 변경한 뒤 243 Agent의 ERP 비밀번호 설정을 갱신하세요."
                        )
                        self.logger.error(msg)
                        return msg
                    if _is_login_failure_blocker(top):
                        msg = (
                            "ERP 로그인 실패: ID 또는 비밀번호가 맞지 않거나 로그인 확인 창이 표시되었습니다. "
                            "업로드 시 ERP 계정 정보를 다시 입력해 주세요."
                        )
                        self.logger.error(msg)
                        return msg
                    top_text = top.window_text() or ""
                    top_auto = top.element_info.automation_id or ""
                    main_keywords = [self.corp_info.get("name", ""), "K-System", "대승", "일강", "제이엠", "더원"]
                    if top.is_visible() and (top_auto == "mainwindow" or any(k and k in top_text for k in main_keywords)):
                        main_win = top
                except:
                    pass
            if not main_win:
                msg = (
                    "ERP 로그인 실패: 10초 안에 ERP 메인 화면이 열리지 않았습니다. "
                    "업로드 시 입력한 ERP ID/PW를 확인해 주세요."
                )
                self.logger.error(msg)
                return msg

            if main_win:
                try:
                    self.erp_process_pid = int(confirmed_pid or getattr(main_win.element_info, "process_id", 0) or 0)
                except Exception:
                    self.erp_process_pid = int(confirmed_pid or 0)
                if not resume_existing_voucher and _is_password_change_blocker(main_win):
                    msg = (
                        "ERP 로그인 실패: 비밀번호 변경 또는 만료 창이 표시되었습니다. "
                        "대승 ERP 계정 비밀번호를 변경한 뒤 243 Agent의 ERP 비밀번호 설정을 갱신하세요."
                    )
                    self.logger.error(msg)
                    return msg
                try:
                    menu_step_wait = max(
                        ERP_BLOCK_WAIT,
                        float(os.getenv("ERP_MENU_STEP_WAIT", "0.75") or "0.75"),
                    )
                    menu_tree_wait = max(
                        ERP_CLICK_WAIT,
                        float(os.getenv("ERP_MENU_TREE_WAIT", "0.35") or "0.35"),
                    )
                    menu_entry_settle_wait = max(
                        ERP_SETTLE_WAIT,
                        float(os.getenv("ERP_MENU_ENTRY_SETTLE_WAIT", "0.60") or "0.60"),
                    )
                    ds_coordinate_menu = (
                        self.corp_code == "DS"
                        and (
                            str(os.getenv("ERP_DS_MENU_COORDINATE_ONLY", "1"))
                            .strip()
                            .lower()
                            not in {"", "0", "false", "no", "off"}
                        )
                    )
                    self._force_erp_window_maximized(main_win, "메뉴 진입 전 ERP 메인 창")
                    if resume_existing_voucher:
                        if (
                            resume_print_only_requested
                            and not self._resume_slip_form_ready(main_win)
                        ):
                            raise RuntimeError(
                                "ERP 전표 복구를 중단했습니다. 현재 ERP 화면이 "
                                "분개전표입력 전표 화면인지 확인되지 않습니다."
                            )
                        if resume_management_save_print:
                            self.logger.info(
                                "  [MGMT-RECOVERY] 현재 열린 전표에서 관리항목 입력·저장·출력을 재개합니다."
                            )
                        else:
                            self.logger.info(
                                "  [PRINT-RESUME] 현재 열린 저장 전표에서 출력 단계만 재개합니다."
                            )
                        self._setup_slip_form(main_win)
                        self._close_erp_after_success(main_win)
                        return True
                    time.sleep(menu_step_wait)
                    self.logger.info("메인 창을 최대화/활성화했습니다. 내비게이션 시작...")
                    self.logger.info(
                        f"  [MENU-SPEED] step={menu_step_wait:.2f}s, "
                        f"tree={menu_tree_wait:.2f}s, entry={menu_entry_settle_wait:.2f}s"
                    )
                    
                    def _elem_autoid(e):
                        try: return e.element_info.automation_id or ""
                        except: return ""
                        
                    def _elem_name(e):
                        try: return e.window_text() or ""
                        except: return ""
                    
                    def _get_item_own_text(item):
                        try:
                            ct = _elem_name(item).strip()
                            if ct: return ct
                            for ch in item.children():
                                ct_type = getattr(ch.element_info, 'control_type', '')
                                cls = getattr(ch.element_info, 'class_name', '') or ""
                                if ct_type == "Text" or "TextBlock" in cls:
                                    tn = _elem_name(ch).strip()
                                    if tn: return tn
                        except: pass
                        return ""

                    def _find_item(tree, text):
                        try:
                            for item in tree.descendants(control_type="TreeItem"):
                                if _get_item_own_text(item) == text:
                                    return item
                        except: pass
                        return None
                        
                    def _count_items(tree):
                        try: return len(tree.descendants(control_type="TreeItem"))
                        except: return 0
                        
                    def _already_expanded(item):
                        try:
                            for ch in item.children():
                                if getattr(ch.element_info, 'control_type', '') == "TreeItem": return True
                        except: pass
                        return False
                        
                    def _expand(tree, item, label):
                        if _already_expanded(item):
                            self.logger.info(f"  '{label}' 노드는 이미 열려있음")
                            return True
                        before = _count_items(tree)
                        try:
                            item.expand()
                            time.sleep(menu_step_wait)
                            if _count_items(tree) > before: return True
                        except: pass
                        try:
                            expander = None
                            for ch in item.children():
                                if _elem_autoid(ch) == "Expander" or getattr(ch.element_info, 'control_type', '') == "Button":
                                    expander = ch; break
                            if expander:
                                expander.click_input()
                                time.sleep(menu_step_wait)
                                if _count_items(tree) > before: return True
                        except: pass
                        try:
                            item.click_input()
                            time.sleep(menu_step_wait)
                            if _count_items(tree) > before: return True
                        except: pass
                        self.logger.warning(f"  '{label}' 노드를 여는데 실패했습니다.")
                        return False

                    def _menu_popup_visible():
                        try:
                            found = set()
                            for b in main_win.descendants(control_type="Button"):
                                n = _elem_name(b).strip()
                                if n in ("인사관리", "근태관리", "회계관리", "추가개발"):
                                    found.add(n)
                            return len(found) >= 2
                        except: return False

                    def _get_tree():
                        try:
                            for t in main_win.descendants(control_type="Tree"):
                                return t
                        except: pass
                        return None

                    def _tree_has(text):
                        tree = _get_tree()
                        return bool(tree and _find_item(tree, text))

                    def _click_text_exact(text, control_types=("Button", "ListItem", "Text")):
                        """ERP 메뉴 타일은 Button/Text로 섞여 잡히므로 이름 기준으로 클릭합니다."""
                        scopes = [main_win]
                        try:
                            scopes += [w for w in Desktop(backend="uia").windows()
                                       if getattr(w.element_info, 'process_id', None) == confirmed_pid]
                        except: pass
                        for scope in scopes:
                            for ct in control_types:
                                try:
                                    for el in scope.descendants(control_type=ct):
                                        if _elem_name(el).strip() == text:
                                            try:
                                                el.click_input()
                                            except Exception:
                                                r = el.rectangle()
                                                pyautogui.click(r.left + r.width() // 2, r.top + r.height() // 2)
                                            return True
                                except: pass
                        return False

                    def _click_rel(x, y, label):
                        r = main_win.rectangle()
                        pyautogui.click(r.left + x, r.top + y)
                        self.logger.info(f"  [DEBUG] {label} 좌표 클릭 완료: rel=({x}, {y}), abs=({r.left + x}, {r.top + y})")

                    def _click_tree_item_by_text(text, *, expand=False, label=None):
                        tree = _get_tree()
                        if not tree:
                            return False
                        item = _find_item(tree, text)
                        if not item:
                            return False
                        label = label or text
                        if expand:
                            if _expand(tree, item, label):
                                self.logger.info(f"  [TREE-UIA] '{label}' 트리 확장 성공")
                                return True
                        try:
                            item.click_input()
                        except Exception:
                            rect = item.rectangle()
                            pyautogui.click((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
                        self.logger.info(f"  [TREE-UIA] '{label}' 트리 항목 클릭 성공")
                        return True

                    def _open_slip_menu_by_uia_path():
                        if _tree_has("분개전표입력"):
                            return _click_slip_menu_by_uia()
                        if not _click_tree_item_by_text("전표", expand=True):
                            return False
                        time.sleep(menu_tree_wait)
                        if _tree_has("분개전표입력"):
                            return _click_slip_menu_by_uia()
                        if not _click_tree_item_by_text("전표처리", expand=True):
                            return False
                        time.sleep(menu_tree_wait)
                        return _click_slip_menu_by_uia()

                    def _slip_menu_fallback_points():
                        if self.corp_code == "DS":
                            base_y = int(os.getenv("ERP_DS_SLIP_ROOT_Y", "137") or "137")
                            row_h = int(os.getenv("ERP_DS_SLIP_ROW_H", "29") or "29")
                            slip_x = int(os.getenv("ERP_DS_SLIP_ROOT_X", "105") or "105")
                            process_x = int(os.getenv("ERP_DS_SLIP_PROCESS_X", "126") or "126")
                            entry_x = int(os.getenv("ERP_DS_SLIP_ENTRY_X", "155") or "155")
                            self.logger.info(
                                f"  [TREE-XY] DS 고정 메뉴 좌표 사용: "
                                f"전표=({slip_x},{base_y}), row_h={row_h}"
                            )
                            return {
                                "slip": (slip_x, base_y),
                                "process": (process_x, base_y + row_h),
                                "entry": (entry_x, base_y + row_h * 2),
                            }
                        return {
                            "slip": (105, 107),
                            "process": (126, 137),
                            "entry": (155, 166),
                        }

                    def _open_slip_menu_by_ds_coordinates():
                        """DS 1920x1040 고정 화면에서 UIA 없이 전표 메뉴를 엽니다."""
                        points = _slip_menu_fallback_points()
                        self.logger.info(
                            "  [TREE-XY] DS 좌표 전용 경로: "
                            "전표 선택/Right -> 전표처리 선택/Right -> 분개전표입력 선택/Enter"
                        )

                        _click_rel(*points["slip"], "전표")
                        time.sleep(menu_tree_wait)
                        pyautogui.press("right")
                        time.sleep(menu_step_wait)

                        _click_rel(*points["process"], "전표처리")
                        time.sleep(menu_tree_wait)
                        pyautogui.press("right")
                        time.sleep(menu_step_wait)

                        _click_rel(*points["entry"], "분개전표입력")
                        time.sleep(menu_tree_wait)
                        pyautogui.press("enter")
                        time.sleep(menu_entry_settle_wait)
                        return True

                    def _open_accounting_menu():
                        self.logger.info("  [MENU-START] 메뉴 진입 시작")

                        # 1. 왼쪽 상단 '메뉴' 버튼
                        self.logger.info("  [MENU-01] 왼쪽 상단 '메뉴' 버튼 클릭 시도")
                        if ds_coordinate_menu:
                            _click_rel(30, 70, "메뉴")
                            self.logger.info("  [MENU-01] DS 좌표 전용으로 '메뉴' 클릭 성공")
                        elif _click_text_exact("메뉴", ("Button", "Text")):
                            self.logger.info("  [MENU-01] UI 요소로 '메뉴' 클릭 성공")
                        else:
                            self.logger.warning("  [MENU-01] UI 요소 '메뉴' 미발견, 좌표 fallback 실행")
                            _click_rel(30, 70, "메뉴")
                        time.sleep(menu_step_wait)
                        self.logger.info("  [MENU-01] 메뉴 클릭 후 짧은 대기 완료")

                        # 2. 왼쪽의 현재 모듈 버튼 '회계관리 >>' 위치 클릭
                        self.logger.info("  [MENU-02] 왼쪽 '회계관리 >>' 위치 클릭 시도")
                        _click_rel(145, 70, "왼쪽 회계관리>>")
                        time.sleep(menu_step_wait)
                        self.logger.info("  [MENU-02] 왼쪽 '회계관리 >>' 클릭 후 짧은 대기 완료")

                        # 3. 메뉴 화면의 '회계관리' 타일 클릭
                        self.logger.info("  [MENU-03] 메뉴 내부 '회계관리' 타일 클릭 시도")
                        clicked_tile = False
                        if ds_coordinate_menu:
                            tile_x = int(os.getenv("ERP_DS_ACCOUNTING_TILE_X", "304") or "304")
                            tile_y = int(os.getenv("ERP_DS_ACCOUNTING_TILE_Y", "201") or "201")
                            _click_rel(tile_x, tile_y, "DS accounting menu tile")
                            self.logger.info("  [MENU-03] DS 좌표 전용으로 회계관리 타일 클릭 성공")
                            clicked_tile = True
                        if not ds_coordinate_menu:
                            try:
                                scopes = [main_win]
                                scopes += [w for w in Desktop(backend="uia").windows()
                                           if getattr(w.element_info, 'process_id', None) == confirmed_pid]
                                for scope in scopes:
                                    if clicked_tile: break
                                    for ct in ("Button", "ListItem", "Text"):
                                        try:
                                            for el in scope.descendants(control_type=ct):
                                                if _elem_name(el).strip() == "회계관리":
                                                    r = el.rectangle()
                                                    # 왼쪽 트리의 '회계관리 >>'가 아니라 메뉴 타일 영역만 허용합니다.
                                                    rel_left = r.left - main_win.rectangle().left
                                                    rel_top = r.top - main_win.rectangle().top
                                                    is_ds_accounting_tile = self.corp_code == "DS" and rel_left >= 60 and rel_top >= 120
                                                    is_legacy_accounting_tile = rel_left > 250
                                                    if is_ds_accounting_tile or is_legacy_accounting_tile:
                                                        try:
                                                            el.click_input()
                                                        except Exception:
                                                            pyautogui.click(r.left + r.width() // 2, r.top + r.height() // 2)
                                                        self.logger.info(f"  [MENU-03] UI 요소로 메뉴 타일 '회계관리' 클릭 성공: rect=({r.left},{r.top})-({r.right},{r.bottom})")
                                                        clicked_tile = True
                                                        break
                                        except: pass
                                        if clicked_tile: break
                            except Exception as e:
                                self.logger.warning(f"  [MENU-03] UI 타일 탐색 중 예외: {e}")

                        if not clicked_tile:
                            self.logger.warning("  [MENU-03] 메뉴 타일 UI 미발견, 좌표 fallback 실행")
                            # 화면 기준: 두 번째 이미지의 회계관리 타일 중앙 부근
                            # DS accounting menu tile moved to first column, second row after operation-management permission was added.
                            if self.corp_code == "DS":
                                tile_x = int(os.getenv("ERP_DS_ACCOUNTING_TILE_X", "304") or "304")
                                tile_y = int(os.getenv("ERP_DS_ACCOUNTING_TILE_Y", "201") or "201")
                                _click_rel(tile_x, tile_y, "DS accounting menu tile")
                            else:
                                _click_rel(390, 115, "accounting menu tile")
                        time.sleep(menu_step_wait)
                        self.logger.info("  [MENU-03] 회계관리 타일 클릭 후 짧은 대기 완료")
                        pyautogui.press("escape")
                        self.logger.info("  [MENU-03] 메뉴 닫기용 ESC 1회 전송 완료")
                        time.sleep(menu_entry_settle_wait)

                        if ds_coordinate_menu:
                            self.logger.info("  [MENU-04] DS 좌표 전용 경로이므로 UIA 트리 검증을 건너뜁니다.")
                            return True

                        # 4. 전환 검증
                        self.logger.info("  [MENU-04] 왼쪽 트리에 '전표'가 보이는지 검증 시작")
                        for attempt in range(1, 3):
                            if _tree_has("전표"):
                                self.logger.info(f"  [MENU-04] 검증 성공: '전표' 발견 (시도 {attempt}/4)")
                                return True
                            self.logger.warning(
                                f"  [MENU-04] 아직 '전표' 미발견 (시도 {attempt}/2), "
                                f"{menu_entry_settle_wait:.2f}초 대기"
                            )
                            time.sleep(menu_entry_settle_wait)
                        self.logger.warning("  [MENU-04] UIA로 '전표' 미검출. 화면상 노출 가능성이 높아 좌표 fallback으로 진행합니다.")
                        return True

                    def _click_slip_menu_by_uia():
                        try:
                            for el in main_win.descendants():
                                if str(el.window_text() or "").strip() == "분개전표입력":
                                    rect = el.rectangle()
                                    pyautogui.click((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
                                    self.logger.info(
                                        f"  [TREE-UIA] 분개전표입력 UI 요소 클릭 전송: "
                                        f"rect=({rect.left},{rect.top})-({rect.right},{rect.bottom})"
                                    )
                                    time.sleep(menu_entry_settle_wait)
                                    return True
                        except Exception as e:
                            self.logger.warning(f"  [TREE-UIA] 분개전표입력 UI 클릭 실패: {e}")
                        return False

                    def _slip_form_ready():
                        try:
                            expected_texts = {
                                "신규",
                                "전표출력",
                                "회계일",
                                "회계단위",
                                "전표관리단위",
                                "계정과목",
                            }
                            for el in main_win.descendants():
                                text = str(el.window_text() or "").strip()
                                auto_id = str(getattr(el.element_info, "automation_id", "") or "").strip()
                                if auto_id == "New" or text in expected_texts:
                                    return True
                        except Exception as e:
                            self.logger.warning(f"  [TREE-VERIFY] 분개전표입력 화면 검증 중 오류: {e}")
                        return False

                    def _wait_slip_form_ready(timeout=0.45):
                        end_at = time.time() + max(0.05, timeout)
                        while time.time() < end_at:
                            if _slip_form_ready():
                                return True
                            time.sleep(0.05)
                        return _slip_form_ready()

                    def _close_left_menu_before_form_input():
                        """분개전표입력 선택 후 남는 좌측 메뉴 패널을 닫아 첫 입력 클릭이 먹히지 않게 합니다."""
                        try:
                            pyautogui.press("escape")
                            time.sleep(menu_tree_wait)
                        except Exception as e:
                            self.logger.warning(f"  [MENU-CLOSE] ESC 메뉴 닫기 실패: {e}")
                        try:
                            r = main_win.rectangle()
                            x = int(os.getenv("ERP_MENU_CLOSE_CLICK_X", "620") or "620")
                            y = int(os.getenv("ERP_MENU_CLOSE_CLICK_Y", "124") or "124")
                            pyautogui.click(r.left + x, r.top + y)
                            self.logger.info(f"  [MENU-CLOSE] 폼 영역 클릭으로 좌측 메뉴 닫기 시도: rel=({x}, {y})")
                            time.sleep(menu_entry_settle_wait)
                        except Exception as e:
                            self.logger.warning(f"  [MENU-CLOSE] 폼 영역 클릭 실패: {e}")
                        return _wait_slip_form_ready(0.35)

                    # Step 1~3: 실제 사용자 동선 그대로 메뉴 -> 왼쪽 회계관리>> -> 메뉴 내부 회계관리 타일 선택
                    if ds_coordinate_menu or not _tree_has("전표"):
                        self.logger.info("  [MENU] 메뉴 버튼 -> 왼쪽 회계관리>> -> 메뉴 내부 회계관리 타일 선택 시작")
                        if _open_accounting_menu():
                            self.logger.info("  ✅ 회계관리 트리 전환 확인")
                        else:
                            self.logger.warning("  [MENU] 회계관리 전환 확인 실패")

                    # Step 3~5: 트리 탐색 및 분개전표입력 클릭
                    # DS는 고정 1920x1040 화면의 좌표/키 경로만 사용합니다.
                    # 다른 법인은 UIA 텍스트 경로를 먼저 사용하고 실패할 때만 좌표 fallback을 사용합니다.
                    opened_slip_form = False
                    self.logger.info("  [TREE] 전표 -> 전표처리 -> 분개전표입력 진입 시작")

                    if ds_coordinate_menu:
                        _open_slip_menu_by_ds_coordinates()
                        self.logger.info("  [TREE-XY] DS 좌표 전용 경로 클릭 완료")
                    elif _open_slip_menu_by_uia_path():
                        self.logger.info("  [TREE-UIA] 분개전표입력 텍스트 경로 클릭 완료")
                    else:
                        points = _slip_menu_fallback_points()
                        self.logger.warning("  [TREE-XY] UIA 텍스트 경로 실패, 좌표 fallback으로 전표 메뉴를 엽니다.")
                        slip_menu_visible = _tree_has("분개전표입력")
                        slip_process_visible = _tree_has("전표처리")

                        if slip_menu_visible:
                            self.logger.info("  [TREE-XY] '분개전표입력'이 이미 보임. 전표/전표처리 확장 클릭 스킵")
                        else:
                            if slip_process_visible:
                                self.logger.info("  [TREE-XY] '전표처리'가 이미 보임. 전표 클릭 스킵")
                            else:
                                _click_rel(*points["slip"], "전표")
                                time.sleep(menu_tree_wait)

                            if _tree_has("분개전표입력"):
                                self.logger.info("  [TREE-XY] '분개전표입력'이 이미 보임. 전표처리 클릭 스킵")
                            else:
                                _click_rel(*points["process"], "전표처리")
                                time.sleep(menu_tree_wait)

                        if not _click_slip_menu_by_uia():
                            _click_rel(*points["entry"], "분개전표입력")
                            self.logger.info("  [TREE-XY] 분개전표입력 좌표 클릭 전송")
                            time.sleep(menu_entry_settle_wait)

                    opened_slip_form = _wait_slip_form_ready(
                        float(os.getenv("ERP_SLIP_OPEN_WAIT", "0.45") or "0.45")
                    )
                    if not opened_slip_form:
                        if ds_coordinate_menu:
                            self.logger.error(
                                "  [TREE-VERIFY] DS 좌표 전용 경로 검증 실패. "
                                "다른 메뉴나 폼 셀 오클릭을 막기 위해 추가 클릭 없이 중단합니다."
                            )
                        else:
                            self.logger.warning("  [TREE-VERIFY] 분개전표입력 화면 검증 실패. 진입을 한 번 재시도합니다.")
                            if _click_slip_menu_by_uia():
                                opened_slip_form = _wait_slip_form_ready(0.35)
                            if not opened_slip_form:
                                pyautogui.press("enter")
                                time.sleep(menu_entry_settle_wait)
                                opened_slip_form = _wait_slip_form_ready(0.35)
                    if opened_slip_form:
                        self.logger.info("  [TREE-VERIFY] 분개전표입력 화면 진입 확인")
                        if _close_left_menu_before_form_input():
                            self.logger.info("  [MENU-CLOSE] 좌측 메뉴 정리 후 폼 입력 준비 완료")
                        else:
                            self.logger.warning("  [MENU-CLOSE] 좌측 메뉴 정리 후 폼 검증 실패. 기존 흐름으로 계속 진행합니다.")
                            
                    # ── 최종 단계: 폼 데이터 입력 (클립보드 방식 개선된 v6.1 _setup_slip_form 호출) ──
                    if opened_slip_form:
                        self.logger.info("👉 폼 데이터 세팅을 시작합니다...")
                        self._setup_slip_form(main_win)
                        self._close_erp_after_success(main_win)
                    else:
                        raise RuntimeError("분개전표입력 화면 진입 검증 실패. 폼 세팅을 중단합니다.")
                    
                except Exception as e:
                    self.logger.error(f"메뉴/폼 자동입력 실패: {e}")
                    return f"메뉴/폼 자동입력 실패:\n{e}"

            return True

        except Exception as e: 
            return f"알 수 없는 에러:\n{e}"

    def _resume_slip_form_ready(self, main_win):
        """출력 복구가 현재 열린 분개전표 화면에만 붙도록 강하게 검증합니다."""
        identity_hits = set()
        structure_hits = set()

        controls = [main_win]
        try:
            controls.extend(main_win.descendants())
        except Exception as e:
            self.logger.warning(f"  [PRINT-RESUME] 현재 전표 화면 UIA 조회 실패: {e}")

        for ctrl in controls:
            try:
                if ctrl is not main_win and hasattr(ctrl, "is_visible") and not ctrl.is_visible():
                    continue
            except Exception:
                continue

            try:
                text = str(ctrl.window_text() or "").strip()
            except Exception:
                text = ""
            try:
                auto_id = str(getattr(ctrl.element_info, "automation_id", "") or "").strip()
            except Exception:
                auto_id = ""
            try:
                class_name = str(getattr(ctrl.element_info, "class_name", "") or "").strip()
            except Exception:
                class_name = ""

            compact_text = re.sub(r"\s+", "", text).lower()
            technical_id = f"{auto_id} {class_name}".lower()
            if "분개전표입력" in compact_text:
                identity_hits.add("분개전표입력")
            if "frmacslip" in technical_id or "frmacslip" in compact_text:
                identity_hits.add("FrmAcSlip")

            if auto_id.lower() == "new" or compact_text == "신규":
                structure_hits.add("신규")
            if "전표출력" in compact_text:
                structure_hits.add("전표출력")
            if "전표관리단위" in compact_text:
                structure_hits.add("전표관리단위")
            if "전표분개유형" in compact_text:
                structure_hits.add("전표분개유형")
            if compact_text == "회계일" or compact_text.startswith("회계일"):
                structure_hits.add("회계일")
            if compact_text == "계정과목" or compact_text.startswith("계정과목"):
                structure_hits.add("계정과목")

        ready = bool(identity_hits) and len(structure_hits) >= 2
        self.logger.info(
            "  [PRINT-RESUME] 현재 전표 화면 검증: "
            f"ready={ready}, identity={sorted(identity_hits)}, "
            f"structure={sorted(structure_hits)}"
        )
        return ready

    def _setup_slip_form(self, main_win):
        """
        분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)
        """
        resume_print_only_requested = (
            str(os.getenv("ERP_RESUME_PRINT_ONLY", "0"))
            .strip()
            .lower()
            in {"1", "true", "yes", "y", "on"}
        )
        resume_management_save_print = (
            str(os.getenv("ERP_RESUME_MANAGEMENT_SAVE_PRINT", "0"))
            .strip()
            .lower()
            in {"1", "true", "yes", "y", "on"}
        )
        if resume_print_only_requested and resume_management_save_print:
            raise RuntimeError("출력 전용 복구와 관리항목·저장·출력 복구를 동시에 실행할 수 없습니다.")
        # Keep all existing no-new/no-paste guards effective for either recovery.
        resume_existing_voucher = resume_print_only_requested or resume_management_save_print
        original_clipboard = pyperclip.paste()
        form_data = getattr(self.manager.main_app, 'data', {})
        form_clipboard_rows = form_data.get('erp_clipboard_rows') or []
        if not resume_existing_voucher and isinstance(form_clipboard_rows, list) and form_clipboard_rows:
            original_clipboard = "\r\n".join(str(row) for row in form_clipboard_rows)
            pyperclip.copy(original_clipboard)
            self.logger.info(f"[폼세팅] form_data ERP clipboard rows restored: {len(form_clipboard_rows)}")
        site_name    = form_data.get('site_name', '')
        invoice_date = form_data.get('invoice_date', '')
        if not invoice_date and not resume_existing_voucher:
            tax_path = getattr(self.manager.main_app, 'tax_path', '')
            try:
                invoice_date = self.manager.main_app._extract_issue_date_from_pdf(tax_path)
                if invoice_date:
                    self.logger.info(f"[폼세팅] tax PDF에서 회계일 복구: {invoice_date}")
            except Exception:
                invoice_date = ""
            m = re.search(r'(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})', os.path.basename(tax_path or ''))
            if invoice_date:
                pass
            elif m:
                invoice_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                self.logger.info(f"[폼세팅] tax filename에서 회계일 복구: {invoice_date}")
            else:
                msg = "세금계산서 작성일자를 찾지 못해 회계일을 입력할 수 없습니다. 오늘 날짜 자동입력은 차단했습니다."
                self.logger.error(f"[폼세팅] {msg}")
                raise RuntimeError(msg)
        items_list   = form_data.get('items', [])
        clipboard_rows = [line for line in str(original_clipboard or '').splitlines() if line.strip()]
        row_count = int(form_data.get('erp_row_count') or len(clipboard_rows) or ((len(items_list) + 2) if items_list else 1))

        def _env_flag(name, default="0"):
            return str(os.getenv(name, default)).strip().lower() not in ("0", "false", "no", "off", "")

        fast_input = _env_flag("ERP_FAST_INPUT", "0")
        fast_field_verify = _env_flag("ERP_FAST_FIELD_VERIFY", "0")
        fast_management = _env_flag("ERP_FAST_MANAGEMENT", "0")
        strict_form_steps = _env_flag("ERP_STRICT_FORM_STEPS", "0")
        verbose_keysafe = _env_flag("ERP_VERBOSE_KEYSAFE", "0")
        verbose_management_clear = _env_flag("ERP_VERBOSE_MGMT_CLEAR", "0")
        quick_wait = 0.05 if fast_input else 0.10
        critical_field_wait = max(0.12, float(os.getenv("ERP_CRITICAL_FIELD_WAIT", "0.18") or "0.18"))
        form_step_wait = max(0.0, float(os.getenv("ERP_FORM_STEP_WAIT", "0.0") or "0.0"))
        mgmt_key_default = "0.08" if fast_management else "0.16"
        mgmt_commit_default = "0.14" if fast_management else "0.26"
        mgmt_focus_default = "0.10" if fast_management else "0.20"
        mgmt_click_default = "0.12" if fast_management else "0.24"
        mgmt_clipboard_default = "0.04" if fast_management else "0.08"
        mgmt_key_wait = max(quick_wait, float(os.getenv("ERP_MGMT_KEY_WAIT", mgmt_key_default) or mgmt_key_default))
        mgmt_commit_wait = max(mgmt_key_wait, float(os.getenv("ERP_MGMT_COMMIT_WAIT", mgmt_commit_default) or mgmt_commit_default))
        mgmt_focus_wait = max(quick_wait, float(os.getenv("ERP_MGMT_FOCUS_WAIT", mgmt_focus_default) or mgmt_focus_default))
        mgmt_click_wait = max(quick_wait, float(os.getenv("ERP_MGMT_CLICK_WAIT", mgmt_click_default) or mgmt_click_default))
        mgmt_clipboard_wait = max(0.02, float(os.getenv("ERP_MGMT_CLIPBOARD_WAIT", mgmt_clipboard_default) or mgmt_clipboard_default))
        mgmt_summary_open_wait = max(mgmt_click_wait, float(os.getenv("ERP_MGMT_SUMMARY_OPEN_WAIT", "0.55") or "0.55"))
        mgmt_after_summary_open_wait = max(0.0, float(os.getenv("ERP_MGMT_AFTER_SUMMARY_OPEN_WAIT", "0.05" if fast_management else "0.20") or "0.0"))
        mgmt_after_grid_paste_wait = max(0.40, float(os.getenv("ERP_MGMT_AFTER_GRID_PASTE_WAIT", "0.70") or "0.70"))
        vendor_popup_open_wait = max(0.35, float(os.getenv("ERP_VENDOR_POPUP_OPEN_WAIT", "0.55") or "0.55"))
        vendor_popup_focus_wait = max(mgmt_focus_wait, float(os.getenv("ERP_VENDOR_POPUP_FOCUS_WAIT", "0.12" if fast_management else "0.45") or "0.45"))
        vendor_popup_search_wait = max(mgmt_key_wait, float(os.getenv("ERP_VENDOR_POPUP_SEARCH_WAIT", "0.25" if fast_management else "0.55") or "0.55"))
        finance_vendor_paste_settle_wait = max(
            mgmt_key_wait,
            float(os.getenv("ERP_FINANCE_VENDOR_PASTE_SETTLE_WAIT", "1.00") or "1.00"),
        )
        finance_vendor_commit_settle_wait = max(
            mgmt_commit_wait,
            float(os.getenv("ERP_FINANCE_VENDOR_COMMIT_SETTLE_WAIT", "2.00") or "2.00"),
        )
        # 분할 바 위치에 따라 전표 그리드가 커지면 GDI/RDP 스크롤 재도색이
        # 더 느려진다. 행 전환 대기는 큰 화면 기준으로 충분히 잡는다.
        finance_row_advance_settle_wait = max(
            mgmt_commit_wait,
            float(os.getenv("ERP_FINANCE_ROW_ADVANCE_SETTLE_WAIT", "2.50") or "2.50"),
        )
        vendor_double_click_hold = min(
            0.25,
            max(0.04, float(os.getenv("ERP_VENDOR_DOUBLE_CLICK_HOLD", "0.08") or "0.08")),
        )
        vendor_double_click_interval = min(
            0.40,
            max(0.12, float(os.getenv("ERP_VENDOR_DOUBLE_CLICK_INTERVAL", "0.18") or "0.18")),
        )
        vendor_popup_result_close_wait = max(
            1.0,
            float(os.getenv("ERP_VENDOR_POPUP_RESULT_CLOSE_WAIT", "2.5") or "2.5"),
        )
        skip_visible_row_scan = _env_flag("ERP_SKIP_VISIBLE_ROW_SCAN", "1" if fast_management else "0")

        if fast_input:
            try:
                pause = max(0.0, float(os.getenv("ERP_PYAUTOGUI_PAUSE", "0.01") or "0.01"))
                pyautogui.PAUSE = pause
                if hasattr(pyautogui, "MINIMUM_DURATION"):
                    pyautogui.MINIMUM_DURATION = 0
                if hasattr(pyautogui, "MINIMUM_SLEEP"):
                    pyautogui.MINIMUM_SLEEP = 0
                if hasattr(pyautogui, "DARWIN_CATCH_UP_TIME"):
                    pyautogui.DARWIN_CATCH_UP_TIME = 0
                self.logger.info(
                    f"[FORM-SPEED] pyautogui_pause={pause}, mgmt_key={mgmt_key_wait}, "
                    f"mgmt_commit={mgmt_commit_wait}, mgmt_click={mgmt_click_wait}"
                )
            except Exception as e:
                self.logger.warning(f"[FORM-SPEED] pyautogui 속도 설정 실패: {e}")

        self.logger.info(f"[폼세팅] site={site_name} / date={invoice_date} / rows={row_count} / clipboard_rows={len(clipboard_rows)}")
        self._force_erp_window_maximized(main_win, "폼 좌표 입력 전 ERP 메인 창")

        # 덤프 진단
        if _env_flag("ERP_FORM_DEBUG_DUMP", "0"):
            try:
                dump_path = os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys,'frozen',False) else __file__)), "erp_ui_dump.txt")
                lines = []
                for ctrl in main_win.descendants():
                    try:
                        aid  = ctrl.element_info.automation_id or ''
                        name = ctrl.window_text() or ''
                        ct   = ctrl.element_info.control_type or ''
                        r    = ctrl.rectangle()
                        lines.append(f"{ct}  aid={aid!r}  name={name!r}  rect=({r.left},{r.top})-({r.right},{r.bottom})")
                    except: pass
                with open(dump_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                self.logger.info(f"  [진단] UI 덤프 저장됨 → {dump_path}")
            except Exception as e:
                self.logger.warning(f"  [진단] 덤프 실패: {e}")

        # [신규] 버튼. 두 복구 모드에서는 현재 붙여넣은 전표를 보존해야 하므로 절대 누르지 않습니다.
        if not resume_existing_voucher:
            try:
                btn_new = None
                for b in main_win.descendants(control_type='Button'):
                    try:
                        aid = b.element_info.automation_id or ''
                        nm  = b.window_text() or ''
                        nm_norm = _norm_text(nm)
                        if "복사" in nm_norm or "저장" in nm_norm:
                            continue
                        if aid == 'New' or nm_norm == _norm_text('신규'):
                            btn_new = b; break
                    except: pass
                if btn_new and btn_new.is_visible():
                    try:
                        new_click_count = int(str(os.getenv("ERP_NEW_CLICK_COUNT", "1") or "1").strip())
                    except:
                        new_click_count = 1
                    new_click_count = max(1, min(2, new_click_count))
                    for idx in range(new_click_count):
                        btn_new.click_input()
                        self.logger.info(f"  ✅ [신규] 클릭 ({idx + 1}/{new_click_count})")
                        time.sleep(max(0.03, float(os.getenv("ERP_NEW_FORM_WAIT", "0.12") or "0.12")))
            except Exception as e:
                self.logger.warning(f"  [신규] 클릭 실패: {e}")

        def _safe_paste(text):
            pyperclip.copy(text)
            time.sleep(0.02 if fast_input else 0.04)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.02 if fast_input else 0.04)

        excel_copy_context = {"app": None, "book": None, "sheet_name": None, "end_row": 0, "end_col": 0}

        def _grid_row_to_excel_values(line):
            cols = str(line or "").split("\t")
            if len(cols) >= 5 and not cols[1].strip():
                summary_cols = cols[4:]
                if summary_cols and not summary_cols[0].strip():
                    summary_cols = summary_cols[1:]
                cols = [cols[0], cols[2], cols[3], "", "\t".join(summary_cols)]
            elif len(cols) == 4:
                cols = [cols[0], cols[1], cols[2], "", cols[3]]
            elif len(cols) >= 5:
                cols = [cols[0], cols[1], cols[2], cols[3], "\t".join(cols[4:])]
            else:
                cols = (cols + ["", "", "", "", ""])[:5]

            result = [str(value or "").strip() for value in cols[:5]]
            for idx in (1, 2):
                compact = result[idx].replace(",", "")
                if re.fullmatch(r"-?\d+", compact or ""):
                    result[idx] = int(compact)
                elif compact == "":
                    result[idx] = 0
            return result

        def _copy_grid_rows_via_excel():
            if not _env_flag("ERP_GRID_COPY_VIA_EXCEL", "0"):
                return False

            source_path = str(form_data.get("erp_excel_source_path") or "").strip()
            if not source_path:
                self.logger.info("  [FORM-GRID] Excel source path empty; clipboard fallback")
                return False
            if not os.path.exists(source_path):
                raise RuntimeError(f"Excel source file not found for ERP paste: {source_path}")

            rows_for_excel = [
                _grid_row_to_excel_values(line)
                for line in str(original_clipboard or "").splitlines()
                if str(line or "").strip()
            ]
            if not rows_for_excel:
                raise RuntimeError("ERP paste rows are empty.")

            abs_source_path = os.path.abspath(source_path)
            sheet_name = "ERP_PASTE"
            pythoncom.CoInitialize()
            app = win32.DispatchEx("Excel.Application")
            app.Visible = True
            app.DisplayAlerts = False
            book = app.Workbooks.Open(abs_source_path)
            excel_copy_context["app"] = app
            excel_copy_context["book"] = book

            for idx in range(book.Worksheets.Count, 0, -1):
                sheet = book.Worksheets(idx)
                if str(sheet.Name).strip().lower() == sheet_name.lower():
                    sheet.Delete()
                    break

            sheet = book.Worksheets.Add(After=book.Worksheets(book.Worksheets.Count))
            sheet.Name = sheet_name
            end_row = len(rows_for_excel)
            end_col = 5
            target = sheet.Range(sheet.Cells(1, 1), sheet.Cells(end_row, end_col))
            target.Value = tuple(tuple(row) for row in rows_for_excel)
            sheet.Columns("A:E").AutoFit()
            book.Save()
            sheet.Activate()
            target.Select()
            target.Copy()
            excel_copy_context["sheet_name"] = sheet_name
            excel_copy_context["end_row"] = end_row
            excel_copy_context["end_col"] = end_col
            time.sleep(max(0.2, float(os.getenv("ERP_EXCEL_COPY_SETTLE_SECONDS", "0.8") or "0.8")))
            self.logger.info(
                f"  [FORM-GRID] Excel range copied: path={abs_source_path}, "
                f"sheet={sheet_name}, range=A1:E{end_row}"
            )
            return True

        def _refresh_excel_grid_clipboard():
            book = excel_copy_context.get("book")
            if book is None:
                return False
            try:
                sheet_name = str(excel_copy_context.get("sheet_name") or "ERP_PASTE")
                end_row = int(excel_copy_context.get("end_row") or 0)
                end_col = int(excel_copy_context.get("end_col") or 0)
                if end_row <= 0 or end_col <= 0:
                    return False
                sheet = book.Worksheets(sheet_name)
                target = sheet.Range(sheet.Cells(1, 1), sheet.Cells(end_row, end_col))
                sheet.Activate()
                target.Select()
                target.Copy()
                time.sleep(max(0.2, float(os.getenv("ERP_EXCEL_COPY_SETTLE_SECONDS", "0.8") or "0.8")))
                self.logger.info(f"  [FORM-GRID] Excel range re-copied for ERP paste: range=A1:E{end_row}")
                return True
            except Exception as e:
                self.logger.warning(f"  [FORM-GRID] Excel range re-copy failed; text clipboard fallback: {e}")
                return False

        def _close_excel_copy_workbook():
            if _env_flag("ERP_KEEP_PASTE_WORKBOOK", "0"):
                return
            book = excel_copy_context.get("book")
            app = excel_copy_context.get("app")
            if book is not None:
                try:
                    book.Close(SaveChanges=True)
                except Exception as e:
                    self.logger.warning(f"  [FORM-GRID] Excel paste workbook close failed: {e}")
            if app is not None:
                try:
                    app.Quit()
                except Exception as e:
                    self.logger.warning(f"  [FORM-GRID] Excel paste app quit failed: {e}")
            excel_copy_context["book"] = None
            excel_copy_context["app"] = None
            excel_copy_context["sheet_name"] = None
            excel_copy_context["end_row"] = 0
            excel_copy_context["end_col"] = 0

        main_rect_cache = None

        def _main_rect():
            nonlocal main_rect_cache
            # 운영 fast 경로에서 GDI 화면을 2초마다 확인할 때마다
            # main_win.rectangle()을 다시 호출하면 UIA provider가 60~300초씩
            # 멈출 수 있다. 폼 세팅/붙여넣기 클릭에서 한 번 확인한 좌표를
            # 이후 화면 감지와 관리항목 입력 전체에서 즉시 재사용한다.
            if skip_visible_row_scan and main_rect_cache is not None:
                return main_rect_cache
            try:
                main_rect_cache = main_win.rectangle()
                return main_rect_cache
            except Exception as e:
                if main_rect_cache is not None:
                    self.logger.warning(f"  [UIA-FALLBACK] 메인 창 좌표 캐시 사용: {e}")
                    return main_rect_cache
                raise

        def _click_form_xy(x, y, label, wait=None):
            r = _main_rect()
            ax, ay = r.left + x, r.top + y
            pyautogui.click(ax, ay)
            self.logger.info(f"  [FORM-XY] {label} 클릭: rel=({x},{y}), abs=({ax},{ay})")
            time.sleep(ERP_FORM_WAIT if wait is None else wait)

        def _release_modifiers(label="", wait=True):
            for key in ("ctrl", "shift", "alt", "win"):
                try:
                    pyautogui.keyUp(key)
                except:
                    pass
            if wait:
                time.sleep(quick_wait)
            if label and verbose_keysafe:
                self.logger.info(f"  [KEYSAFE] {label}: Ctrl/Shift/Alt/Win 강제 해제")

        def _paste_form_xy(x, y, text, label, clear=True, enter=False, tab=False):
            _click_form_xy(x, y, label)
            if clear:
                pyautogui.hotkey('ctrl', 'a')
                _release_modifiers(f"{label} Ctrl+A 후")
                time.sleep(0.03)
                pyautogui.press('backspace')
                time.sleep(0.03)
            _safe_paste(text)
            if enter:
                pyautogui.press('enter')
            if tab:
                pyautogui.press('tab')
            self.logger.info(f"  [FORM-XY] {label} 입력 완료: {text}")

        def _type_form_xy(x, y, text, label, clear=True, enter=False, tab=False):
            _click_form_xy(x, y, label)
            if clear:
                pyautogui.hotkey('ctrl', 'a')
                _release_modifiers(f"{label} Ctrl+A 후")
                time.sleep(0.03)
                pyautogui.press('backspace')
                time.sleep(0.03)
            pyautogui.write(str(text), interval=0.015)
            if enter:
                pyautogui.press('enter')
            if tab:
                pyautogui.press('tab')
            self.logger.info(f"  [FORM-XY] {label} 타이핑 완료: {text}")

        def _site_code(value):
            text = str(value or "")
            if "일강1" in text:
                # 한글 타이핑 불안정 방지: Like/자동완성 기준으로 숫자만 입력 후 Enter.
                return "1"
            if "일강2" in text:
                return "2"
            m = re.search(r'(P\d|D\d)', text, re.IGNORECASE)
            if m:
                return m.group(1).upper()
            return text

        def _acc_unit_display(value):
            text = str(value or "")
            if "일강1" in text:
                return "일강 1공장"
            if "일강2" in text:
                return "일강 2공장"
            return text

        def _norm_text(value):
            return re.sub(r"\s+", "", str(value or "")).strip()

        def _control_text(ctrl):
            values = []
            seen = set()
            for getter in (
                lambda: ctrl.get_value(),
                lambda: ctrl.window_text(),
                lambda: ctrl.iface_value.CurrentValue,
                lambda: " ".join(ctrl.texts()),
            ):
                try:
                    value = getter()
                    if value:
                        text = str(value).strip()
                        key = _norm_text(text)
                        if key and key not in seen:
                            values.append(text)
                            seen.add(key)
                except:
                    pass
            return " ".join(values).strip()

        def _iter_visible(control_type=None):
            try:
                controls = main_win.descendants(control_type=control_type) if control_type else main_win.descendants()
            except:
                return []
            visible = []
            for ctrl in controls:
                try:
                    if ctrl.is_visible() and ctrl.is_enabled():
                        visible.append(ctrl)
                except:
                    pass
            return visible

        def _find_near_control(x, y, control_types):
            r = main_win.rectangle()
            tx, ty = r.left + x, r.top + y
            best = None
            best_score = 10 ** 12
            for ct in control_types:
                for ctrl in _iter_visible(ct):
                    try:
                        cr = ctrl.rectangle()
                        if cr.left <= tx <= cr.right and cr.top <= ty <= cr.bottom:
                            return ctrl
                        cx = (cr.left + cr.right) // 2
                        cy = (cr.top + cr.bottom) // 2
                        score = abs(cx - tx) + abs(cy - ty)
                        if score < best_score:
                            best = ctrl
                            best_score = score
                    except:
                        pass
            return best

        def _find_acc_unit_combo():
            r = main_win.rectangle()
            best = None
            best_score = 10 ** 12
            for ctrl in _iter_visible("ComboBox"):
                try:
                    cr = ctrl.rectangle()
                    aid = str(ctrl.element_info.automation_id or "")
                    text = _control_text(ctrl)
                    score = abs(((cr.left + cr.right) // 2) - (r.left + 493)) + abs(((cr.top + cr.bottom) // 2) - (r.top + 124))
                    if aid == "cboAccUnit":
                        score -= 10000
                    if "공장" in text or "일강" in text or "제이엠" in text or "더원" in text:
                        score -= 500
                    if score < best_score:
                        best = ctrl
                        best_score = score
                except:
                    pass
            return best

        def _visible_acc_unit_items():
            order_set = {"P1공장", "P2공장", "P3공장", "P4공장", "D1공장", "D2공장", "D3공장", "일강 1공장", "일강 2공장", "제이엠", "더원"}
            found = []
            try:
                for w in Desktop(backend="uia").windows():
                    try:
                        for li in w.descendants(control_type="ListItem"):
                            try:
                                if not li.is_visible():
                                    continue
                            except:
                                pass
                            text = str(li.window_text() or "").strip()
                            if text in order_set:
                                found.append(li)
                    except:
                        pass
            except:
                pass
            return found

        def _dump_form_diagnostics(reason):
            try:
                debug_dir = Path(r"C:\ERP_DB\debug")
                debug_dir.mkdir(parents=True, exist_ok=True)
                job_id = str(getattr(self.manager.main_app, "erp_job_id", "job") or "job")
                invoice_id = str(getattr(self.manager.main_app, "erp_invoice_id", "invoice") or "invoice")
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                png_path = debug_dir / f"erp_form_fail_{job_id}_{invoice_id}_{stamp}.png"
                screenshot_saved = False
                try:
                    pyautogui.screenshot(str(png_path))
                    screenshot_saved = True
                    self.logger.warning(f"  [DIAGNOSTIC] failure screenshot saved: {png_path}")
                except Exception as e:
                    self.logger.warning(f"  [DIAGNOSTIC] failure screenshot save failed: {e}")
                dump_path = os.path.join(BASE_EXE_DIR, "erp_ui_dump.txt")
                lines = [
                    f"reason={reason}",
                    f"title={main_win.window_text()}",
                    f"time={stamp}",
                    "",
                ]
                for ct in ("ComboBox", "Edit", "Button", "Text"):
                    lines.append(f"[{ct}]")
                    for ctrl in _iter_visible(ct):
                        try:
                            cr = ctrl.rectangle()
                            aid = str(ctrl.element_info.automation_id or "")
                            name = str(ctrl.window_text() or "")
                            value = _control_text(ctrl)
                            lines.append(f"aid={aid} name={name} value={value} rect=({cr.left},{cr.top})-({cr.right},{cr.bottom})")
                        except Exception as e:
                            lines.append(f"<dump error: {e}>")
                    lines.append("")
                with open(dump_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                self.logger.warning(f"  [진단] UI 덤프 저장됨 → {dump_path}")
                try:
                    if screenshot_saved:
                        return
                    pyautogui.screenshot(str(png_path))
                    self.logger.warning(f"  [진단] 실패 스크린샷 저장됨 → {png_path}")
                except Exception as e:
                    self.logger.warning(f"  [진단] 실패 스크린샷 저장 실패: {e}")
            except Exception as e:
                self.logger.warning(f"  [진단] UI 덤프 저장 실패: {e}")

        def _fail_form(message):
            _dump_form_diagnostics(message)
            raise RuntimeError(message)

        def _verify_acc_unit(expected):
            expected_norm = _norm_text(expected)
            checks = []
            combo = _find_acc_unit_combo()
            if combo:
                checks.append(_control_text(combo))
            near = _find_near_control(237, 124, ("ComboBox", "Edit", "Text"))
            if near:
                checks.append(_control_text(near))
            for actual in checks:
                if expected_norm and expected_norm in _norm_text(actual):
                    self.logger.info(f"  [FORM-VERIFY] 회계단위 선택 검증 완료: {expected}")
                    return True
            _fail_form(f"회계단위 선택 검증 실패: expected={expected}, actual={checks}")

        def _verify_field_xy(x, y, expected, label, date_mode=False):
            ctrl = _find_near_control(x, y, ("Edit", "ComboBox", "Text"))
            actual = _control_text(ctrl) if ctrl else ""
            if date_mode:
                expected_digits = re.sub(r"[^0-9]", "", str(expected or ""))
                actual_digits = re.sub(r"[^0-9]", "", actual)
                ok = bool(expected_digits) and expected_digits in actual_digits
            else:
                ok = _norm_text(expected) and _norm_text(expected) in _norm_text(actual)
            if ok:
                self.logger.info(f"  [FORM-VERIFY] {label} 검증 완료: {expected}")
                return True
            _fail_form(f"{label} 검증 실패: expected={expected}, actual={actual}")

        def _label_candidates(label):
            needle = _norm_text(label)
            items = []
            for ctrl in _iter_visible():
                try:
                    text = _control_text(ctrl) or ctrl.window_text()
                    if _norm_text(text) == needle:
                        items.append(ctrl)
                except:
                    pass
            return items

        def _input_right_of_label(label, control_types=("Edit", "ComboBox", "Pane")):
            labels = _label_candidates(label)
            best = None
            best_score = 10 ** 12
            for lab in labels:
                try:
                    lr = lab.rectangle()
                    lcy = (lr.top + lr.bottom) // 2
                except:
                    continue
                for ct in control_types:
                    for ctrl in _iter_visible(ct):
                        try:
                            target = ctrl
                            if ct == "Pane":
                                edits = ctrl.descendants(control_type="Edit")
                                if not edits:
                                    continue
                                target = edits[0]
                            cr = target.rectangle()
                            ccy = (cr.top + cr.bottom) // 2
                            if cr.left < lr.right - 4:
                                continue
                            if abs(ccy - lcy) > 28:
                                continue
                            gap = cr.left - lr.right
                            if gap > 420:
                                continue
                            score = gap + abs(ccy - lcy) * 5
                            if score < best_score:
                                best = target
                                best_score = score
                        except:
                            pass
            return best

        def _click_control(ctrl, label):
            r = ctrl.rectangle()
            pyautogui.click((r.left + r.right) // 2, (r.top + r.bottom) // 2)
            rel_x = ((r.left + r.right) // 2) - main_win.rectangle().left
            rel_y = ((r.top + r.bottom) // 2) - main_win.rectangle().top
            self.logger.info(f"  [FORM-ANCHOR] {label} 입력칸 클릭: rel=({rel_x},{rel_y}), rect=({r.left},{r.top})-({r.right},{r.bottom})")
            time.sleep(ERP_FORM_WAIT)

        def _type_anchor_field(label, text, fallback_xy, clear=True, enter=False, tab=False, date_mode=False):
            ctrl = _input_right_of_label(label)
            if ctrl:
                _click_control(ctrl, label)
            else:
                self.logger.warning(f"  [FORM-ANCHOR] {label} 입력칸 미발견, 좌표 fallback 사용: {fallback_xy}")
                _click_form_xy(*fallback_xy, label)
            if clear:
                pyautogui.hotkey('ctrl', 'a')
                _release_modifiers(f"{label} Ctrl+A 후")
                time.sleep(0.03)
                pyautogui.press('backspace')
                time.sleep(0.03)
            _safe_paste(str(text or ""))
            if enter:
                pyautogui.press('enter')
            if tab:
                pyautogui.press('tab')
            self.logger.info(f"  [FORM-ANCHOR] {label} 입력 완료: {text}")
            _verify_anchor_field(label, text, fallback_xy, date_mode=date_mode)

        def _verify_anchor_field(label, expected, fallback_xy, date_mode=False):
            ctrl = _input_right_of_label(label) or _find_near_control(*fallback_xy, ("Edit", "ComboBox", "Text"))
            actual = _control_text(ctrl) if ctrl else ""
            if date_mode:
                expected_digits = re.sub(r"[^0-9]", "", str(expected or ""))
                actual_digits = re.sub(r"[^0-9]", "", actual)
                ok = bool(expected_digits) and expected_digits in actual_digits
            else:
                ok = _norm_text(expected) and _norm_text(expected) in _norm_text(actual)
            if ok:
                self.logger.info(f"  [FORM-VERIFY] {label} 검증 완료: {expected}")
                return True
            _fail_form(f"{label} 검증 실패: expected={expected}, actual={actual}")

        def _verify_anchor_field_retry(label, expected, fallback_xy, date_mode=False, attempts=1):
            last_error = None
            for attempt in range(max(1, attempts)):
                try:
                    return _verify_anchor_field(label, expected, fallback_xy, date_mode=date_mode)
                except Exception as e:
                    last_error = e
                    if attempt >= attempts - 1:
                        break
                    self.logger.warning(f"  [FORM-VERIFY] {label} 검증 재시도 대기 ({attempt + 1}/{attempts}): {e}")
                    time.sleep(critical_field_wait)
            raise last_error

        def _verify_field_xy_retry(x, y, expected, label, date_mode=False, attempts=1):
            last_error = None
            for attempt in range(max(1, attempts)):
                try:
                    return _verify_field_xy(x, y, expected, label, date_mode=date_mode)
                except Exception as e:
                    last_error = e
                    if attempt >= attempts - 1:
                        break
                    self.logger.warning(f"  [FORM-VERIFY] {label} 좌표 검증 재시도 대기 ({attempt + 1}/{attempts}): {e}")
                    time.sleep(critical_field_wait)
            raise last_error

        def _type_anchor_field(label, text, fallback_xy, clear=True, enter=False, tab=False, date_mode=False):
            is_critical = label in ("전표관리단위", "회계일")
            if is_critical:
                self.logger.info(f"  [FORM-STEP] {label} 입력 시작: {text}")
            used_anchor = False
            coord_first = str(os.getenv("ERP_FORM_COORD_FIRST", "1")).strip().lower() not in ("0", "false", "no", "off")
            if coord_first:
                _click_form_xy(*fallback_xy, label)
            else:
                ctrl = _input_right_of_label(label)
                if ctrl:
                    _click_control(ctrl, label)
                    used_anchor = True
                else:
                    self.logger.warning(f"  [FORM-ANCHOR] {label} input not found; coordinate fallback: {fallback_xy}")
                    _click_form_xy(*fallback_xy, label)
            if clear:
                pyautogui.hotkey('ctrl', 'a')
                _release_modifiers(f"{label} Ctrl+A after anchor click")
                time.sleep(quick_wait)
                pyautogui.press('backspace')
                time.sleep(quick_wait)
            _safe_paste(str(text or ""))
            if enter:
                pyautogui.press('enter')
                if is_critical:
                    time.sleep(critical_field_wait)
            if tab:
                pyautogui.press('tab')
                if is_critical:
                    time.sleep(critical_field_wait)
            if is_critical and form_step_wait:
                time.sleep(form_step_wait)
            if used_anchor:
                self.logger.info(f"  [FORM-ANCHOR] {label} input complete: {text}")
                if is_critical and fast_field_verify:
                    self.logger.info(f"  [FORM-VERIFY] {label} fast verify skipped after stable wait: {text}")
                else:
                    _verify_anchor_field_retry(
                        label,
                        text,
                        fallback_xy,
                        date_mode=date_mode,
                        attempts=3 if (strict_form_steps and is_critical) else 1,
                    )
            else:
                self.logger.info(f"  [FORM-FAST] {label} input complete: {text}")
                if fast_field_verify:
                    self.logger.info(f"  [FORM-VERIFY] {label} fast verify skipped: {text}")
                else:
                    _verify_field_xy_retry(
                        *fallback_xy,
                        text,
                        label,
                        date_mode=date_mode,
                        attempts=3 if (strict_form_steps and is_critical) else 1,
                    )
            if is_critical:
                self.logger.info(f"  [FORM-STEP] {label} 입력 완료: {text}")

        def _click_grid_first_account_cell(fallback_xy):
            header = None
            for ctrl in _label_candidates("계정과목"):
                try:
                    r = ctrl.rectangle()
                    if r.top > main_win.rectangle().top + 180:
                        header = ctrl
                        break
                except:
                    pass
            if header:
                r = header.rectangle()
                x = (r.left + r.right) // 2
                y = r.bottom + 18
                pyautogui.click(x, y)
                self.logger.info(
                    f"  [FORM-ANCHOR] 그리드 첫 계정과목 셀 클릭: "
                    f"rel=({x - main_win.rectangle().left},{y - main_win.rectangle().top}), "
                    f"header=({r.left},{r.top})-({r.right},{r.bottom})"
                )
                time.sleep(ERP_FORM_WAIT)
                return

            for c in _iter_visible("Custom"):
                try:
                    if (c.element_info.automation_id or "") == "SS_Row":
                        r = c.rectangle()
                        pyautogui.click(r.left + 150, r.top + 45)
                        self.logger.info("  [FORM-ANCHOR] SS_Row 기준 그리드 첫 계정과목 셀 클릭")
                        time.sleep(ERP_FORM_WAIT)
                        return
                except:
                    pass
            self.logger.warning(f"  [FORM-ANCHOR] 계정과목 헤더 미발견, 좌표 fallback 사용: {fallback_xy}")
            _click_form_xy(*fallback_xy, "그리드 첫 계정과목 셀")

        def _click_grid_first_account_cell(fallback_xy):
            # WEB Fix24: click the intersection of the real account header and the
            # first data row. The previous loose fallback could drift into the
            # right-side "부가세행추가" button area.
            grid_coord_first = str(os.getenv("ERP_GRID_COORD_FIRST", "1")).strip().lower() not in ("0", "false", "no", "off")
            if grid_coord_first:
                self.logger.info(f"  [FORM-GRID] account cell coordinate-first: {fallback_xy}")
                _click_form_xy(*fallback_xy, "grid first account cell")
                return

            main_rect = main_win.rectangle()

            def _text(ctrl):
                try:
                    return str(ctrl.window_text() or "").strip()
                except:
                    return ""

            def _rel(rect):
                return (
                    rect.left - main_rect.left,
                    rect.top - main_rect.top,
                    rect.right - main_rect.left,
                    rect.bottom - main_rect.top,
                )

            headers = []
            for ctrl_type in ("Header", "Text", "Custom"):
                for ctrl in _iter_visible(ctrl_type):
                    try:
                        text = _norm_text(_text(ctrl))
                        if text != _norm_text("계정과목"):
                            continue
                        rect = ctrl.rectangle()
                        rel_left, rel_top, _, _ = _rel(rect)
                        width = rect.right - rect.left
                        height = rect.bottom - rect.top
                        if not (50 <= rel_left <= 420 and 120 <= rel_top <= 340):
                            continue
                        if not (20 <= width <= 260 and 10 <= height <= 70):
                            continue
                        headers.append((abs(rel_top - 205), rel_left, ctrl, rect))
                    except:
                        pass

            if headers:
                _, _, _, header_rect = sorted(headers, key=lambda item: (item[0], item[1]))[0]
                row_markers = []
                for ctrl_type in ("Text", "Custom"):
                    for ctrl in _iter_visible(ctrl_type):
                        try:
                            if _norm_text(_text(ctrl)) != "001":
                                continue
                            rect = ctrl.rectangle()
                            rel_left, _, _, _ = _rel(rect)
                            if not (0 <= rel_left <= 140):
                                continue
                            if not (header_rect.top - 10 <= rect.top <= header_rect.bottom + 70):
                                continue
                            marker_y = (rect.top + rect.bottom) // 2
                            row_markers.append((abs(marker_y - (header_rect.bottom + 14)), rect))
                        except:
                            pass
                if row_markers:
                    row_rect = sorted(row_markers, key=lambda item: item[0])[0][1]
                    y = (row_rect.top + row_rect.bottom) // 2
                else:
                    y = header_rect.bottom + 16
                x = (header_rect.left + header_rect.right) // 2
                pyautogui.click(x, y)
                self.logger.info(
                    f"  [FORM-GRID] account cell click verified by header/row: "
                    f"rel=({x - main_rect.left},{y - main_rect.top}), "
                    f"header=({header_rect.left},{header_rect.top})-({header_rect.right},{header_rect.bottom})"
                )
                time.sleep(ERP_FORM_WAIT)
                return

            for ctrl in _iter_visible("Custom"):
                try:
                    if (ctrl.element_info.automation_id or "") != "SS_Row":
                        continue
                    rect = ctrl.rectangle()
                    rel_left, rel_top, _, _ = _rel(rect)
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top
                    if rel_left > 120 or rel_top > 360 or width < 700 or height < 80:
                        continue
                    x = rect.left + min(190, max(120, width // 8))
                    y = rect.top + 38
                    pyautogui.click(x, y)
                    self.logger.info(
                        f"  [FORM-GRID] account cell click by constrained SS_Row: "
                        f"rel=({x - main_rect.left},{y - main_rect.top})"
                    )
                    time.sleep(ERP_FORM_WAIT)
                    return
                except:
                    pass

            safe_xy = fallback_xy
            self.logger.warning(
                f"  [FORM-GRID] account header not found; using safe grid fallback {safe_xy} "
                "instead of scanned coordinates"
            )
            _click_form_xy(*safe_xy, "grid first account cell")

        def _click_add_row(add_clicks, fallback_xy):
            if add_clicks <= 0:
                return
            if _env_flag("ERP_ADD_ROW_COORD_FIRST", "1"):
                r = main_win.rectangle()
                ax, ay = r.left + fallback_xy[0], r.top + fallback_xy[1]
                for _ in range(add_clicks):
                    pyautogui.click(ax, ay)
                    time.sleep(ERP_CLICK_WAIT)
                self.logger.info(f"  [FORM-FAST] 행추가 좌표 {add_clicks}회 완료: rel={fallback_xy}")
                return
            btn = None
            candidates = []

            def _add_row_candidate(ctrl):
                try:
                    text = _norm_text(_control_text(ctrl) or ctrl.window_text())
                    aid = str(ctrl.element_info.automation_id or "")
                    if "부가세" in text:
                        return None
                    if text != "행추가" and aid != "btnAddRow":
                        return None
                    rect = ctrl.rectangle()
                    main_rect = main_win.rectangle()
                    rel_x = (rect.left + rect.right) // 2 - main_rect.left
                    rel_y = (rect.top + rect.bottom) // 2 - main_rect.top
                    score = 0
                    if text == "행추가":
                        score -= 1000
                    if rel_x > (main_rect.right - main_rect.left) * 0.70:
                        score -= 100
                    score += abs(rel_y - 385)
                    return (score, ctrl, text or aid, rel_x, rel_y)
                except:
                    return None

            for b in _iter_visible("Button"):
                item = _add_row_candidate(b)
                if item:
                    candidates.append(item)
            for c in _iter_visible("Custom"):
                item = _add_row_candidate(c)
                if item:
                    candidates.append(item)
            if candidates:
                candidates.sort(key=lambda row: row[0])
                _, btn, caption, rel_x, rel_y = candidates[0]
                self.logger.info(f"  [FORM-ANCHOR] 행추가 버튼 선택: text={caption}, rel=({rel_x},{rel_y})")
            if btn:
                r = btn.rectangle()
                for _ in range(add_clicks):
                    pyautogui.click((r.left + r.right) // 2, (r.top + r.bottom) // 2)
                    time.sleep(ERP_CLICK_WAIT)
                self.logger.info(f"  [FORM-ANCHOR] 행추가 {add_clicks}회 완료")
                return
            self.logger.warning(f"  [FORM-ANCHOR] 행추가 버튼 미발견, 좌표 fallback 사용: {fallback_xy}")
            for _ in range(add_clicks):
                _click_form_xy(*fallback_xy, "행추가")
                time.sleep(ERP_CLICK_WAIT)

        def _expected_first_grid_account():
            for line in str(original_clipboard or "").splitlines():
                cols = line.split("\t")
                if cols and cols[0].strip():
                    return cols[0].strip()
            return ""

        grid_paste_state = {"verified": False}

        def _verify_grid_paste_or_fail(first_account_cell_xy):
            if not _env_flag("ERP_VERIFY_GRID_PASTE", "0"):
                self.logger.info("  [FORM-VERIFY] 그리드 붙여넣기 검증 스킵")
                return
            expected = _expected_first_grid_account()
            if not expected:
                if _env_flag("ERP_ALLOW_UNVERIFIED_GRID_SAVE", "1"):
                    self.logger.warning("  [FORM-VERIFY] 그리드 붙여넣기 데이터가 비어 있지만 저장/전표출력을 계속 진행합니다.")
                    return
                _fail_form("그리드 붙여넣기 데이터가 비어 있어 저장을 중단합니다.")
            sentinel = f"__ERP_GRID_VERIFY_{int(time.time() * 1000)}__"
            copied = ""
            try:
                pyperclip.copy(sentinel)
                time.sleep(0.03)
                _click_grid_first_account_cell(first_account_cell_xy)
                pyautogui.hotkey("ctrl", "c")
                time.sleep(max(0.08, ERP_FORM_WAIT))
                copied = str(pyperclip.paste() or "")
            finally:
                try:
                    pyperclip.copy(original_clipboard)
                except:
                    pass
            copied_norm = _norm_text(copied)
            expected_norm = _norm_text(expected)
            if copied == sentinel or not copied_norm or expected_norm not in copied_norm:
                if _env_flag("ERP_ALLOW_UNVERIFIED_GRID_SAVE", "1"):
                    self.logger.warning(
                        "  [FORM-VERIFY] 그리드 붙여넣기 검증 실패 상태지만 저장/전표출력을 계속 진행합니다. "
                        f"expected_account={expected}, copied={copied[:120]}"
                    )
                    return
                _fail_form(
                    "그리드 붙여넣기 검증 실패: "
                    f"expected_account={expected}, copied={copied[:120]}"
                )
            grid_paste_state["verified"] = True
            self.logger.info(f"  [FORM-VERIFY] 그리드 붙여넣기 검증 완료: {expected}")

        def _grid_first_cell_matches_expected(first_account_cell_xy, context="grid paste"):
            expected = _expected_first_grid_account()
            if not expected:
                self.logger.warning("  [FORM-VERIFY] grid first-cell check skipped: expected account is empty")
                return False
            sentinel = f"__ERP_GRID_VERIFY_{int(time.time() * 1000)}__"
            copied = ""
            try:
                pyperclip.copy(sentinel)
                time.sleep(0.05)
                _click_grid_first_account_cell(first_account_cell_xy)
                pyautogui.hotkey("ctrl", "c")
                _release_modifiers(f"{context} Ctrl+C", wait=False)
                time.sleep(max(0.15, ERP_FORM_WAIT))
                copied = str(pyperclip.paste() or "")
            finally:
                try:
                    pyperclip.copy(original_clipboard)
                except:
                    pass
            copied_norm = _norm_text(copied)
            expected_norm = _norm_text(expected)
            matched = copied != sentinel and expected_norm and expected_norm in copied_norm
            if matched:
                grid_paste_state["verified"] = True
                self.logger.info(
                    f"  [FORM-VERIFY] grid paste reflected in first cell: context={context}, expected={expected}"
                )
            else:
                self.logger.warning(
                    f"  [FORM-VERIFY] grid paste not reflected yet: context={context}, "
                    f"expected={expected}, copied={copied[:120]}"
                )
            return matched

        management_grid_ready_state = {"snapshot": None}

        def _management_grid_visual_boundary(first_value_abs, fallback_abs):
            """Find the live voucher-grid bottom from the two painted separator lines."""
            try:
                main_rect = _main_rect()
                row_height = max(
                    10,
                    int(os.getenv("ERP_MGMT_ROW_HEIGHT", "20") or "20"),
                )
                scan_step = max(
                    2,
                    int(os.getenv("ERP_MGMT_VISUAL_SCAN_STEP", "4") or "4"),
                )
                scan_left = main_rect.left + 60
                scan_right = min(main_rect.right - 180, main_rect.left + 1500)
                scan_top = max(
                    main_rect.top + 250,
                    int(first_value_abs) - max(100, row_height * 7),
                )
                scan_bottom = min(
                    main_rect.bottom - 90,
                    int(first_value_abs) - max(16, row_height),
                )
                if scan_right <= scan_left or scan_bottom - scan_top < 20:
                    return int(fallback_abs), None
                image = pyautogui.screenshot(
                    region=(
                        scan_left,
                        scan_top,
                        scan_right - scan_left,
                        scan_bottom - scan_top,
                    )
                )
                width, height = image.size
                sample_count = max(1, len(range(0, width, scan_step)))
                minimum_line_pixels = max(
                    20,
                    int(round(sample_count * 0.30)),
                )
                painted_rows = []
                for y in range(height):
                    line_pixels = 0
                    for x in range(0, width, scan_step):
                        r, g, b = image.getpixel((x, y))[:3]
                        neutral = abs(r - g) < 10 and abs(g - b) < 10
                        if neutral and (r < 100 or 125 <= r <= 225):
                            line_pixels += 1
                    if line_pixels >= minimum_line_pixels:
                        painted_rows.append((scan_top + y, line_pixels))
                clusters = []
                for abs_y, line_pixels in painted_rows:
                    if not clusters or abs_y > clusters[-1][-1][0] + 2:
                        clusters.append([(abs_y, line_pixels)])
                    else:
                        clusters[-1].append((abs_y, line_pixels))
                line_candidates = []
                for cluster in clusters:
                    strongest_y, strongest_score = max(
                        cluster,
                        key=lambda item: item[1],
                    )
                    line_candidates.append((int(strongest_y), int(strongest_score)))
                pair_gap_max = max(12, int(round(row_height * 0.80)))
                separator_groups = []
                current_group = []
                for upper, lower in zip(line_candidates, line_candidates[1:]):
                    gap = int(lower[0]) - int(upper[0])
                    if 4 <= gap <= pair_gap_max:
                        if not current_group:
                            current_group = [upper]
                        current_group.append(lower)
                    elif current_group:
                        separator_groups.append(current_group)
                        current_group = []
                if current_group:
                    separator_groups.append(current_group)
                valid_groups = [
                    group
                    for group in separator_groups
                    if row_height
                    <= int(first_value_abs) - int(group[-1][0])
                    <= row_height * 4
                ]
                if not valid_groups:
                    return int(fallback_abs), {
                        "source": "offset-fallback",
                        "lines": [item[0] for item in line_candidates[-8:]],
                    }
                selected_group = max(valid_groups, key=lambda group: int(group[-1][0]))
                expected_offset = max(
                    row_height * 2,
                    int(round(
                        row_height
                        * float(
                            os.getenv(
                                "ERP_MGMT_VISUAL_BOUNDARY_OFFSET_ROWS",
                                "2.4",
                            )
                            or "2.4"
                        )
                    )),
                )
                boundary_abs = int(
                    min(
                        selected_group,
                        key=lambda line: (
                            abs(
                                (int(first_value_abs) - int(line[0]))
                                - expected_offset
                            ),
                            -int(line[0]),
                        ),
                    )[0]
                )
                return int(boundary_abs), {
                    "source": "painted-separator",
                    "expected_offset": int(expected_offset),
                    "gaps": [
                        int(next_line[0]) - int(line[0])
                        for line, next_line in zip(selected_group, selected_group[1:])
                    ],
                    "lines": [item[0] for item in line_candidates[-8:]],
                }
            except Exception as exc:
                self.logger.debug(
                    f"  [FORM-VERIFY] voucher painted boundary scan failed: {exc}"
                )
                return int(fallback_abs), None

        def _management_grid_visual_snapshot():
            """Detect the painted GDI management grid without enumerating UIA descendants."""
            main_rect = _main_rect()
            visual_ready = False
            visual_score = 0
            visual_signature = None
            visual_band_top = None
            visual_counts = {"red": 0, "dark": 0, "gray": 0, "red_rows": 0}
            band_diagnostics = []
            value_x = int(os.getenv("ERP_MGMT_VALUE_X", "1118") or "1118")
            first_value_y = None
            voucher_clip_bottom_abs = None
            try:
                scan_left = main_rect.left + 650
                scan_right = min(main_rect.right - 40, main_rect.left + 1220)
                label_left = main_rect.left + int(
                    os.getenv("ERP_MGMT_LABEL_X_MIN", "600") or "600"
                )
                label_right = main_rect.left + int(
                    os.getenv("ERP_MGMT_LABEL_X_MAX", "900") or "900"
                )
                max_top = max(331, min(main_rect.bottom - main_rect.top - 110, 900))
                step = max(2, int(os.getenv("ERP_MGMT_VISUAL_SCAN_STEP", "4") or "4"))
                row_height = max(10, int(os.getenv("ERP_MGMT_ROW_HEIGHT", "20") or "20"))
                value_to_grid_bottom = max(
                    row_height,
                    int(os.getenv("ERP_MGMT_VISUAL_VALUE_TO_GRID_BOTTOM", "44") or "44"),
                )
                # The horizontal splitter height is persisted by the ERP user
                # account.  A management row can therefore straddle any boundary
                # of the normal 120px bands after a person resized the panes and
                # closed ERP.  Keep the common bands first for normal speed, then
                # inspect overlapping bands only when none of them contained a
                # complete management row.
                for top_rel in (360, 480, 600, 720, 820, 420, 540, 660, 780):
                    if top_rel >= max_top:
                        continue
                    top = main_rect.top + top_rel
                    bottom = min(main_rect.bottom - 90, top + 120)
                    if scan_right <= scan_left or bottom <= top:
                        continue
                    image = pyautogui.screenshot(
                        region=(scan_left, top, scan_right - scan_left, bottom - top)
                    )
                    width, height = image.size
                    red_pixels = 0
                    dark_pixels = 0
                    gray_lines = 0
                    red_sample_ys = []
                    label_ink_rows = []
                    for y in range(0, height, step):
                        red_on_row = 0
                        label_ink_on_row = 0
                        for x in range(0, width, step):
                            r, g, b = image.getpixel((x, y))[:3]
                            sample_abs_x = scan_left + x
                            in_label_roi = label_left <= sample_abs_x <= label_right
                            is_label_ink = in_label_roi and (
                                max(r, g, b) < 120
                                or (
                                    max(r, g, b) - min(r, g, b) >= 35
                                    and min(r, g, b) < 135
                                )
                            )
                            if is_label_ink:
                                label_ink_on_row += 1
                            if (
                                in_label_roi
                                and r > 150
                                and g < 95
                                and b < 95
                            ):
                                red_pixels += 1
                                red_on_row += 1
                            elif r < 95 and g < 95 and b < 95:
                                dark_pixels += 1
                            elif abs(r - g) < 8 and abs(g - b) < 8 and 145 <= r <= 215:
                                gray_lines += 1
                        if red_on_row:
                            red_sample_ys.append(y)
                        if label_ink_on_row:
                            label_ink_rows.append(y)
                    red_row_clusters = []
                    for sample_y in red_sample_ys:
                        if (
                            not red_row_clusters
                            or sample_y > red_row_clusters[-1][-1] + (step * 2)
                        ):
                            red_row_clusters.append([sample_y])
                        else:
                            red_row_clusters[-1].append(sample_y)

                    # The ERP paints management labels in either red or black depending
                    # on the active account/required state.  Readiness therefore comes
                    # from the table itself: two painted row boundaries, a continuous
                    # label/value divider and actual ink inside the first value row.
                    sample_count = max(1, len(range(0, width, step)))
                    # Some ERP themes paint the same management separator with a
                    # shorter neutral segment (notably the vendor-only first row).
                    # The three required vertical borders below carry the strong
                    # structural discrimination, so 25% is sufficient here.
                    minimum_line_pixels = max(20, int(round(sample_count * 0.25)))
                    painted_rows = []
                    for y in range(height):
                        line_pixels = 0
                        for x in range(0, width, step):
                            r, g, b = image.getpixel((x, y))[:3]
                            # Required/selected bank rows can tint the horizontal
                            # separator beige or blue.  Exclude white and the very
                            # light-blue cell interior, but do not require neutrality.
                            if max(r, g, b) <= 245 and min(r, g, b) <= 230:
                                line_pixels += 1
                        if line_pixels >= minimum_line_pixels:
                            painted_rows.append((int(y), int(line_pixels)))
                    painted_clusters = []
                    for row_y, line_pixels in painted_rows:
                        if not painted_clusters or row_y > painted_clusters[-1][-1][0] + 2:
                            painted_clusters.append([(row_y, line_pixels)])
                        else:
                            painted_clusters[-1].append((row_y, line_pixels))
                    horizontal_lines = [
                        max(cluster, key=lambda item: item[1])
                        for cluster in painted_clusters
                    ]

                    divider_search_left = max(
                        0,
                        int(main_rect.left + value_x - 360 - scan_left),
                    )
                    divider_search_right = min(
                        width - 1,
                        int(main_rect.left + value_x - 160 - scan_left),
                    )
                    # The management value cell ends only a few pixels to the right
                    # of the configured click anchor.  Requiring that painted right
                    # border prevents an ordinary voucher-grid row (which has the
                    # same horizontal pitch and plenty of text) from being accepted.
                    right_border_search_left = max(
                        0,
                        int(main_rect.left + value_x + 12 - scan_left),
                    )
                    right_border_search_right = min(
                        width - 1,
                        int(main_rect.left + value_x + 60 - scan_left),
                    )
                    structural_candidate = None
                    candidate_checks = []
                    row_gap_min = max(10, int(round(row_height * 0.60)))
                    row_gap_max = max(row_gap_min + 2, int(round(row_height * 1.20)))
                    for upper, lower in zip(horizontal_lines, horizontal_lines[1:]):
                        upper_y = int(upper[0])
                        lower_y = int(lower[0])
                        row_gap = lower_y - upper_y
                        if not (row_gap_min <= row_gap <= row_gap_max):
                            continue
                        ink_start = upper_y + 2
                        ink_end = lower_y - 1
                        if ink_end <= ink_start:
                            continue
                        divider_x = None
                        divider_score = 0
                        divider_minimum = max(6, int(round((row_gap + 1) * 0.72)))
                        for x in range(divider_search_left, divider_search_right + 1):
                            vertical_pixels = 0
                            for y in range(upper_y, lower_y + 1):
                                r, g, b = image.getpixel((x, y))[:3]
                                if max(r, g, b) <= 245 and min(r, g, b) <= 230:
                                    vertical_pixels += 1
                            if vertical_pixels > divider_score:
                                divider_score = int(vertical_pixels)
                                divider_x = int(x)
                        if divider_x is None or divider_score < divider_minimum:
                            candidate_checks.append(
                                {
                                    "upper": upper_y,
                                    "lower": lower_y,
                                    "left_border_score": 0,
                                    "divider_score": int(divider_score),
                                    "right_border_score": 0,
                                    "ink_pixels": 0,
                                    "accepted": False,
                                }
                            )
                            continue

                        left_border_x = None
                        left_border_score = 0
                        left_border_minimum = max(
                            6,
                            int(round((row_gap + 1) * 0.72)),
                        )
                        left_border_search_left = max(0, int(divider_x - 200))
                        left_border_search_right = max(
                            left_border_search_left,
                            int(divider_x - 70),
                        )
                        for x in range(
                            left_border_search_left,
                            left_border_search_right + 1,
                        ):
                            vertical_pixels = 0
                            for y in range(upper_y, lower_y + 1):
                                r, g, b = image.getpixel((x, y))[:3]
                                if max(r, g, b) <= 245 and min(r, g, b) <= 230:
                                    vertical_pixels += 1
                            if vertical_pixels > left_border_score:
                                left_border_score = int(vertical_pixels)
                                left_border_x = int(x)
                        if (
                            left_border_x is None
                            or left_border_score < left_border_minimum
                        ):
                            candidate_checks.append(
                                {
                                    "upper": upper_y,
                                    "lower": lower_y,
                                    "left_border_score": int(left_border_score),
                                    "divider_score": int(divider_score),
                                    "right_border_score": 0,
                                    "ink_pixels": 0,
                                    "accepted": False,
                                }
                            )
                            continue

                        right_border_x = None
                        right_border_score = 0
                        right_border_minimum = max(
                            6,
                            int(round((row_gap + 1) * 0.72)),
                        )
                        for x in range(
                            right_border_search_left,
                            right_border_search_right + 1,
                        ):
                            vertical_pixels = 0
                            for y in range(upper_y, lower_y + 1):
                                r, g, b = image.getpixel((x, y))[:3]
                                if max(r, g, b) <= 245 and min(r, g, b) <= 230:
                                    vertical_pixels += 1
                            if vertical_pixels > right_border_score:
                                right_border_score = int(vertical_pixels)
                                right_border_x = int(x)
                        if (
                            right_border_x is None
                            or right_border_score < right_border_minimum
                            or right_border_x - divider_x < max(80, row_height * 4)
                        ):
                            candidate_checks.append(
                                {
                                    "upper": upper_y,
                                    "lower": lower_y,
                                    "left_border_score": int(left_border_score),
                                    "divider_score": int(divider_score),
                                    "right_border_score": int(right_border_score),
                                    "ink_pixels": 0,
                                    "accepted": False,
                                }
                            )
                            continue

                        # Count ink only inside this candidate's first label cell.
                        # Border pixels and text in the value cell must not satisfy
                        # the readiness gate.
                        ink_left = max(0, int(left_border_x + 3))
                        ink_right = min(width - 1, int(divider_x - 3))
                        ink_rows = set()
                        ink_pixels = 0
                        if ink_right > ink_left:
                            for y in range(ink_start, ink_end + 1, step):
                                for x in range(ink_left, ink_right + 1, step):
                                    r, g, b = image.getpixel((x, y))[:3]
                                    is_ink = max(r, g, b) < 120 or (
                                        max(r, g, b) - min(r, g, b) >= 35
                                        and min(r, g, b) < 135
                                    )
                                    if is_ink:
                                        ink_pixels += 1
                                        ink_rows.add(int(y))
                        accepted = ink_pixels >= 2 and len(ink_rows) >= 1
                        candidate_checks.append(
                            {
                                "upper": upper_y,
                                "lower": lower_y,
                                "left_border_score": int(left_border_score),
                                "divider_score": int(divider_score),
                                "right_border_score": int(right_border_score),
                                "ink_pixels": int(ink_pixels),
                                "accepted": bool(accepted),
                            }
                        )
                        if not accepted:
                            continue
                        structural_candidate = {
                            "upper": upper_y,
                            "lower": lower_y,
                            "left_border_x": left_border_x,
                            "left_border_score": left_border_score,
                            "divider_x": divider_x,
                            "divider_score": divider_score,
                            "right_border_x": right_border_x,
                            "right_border_score": right_border_score,
                            "ink_rows": sorted(ink_rows),
                            "ink_pixels": int(ink_pixels),
                        }
                        break

                    # In some GDI states only one horizontal separator of the
                    # first management row is painted strongly enough to survive
                    # capture.  Infer the row on either side of that line, but keep
                    # the same strict three-border + in-cell-ink requirements.  The
                    # normal adjacent-line path above always has priority.
                    if structural_candidate is None and horizontal_lines:
                        adjacent_intervals = {
                            (int(upper[0]), int(lower[0]))
                            for upper, lower in zip(
                                horizontal_lines,
                                horizontal_lines[1:],
                            )
                            if row_gap_min
                            <= int(lower[0]) - int(upper[0])
                            <= row_gap_max
                        }
                        inferred_intervals = []
                        seen_intervals = set()
                        for line, _line_score in horizontal_lines:
                            line_y = int(line)
                            for interval in (
                                (line_y - row_height, line_y),
                                (line_y, line_y + row_height),
                            ):
                                upper_y, lower_y = interval
                                if (
                                    upper_y < 0
                                    or lower_y >= height
                                    or interval in adjacent_intervals
                                    or interval in seen_intervals
                                ):
                                    continue
                                seen_intervals.add(interval)
                                inferred_intervals.append(interval)

                        def _best_painted_vertical(
                            search_from,
                            search_to,
                            upper_y,
                            lower_y,
                        ):
                            best_x = None
                            best_score = 0
                            for x in range(search_from, search_to + 1):
                                vertical_pixels = 0
                                for y in range(upper_y, lower_y + 1):
                                    r, g, b = image.getpixel((x, y))[:3]
                                    if max(r, g, b) <= 245 and min(r, g, b) <= 230:
                                        vertical_pixels += 1
                                if vertical_pixels > best_score:
                                    best_score = int(vertical_pixels)
                                    best_x = int(x)
                            return best_x, best_score

                        for upper_y, lower_y in inferred_intervals:
                            row_gap = int(lower_y - upper_y)
                            border_minimum = max(
                                6,
                                int(round((row_gap + 1) * 0.72)),
                            )
                            divider_x, divider_score = _best_painted_vertical(
                                divider_search_left,
                                divider_search_right,
                                upper_y,
                                lower_y,
                            )
                            divider_ok = (
                                divider_x is not None
                                and divider_score >= border_minimum
                            )

                            left_border_x = None
                            left_border_score = 0
                            if divider_ok:
                                left_search_from = max(0, int(divider_x - 200))
                                left_search_to = max(
                                    left_search_from,
                                    int(divider_x - 70),
                                )
                                (
                                    left_border_x,
                                    left_border_score,
                                ) = _best_painted_vertical(
                                    left_search_from,
                                    left_search_to,
                                    upper_y,
                                    lower_y,
                                )
                            left_ok = (
                                left_border_x is not None
                                and left_border_score >= border_minimum
                            )

                            right_border_x = None
                            right_border_score = 0
                            if divider_ok and left_ok:
                                (
                                    right_border_x,
                                    right_border_score,
                                ) = _best_painted_vertical(
                                    right_border_search_left,
                                    right_border_search_right,
                                    upper_y,
                                    lower_y,
                                )
                            right_ok = (
                                right_border_x is not None
                                and right_border_score >= border_minimum
                                and right_border_x - divider_x
                                >= max(80, row_height * 4)
                            )

                            ink_rows = set()
                            ink_pixels = 0
                            if divider_ok and left_ok and right_ok:
                                ink_left = max(0, int(left_border_x + 3))
                                ink_right = min(width - 1, int(divider_x - 3))
                                for y in range(upper_y + 2, lower_y, step):
                                    for x in range(ink_left, ink_right + 1, step):
                                        r, g, b = image.getpixel((x, y))[:3]
                                        is_ink = max(r, g, b) < 120 or (
                                            max(r, g, b) - min(r, g, b) >= 35
                                            and min(r, g, b) < 135
                                        )
                                        if is_ink:
                                            ink_pixels += 1
                                            ink_rows.add(int(y))
                            accepted = ink_pixels >= 2 and len(ink_rows) >= 1
                            candidate_checks.append(
                                {
                                    "source": "inferred-single-line",
                                    "upper": int(upper_y),
                                    "lower": int(lower_y),
                                    "left_border_score": int(left_border_score),
                                    "divider_score": int(divider_score),
                                    "right_border_score": int(right_border_score),
                                    "ink_pixels": int(ink_pixels),
                                    "accepted": bool(accepted),
                                }
                            )
                            if not accepted:
                                continue
                            structural_candidate = {
                                "source": "inferred-single-line",
                                "upper": int(upper_y),
                                "lower": int(lower_y),
                                "left_border_x": left_border_x,
                                "left_border_score": left_border_score,
                                "divider_x": divider_x,
                                "divider_score": divider_score,
                                "right_border_x": right_border_x,
                                "right_border_score": right_border_score,
                                "ink_rows": sorted(ink_rows),
                                "ink_pixels": int(ink_pixels),
                            }
                            break

                    score = red_pixels * 3 + dark_pixels + gray_lines
                    if score > visual_score:
                        visual_score = score
                        visual_counts = {
                            "red": red_pixels,
                            "dark": dark_pixels,
                            "gray": gray_lines,
                            "red_rows": len(red_row_clusters),
                        }
                    band_diagnostics.append(
                        {
                            "top": int(top_rel),
                            "red": int(red_pixels),
                            "dark": int(dark_pixels),
                            "gray": int(gray_lines),
                            "ink_rows": len(label_ink_rows),
                            "horizontal_lines": [int(item[0]) for item in horizontal_lines],
                            "candidate_checks": candidate_checks,
                            "structure": structural_candidate,
                        }
                    )
                    if structural_candidate is not None:
                        structure_sample_center = int(round(
                            (
                                int(structural_candidate["upper"])
                                + int(structural_candidate["lower"])
                            )
                            / 2.0
                        ))
                        first_sample_center = int(structure_sample_center)
                        if (
                            structural_candidate.get("source") == "inferred-single-line"
                            and int(structural_candidate["lower"])
                            <= int(round(row_height * 1.5))
                        ):
                            # A lone separator near the top of the 720px scan band
                            # is the management header's lower edge.  The detected
                            # ink belongs to 관리항목/관리항목값, while the first data
                            # row is one pitch below it (observed at y=756, not 736).
                            first_sample_center += row_height
                        first_value_y = top_rel + first_sample_center
                        first_value_abs = main_rect.top + first_value_y
                        boundary_reference_abs = (
                            main_rect.top + top_rel + structure_sample_center
                        )
                        fallback_boundary_abs = (
                            boundary_reference_abs - value_to_grid_bottom
                        )
                        (
                            voucher_clip_bottom_abs,
                            boundary_detail,
                        ) = _management_grid_visual_boundary(
                            boundary_reference_abs,
                            fallback_boundary_abs,
                        )
                        # GDI/원격 화면 배율에 따라 얇은 구분선이 캡처에서 빠질 수
                        # 있다. 관리항목의 붉은 라벨과 표 구조가 이미 검출됐으므로
                        # 이 경우에는 실제 첫 값 행에서 계산한 44px 경계를 사용한다.
                        # 동일 signature 2회 확인은 바깥 ready wait에서 계속 수행된다.
                        if not isinstance(boundary_detail, dict):
                            boundary_detail = {
                                "source": "offset-fallback",
                                "lines": [],
                            }
                        visual_ready = True
                        visual_band_top = top_rel
                        visual_signature = (
                            int(top_rel),
                            int(first_value_y),
                            int(voucher_clip_bottom_abs - main_rect.top),
                            1,
                        )
                        visual_counts = {
                            "red": red_pixels,
                            "dark": dark_pixels,
                            "gray": gray_lines,
                            "red_rows": len(red_row_clusters),
                        }
                        visual_counts["boundary"] = boundary_detail
                        break
            except Exception as e:
                self.logger.debug(f"  [FORM-VERIFY] management visual snapshot failed: {e}")
            return {
                "visual_ready": visual_ready,
                "visual_score": visual_score,
                "visual_signature": visual_signature,
                "visual_band_top": visual_band_top,
                "visual_counts": {**visual_counts, "bands": band_diagnostics},
                "value_x": value_x,
                "first_value_y": first_value_y,
                "voucher_clip_bottom_abs": voucher_clip_bottom_abs,
            }

        def _management_grid_snapshot(include_visual=False):
            main_rect = _main_rect()
            header_label = None
            header_value = None
            cash_processing_checkbox = None
            cash_processing_checkbox_candidates = []
            item_rows = []
            visual_ready = False
            visual_score = 0
            voucher_viewport_candidates = []
            voucher_horizontal_scrollbars = []
            voucher_first_row_y = int(os.getenv("ERP_MGMT_FIRST_ROW_Y", "231") or "231")
            voucher_row_height = max(10, int(os.getenv("ERP_MGMT_ROW_HEIGHT", "20") or "20"))
            item_needles = {
                _norm_text("계좌번호"),
                _norm_text("금융기관지점"),
                _norm_text("거래처"),
                _norm_text("증빙"),
                _norm_text("공급가액"),
                _norm_text("거래일"),
                _norm_text("사업자번호"),
                _norm_text("프로젝트코드"),
            }
            for ctrl in _iter_visible():
                try:
                    rect = ctrl.rectangle()
                    automation_id = str(ctrl.element_info.automation_id or "")
                    control_type = str(ctrl.element_info.control_type or "")
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top
                    rel_top = rect.top - main_rect.top
                    rel_bottom = rect.bottom - main_rect.top
                    if (
                        automation_id == "SS_Row"
                        and rect.left - main_rect.left <= 180
                        and width >= 700
                        and height >= 120
                        and rel_top - voucher_row_height <= voucher_first_row_y <= rel_bottom
                    ):
                        voucher_viewport_candidates.append((height, -width, rect))
                    if (
                        control_type == "ScrollBar"
                        and width >= max(300, height * 5)
                        and rel_top > voucher_first_row_y + (voucher_row_height * 3)
                    ):
                        voucher_horizontal_scrollbars.append(rect)
                    text = (_control_text(ctrl) or ctrl.window_text() or "").strip()
                    norm = _norm_text(text)
                    center_x = (rect.left + rect.right) // 2
                    center_y = (rect.top + rect.bottom) // 2
                    rel_x = center_x - main_rect.left
                    rel_y = center_y - main_rect.top
                    if control_type == "CheckBox" and automation_id == "Check1":
                        if _norm_text("출납처리여부") in norm:
                            cash_processing_checkbox = ctrl
                        elif (
                            180 <= rel_x <= 650
                            and rel_y >= voucher_first_row_y + (voucher_row_height * 4)
                        ):
                            # ERP GDI mode can expose the standard Check1 toggle with
                            # an empty accessible name. Keep its lower-left geometry so
                            # the ready snapshot can still cache the real Toggle control.
                            cash_processing_checkbox_candidates.append(
                                (ctrl, rect, rel_x, rel_y)
                            )
                    if not norm:
                        continue
                    if rel_x < 580 or rel_y < 300:
                        continue
                    row = {
                        "text": text,
                        "norm": norm,
                        "rect": rect,
                        "rel_x": rel_x,
                        "rel_y": rel_y,
                    }
                    if norm == _norm_text("관리항목"):
                        header_label = row
                    elif norm == _norm_text("관리항목값"):
                        header_value = row
                    elif norm in item_needles:
                        item_rows.append(row)
                except:
                    pass
            voucher_viewport_rect = (
                sorted(voucher_viewport_candidates, key=lambda item: (item[0], item[1]))[0][2]
                if voucher_viewport_candidates
                else None
            )
            voucher_clip_bottom_candidates = []
            if voucher_viewport_rect is not None:
                voucher_clip_bottom_candidates.append(int(voucher_viewport_rect.bottom))
                for scrollbar_rect in voucher_horizontal_scrollbars:
                    if (
                        scrollbar_rect.right <= voucher_viewport_rect.left
                        or scrollbar_rect.left >= voucher_viewport_rect.right
                        or scrollbar_rect.top > voucher_viewport_rect.bottom + voucher_row_height
                    ):
                        continue
                    voucher_clip_bottom_candidates.append(int(scrollbar_rect.top))
            voucher_clip_bottom_abs = (
                min(voucher_clip_bottom_candidates)
                if voucher_clip_bottom_candidates
                else None
            )
            if cash_processing_checkbox is None and cash_processing_checkbox_candidates:
                if voucher_clip_bottom_abs is not None:
                    expected_center_y = int(voucher_clip_bottom_abs) + max(
                        18,
                        int(round(voucher_row_height * 1.25)),
                    )
                    nearby_candidates = [
                        candidate
                        for candidate in cash_processing_checkbox_candidates
                        if int(voucher_clip_bottom_abs) - voucher_row_height
                        <= candidate[1].top
                        <= int(voucher_clip_bottom_abs) + (voucher_row_height * 6)
                    ]
                    candidates = nearby_candidates or cash_processing_checkbox_candidates
                    selected_candidate = min(
                        candidates,
                        key=lambda candidate: (
                            abs(((candidate[1].top + candidate[1].bottom) // 2) - expected_center_y),
                            abs(candidate[2] - 400),
                        ),
                    )
                else:
                    selected_candidate = min(
                        cash_processing_checkbox_candidates,
                        key=lambda candidate: (
                            abs(candidate[2] - 400),
                            -candidate[3],
                        ),
                    )
                cash_processing_checkbox = selected_candidate[0]
                self.logger.info(
                    "  [FORM-VERIFY] GDI 무명 Check1을 출납처리여부 체크박스로 캐시: "
                    f"rel=({selected_candidate[2]},{selected_candidate[3]})"
                )
            if not include_visual:
                item_rows.sort(key=lambda row: (row["rel_y"], row["rel_x"]))
                return {
                    "header_label": header_label,
                    "header_value": header_value,
                    "cash_processing_checkbox": cash_processing_checkbox,
                    "items": item_rows,
                    "labels": [row["text"] for row in item_rows],
                    "label_norms": {row["norm"] for row in item_rows},
                    "visual_ready": visual_ready,
                    "visual_score": visual_score,
                    "voucher_viewport_rect": voucher_viewport_rect,
                    "voucher_clip_bottom_abs": voucher_clip_bottom_abs,
                }
            try:
                # UIA가 ERP 하단 관리항목 글자를 못 읽는 경우가 있어 화면 픽셀도 함께 봅니다.
                # 사용자가 splitter를 움직여도 잡히도록 ERP 창 내부 후보 band를 아래로 훑습니다.
                scan_left = main_rect.left + 650
                scan_right = min(main_rect.right - 40, main_rect.left + 1220)
                max_top = max(331, min(main_rect.bottom - main_rect.top - 190, 900))
                for top_rel in (360, 480, 600, 720, 820):
                    if top_rel >= max_top:
                        continue
                    top = main_rect.top + top_rel
                    bottom = min(main_rect.bottom - 90, top + 120)
                    if scan_right <= scan_left or bottom <= top:
                        continue
                    image = pyautogui.screenshot(region=(scan_left, top, scan_right - scan_left, bottom - top))
                    width, height = image.size
                    red_pixels = 0
                    dark_pixels = 0
                    gray_lines = 0
                    step = max(6, int(os.getenv("ERP_MGMT_VISUAL_SCAN_STEP", "10") or "10"))
                    for y in range(0, height, step):
                        for x in range(0, width, step):
                            r, g, b = image.getpixel((x, y))[:3]
                            if r > 150 and g < 95 and b < 95:
                                red_pixels += 1
                            elif r < 95 and g < 95 and b < 95:
                                dark_pixels += 1
                            elif abs(r - g) < 8 and abs(g - b) < 8 and 145 <= r <= 215:
                                gray_lines += 1
                    score = red_pixels * 3 + dark_pixels + gray_lines
                    if score > visual_score:
                        visual_score = score
                    if red_pixels >= 1 and dark_pixels >= 4 and gray_lines >= 8:
                        visual_ready = True
                        break
            except Exception as e:
                self.logger.debug(f"  [FORM-VERIFY] management visual snapshot failed: {e}")
            item_rows.sort(key=lambda row: (row["rel_y"], row["rel_x"]))
            return {
                "header_label": header_label,
                "header_value": header_value,
                "cash_processing_checkbox": cash_processing_checkbox,
                "items": item_rows,
                "labels": [row["text"] for row in item_rows],
                "label_norms": {row["norm"] for row in item_rows},
                "visual_ready": visual_ready,
                "visual_score": visual_score,
                "voucher_viewport_rect": voucher_viewport_rect,
                "voucher_clip_bottom_abs": voucher_clip_bottom_abs,
            }

        def _wait_for_management_grid_ready(context="Excel paste"):
            default_ready_needles = {
                _norm_text("계좌번호"),
                _norm_text("금융기관지점"),
                _norm_text("거래처"),
            }
            expected_ready_needles = set()
            ready_items = (
                form_data.get('erp_line_management_items')
                or form_data.get('line_management_items')
                or []
            )
            if isinstance(ready_items, list):
                for ready_item in ready_items:
                    if not isinstance(ready_item, dict):
                        continue
                    expected_ready_needles = {
                        _norm_text(item_name)
                        for item_name, item_value in ready_item.items()
                        if str(item_name or "").strip()
                        and str(item_value or "").strip()
                    }
                    if expected_ready_needles:
                        break
            ready_needles = expected_ready_needles or default_ready_needles
            seconds_per_row = max(
                1.0,
                float(os.getenv("ERP_GRID_PASTE_READY_SECONDS_PER_ROW", "10") or "10"),
            )
            uncapped_timeout = max(20.0, row_count * seconds_per_row)
            timeout_cap = max(
                20.0,
                float(os.getenv("ERP_GRID_PASTE_READY_MAX_SECONDS", "180") or "180"),
            )
            timeout = min(uncapped_timeout, timeout_cap)
            poll_seconds = max(
                0.5,
                float(os.getenv("ERP_GRID_PASTE_VISUAL_POLL_SECONDS", "2.0") or "2.0"),
            )
            stable_required = max(
                2,
                int(os.getenv("ERP_GRID_PASTE_VISUAL_STABLE_COUNT", "2") or "2"),
            )
            end_at = time.time() + timeout
            started = time.time()
            last_snapshot = None
            last_visual_signature = None
            stable_visual_count = 0
            while True:
                elapsed = time.time() - started
                snapshot_started = time.time()
                snapshot = _management_grid_visual_snapshot()
                snapshot_seconds = time.time() - snapshot_started
                last_snapshot = snapshot
                has_visual_ready = bool(snapshot.get("visual_ready"))
                visual_signature = snapshot.get("visual_signature")
                if has_visual_ready and visual_signature is not None:
                    if visual_signature == last_visual_signature:
                        stable_visual_count += 1
                    else:
                        stable_visual_count = 1
                    last_visual_signature = visual_signature
                else:
                    stable_visual_count = 0
                    last_visual_signature = None
                if stable_visual_count >= stable_required:
                    snapshot.update(
                        {
                            "header_label": None,
                            "header_value": None,
                            "cash_processing_checkbox": None,
                            "items": [],
                            "labels": [],
                            "label_norms": set(),
                            "voucher_viewport_rect": None,
                            "management_ready": True,
                            "ready_source": "gdi-visual-stable",
                            "stable_gdi_ready": True,
                            "semantic_ready": False,
                            "management_value_x": snapshot.get("value_x"),
                            "management_value_y": snapshot.get("first_value_y"),
                        }
                    )
                    snapshot["expected_label_norms"] = set(ready_needles)
                    vendor_key = _norm_text("거래처")
                    value_x = snapshot.get("value_x")
                    first_value_y = snapshot.get("first_value_y")
                    if (
                        vendor_key in ready_needles
                        and value_x is not None
                        and first_value_y is not None
                    ):
                        management_value_xy_cache[vendor_key] = (
                            int(value_x),
                            int(first_value_y),
                        )
                    self.logger.info(
                        "  [FORM-VERIFY] GDI 하단 관리항목 화면 안정 감지: "
                        f"context={context}, rows={row_count}, elapsed={elapsed:.1f}s, "
                        f"stable={stable_visual_count}/{stable_required}, "
                        f"visual_score={snapshot.get('visual_score')}, "
                        f"signature={visual_signature}, counts={snapshot.get('visual_counts')}, "
                        f"value=({value_x},{first_value_y}), expected={sorted(ready_needles)}"
                    )
                    return snapshot
                self.logger.info(
                    "  [FORM-VERIFY] GDI 하단 관리항목 화면 대기 중: "
                    f"context={context}, elapsed={elapsed:.1f}s/{timeout:.1f}s, "
                    f"next_check={poll_seconds:.1f}s, snapshot={snapshot_seconds:.1f}s, "
                    f"stable={stable_visual_count}/{stable_required}, "
                    f"visual_ready={has_visual_ready}, visual_score={snapshot.get('visual_score')}, "
                    f"signature={visual_signature}, counts={snapshot.get('visual_counts')}, "
                    f"expected={sorted(ready_needles)}"
                )
                if time.time() >= end_at:
                    break
                time.sleep(min(poll_seconds, max(0.5, end_at - time.time())))
            _fail_form(
                "하단 관리항목 표시 대기 실패: "
                f"context={context}, timeout={timeout:.1f}s, "
                f"expected={sorted(ready_needles)}, "
                f"last_visual={(last_snapshot or {}).get('visual_signature')}"
            )

        management_value_xy_cache = {}
        management_bank_value_xy_cache = {}
        management_bank_coordinate_fallback_rows = set()
        management_active_row_context = {"row_no": None}
        finance_vendor_entry_state = {"f9_seeded": False}
        vendor_popup_detection_state = {"signature": None}
        bank_account_popup_state = {
            "opened": False,
            "closed": True,
            "source": "",
        }

        def _prepare_fast_bank_management_coordinates():
            """Reuse the already captured first management row without a full UIA walk."""
            snapshot = management_grid_ready_state.get("snapshot") or {}
            semantic_ready = bool(snapshot.get("semantic_ready"))
            stable_gdi_ready = bool(snapshot.get("stable_gdi_ready"))
            if not (semantic_ready or stable_gdi_ready):
                self.logger.warning(
                    "  [MGMT-ANCHOR] 검증된 관리항목 화면 기준이 없어 "
                    "보통예금 빠른 좌표를 만들지 않습니다."
                )
                return False
            pitch = max(10, int(os.getenv("ERP_MGMT_ROW_HEIGHT", "20") or "20"))
            vendor_key = _norm_text("거래처")
            anchor = management_value_xy_cache.get(vendor_key)
            if stable_gdi_ready and not finance_vendor_entry_state.get("f9_seeded"):
                self.logger.warning(
                    "  [MGMT-ANCHOR] 최초 거래처 F9 성공이 확인되지 않아 "
                    "보통예금 빠른 좌표를 만들지 않습니다."
                )
                return False
            if stable_gdi_ready and anchor is None:
                self.logger.warning(
                    "  [MGMT-ANCHOR] GDI 화면은 준비됐지만 첫 행 F9에 사용한 거래처 좌표가 없어 "
                    "보통예금 빠른 좌표를 만들지 않습니다."
                )
                return False
            if anchor is None:
                item_rows = snapshot.get("items") or []
                vendor_row = next(
                    (row for row in item_rows if (row.get("norm") or "") == vendor_key),
                    None,
                )
                if vendor_row is None and item_rows:
                    vendor_row = min(item_rows, key=lambda row: int(row.get("rel_y") or 10 ** 9))
                value_header = snapshot.get("header_value") or {}
                value_x = value_header.get("rel_x")
                value_y = vendor_row.get("rel_y") if vendor_row else None
                if value_y is None and value_header.get("rel_y") is not None:
                    value_y = int(value_header["rel_y"]) + pitch
                if value_x is not None and value_y is not None:
                    anchor = (int(value_x), int(value_y))
            if anchor is None:
                self.logger.warning(
                    "  [MGMT-ANCHOR] 빠른 보통예금 좌표를 만들 관리항목 첫 행 기준이 없습니다."
                )
                return False
            value_x, first_value_y = (int(anchor[0]), int(anchor[1]))
            management_bank_value_xy_cache[_norm_text("계좌번호")] = (
                value_x,
                first_value_y,
            )
            management_bank_value_xy_cache[_norm_text("금융기관지점")] = (
                value_x,
                first_value_y + pitch,
            )
            self.logger.info(
                "  [MGMT-ANCHOR] 보통예금 관리항목 좌표를 기존 첫 행 기준으로 준비: "
                f"account=({value_x},{first_value_y}), bank=({value_x},{first_value_y + pitch})"
            )
            return True

        def _management_value_xy(item_name, fallback_y):
            target = _norm_text(item_name)
            snapshot = management_grid_ready_state.get("snapshot")
            main_rect = _main_rect()
            fast_anchor = _env_flag("ERP_FAST_MGMT_ANCHOR", "1")
            cache_key = target or str(item_name or "").strip()
            strict_item = target in {
                _norm_text("계좌번호"),
                _norm_text("금융기관지점"),
            }
            active_row_no = management_active_row_context.get("row_no")
            if strict_item and active_row_no in management_bank_coordinate_fallback_rows:
                cached_bank_xy = management_bank_value_xy_cache.get(target)
                if cached_bank_xy is not None:
                    self.logger.info(
                        f"  [MGMT-ANCHOR] {item_name} 빠른 보통예금 좌표 재사용: rel={cached_bank_xy}"
                    )
                    return int(cached_bank_xy[0]), int(cached_bank_xy[1])
            if fast_anchor and not strict_item and cache_key in management_value_xy_cache:
                cached_x, cached_y = management_value_xy_cache[cache_key]
                self.logger.info(
                    f"  [MGMT-ANCHOR] {item_name} cached coordinate reuse: rel=({cached_x},{cached_y})"
                )
                return int(cached_x), int(cached_y)
            attempts = 1 if fast_anchor else 8
            for attempt in range(attempts):
                if snapshot is None or attempt > 0:
                    snapshot = _management_grid_snapshot()
                value_header = snapshot.get("header_value")
                for row in snapshot.get("items") or []:
                    row_norm = row.get("norm") or ""
                    if not target or (target != row_norm and target not in row_norm and row_norm not in target):
                        continue
                    if value_header:
                        value_x = value_header["rel_x"]
                    else:
                        rect = row["rect"]
                        value_x = min(1450, max(820, (rect.right - main_rect.left) + 260))
                    value_y = row["rel_y"]
                    self.logger.info(
                        f"  [MGMT-ANCHOR] {item_name} 현재 위치 기준 입력 좌표: "
                        f"rel=({value_x},{value_y}), labels={snapshot.get('labels')}"
                    )
                    if fast_anchor and not strict_item and cache_key:
                        management_value_xy_cache[cache_key] = (int(value_x), int(value_y))
                    return int(value_x), int(value_y)
                if fast_anchor and not (snapshot.get("items") or snapshot.get("header_value")):
                    break
                time.sleep(0.25)
            if strict_item and active_row_no not in management_bank_coordinate_fallback_rows:
                raise RuntimeError(
                    f"{item_name} management item is not visible; aborting strict bank-account input. "
                    f"labels={(snapshot or {}).get('labels')}"
                )
            log_msg = (
                f"  [MGMT-ANCHOR] {item_name} 위치 미검출, fallback 사용: rel=(1118,{fallback_y}), "
                f"labels={(snapshot or {}).get('labels')}"
            )
            if fast_anchor:
                self.logger.info(log_msg)
            else:
                self.logger.warning(log_msg)
            if fast_anchor and not strict_item and cache_key:
                management_value_xy_cache[cache_key] = (1118, int(fallback_y))
            return 1118, fallback_y

        def _select_acc_unit_by_coord(target_site):
            order = ["P1공장", "P2공장", "P3공장", "P4공장", "D1공장", "D2공장", "D3공장", "일강 1공장", "일강 2공장", "제이엠", "더원"]
            key = _acc_unit_display(target_site)
            down_count = order.index(key) if key in order else 0
            self.logger.info(f"  [FORM-XY] 회계단위 좌표 선택 시작: target={key}, down={down_count}")
            combo = _find_acc_unit_combo()

            def _try_open(method):
                try:
                    if method == "expand" and combo:
                        combo.expand()
                    elif method == "combo-arrow" and combo:
                        cr = combo.rectangle()
                        pyautogui.click(cr.right - 12, (cr.top + cr.bottom) // 2)
                    elif method == "alt-down":
                        if combo:
                            combo.click_input()
                        else:
                            _click_form_xy(237, 124, "회계단위 드롭다운")
                        pyautogui.hotkey("alt", "down")
                    elif method == "f4":
                        if combo:
                            combo.click_input()
                        else:
                            _click_form_xy(237, 124, "회계단위 드롭다운")
                        pyautogui.press("f4")
                    elif method == "xy-arrow":
                        _click_form_xy(237, 124, "회계단위 드롭다운")
                    time.sleep(ERP_SETTLE_WAIT)
                    items = _visible_acc_unit_items()
                    if items:
                        self.logger.info(f"  [FORM-VERIFY] 회계단위 드롭다운 열림 확인: {method} / {len(items)}건")
                        return items
                except Exception as e:
                    self.logger.warning(f"  [FORM-XY] 회계단위 드롭다운 열기 실패({method}): {e}")
                return []

            items = []
            for method in ("expand", "combo-arrow", "alt-down", "f4", "xy-arrow"):
                items = _try_open(method)
                if items:
                    break
            if not items:
                _fail_form(f"회계단위 드롭다운 열기 실패: target={key}")

            target_item = None
            for item in items:
                if str(item.window_text() or "").strip() == key:
                    target_item = item
                    break
            if target_item is None:
                _fail_form(f"회계단위 항목 미발견: target={key}, items={[str(i.window_text() or '').strip() for i in items]}")

            lr = target_item.rectangle()
            pyautogui.click(lr.left + lr.width() // 2, lr.top + lr.height() // 2)
            time.sleep(ERP_SETTLE_WAIT)
            if fast_field_verify:
                self.logger.info(f"  [FORM-VERIFY] 회계단위 fast verify skipped: {key}")
            else:
                _verify_acc_unit(key)
            self.logger.info(f"  [FORM-XY] 회계단위 좌표 선택 완료: {key}")

        def _double_click_form_xy(x, y, label, wait=None):
            r = _main_rect()
            ax, ay = r.left + x, r.top + y
            pyautogui.doubleClick(ax, ay, interval=0.05)
            self.logger.info(f"  [MGMT-XY] {label} 더블클릭: rel=({x},{y}), abs=({ax},{ay})")
            time.sleep(ERP_FORM_WAIT if wait is None else wait)

        def _vendor_double_click_abs(x, y, label, wait=None):
            # K-System GDI 관리항목 셀은 너무 짧은 synthetic doubleClick을
            # 한 번의 포커스 클릭으로만 처리할 수 있다. 두 번의 down/up을
            # 사람이 누르는 간격으로 보내 최초 셀과 검색 결과 모두 같은
            # 방식으로 확정한다.
            _release_modifiers(f"{label} 더블클릭 직전", wait=False)
            pyautogui.moveTo(int(x), int(y))
            for click_no in range(2):
                pyautogui.mouseDown(button="left")
                time.sleep(vendor_double_click_hold)
                pyautogui.mouseUp(button="left")
                if click_no == 0:
                    time.sleep(vendor_double_click_interval)
            self.logger.info(
                f"  [MGMT-XY] {label} 안정 더블클릭: abs=({int(x)},{int(y)}), "
                f"hold={vendor_double_click_hold:.2f}, interval={vendor_double_click_interval:.2f}"
            )
            time.sleep(ERP_FORM_WAIT if wait is None else wait)

        def _double_click_vendor_value_xy(x, y, label, wait=None):
            r = _main_rect()
            _vendor_double_click_abs(
                r.left + int(x),
                r.top + int(y),
                label,
                wait=wait,
            )

        def _value_text(value, comma=False):
            if value is None:
                return ""
            if isinstance(value, (int, float)):
                return f"{int(value):,}" if comma else str(int(value))
            text = str(value).strip()
            if not text:
                return ""
            if not comma:
                text = text.replace(",", "")
            return text

        mgmt_clipboard_cache = {"text": None}

        def _type_or_paste_text(text, label, settle_wait=None):
            text = str(text or "")
            # 관리항목은 Ctrl+A/Backspace 없이 현재 셀에 바로 붙여넣습니다.
            # 이전 오류 원인은 붙여넣기보다 Ctrl+A 단축키 오동작 가능성이 높아 이 경로로 재검증합니다.
            _release_modifiers(f"{label} 붙여넣기 직전", wait=False)
            if mgmt_clipboard_cache.get("text") != text:
                pyperclip.copy(text)
                mgmt_clipboard_cache["text"] = text
                time.sleep(mgmt_clipboard_wait)
            pyautogui.hotkey('ctrl', 'v')
            _release_modifiers(f"{label} 붙여넣기 직후", wait=False)
            effective_settle_wait = (
                mgmt_key_wait
                if settle_wait is None
                else max(mgmt_key_wait, float(settle_wait))
            )
            time.sleep(effective_settle_wait)
            self.logger.info(f"  [MGMT-XY] {label} 값 붙여넣기 완료(Ctrl+A 미사용): {text}")

        def _input_value_xy(
            x,
            y,
            text,
            label,
            enter_count=0,
            clear=True,
            paste_settle_wait=None,
            commit_settle_wait=None,
        ):
            _click_form_xy(x, y, label, wait=mgmt_click_wait)
            _release_modifiers(f"{label} 클릭 후", wait=False)
            time.sleep(mgmt_focus_wait)
            # 하단 관리항목 그리드는 Ctrl+A/Backspace가 ERP 단축키로 오동작할 수 있어
            # 기존값 초기화 없이 현재 포커스 위치에 바로 붙여넣습니다.
            if clear and verbose_management_clear:
                self.logger.info(f"  [MGMT-XY] {label} clear 요청 무시: Ctrl+A/Backspace 미사용")
            _type_or_paste_text(text, label, settle_wait=paste_settle_wait)
            effective_commit_wait = (
                mgmt_commit_wait
                if commit_settle_wait is None
                else max(mgmt_commit_wait, float(commit_settle_wait))
            )
            for _ in range(max(0, int(enter_count))):
                _release_modifiers(f"{label} Enter 직전", wait=False)
                pyautogui.press('enter')
                time.sleep(effective_commit_wait)
            time.sleep(effective_commit_wait if enter_count else mgmt_key_wait)
        def _business_query_for_management(site):
            text = str(site or "")
            mapping = {
                "D1공장": "(주)대승-평택1공장",
                "D2공장": "(주)대승-김제2공장",
                "D3공장": "(주)대승-김제5공장",
                "P1공장": "대승정밀(주)-평택P1",
                "P2공장": "대승정밀(주)-김제P2",
                "P3공장": "대승정밀(주)-김제P3",
                "P4공장": "대승정밀(주)-김제P4",
                "일강1공장": "(주)일강-평택",
                "일강2공장": "(주)일강-김제",
            }
            for key, value in mapping.items():
                if key in text:
                    return value
            return text

        def _corp_group():
            corp_name = CORP_MAP.get(site_name, "")
            if "대승정밀" in corp_name or re.search(r"\bP[1-4]\b|P[1-4]공장", str(site_name), re.IGNORECASE):
                return "대승정밀"
            if "일강" in corp_name or "일강" in str(site_name):
                return "일강"
            return "대승"

        def _normalize_account_name(account_name):
            text = str(account_name or "").strip()
            text = re.sub(r'\s+', '', text)
            if "부가세" in text and "대급금" in text:
                return "부가세대급금"
            if "가지급금" in text:
                return "가지급금(업체)"
            if "미지급금" in text:
                return "미지급금(원화)"
            if "컴퓨터" in text and ("소프트웨어" in text or "S/W" in text.upper()):
                return "컴퓨터소프트웨어"
            if "집기" in text and "비품" in text:
                return "집기비품"
            if "소모품" in text:
                return "소모품비"
            if "지급수수료" in text:
                return "지급수수료"
            if "통신비" in text:
                return "통신비"
            return text

        def _management_plan(account_name):
            account = _normalize_account_name(account_name)
            corp = _corp_group()
            plans = {
                ("집기비품", "대승"): ["vendor"],
                ("집기비품", "대승정밀"): ["vendor"],
                ("집기비품", "일강"): ["evidence", "vendor", "project"],
                ("컴퓨터소프트웨어", "대승"): [],
                ("컴퓨터소프트웨어", "일강"): ["vendor"],
                ("소모품비", "대승"): [],
                ("소모품비", "대승정밀"): [],
                ("소모품비", "일강"): ["evidence"],
                ("지급수수료", "대승"): [],
                ("지급수수료", "대승정밀"): ["vendor"],
                ("지급수수료", "일강"): ["evidence"],
                ("통신비", "대승"): [],
                ("통신비", "대승정밀"): [],
                ("통신비", "일강"): ["evidence"],
                ("부가세대급금", "대승"): ["evidence", "date", "vendor_vat", "supply", "business"],
                ("부가세대급금", "대승정밀"): ["evidence", "date", "vendor_vat", "supply", "business"],
                ("부가세대급금", "일강"): ["evidence", "date", "vendor_vat", "supply", "business"],
                ("가지급금(업체)", "대승"): ["vendor"],
                ("가지급금(업체)", "대승정밀"): ["vendor"],
                ("가지급금(업체)", "일강"): ["vendor"],
                ("미지급금(원화)", "대승"): ["vendor"],
                ("미지급금(원화)", "대승정밀"): ["vendor"],
                ("미지급금(원화)", "일강"): ["vendor"],
            }
            return account, corp, plans.get((account, corp), [])

        def _evidence_keyword(account, corp):
            if account == "부가세대급금":
                return "세금계산서(일반과세)-전자"
            if corp == "일강" and account in ("집기비품", "소모품비", "지급수수료", "통신비"):
                return "지출증빙-세금계산서"
            return "세금계산서(일반과세)-전자"

        def _uncheck_cash_processing(row_no):
            if skip_visible_row_scan:
                cached_checkbox = (
                    (management_grid_ready_state.get("snapshot") or {}).get(
                        "cash_processing_checkbox"
                    )
                )
                if cached_checkbox is None:
                    self.logger.warning(
                        f"  [MGMT-XY] {row_no}행 출납처리여부 체크박스가 GDI UIA에 노출되지 않아 "
                        "임의 좌표 클릭 없이 현재 기본 해제 상태를 유지합니다."
                    )
                    return
                try:
                    state = cached_checkbox.get_toggle_state()
                    self.logger.info(
                        f"  [MGMT-XY] {row_no}행 출납처리여부 캐시 상태={state}"
                    )
                    if state == 1:
                        cached_checkbox.click_input()
                        time.sleep(ERP_FORM_WAIT)
                        self.logger.info(
                            f"  [MGMT-XY] {row_no}행 출납처리여부 체크 해제 완료(최초 UIA 캐시)"
                        )
                    return
                except Exception as e:
                    self.logger.warning(
                        f"  [MGMT-XY] {row_no}행 출납처리여부 최초 UIA 캐시를 재사용하지 못해 "
                        f"임의 좌표 클릭 없이 현재 상태를 유지합니다: {e}"
                    )
                    return
            try:
                for cb in main_win.descendants(control_type='CheckBox'):
                    try:
                        name = cb.window_text() or ''
                        aid = cb.element_info.automation_id or ''
                        if aid == 'Check1' and '출납처리여부' in name:
                            state = cb.get_toggle_state()
                            self.logger.info(f"  [MGMT-XY] {row_no}행 출납처리여부 현재상태={state}")
                            if state == 1:
                                cb.click_input()
                                time.sleep(ERP_FORM_WAIT)
                                self.logger.info(f"  [MGMT-XY] {row_no}행 출납처리여부 체크 해제 완료(UIA)")
                            else:
                                self.logger.info(f"  [MGMT-XY] {row_no}행 출납처리여부 이미 해제 상태")
                            return
                    except:
                        pass
                raise RuntimeError("출납처리여부 체크박스 UIA 미검출")
            except Exception as e:
                self.logger.warning(f"  [MGMT-XY] {row_no}행 출납처리여부 UIA 해제 실패: {e}. 좌표 1회 클릭 fallback")
                _click_form_xy(506, 772, f"{row_no}행 출납처리여부 체크박스")

        def _fill_management_for_current_row(row_no, account_name):
            vendor_name = str(form_data.get('vendor_name', '') or '').strip()
            vendor_biz_no = str(
                form_data.get('vendor_biz_no')
                or form_data.get('vendor_business_no')
                or form_data.get('vendor_business_number')
                or form_data.get('supplier_biz_no')
                or form_data.get('supplier_business_no')
                or form_data.get('supplier_business_number')
                or ''
            ).strip()

            def _vendor_match_text(*values):
                text = " ".join(str(value or "") for value in values)
                text = re.sub(r"\([^)]*\)", "", text)
                return re.sub(r"\s+", "", text).lower()

            def _vendor_biz_no_override(*values):
                compact = _vendor_match_text(*values)
                rules = [
                    (("컴퓨존",), "컴퓨존", "106-81-83458"),
                    (("kt", "케이티"), "케이티", "102-81-42945"),
                    (("오토에버", "현대오토에버", "autoever"), "현대오토에버시스템즈", "104-81-53190"),
                    (("다우", "다우기술", "다우오피스"), "다우기술", "220-81-02810"),
                    (("안랩", "ahnlab"), "주식회사 안랩", "214-81-83536"),
                    (("시큐어포인트", "genian", "nac"), "시큐어포인트", "534-87-01726"),
                    (("동양정보통신",), "동양정보통신", "402-81-23213"),
                    (("대신아이씨티",), "대신아이씨티", "504-86-20609"),
                    (("이테크", "이테크시스템", "acronis"), "이테크시스템", "211-88-35257"),
                    (("에티버스",), "에티버스", "106-81-43363"),
                    (("피플러스", "pplus", "peoplus", "gradius"), "피플러스", "129-86-49875"),
                ]
                for aliases, erp_name, biz_no in rules:
                    if any(alias.lower() in compact for alias in aliases):
                        return erp_name, biz_no
                return "", ""

            supply_amount = _value_text(form_data.get('target_supply', 0), comma=False)
            business_query = _business_query_for_management(site_name)
            account_key, corp, plan = _management_plan(account_name)
            line_management_items = form_data.get('erp_line_management_items') or form_data.get('line_management_items') or []
            explicit_management = {}
            if isinstance(line_management_items, list) and row_no - 1 < len(line_management_items):
                candidate = line_management_items[row_no - 1]
                if isinstance(candidate, dict):
                    explicit_management = {
                        str(key): str(value or "")
                        for key, value in candidate.items()
                        if str(key or "").strip()
                    }
            if explicit_management:
                plan = ["explicit"]
            vendor_upper = vendor_name.upper()
            compact_vendor = _vendor_match_text(vendor_name)
            is_kt_vendor = bool(vendor_name) and (
                vendor_upper == "KT"
                or "케이티" in vendor_name
                or "KT" in vendor_upper
            )
            is_autoever_vendor = bool(vendor_name) and (
                "오토에버" in compact_vendor
                or "현대오토에버" in compact_vendor
                or "AUTOEVER" in vendor_upper
            )
            vendor_target_biz_no = ""
            vendor_search_name = vendor_name
            vendor_target_optional = False
            vendor_biz_digits = re.sub(r"[^0-9]", "", vendor_biz_no or "")
            raw_vendor_biz_no = vendor_biz_no
            if vendor_biz_no and len(vendor_biz_digits) != 10:
                self.logger.warning(
                    f"  [MGMT-XY] {row_no}행 거래처 사업자번호 값이 10자리 숫자가 아니라 제외: {vendor_biz_no}"
                )
                vendor_biz_no = ""
                vendor_biz_digits = ""
            override_vendor_name, override_biz_no = _vendor_biz_no_override(
                vendor_name,
                raw_vendor_biz_no,
                vendor_biz_no,
                form_data.get('supplier_name'),
                form_data.get('summary'),
                form_data.get('slip_summary'),
                form_data.get('item_name'),
            )
            vendor_probe_digits = re.sub(
                r"[^0-9]",
                "",
                " ".join(
                    str(value or "")
                    for value in (
                        vendor_name,
                        raw_vendor_biz_no,
                        vendor_biz_no,
                        form_data.get('supplier_name'),
                        form_data.get('summary'),
                        form_data.get('slip_summary'),
                        form_data.get('item_name'),
                    )
                ),
            )
            is_autoever_biz_no = vendor_biz_digits == "1048153190" or "1048153190" in vendor_probe_digits
            if override_biz_no:
                vendor_target_biz_no = override_biz_no
                vendor_search_name = override_vendor_name or vendor_name
            elif is_kt_vendor:
                vendor_target_biz_no = "102-81-42945"
                vendor_search_name = "케이티"
                vendor_target_optional = True
            elif is_autoever_vendor or is_autoever_biz_no:
                vendor_target_biz_no = "104-81-53190"
                vendor_search_name = "현대오토에버시스템즈"
                vendor_target_optional = True
            elif len(vendor_biz_digits) == 10:
                vendor_target_biz_no = f"{vendor_biz_digits[:3]}-{vendor_biz_digits[3:5]}-{vendor_biz_digits[5:]}"
            elif "동양정보통신" in compact_vendor:
                vendor_target_biz_no = "402-81-23213"
                vendor_search_name = "동양정보통신"
            vendor_target_digits = re.sub(r"[^0-9]", "", vendor_target_biz_no or "")
            is_special_vendor_keyboard = len(vendor_target_digits) == 10

            self.logger.info(
                f"  [MGMT-XY] {row_no}행 관리항목 조건판정: raw_account={account_name}, "
                f"account={account_key}, corp={corp}, plan={plan}"
            )

            if not plan:
                self.logger.info(f"  [MGMT-XY] {row_no}행은 입력 불필요 계정이라 관리항목 입력 스킵")
                return

            if "uncheck_cash" in plan:
                _uncheck_cash_processing(row_no)

            if "evidence" in plan:
                evidence_text = _evidence_keyword(account_key, corp)
                self.logger.info(f"  [MGMT-XY] {row_no}행 증빙 검색어: {evidence_text}")
                # 증빙 칸은 Enter 입력 시 ERP가 통화 필드로 포커스를 넘기는 경우가 있어 타이핑만 수행합니다.
                _input_value_xy(408, 826, evidence_text, f"{row_no}행 증빙", enter_count=0, clear=True)

            def _vendor_popup_context(root, rect=None, source="top-level"):
                return {
                    "root": root,
                    "rect": rect if rect is not None else root.rectangle(),
                    "source": source,
                }

            def _vendor_popup_root(popup):
                return popup.get("root") if isinstance(popup, dict) else popup

            def _vendor_popup_rect(popup):
                return popup.get("rect") if isinstance(popup, dict) else popup.rectangle()

            def _visible_vendor_popup_controls(popup, control_type=None, top_band=False):
                root = _vendor_popup_root(popup)
                popup_rect = _vendor_popup_rect(popup)
                try:
                    controls = root.descendants()
                except Exception:
                    return []
                visible = []
                top_limit = popup_rect.top + min(150, max(80, popup_rect.height() // 4))
                for ctrl in controls:
                    try:
                        if not ctrl.is_visible() or not ctrl.is_enabled():
                            continue
                        if control_type and str(ctrl.element_info.control_type or "") != control_type:
                            continue
                        rect = ctrl.rectangle()
                        center_x = (rect.left + rect.right) // 2
                        center_y = (rect.top + rect.bottom) // 2
                        if not (
                            popup_rect.left <= center_x <= popup_rect.right
                            and popup_rect.top <= center_y <= popup_rect.bottom
                        ):
                            continue
                        if top_band and center_y > top_limit:
                            continue
                        visible.append(ctrl)
                    except Exception:
                        pass
                return visible

            def _direct_vendor_popup_text(ctrl):
                values = []
                for getter in (
                    lambda: ctrl.window_text(),
                    lambda: ctrl.element_info.name,
                ):
                    try:
                        value = _norm_text(getter())
                        if value and value not in values:
                            values.append(value)
                    except Exception:
                        pass
                return values

            def _vendor_control_identity(ctrl):
                try:
                    handle = int(ctrl.handle or 0)
                    if handle:
                        return ("handle", handle)
                except Exception:
                    pass
                try:
                    runtime_id = ctrl.element_info.runtime_id
                    if callable(runtime_id):
                        runtime_id = runtime_id()
                    if runtime_id:
                        return ("runtime", tuple(runtime_id))
                except Exception:
                    pass
                return ("object", id(ctrl))

            def _find_internal_vendor_popup():
                try:
                    descendants = main_win.descendants()
                except Exception:
                    return None
                controls = []
                for ctrl in descendants:
                    try:
                        if ctrl.is_visible():
                            controls.append(ctrl)
                    except Exception:
                        pass

                title_controls = []
                marker_controls = []
                marker_names = {
                    _norm_text("거래처번호"),
                    _norm_text("거래처코드"),
                    _norm_text("거래처명"),
                    _norm_text("사업자번호"),
                    _norm_text("대표자"),
                    _norm_text("유통분류"),
                    _norm_text("종사업자번호"),
                    _norm_text("부서명"),
                }
                seen_markers = set()
                for ctrl in controls:
                    direct_values = _direct_vendor_popup_text(ctrl)
                    if any("거래처ds" in value.lower() for value in direct_values):
                        title_controls.append(ctrl)
                    for value in direct_values:
                        if value in marker_names:
                            seen_markers.add(value)
                            marker_controls.append(ctrl)

                required_headers = {_norm_text("거래처코드"), _norm_text("거래처명")}
                has_title = bool(title_controls)
                has_header_signature = required_headers.issubset(seen_markers) and len(seen_markers) >= 3
                if not has_title and not has_header_signature:
                    return None

                main_rect = _main_rect()
                candidates = []
                for ctrl in title_controls + marker_controls:
                    current = ctrl
                    for _ in range(10):
                        try:
                            rect = current.rectangle()
                            width = rect.width()
                            height = rect.height()
                            inside_main = (
                                rect.left >= main_rect.left - 5
                                and rect.top >= main_rect.top - 5
                                and rect.right <= main_rect.right + 5
                                and rect.bottom <= main_rect.bottom + 5
                            )
                            if (
                                inside_main
                                and width >= int(main_rect.width() * 0.65)
                                and height >= int(main_rect.height() * 0.45)
                            ):
                                candidates.append((width * height, current, rect))
                            parent = current.parent()
                            if parent is None:
                                break
                            current = parent
                        except Exception:
                            break

                if candidates:
                    seen_candidates = set()
                    for _, root, popup_rect in sorted(candidates, key=lambda item: item[0]):
                        candidate_key = (
                            _vendor_control_identity(root),
                            popup_rect.left,
                            popup_rect.top,
                            popup_rect.right,
                            popup_rect.bottom,
                        )
                        if candidate_key in seen_candidates:
                            continue
                        seen_candidates.add(candidate_key)
                        nearly_main_window = (
                            abs(popup_rect.left - main_rect.left) <= 12
                            and abs(popup_rect.top - main_rect.top) <= 12
                            and popup_rect.width() >= int(main_rect.width() * 0.95)
                            and popup_rect.height() >= int(main_rect.height() * 0.90)
                        )
                        if nearly_main_window:
                            continue
                        candidate_popup = _vendor_popup_context(root, popup_rect, "internal-uia")
                        # 결과 그리드도 충분히 큰 조상 컨테이너일 수 있다. 검색조건과
                        # 검색값 컨트롤을 모두 포함한 후보만 실제 MDI 화면으로 채택한다.
                        candidate_combos = _visible_vendor_popup_controls(
                            candidate_popup,
                            "ComboBox",
                            top_band=True,
                        )
                        candidate_edits = _visible_vendor_popup_controls(
                            candidate_popup,
                            "Edit",
                            top_band=True,
                        )
                        if candidate_combos and candidate_edits:
                            return candidate_popup

                # 거래처ds는 ERP MDI 내부 화면이라 UIA가 컨테이너 대신 메인 창만
                # 반환할 수 있다. 이때는 메인 창의 고정된 MDI 여백만 제외한다.
                popup_rect = UiaRect(
                    main_rect.left + 8,
                    main_rect.top + 52,
                    main_rect.right - 8,
                    main_rect.bottom - 8,
                )
                return _vendor_popup_context(main_win, popup_rect, "internal-signature")

            def _log_vendor_popup_detection(popup):
                popup_rect = _vendor_popup_rect(popup)
                source = popup.get("source", "top-level") if isinstance(popup, dict) else "top-level"
                signature = (
                    source,
                    popup_rect.left,
                    popup_rect.top,
                    popup_rect.right,
                    popup_rect.bottom,
                )
                if signature == vendor_popup_detection_state["signature"]:
                    return
                vendor_popup_detection_state["signature"] = signature
                self.logger.info(
                    "  [MGMT-XY] 거래처 팝업 감지: "
                    f"source={source}, rect=({popup_rect.left},{popup_rect.top})-"
                    f"({popup_rect.right},{popup_rect.bottom})"
                )

            def _find_vendor_popup(timeout=3.0):
                end_at = time.time() + timeout
                while time.time() < end_at:
                    same_handle_vendor_win = None
                    try:
                        for win in Desktop(backend="uia").windows():
                            try:
                                title = win.window_text() or ""
                                same_as_main = win is main_win
                                try:
                                    same_as_main = same_as_main or int(win.handle) == int(main_win.handle)
                                except Exception:
                                    pass
                                if same_as_main:
                                    # K-System의 거래처ds는 별도 최상위 창이 아니라 기존 ERP
                                    # native handle의 MDI 제목만 거래처ds로 바뀌어 노출될 수 있다.
                                    # 이 신호까지 무조건 제외하면 최초 관리항목값 셀만 선택된 채
                                    # 팝업을 열지 못한 것으로 판단한다.
                                    if win.is_visible() and "거래처ds" in _norm_text(title).lower():
                                        same_handle_vendor_win = win
                                    continue
                                if win.is_visible() and "거래처" in title:
                                    popup = _vendor_popup_context(win, source="top-level")
                                    _log_vendor_popup_detection(popup)
                                    return popup
                            except Exception:
                                pass
                    except Exception:
                        pass
                    if same_handle_vendor_win is not None:
                        main_rect = _main_rect()
                        popup = _vendor_popup_context(
                            same_handle_vendor_win,
                            UiaRect(
                                main_rect.left + 8,
                                main_rect.top + 52,
                                main_rect.right - 8,
                                main_rect.bottom - 8,
                            ),
                            "internal-title",
                        )
                        _log_vendor_popup_detection(popup)
                        return popup
                    # 같은 ERP native handle의 제목이 이미 거래처ds로 바뀌었다면
                    # 이것만으로 MDI 화면이 열린 것이 확인된다. 이 신호를 확인한 뒤
                    # main_win.descendants()를 먼저 호출하면 GDI 화면에서 수분 동안
                    # 멈출 수 있으므로, 전체 내부 UIA 탐색은 제목 신호가 없을 때만 한다.
                    popup = _find_internal_vendor_popup()
                    if popup:
                        _log_vendor_popup_detection(popup)
                        return popup
                    time.sleep(0.1)
                return None

            def _paste_text_fast(text, label):
                try:
                    # 거래처ds 검색칸은 직전 검증/Excel 복사로 시스템 클립보드가
                    # 바뀔 수 있으므로 캐시를 신뢰하지 않고 매번 목표값을 복사한다.
                    pyperclip.copy(text)
                    mgmt_clipboard_cache["text"] = text
                    time.sleep(mgmt_clipboard_wait)
                    pyautogui.hotkey('ctrl', 'v')
                    _release_modifiers(f"{label} 붙여넣기 직후", wait=False)
                    time.sleep(mgmt_key_wait)
                except Exception:
                    pyautogui.write(text, interval=0.01)

            def _select_vendor_popup_filter(popup, search_label, up_presses):
                combos = _visible_vendor_popup_controls(popup, "ComboBox", top_band=True)
                combos.sort(key=lambda ctrl: (ctrl.rectangle().top, ctrl.rectangle().left))
                for combo in combos:
                    try:
                        if search_label in (combo.window_text() or ""):
                            return True
                    except Exception:
                        pass
                    try:
                        combo.select(search_label)
                        time.sleep(ERP_CLICK_WAIT)
                        return True
                    except Exception:
                        pass
                    try:
                        combo.click_input()
                        time.sleep(ERP_CLICK_WAIT)
                        pyautogui.press('down', presses=5, interval=0.08)
                        pyautogui.press('up', presses=max(1, int(up_presses)), interval=0.08)
                        pyautogui.press('enter')
                        time.sleep(ERP_CLICK_WAIT)
                        return True
                    except Exception:
                        pass
                try:
                    popup_rect = _vendor_popup_rect(popup)
                    pyautogui.click(popup_rect.left + 80, popup_rect.top + 58)
                    time.sleep(ERP_CLICK_WAIT)
                    pyautogui.press('down', presses=5, interval=0.08)
                    pyautogui.press('up', presses=max(1, int(up_presses)), interval=0.08)
                    pyautogui.press('enter')
                    time.sleep(ERP_CLICK_WAIT)
                    self.logger.info(
                        f"  [MGMT-XY] 거래처 팝업 검색조건 직접 선택: {search_label} "
                        f"(Up {max(1, int(up_presses))})"
                    )
                    return True
                except Exception:
                    return False

            def _input_vendor_popup_search_text(popup, text, label):
                edits = _visible_vendor_popup_controls(popup, "Edit", top_band=True)
                edits.sort(key=lambda ctrl: (ctrl.rectangle().top, -ctrl.rectangle().width()))
                for edit in edits:
                    try:
                        edit.click_input()
                        time.sleep(ERP_CLICK_WAIT)
                        pyautogui.hotkey('ctrl', 'a')
                        _release_modifiers("거래처 팝업 검색어 Ctrl+A 후", wait=False)
                        _paste_text_fast(text, f"거래처 팝업 {label} 검색어")
                        return True
                    except Exception:
                        pass
                try:
                    popup_rect = _vendor_popup_rect(popup)
                    pyautogui.click(
                        popup_rect.left + max(240, popup_rect.width() // 2),
                        popup_rect.top + 58,
                    )
                    time.sleep(ERP_CLICK_WAIT)
                    pyautogui.hotkey('ctrl', 'a')
                    _release_modifiers("거래처 팝업 검색어 직접 클릭 Ctrl+A 후", wait=False)
                    _paste_text_fast(text, f"거래처 팝업 {label} 검색어")
                    return True
                except Exception:
                    return False

            def _click_vendor_popup_search_button(popup, label):
                search_norm = _norm_text("검색")
                popup_rect = _vendor_popup_rect(popup)
                search_x = popup_rect.right - 58
                search_y = popup_rect.top + 58
                buttons = _visible_vendor_popup_controls(popup, "Button", top_band=True)
                buttons.sort(
                    key=lambda ctrl: (
                        (((ctrl.rectangle().left + ctrl.rectangle().right) // 2) - search_x) ** 2
                        + (((ctrl.rectangle().top + ctrl.rectangle().bottom) // 2) - search_y) ** 2
                    )
                )
                for button in buttons:
                    try:
                        direct_values = _direct_vendor_popup_text(button)
                        if not any(
                            value == search_norm
                            or re.fullmatch(
                                rf"{re.escape(search_norm)}(?:\(.+\)|\[.+\])",
                                value,
                            )
                            for value in direct_values
                        ):
                            continue
                        button.click_input()
                        self.logger.info(f"  [MGMT-XY] {label}: 거래처 팝업 검색 버튼 클릭(UIA)")
                        time.sleep(max(1.0, vendor_popup_search_wait))
                        return True
                    except Exception:
                        pass
                try:
                    pyautogui.click(search_x, search_y)
                    self.logger.info(
                        f"  [MGMT-XY] {label}: 거래처 팝업 검색 버튼 클릭: "
                        f"popup_rel=({popup_rect.width() - 58},58), abs=({search_x},{search_y})"
                    )
                    time.sleep(max(1.0, vendor_popup_search_wait))
                    return True
                except Exception as exc:
                    self.logger.warning(f"  [MGMT-XY] {label}: 거래처 팝업 검색 버튼 클릭 실패: {exc}")
                    return False

            def _wait_vendor_popup_closed(timeout):
                end_at = time.time() + max(0.1, float(timeout))
                consecutive_misses = 0
                while time.time() < end_at:
                    if not _find_vendor_popup(timeout=0.15):
                        consecutive_misses += 1
                        if consecutive_misses >= 2:
                            return True
                    else:
                        consecutive_misses = 0
                    time.sleep(0.10)
                return False

            def _select_first_vendor_popup_result(popup, label, allow_enter_fallback=True):
                try:
                    popup_rect = _vendor_popup_rect(popup)
                    first_row_x = popup_rect.left + 82
                    first_row_y = popup_rect.top + 174
                    _vendor_double_click_abs(
                        first_row_x,
                        first_row_y,
                        f"{label} 거래처 검색 첫 행",
                        wait=ERP_FORM_WAIT,
                    )
                    close_wait = vendor_popup_result_close_wait if not allow_enter_fallback else 0.45
                    if _wait_vendor_popup_closed(close_wait):
                        self.logger.info(f"  [MGMT-XY] {label}: 거래처 검색 첫 행 확정 완료")
                        return True
                    if not allow_enter_fallback:
                        self.logger.warning(
                            f"  [MGMT-XY] {label}: 거래처 검색 첫 행 더블클릭 후 화면이 닫히지 않아 중단"
                        )
                        return False
                    pyautogui.press('enter')
                    time.sleep(ERP_FORM_WAIT)
                    if _wait_vendor_popup_closed(0.45):
                        self.logger.info(f"  [MGMT-XY] {label}: 거래처 검색 첫 행 Enter 확정 완료")
                        return True
                except Exception as exc:
                    self.logger.warning(f"  [MGMT-XY] {label}: 거래처 검색 첫 행 확정 실패: {exc}")
                return False

            def _input_vendor_by_popup_keyboard(
                x,
                y,
                label,
                search_text,
                search_label,
                up_presses,
                allow_result_enter_fallback=True,
            ):
                popup = None
                popup = _find_vendor_popup(timeout=0.70)
                if popup:
                    self.logger.info(f"  [MGMT-XY] {label}: vendor popup already opened; skip popup-open click")
                for open_try in range(2):
                    if popup:
                        break
                    _double_click_vendor_value_xy(
                        x,
                        y,
                        f"{label} 팝업 열기",
                        wait=vendor_popup_open_wait,
                    )
                    time.sleep(0.75 if open_try == 0 else ERP_FORM_WAIT + 0.65)
                    popup = _find_vendor_popup(timeout=0.80 if open_try == 0 else 3.5)
                    if popup:
                        self.logger.info(f"  [MGMT-XY] {label}: vendor popup opened after click {open_try + 1}; stopping extra clicks")
                        break
                if not popup:
                    self.logger.warning(f"  [MGMT-XY] {label}: 거래처 팝업을 열지 못해 PASS")
                    return False
                # ERP vendor popup opens with the search text box focused.
                # Do not call popup.set_focus(); it can move focus to the
                # window/grid, so the business-number paste disappears and
                # navigation confirms a wrong row.
                self.logger.info(
                    f"  [MGMT-XY] {label}: vendor popup opened; relation cell untouched, keeping default search-box focus"
                )
                time.sleep(vendor_popup_focus_wait)

                if search_label == "거래처번호":
                    if not _input_vendor_popup_search_text(popup, search_text, search_label):
                        self.logger.warning(f"  [MGMT-XY] {label}: 거래처번호 검색칸 입력 실패")
                        return False
                    time.sleep(max(1.0, vendor_popup_search_wait))
                    self.logger.info(f"  [MGMT-XY] {label}: 거래처번호 입력 후 1초 대기 완료: {search_text}")
                    if not _select_vendor_popup_filter(popup, search_label, up_presses):
                        self.logger.warning(f"  [MGMT-XY] {label}: 거래처번호 검색조건 선택 실패")
                        return False
                    if not _click_vendor_popup_search_button(popup, label):
                        return False
                    return _select_first_vendor_popup_result(
                        popup,
                        label,
                        allow_enter_fallback=allow_result_enter_fallback,
                    )

                # ERP 거래처 팝업은 UIA/검색칸 추정이 불안정해 확인된 키보드 흐름을 사용합니다.
                # 사업자번호를 사용하는 기존 전산 자동화 경로만 이 키보드 흐름을 유지합니다.
                pyautogui.hotkey('ctrl', 'a')
                _release_modifiers(f"{label} 거래처 팝업 검색칸 Ctrl+A 후", wait=False)
                time.sleep(max(0.18, mgmt_key_wait))
                _paste_text_fast(search_text, f"{label} 거래처 {search_label}")
                search_settle_wait = max(
                    vendor_popup_search_wait,
                    1.0 if search_label == "거래처번호" else 0.0,
                )
                time.sleep(search_settle_wait)
                self.logger.info(f"  [MGMT-XY] {label}: 거래처 {search_label} 붙여넣기: {search_text}")
                pyautogui.press('tab', presses=4, interval=0.08)
                time.sleep(mgmt_key_wait)
                pyautogui.press('down', presses=5, interval=0.08)
                time.sleep(mgmt_key_wait)
                pyautogui.press('up', presses=max(1, int(up_presses)), interval=0.08)
                time.sleep(mgmt_key_wait)
                pyautogui.press('tab', presses=3, interval=0.08)
                time.sleep(mgmt_key_wait)
                pyautogui.press('enter', presses=2, interval=0.12)
                time.sleep(ERP_FORM_WAIT)
                self.logger.info(
                    f"  [MGMT-XY] {label}: 거래처 {search_label} 키보드 시퀀스 확정"
                    f"(Up {max(1, int(up_presses))}, Enter 2회): {search_text}"
                )
                return True

            def _input_vendor_by_business_no_keyboard(x, y, label, target_biz_no):
                return _input_vendor_by_popup_keyboard(x, y, label, target_biz_no, "사업자번호", 1)

            def _foreground_window_title():
                """Read the active top-level title without a slow UIA descendant scan."""
                try:
                    user32 = ctypes.windll.user32
                    hwnd = int(user32.GetForegroundWindow() or 0)
                    length = int(user32.GetWindowTextLengthW(hwnd) or 0)
                    buffer = ctypes.create_unicode_buffer(max(256, length + 2))
                    user32.GetWindowTextW(hwnd, buffer, len(buffer))
                    return hwnd, str(buffer.value or "").strip()
                except Exception as exc:
                    self.logger.debug(
                        f"  [MGMT-VERIFY] foreground title read failed: {exc}"
                    )
                    return 0, ""

            def _is_vendor_ds_title(title):
                compact = re.sub(r"[\s_]+", "", str(title or "")).lower()
                return "거래처ds" in compact

            def _window_process_id(hwnd):
                try:
                    process_id = ctypes.c_ulong(0)
                    ctypes.windll.user32.GetWindowThreadProcessId(
                        int(hwnd or 0),
                        ctypes.byref(process_id),
                    )
                    return int(process_id.value or 0)
                except Exception:
                    return 0

            def _wait_vendor_ds_foreground(expected_process_id, timeout):
                deadline = time.time() + max(0.5, float(timeout))
                last_hwnd = 0
                last_title = ""
                last_process_id = 0
                while time.time() < deadline:
                    last_hwnd, last_title = _foreground_window_title()
                    last_process_id = _window_process_id(last_hwnd)
                    if (
                        _is_vendor_ds_title(last_title)
                        and (
                            not expected_process_id
                            or int(last_process_id) == int(expected_process_id)
                        )
                    ):
                        return int(last_hwnd), last_title
                    # F9로 열린 거래처ds가 ERP 본창 뒤에 생기는 경우가 있다.
                    # 느린 UIA 탐색 없이 최상위 HWND만 열거해 같은 ERP 프로세스의
                    # 거래처ds를 앞으로 가져온다.
                    candidates = []
                    try:
                        user32 = ctypes.windll.user32
                        enum_proc_type = ctypes.WINFUNCTYPE(
                            ctypes.c_bool,
                            ctypes.c_void_p,
                            ctypes.c_void_p,
                        )

                        def _enum_vendor_ds(hwnd, _lparam):
                            try:
                                hwnd = int(hwnd or 0)
                                if not hwnd or not user32.IsWindowVisible(hwnd):
                                    return True
                                length = int(user32.GetWindowTextLengthW(hwnd) or 0)
                                buffer = ctypes.create_unicode_buffer(max(256, length + 2))
                                user32.GetWindowTextW(hwnd, buffer, len(buffer))
                                title = str(buffer.value or "").strip()
                                process_id = _window_process_id(hwnd)
                                if (
                                    _is_vendor_ds_title(title)
                                    and (
                                        not expected_process_id
                                        or int(process_id) == int(expected_process_id)
                                    )
                                ):
                                    candidates.append((hwnd, title, process_id))
                            except Exception:
                                pass
                            return True

                        callback = enum_proc_type(_enum_vendor_ds)
                        user32.EnumWindows(callback, 0)
                        if candidates:
                            candidate_hwnd, candidate_title, candidate_pid = candidates[0]
                            current_thread_id = int(
                                ctypes.windll.kernel32.GetCurrentThreadId() or 0
                            )
                            foreground_thread_id = int(
                                user32.GetWindowThreadProcessId(
                                    user32.GetForegroundWindow(),
                                    None,
                                )
                                or 0
                            )
                            target_thread_id = int(
                                user32.GetWindowThreadProcessId(candidate_hwnd, None)
                                or 0
                            )
                            attached_thread_ids = []
                            try:
                                for thread_id in (
                                    foreground_thread_id,
                                    target_thread_id,
                                ):
                                    if (
                                        thread_id
                                        and thread_id != current_thread_id
                                        and thread_id not in attached_thread_ids
                                        and user32.AttachThreadInput(
                                            current_thread_id,
                                            thread_id,
                                            True,
                                        )
                                    ):
                                        attached_thread_ids.append(thread_id)
                                user32.ShowWindow(candidate_hwnd, 9)  # SW_RESTORE
                                user32.BringWindowToTop(candidate_hwnd)
                                user32.SetForegroundWindow(candidate_hwnd)
                                user32.SetActiveWindow(candidate_hwnd)
                            finally:
                                for thread_id in reversed(attached_thread_ids):
                                    user32.AttachThreadInput(
                                        current_thread_id,
                                        thread_id,
                                        False,
                                    )
                            last_hwnd = int(candidate_hwnd)
                            last_title = str(candidate_title)
                            last_process_id = int(candidate_pid)
                    except Exception as exc:
                        self.logger.debug(
                            f"  [MGMT-XY] 거래처ds 최상위 창 활성화 실패: {exc}"
                        )
                    time.sleep(0.10)
                self.logger.warning(
                    "  [MGMT-VERIFY] F9 후 거래처ds foreground 미확인 "
                    f"(expected_pid={expected_process_id}, last_pid={last_process_id}, "
                    f"last_hwnd={last_hwnd}, last_title={last_title!r})"
                )
                return 0, ""

            def _management_value_visual_ink(x, y):
                """Count painted text inside the value cell, excluding its borders."""
                try:
                    rect = _main_rect()
                    right = rect.left + int(x) - 10
                    # 분할 바 위치에 따라 관리항목값 칸의 구분선이 클릭 지점보다
                    # 훨씬 왼쪽(value_x-360 부근)까지 올 수 있다. 짧은 거래처
                    # 코드가 칸 왼쪽 끝에 그려져도 잡히도록 값 칸 전체를 본다.
                    # (칸 왼쪽의 관리항목 이름은 빨간 글자라 잉크로 세지 않는다.)
                    scan_width = max(
                        250,
                        int(float(os.getenv("ERP_MGMT_VALUE_SCAN_WIDTH", "350") or "350")),
                    )
                    left = max(rect.left, right - scan_width)
                    top = rect.top + int(y) - 8
                    bottom = rect.top + int(y) + 8
                    image = pyautogui.screenshot(
                        region=(left, top, max(1, right - left), max(1, bottom - top))
                    )
                    ink_pixels = 0
                    ink_rows = set()
                    ink_columns = set()
                    width, height = image.size
                    for sample_y in range(1, max(1, height - 1)):
                        for sample_x in range(0, width, 2):
                            r, g, b = image.getpixel((sample_x, sample_y))[:3]
                            # 선택 셀의 하늘색 배경/테두리는 제외하고 어두운 글자만 센다.
                            is_ink = max(r, g, b) < 125
                            if is_ink:
                                ink_pixels += 1
                                ink_rows.add(sample_y)
                                ink_columns.add(sample_x)
                    ink_span = (
                        max(ink_columns) - min(ink_columns)
                        if len(ink_columns) >= 2
                        else 0
                    )
                    return int(ink_pixels), len(ink_rows), len(ink_columns), int(ink_span)
                except Exception as exc:
                    self.logger.debug(
                        f"  [MGMT-VERIFY] management value visual scan failed: {exc}"
                    )
                    return 0, 0, 0, 0

            def _force_english_ime(label=""):
                # 물리 키 입력은 세션의 한/영 IME 상태를 그대로 거친다. 한글
                # 모드면 거래처번호가 자모로 깨지므로(예: PT→ㅔㅅ) 키 입력
                # 직전마다 IME를 영숫자 모드로 강제 전환한다.
                try:
                    import ctypes

                    user32 = ctypes.windll.user32
                    imm32 = ctypes.windll.imm32
                    hwnd = user32.GetForegroundWindow()
                    if not hwnd:
                        return
                    himc = imm32.ImmGetContext(hwnd)
                    if himc:
                        try:
                            imm32.ImmSetConversionStatus(himc, 0, 0)
                        finally:
                            imm32.ImmReleaseContext(hwnd, himc)
                    ime_hwnd = imm32.ImmGetDefaultIMEWnd(hwnd)
                    if ime_hwnd:
                        WM_IME_CONTROL = 0x283
                        IMC_SETCONVERSIONMODE = 0x002
                        user32.SendMessageW(
                            ime_hwnd, WM_IME_CONTROL, IMC_SETCONVERSIONMODE, 0
                        )
                except Exception as exc:
                    self.logger.debug(f"  [IME] 영문 전환 실패({label}): {exc}")

            def _type_vendor_code(vendor_code, label, interval=None):
                vendor_code = str(vendor_code or "").strip()
                if not vendor_code.isascii() or not re.fullmatch(
                    r"[A-Za-z0-9_-]+", vendor_code
                ):
                    self.logger.warning(
                        f"  [MGMT-XY] {label}: 키보드 입력 불가 거래처번호: "
                        f"{vendor_code!r}"
                    )
                    return False
                _force_english_ime(label)
                try:
                    # 사용자 지시: 거래처번호/계좌번호는 타이핑하지 않고
                    # 클립보드로 붙여넣는다. 붙여넣기는 한/영 IME 상태와
                    # 무관해 자모 깨짐(예: PT→ㅔㅅ)이 없다.
                    pyperclip.copy(vendor_code)
                    time.sleep(max(0.05, mgmt_clipboard_wait))
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.10)
                    return True
                except Exception as exc:
                    self.logger.warning(
                        f"  [MGMT-XY] {label}: 거래처번호 붙여넣기 실패: {exc}"
                    )
                    return False

            def _wait_first_vendor_value_committed(
                x,
                y,
                label,
                timeout,
                expected_hwnd,
                baseline_ink,
            ):
                deadline = time.time() + max(1.0, float(timeout))
                last_hwnd = 0
                last_title = ""
                last_ink = 0
                last_ink_rows = 0
                last_ink_columns = 0
                last_ink_span = 0
                while time.time() < deadline:
                    last_hwnd, last_title = _foreground_window_title()
                    (
                        last_ink,
                        last_ink_rows,
                        last_ink_columns,
                        last_ink_span,
                    ) = _management_value_visual_ink(x, y)
                    if (
                        (not expected_hwnd or int(last_hwnd) == int(expected_hwnd))
                        and not _is_vendor_ds_title(last_title)
                        and last_ink >= max(10, int(baseline_ink) + 4)
                        and last_ink_rows >= 3
                        and last_ink_columns >= 3
                        and last_ink_span >= 6
                    ):
                        self.logger.info(
                            f"  [MGMT-VERIFY] {label}: F9 복귀 및 관리항목값 표시 확인 "
                            f"(hwnd={last_hwnd}, foreground={last_title!r}, ink={last_ink}, "
                            f"rows={last_ink_rows}, columns={last_ink_columns}, "
                            f"span={last_ink_span})"
                        )
                        return True
                    time.sleep(0.25)
                self.logger.warning(
                    f"  [MGMT-VERIFY] {label}: F9 결과 미확인 "
                    f"(expected_hwnd={expected_hwnd}, last_hwnd={last_hwnd}, "
                    f"foreground={last_title!r}, vendor_ds={_is_vendor_ds_title(last_title)}, "
                    f"ink={last_ink}, baseline={baseline_ink}, rows={last_ink_rows}, "
                    f"columns={last_ink_columns}, span={last_ink_span})"
                )
                return False

            def _replace_vendor_ds_search_text(
                vendor_code,
                label,
                settle_wait,
            ):
                vendor_code = str(vendor_code or "").strip()
                if not vendor_code.isascii() or not re.fullmatch(
                    r"[A-Za-z0-9_-]+", vendor_code
                ):
                    self.logger.warning(
                        f"  [MGMT-VERIFY] {label}: 키보드 입력 불가 거래처번호: "
                        f"{vendor_code!r}"
                    )
                    return False
                type_interval = max(
                    0.10,
                    float(os.getenv("ERP_MGMT_VENDOR_TYPE_INTERVAL", "0.15") or "0.15"),
                )
                _release_modifiers(f"{label} 거래처번호 붙여넣기 직전", wait=False)
                # 사용자 지시: 검색칸도 타이핑하지 않고 클립보드로 붙여넣는다.
                if not _type_vendor_code(vendor_code, label, interval=type_interval):
                    self.logger.warning(
                        f"  [MGMT-XY] {label}: 거래처ds 검색칸 입력 실패"
                    )
                    return False
                _release_modifiers(f"{label} 거래처번호 붙여넣기 후", wait=False)
                time.sleep(max(0.25, float(settle_wait)))
                self.logger.info(
                    f"  [MGMT-XY] {label}: 거래처ds 검색칸 붙여넣기 완료: "
                    f"{vendor_code}"
                )
                return True

            def _seed_vendor_by_number_f9(x, y, label, vendor_code):
                try:
                    # 재정 미지급금 첫 행은 ERP에서 확인한 키보드 흐름만 사용한다.
                    # 관리항목값 셀 1회 클릭 -> F9 -> 거래처번호 ->
                    # Tab 4 -> Down 5 -> Up 2 -> Tab 3 -> Enter 2.
                    _click_form_xy(x, y, f"{label} 관리항목값", wait=mgmt_click_wait)
                    _release_modifiers(f"{label} F9 직전", wait=False)
                    time.sleep(mgmt_focus_wait)
                    base_process_id = 0
                    if not skip_visible_row_scan:
                        base_hwnd, base_title = _foreground_window_title()
                        base_process_id = _window_process_id(base_hwnd)
                        if _is_vendor_ds_title(base_title):
                            self.logger.warning(
                                f"  [MGMT-XY] {label}: F9 전부터 거래처ds가 열려 있어 입력을 중단합니다."
                            )
                            return False
                    # 거래처ds는 같은 ERP 프로세스의 별도 최상위 창으로 본창 뒤에
                    # 열릴 수 있다. UIA 자손 탐색 없이 HWND만 앞으로 가져온 뒤
                    # 사용자가 확인한 F9 키보드 시퀀스를 그대로 수행한다.
                    # 비-fast 경로의 기존 팝업 검증은 그대로 유지한다.
                    f9_open_wait = max(
                        1.0,
                        vendor_popup_open_wait,
                        float(os.getenv("ERP_MGMT_F9_OPEN_WAIT", "3.00") or "3.00"),
                    )
                    f9_search_wait = max(
                        vendor_popup_search_wait,
                        float(os.getenv("ERP_MGMT_F9_SEARCH_WAIT", "2.00") or "2.00"),
                    )
                    f9_key_interval = max(
                        0.12,
                        float(os.getenv("ERP_MGMT_F9_KEY_INTERVAL", "0.18") or "0.18"),
                    )
                    f9_group_wait = max(
                        mgmt_key_wait,
                        float(os.getenv("ERP_MGMT_F9_GROUP_WAIT", "0.35") or "0.35"),
                    )
                    f9_enter_interval = max(
                        0.20,
                        float(os.getenv("ERP_MGMT_F9_ENTER_INTERVAL", "0.40") or "0.40"),
                    )
                    pyautogui.press('f9')
                    if skip_visible_row_scan:
                        # 운영 fast 경로는 F9 뒤 창 제목/UIA 판정을 하지 않는다.
                        # ERP에서 확인된 고정 대기 뒤 사용자가 지정한 키 순서를 그대로 보낸다.
                        time.sleep(f9_open_wait)
                    else:
                        opened_hwnd, _opened_title = _wait_vendor_ds_foreground(
                            base_process_id,
                            f9_open_wait,
                        )
                        if not opened_hwnd:
                            self.logger.warning(f"  [MGMT-XY] {label}: F9 후 거래처ds 화면 미검출")
                            return False
                        time.sleep(vendor_popup_focus_wait)
                    if not _replace_vendor_ds_search_text(
                        vendor_code,
                        label,
                        min(f9_search_wait, 0.50),
                    ):
                        self.logger.warning(
                            f"  [MGMT-XY] {label}: 거래처ds 검색칸에 거래처번호가 "
                            "입력되지 않아 키 이동 전에 중단합니다."
                        )
                        return False
                    time.sleep(f9_search_wait)
                    pyautogui.press('tab', presses=4, interval=f9_key_interval)
                    time.sleep(f9_group_wait)
                    pyautogui.press('down', presses=5, interval=f9_key_interval)
                    time.sleep(f9_group_wait)
                    pyautogui.press('up', presses=2, interval=f9_key_interval)
                    time.sleep(f9_group_wait)
                    pyautogui.press('tab', presses=3, interval=f9_key_interval)
                    time.sleep(f9_group_wait)
                    pyautogui.press('enter', presses=2, interval=f9_enter_interval)
                    time.sleep(ERP_FORM_WAIT)
                    self.logger.info(
                        f"  [MGMT-XY] {label}: F9 거래처번호 키보드 시퀀스 완료"
                        f"(Tab 4, Down 5, Up 2, Tab 3, Enter 2): {vendor_code}"
                    )
                    return True
                except Exception as exc:
                    self.logger.warning(f"  [MGMT-XY] {label}: F9 거래처번호 입력 실패: {exc}")
                    return False

            def _input_finance_vendor_code_xy(
                x,
                y,
                vendor_code,
                label,
                paste_settle_wait,
                commit_settle_wait,
            ):
                vendor_code = str(vendor_code or "").strip()
                if not vendor_code.isascii() or not re.fullmatch(
                    r"[A-Za-z0-9_-]+", vendor_code
                ):
                    self.logger.warning(
                        f"  [MGMT-XY] {label}: 키보드 입력 불가 거래처번호: "
                        f"{vendor_code!r}"
                    )
                    return False
                # 새 행의 관리항목값 셀은 비어 있어야 한다. 편집 상태의 셀은
                # 글자가 선택 반전으로 그려져 잉크가 잡히지 않을 수 있으므로
                # 셀을 클릭하기 전(표시 상태)에 검사한다. 이전 행 값이 남아
                # 보이면 전표 행이 이동하지 않은 것이므로 즉시 중단한다.
                pre_ink = _management_value_visual_ink(x, y)
                if (
                    pre_ink[0] >= 6
                    and pre_ink[1] >= 3
                    and pre_ink[2] >= 3
                    and pre_ink[3] >= 8
                ):
                    self.logger.warning(
                        f"  [MGMT-XY] {label}: 클릭 전 관리항목값 셀이 비어 있지 "
                        f"않아 중단합니다(전표 행 미이동 의심, ink={pre_ink})."
                    )
                    return False
                _click_form_xy(x, y, label, wait=mgmt_click_wait)
                _release_modifiers(f"{label} 클릭 후", wait=False)
                time.sleep(max(0.20, mgmt_focus_wait))
                type_interval = max(
                    0.10,
                    float(os.getenv("ERP_MGMT_VENDOR_TYPE_INTERVAL", "0.15") or "0.15"),
                )
                if not _type_vendor_code(
                    vendor_code,
                    label,
                    interval=type_interval,
                ):
                    return False
                _release_modifiers(f"{label} 거래처번호 키보드 입력 후", wait=False)
                time.sleep(max(0.25, float(paste_settle_wait)))
                # 사용자 확정 흐름: 거래처번호 입력 → F9 → Enter.
                # F9가 입력된 번호로 거래처 조회를 명시적으로 실행하게 한 뒤
                # Enter로 확정한다.
                pyautogui.press('f9')
                f9_wait = max(
                    0.35,
                    float(os.getenv("ERP_FINANCE_VENDOR_F9_WAIT", "1.00") or "1.00"),
                )
                time.sleep(f9_wait)
                pyautogui.press('enter')
                time.sleep(max(mgmt_key_wait, float(commit_settle_wait)))
                return True

            def _input_vendor_by_number_keyboard(x, y, label, vendor_code):
                return _input_vendor_by_popup_keyboard(x, y, label, vendor_code, "거래처번호", 2)

            def _find_internal_bank_account_popup():
                """Find the 계좌 selector when K-System hosts it inside the ERP MDI."""
                try:
                    descendants = main_win.descendants()
                except Exception as exc:
                    self.logger.debug(
                        f"  [MGMT-BANK] 내부 계좌 팝업 UIA 탐색 실패: {exc}"
                    )
                    return None

                title_controls = []
                marker_controls = []
                marker_names = {
                    _norm_text("계좌번호"),
                    _norm_text("계좌명"),
                    _norm_text("금융기관지점명"),
                    _norm_text("계정과목"),
                    _norm_text("계정코드"),
                }
                seen_markers = set()
                for ctrl in descendants:
                    try:
                        if not ctrl.is_visible():
                            continue
                        values = _direct_vendor_popup_text(ctrl)
                        if any(value == _norm_text("계좌") for value in values):
                            title_controls.append(ctrl)
                        for value in values:
                            if value in marker_names:
                                seen_markers.add(value)
                                marker_controls.append(ctrl)
                    except Exception:
                        continue

                required_headers = {
                    _norm_text("계좌번호"),
                    _norm_text("계좌명"),
                    _norm_text("금융기관지점명"),
                }
                if not title_controls and not required_headers.issubset(seen_markers):
                    return None

                main_rect = _main_rect()
                min_width = max(500, int(main_rect.width() * 0.35))
                min_height = max(250, int(main_rect.height() * 0.25))
                candidates = []
                for ctrl in title_controls + marker_controls:
                    current = ctrl
                    for _ in range(10):
                        try:
                            rect = current.rectangle()
                            inside_main = (
                                rect.left >= main_rect.left - 5
                                and rect.top >= main_rect.top - 5
                                and rect.right <= main_rect.right + 5
                                and rect.bottom <= main_rect.bottom + 5
                            )
                            if (
                                inside_main
                                and rect.width() >= min_width
                                and rect.height() >= min_height
                            ):
                                candidates.append(
                                    (rect.width() * rect.height(), current, rect)
                                )
                            parent = current.parent()
                            if parent is None:
                                break
                            current = parent
                        except Exception:
                            break

                seen_candidates = set()
                for _, root, popup_rect in sorted(candidates, key=lambda item: item[0]):
                    candidate_key = (
                        _vendor_control_identity(root),
                        popup_rect.left,
                        popup_rect.top,
                        popup_rect.right,
                        popup_rect.bottom,
                    )
                    if candidate_key in seen_candidates:
                        continue
                    seen_candidates.add(candidate_key)
                    nearly_main_window = (
                        abs(popup_rect.left - main_rect.left) <= 12
                        and abs(popup_rect.top - main_rect.top) <= 12
                        and popup_rect.width() >= int(main_rect.width() * 0.95)
                        and popup_rect.height() >= int(main_rect.height() * 0.90)
                    )
                    if nearly_main_window:
                        continue
                    popup = _vendor_popup_context(
                        root,
                        popup_rect,
                        "bank-account-internal-uia",
                    )
                    edits = _visible_vendor_popup_controls(
                        popup,
                        "Edit",
                        top_band=True,
                    )
                    combos = _visible_vendor_popup_controls(
                        popup,
                        "ComboBox",
                        top_band=True,
                    )
                    if edits and (combos or title_controls):
                        return popup
                return None

            def _find_bank_account_popup(timeout=3.0):
                """Find the ERP account selector opened from the 계좌번호 item."""
                deadline = time.time() + max(0.0, float(timeout))
                expected_pid = int(getattr(self, "erp_process_pid", 0) or 0)
                internal_scanned = False
                while True:
                    try:
                        for win in Desktop(backend="uia").windows():
                            try:
                                title = re.sub(r"\s+", "", str(win.window_text() or ""))
                                if title != "계좌" or not win.is_visible():
                                    continue
                                pid = 0
                                try:
                                    pid = int(win.process_id() or 0)
                                except Exception:
                                    try:
                                        pid = int(win.element_info.process_id or 0)
                                    except Exception:
                                        pid = 0
                                if expected_pid and pid and pid != expected_pid:
                                    continue
                                rect = win.rectangle()
                                if rect.width() < 500 or rect.height() < 250:
                                    continue
                                popup = _vendor_popup_context(
                                    win,
                                    rect,
                                    "bank-account-top-level",
                                )
                                self.logger.info(
                                    "  [MGMT-BANK] 계좌 선택 팝업 감지: "
                                    f"source=bank-account-top-level, pid={pid}, "
                                    f"rect=({rect.left},{rect.top})-"
                                    f"({rect.right},{rect.bottom})"
                                )
                                return popup
                            except Exception:
                                continue
                    except Exception:
                        pass
                    if not internal_scanned:
                        popup = _find_internal_bank_account_popup()
                        internal_scanned = True
                        if popup is not None:
                            popup_rect = _vendor_popup_rect(popup)
                            self.logger.info(
                                "  [MGMT-BANK] 계좌 선택 팝업 감지: "
                                "source=bank-account-internal-uia, "
                                f"rect=({popup_rect.left},{popup_rect.top})-"
                                f"({popup_rect.right},{popup_rect.bottom})"
                            )
                            return popup
                    if time.time() >= deadline:
                        return None
                    time.sleep(0.10)

            def _wait_bank_account_popup_closed(timeout=3.0):
                deadline = time.time() + max(0.2, float(timeout))
                consecutive_misses = 0
                while time.time() < deadline:
                    if _find_bank_account_popup(timeout=0.0) is None:
                        consecutive_misses += 1
                        if consecutive_misses >= 2:
                            return True
                    else:
                        consecutive_misses = 0
                    time.sleep(0.12)
                return False

            def _bank_account_result_target(popup, account_no, branch_name):
                """Return an exact result-cell point, or a verified first-row fallback."""
                popup_rect = _vendor_popup_rect(popup)
                target_digits = re.sub(r"[^0-9]", "", str(account_no or ""))
                branch_norm = _norm_text(branch_name)
                account_hits = []
                branch_hits = []
                for ctrl in _visible_vendor_popup_controls(popup):
                    try:
                        rect = ctrl.rectangle()
                        if rect.top <= popup_rect.top + 120:
                            continue
                        values = _direct_vendor_popup_text(ctrl)
                        joined = " ".join(values)
                        digits = re.sub(r"[^0-9]", "", joined)
                        normalized = _norm_text(joined)
                        center_y = (rect.top + rect.bottom) // 2
                        center_x = (rect.left + rect.right) // 2
                        if target_digits and target_digits in digits:
                            account_hits.append((center_y, center_x, rect, joined))
                        if branch_norm and branch_norm in normalized:
                            branch_hits.append((center_y, center_x, rect, joined))
                    except Exception:
                        continue

                for account_hit in account_hits:
                    account_y = int(account_hit[0])
                    if not branch_norm or any(
                        abs(int(branch_hit[0]) - account_y) <= 12
                        for branch_hit in branch_hits
                    ):
                        return int(account_hit[1]), account_y, "exact-uia"

                # Some K-System result grids paint text through GDI and expose no
                # value cells to UIA.  The search condition is the exact unique
                # account number, so accept the first row only when its data area
                # visibly contains dark text.  Exclude the row-header 'A' column.
                try:
                    row_left = popup_rect.left + 48
                    # Header text ends around popup_top+183.  Scan only the first
                    # data row so an empty result grid cannot pass on header ink.
                    row_top = popup_rect.top + 184
                    row_width = max(1, popup_rect.width() - 210)
                    row_height_px = 20
                    image = pyautogui.screenshot(
                        region=(row_left, row_top, row_width, row_height_px)
                    )
                    ink_pixels = 0
                    for sample_y in range(2, max(2, image.size[1] - 2)):
                        for sample_x in range(2, max(2, image.size[0] - 2), 2):
                            r, g, b = image.getpixel((sample_x, sample_y))[:3]
                            if max(r, g, b) < 125:
                                ink_pixels += 1
                    if ink_pixels >= 10:
                        return (
                            popup_rect.left + 140,
                            popup_rect.top + 194,
                            f"exact-search-first-row-ink:{ink_pixels}",
                        )
                except Exception as exc:
                    self.logger.debug(
                        f"  [MGMT-BANK] 계좌 검색 첫 행 화면 검증 실패: {exc}"
                    )
                return None

            def _input_bank_account_by_popup(
                x,
                y,
                account_no,
                branch_name,
                label,
            ):
                account_no = str(account_no or "").strip()
                branch_name = str(branch_name or "").strip()
                if not account_no:
                    raise RuntimeError("보통예금 계좌번호가 비어 있어 계좌 선택을 중단합니다.")

                # The ERP user can persist any one of the three account search
                # conditions.  Force F9 and normalize it to 계좌번호 every time.
                f9_open_wait = max(
                    1.0,
                    vendor_popup_open_wait,
                    float(os.getenv("ERP_MGMT_BANK_F9_OPEN_WAIT", "2.00") or "2.00"),
                )
                f9_search_wait = max(
                    vendor_popup_search_wait,
                    float(os.getenv("ERP_MGMT_BANK_F9_SEARCH_WAIT", "2.00") or "2.00"),
                )
                f9_key_interval = max(
                    0.12,
                    float(os.getenv("ERP_MGMT_BANK_F9_KEY_INTERVAL", "0.18") or "0.18"),
                )
                f9_group_wait = max(
                    mgmt_key_wait,
                    float(os.getenv("ERP_MGMT_BANK_F9_GROUP_WAIT", "0.35") or "0.35"),
                )
                f9_enter_interval = max(
                    0.20,
                    float(os.getenv("ERP_MGMT_BANK_F9_ENTER_INTERVAL", "0.40") or "0.40"),
                )

                _click_form_xy(x, y, f"{label} 관리항목값", wait=mgmt_click_wait)
                _release_modifiers(f"{label} F9 직전", wait=False)
                time.sleep(mgmt_focus_wait)
                pyautogui.press("f9")
                time.sleep(f9_open_wait)

                bank_account_popup_state["opened"] = True
                bank_account_popup_state["closed"] = False
                bank_account_popup_state["source"] = "bank-account-f9-command"
                self.logger.info(
                    f"  [MGMT-BANK] {label}: F9 후 {f9_open_wait:.2f}초 대기 완료; "
                    "계좌번호 입력과 고정 키보드 시퀀스를 바로 실행합니다."
                )
                type_interval = max(
                    0.10,
                    float(os.getenv("ERP_MGMT_BANK_TYPE_INTERVAL", "0.10") or "0.10"),
                )
                if not account_no.isascii() or not re.fullmatch(r"[0-9-]+", account_no):
                    raise RuntimeError(
                        f"{label} 계좌번호 형식이 숫자/하이픈이 아닙니다: {account_no!r}"
                    )
                _release_modifiers(f"{label} 계좌번호 붙여넣기 직전", wait=False)
                # 사용자 지시: 계좌번호도 타이핑하지 않고 클립보드로 붙여넣는다.
                if not _type_vendor_code(account_no, label, interval=type_interval):
                    raise RuntimeError(
                        f"{label} 계좌 팝업 검색칸에 계좌번호를 입력하지 못했습니다."
                    )
                _release_modifiers(f"{label} 계좌번호 붙여넣기 후", wait=False)
                time.sleep(max(0.25, min(f9_search_wait, 0.50)))
                self.logger.info(
                    f"  [MGMT-BANK] {label}: 계좌번호 붙여넣기 완료: "
                    f"{account_no}"
                )
                time.sleep(f9_search_wait)

                self.logger.info(
                    f"  [MGMT-BANK] {label}: F9 계좌번호 키보드 시퀀스 시작"
                    "(Tab 4 → Up 2 → Tab 3 → Enter 2)"
                )
                pyautogui.press("tab", presses=4, interval=f9_key_interval)
                time.sleep(f9_group_wait)
                pyautogui.press("up", presses=2, interval=f9_key_interval)
                time.sleep(f9_group_wait)
                pyautogui.press("tab", presses=3, interval=f9_key_interval)
                time.sleep(f9_group_wait)
                # 실기기 확인: 첫 Enter는 조회만 실행하고 선택 팝업이 열린 채
                # 남는다. 거래처ds와 동일하게 두 번째 Enter로 결과행을 확정한다.
                pyautogui.press("enter", presses=2, interval=f9_enter_interval)
                time.sleep(ERP_FORM_WAIT)

                pitch = max(10, int(os.getenv("ERP_MGMT_ROW_HEIGHT", "20") or "20"))
                branch_metrics = (0, 0, 0, 0)
                branch_confirmed = False
                for _ in range(8):
                    branch_metrics = _management_value_visual_ink(x, y + pitch)
                    ink_pixels, ink_rows, ink_columns, ink_span = branch_metrics
                    if (
                        ink_pixels >= 6
                        and ink_rows >= 3
                        and ink_columns >= 3
                        and ink_span >= 8
                    ):
                        branch_confirmed = True
                        break
                    time.sleep(0.25)
                if branch_name and not branch_confirmed:
                    raise RuntimeError(
                        f"{label} 선택 후 금융기관지점 자동입력 화면을 확인하지 못했습니다."
                    )
                bank_account_popup_state["closed"] = True
                self.logger.info(
                    f"  [MGMT-BANK] {label}: F9 계좌번호 선택·팝업 종료·"
                    "금융기관지점 자동입력 확인 "
                    f"(account={account_no}, branch={branch_name}, ink={branch_metrics})"
                )
                time.sleep(max(0.50, mgmt_commit_wait))
                return True

            def _input_vendor_value_xy(x, y, label):
                if not vendor_name and not vendor_target_biz_no:
                    return
                if is_special_vendor_keyboard and vendor_target_biz_no:
                    if _input_vendor_by_business_no_keyboard(x, y, label, vendor_target_biz_no):
                        return
                    if vendor_name:
                        self.logger.warning(
                            f"  [MGMT-XY] {label}: 사업자번호 팝업 진입 실패, 기존 거래처명 입력 fallback: {vendor_name}"
                        )
                        _input_value_xy(x, y, vendor_name, label, enter_count=1, clear=True)
                    return
                if vendor_target_biz_no:
                    target_biz_no = vendor_target_biz_no
                    _input_value_xy(x, y, target_biz_no, label, enter_count=0, clear=True)
                    pyautogui.press('enter')
                    time.sleep(ERP_FORM_WAIT)
                    picked = False
                    popup_seen = False
                    try:
                        target_digits = re.sub(r"[^0-9]", "", target_biz_no)
                        for _popup_try in range(12):
                            for win in Desktop(backend="uia").windows():
                                try:
                                    title = win.window_text() or ""
                                    if "거래처" not in title:
                                        continue
                                    popup_seen = True
                                    win_rect = win.rectangle()
                                    for cell in win.descendants():
                                        try:
                                            cell_text = (cell.window_text() or "").strip()
                                            cell_digits = re.sub(r"[^0-9]", "", cell_text)
                                            if (
                                                target_biz_no not in cell_text
                                                and cell_text != target_biz_no
                                                and (not target_digits or target_digits not in cell_digits)
                                                and cell_digits != target_digits
                                            ):
                                                continue
                                            rect = cell.rectangle()
                                            row_y = rect.top + rect.height() // 2
                                            row_x = min(max(win_rect.left + 90, win_rect.left + 20), win_rect.right - 20)
                                            pyautogui.click(row_x, row_y)
                                            time.sleep(ERP_CLICK_WAIT)
                                            pyautogui.doubleClick(row_x, row_y, interval=0.05)
                                            time.sleep(ERP_CLICK_WAIT)
                                            pyautogui.press('enter')
                                            picked = True
                                            self.logger.info(
                                                f"  [MGMT-XY] {label}: 거래처 사업자번호 {target_biz_no} 행 선택"
                                            )
                                            break
                                        except Exception:
                                            pass
                                    if picked:
                                        break
                                except Exception:
                                    pass
                            if picked or popup_seen:
                                break
                            time.sleep(0.15)
                    except Exception as e:
                        self.logger.warning(f"  [MGMT-XY] {label}: 거래처 사업자번호 행 탐색 실패: {e}")
                    if not picked:
                        if vendor_target_optional:
                            self.logger.warning(
                                f"  [MGMT-XY] {label}: special vendor business no {target_biz_no} not found; PASS"
                            )
                            if popup_seen:
                                pyautogui.press('esc')
                            time.sleep(ERP_FORM_WAIT)
                            return
                        self.logger.warning(
                            f"  [MGMT-XY] {label}: 거래처 사업자번호 {target_biz_no} 미검출, 사업자번호 입력 후 Enter fallback"
                        )
                        pyautogui.press('enter')
                    time.sleep(ERP_FORM_WAIT)
                    return
                _input_value_xy(x, y, vendor_name, label, enter_count=1, clear=True)

            def _fill_explicit_management_items():
                management_enter_sent = False
                management_active_row_context["row_no"] = row_no
                if str(form_data.get('cash_processing_enabled', '')).strip().lower() not in ("1", "true", "yes", "on"):
                    _uncheck_cash_processing(row_no)
                explicit_key_norms = {_norm_text(key) for key in explicit_management.keys()}
                bank_required = {
                    _norm_text("계좌번호"),
                    _norm_text("금융기관지점"),
                }
                if explicit_key_norms & bank_required:
                    if row_no in management_bank_coordinate_fallback_rows:
                        self.logger.warning(
                            f"  [MGMT-XY] {row_no}행 보통예금은 계정과목 검증과 빠른 좌표 준비가 "
                            "완료되어 전체 UIA 라벨 탐색을 생략합니다."
                        )
                    else:
                        snapshot = _management_grid_snapshot()
                        visible_labels = snapshot.get("label_norms") or set()
                        missing = [label for label in bank_required if label not in visible_labels]
                        if missing:
                            raise RuntimeError(
                                f"{row_no}행 보통예금 관리항목이 표시되지 않아 계좌번호 입력을 중단합니다. "
                                f"visible_labels={snapshot.get('labels')}"
                            )
                normalized_explicit = {
                    _norm_text(key): str(value or "").strip()
                    for key, value in explicit_management.items()
                }
                bank_account_value = normalized_explicit.get(
                    _norm_text("계좌번호"),
                    "",
                )
                bank_branch_value = normalized_explicit.get(
                    _norm_text("금융기관지점"),
                    "",
                )
                bank_selected = False
                if explicit_key_norms & bank_required:
                    if not bank_account_value:
                        raise RuntimeError(
                            f"{row_no}행 보통예금 계좌번호가 없어 금융기관지점 자동입력을 진행할 수 없습니다."
                        )
                    account_x, account_y = _management_value_xy("계좌번호", 797)
                    _input_bank_account_by_popup(
                        account_x,
                        account_y,
                        bank_account_value,
                        bank_branch_value,
                        f"{row_no}행 계좌번호",
                    )
                    bank_selected = True
                y = 797
                for item_name, item_value in explicit_management.items():
                    item_norm = _norm_text(item_name)
                    if bank_selected and item_norm in bank_required:
                        self.logger.info(
                            f"  [MGMT-BANK] {row_no}행 {item_name}: "
                            "계좌 선택으로 계좌번호/금융기관지점이 함께 확정되어 직접 입력을 생략합니다."
                        )
                        y += 20
                        continue
                    text = str(item_value or "").strip()
                    if not text:
                        self.logger.info(f"  [MGMT-XY] {row_no}행 {item_name} 값 없음: 스킵")
                        y += 20
                        continue
                    value_x, value_y = _management_value_xy(item_name, y)
                    item_key = re.sub(r"\s+", "", str(item_name or "")).lower()
                    if item_key in ("거래처", "거래처코드", "업체코드", "vendor", "vendor_code"):
                        label = f"{row_no}행 {item_name}"
                        if account_key == "미지급금(원화)":
                            if not finance_vendor_entry_state["f9_seeded"]:
                                if not _seed_vendor_by_number_f9(value_x, value_y, label, text):
                                    raise RuntimeError(
                                        f"{row_no}행 거래처번호 F9 키보드 입력에 실패했습니다."
                                    )
                                finance_vendor_entry_state["f9_seeded"] = True
                                self.logger.info(
                                    f"  [MGMT-XY] {label}: 최초 F9 키보드 입력 완료, 이후 행 직접 입력 전환"
                                )
                            else:
                                if not _input_finance_vendor_code_xy(
                                    value_x,
                                    value_y,
                                    text,
                                    label,
                                    finance_vendor_paste_settle_wait,
                                    finance_vendor_commit_settle_wait,
                                ):
                                    raise RuntimeError(
                                        f"{row_no}행 거래처번호 직접 키보드 입력에 실패했습니다."
                                    )
                                management_enter_sent = True
                                self.logger.info(
                                    f"  [MGMT-XY] {label}: 관리항목값 셀 키보드 입력 후 Enter 완료"
                                    f"(입력대기 {finance_vendor_paste_settle_wait:.2f}s, "
                                    f"Enter 확정 {finance_vendor_commit_settle_wait:.2f}s): {text}"
                                )
                            y += 20
                            continue
                        if _input_vendor_by_number_keyboard(value_x, value_y, label, text):
                            y += 20
                            continue
                        self.logger.warning(
                            f"  [MGMT-XY] {label}: 거래처번호 팝업 입력 실패, 직접 입력 fallback: {text}"
                        )
                    _input_value_xy(value_x, value_y, text, f"{row_no}행 {item_name}", enter_count=1, clear=True)
                    y += 20
                self.logger.info(f"  [MGMT-XY] {row_no}행 명시 관리항목 입력 완료: {list(explicit_management.keys())}")
                return management_enter_sent

            if "explicit" in plan:
                return bool(_fill_explicit_management_items())

            if account_key == "부가세대급금" and corp == "일강":
                if "vendor_vat" in plan:
                    _input_vendor_value_xy(1118, 797, f"{row_no}행 거래처")
                if "supply" in plan and supply_amount:
                    _input_value_xy(1118, 817, supply_amount, f"{row_no}행 공급가액", enter_count=0, clear=True)
                if "date" in plan:
                    _input_value_xy(1118, 837, invoice_date, f"{row_no}행 거래일", enter_count=0, clear=True)
                if "business" in plan and business_query:
                    _input_value_xy(1118, 857, business_query, f"{row_no}행 사업자번호", enter_count=1, clear=True)
                self.logger.info(f"  [MGMT-XY] {row_no}행 일강 부가세대급금 관리항목 입력 완료")
                return False

            if "project" in plan:
                # 일강 집기비품: 거래처 다음 줄(프로젝트코드)에 "일반"을 입력합니다.
                _input_value_xy(1118, 817, "일반", f"{row_no}행 프로젝트코드", enter_count=1, clear=True)

            if "date" in plan:
                _input_value_xy(1118, 797, invoice_date, f"{row_no}행 거래일/관리일", enter_count=0, clear=True)

            if "vendor_vat" in plan and (vendor_name or vendor_target_biz_no):
                _input_vendor_value_xy(1118, 817, f"{row_no}행 거래처")

            if "vendor" in plan and (vendor_name or vendor_target_biz_no):
                _input_vendor_value_xy(1118, 797, f"{row_no}행 거래처")

            if "supply" in plan and supply_amount:
                _input_value_xy(1118, 837, supply_amount, f"{row_no}행 공급가액", enter_count=0, clear=True)

            if "business" in plan and business_query:
                _input_value_xy(1118, 857, business_query, f"{row_no}행 사업자번호", enter_count=1, clear=True)

            self.logger.info(f"  [MGMT-XY] {row_no}행 관리항목 입력 완료")
            return False

        def _fill_management_items_by_coord():
            erp_rows = form_data.get('erp_clipboard_rows') or []
            line_management_items = form_data.get('erp_line_management_items') or form_data.get('line_management_items') or []
            rows_to_fill = max(0, int(form_data.get('erp_row_count') or len(erp_rows) or row_count))
            self.logger.info(f"  [MGMT-XY] 행별 적요/관리항목 좌표 입력 시작: rows={rows_to_fill}")
            summary_x = int(os.getenv("ERP_MGMT_SUMMARY_X", "970") or "970")
            first_row_y = int(os.getenv("ERP_MGMT_FIRST_ROW_Y", "231") or "231")
            row_height = max(10, int(os.getenv("ERP_MGMT_ROW_HEIGHT", "20") or "20"))
            sequential_nav = _env_flag("ERP_MGMT_SEQUENTIAL_NAV", "1")
            account_x = int(os.getenv("ERP_MGMT_ACCOUNT_X", "229") or "229")
            row_number_x = int(os.getenv("ERP_MGMT_ROW_NUMBER_X", "112") or "112")

            def _median_number(values, fallback):
                ordered = sorted(float(value) for value in values)
                if not ordered:
                    return float(fallback)
                middle = len(ordered) // 2
                if len(ordered) % 2:
                    return ordered[middle]
                return (ordered[middle - 1] + ordered[middle]) / 2.0

            def _fast_visible_voucher_row_snapshot(expected_row_no=None):
                """Build live 24/26-row geometry without enumerating the full UIA tree."""
                try:
                    main_rect = _main_rect()
                    boundary_candidates = []
                    boundary_source = "ready-snapshot"
                    ready_snapshot = management_grid_ready_state.get("snapshot") or {}
                    for key in ("header_label", "header_value"):
                        row = ready_snapshot.get(key)
                        rect = row.get("rect") if isinstance(row, dict) else None
                        if rect is not None:
                            center_x = ((rect.left + rect.right) // 2) - main_rect.left
                            rel_top = rect.top - main_rect.top
                            if 500 <= center_x <= 1250 and rel_top > first_row_y + (row_height * 3):
                                boundary_candidates.append(int(rect.top))

                    header_boundary_found = bool(boundary_candidates)
                    viewport_boundary = ready_snapshot.get("voucher_clip_bottom_abs")
                    if viewport_boundary is not None:
                        viewport_rel_bottom = int(viewport_boundary) - main_rect.top
                        if viewport_rel_bottom > first_row_y + (row_height * 3):
                            boundary_candidates.append(int(viewport_boundary))
                            boundary_source = (
                                "ready-header-viewport-snapshot"
                                if header_boundary_found
                                else "ready-viewport-snapshot"
                            )

                    # The upload-ready check normally captured both management headers.
                    # UIA text can be absent even when the pixel verification succeeded,
                    # so the already captured SS_Row viewport is the only fallback. Never
                    # run a new full UIA walk here; that recreates the 210-row hang.

                    if not boundary_candidates:
                        self.logger.warning(
                            "  [MGMT-XY] 빠른 UIA 경계 탐색에서 관리항목 헤더를 찾지 못했습니다."
                        )
                        return None

                    clip_bottom = min(boundary_candidates) - main_rect.top
                    pitch = max(1, int(row_height))
                    first_y = int(first_row_y)
                    guard = max(
                        1.0,
                        float(os.getenv("ERP_MGMT_FULL_ROW_BOTTOM_GUARD", "2") or "2"),
                    )
                    usable_height = float(clip_bottom) - guard - first_y - (pitch / 2.0)
                    last_offset = int(usable_height // pitch)
                    if last_offset < 0:
                        self.logger.warning(
                            "  [MGMT-XY] 빠른 UIA 경계가 첫 전표 행보다 위에 있어 사용할 수 없습니다: "
                            f"clip_bottom={clip_bottom}, first_y={first_y}, pitch={pitch}"
                        )
                        return None

                    visible_count = last_offset + 1
                    max_visible_count = max(
                        1,
                        ((main_rect.bottom - main_rect.top) // pitch) + 1,
                    )
                    if visible_count > max_visible_count:
                        self.logger.warning(
                            "  [MGMT-XY] 빠른 UIA 경계의 표시 행 수가 화면 높이를 초과합니다: "
                            f"visible_count={visible_count}, max={max_visible_count}"
                        )
                        return None
                    slot_ys = [first_y + (slot * pitch) for slot in range(visible_count)]
                    scroll_anchor_index = max(0, len(slot_ys) - 2)
                    logical_first = 1
                    named_rows = {
                        logical_first + slot: relative_y
                        for slot, relative_y in enumerate(slot_ys)
                    }
                    management_value_ys = [
                        int(row.get("rel_y"))
                        for row in (ready_snapshot.get("items") or [])
                        if row.get("rel_y") is not None
                    ]
                    management_value_y = min(management_value_ys) if management_value_ys else None
                    if management_value_y is None:
                        value_header = ready_snapshot.get("header_value") or {}
                        if value_header.get("rel_y") is not None:
                            management_value_y = int(value_header["rel_y"]) + pitch
                    snapshot = {
                        "rows": named_rows,
                        "slot_ys": slot_ys,
                        "first_y": slot_ys[0],
                        "last_full_y": slot_ys[-1],
                        "scroll_anchor_y": slot_ys[scroll_anchor_index],
                        "management_value_y": management_value_y,
                        "last_summary_raise": (
                            int(management_value_y) - int(slot_ys[-1])
                            if management_value_y is not None
                            else None
                        ),
                        "row_pitch": pitch,
                        "clip_bottom": int(clip_bottom),
                        "has_exact_row_numbers": False,
                        "has_logical_row_numbers": False,
                        "geometry_source": boundary_source,
                    }
                    self.logger.info(
                        "  [MGMT-XY] 빠른 UIA 완전 표시 행 스냅샷: "
                        f"source={boundary_source}, slots={visible_count}, "
                        f"first_y={snapshot['first_y']}, last_y={snapshot['last_full_y']}, "
                        f"management_value_y={snapshot['management_value_y']}, "
                        f"raise={snapshot['last_summary_raise']}, "
                        f"clip_bottom={snapshot['clip_bottom']}, logical={logical_first}.."
                        f"{logical_first + visible_count - 1}"
                    )
                    return snapshot
                except Exception as exc:
                    self.logger.warning(f"  [MGMT-XY] 빠른 UIA 완전 표시 행 스냅샷 실패: {exc}")
                    return None

            def _fully_visible_voucher_row_snapshot():
                """Return actual UIA row centers, excluding the clipped bottom row."""
                try:
                    main_rect = _main_rect()
                    controls = _iter_visible()
                    viewport_candidates = []
                    lower_pane_tops = []
                    horizontal_scrollbars = []

                    for ctrl in controls:
                        try:
                            control_type = str(ctrl.element_info.control_type or "")
                            automation_id = str(ctrl.element_info.automation_id or "")
                            rect = ctrl.rectangle()
                            width = rect.right - rect.left
                            height = rect.bottom - rect.top
                            rel_left = rect.left - main_rect.left
                            rel_top = rect.top - main_rect.top
                            rel_bottom = rect.bottom - main_rect.top

                            if (
                                control_type == "Custom"
                                and automation_id == "SS_Row"
                                and rel_left <= 180
                                and width >= 700
                                and height >= 120
                                and rel_top - row_height <= first_row_y <= rel_bottom
                            ):
                                viewport_candidates.append((height, -width, rect))

                            if control_type == "ScrollBar" and width >= max(300, height * 5):
                                if rel_top > first_row_y + (row_height * 3):
                                    horizontal_scrollbars.append(rect)

                            if control_type in ("Header", "HeaderItem", "Text", "Custom"):
                                text = _norm_text(_control_text(ctrl) or ctrl.window_text())
                                if text in (_norm_text("관리항목"), _norm_text("관리항목값")):
                                    center_x = ((rect.left + rect.right) // 2) - main_rect.left
                                    if 500 <= center_x <= 1250 and rel_top > first_row_y + (row_height * 3):
                                        lower_pane_tops.append(rect.top)
                        except Exception:
                            pass

                    viewport_rect = None
                    if viewport_candidates:
                        viewport_rect = sorted(viewport_candidates, key=lambda item: (item[0], item[1]))[0][2]

                    clip_bottom_candidates = []
                    if viewport_rect is not None:
                        clip_bottom_candidates.append(viewport_rect.bottom)
                    for scrollbar_rect in horizontal_scrollbars:
                        if viewport_rect is not None:
                            if (
                                scrollbar_rect.right <= viewport_rect.left
                                or scrollbar_rect.left >= viewport_rect.right
                                or scrollbar_rect.top > viewport_rect.bottom + row_height
                            ):
                                continue
                        clip_bottom_candidates.append(scrollbar_rect.top)
                    clip_bottom_candidates.extend(lower_pane_tops)
                    if not clip_bottom_candidates:
                        self.logger.warning("  [MGMT-XY] UIA 전표 그리드 하단 경계 미검출")
                        return None

                    clip_bottom = min(clip_bottom_candidates)
                    viewport_top = (
                        viewport_rect.top
                        if viewport_rect is not None
                        else main_rect.top + first_row_y - row_height
                    )
                    viewport_left = viewport_rect.left if viewport_rect is not None else main_rect.left
                    viewport_right = viewport_rect.right if viewport_rect is not None else main_rect.right - 200
                    raw_rows = []

                    for ctrl in controls:
                        try:
                            control_type = str(ctrl.element_info.control_type or "")
                            if control_type not in ("Text", "Custom", "DataItem"):
                                continue
                            rect = ctrl.rectangle()
                            center_x = (rect.left + rect.right) / 2.0
                            center_y = (rect.top + rect.bottom) / 2.0
                            height = rect.bottom - rect.top
                            if (
                                height <= 0
                                or height > max(50.0, row_height * 2.50)
                                or rect.right <= viewport_left
                                or rect.left >= viewport_right
                            ):
                                continue
                            if center_y < main_rect.top + first_row_y - row_height or rect.top >= clip_bottom:
                                continue

                            text = _norm_text(_control_text(ctrl) or ctrl.window_text())
                            row_no = None
                            row_source = None
                            if re.fullmatch(r"\d{3}", text or ""):
                                relative_center_x = center_x - main_rect.left
                                if not (0 <= relative_center_x <= 180):
                                    continue
                                row_no = int(text)
                                row_source = "label"
                            elif control_type == "DataItem":
                                try:
                                    grid_row = int(ctrl.iface_grid_item.CurrentRow)
                                    if grid_row >= 0:
                                        row_no = grid_row + 1
                                        row_source = "grid"
                                except Exception:
                                    row_no = None
                            else:
                                continue

                            raw_rows.append(
                                {
                                    "center_y": center_y,
                                    "height": float(height),
                                    "top": float(rect.top),
                                    "bottom": float(rect.bottom),
                                    "row_no": row_no,
                                    "row_source": row_source,
                                }
                            )
                        except Exception:
                            pass

                    if len(raw_rows) < 2:
                        self.logger.warning(
                            f"  [MGMT-XY] UIA 전표 행 마커 부족: count={len(raw_rows)}"
                        )
                        return None

                    cluster_tolerance = max(2.0, min(6.0, row_height * 0.30))
                    clusters = []
                    for item in sorted(raw_rows, key=lambda value: value["center_y"]):
                        if (
                            not clusters
                            or abs(item["center_y"] - clusters[-1]["center_y"]) > cluster_tolerance
                        ):
                            clusters.append(
                                {
                                    "items": [item],
                                    "center_y": item["center_y"],
                                }
                            )
                        else:
                            clusters[-1]["items"].append(item)
                            clusters[-1]["center_y"] = _median_number(
                                [value["center_y"] for value in clusters[-1]["items"]],
                                item["center_y"],
                            )

                    centers = [cluster["center_y"] for cluster in clusters]
                    pitch_candidates = [
                        current - previous
                        for previous, current in zip(centers, centers[1:])
                        if max(7.0, row_height * 0.45)
                        <= current - previous
                        <= max(40.0, row_height * 1.80)
                    ]
                    measured_pitch = _median_number(pitch_candidates, row_height)
                    cluster_heights = [
                        max(item["height"] for item in cluster["items"])
                        for cluster in clusters
                    ]
                    normal_height = _median_number(cluster_heights, measured_pitch * 0.80)
                    guard = max(
                        1.0,
                        float(os.getenv("ERP_MGMT_FULL_ROW_BOTTOM_GUARD", "2") or "2"),
                    )
                    min_height_ratio = min(
                        1.0,
                        max(
                            0.50,
                            float(os.getenv("ERP_MGMT_FULL_ROW_MIN_HEIGHT_RATIO", "0.80") or "0.80"),
                        ),
                    )
                    full_clusters = []
                    for cluster, cluster_height in zip(clusters, cluster_heights):
                        center_y = cluster["center_y"]
                        representative_top = min(item["top"] for item in cluster["items"])
                        representative_bottom = max(item["bottom"] for item in cluster["items"])
                        intersection_height = max(
                            0.0,
                            min(representative_bottom, float(clip_bottom))
                            - max(representative_top, float(viewport_top)),
                        )
                        if center_y + (measured_pitch / 2.0) > float(clip_bottom) - guard:
                            continue
                        if cluster_height < normal_height * min_height_ratio:
                            continue
                        if intersection_height < normal_height * min_height_ratio:
                            continue
                        full_clusters.append(cluster)

                    if not full_clusters:
                        self.logger.warning(
                            f"  [MGMT-XY] 완전 표시 전표 행 미검출: clip_bottom={clip_bottom}"
                        )
                        return None

                    slot_ys = [
                        int(round(cluster["center_y"] - main_rect.top))
                        for cluster in full_clusters
                    ]
                    named_rows = {}
                    exact_label_rows = set()
                    for cluster, relative_y in zip(full_clusters, slot_ys):
                        label_row_numbers = [
                            item["row_no"]
                            for item in cluster["items"]
                            if item.get("row_source") == "label" and item.get("row_no") is not None
                        ]
                        grid_row_numbers = [
                            item["row_no"]
                            for item in cluster["items"]
                            if item.get("row_source") == "grid" and item.get("row_no") is not None
                        ]
                        row_numbers = label_row_numbers or grid_row_numbers
                        if row_numbers:
                            named_rows[int(round(_median_number(row_numbers, row_numbers[0])))] = relative_y
                        exact_label_rows.update(int(value) for value in label_row_numbers)

                    snapshot = {
                        "rows": named_rows,
                        "slot_ys": slot_ys,
                        "first_y": slot_ys[0],
                        "last_full_y": slot_ys[-1],
                        "scroll_anchor_y": slot_ys[-2] if len(slot_ys) >= 2 else slot_ys[-1],
                        "row_pitch": max(1, int(round(measured_pitch))),
                        "clip_bottom": int(round(clip_bottom - main_rect.top)),
                        "has_exact_row_numbers": bool(exact_label_rows),
                        "has_logical_row_numbers": bool(named_rows),
                    }
                    self.logger.info(
                        f"  [MGMT-XY] UIA 완전 표시 행 스냅샷: slots={len(slot_ys)}, "
                        f"first_y={snapshot['first_y']}, last_y={snapshot['last_full_y']}, "
                        f"pitch={snapshot['row_pitch']}, named={sorted(named_rows)[:3]}.."
                        f"{sorted(named_rows)[-3:] if named_rows else []}"
                    )
                    return snapshot
                except Exception as exc:
                    self.logger.warning(f"  [MGMT-XY] UIA 완전 표시 행 스냅샷 실패: {exc}")
                    return None

            def _validate_initial_voucher_row_snapshot(snapshot):
                if not snapshot or not snapshot.get("slot_ys"):
                    _fail_form(
                        "전표 그리드의 완전히 표시된 마지막 행을 UIA로 확인하지 못해 "
                        "관리항목 입력을 중단합니다."
                    )
                if (
                    snapshot.get("has_logical_row_numbers")
                    and 1 not in (snapshot.get("rows") or {})
                ):
                    _fail_form(
                        "관리항목 입력 시작 전 UIA 전표 그리드에서 001행을 찾지 못했습니다. "
                        "스크롤 위치가 첫 행이 아니므로 입력을 중단합니다."
                    )
                return snapshot

            def _uia_voucher_row_number_at_y(
                desktop,
                relative_y,
                allow_grid_fallback=False,
                expected_row_nos=None,
            ):
                main_rect = _main_rect()
                absolute_y = main_rect.top + int(relative_y)
                x_offsets = (0, -8, 8, -16, 16)
                expected_rows = {
                    int(value)
                    for value in (expected_row_nos or set())
                    if int(value) > 0
                }
                label_candidates = []
                grid_candidates = []
                for x_offset in x_offsets:
                    try:
                        ctrl = desktop.from_point(
                            main_rect.left + int(row_number_x) + x_offset,
                            absolute_y,
                        )
                    except Exception:
                        continue
                    candidates = []
                    current = ctrl
                    for _ in range(4):
                        if current is None:
                            break
                        candidates.append(current)
                        try:
                            parent = current.parent()
                        except Exception:
                            parent = None
                        if parent is current:
                            break
                        current = parent
                    # The displayed row label is the real voucher row number. GridItem.Row
                    # is viewport-relative on this ERP grid after scrolling, so it must not
                    # win over a label such as "025".
                    for candidate_index, candidate in enumerate(candidates):
                        values = []
                        for getter in (
                            lambda candidate=candidate: candidate.element_info.name,
                            lambda candidate=candidate: candidate.window_text(),
                            lambda candidate=candidate: _control_text(candidate),
                            lambda candidate=candidate: candidate.iface_value.CurrentValue,
                        ):
                            try:
                                value = str(getter() or "").strip()
                            except Exception:
                                value = ""
                            if value:
                                values.append(value)
                        for value in values:
                            compact = re.sub(r"\s+", "", value)
                            # ERP displays voucher rows as at least three digits
                            # (001, 024, 230). Ignore short viewport-relative text.
                            if re.fullmatch(r"\d{3,6}", compact):
                                row_no = int(compact)
                                if 1 <= row_no <= max(rows_to_fill + len(initial_snapshot.get("slot_ys") or []), 1):
                                    label_candidates.append(
                                        (
                                            int(row_no in expected_rows),
                                            int(compact.startswith("0")),
                                            -int(candidate_index),
                                            row_no,
                                        )
                                    )
                    if allow_grid_fallback:
                        for candidate in candidates:
                            try:
                                grid_row = int(candidate.iface_grid_item.CurrentRow)
                                if grid_row >= 0:
                                    grid_candidates.append(grid_row + 1)
                            except Exception:
                                pass
                    if label_candidates:
                        return int(max(label_candidates)[3])
                if label_candidates:
                    return int(max(label_candidates)[3])
                if grid_candidates:
                    return int(grid_candidates[0])
                return None

            def _uia_voucher_row_selected_at_y(desktop, relative_y):
                main_rect = _main_rect()
                absolute_y = main_rect.top + int(relative_y)
                saw_unselected = False
                for x_offset in (0, -8, 8, -16, 16):
                    try:
                        current = desktop.from_point(
                            main_rect.left + int(row_number_x) + x_offset,
                            absolute_y,
                        )
                    except Exception:
                        continue
                    for _ in range(4):
                        if current is None:
                            break
                        try:
                            selected = bool(
                                current.iface_selection_item.CurrentIsSelected
                            )
                            if selected:
                                return True
                            saw_unselected = True
                        except Exception:
                            pass
                        try:
                            parent = current.parent()
                        except Exception:
                            parent = None
                        if parent is current:
                            break
                        current = parent
                return False if saw_unselected else None

            def _targeted_uia_voucher_rows(
                snapshot,
                target_row_nos,
                allow_grid_fallback=False,
            ):
                targets = {int(value) for value in (target_row_nos or set()) if int(value) > 0}
                rows = {}
                desktop = Desktop(backend="uia")
                slot_ys = [int(value) for value in (snapshot.get("slot_ys") or [])]
                for relative_y in reversed(slot_ys):
                    row_no = _uia_voucher_row_number_at_y(
                        desktop,
                        relative_y,
                        allow_grid_fallback=allow_grid_fallback,
                        expected_row_nos=targets,
                    )
                    if row_no is not None:
                        rows[int(row_no)] = int(relative_y)
                    if targets and targets.issubset(rows):
                        break
                self.logger.info(
                    "  [MGMT-XY] 좌표 지점 UIA 행번호 확인: "
                    f"targets={sorted(targets)}, rows={sorted(rows.items())}"
                )
                return rows

            def _initial_voucher_rows_with_geometry_fallback(
                snapshot,
                target_row_nos,
            ):
                """Keep validated viewport geometry when GDI hides row labels from UIA."""
                targets = {
                    int(value)
                    for value in (target_row_nos or set())
                    if int(value) > 0
                }
                targeted_rows = _targeted_uia_voucher_rows(
                    snapshot,
                    targets,
                    allow_grid_fallback=True,
                )
                merged_rows = {
                    int(row_no): int(relative_y)
                    for row_no, relative_y in (snapshot.get("rows") or {}).items()
                }
                merged_rows.update(
                    {
                        int(row_no): int(relative_y)
                        for row_no, relative_y in targeted_rows.items()
                    }
                )
                missing_targets = targets - set(targeted_rows)
                unresolved_targets = missing_targets - set(merged_rows)
                if unresolved_targets:
                    _fail_form(
                        "관리항목 입력 시작 전 행번호 좌표를 확인하지 못했습니다: "
                        f"missing={sorted(unresolved_targets)}, found={sorted(targeted_rows)}"
                    )
                if missing_targets:
                    self.logger.warning(
                        "  [MGMT-XY] 점 단위 UIA가 행번호를 노출하지 않아 검증된 "
                        "전표 viewport 좌표를 사용합니다: "
                        f"missing={sorted(missing_targets)}, geometry="
                        f"{[(row_no, merged_rows[row_no]) for row_no in sorted(missing_targets)]}"
                    )
                return merged_rows, not bool(missing_targets)

            if skip_visible_row_scan:
                initial_snapshot = _validate_initial_voucher_row_snapshot(
                    _fast_visible_voucher_row_snapshot()
                )
                # The fast path is intentionally geometry-only.  Point UIA on this
                # GDI grid can block for minutes even though the rows are already
                # painted, so keep the logical row map produced from the cached
                # viewport boundary and do not probe row labels before row 1.
                initial_row_map = {
                    int(row_no): int(relative_y)
                    for row_no, relative_y in (initial_snapshot.get("rows") or {}).items()
                }
                initial_point_uia_complete = False
            else:
                initial_snapshot = _validate_initial_voucher_row_snapshot(
                    _fully_visible_voucher_row_snapshot()
                )
                initial_probe_targets = {1, min(max(1, rows_to_fill), len(initial_snapshot["slot_ys"]))}
                initial_row_map, initial_point_uia_complete = (
                    _initial_voucher_rows_with_geometry_fallback(
                        initial_snapshot,
                        initial_probe_targets,
                    )
                )
            first_row_y = int(initial_snapshot["rows"].get(1, initial_snapshot["first_y"]))
            row_height = int(initial_snapshot["row_pitch"])
            visible_rows = len(initial_snapshot["slot_ys"])
            max_row_y = int(initial_snapshot["last_full_y"])
            initial_snapshot["rows"] = dict(initial_row_map)
            initial_snapshot["has_exact_row_numbers"] = bool(initial_point_uia_complete)
            initial_snapshot["has_logical_row_numbers"] = True
            first_row_y = int(initial_row_map.get(1, first_row_y))
            last_initial_row_no = max(
                (
                    row_no
                    for row_no in initial_row_map
                    if 1 <= int(row_no) <= rows_to_fill
                ),
                default=1,
            )
            calibration_row_no = None if skip_visible_row_scan else int(last_initial_row_no)
            row_geometry_state = {
                "snapshot": initial_snapshot,
                "bottom_scroll_mode": False,
                "scroll_anchor_y": None,
                "calibrate_on_focus_row": None,
                "calibrate_after_commit": False,
                "calibration_focus_y": None,
                "calibration_focus_next_y": None,
                "calibration_row_no": calibration_row_no,
                "fixed_boundary_row_no": (
                    int(last_initial_row_no) if skip_visible_row_scan else None
                ),
                "scroll_advance_mode": None,
            }
            self.logger.info(
                f"  [MGMT-XY] 행 이동 방식: sequential={sequential_nav}, dynamic_uia=True, "
                f"first_y={first_row_y}, row_h={row_height}, visible_rows={visible_rows}, "
                f"last_full_y={max_row_y}, skip_name_scan={skip_visible_row_scan}"
            )

            def _next_visible_voucher_row_y(current_y, next_row_no, snapshot):
                pitch = max(1, int(snapshot.get("row_pitch") or row_height))
                tolerance = max(2.0, pitch * 0.35)
                named_y = (snapshot.get("rows") or {}).get(int(next_row_no))
                if named_y is not None and float(named_y) > float(current_y) + tolerance:
                    next_y = int(named_y)
                    return next_y, abs(next_y - int(snapshot["last_full_y"])) <= tolerance
                lower_slots = [
                    int(value)
                    for value in (snapshot.get("slot_ys") or [])
                    if float(value) > float(current_y) + tolerance
                ]
                if lower_slots:
                    next_y = min(lower_slots)
                    return next_y, abs(next_y - int(snapshot["last_full_y"])) <= tolerance
                return int(snapshot["last_full_y"]), True

            def _set_calibrated_scroll_anchor(
                row_no,
                relative_y,
                source,
                advance_mode,
            ):
                snapshot = row_geometry_state["snapshot"]
                anchor_y = min(
                    int(snapshot["last_full_y"]),
                    max(int(snapshot["first_y"]), int(relative_y)),
                )
                row_geometry_state["scroll_anchor_y"] = anchor_y
                row_geometry_state["bottom_scroll_mode"] = True
                row_geometry_state["calibrate_on_focus_row"] = None
                row_geometry_state["calibrate_after_commit"] = False
                row_geometry_state["calibration_focus_y"] = None
                row_geometry_state["calibration_focus_next_y"] = None
                row_geometry_state["scroll_advance_mode"] = str(advance_mode)
                snapshot["scroll_anchor_y"] = anchor_y
                self.logger.info(
                    f"  [MGMT-XY] 스크롤 고정 좌표 확정: row={row_no}, y={anchor_y}, "
                    f"source={source}, advance={advance_mode}"
                )
                return anchor_y

            def _calibrate_focused_last_row(row_no, clicked_y):
                snapshot = row_geometry_state["snapshot"]
                targeted_rows = _targeted_uia_voucher_rows(
                    snapshot,
                    {row_no, row_no + 1},
                )
                actual_y = targeted_rows.get(int(row_no))
                if actual_y is None:
                    actual_y = int(clicked_y)
                    self.logger.warning(
                        f"  [MGMT-XY] {row_no}행 마지막 적요 더블클릭 후 점 단위 UIA가 "
                        "행번호를 노출하지 않아 클릭 좌표를 유지합니다. "
                        "관리항목 Enter 뒤 마지막 완전 표시 좌표를 고정합니다."
                    )
                tolerance = max(2, int((snapshot.get("row_pitch") or row_height) * 0.35))
                moved = abs(int(actual_y) - int(clicked_y)) > tolerance
                next_row_visible = int(row_no + 1) in targeted_rows
                row_geometry_state["calibrate_after_commit"] = True
                row_geometry_state["calibrate_on_focus_row"] = None
                row_geometry_state["calibration_focus_y"] = int(actual_y)
                row_geometry_state["calibration_focus_next_y"] = targeted_rows.get(
                    int(row_no + 1)
                )
                self.logger.info(
                    f"  [MGMT-XY] {row_no}행 마지막 적요 더블클릭 뒤 실제 좌표 확인: "
                    f"clicked_y={clicked_y}, actual_y={actual_y}, moved={moved}, "
                    f"next_visible={next_row_visible}; 값 입력 뒤 실제 이동 방식을 1회 확정합니다."
                )
                return int(actual_y)

            def _focus_grid_row(row_no, expected_y):
                snapshot = row_geometry_state["snapshot"]
                target_y = expected_y
                if row_geometry_state["bottom_scroll_mode"]:
                    target_y = int(
                        row_geometry_state.get("scroll_anchor_y")
                        or snapshot.get("scroll_anchor_y")
                        or target_y
                    )
                elif row_geometry_state.get("calibrate_on_focus_row") == int(row_no):
                    # Keep the runtime-calibration candidate Y instead of restoring
                    # a stale initial slot while the viewport is at its boundary.
                    target_y = int(expected_y)
                else:
                    target_y = (snapshot.get("rows") or {}).get(row_no, target_y)
                target_y = min(
                    int(snapshot["last_full_y"]),
                    max(int(snapshot["first_y"]), int(target_y)),
                )
                _double_click_form_xy(summary_x, target_y, f"{row_no}행 적요", wait=mgmt_summary_open_wait)
                if row_geometry_state.get("calibrate_on_focus_row") == int(row_no):
                    target_y = _calibrate_focused_last_row(row_no, target_y)
                return target_y

            def _advance_grid_row(
                current_y,
                next_row_no,
                management_enter_sent=False,
            ):
                if not sequential_nav:
                    return current_y
                snapshot = row_geometry_state["snapshot"]
                if row_geometry_state["bottom_scroll_mode"]:
                    anchor_y = int(
                        row_geometry_state.get("scroll_anchor_y")
                        or snapshot.get("scroll_anchor_y")
                        or current_y
                    )
                    if (
                        management_enter_sent
                        and not skip_visible_row_scan
                        and row_geometry_state.get("scroll_advance_mode") == "enter"
                    ):
                        self.logger.info(
                            f"  [MGMT-XY] {next_row_no}행 이동: 보정된 Enter 이동 좌표 재사용 "
                            f"y={anchor_y}"
                        )
                        return anchor_y
                    _click_form_xy(
                        summary_x,
                        anchor_y,
                        f"{next_row_no - 1}행 선택 복귀",
                        wait=mgmt_key_wait,
                    )
                    pyautogui.press('down')
                    time.sleep(mgmt_commit_wait)
                    return anchor_y

                if skip_visible_row_scan:
                    boundary_row_no = row_geometry_state.get("fixed_boundary_row_no")
                    if (
                        boundary_row_no is not None
                        and int(next_row_no) > int(boundary_row_no)
                    ):
                        # From the first row beyond the painted viewport onward,
                        # the fully visible bottom slot is the fixed coordinate.
                        # In the GDI-only production screen, Enter commits the
                        # management value but does not advance the voucher row.
                        # Always restore the current summary row and press Down once.
                        anchor_y = int(snapshot["last_full_y"])
                        _click_form_xy(
                            summary_x,
                            int(current_y),
                            f"{next_row_no - 1}행 선택 복귀",
                            wait=mgmt_key_wait,
                        )
                        pyautogui.press('down')
                        # Down 후 ERP 스크롤/재도색이 끝나기 전에 다음 적요를
                        # 더블클릭하면 같은 슬롯에 남아 있는 이전 행을 다시
                        # 선택해 이후 거래처가 한 행씩 밀린다. 화면 이동이
                        # 끝날 때까지 충분히 기다린다.
                        time.sleep(finance_row_advance_settle_wait)
                        return _set_calibrated_scroll_anchor(
                            next_row_no,
                            anchor_y,
                            "fast-management-down-geometry",
                            "down",
                        )

                if row_geometry_state.get("calibrate_after_commit"):
                    before_y = int(
                        row_geometry_state.get("calibration_focus_y") or current_y
                    )
                    targeted_rows = _targeted_uia_voucher_rows(
                        snapshot,
                        {next_row_no - 1, next_row_no},
                    )
                    current_after_y = targeted_rows.get(int(next_row_no - 1))
                    next_after_y = targeted_rows.get(int(next_row_no))
                    if (
                        management_enter_sent
                        and current_after_y is None
                        and next_after_y is None
                    ):
                        geometry_y = int(snapshot["last_full_y"])
                        self.logger.warning(
                            f"  [MGMT-XY] {next_row_no}행 이동 시 점 단위 UIA가 행번호를 "
                            "노출하지 않아 관리항목 Enter 이동과 마지막 완전 표시 좌표를 "
                            f"고정합니다: y={geometry_y}"
                        )
                        return _set_calibrated_scroll_anchor(
                            next_row_no,
                            geometry_y,
                            "management-enter-geometry-fallback",
                            "enter",
                        )
                    tolerance = max(
                        2,
                        int((snapshot.get("row_pitch") or row_height) * 0.35),
                    )
                    viewport_moved = (
                        current_after_y is None
                        or abs(int(current_after_y) - before_y) > tolerance
                    )
                    next_selected = None
                    if next_after_y is not None:
                        try:
                            next_selected = _uia_voucher_row_selected_at_y(
                                Desktop(backend="uia"),
                                next_after_y,
                            )
                        except Exception:
                            next_selected = None
                    if (
                        management_enter_sent
                        and next_after_y is not None
                        and (viewport_moved or next_selected is True)
                    ):
                        return _set_calibrated_scroll_anchor(
                            next_row_no,
                            next_after_y,
                            "management-enter-observed",
                            "enter",
                        )
                    _click_form_xy(
                        summary_x,
                        int(current_after_y if current_after_y is not None else before_y),
                        f"{next_row_no - 1}행 선택 복귀",
                        wait=mgmt_key_wait,
                    )
                    pyautogui.press('down')
                    time.sleep(mgmt_commit_wait)
                    targeted_rows = _targeted_uia_voucher_rows(snapshot, {next_row_no})
                    actual_y = targeted_rows.get(int(next_row_no))
                    if actual_y is None:
                        _fail_form(
                            f"경계행 Down 후 {next_row_no}행 실제 좌표를 UIA로 확인하지 못했습니다."
                        )
                    self.logger.info(
                        f"  [MGMT-XY] 마지막 적요 더블클릭 뒤 화면 이동이 없어 "
                        f"Down 1회 후 {next_row_no}행 실제 좌표를 고정합니다."
                    )
                    return _set_calibrated_scroll_anchor(
                        next_row_no,
                        actual_y,
                        "down-after-last-row",
                        "down",
                    )

                next_y, _ = _next_visible_voucher_row_y(
                    current_y,
                    next_row_no,
                    snapshot,
                )
                calibration_row = row_geometry_state.get("calibration_row_no")
                if calibration_row is not None and int(next_row_no) == int(calibration_row):
                    if management_enter_sent:
                        targeted_rows = _targeted_uia_voucher_rows(
                            snapshot,
                            {next_row_no},
                        )
                        live_next_y = targeted_rows.get(int(next_row_no))
                        if live_next_y is None:
                            self.logger.warning(
                                f"  [MGMT-XY] 관리항목 Enter 뒤 경계 {next_row_no}행을 "
                                "점 단위 UIA로 읽지 못해 계산된 완전 표시 좌표를 유지합니다: "
                                f"y={next_y}"
                            )
                        else:
                            next_y = int(live_next_y)
                    row_geometry_state["calibrate_on_focus_row"] = int(next_row_no)
                    self.logger.info(
                        f"  [MGMT-XY] {next_row_no}행은 계산된 마지막 적요 좌표에서 직접 더블클릭 후 "
                        "행번호 지점 UIA로 스크롤 여부를 확인합니다."
                    )
                    return int(next_y)

                _click_form_xy(
                    summary_x,
                    int(current_y),
                    f"{next_row_no - 1}행 선택 복귀",
                    wait=mgmt_key_wait,
                )
                pyautogui.press('down')
                time.sleep(mgmt_commit_wait)
                return int(next_y)

            bank_management_norms = {
                _norm_text("계좌번호"),
                _norm_text("금융기관지점"),
            }

            def _explicit_management_for_index(idx):
                if (
                    isinstance(line_management_items, list)
                    and idx < len(line_management_items)
                    and isinstance(line_management_items[idx], dict)
                ):
                    return line_management_items[idx]
                return {}

            def _requires_bank_management(management):
                if not isinstance(management, dict):
                    return False
                return bool({_norm_text(key) for key in management.keys()} & bank_management_norms)

            def _bank_management_visible():
                snapshot = _management_grid_snapshot()
                management_grid_ready_state["snapshot"] = snapshot
                labels = snapshot.get("label_norms") or set()
                return bank_management_norms.issubset(labels), snapshot

            def _current_row_account_matches(row_no, current_y, expected_account):
                expected_norm = _norm_text(expected_account)
                if not expected_norm:
                    return False
                expected_summary = ""
                if 1 <= int(row_no) <= len(erp_rows):
                    expected_columns = str(erp_rows[int(row_no) - 1] or "").split('\t')
                    if expected_columns:
                        expected_summary = expected_columns[-1].strip()
                expected_summary_norm = _norm_text(expected_summary)
                old_clipboard = None
                copied = ""
                matched_x = None
                matched_by = None
                probe_results = []
                try:
                    old_clipboard = pyperclip.paste()
                except Exception:
                    old_clipboard = None
                try:
                    verify_center_x = int(
                        os.getenv("ERP_MGMT_ACCOUNT_VERIFY_CENTER_X", "295") or "295"
                    )
                    if expected_summary_norm:
                        try:
                            focus_sentinel = f"__ERP_ACCOUNT_VERIFY_{row_no}_FOCUS__"
                            pyperclip.copy(focus_sentinel)
                            pyautogui.hotkey('ctrl', 'c')
                            time.sleep(max(0.08, mgmt_key_wait))
                            copied = str(pyperclip.paste() or "")
                            copied_norm = _norm_text(copied)
                            probe_results.append(("focus", copied[:80]))
                            if copied != focus_sentinel and copied_norm == expected_summary_norm:
                                matched_by = "focused-summary"
                        except Exception as focus_error:
                            probe_results.append(("focus", f"ERROR: {focus_error}"))
                    probe_xs = []
                    for probe_x in (account_x, verify_center_x):
                        if probe_x not in probe_xs:
                            probe_xs.append(probe_x)
                    for probe_x in ([] if matched_by else probe_xs):
                        try:
                            sentinel = f"__ERP_ACCOUNT_VERIFY_{row_no}_{probe_x}__"
                            pyperclip.copy(sentinel)
                            _click_form_xy(
                                probe_x,
                                int(current_y),
                                f"{row_no}행 계정과목 검증",
                                wait=mgmt_key_wait,
                            )
                            pyautogui.hotkey('ctrl', 'c')
                            time.sleep(max(0.08, mgmt_key_wait))
                            copied = str(pyperclip.paste() or "")
                            copied_norm = _norm_text(copied)
                            probe_results.append((probe_x, copied[:80]))
                            if copied != sentinel and expected_norm in copied_norm:
                                matched_x = probe_x
                                matched_by = "account"
                                break
                            if (
                                copied != sentinel
                                and expected_summary_norm
                                and copied_norm == expected_summary_norm
                            ):
                                matched_x = probe_x
                                matched_by = "summary"
                                break
                        except Exception as probe_error:
                            probe_results.append((probe_x, f"ERROR: {probe_error}"))
                finally:
                    if old_clipboard is not None:
                        try:
                            pyperclip.copy(old_clipboard)
                        except Exception:
                            pass
                ok = matched_by is not None
                self.logger.info(
                    f"  [MGMT-XY] {row_no}행 계정과목 검증: expected={expected_account}, "
                    f"expected_summary={expected_summary}, matched_by={matched_by}, "
                    f"matched_x={matched_x}, probes={probe_results}, ok={ok}"
                )
                return ok

            def _ensure_bank_management_row(row_no, current_y, expected_account):
                if skip_visible_row_scan:
                    if not _prepare_fast_bank_management_coordinates():
                        _fail_form(
                            f"{row_no}행 보통예금 관리항목의 빠른 입력 좌표를 준비하지 못했습니다."
                        )
                    management_bank_coordinate_fallback_rows.add(row_no)
                    self.logger.info(
                        f"  [MGMT-XY] {row_no}행은 payload에 계좌번호/금융기관지점이 명시된 "
                        "마지막 보통예금 행이므로 불안정한 GDI Ctrl+C 검증 없이 입력을 진행합니다."
                    )
                    return current_y
                ok, snapshot = _bank_management_visible()
                if ok:
                    self.logger.info(f"  [MGMT-XY] {row_no}행 보통예금 관리항목 표시 확인")
                    return current_y
                if _current_row_account_matches(row_no, current_y, expected_account):
                    management_bank_coordinate_fallback_rows.add(row_no)
                    self.logger.warning(
                        f"  [MGMT-XY] {row_no}행 보통예금 계정과목은 확인됐지만 관리항목 라벨이 미검출되어 "
                        "고정 좌표 입력 fallback을 허용합니다."
                    )
                    return current_y
                for wait_try in range(2):
                    time.sleep(max(0.25, mgmt_commit_wait))
                    ok, snapshot = _bank_management_visible()
                    if ok:
                        self.logger.info(f"  [MGMT-XY] {row_no}행 보통예금 관리항목 지연 표시 확인({wait_try + 1})")
                        return current_y
                    if _current_row_account_matches(row_no, current_y, expected_account):
                        management_bank_coordinate_fallback_rows.add(row_no)
                        self.logger.warning(
                            f"  [MGMT-XY] {row_no}행 보통예금 계정과목 검증 완료로 "
                            "관리항목 고정 좌표 입력 fallback을 허용합니다."
                        )
                        return current_y
                for retry in range(5):
                    self.logger.warning(
                        f"  [MGMT-XY] {row_no}행 보통예금 관리항목 미표시, 다음 행 이동 재시도 "
                        f"({retry + 1}/5): labels={snapshot.get('labels')}"
                    )
                    _click_form_xy(summary_x, int(current_y), f"{row_no}행 보통예금 행 이동 재시도", wait=mgmt_key_wait)
                    pyautogui.press('down')
                    time.sleep(max(0.35, mgmt_commit_wait))
                    retry_snapshot = row_geometry_state["snapshot"]
                    current_y = int(
                        retry_snapshot.get("scroll_anchor_y") or retry_snapshot["last_full_y"]
                    )
                    _double_click_form_xy(summary_x, int(current_y), f"{row_no}행 보통예금 재선택", wait=mgmt_summary_open_wait)
                    if mgmt_after_summary_open_wait:
                        time.sleep(mgmt_after_summary_open_wait)
                    ok, snapshot = _bank_management_visible()
                    if ok:
                        self.logger.info(f"  [MGMT-XY] {row_no}행 보통예금 관리항목 표시 확인(재시도 {retry + 1})")
                        return current_y
                    if _current_row_account_matches(row_no, current_y, expected_account):
                        management_bank_coordinate_fallback_rows.add(row_no)
                        self.logger.warning(
                            f"  [MGMT-XY] {row_no}행 보통예금 계정과목 검증 완료(재시도 {retry + 1})로 "
                            "관리항목 고정 좌표 입력 fallback을 허용합니다."
                        )
                        return current_y
                _fail_form(
                    f"{row_no}행 보통예금 관리항목이 표시되지 않아 계좌번호 입력을 중단합니다. "
                    f"visible_labels={snapshot.get('labels')}"
                )

            current_y = first_row_y
            for idx in range(rows_to_fill):
                account_name = ""
                if idx < len(erp_rows):
                    account_name = str(erp_rows[idx]).split('\t')[0].strip()
                row_no = idx + 1
                account_key, corp, plan = _management_plan(account_name)
                explicit_management_for_row = _explicit_management_for_index(idx)
                has_explicit_management = (
                    isinstance(explicit_management_for_row, dict)
                    and bool(explicit_management_for_row)
                )
                if not plan and not has_explicit_management:
                    self.logger.info(f"  [MGMT-XY] {row_no}행 스킵: account={account_key}, corp={corp}, 입력 불필요")
                    if row_geometry_state.get("calibrate_on_focus_row") == row_no:
                        current_y = _focus_grid_row(row_no, current_y)
                    if idx < rows_to_fill - 1:
                        current_y = _advance_grid_row(current_y, row_no + 1)
                    continue
                summary_y = current_y if sequential_nav else first_row_y + (idx * row_height)
                current_y = _focus_grid_row(row_no, summary_y)
                if mgmt_after_summary_open_wait:
                    time.sleep(mgmt_after_summary_open_wait)
                if _requires_bank_management(explicit_management_for_row):
                    current_y = _ensure_bank_management_row(row_no, current_y, account_name)
                management_enter_sent = bool(
                    _fill_management_for_current_row(row_no, account_name)
                )
                time.sleep(mgmt_key_wait)
                if idx < rows_to_fill - 1:
                    current_y = _advance_grid_row(
                        current_y,
                        row_no + 1,
                        management_enter_sent=management_enter_sent,
                    )

            self.logger.info("  [MGMT-XY] 행별 적요/관리항목 좌표 입력 완료")

        def _prepare_management_recovery_from_first_row():
            """Reset the existing voucher to row 1 and rebuild fast GDI anchors.

            The recovery job is intentionally limited to the already-pasted voucher:
            it neither opens a new form nor pastes voucher rows again.  It validates
            the first summary through the grid clipboard, captures the currently
            painted management pane without a full UIA descendant walk, and then lets
            the normal management loop run unchanged.
            """
            erp_rows = form_data.get('erp_clipboard_rows') or []
            line_management_items = (
                form_data.get('erp_line_management_items')
                or form_data.get('line_management_items')
                or []
            )
            rows_to_fill = max(
                0,
                int(form_data.get('erp_row_count') or len(erp_rows) or row_count),
            )
            if not erp_rows or rows_to_fill <= 0:
                _fail_form("관리항목 복구 payload에 ERP 전표 행이 없습니다.")
            if len(erp_rows) < rows_to_fill:
                _fail_form(
                    "관리항목 복구 payload의 ERP 전표 행 수가 부족합니다: "
                    f"expected={rows_to_fill}, actual={len(erp_rows)}"
                )
            if not isinstance(line_management_items, list) or len(line_management_items) < rows_to_fill:
                _fail_form(
                    "관리항목 복구 payload의 행별 관리항목 수가 부족합니다: "
                    f"expected={rows_to_fill}, actual="
                    f"{len(line_management_items) if isinstance(line_management_items, list) else 0}"
                )

            last_account = str(erp_rows[rows_to_fill - 1] or "").split('\t')[0].strip()
            last_management = line_management_items[rows_to_fill - 1]
            last_management_norm = {
                _norm_text(key): str(value or "").strip()
                for key, value in (last_management.items() if isinstance(last_management, dict) else [])
            }
            required_bank_values = {
                _norm_text("계좌번호"): last_management_norm.get(_norm_text("계좌번호"), ""),
                _norm_text("금융기관지점"): last_management_norm.get(_norm_text("금융기관지점"), ""),
            }
            if _norm_text("보통예금") not in _norm_text(last_account):
                _fail_form(
                    "관리항목 복구의 마지막 ERP 행이 보통예금이 아닙니다: "
                    f"row={rows_to_fill}, account={last_account}"
                )
            missing_bank_values = [
                name for name, value in required_bank_values.items() if not value
            ]
            if missing_bank_values:
                _fail_form(
                    "관리항목 복구 payload의 마지막 보통예금 필수값이 비어 있습니다: "
                    f"missing={missing_bank_values}"
                )

            summary_x = int(os.getenv("ERP_MGMT_SUMMARY_X", "970") or "970")
            first_row_y = int(os.getenv("ERP_MGMT_FIRST_ROW_Y", "231") or "231")
            try:
                main_win.set_focus()
            except Exception:
                pass
            _click_form_xy(
                summary_x,
                first_row_y,
                "관리항목 복구 전표 그리드 포커스",
                wait=mgmt_click_wait,
            )
            _release_modifiers("관리항목 복구 Ctrl+Home 직전", wait=False)
            pyautogui.hotkey('ctrl', 'home')
            _release_modifiers("관리항목 복구 Ctrl+Home 직후", wait=False)
            time.sleep(max(mgmt_commit_wait, 0.35))
            first_columns = str(erp_rows[0] or "").split('\t')
            expected_first_account = first_columns[0].strip() if first_columns else ""
            expected_first_debit = first_columns[1].strip() if len(first_columns) > 1 else ""
            expected_first_credit = first_columns[2].strip() if len(first_columns) > 2 else ""
            expected_first_summary = first_columns[-1].strip() if first_columns else ""

            old_clipboard = None
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                old_clipboard = None

            def _copy_first_row_cell(relative_x, label):
                sentinel = f"__ERP_MGMT_RECOVERY_{label}__"
                pyperclip.copy(sentinel)
                _click_form_xy(
                    int(relative_x),
                    first_row_y,
                    f"관리항목 복구 1행 {label} 검증",
                    wait=mgmt_key_wait,
                )
                pyautogui.hotkey('ctrl', 'c')
                _release_modifiers(f"관리항목 복구 1행 {label} Ctrl+C 직후", wait=False)
                time.sleep(max(0.10, mgmt_key_wait))
                copied = str(pyperclip.paste() or "").strip()
                if copied == sentinel:
                    return ""
                return copied

            copied_first = {}
            try:
                copied_first = {
                    "account": _copy_first_row_cell(
                        int(os.getenv("ERP_MGMT_ACCOUNT_X", "229") or "229"),
                        "계정과목",
                    ),
                    "debit": _copy_first_row_cell(
                        int(os.getenv("ERP_MGMT_DEBIT_X", "390") or "390"),
                        "차변금액",
                    ),
                    "credit": _copy_first_row_cell(
                        int(os.getenv("ERP_MGMT_CREDIT_X", "500") or "500"),
                        "대변금액",
                    ),
                    "summary": _copy_first_row_cell(summary_x, "적요"),
                }
            finally:
                if old_clipboard is not None:
                    try:
                        pyperclip.copy(old_clipboard)
                    except Exception:
                        pass

            def _amount_digits(value):
                compact = re.sub(r"[^0-9-]", "", str(value or ""))
                try:
                    return int(compact)
                except (TypeError, ValueError):
                    return None

            first_row_confirmed = bool(
                _norm_text(expected_first_account)
                and _norm_text(copied_first.get("account")) == _norm_text(expected_first_account)
                and _amount_digits(copied_first.get("debit")) == _amount_digits(expected_first_debit)
                and _amount_digits(copied_first.get("credit")) == _amount_digits(expected_first_credit)
                and _norm_text(expected_first_summary)
                and _norm_text(copied_first.get("summary")) == _norm_text(expected_first_summary)
            )
            self.logger.info(
                "  [MGMT-RECOVERY] 1행 전표 식별값 검증: "
                f"expected={{'account': {expected_first_account!r}, "
                f"'debit': {expected_first_debit!r}, 'credit': {expected_first_credit!r}, "
                f"'summary': {expected_first_summary!r}}}, copied={copied_first}, "
                f"ok={first_row_confirmed}"
            )
            if not first_row_confirmed:
                _fail_form(
                    "현재 열린 전표의 1행 계정과목/차변/대변/적요가 복구 원본과 "
                    "일치하지 않아 관리항목 복구를 중단합니다: "
                    f"expected_account={expected_first_account}, "
                    f"expected_debit={expected_first_debit}, "
                    f"expected_credit={expected_first_credit}, "
                    f"expected_summary={expected_first_summary}, copied={copied_first}"
                )

            _double_click_form_xy(
                summary_x,
                first_row_y,
                "관리항목 복구 1행 적요",
                wait=mgmt_summary_open_wait,
            )
            if mgmt_after_summary_open_wait:
                time.sleep(mgmt_after_summary_open_wait)

            stable_required = max(
                1,
                int(os.getenv("ERP_GRID_PASTE_VISUAL_STABLE_COUNT", "2") or "2"),
            )
            stable_count = 0
            previous_signature = None
            ready_snapshot = None
            visual_attempts = max(3, stable_required + 1)
            for attempt in range(1, visual_attempts + 1):
                snapshot = _management_grid_visual_snapshot()
                signature = snapshot.get("visual_signature")
                if snapshot.get("visual_ready") and signature is not None:
                    stable_count = stable_count + 1 if signature == previous_signature else 1
                    previous_signature = signature
                    ready_snapshot = snapshot
                    if stable_count >= stable_required:
                        break
                else:
                    stable_count = 0
                    previous_signature = None
                self.logger.info(
                    "  [MGMT-RECOVERY] 1행 관리항목 GDI 기준 대기: "
                    f"attempt={attempt}/{visual_attempts}, ready={snapshot.get('visual_ready')}, "
                    f"signature={signature}, stable={stable_count}/{stable_required}"
                )
                time.sleep(max(0.20, mgmt_key_wait))
            if (
                ready_snapshot is None
                or stable_count < stable_required
                or ready_snapshot.get("first_value_y") is None
                or ready_snapshot.get("voucher_clip_bottom_abs") is None
            ):
                _fail_form(
                    "현재 열린 전표 1행의 하단 관리항목 좌표를 GDI 화면에서 확인하지 못했습니다."
                )

            ready_snapshot.update(
                {
                    "stable_gdi_ready": True,
                    "semantic_ready": False,
                    "expected_label_norms": {_norm_text("거래처")},
                    "items": [],
                }
            )
            management_grid_ready_state["snapshot"] = ready_snapshot
            vendor_key = _norm_text("거래처")
            management_value_xy_cache[vendor_key] = (
                int(ready_snapshot["value_x"]),
                int(ready_snapshot["first_value_y"]),
            )
            finance_vendor_entry_state["f9_seeded"] = False
            self.logger.info(
                "  [MGMT-RECOVERY] 신규/재붙여넣기 없이 기존 전표 전체 관리항목 복구 준비 완료: "
                f"rows={rows_to_fill}, first_value="
                f"({ready_snapshot['value_x']},{ready_snapshot['first_value_y']}), "
                f"signature={ready_snapshot.get('visual_signature')}"
            )
            return ready_snapshot

        def _wait_process_by_name(process_name, timeout_sec=10):
            target = str(process_name or "").lower()
            end_at = time.time() + timeout_sec
            while time.time() < end_at:
                try:
                    for proc in psutil.process_iter(['name']):
                        name = (proc.info.get('name') or '').lower()
                        if name == target:
                            self.logger.info(f"  [PRINT] 프로세스 감지 완료: {process_name} (pid={proc.pid})")
                            return True
                except:
                    pass
                time.sleep(ERP_CLICK_WAIT)
            self.logger.warning(f"  [PRINT] 프로세스 감지 시간초과: {process_name}")
            return False

        def _find_rd_viewer_process():
            try:
                for proc in psutil.process_iter(["pid", "name"]):
                    name = (proc.info.get("name") or "").strip().lower()
                    if name.startswith("rdviewer"):
                        return proc, name
            except Exception:
                pass
            return None, ""

        def _find_rd_viewer_window():
            title_re = r"(Report\s*Designer\s*Viewer|RD\s*Viewer|Designer\s*Viewer)"
            for backend in ("win32", "uia"):
                try:
                    for win in Desktop(backend=backend).windows():
                        title = (win.window_text() or "").strip()
                        if re.search(title_re, title, re.I):
                            return win, backend, title
                except Exception:
                    pass
            return None, "", ""

        def _new_rd_viewer_processes(baseline=None):
            baseline_pids = {
                int(pid)
                for pid in dict((baseline or {}).get("processes") or {}).keys()
                if str(pid).isdigit()
            }
            found = []
            try:
                for proc in psutil.process_iter(["pid", "name"]):
                    pid = int(proc.info.get("pid") or 0)
                    name = str(proc.info.get("name") or "").strip().lower()
                    if pid and name.startswith("rdviewer") and pid not in baseline_pids:
                        found.append((proc, name))
            except Exception:
                pass
            return found

        def _find_fresh_rd_viewer_window(baseline=None, preferred_pids=None):
            """Find a visible Viewer window that did not exist before this print attempt."""
            title_re = r"(Report\s*Designer\s*Viewer|RD\s*Viewer|Designer\s*Viewer)"
            preferred = {int(pid) for pid in (preferred_pids or set()) if int(pid or 0)}
            baseline_windows = {
                (
                    int(item.get("pid") or 0),
                    int(item.get("handle") or 0),
                    str(item.get("title") or ""),
                    str(item.get("class") or ""),
                    str(item.get("rect") or ""),
                )
                for item in list((baseline or {}).get("windows") or [])
            }
            candidates = []
            seen = set()
            for backend in ("win32", "uia"):
                try:
                    windows = Desktop(backend=backend).windows()
                except Exception:
                    continue
                for win in windows:
                    try:
                        if hasattr(win, "is_visible") and not win.is_visible():
                            continue
                    except Exception:
                        continue
                    try:
                        pid = int(win.process_id() or 0)
                    except Exception:
                        pid = int(
                            getattr(getattr(win, "element_info", None), "process_id", 0) or 0
                        )
                    try:
                        title = str(win.window_text() or "").strip()
                    except Exception:
                        title = ""
                    title_matches = bool(re.search(title_re, title, re.I))
                    # For a newly-created rdviewer PID, any visible top-level window is
                    # eligible even while its localized/final title is still changing.
                    if pid not in preferred and not title_matches:
                        continue
                    try:
                        class_name = str(win.class_name() or "").strip()
                    except Exception:
                        class_name = str(
                            getattr(getattr(win, "element_info", None), "class_name", "") or ""
                        ).strip()
                    try:
                        rect = win.rectangle()
                        rect_text = f"{rect.left},{rect.top},{rect.right},{rect.bottom}"
                    except Exception:
                        rect_text = ""
                    try:
                        handle = int(getattr(win, "handle", 0) or 0)
                    except Exception:
                        handle = 0
                    identity = (pid, handle, title, class_name, rect_text)
                    if identity in seen or identity in baseline_windows:
                        continue
                    seen.add(identity)
                    meta = {
                        "pid": pid,
                        "handle": handle,
                        "title": title,
                        "class": class_name,
                        "rect": rect_text,
                        "identity": identity,
                    }
                    # A window linked to the new rdviewer PID wins over a title-only
                    # window from an older process.
                    candidates.append((0 if pid in preferred else 1, win, backend, title, meta))
            if not candidates:
                return None, "", "", {}
            candidates.sort(key=lambda item: item[0])
            _rank, win, backend, title, meta = candidates[0]
            return win, backend, title, meta

        def _capture_print_runtime():
            processes = {}
            try:
                for proc in psutil.process_iter(["pid", "name"]):
                    pid = int(proc.info.get("pid") or 0)
                    if pid:
                        processes[pid] = str(proc.info.get("name") or "")
            except Exception:
                pass

            windows = []
            seen = set()
            for backend in ("win32", "uia"):
                try:
                    for win in Desktop(backend=backend).windows():
                        try:
                            if hasattr(win, "is_visible") and not win.is_visible():
                                continue
                        except Exception:
                            continue
                        try:
                            title = str(win.window_text() or "").strip()
                        except Exception:
                            title = ""
                        try:
                            class_name = str(win.class_name() or "").strip()
                        except Exception:
                            class_name = str(
                                getattr(getattr(win, "element_info", None), "class_name", "") or ""
                            ).strip()
                        try:
                            pid = int(win.process_id() or 0)
                        except Exception:
                            pid = int(
                                getattr(getattr(win, "element_info", None), "process_id", 0) or 0
                            )
                        try:
                            rect = win.rectangle()
                            rect_text = f"{rect.left},{rect.top},{rect.right},{rect.bottom}"
                        except Exception:
                            rect_text = ""
                        try:
                            handle = int(getattr(win, "handle", 0) or 0)
                        except Exception:
                            handle = 0
                        key = (pid, handle, title, class_name, rect_text)
                        if key in seen:
                            continue
                        seen.add(key)
                        windows.append(
                            {
                                "backend": backend,
                                "pid": pid,
                                "handle": handle,
                                "process": processes.get(pid, ""),
                                "title": title,
                                "class": class_name,
                                "rect": rect_text,
                            }
                        )
                except Exception:
                    pass
            return {"processes": processes, "windows": windows}

        def _log_print_runtime_delta(label, baseline):
            current = _capture_print_runtime()
            baseline_processes = dict((baseline or {}).get("processes") or {})
            new_processes = [
                {"pid": pid, "name": name}
                for pid, name in current["processes"].items()
                if pid not in baseline_processes
            ]
            baseline_windows = {
                (
                    item.get("pid"),
                    item.get("handle"),
                    item.get("title"),
                    item.get("class"),
                    item.get("rect"),
                )
                for item in list((baseline or {}).get("windows") or [])
            }
            new_windows = [
                item
                for item in current["windows"]
                if (
                    item.get("pid"),
                    item.get("handle"),
                    item.get("title"),
                    item.get("class"),
                    item.get("rect"),
                )
                not in baseline_windows
            ]
            visible_windows = [
                item for item in current["windows"] if item.get("title") or item.get("class")
            ]
            related_processes = [
                {"pid": pid, "name": name}
                for pid, name in current["processes"].items()
                if re.search(r"(rd|viewer|report|print|rpt|ubi|rexpert|clip)", name, re.I)
            ]
            self.logger.warning(
                f"  [PRINT-DIAG] {label}: new_processes="
                f"{json.dumps(new_processes[:80], ensure_ascii=False)}, new_windows="
                f"{json.dumps(new_windows[:80], ensure_ascii=False)}, visible_windows="
                f"{json.dumps(visible_windows[:120], ensure_ascii=False)}, related_processes="
                f"{json.dumps(related_processes[:80], ensure_ascii=False)}"
            )

        def _save_print_timeout_screenshot():
            try:
                job_id = str(getattr(self.manager.main_app, "erp_job_id", "") or "unknown")
                safe_job_id = re.sub(r"[^0-9A-Za-z_.-]+", "_", job_id)
                output_dir = Path(
                    str(os.getenv("ERP_OUTPUT_DIR", "") or tempfile.gettempdir())
                )
                output_dir.mkdir(parents=True, exist_ok=True)
                screenshot_path = output_dir / f"{safe_job_id}_print_timeout.png"
                pyautogui.screenshot(str(screenshot_path))
                self.logger.warning(
                    f"  [PRINT-DIAG] RD Viewer timeout screenshot saved: {screenshot_path}"
                )
                return str(screenshot_path)
            except Exception as e:
                self.logger.warning(f"  [PRINT-DIAG] timeout screenshot 저장 실패: {e}")
                return ""

        def _erp_message_compact(snapshot):
            if not snapshot:
                return ""
            return re.sub(
                r"\s+",
                "",
                f"{snapshot.get('title', '')}\n{snapshot.get('text', '')}",
            ).lower()

        def _find_erp_message_snapshot():
            """Return only a Message dialog owned by the currently attached ERP process."""
            try:
                target_pid = int(self.erp_process_pid or 0)
            except Exception:
                target_pid = 0
            if not target_pid:
                try:
                    target_pid = int(
                        getattr(getattr(main_win, "element_info", None), "process_id", 0) or 0
                    )
                except Exception:
                    target_pid = 0
            if not target_pid:
                self.logger.warning("  [ERP-MESSAGE] ERP PID가 없어 Message 창 탐색을 중단합니다.")
                return None

            title_markers = ("message", "메시지", "알림", "확인")

            def _window_pid(win):
                try:
                    return int(win.process_id() or 0)
                except Exception:
                    try:
                        return int(
                            getattr(getattr(win, "element_info", None), "process_id", 0) or 0
                        )
                    except Exception:
                        return 0

            def _control_texts(control):
                values = []
                for getter in (
                    lambda: control.window_text(),
                    lambda: getattr(getattr(control, "element_info", None), "name", ""),
                ):
                    try:
                        value = str(getter() or "").strip()
                    except Exception:
                        value = ""
                    if value and value not in values:
                        values.append(value)
                try:
                    for value in control.texts() or []:
                        value = str(value or "").strip()
                        if value and value not in values:
                            values.append(value)
                except Exception:
                    pass
                return values

            # ERP Message 창은 WPF(HwndWrapper)라 win32 backend로는 내부
            # 문구/버튼이 보이지 않고 제목 'Message'만 읽힌다. 문구 검증이
            # 가능하도록 uia를 먼저 시도하고 win32는 fallback으로 유지한다.
            for backend in ("uia", "win32"):
                try:
                    windows = Desktop(backend=backend).windows()
                except Exception:
                    continue
                for win in windows:
                    if _window_pid(win) != target_pid:
                        continue
                    title_values = _control_texts(win)
                    title = title_values[0] if title_values else ""
                    compact_title = re.sub(r"\s+", "", title).lower()
                    if not any(marker in compact_title for marker in title_markers):
                        continue

                    values = list(title_values)
                    try:
                        descendants = win.descendants()
                    except Exception:
                        descendants = []
                    for child in descendants:
                        for value in _control_texts(child):
                            if value not in values:
                                values.append(value)
                    text = "\n".join(values)
                    snapshot = {
                        "window": win,
                        "backend": backend,
                        "pid": target_pid,
                        "title": title,
                        "text": text,
                    }
                    self.logger.info(
                        "  [ERP-MESSAGE] same-process Message 감지: "
                        f"backend={backend}, pid={target_pid}, title={title!r}, "
                        f"text={text[:500]!r}"
                    )
                    return snapshot
            return None

        def _wait_erp_message(timeout_sec=10):
            end_at = time.time() + max(0.0, float(timeout_sec or 0.0))
            while True:
                snapshot = _find_erp_message_snapshot()
                if snapshot:
                    return snapshot
                if time.time() >= end_at:
                    return None
                time.sleep(max(ERP_CLICK_WAIT, ERP_POLL_WAIT))

        def _dismiss_verified_erp_message(
            snapshot,
            accepted_phrases,
            button_labels=("확인", "ok"),
            allow_enter_fallback=True,
        ):
            accepted = [
                re.sub(r"\s+", "", str(value or "")).lower()
                for value in accepted_phrases
                if str(value or "").strip()
            ]
            compact = _erp_message_compact(snapshot)
            if not snapshot or not accepted or not any(value in compact for value in accepted):
                raise RuntimeError(
                    "검증되지 않은 ERP Message에는 확인/Enter를 전송할 수 없습니다."
                )

            win = snapshot.get("window")
            accepted_buttons = {
                re.sub(r"\s+", "", str(value or "")).lower()
                for value in button_labels
                if str(value or "").strip()
            }
            try:
                descendants = win.descendants(control_type="Button")
            except TypeError:
                try:
                    descendants = win.descendants()
                except Exception:
                    descendants = []
            except Exception:
                descendants = []

            for button in descendants:
                try:
                    control_type = str(
                        getattr(getattr(button, "element_info", None), "control_type", "") or ""
                    )
                    label = re.sub(r"\s+", "", str(button.window_text() or "")).lower()
                    if label not in accepted_buttons:
                        continue
                    if control_type and control_type.lower() not in {"button", "버튼"}:
                        continue
                    button.click_input()
                    self.logger.info(f"  [ERP-MESSAGE] 검증된 Message {label!r} 버튼 클릭 완료")
                    time.sleep(ERP_SETTLE_WAIT)
                    return True
                except Exception:
                    continue

            if not allow_enter_fallback:
                raise RuntimeError(
                    "검증된 ERP 저장 질문에서 명시적인 승인 버튼을 찾지 못했습니다."
                )
            try:
                win.set_focus()
            except Exception:
                pass
            pyautogui.press("enter")
            self.logger.info("  [ERP-MESSAGE] 검증된 Message에만 Enter fallback 전송 완료")
            time.sleep(ERP_SETTLE_WAIT)
            return True

        def _visible_erp_management_lookup_popups():
            expected_pid = int(getattr(self, "erp_process_pid", 0) or 0)
            blockers = []
            for backend in ("uia", "win32"):
                try:
                    windows = Desktop(backend=backend).windows()
                except Exception:
                    continue
                for win in windows:
                    try:
                        if hasattr(win, "is_visible") and not win.is_visible():
                            continue
                        title = re.sub(r"\s+", "", str(win.window_text() or ""))
                        title_lower = title.lower()
                        if title != "계좌" and "거래처ds" not in title_lower:
                            continue
                        pid = 0
                        try:
                            pid = int(win.process_id() or 0)
                        except Exception:
                            try:
                                pid = int(win.element_info.process_id or 0)
                            except Exception:
                                pid = 0
                        if expected_pid and pid and pid != expected_pid:
                            continue
                        rect = win.rectangle()
                        signature = (
                            title,
                            pid,
                            int(rect.left),
                            int(rect.top),
                            int(rect.right),
                            int(rect.bottom),
                        )
                        if signature not in blockers:
                            blockers.append(signature)
                    except Exception:
                        continue
            if (
                bank_account_popup_state.get("opened")
                and not bank_account_popup_state.get("closed")
            ):
                blockers.append(
                    (
                        "계좌(internal-state)",
                        expected_pid,
                        bank_account_popup_state.get("source", ""),
                    )
                )
            return blockers

        def _assert_no_erp_management_lookup_popup(context):
            blockers = _visible_erp_management_lookup_popups()
            if blockers:
                raise RuntimeError(
                    f"{context} 계좌/거래처 선택 팝업이 닫히지 않아 저장·출력을 중단합니다: "
                    f"{blockers[:8]}"
                )
            self.logger.info(
                f"  [SAVE/PRINT] {context} 미완료 계좌/거래처 팝업 없음 확인"
            )

        def _click_save_button():
            save_xy = str(os.getenv("ERP_SAVE_BUTTON_XY", "250,80") or "250,80").strip()
            coordinate_error = None

            def _verify_exact_save_control_at_point(relative_x, relative_y):
                """Verify the configured save coordinate without walking the GDI tree."""
                main_r = _main_rect()
                absolute_x = int(main_r.left) + int(relative_x)
                absolute_y = int(main_r.top) + int(relative_y)
                control = Desktop(backend="uia").from_point(absolute_x, absolute_y)
                observed = []
                seen = set()
                for _depth in range(6):
                    if control is None:
                        break
                    try:
                        identity = (
                            int(getattr(control, "handle", 0) or 0),
                            str(getattr(getattr(control, "element_info", None), "runtime_id", "") or ""),
                        )
                    except Exception:
                        identity = (id(control), "")
                    if identity in seen:
                        break
                    seen.add(identity)

                    values = []
                    for getter in (
                        lambda: control.window_text(),
                        lambda: getattr(getattr(control, "element_info", None), "name", ""),
                    ):
                        try:
                            value = str(getter() or "").strip()
                        except Exception:
                            value = ""
                        if value and value not in values:
                            values.append(value)
                    observed.extend(value for value in values if value not in observed)
                    for value in values:
                        compact = re.sub(r"\s+", "", value).lower()
                        if compact == "저장" or re.fullmatch(
                            r"저장(?:\([^)]*\)|\[[^]]*\])",
                            compact,
                        ):
                            try:
                                if hasattr(control, "is_visible") and not control.is_visible():
                                    continue
                                if hasattr(control, "is_enabled") and not control.is_enabled():
                                    raise RuntimeError("저장 버튼이 비활성화되어 있습니다.")
                            except RuntimeError:
                                raise
                            except Exception:
                                pass
                            self.logger.info(
                                "  [SAVE] 좌표 지점 UIA 정확 검증 완료: "
                                f"rel=({relative_x},{relative_y}), abs=({absolute_x},{absolute_y}), "
                                f"name={value!r}"
                            )
                            return True
                    try:
                        control = control.parent()
                    except Exception:
                        control = None
                raise RuntimeError(
                    "설정된 저장 좌표에서 정확한 '저장' UI 요소를 확인하지 못했습니다: "
                    f"rel=({relative_x},{relative_y}), observed={observed[:12]}"
                )

            try:
                x_text, y_text = re.split(r"[,xX ]+", save_xy, maxsplit=1)
                x, y = int(float(x_text)), int(float(y_text))
                _verify_exact_save_control_at_point(x, y)
                _click_form_xy(x, y, "ERP 상단 '저장' 툴바 버튼", wait=ERP_SETTLE_WAIT)
                self.logger.info(
                    f"  [SAVE] 정확 검증된 저장 툴바 좌표 클릭 완료: rel=({x},{y})"
                )
                return True
            except Exception as exc:
                coordinate_error = exc
                self.logger.warning(f"  [SAVE] ERP_SAVE_BUTTON_XY 클릭 실패: {exc}")

            if not _env_flag("ERP_SAVE_BUTTON_UIA_FALLBACK", "0"):
                raise RuntimeError(
                    "ERP 저장 툴바 좌표를 정확한 '저장' UI 요소로 검증하지 못해 클릭하지 않았고, "
                    "대량 행 정지를 막기 위해 UIA 전체 탐색 fallback은 기본 비활성화되어 있습니다: "
                    f"{coordinate_error}"
                )

            def _control_texts(control):
                values = []
                for getter in (
                    lambda: control.window_text(),
                    lambda: getattr(getattr(control, "element_info", None), "name", ""),
                ):
                    try:
                        value = re.sub(r"\s+", "", str(getter() or ""))
                    except Exception:
                        value = ""
                    if value and value not in values:
                        values.append(value)
                return values

            def _click_in_scope(scope, label):
                main_r = _main_rect()
                try:
                    controls = scope.descendants()
                except Exception:
                    controls = []
                for control in controls:
                    try:
                        # Exact match deliberately excludes 복사하여저장 and other toolbar actions.
                        if "저장" not in _control_texts(control):
                            continue
                        rect = control.rectangle()
                        if not (main_r.top + 35 <= rect.top <= main_r.top + 135):
                            continue
                        if rect.left > main_r.left + 760:
                            continue
                        if hasattr(control, "is_visible") and not control.is_visible():
                            continue
                        if hasattr(control, "is_enabled") and not control.is_enabled():
                            continue
                        pyautogui.click(
                            rect.left + rect.width() // 2,
                            rect.top + rect.height() // 2,
                        )
                        self.logger.info(
                            f"  [SAVE] {label} 정확한 '저장' 툴바 버튼 클릭: "
                            f"rect=({rect.left},{rect.top})-({rect.right},{rect.bottom})"
                        )
                        time.sleep(ERP_SETTLE_WAIT)
                        return True
                    except Exception as exc:
                        self.logger.warning(f"  [SAVE] {label} 저장 후보 처리 실패: {exc}")
                return False

            try:
                if _click_in_scope(main_win, "main_win"):
                    return True
            except Exception as exc:
                self.logger.warning(f"  [SAVE] main_win 저장 툴바 탐색 실패: {exc}")

            try:
                handle = int(getattr(main_win, "handle", 0) or 0)
            except Exception:
                handle = 0
            if handle:
                for backend in ("uia", "win32"):
                    try:
                        fresh_win = Application(backend=backend).connect(handle=handle).window(handle=handle)
                        if _click_in_scope(fresh_win, f"fresh-{backend}"):
                            return True
                    except Exception as exc:
                        self.logger.warning(f"  [SAVE] fresh-{backend} 저장 툴바 탐색 실패: {exc}")

            raise RuntimeError(
                "ERP 상단 툴바에서 정확한 '저장' 버튼을 찾지 못했습니다. "
                "복사하여저장은 대체 클릭하지 않습니다."
            )

        def _save_current_voucher_via_toolbar():
            save_required = "저장 후 출력해 주십시오."
            save_question_phrases = (
                "저장하시겠습니까",
                "저장 하시겠습니까",
                "저장할까요",
            )
            save_success_phrases = (
                "저장되었습니다",
                "저장이 완료되었습니다",
                "저장완료",
                "정상적으로 저장",
            )

            _assert_no_erp_management_lookup_popup("저장 전")
            stale_message = _find_erp_message_snapshot()
            if stale_message:
                if re.sub(r"\s+", "", save_required).lower() in _erp_message_compact(stale_message):
                    self.logger.warning(
                        "  [SAVE] 이전 출력 시도의 '저장 후 출력' Message를 검증하고 닫습니다."
                    )
                    _dismiss_verified_erp_message(stale_message, (save_required,))
                else:
                    raise RuntimeError(
                        "저장 전 알 수 없는 ERP Message가 열려 있어 저장/출력을 중단합니다: "
                        f"{stale_message.get('text', '')[:500]}"
                    )

            try:
                if main_win.is_minimized():
                    main_win.restore()
            except Exception:
                pass
            try:
                main_win.set_focus()
            except Exception as exc:
                self.logger.warning(f"  [SAVE] 저장 전 ERP 메인 창 활성화 실패: {exc}")
            time.sleep(ERP_SETTLE_WAIT)

            _click_save_button()
            try:
                # 210행급 대형 전표는 저장 처리 후 '자료가 저장되었습니다'
                # 확인창이 수십 초 뒤에 뜰 수 있다. 확인창을 닫지 않고 출력을
                # 시작하면 모달에 막혀 RD Viewer가 열리지 않는다.
                confirmation_timeout = float(
                    os.getenv("ERP_SAVE_CONFIRM_TIMEOUT_SECONDS", "60") or "60"
                )
            except ValueError:
                confirmation_timeout = 60.0
            confirmation = _wait_erp_message(max(1.0, confirmation_timeout))
            if not confirmation:
                self.logger.info(
                    "  [SAVE] 저장 후 별도 Message가 없어 출력 단계로 이동합니다. "
                    "출력 시 '저장 후 출력' Message를 즉시 감지해 최종 검증합니다."
                )
                return True

            compact = _erp_message_compact(confirmation)
            if re.sub(r"\s+", "", save_required).lower() in compact:
                raise RuntimeError(
                    "ERP 저장 클릭 후에도 '저장 후 출력해 주십시오.' Message가 "
                    "표시되어 출력을 중단합니다."
                )
            if any(
                re.sub(r"\s+", "", phrase).lower() in compact
                for phrase in save_question_phrases
            ):
                _dismiss_verified_erp_message(
                    confirmation,
                    save_question_phrases,
                    button_labels=("예", "yes", "확인", "저장"),
                    allow_enter_fallback=False,
                )
                followup = _wait_erp_message(max(1.0, confirmation_timeout))
                if not followup:
                    self.logger.info(
                        "  [SAVE] 저장 질문의 승인 버튼을 클릭했고 후속 Message는 없습니다. "
                        "출력 단계의 '저장 후 출력' 즉시 감지로 최종 검증합니다."
                    )
                    return True
                confirmation = followup
                compact = _erp_message_compact(confirmation)
                if re.sub(r"\s+", "", save_required).lower() in compact:
                    raise RuntimeError(
                        "ERP 저장 질문 승인 후에도 '저장 후 출력해 주십시오.' "
                        "Message가 표시되어 출력을 중단합니다."
                    )
            if not any(
                re.sub(r"\s+", "", phrase).lower() in compact
                for phrase in save_success_phrases
            ):
                raise RuntimeError(
                    "ERP 저장 후 알 수 없는 Message가 표시되어 출력을 중단합니다: "
                    f"{confirmation.get('text', '')[:500]}"
                )

            _dismiss_verified_erp_message(confirmation, save_success_phrases)
            self.logger.info("  [SAVE] ERP 저장 완료 Message 검증 완료; 이제 출력을 허용합니다.")
            return True

        def _wait_rd_viewer_ready(timeout_sec=10, phase="", baseline=None):
            end_at = time.time() + max(0.0, float(timeout_sec or 0.0))
            last_pending_pids = None
            while True:
                erp_message = _find_erp_message_snapshot()
                if "저장후출력해주십시오." in _erp_message_compact(erp_message):
                    self.logger.error(
                        "  [PRINT] ERP Message '저장 후 출력해 주십시오.'를 즉시 감지했습니다."
                    )
                    raise RuntimeError(
                        "ERP 전표가 저장되지 않아 출력할 수 없습니다: "
                        "저장 후 출력해 주십시오."
                    )
                new_processes = _new_rd_viewer_processes(baseline)
                new_pids = {int(proc.pid) for proc, _name in new_processes}
                win, backend, title, window_meta = _find_fresh_rd_viewer_window(
                    baseline,
                    preferred_pids=new_pids,
                )
                if win is not None:
                    self.logger.info(
                        f"  [PRINT] 신규 RD Viewer 창 감지 완료: phase={phase}, "
                        f"backend={backend}, pid={window_meta.get('pid')}, title={title}"
                    )
                    return {
                        "source": "title",
                        "window": win,
                        "backend": backend,
                        "title": title,
                        "pid": int(window_meta.get("pid") or 0),
                        "process_name": next(
                            (
                                name
                                for proc, name in new_processes
                                if int(proc.pid) == int(window_meta.get("pid") or 0)
                            ),
                            "",
                        ),
                        "window_identity": window_meta.get("identity"),
                        "baseline": baseline or {"processes": {}, "windows": []},
                    }

                pending_pids = tuple(sorted(new_pids))
                if pending_pids and pending_pids != last_pending_pids:
                    self.logger.info(
                        "  [PRINT] 신규 RD Viewer 프로세스는 시작됐지만 "
                        f"표시 가능한 새 창을 대기합니다: phase={phase}, pids={list(pending_pids)}"
                    )
                last_pending_pids = pending_pids

                if time.time() >= end_at:
                    break
                time.sleep(ERP_CLICK_WAIT)

            self.logger.warning(
                f"  [PRINT] RD Viewer 준비 감지 시간초과: phase={phase}, "
                f"timeout={float(timeout_sec or 0.0):.1f}s"
            )
            return None

        def _click_print_button():
            def _ui_text(el):
                values = []
                try:
                    values.append(el.window_text() or "")
                except:
                    pass
                try:
                    values.append(getattr(el.element_info, "name", "") or "")
                except:
                    pass
                normalized = []
                for value in values:
                    text = re.sub(r"\s+", "", str(value or ""))
                    if text and text not in normalized:
                        normalized.append(text)
                return normalized

            def _toolbar_snapshot(scope, label):
                try:
                    main_r = _main_rect()
                    items = []
                    for el in scope.descendants():
                        try:
                            r = el.rectangle()
                            if not (main_r.top + 35 <= r.top <= main_r.top + 135):
                                continue
                            text = "/".join(_ui_text(el))
                            if text:
                                items.append(f"{text}@({r.left},{r.top})-({r.right},{r.bottom})")
                        except:
                            pass
                    if items:
                        self.logger.info(f"  [PRINT] {label} toolbar candidates: {' | '.join(items[:40])}")
                except Exception as e:
                    self.logger.warning(f"  [PRINT] {label} toolbar snapshot 실패: {e}")

            def _click_print_in_scope(scope, label):
                main_r = _main_rect()
                for el in scope.descendants():
                    try:
                        texts = _ui_text(el)
                        if "전표출력" not in texts:
                            continue
                        r = el.rectangle()
                        if not (main_r.top + 35 <= r.top <= main_r.top + 135):
                            self.logger.warning(
                                f"  [PRINT] 전표출력 후보 무시: toolbar 영역 밖 rect=({r.left},{r.top})-({r.right},{r.bottom})"
                            )
                            continue
                        if r.left > main_r.left + 760:
                            self.logger.warning(
                                f"  [PRINT] 전표출력 후보 무시: 변경내역 영역에 가까움 rect=({r.left},{r.top})-({r.right},{r.bottom})"
                            )
                            continue
                        pyautogui.click(r.left + r.width() // 2, r.top + r.height() // 2)
                        self.logger.info(
                            f"  [PRINT] {label} UI 요소로 전표출력 클릭: rect=({r.left},{r.top})-({r.right},{r.bottom})"
                        )
                        time.sleep(ERP_SETTLE_WAIT)
                        return True
                    except Exception as e:
                        self.logger.warning(f"  [PRINT] {label} 전표출력 후보 처리 실패: {e}")
                _toolbar_snapshot(scope, label)
                return False

            try:
                if _click_print_in_scope(main_win, "main_win"):
                    return True
            except Exception as e:
                self.logger.warning(f"  [PRINT] 전표출력 main_win 탐색 실패: {e}")

            handle = None
            try:
                handle = main_win.handle
            except:
                handle = None
            if handle:
                for backend in ("uia", "win32"):
                    try:
                        fresh_win = Application(backend=backend).connect(handle=handle).window(handle=handle)
                        if _click_print_in_scope(fresh_win, f"fresh-{backend}"):
                            return True
                    except Exception as e:
                        self.logger.warning(f"  [PRINT] 전표출력 fresh-{backend} 탐색 실패: {e}")

            if _env_flag("ERP_DISABLE_PRINT_BUTTON_XY_FALLBACK", "0"):
                raise RuntimeError("전표출력 버튼을 UIA로 찾지 못했고 좌표 fallback이 비활성화되어 있습니다.")

            override_xy = os.getenv("ERP_PRINT_BUTTON_XY", "620,80").strip()
            try:
                x_text, y_text = re.split(r"[,xX ]+", override_xy, maxsplit=1)
                x, y = int(float(x_text)), int(float(y_text))
                _click_form_xy(x, y, "전표출력 검증형 좌표 fallback")
                self.logger.warning(f"  [PRINT] UIA 미검출, ERP 메인창 기준 좌표 fallback 클릭: rel=({x},{y})")
                time.sleep(ERP_SETTLE_WAIT)
                return True
            except Exception as e:
                self.logger.warning(f"  [PRINT] ERP_PRINT_BUTTON_XY 파싱/클릭 실패: {e}")
                raise RuntimeError("전표출력 버튼을 UIA/좌표 fallback 모두에서 클릭하지 못했습니다.") from e

        def _ask_print_target():
            override = getattr(self.manager.main_app, "print_choice_override", None)
            if override:
                self.logger.info(f"  [PRINT] 원클릭 출력 대상 사용: {override}")
                return dict(override)
            result = {"choice": None}
            root = getattr(self.manager, "root", None)
            parent = root if root else None
            dialog = tk.Toplevel(parent)
            dialog.title("출력 프린터 선택")
            dialog.geometry("360x250")
            dialog.resizable(False, False)
            dialog.attributes("-topmost", True)
            dialog.grab_set()

            tk.Label(
                dialog,
                text="어떤 프린터로 출력할까요?",
                font=("맑은 고딕", 12, "bold")
            ).pack(pady=(18, 10))

            def choose(choice):
                result["choice"] = choice
                dialog.destroy()

            buttons = [(f"{opt['label']} 출력", dict(opt)) for opt in PRINT_TARGET_OPTIONS]
            buttons.append(("닫기 : 출력안함", None))

            for text, choice in buttons:
                tk.Button(
                    dialog,
                    text=text,
                    width=24,
                    height=1,
                    command=lambda c=choice: choose(c)
                ).pack(pady=4)

            dialog.protocol("WM_DELETE_WINDOW", lambda: choose(None))
            dialog.focus_force()
            dialog.wait_window()
            self.logger.info(f"  [PRINT] 담당자 출력 선택: {result['choice']}")
            return result["choice"]

        def _wait_print_dialog(timeout_sec=10):
            end_at = time.time() + timeout_sec
            while time.time() < end_at:
                for backend in ("win32", "uia"):
                    try:
                        for w in Desktop(backend=backend).windows():
                            title = (w.window_text() or "").strip()
                            if title in ("인쇄", "Print") or "인쇄" in title:
                                try:
                                    w.set_focus()
                                except:
                                    pass
                                self.logger.info(f"  [PRINT] 인쇄창 감지 완료: backend={backend}, title={title}")
                                return w
                    except:
                        pass
                time.sleep(ERP_CLICK_WAIT)
            self.logger.warning("  [PRINT] 인쇄창 감지 시간초과")
            return None

        def _wait_pdf_save_dialog(timeout_sec=10):
            end_at = time.time() + timeout_sec
            title_patterns = (
                "save print output as",
                "print output",
                "printer output",
                "다음 이름으로 프린터 출력 저장",
                "프린터 출력 저장",
                "인쇄 출력 저장",
                "출력 저장",
            )
            while time.time() < end_at:
                for backend in ("win32", "uia"):
                    try:
                        for w in Desktop(backend=backend).windows():
                            title = (w.window_text() or "").strip()
                            title_lower = title.lower()
                            title_match = any(pattern in title_lower for pattern in title_patterns[:3])
                            title_match = title_match or any(pattern in title for pattern in title_patterns[3:])
                            blob = ""
                            if not title_match:
                                try:
                                    blob = _dialog_text_blob(w)
                                except Exception:
                                    blob = ""
                                title_match = (
                                    ("파일 이름" in blob or "File name" in blob)
                                    and ("PDF" in blob or "*.pdf" in blob or "문서" in blob)
                                    and ("저장" in blob or "Save" in blob)
                                )
                            if title_match:
                                try:
                                    w.set_focus()
                                except:
                                    pass
                                self.logger.info(f"  [PRINT] PDF 저장창 감지 완료: backend={backend}, title={title}")
                                return w
                    except:
                        pass
                time.sleep(ERP_CLICK_WAIT)
            self.logger.warning("  [PRINT] PDF 저장창 감지 시간초과")
            return None

        def _focus_rd_viewer_window(timeout_sec=8, ready_hint=None):
            def _focus_window(win, backend, title, source):
                try:
                    win.restore()
                except Exception:
                    pass
                try:
                    win.set_focus()
                except Exception:
                    pass
                try:
                    r = win.rectangle()
                    pyautogui.click(r.left + 40, r.top + 15)
                except Exception:
                    pass
                self.logger.info(
                    f"  [PRINT] RD Viewer 포커스 완료: source={source}, "
                    f"backend={backend}, title={title}"
                )
                return win

            hinted_window = (ready_hint or {}).get("window")
            if hinted_window is not None:
                try:
                    return _focus_window(
                        hinted_window,
                        (ready_hint or {}).get("backend", "ready-hint"),
                        (ready_hint or {}).get("title", ""),
                        "ready-title",
                    )
                except Exception:
                    pass

            strict_baseline = (ready_hint or {}).get("baseline")
            hinted_pid = int((ready_hint or {}).get("pid") or 0)
            end_at = time.time() + timeout_sec
            while time.time() < end_at:
                if strict_baseline is not None:
                    preferred_pids = {hinted_pid} if hinted_pid else set()
                    win, backend, title, _meta = _find_fresh_rd_viewer_window(
                        strict_baseline,
                        preferred_pids=preferred_pids,
                    )
                else:
                    win, backend, title = _find_rd_viewer_window()
                if win is not None:
                    try:
                        return _focus_window(
                            win,
                            backend,
                            title,
                            "fresh-title" if strict_baseline is not None else "title",
                        )
                    except Exception:
                        pass

                if strict_baseline is not None:
                    # Never replace the verified fresh window with a stale Viewer
                    # merely because the old process is still alive.
                    time.sleep(ERP_CLICK_WAIT)
                    continue

                proc, process_name = _find_rd_viewer_process()
                pid = hinted_pid or (int(proc.pid) if proc is not None else None)
                if pid:
                    for process_backend in ("win32", "uia"):
                        try:
                            app = Application(backend=process_backend).connect(process=int(pid))
                            for process_win in app.windows():
                                try:
                                    if not process_win.is_visible():
                                        continue
                                except Exception:
                                    pass
                                try:
                                    process_title = (process_win.window_text() or "").strip()
                                except Exception:
                                    process_title = ""
                                return _focus_window(
                                    process_win,
                                    process_backend,
                                    process_title,
                                    f"pid={pid},name={process_name or (ready_hint or {}).get('process_name', '')}",
                                )
                        except Exception:
                            pass

                time.sleep(ERP_CLICK_WAIT)
            self.logger.warning("  [PRINT] RD Viewer 창 포커스 시간초과")
            return None

        def _close_rd_viewer(timeout_sec=5):
            """전표 출력 후 열린 Report Designer Viewer 창을 정리합니다."""
            closed = False
            end_at = time.time() + timeout_sec
            title_re = r".*(Report Designer Viewer|RD Viewer|Designer Viewer).*"

            while time.time() < end_at:
                found_any = False
                for backend in ("win32", "uia"):
                    try:
                        for win in Desktop(backend=backend).windows():
                            title = (win.window_text() or "").strip()
                            if not re.search(title_re, title, re.I):
                                continue
                            found_any = True
                            try:
                                win.set_focus()
                            except Exception:
                                pass
                            try:
                                win.close()
                                closed = True
                                self.logger.info(f"  [PRINT] RD Viewer 창 닫기 완료: {title}")
                                time.sleep(0.5)
                                continue
                            except Exception:
                                pass
                            try:
                                r = win.rectangle()
                                pyautogui.click(r.right - 18, r.top + 16)
                                closed = True
                                self.logger.info(f"  [PRINT] RD Viewer 닫기 좌표 fallback 완료: {title}")
                                time.sleep(0.5)
                            except Exception as e:
                                self.logger.warning(f"  [PRINT] RD Viewer 창 닫기 실패: {title} / {e}")
                    except Exception:
                        pass
                if not found_any:
                    break
                time.sleep(0.3)

            try:
                for proc in psutil.process_iter(["pid", "name"]):
                    name = (proc.info.get("name") or "").lower()
                    if name != "rdviewer_u.exe":
                        continue
                    try:
                        proc.terminate()
                        closed = True
                        self.logger.info(f"  [PRINT] 남은 RD Viewer 프로세스 종료 요청: pid={proc.pid}")
                    except Exception as e:
                        self.logger.warning(f"  [PRINT] RD Viewer 프로세스 종료 실패: pid={proc.pid} / {e}")
            except Exception:
                pass
            return closed

        def _save_pdf_output_dialog(save_path):
            dialog = _wait_pdf_save_dialog(timeout_sec=15)
            if not dialog:
                return False

            if not save_path:
                self.logger.warning("  [PRINT] ERP PDF 저장 경로가 비어 있어 저장을 중단합니다.")
                return False
            norm_path = os.path.abspath(save_path)
            os.makedirs(os.path.dirname(norm_path), exist_ok=True)
            pdf_started_at = time.time()
            try:
                pdf_wait_seconds = max(30.0, float(os.getenv("ERP_PDF_SAVE_WAIT_SECONDS", "90") or "90"))
            except Exception:
                pdf_wait_seconds = 90.0
            try:
                if os.path.exists(norm_path):
                    os.remove(norm_path)
            except Exception as e:
                self.logger.warning(f"  [PRINT] 기존 ERP PDF 삭제 실패: {norm_path} / {e}")
            try:
                edits = dialog.descendants(control_type="Edit")
                target_edit = edits[-1] if edits else None
            except:
                target_edit = None

            old_clipboard = ""
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                old_clipboard = ""

            def _restore_pdf_clipboard():
                try:
                    if old_clipboard:
                        pyperclip.copy(old_clipboard)
                except Exception:
                    pass

            def _is_stable_pdf(path, interval=0.5):
                try:
                    size1 = os.path.getsize(path)
                    time.sleep(interval)
                    size2 = os.path.getsize(path)
                    return size1 == size2 and size2 > 0
                except Exception:
                    return False

            def _recover_misplaced_pdf():
                target = Path(norm_path)
                roots = [
                    target.parent,
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
                        candidates.extend(root.glob(target.name))
                        candidates.extend(root.glob(f"**/{target.name}"))
                    except Exception:
                        continue
                    try:
                        candidates = sorted(
                            set(candidates),
                            key=lambda p: p.stat().st_mtime if p.exists() else 0,
                            reverse=True,
                        )
                    except Exception:
                        pass
                    for candidate in candidates:
                        try:
                            if candidate.resolve() == target.resolve():
                                continue
                            if candidate.suffix.lower() != ".pdf" or candidate.name != target.name:
                                continue
                            if candidate.stat().st_mtime < pdf_started_at - 10:
                                continue
                            if not _is_stable_pdf(str(candidate), interval=0.5):
                                continue
                            target.parent.mkdir(parents=True, exist_ok=True)
                            if target.exists():
                                target.unlink()
                            candidate.replace(target)
                            self.logger.info(f"  [PRINT] misplaced PDF recovered: {candidate} -> {target}")
                            return True
                        except Exception:
                            continue
                return False

            def _wait_pdf_created(timeout_sec=20):
                end_at = time.time() + timeout_sec
                while time.time() < end_at:
                    if os.path.exists(norm_path) and _is_stable_pdf(norm_path, interval=0.3):
                        getattr(self.manager.main_app, "last_erp_print_output", "")
                        self.manager.main_app.last_erp_print_output = norm_path
                        self.logger.info(f"  [PRINT] ERP PDF saved: {norm_path}")
                        return True
                    if _recover_misplaced_pdf():
                        getattr(self.manager.main_app, "last_erp_print_output", "")
                        self.manager.main_app.last_erp_print_output = norm_path
                        self.logger.info(f"  [PRINT] ERP PDF saved after recovery: {norm_path}")
                        return True
                    time.sleep(0.4)
                return False

            def _save_pdf_by_filename_edit():
                def _edit_candidates(save_dialog):
                    candidates = []
                    seen = set()
                    for query in ({"control_type": "Edit"}, {"class_name": "Edit"}):
                        try:
                            controls = save_dialog.descendants(**query)
                        except Exception:
                            controls = []
                        for edit in controls:
                            try:
                                r = edit.rectangle()
                                key = (r.left, r.top, r.right, r.bottom)
                                if key in seen:
                                    continue
                                seen.add(key)
                                if r.width() < 180 or r.height() < 14:
                                    continue
                                candidates.append((r, edit))
                            except Exception:
                                continue
                    return candidates

                try:
                    save_dialog = _wait_pdf_save_dialog(timeout_sec=1) or dialog
                    save_dialog.set_focus()
                    dlg_r = save_dialog.rectangle()
                    dlg_h = max(1, dlg_r.bottom - dlg_r.top)
                    lower_top = dlg_r.top + int(dlg_h * 0.55)
                    candidates = _edit_candidates(save_dialog)
                    lower_candidates = [(r, edit) for r, edit in candidates if r.top >= lower_top]
                    if lower_candidates:
                        # In the common Save As dialog the file-name edit is the first wide edit
                        # in the lower form area; the file-type combo usually sits below it.
                        target_r, target_edit = sorted(
                            lower_candidates,
                            key=lambda item: (item[0].top, -item[0].width()),
                        )[0]
                    elif candidates:
                        target_r, target_edit = sorted(
                            candidates,
                            key=lambda item: (-item[0].width(), item[0].top),
                        )[0]
                    else:
                        self.logger.warning("  [PRINT] PDF 저장창 파일명 입력칸 후보를 찾지 못했습니다.")
                        return False

                    try:
                        target_edit.set_focus()
                    except Exception:
                        pass
                    try:
                        target_edit.click_input()
                    except Exception:
                        pyautogui.click(
                            target_r.left + target_r.width() // 2,
                            target_r.top + target_r.height() // 2,
                        )
                    time.sleep(0.2)
                    pyperclip.copy(norm_path)
                    pyautogui.hotkey("ctrl", "a")
                    time.sleep(0.05)
                    pyautogui.press("backspace")
                    time.sleep(0.05)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.15)
                    pyautogui.press("enter")
                    self.logger.info(
                        f"  [PRINT] PDF 파일명 입력칸 직접 저장 시도: rect=({target_r.left},{target_r.top})-({target_r.right},{target_r.bottom}), path={norm_path}"
                    )
                except Exception as e:
                    self.logger.warning(f"  [PRINT] PDF 파일명 입력칸 직접 저장 실패: {e}")
                    return False

                if _wait_pdf_created(timeout_sec=12):
                    return True

                for _ in range(4):
                    try:
                        pyautogui.press("enter")
                    except Exception:
                        pass
                    if _wait_pdf_created(timeout_sec=3):
                        return True
                return False

            def _save_pdf_by_common_dialog_hotkeys():
                folder = os.path.dirname(norm_path)
                filename = os.path.basename(norm_path)
                for attempt in range(1, 4):
                    try:
                        save_dialog = _wait_pdf_save_dialog(timeout_sec=1) or dialog
                        save_dialog.set_focus()
                    except Exception:
                        save_dialog = dialog
                    time.sleep(0.25)
                    try:
                        for key in ("alt", "ctrl", "shift", "win"):
                            pyautogui.keyUp(key)

                        pyperclip.copy(folder)
                        pyautogui.hotkey("alt", "d")
                        time.sleep(0.10)
                        pyautogui.hotkey("ctrl", "a")
                        time.sleep(0.05)
                        pyautogui.hotkey("ctrl", "v")
                        time.sleep(0.10)
                        pyautogui.press("enter")
                        time.sleep(0.90)

                        pyperclip.copy(filename)
                        pyautogui.hotkey("alt", "n")
                        time.sleep(0.10)
                        pyautogui.hotkey("ctrl", "a")
                        time.sleep(0.05)
                        pyautogui.hotkey("ctrl", "v")
                        time.sleep(0.15)
                        pyautogui.hotkey("alt", "s")
                        self.logger.info(
                            f"  [PRINT] PDF Save As folder/name sent ({attempt}/3): folder={folder}, filename={filename}"
                        )
                    except Exception as e:
                        self.logger.warning(f"  [PRINT] PDF Save As hotkey path failed ({attempt}/3): {e}")
                        continue

                    for _ in range(8):
                        try:
                            overwrite = _wait_pdf_save_dialog(timeout_sec=0.2)
                            if not overwrite:
                                break
                            blob = _dialog_text_blob(overwrite)
                            if not any(token in blob for token in ("이미", "바꾸", "덮어", "already", "replace", "overwrite")):
                                break
                            pyautogui.press("left")
                            pyautogui.press("enter")
                            self.logger.info("  [PRINT] existing PDF overwrite confirmed")
                            break
                        except Exception:
                            try:
                                pyautogui.press("enter")
                            except Exception:
                                pass
                            break

                    if _wait_pdf_created(timeout_sec=min(20, pdf_wait_seconds)):
                        return True
                return False

            if _save_pdf_by_common_dialog_hotkeys():
                _restore_pdf_clipboard()
                return True

            if _save_pdf_by_filename_edit():
                _restore_pdf_clipboard()
                return True

            if target_edit is not None:
                try:
                    dialog.set_focus()
                except Exception:
                    pass
                try:
                    target_edit.set_focus()
                except Exception:
                    pass
                try:
                    target_edit.click_input()
                except Exception:
                    pass
                try:
                    pyperclip.copy(norm_path)
                    pyautogui.hotkey("ctrl", "a")
                    time.sleep(0.05)
                    pyautogui.press("backspace")
                    time.sleep(0.05)
                    pyautogui.hotkey("ctrl", "v")
                    self.logger.info(f"  [PRINT] PDF 저장 경로 입력 완료: {norm_path}")
                except Exception:
                    try:
                        target_edit.set_edit_text(norm_path)
                        self.logger.info(f"  [PRINT] PDF 저장 경로 set_edit_text 완료: {norm_path}")
                    except Exception as e:
                        self.logger.warning(f"  [PRINT] PDF 저장 경로 입력 실패: {e}")
                        pass
            else:
                try:
                    pyperclip.copy(norm_path)
                    pyautogui.hotkey("ctrl", "v")
                    self.logger.info(f"  [PRINT] PDF 저장 경로 붙여넣기 fallback 완료: {norm_path}")
                except Exception:
                    pyautogui.write(norm_path, interval=0.01)

            time.sleep(ERP_BLOCK_WAIT)
            clicked_save = False
            try:
                for btn in dialog.descendants(control_type="Button"):
                    btn_text = (btn.window_text() or "").strip()
                    if "저장" in btn_text or btn_text.lower() in ("save", "&save"):
                        btn.click_input()
                        clicked_save = True
                        self.logger.info("  [PRINT] PDF 저장 버튼 클릭 완료")
                        break
                if not clicked_save:
                    pyautogui.press("enter")
                    self.logger.info("  [PRINT] PDF 저장 Enter fallback 완료")
            except:
                pyautogui.press("enter")
                self.logger.info("  [PRINT] PDF 저장 Enter fallback 완료")

            for _ in range(8):
                time.sleep(0.25)
                overwrite = _wait_pdf_save_dialog(timeout_sec=0.1)
                if not overwrite:
                    break
                blob = _dialog_text_blob(overwrite)
                if not any(token in blob for token in ("이미", "바꾸", "덮어", "already", "replace", "overwrite")):
                    break
                try:
                    pyautogui.press("left")
                    pyautogui.press("enter")
                except Exception:
                    pyautogui.press("enter")
                self.logger.info("  [PRINT] 기존 PDF 덮어쓰기 확인 완료")

            if _wait_pdf_created(timeout_sec=pdf_wait_seconds):
                _restore_pdf_clipboard()
                self.logger.info(f"  [PRINT] ERP PDF 저장 완료: {norm_path}")
                return True
            _restore_pdf_clipboard()
            self.logger.warning(f"  [PRINT] ERP PDF 저장 대기 시간초과: {norm_path}")
            return False

        def _dialog_text_blob(dialog):
            chunks = []
            try:
                chunks.append(dialog.window_text() or "")
                for el in dialog.descendants():
                    try:
                        txt = el.window_text() or ""
                        if txt:
                            chunks.append(txt)
                    except:
                        pass
            except:
                pass
            return "\n".join(chunks)

        def _print_target_matches(blob, target):
            target = str(target or "").strip()
            if not target:
                return False
            # IP는 172.17.30.162_1 같은 변형 장치를 제외하고 정확히 독립 토큰만 인정한다.
            if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", target):
                pattern = rf"(?<![0-9A-Za-z_.-]){re.escape(target)}(?![0-9A-Za-z_.-])"
                return re.search(pattern, blob or "") is not None
            return target.casefold() in (blob or "").casefold()

        def _select_printer_in_dialog(choice):
            if not choice:
                self.logger.info("  [PRINT] 출력안함 선택. Ctrl+P/인쇄를 진행하지 않습니다.")
                return False

            try:
                print_dialog_timeout = float(os.getenv("ERP_PRINT_DIALOG_TIMEOUT_SECONDS", "25") or "25")
            except ValueError:
                print_dialog_timeout = 25.0
            dialog = _wait_print_dialog(timeout_sec=print_dialog_timeout)
            if not dialog:
                return False

            target = str(choice.get("match", "")).strip()
            self.logger.info(f"  [PRINT] 프린터 선택 시작: {choice.get('label')} / match={target}")

            combo = None
            try:
                combos = dialog.descendants(control_type="ComboBox")
                if combos:
                    combo = combos[0]
            except:
                pass

            if combo is None:
                try:
                    combos = dialog.descendants(class_name="ComboBox")
                    if combos:
                        combo = combos[0]
                except:
                    pass

            if combo is None:
                self.logger.warning("  [PRINT] 프린터 ComboBox를 찾지 못했습니다.")
                return False

            item_count = 0
            try:
                item_count = combo.item_count()
            except:
                try:
                    item_count = len(combo.item_texts())
                except:
                    item_count = 0

            selected = False
            for idx in range(max(0, item_count)):
                try:
                    combo.select(idx)
                except:
                    try:
                        combo.type_keys("{HOME}" + "{DOWN}" * idx + "{ENTER}")
                    except:
                        pass
                time.sleep(ERP_FORM_WAIT)

                blob = _dialog_text_blob(dialog)
                try:
                    current_name = combo.window_text() or ""
                except:
                    current_name = ""
                if _print_target_matches(f"{current_name}\n{blob}", target):
                    selected = True
                    self.logger.info(f"  [PRINT] 프린터 매칭 성공: idx={idx}, current={current_name}")
                    break

            if not selected:
                self.logger.warning(f"  [PRINT] 프린터 매칭 실패: {target}")
                return False

            try:
                for btn in dialog.descendants(control_type="Button"):
                    if (btn.window_text() or "").strip() in ("확인", "OK"):
                        btn.click_input()
                        self.logger.info("  [PRINT] 인쇄 확인 버튼 클릭 완료")
                        break
                else:
                    pyautogui.press("enter")
                    self.logger.info("  [PRINT] 인쇄 확인 Enter fallback 완료")
            except:
                pyautogui.press("enter")
                self.logger.info("  [PRINT] 인쇄 확인 Enter fallback 완료")

            if choice.get("kind") == "pdf_merge":
                return _save_pdf_output_dialog(choice.get("save_path", ""))
            return True

        def _save_and_open_print_dialog():
            if _env_flag("ERP_VERIFY_GRID_PASTE", "0") and not grid_paste_state.get("verified"):
                self.logger.warning("  [SAVE] 그리드 붙여넣기 검증 미완료 상태지만 저장/전표출력을 계속 진행합니다.")
            try:
                if _env_flag("ERP_RESUME_PRINT_ONLY", "0"):
                    self.logger.info(
                        "  [PRINT-RESUME] 이미 저장된 현재 전표를 유지하고 Ctrl+S를 생략합니다."
                    )
                    try:
                        main_win.set_focus()
                    except Exception:
                        pass
                    time.sleep(ERP_SETTLE_WAIT)
                elif _env_flag("ERP_RESUME_MANAGEMENT_SAVE_PRINT", "0"):
                    self.logger.info(
                        "  [MANAGEMENT-RECOVERY] 관리항목 복구 후 실제 '저장' 툴바 버튼으로 저장합니다."
                    )
                    _save_current_voucher_via_toolbar()
                else:
                    self.logger.info(
                        "  [SAVE] 신규 전표를 실제 '저장' 툴바 버튼으로 저장하고 결과를 검증합니다."
                    )
                    _save_current_voucher_via_toolbar()

                _assert_no_erp_management_lookup_popup("출력 전")
                print_runtime_baseline = _capture_print_runtime()
                self.logger.info("  [PRINT] ERP 전표출력 Ctrl+P 전송")
                pyautogui.hotkey('ctrl', 'p')
                time.sleep(ERP_SETTLE_WAIT)

                try:
                    viewer_base_timeout = float(
                        os.getenv("ERP_PRINT_VIEWER_DETECT_TIMEOUT_SECONDS", "45") or "45"
                    )
                except ValueError:
                    viewer_base_timeout = 45.0
                try:
                    viewer_seconds_per_row = float(
                        os.getenv("ERP_PRINT_VIEWER_SECONDS_PER_ROW", "0.8") or "0.8"
                    )
                except ValueError:
                    viewer_seconds_per_row = 0.8
                try:
                    configured_viewer_cap = float(
                        os.getenv("ERP_PRINT_VIEWER_TIMEOUT_CAP_SECONDS", "300") or "300"
                    )
                except ValueError:
                    configured_viewer_cap = 300.0
                viewer_cap = min(300.0, max(45.0, configured_viewer_cap))
                effective_row_count = max(1, int(row_count or 1))
                viewer_timeout = min(
                    viewer_cap,
                    max(
                        1.0,
                        viewer_base_timeout,
                        effective_row_count * max(0.0, viewer_seconds_per_row),
                    ),
                )

                try:
                    initial_base_timeout = float(
                        os.getenv("ERP_PRINT_VIEWER_INITIAL_DETECT_TIMEOUT_SECONDS", "8") or "8"
                    )
                except ValueError:
                    initial_base_timeout = 8.0
                try:
                    initial_seconds_per_row = float(
                        os.getenv("ERP_PRINT_VIEWER_INITIAL_SECONDS_PER_ROW", "0.5") or "0.5"
                    )
                except ValueError:
                    initial_seconds_per_row = 0.5
                try:
                    initial_cap = float(
                        os.getenv("ERP_PRINT_VIEWER_INITIAL_TIMEOUT_CAP_SECONDS", "120") or "120"
                    )
                except ValueError:
                    initial_cap = 120.0
                initial_viewer_timeout = min(
                    viewer_timeout,
                    max(
                        0.5,
                        initial_base_timeout,
                        min(
                            max(0.5, initial_cap),
                            effective_row_count * max(0.0, initial_seconds_per_row),
                        ),
                    ),
                )
                self.logger.info(
                    "  [PRINT] RD Viewer 행 수 기반 동적 대기: "
                    f"rows={effective_row_count}, initial={initial_viewer_timeout:.1f}s, "
                    f"total={viewer_timeout:.1f}s, cap={viewer_cap:.1f}s"
                )

                viewer_ready = _wait_rd_viewer_ready(
                    timeout_sec=initial_viewer_timeout,
                    phase="Ctrl+P",
                    baseline=print_runtime_baseline,
                )
                if not viewer_ready:
                    _log_print_runtime_delta("Ctrl+P timeout", print_runtime_baseline)
                    pending_new_processes = _new_rd_viewer_processes(print_runtime_baseline)
                    if pending_new_processes:
                        pending_pids = [int(proc.pid) for proc, _name in pending_new_processes]
                        retry_phase = "신규 RD Viewer 창 렌더링 대기"
                        self.logger.warning(
                            "  [PRINT] Ctrl+P 후 신규 RD Viewer 프로세스가 렌더링 중이므로 "
                            f"중복 출력 클릭을 생략하고 새 창을 계속 대기합니다: pids={pending_pids}"
                        )
                    else:
                        retry_phase = "전표출력 버튼 fallback"
                        self.logger.warning(
                            "  [PRINT] Ctrl+P로 신규 RD Viewer 프로세스/창이 생성되지 않아 "
                            "기존 전표출력 버튼을 1회 재시도합니다."
                        )
                        try:
                            if main_win.is_minimized():
                                main_win.restore()
                        except Exception:
                            pass
                        try:
                            main_win.set_focus()
                            self.logger.info("  [PRINT] 출력 버튼 fallback 전 ERP 메인 창 활성화 완료")
                        except Exception as e:
                            self.logger.warning(f"  [PRINT] 출력 버튼 fallback 전 ERP 메인 창 활성화 실패: {e}")
                        time.sleep(ERP_SETTLE_WAIT)
                        _click_print_button()
                        _log_print_runtime_delta(
                            "전표출력 버튼 클릭 직후",
                            print_runtime_baseline,
                        )
                    remaining_viewer_timeout = max(
                        0.5,
                        viewer_timeout - initial_viewer_timeout,
                    )
                    viewer_ready = _wait_rd_viewer_ready(
                        timeout_sec=remaining_viewer_timeout,
                        phase=retry_phase,
                        baseline=print_runtime_baseline,
                    )

                if not viewer_ready:
                    _log_print_runtime_delta(
                        "전표출력 버튼 fallback timeout",
                        print_runtime_baseline,
                    )
                    _save_print_timeout_screenshot()
                    raise RuntimeError("전표출력 후 RD Viewer가 감지되지 않아 인쇄를 중단합니다.")
                if not _focus_rd_viewer_window(timeout_sec=10, ready_hint=viewer_ready):
                    raise RuntimeError("RD Viewer 준비는 감지됐지만 창 포커스를 잡지 못했습니다.")
                time.sleep(ERP_PRINT_VIEWER_WAIT)

                choice = _ask_print_target()
                if not choice:
                    self.logger.info("  [PRINT] 담당자가 출력안함을 선택하여 인쇄를 중단합니다.")
                    return

                self.logger.info("  [PRINT] RD Viewer Ctrl+P 전송")
                if not _focus_rd_viewer_window(timeout_sec=8, ready_hint=viewer_ready):
                    raise RuntimeError("RD Viewer 창을 찾지 못해 Ctrl+P를 전송하지 못했습니다.")
                pyautogui.hotkey('ctrl', 'p')
                time.sleep(ERP_BLOCK_WAIT)
                self.logger.info("  [PRINT] 인쇄 프린터 선택창 호출 완료")
                printed = _select_printer_in_dialog(choice)
                if printed:
                    time.sleep(ERP_SETTLE_WAIT)
                    _close_rd_viewer(timeout_sec=8)
                else:
                    raise RuntimeError("RD Viewer 인쇄/PDF 저장 단계가 실패했습니다.")
            except Exception as e:
                self.logger.warning(f"  [SAVE/PRINT] 자동 저장/출력 흐름 실패: {e}")
                raise

        def _setup_by_coordinates_only():
            nonlocal main_rect_cache
            self._force_erp_window_maximized(main_win, "좌표 전용 폼 세팅 전 ERP 메인 창")
            main_rect_cache = None
            self.logger.info("  [FORM-XY] 좌표 전용 폼 세팅 시작")
            acc_unit_xy = (237, 124)
            slip_unit_xy = (512, 124)
            invoice_date_xy = (237, 149)
            first_account_cell_xy = (229, 239)

            # 1. 신규 버튼은 폼 진입 직후 상단 공통 초기화 단계에서 처리합니다.
            # 2. 전표관리단위: 사업장 코드를 먼저 입력해서 열린 메뉴/포커스를 정리합니다.
            if site_name:
                slip_unit = _site_code(site_name)
                _type_anchor_field("전표관리단위", slip_unit, slip_unit_xy, clear=True, enter=True, tab=False)

            # 3. 회계단위: 전표관리단위 입력 후 드롭박스를 열어 사업장을 선택합니다.
            if site_name:
                _select_acc_unit_by_coord(site_name)

            # 4. 회계일: 세금계산서 작성일자 그대로 yyyy-mm-dd 타이핑
            _type_anchor_field("회계일", invoice_date, invoice_date_xy, clear=True, enter=True, date_mode=True)

            # 5. 그리드용 클립보드 복구 후 행추가
            pyperclip.copy(original_clipboard)
            time.sleep(ERP_FORM_WAIT)
            add_clicks = max(0, row_count - 1)
            self.logger.info(f"  [FORM-XY] 행추가 시작: {add_clicks}회")
            _click_add_row(add_clicks, (1856, 386))

            # 6. 그리드 첫 계정과목 셀에 계정과목/금액/적요 행 전체를 입력합니다.
            excel_copy_used = _copy_grid_rows_via_excel()
            if not excel_copy_used:
                pyperclip.copy(original_clipboard)
                time.sleep(ERP_FORM_WAIT)
            first_clipboard_row = next((line for line in str(original_clipboard or "").splitlines() if line.strip()), "")
            first_clipboard_cols = first_clipboard_row.split("\t") if first_clipboard_row else []
            self.logger.info(
                "  [FORM-GRID] clipboard first row cols="
                f"{len(first_clipboard_cols)} preview={first_clipboard_cols[:5]}"
            )
            def _paste_grid_until_reflected():
                nonlocal main_rect_cache
                attempts = max(1, int(os.getenv("ERP_GRID_PASTE_RETRIES", "3") or "3"))
                verify_first_cell = _env_flag("ERP_VERIFY_GRID_PASTE", "0")
                first_cell_wait = max(
                    0.3,
                    float(os.getenv("ERP_GRID_PASTE_FIRST_CELL_WAIT_SECONDS", "20") or "20"),
                )
                sent_wait = max(
                    0.3,
                    float(os.getenv("ERP_GRID_PASTE_SENT_WAIT_SECONDS", "1.0") or "1.0"),
                )
                for attempt in range(1, attempts + 1):
                    self._force_erp_window_maximized(
                        main_win,
                        f"grid paste attempt {attempt} before ERP main window",
                    )
                    main_rect_cache = None
                    used_excel_clipboard = False
                    if excel_copy_used:
                        used_excel_clipboard = _refresh_excel_grid_clipboard()
                    if not used_excel_clipboard:
                        pyperclip.copy(original_clipboard)
                        time.sleep(max(0.2, ERP_FORM_WAIT))
                    _release_modifiers(f"grid paste attempt {attempt} before paste", wait=False)
                    _click_grid_first_account_cell(first_account_cell_xy)
                    pyautogui.hotkey('ctrl', 'v')
                    _release_modifiers(f"grid paste attempt {attempt} after paste", wait=False)
                    source = "excel-range" if used_excel_clipboard else "text"
                    self.logger.info(
                        f"  [FORM-XY] grid paste sent: attempt={attempt}/{attempts}, source={source}"
                    )
                    time.sleep(first_cell_wait if verify_first_cell else sent_wait)
                    if not verify_first_cell:
                        grid_paste_state["verified"] = False
                        self.logger.info(
                            "  [FORM-VERIFY] grid first-cell copy check skipped after paste; "
                            "management-item display will be used as the completion signal"
                        )
                        return
                    if _grid_first_cell_matches_expected(first_account_cell_xy, f"grid paste attempt {attempt}"):
                        self.logger.info(
                            f"  [FORM-VERIFY] grid paste first-cell confirmed: attempt={attempt}/{attempts}"
                        )
                        return
                    if attempt < attempts:
                        self.logger.warning(
                            f"  [FORM-VERIFY] grid paste will retry because ERP grid is still blank: "
                            f"attempt={attempt}/{attempts}"
                        )
                _fail_form(
                    "ERP grid paste was sent but the first account cell stayed blank. "
                    "The voucher grid paste did not reach ERP, so saving was stopped."
                )

            _paste_grid_until_reflected()
            self.logger.info("  [FORM-XY] grid paste reflected; waiting for management items")
            try:
                if excel_copy_used:
                    management_grid_ready_state["snapshot"] = _wait_for_management_grid_ready(
                        "Excel range paste"
                    )
                else:
                    time.sleep(mgmt_after_grid_paste_wait)
                    _verify_grid_paste_or_fail(first_account_cell_xy)
                    management_grid_ready_state["snapshot"] = _wait_for_management_grid_ready(
                        "text clipboard paste"
                    )
            finally:
                if excel_copy_used:
                    _close_excel_copy_workbook()

            # 7. 계정과목별 관리항목값을 입력합니다.
            _fill_management_items_by_coord()

            # 8. 자동입력이 끝나면 저장 후 전표 출력 인쇄창까지 호출
            _save_and_open_print_dialog()

            self.logger.info("🏁 좌표 전용 폼 자동 세팅 완료")

        if resume_management_save_print:
            self.logger.info(
                "  [MGMT-RECOVERY] 신규/전표 재붙여넣기를 건너뛰고 현재 열린 전표의 "
                "전체 관리항목 입력을 1행부터 다시 실행합니다."
            )
            stale_message = _find_erp_message_snapshot()
            if stale_message:
                stale_compact = _erp_message_compact(stale_message)
                save_required_phrase = re.sub(r"\s+", "", "저장 후 출력해 주십시오.").lower()
                if save_required_phrase not in stale_compact:
                    raise RuntimeError(
                        "관리항목 복구 시작 전 알 수 없는 ERP Message가 표시되어 중단합니다: "
                        f"{stale_message.get('text', '')[:500]}"
                    )
                _dismiss_verified_erp_message(
                    stale_message,
                    ("저장 후 출력해 주십시오.",),
                )
                self.logger.info(
                    "  [MGMT-RECOVERY] 이전 출력 시도의 '저장 후 출력' Message만 확인 후 닫았습니다."
                )
            _prepare_management_recovery_from_first_row()
            _fill_management_items_by_coord()
            _save_and_open_print_dialog()
            return

        if resume_print_only_requested:
            self.logger.info(
                "  [PRINT-RESUME] 폼 입력과 저장을 건너뛰고 현재 열린 전표의 출력만 실행합니다."
            )
            _save_and_open_print_dialog()
            return

        # UIA 탐색으로 시간 끌지 않고, 신규 이후는 화면 좌표 기준으로 즉시 진행합니다.
        try:
            _setup_by_coordinates_only()
            return
        except Exception as e:
            self.logger.error(f"  [FORM-XY] 좌표 전용 폼 세팅 실패: {e}")
            raise

        def _all_edits():
            result = []
            for c in main_win.descendants(control_type='Edit'):
                try:
                    if c.is_visible() and c.is_enabled():
                        result.append(c)
                except: pass
            return result

        # 회계단위 (ComboBox)
        if site_name:
            cb_site = None
            for c in main_win.descendants(control_type='ComboBox'):
                try:
                    if (c.element_info.automation_id or '') == 'cboAccUnit': cb_site = c; break
                except: pass
                
            if cb_site is None:
                for c in main_win.descendants(control_type='ComboBox'):
                    try:
                        nm = c.window_text() or ''
                        if '단위' in nm or '공장' in nm or '㈜' in nm: cb_site = c; break
                    except: pass

            if cb_site:
                try:
                    try: cb_site.select(site_name)
                    except: pass
                    self.logger.info(f"  ✅ [회계단위] '{site_name}' 선택 시도")
                    time.sleep(0.3)
                    
                    cr = cb_site.rectangle()
                    pyautogui.click(cr.right - 10, cr.top + (cr.height()//2))
                    time.sleep(0.4)
                    
                    selected = False
                    scopes = [main_win]
                    try:
                        for w in Desktop(backend="uia").windows():
                            if getattr(w.element_info, 'process_id', None) == getattr(main_win.element_info, 'process_id', None):
                                scopes.append(w)
                    except: pass
                    
                    for scope in scopes:
                        try:
                            for li in scope.descendants(control_type='ListItem'):
                                if (li.window_text() or '').strip() == site_name:
                                    lr = li.rectangle()
                                    if lr.width() > 0 and lr.height() > 0:
                                        pyautogui.click(lr.left + (lr.width()//2), lr.top + (lr.height()//2))
                                        selected = True; break
                        except: pass
                        if selected: break
                        
                    if selected: self.logger.info(f"  ✅ [회계단위] '{site_name}' 수동 클릭 완료")
                    else:
                        self.logger.warning(f"  [회계단위] '{site_name}' 항목을 찾지 못해 닫습니다.")
                        pyautogui.press('escape')
                    time.sleep(0.4)
                except Exception as ex:
                    self.logger.warning(f"  [회계단위] 클릭 실패: {ex}")
            else:
                self.logger.warning("  [회계단위] ComboBox를 찾을 수 없음")

            # 화면 좌표 fallback: 이미지 기준 회계단위 콤보박스 위치
            try:
                self.logger.info(f"  [FORM-XY] 회계단위 좌표 fallback 시작: {site_name}")
                _click_form_xy(237, 124, "회계단위 드롭다운 화살표")
                time.sleep(0.4)
                picked = False
                for w in Desktop(backend="uia").windows():
                    try:
                        for li in w.descendants(control_type='ListItem'):
                            if (li.window_text() or '').strip() == site_name:
                                lr = li.rectangle()
                                pyautogui.click(lr.left + lr.width() // 2, lr.top + lr.height() // 2)
                                self.logger.info(f"  [FORM-XY] 회계단위 목록 항목 클릭 완료: {site_name}")
                                picked = True
                                break
                    except: pass
                    if picked: break
                if not picked:
                    self.logger.warning(f"  [FORM-XY] 회계단위 목록에서 '{site_name}' 미발견. 입력 fallback 실행")
                    _paste_form_xy(237, 124, site_name, "회계단위", clear=True, enter=True)
            except Exception as e:
                self.logger.warning(f"  [FORM-XY] 회계단위 fallback 실패: {e}")

        # 전표관리단위 (TextBox)
        if site_name:
            tb = None
            for c in main_win.descendants(control_type='Pane'):
                if (c.element_info.automation_id or '') == 'txtSlipUnit':
                    try:
                        edits = c.descendants(control_type='Edit')
                        if edits: tb = edits[0]
                    except: pass
                    
            if tb is None:
                edits = _all_edits()
                if len(edits) >= 2: tb = edits[1]

            if tb:
                try:
                    r = tb.rectangle()
                    pyautogui.click(r.left + (r.width()//2), r.top + (r.height()//2))
                    time.sleep(0.3)
                    pyautogui.press('right', presses=10)
                    pyautogui.press('backspace', presses=20)
                    time.sleep(0.1)
                    _safe_paste(site_name)
                    time.sleep(0.2)
                    pyautogui.press('tab')
                    self.logger.info(f"  ✅ [전표관리단위] '{site_name}' 입력 완료")
                    time.sleep(0.4)
                except Exception as e:
                    self.logger.warning(f"  [전표관리단위] 입력 실패: {e}")
            else:
                self.logger.warning("  [전표관리단위] Edit를 찾을 수 없음")

            # 화면 좌표 fallback: 이미지 기준 전표관리단위 입력칸
            try:
                _paste_form_xy(512, 124, site_name, "전표관리단위", clear=True, tab=True)
            except Exception as e:
                self.logger.warning(f"  [FORM-XY] 전표관리단위 fallback 실패: {e}")

        # 회계일
        date_str = invoice_date
        tb_date = None
        for c in main_win.descendants(control_type='Pane'):
            if (c.element_info.automation_id or '') == 'datAccDate':
                try:
                    edits = c.descendants(control_type='Edit')
                    if edits: tb_date = edits[0]
                except: pass
                
        if tb_date is None:
            edits = _all_edits()
            if len(edits) >= 3: tb_date = edits[2]
            elif len(edits) >= 1: tb_date = edits[0]

        if tb_date:
            try:
                r = tb_date.rectangle()
                pyautogui.click(r.left + (r.width()//2), r.top + (r.height()//2))
                time.sleep(0.3)
                pyautogui.press('right', presses=10)
                pyautogui.press('backspace', presses=20)
                time.sleep(0.1)
                _safe_paste(date_str)
                time.sleep(0.2)
                pyautogui.press('enter')
                self.logger.info(f"  ✅ [회계일] '{invoice_date}' 입력 완료")
                time.sleep(0.5)
            except Exception as e:
                self.logger.warning(f"  [회계일] 입력 실패: {e}")
        else:
            self.logger.warning("  [회계일] Edit를 찾을 수 없음")

        # 화면 좌표 fallback: 이미지 기준 회계일 입력칸
        try:
            _paste_form_xy(470, 186, date_str, "회계일", clear=True, enter=True)
        except Exception as e:
            self.logger.warning(f"  [FORM-XY] 회계일 fallback 실패: {e}")

        # 원본 클립보드 원복
        pyperclip.copy(original_clipboard)
        time.sleep(0.2)

        # 행추가
        try:
            btn_add = None
            add_candidates = []

            def _legacy_add_row_candidate(ctrl):
                try:
                    text = _norm_text(_control_text(ctrl) or ctrl.window_text())
                    aid = str(ctrl.element_info.automation_id or "")
                    if "부가세" in text:
                        return None
                    if text != "행추가" and aid != "btnAddRow":
                        return None
                    r = ctrl.rectangle()
                    mr = main_win.rectangle()
                    rel_x = (r.left + r.right) // 2 - mr.left
                    rel_y = (r.top + r.bottom) // 2 - mr.top
                    score = abs(rel_y - 385)
                    if text == "행추가":
                        score -= 1000
                    return (score, ctrl)
                except:
                    return None

            for b in main_win.descendants(control_type='Button'):
                item = _legacy_add_row_candidate(b)
                if item:
                    add_candidates.append(item)
            for c in main_win.descendants(control_type='Custom'):
                item = _legacy_add_row_candidate(c)
                if item:
                    add_candidates.append(item)
            if add_candidates:
                add_candidates.sort(key=lambda row: row[0])
                btn_add = add_candidates[0][1]

            add_clicks = max(0, row_count - 1)
            if btn_add and add_clicks > 0:
                r = btn_add.rectangle()
                cx, cy = r.left + (r.width() // 2), r.top + (r.height() // 2)
                for _ in range(add_clicks):
                    pyautogui.click(cx, cy)
                    time.sleep(0.25)
                self.logger.info(f"  ✅ [행추가] {add_clicks}회 추가")
            elif btn_add is None:
                self.logger.warning("  [행추가] 버튼 미발견")
                if add_clicks > 0:
                    self.logger.info("  [FORM-XY] 행추가 좌표 fallback 실행")
                    for _ in range(add_clicks):
                        _click_form_xy(1856, 386, "행추가")
                        time.sleep(0.25)
            time.sleep(0.5)
        except Exception as e:
            self.logger.warning(f"  [행추가] 실패: {e}")
            try:
                add_clicks = max(0, row_count - 1)
                if add_clicks > 0:
                    self.logger.info("  [FORM-XY] 행추가 예외 후 좌표 fallback 실행")
                    for _ in range(add_clicks):
                        _click_form_xy(1856, 386, "행추가")
                        time.sleep(0.25)
            except Exception as ex:
                self.logger.warning(f"  [FORM-XY] 행추가 fallback 실패: {ex}")

        # 그리드 계정과목 셀 클릭 -> Ctrl+V
        try:
            ss_row = None
            for c in main_win.descendants(control_type='Custom'):
                if (c.element_info.automation_id or '') == 'SS_Row': ss_row = c; break

            if ss_row:
                rect = ss_row.rectangle()
                pyautogui.click(rect.left + 150, rect.top + 45)
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'v')
                self.logger.info("  ✅ [Ctrl+V] 그리드 붙여넣기 완료")
                time.sleep(1.0)
            else:
                self.logger.warning("  [그리드] SS_Row 미발견")
                pyperclip.copy(original_clipboard)
                time.sleep(0.2)
                _click_form_xy(498, 287, "그리드 첫 계정과목 셀")
                pyautogui.hotkey('ctrl', 'v')
                self.logger.info("  [FORM-XY] 그리드 좌표 붙여넣기 완료")
        except Exception as e:
            self.logger.warning(f"  [그리드 Ctrl+V] 실패: {e}")
            try:
                pyperclip.copy(original_clipboard)
                time.sleep(0.2)
                _click_form_xy(498, 287, "그리드 첫 계정과목 셀")
                pyautogui.hotkey('ctrl', 'v')
                self.logger.info("  [FORM-XY] 그리드 예외 후 좌표 붙여넣기 완료")
            except Exception as ex:
                self.logger.warning(f"  [FORM-XY] 그리드 fallback 실패: {ex}")

        self.logger.info("🏁 폼 자동 세팅 완료!")


class AppManager:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.app_data = self.load_data()
        
        # 프로그램 실행 중에만 유지되는 메모리 공간
        self.erp_pids = {}
        
        self.current_user = None
        self.main_app = None
        self.config_mgr = ERPConfig()
        self.logger = setup_logger()
        self.show_login()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
        return {"hide_patch_notes": False, "hide_win_v_guide": False, "last_seen_version": ""}

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(self.app_data, f, ensure_ascii=False, indent=4)

    def show_login(self):
        self.lt = tk.Toplevel(self.root)
        self.lt.title("전표 자동화 시스템 로그인")
        self.lt.geometry("350x320")
        self.lt.resizable(False, False)
        self.lt.protocol("WM_DELETE_WINDOW", self.root.destroy)
        
        tk.Label(self.lt, text="사내 전표 시스템", font=("맑은 고딕", 14, "bold")).pack(pady=15)
        
        f_i = tk.Frame(self.lt)
        f_i.pack(pady=5)
        tk.Label(f_i, text="아이디:", width=8).pack(side="left")
        e_i = tk.Entry(f_i, width=20)
        e_i.insert(0, "rlckd9646")
        e_i.pack(side="left")
        
        f_p = tk.Frame(self.lt)
        f_p.pack(pady=5)
        tk.Label(f_p, text="비밀번호:", width=8).pack(side="left")
        e_p = tk.Entry(f_p, show="*", width=20)
        e_p.pack(side="left")
        
        def do_l(event=None):
            try:
                res = requests.post(LOGIN_URL, json={"id": e_i.get().strip(), "pw": e_p.get().strip()}, timeout=3)
                if res.status_code == 200:
                    d = res.json()
                    if d.get("status") == "success":
                        if d.get("is_initial"): 
                            self.force_pw(e_i.get().strip())
                        else: 
                            self.lt.destroy()
                            self.root.deiconify()
                            self.current_user = d["name"]
                            self.main_app = ERPAutoApp(self.root, self.current_user, self)
                    else: 
                        messagebox.showerror("오류", "계정 정보가 일치하지 않습니다.")
                else: 
                    messagebox.showerror("오류", "서버 통신 오류")
            except Exception as e: 
                messagebox.showerror("연결 실패", str(e))
                
        e_p.bind("<Return>", do_l)
        tk.Button(self.lt, text="로그인", bg="#2196F3", fg="white", width=25, height=2, command=do_l).pack(pady=10)

        def find():
            uid = simpledialog.askstring("비밀번호 찾기", "사원 아이디를 입력해 주십시오:")
            if not uid: return
            try:
                if requests.post(CHECK_USER_URL, json={"id": uid}, timeout=3).status_code == 200:
                    em = f"{uid}@dae-seung.co.kr"
                    tpw = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    msg = MIMEText(f"임시 비밀번호를 발송해 드립니다.\n\n임시 비밀번호: {tpw}\n\n로그인 후 즉시 변경 요망.")
                    msg['Subject'] = "[전산팀] 전표 자동화 시스템 임시 비밀번호 발급"
                    msg['From'] = "rlckd9646@dae-seung.co.kr"
                    msg['To'] = em
                    msg['Date'] = formatdate(localtime=True)
                    msg['Message-ID'] = make_msgid()
                    try:
                        s = smtplib.SMTP("35.216.76.148", 25)
                        s.ehlo()
                        if s.has_extn('STARTTLS'): 
                            s.starttls()
                            s.ehlo()
                        s.login("rlckd9646", "@gozld2201")
                        s.send_message(msg)
                        s.quit()
                        requests.post(UPDATE_PW_URL, json={"id": uid, "new_pw": tpw, "is_initial": True}, timeout=3)
                        messagebox.showinfo("안내", f"임시 비밀번호가 사내 메일({em})로 발송되었습니다.")
                    except Exception as e: 
                        messagebox.showerror("실패", f"SMTP 에러: {e}")
                else: 
                    messagebox.showerror("오류", "존재하지 않는 아이디입니다.")
            except Exception as e: 
                messagebox.showerror("통신 오류", f"서버 통신에 실패하였습니다.\n{e}")
                
        tk.Button(self.lt, text="비밀번호 찾기", bd=0, fg="blue", command=find).pack(pady=5)

    def force_pw(self, uid):
        top = tk.Toplevel(self.lt)
        top.title("비밀번호 변경")
        top.geometry("300x200")
        top.grab_set()
        
        tk.Label(top, text="보안을 위해 초기 비밀번호를 변경해 주십시오.", fg="red", font=("맑은 고딕", 9, "bold")).pack(pady=15)
        tk.Label(top, text="새 비밀번호:").pack()
        e1 = tk.Entry(top, show="*")
        e1.pack(pady=5)
        tk.Label(top, text="비밀번호 확인:").pack()
        e2 = tk.Entry(top, show="*")
        e2.pack(pady=5)
        
        def save():
            if e1.get() != e2.get(): 
                messagebox.showerror("오류", "비밀번호가 일치하지 않습니다.", parent=top)
                return
            if len(e1.get()) < 4: 
                messagebox.showerror("오류", "비밀번호 길이를 4자리 이상으로 설정하세요.", parent=top)
                return
            try:
                requests.post(UPDATE_PW_URL, json={"id": uid, "new_pw": e1.get(), "is_initial": False}, timeout=3)
                messagebox.showinfo("성공", "변경이 완료되었습니다. 새 비밀번호로 다시 로그인해 주십시오.", parent=top)
                top.destroy()
            except Exception as e: 
                messagebox.showerror("오류", str(e), parent=top)
                
        tk.Button(top, text="변경 적용", command=save, bg="#4CAF50", fg="white").pack(pady=10)

class ERPAutoApp:
    def __init__(self, root, user_name, manager):
        self.root = root
        self.root.title(f"전표 자동화 V{CURRENT_VERSION} - {user_name}")
        self.root.geometry("900x900")
        self.root.minsize(900, 860)
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.attributes("-zoomed", True)
        self.manager = manager
        self.user_name = user_name
        self.data = {}
        self.dept_entries = {}
        self.current_invoice_id = None
        self.tax_path = ""
        self.quote_path = ""
        self.approval_pdf_paths = []
        self.approval_order_number = ""
        self.approval_fetching = False
        self.print_choice_override = None
        self.batch_erp_pdf_path = ""
        self.last_erp_print_output = ""
        self.create_widgets()
        self.poll_dashboard() 

    def log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"> {msg}\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _on_oneclick_output_changed(self, event=None):
        try:
            self.manager.config_mgr.set_common_value("oneclick_output_label", self.oneclick_output_var.get().strip())
        except Exception:
            pass

    def _get_print_choice_by_label(self, label):
        text = str(label or "").strip()
        for option in PRINT_TARGET_OPTIONS:
            if option["label"] == text:
                return dict(option)
        return dict(PRINT_TARGET_OPTIONS[0])

    def _get_selected_oneclick_choice(self):
        return self._get_print_choice_by_label(self.oneclick_output_var.get())

    def _resolve_print_choice(self, choice=None):
        return dict(choice) if choice else self._get_selected_oneclick_choice()

    def _refresh_batch_button_state(self):
        state = "normal" if self.dept_entries and self.tax_path and self.quote_path else "disabled"
        try:
            self.btn_oneclick_set.config(state=state)
        except Exception:
            pass

    def _merge_pdf_documents(self, source_paths, output_path):
        merged = fitz.open()
        try:
            for src_path in source_paths:
                ext = Path(src_path).suffix.lower()
                if ext == ".pdf":
                    src_doc = fitz.open(src_path)
                    try:
                        merged.insert_pdf(src_doc)
                    finally:
                        src_doc.close()
                else:
                    img_doc = fitz.open(src_path)
                    try:
                        pdf_bytes = img_doc.convert_to_pdf()
                    finally:
                        img_doc.close()
                    pdf_doc = fitz.open("pdf", pdf_bytes)
                    try:
                        merged.insert_pdf(pdf_doc)
                    finally:
                        pdf_doc.close()
            merged.save(output_path)
        finally:
            merged.close()

    def _build_oneclick_pdf_filename(self):
        vendor = str(self.data.get("vendor_name", "") or "업체명").strip()
        invoice_date = str(self.data.get("invoice_date", "") or "").strip()
        total_sum = int(self.data.get("total_sum", 0) or 0)
        safe_vendor = re.sub(r'[\\/:*?"<>|]', "_", vendor) or "업체명"
        safe_date = re.sub(r'[\\/:*?"<>|]', "_", invoice_date) or datetime.now().strftime("%Y-%m-%d")
        return f"전표SET - {safe_vendor}({safe_date} - {total_sum:,}원).pdf"

    def _recover_qty_from_item_text(self, item):
        item = dict(item or {})
        raw_desc = str(item.get('raw_desc', '') or '')
        name = str(item.get('name', '') or '')
        text = f"{raw_desc}\n{name}"

        current_qty = max(1, int(item.get('qty', 1) or 1))
        repaired_qty = current_qty

        patterns = [
            r'(?<!\d)(\d{1,3})\s*(?:EA|개|PCS?|SET)\b',
            r'(?<!\d)(\d{1,3})\s*/\s*\d{1,3}(?:,\d{3})*\s*원',
            r'수량\s*[:：]?\s*(\d{1,3})',
        ]

        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                repaired_qty = max(1, int(m.group(1)))
                break

        if repaired_qty != current_qty:
            item['qty'] = repaired_qty
            self.log(f"[QTY-RECOVER] {item.get('name', '품목')}: {current_qty}EA -> {repaired_qty}EA")
        return item

    def _normalize_items_for_display(self, items):
        fixed = []
        for item in list(items or []):
            repaired = self._recover_qty_from_item_text(item)
            item_text = " ".join(
                str(repaired.get(key, "") or "")
                for key in ("name", "raw_desc", "original_text", "desc")
            )
            if "모니터암" in item_text or "모니터 암" in item_text:
                repaired["account"] = "소모품비"
                repaired["is_a"] = False
                if not str(repaired.get("name", "")).strip():
                    repaired["name"] = "모니터암"
            fixed.append(repaired)
        return fixed

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        self.tab_purchase = tk.Frame(self.notebook)
        self.tab_regular = tk.Frame(self.notebook)
        self.notebook.add(self.tab_purchase, text="컴퓨존 구매 회계처리")
        self.notebook.add(self.tab_regular, text="정기 회계처리")

        purchase_parent = self.tab_purchase

        dash_frame = tk.LabelFrame(purchase_parent, text=" [전사 공용] 세금계산서 수신 내역 ", padx=10, pady=5)
        dash_frame.pack(fill="x", padx=20, pady=5)
        
        columns = ("id", "status", "date", "title", "user")
        self.tv = ttk.Treeview(dash_frame, columns=columns, show="headings", height=5, selectmode="extended")
        self.tv.heading("id", text="No.")
        self.tv.column("id", width=40, anchor="center")
        self.tv.heading("status", text="상태")
        self.tv.column("status", width=80, anchor="center")
        self.tv.heading("date", text="수신일시")
        self.tv.column("date", width=130, anchor="center")
        self.tv.heading("title", text="계산서 제목")
        self.tv.column("title", width=400, anchor="w")
        self.tv.heading("user", text="담당자")
        self.tv.column("user", width=100, anchor="center")
        self.tv.pack(fill="x", pady=5)
        
        btn_frame = tk.Frame(dash_frame)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="🔄 새로고침", command=self.refresh_dashboard).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑 선택 항목 삭제", bg="#b71c1c", fg="white", command=self.delete_purchase_invoice).pack(side="right", padx=5)
        tk.Button(btn_frame, text="☑ 선택 항목 수동 처리완료", bg="#607d8b", fg="white", command=self.complete_invoice_manually).pack(side="right", padx=5)
        tk.Button(btn_frame, text="✅ 선택한 계산서 분석/처리하기", bg="#ff9800", fg="white", font=("맑은 고딕", 10, "bold"), command=self.lock_and_process).pack(side="right", padx=5)

        self.f1 = tk.LabelFrame(purchase_parent, text=" 1. 증빙 서류 (세금계산서/견적서 첨부) ", padx=10, pady=10)
        self.f1.pack(fill="x", padx=20, pady=5)
        self.f1.columnconfigure(0, weight=1)

        tax_panel = tk.Frame(self.f1, bg="#f7f9fc", bd=1, relief="solid", padx=10, pady=8)
        tax_panel.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tax_panel.columnconfigure(1, weight=1)
        self.btn_tax_attach = tk.Button(
            tax_panel,
            text="세금계산서 수동 첨부",
            command=lambda: self.select_f('tax'),
            width=20,
            bg="#5c6bc0",
            fg="white",
            activebackground="#4b5ab4",
            activeforeground="white",
            font=("맑은 고딕", 10, "bold"),
            relief="flat",
            cursor="hand2",
            pady=4,
        )
        self.btn_tax_attach.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="w")
        self.lbl_tax = tk.Label(
            tax_panel,
            text="[대기] 상단 목록 선택 또는 수동 첨부",
            fg="#607d8b",
            bg="#f7f9fc",
            font=("맑은 고딕", 10, "bold"),
        )
        self.lbl_tax.grid(row=0, column=1, sticky="w")
        tax_action_frame = tk.Frame(tax_panel, bg="#f7f9fc")
        tax_action_frame.grid(row=1, column=1, sticky="w", pady=(7, 0))
        self.btn_tax_download = tk.Button(
            tax_action_frame,
            text="⬇ 세금계산서 다운로드",
            command=self.download_tax_invoice,
            width=21,
            state="disabled",
            bg="#90a4ae",
            fg="white",
            activebackground="#1976d2",
            activeforeground="white",
            font=("맑은 고딕", 9, "bold"),
            relief="flat",
            cursor="hand2",
            pady=4,
            disabledforeground="#eceff1",
        )
        self.btn_tax_download.pack(side="left")
        self.btn_tax_preview = tk.Button(
            tax_action_frame,
            text="🔍 세금계산서 미리보기",
            command=self.preview_tax_invoice,
            width=20,
            state="disabled",
            bg="#90a4ae",
            fg="white",
            activebackground="#455a64",
            activeforeground="white",
            font=("맑은 고딕", 9, "bold"),
            relief="flat",
            cursor="hand2",
            pady=4,
            disabledforeground="#eceff1",
        )
        self.btn_tax_preview.pack(side="left", padx=(8, 0))
        self.btn_tax_print = tk.Button(
            tax_action_frame,
            text="🖨 세금계산서 출력",
            command=self.print_tax_invoice,
            width=18,
            state="disabled",
            bg="#90a4ae",
            fg="white",
            activebackground="#ef6c00",
            activeforeground="white",
            font=("맑은 고딕", 9, "bold"),
            relief="flat",
            cursor="hand2",
            pady=4,
            disabledforeground="#eceff1",
        )
        self.btn_tax_print.pack(side="left", padx=(8, 0))

        quote_panel = tk.Frame(self.f1, bg="#fcfcfc", bd=1, relief="solid", padx=10, pady=8)
        quote_panel.grid(row=1, column=0, sticky="ew")
        quote_panel.columnconfigure(1, weight=1)
        self.btn_quote_attach = tk.Button(
            quote_panel,
            text="견적서/명세서 수동 첨부",
            command=lambda: self.select_f('quote'),
            width=20,
            bg="#6d6d6d",
            fg="white",
            activebackground="#545454",
            activeforeground="white",
            font=("맑은 고딕", 10, "bold"),
            relief="flat",
            cursor="hand2",
            pady=4,
        )
        self.btn_quote_attach.grid(row=0, column=0, padx=(0, 12), sticky="w")
        self.lbl_quote = tk.Label(
            quote_panel,
            text="선택되지 않음 (상세 분석을 위해 필수)",
            fg="#d32f2f",
            bg="#fcfcfc",
            font=("맑은 고딕", 10, "bold"),
        )
        self.lbl_quote.grid(row=0, column=1, sticky="w")
        approval_action_frame = tk.Frame(quote_panel, bg="#fcfcfc")
        approval_action_frame.grid(row=1, column=1, sticky="w", pady=(7, 0))
        self.lbl_approval = tk.Label(
            approval_action_frame,
            text="품의결재본: 분석 후 자동 확보",
            fg="#607d8b",
            bg="#fcfcfc",
            font=("맑은 고딕", 9, "bold"),
        )
        self.lbl_approval.pack(side="left", padx=(0, 10))
        self.btn_approval_download = tk.Button(
            approval_action_frame,
            text="⬇ 품의결재본 다운로드",
            command=self.download_approval_pdf,
            width=20,
            state="disabled",
            bg="#b0bec5",
            fg="white",
            activebackground="#8e24aa",
            activeforeground="white",
            font=("맑은 고딕", 9, "bold"),
            relief="flat",
            cursor="arrow",
            pady=4,
            disabledforeground="#eceff1",
        )
        self.btn_approval_download.pack(side="left")
        self.btn_approval_print = tk.Button(
            approval_action_frame,
            text="🖨 품의결재본 출력",
            command=self.print_approval_pdf,
            width=18,
            state="disabled",
            bg="#b0bec5",
            fg="white",
            activebackground="#6a1b9a",
            activeforeground="white",
            font=("맑은 고딕", 9, "bold"),
            relief="flat",
            cursor="arrow",
            pady=4,
            disabledforeground="#eceff1",
        )
        self.btn_approval_print.pack(side="left", padx=(8, 0))
        
        self.btn_analyze = tk.Button(purchase_parent, text="🧠 지능형 문서 분석 시작", command=self.start_analysis, bg="#9C27B0", fg="white", font=("맑은 고딕", 11, "bold"), height=2, state="disabled")
        self.btn_analyze.pack(fill="x", padx=20, pady=5)
        
        self.dept_frame = tk.LabelFrame(purchase_parent, text=" 2. 분석 결과 확인 및 부서 수정 ", padx=10, pady=6)
        self.dept_frame.pack(fill="x", expand=False, padx=20, pady=5)
        self.canvas = tk.Canvas(self.dept_frame)
        self.canvas.configure(height=140)
        self.sb = ttk.Scrollbar(self.dept_frame, orient="vertical", command=self.canvas.yview)
        self.sf = tk.Frame(self.canvas)
        self.sf.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.sf, anchor="nw")
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.sb.pack(side="right", fill="y")
        
        log_frame = tk.LabelFrame(purchase_parent, text=" [분석 및 처리 로그] ")
        log_frame.pack(fill="x", padx=20, pady=5)
        self.log_box = tk.Text(log_frame, height=6, font=("Consolas", 9), state="disabled", bg="#f0f0f0")
        self.log_box.pack(fill="x")
        
        self.bottom_frame = tk.Frame(purchase_parent)
        self.bottom_frame.pack(fill="x", padx=20, pady=10)
        self.btn_erp = tk.Button(self.bottom_frame, text="ERP 자동 로그인 및 데이터 복사", command=self.copy_erp, bg="#4CAF50", fg="white", font=("맑은 고딕", 10, "bold"), height=2, state="disabled")
        self.btn_erp.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.btn_cash = tk.Button(self.bottom_frame, text="결의서 데이터 복사", command=self.create_expense_report, bg="#007bff", fg="white", font=("맑은 고딕", 10, "bold"), height=2, state="disabled")
        self.btn_cash.pack(side="right", expand=True, fill="x", padx=(5, 0))

        self.oneclick_frame = tk.Frame(purchase_parent)
        self.oneclick_frame.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(self.oneclick_frame, text="SET 출력 대상", font=("맑은 고딕", 9, "bold")).pack(side="left", padx=(0, 8))
        default_print_label = self.manager.config_mgr.config.get("COMMON", "oneclick_output_label", fallback=PRINT_TARGET_OPTIONS[0]["label"])
        self.oneclick_output_var = tk.StringVar(value=default_print_label)
        self.cmb_oneclick_output = ttk.Combobox(
            self.oneclick_frame,
            width=22,
            state="readonly",
            textvariable=self.oneclick_output_var,
            values=[opt["label"] for opt in PRINT_TARGET_OPTIONS],
        )
        self.cmb_oneclick_output.pack(side="left")
        self.cmb_oneclick_output.bind("<<ComboboxSelected>>", self._on_oneclick_output_changed)
        self.btn_oneclick_set = tk.Button(
            self.oneclick_frame,
            text="One-Click 전표 SET 출력",
            command=self.run_oneclick_set,
            bg="#263238",
            fg="white",
            activebackground="#37474f",
            activeforeground="white",
            font=("맑은 고딕", 10, "bold"),
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=6,
            state="disabled",
        )
        self.btn_oneclick_set.pack(side="right")

        self.create_regular_tab(self.tab_regular)

    def create_regular_tab(self, parent):
        dash_frame = tk.LabelFrame(parent, text=" [전사 공용] 정기 세금계산서 수신 내역 ", padx=10, pady=5)
        dash_frame.pack(fill="x", padx=20, pady=5)

        columns = ("id", "status", "date", "site", "vendor", "amount", "title", "user")
        self.regular_tv = ttk.Treeview(dash_frame, columns=columns, show="headings", height=7, selectmode="extended")
        headers = {
            "id": ("No.", 45, "center"),
            "status": ("상태", 75, "center"),
            "date": ("수신일시", 115, "center"),
            "site": ("사업장", 95, "center"),
            "vendor": ("업체명", 125, "w"),
            "amount": ("합계금액", 95, "e"),
            "title": ("계산서 제목", 260, "w"),
            "user": ("담당자", 80, "center"),
        }
        for key, (text, width, anchor) in headers.items():
            self.regular_tv.heading(key, text=text)
            self.regular_tv.column(key, width=width, anchor=anchor)
        self.regular_tv.pack(fill="x", pady=5)

        btn_frame = tk.Frame(dash_frame)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="새로고침", command=self.refresh_regular_dashboard).pack(side="left", padx=5)
        tk.Button(btn_frame, text="선택 항목 삭제", bg="#b71c1c", fg="white", command=self.delete_regular_invoice).pack(side="right", padx=5)
        tk.Button(btn_frame, text="선택 항목 수동 처리완료", bg="#607d8b", fg="white", command=self.complete_regular_invoice_manually).pack(side="right", padx=5)
        tk.Button(btn_frame, text="선택한 정기 계산서 처리", bg="#ff9800", fg="white", font=("맑은 고딕", 10, "bold"), command=self.lock_and_process_regular).pack(side="right", padx=5)

        info_frame = tk.LabelFrame(parent, text=" 1. 정기 세금계산서 정보 ", padx=10, pady=8)
        info_frame.pack(fill="x", padx=20, pady=5)
        info_frame.columnconfigure(1, weight=1)
        self.lbl_regular_tax = tk.Label(info_frame, text="[대기] 상단 목록에서 계산서를 선택하세요.", fg="#607d8b", font=("맑은 고딕", 10, "bold"))
        self.lbl_regular_tax.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.lbl_regular_summary = tk.Label(info_frame, text="사업장/업체/금액: 미선택", fg="#333333", font=("맑은 고딕", 10))
        self.lbl_regular_summary.grid(row=1, column=0, columnspan=2, sticky="w")
        self.lbl_regular_period = tk.Label(info_frame, text="처리 기준월: 미확인", fg="#455a64", font=("맑은 고딕", 10))
        self.lbl_regular_period.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        item_frame = tk.LabelFrame(parent, text=" 2. 전표 품목 및 계정 확인 ", padx=10, pady=6)
        item_frame.pack(fill="x", expand=False, padx=20, pady=5)
        self.regular_canvas = tk.Canvas(item_frame)
        self.regular_canvas.configure(height=150)
        self.regular_sb = ttk.Scrollbar(item_frame, orient="vertical", command=self.regular_canvas.yview)
        self.regular_sf = tk.Frame(self.regular_canvas)
        self.regular_sf.bind("<Configure>", lambda e: self.regular_canvas.configure(scrollregion=self.regular_canvas.bbox("all")))
        self.regular_canvas.create_window((0, 0), window=self.regular_sf, anchor="nw")
        self.regular_canvas.configure(yscrollcommand=self.regular_sb.set)
        self.regular_canvas.pack(side="left", fill="both", expand=True)
        self.regular_sb.pack(side="right", fill="y")

        log_frame = tk.LabelFrame(parent, text=" [정기 처리 로그] ")
        log_frame.pack(fill="x", padx=20, pady=5)
        self.regular_log_box = tk.Text(log_frame, height=6, font=("Consolas", 9), state="disabled", bg="#f0f0f0")
        self.regular_log_box.pack(fill="x")

        action_frame = tk.Frame(parent)
        action_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(action_frame, text="출력 대상", font=("맑은 고딕", 9, "bold")).pack(side="left", padx=(0, 8))
        default_print_label = self.manager.config_mgr.config.get("COMMON", "oneclick_output_label", fallback=PRINT_TARGET_OPTIONS[0]["label"])
        self.regular_output_var = tk.StringVar(value=default_print_label)
        self.cmb_regular_output = ttk.Combobox(
            action_frame,
            width=22,
            state="readonly",
            textvariable=self.regular_output_var,
            values=[opt["label"] for opt in PRINT_TARGET_OPTIONS],
        )
        self.cmb_regular_output.pack(side="left")
        self.btn_regular_erp = tk.Button(action_frame, text="ERP 전표 생성", command=self.copy_regular_erp, bg="#4CAF50", fg="white", font=("맑은 고딕", 10, "bold"), height=2, state="disabled")
        self.btn_regular_erp.pack(side="left", expand=True, fill="x", padx=(10, 5))
        self.btn_regular_tax_preview = tk.Button(action_frame, text="세금계산서 미리보기", command=self.preview_tax_invoice, bg="#546e7a", fg="white", font=("맑은 고딕", 10, "bold"), height=2, state="disabled")
        self.btn_regular_tax_preview.pack(side="left", expand=True, fill="x", padx=5)
        self.btn_regular_tax_print = tk.Button(action_frame, text="세금계산서 출력", command=lambda: self.print_tax_invoice(choice=self._get_regular_print_choice()), bg="#ef6c00", fg="white", font=("맑은 고딕", 10, "bold"), height=2, state="disabled")
        self.btn_regular_tax_print.pack(side="left", expand=True, fill="x", padx=5)
        self.btn_regular_set = tk.Button(action_frame, text="전표 + 세금계산서 출력", command=self.run_regular_print_set, bg="#263238", fg="white", font=("맑은 고딕", 10, "bold"), height=2, state="disabled")
        self.btn_regular_set.pack(side="right", expand=True, fill="x", padx=(5, 0))

        self.regular_entries = {}
        self.regular_data = {}

    def regular_log(self, msg):
        if not hasattr(self, "regular_log_box"):
            return
        self.regular_log_box.config(state="normal")
        self.regular_log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.regular_log_box.see("end")
        self.regular_log_box.config(state="disabled")

    @staticmethod
    def _to_int(value):
        try:
            if isinstance(value, (int, float)):
                return int(value)
            text = re.sub(r"[^0-9-]", "", str(value or ""))
            return int(text) if text not in ("", "-") else 0
        except Exception:
            return 0

    @staticmethod
    def _is_sane_amount(value):
        return 0 <= int(value or 0) <= 10_000_000_000

    @staticmethod
    def _normalize_biz_no(value):
        digits = re.sub(r"[^0-9]", "", str(value or ""))
        if len(digits) != 10:
            return ""
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"

    def _site_from_biz_no(self, value):
        biz_no = self._normalize_biz_no(value)
        return FACTORY_MAP.get(biz_no, "") if biz_no else ""

    def _recover_site_name(self, current_site, *sources):
        invalid_sites = {"", "사업장미상", "사업장미검출", "미검출", "사업장 미검출"}
        current = str(current_site or "").strip()
        if current and current not in invalid_sites:
            if current in CORP_MAP:
                return current
            compact = re.sub(r"\s+", "", current)
            for site in CORP_MAP:
                if compact == re.sub(r"\s+", "", site):
                    return site

        joined = "\n".join(str(src or "") for src in sources)
        compact_joined = re.sub(r"\s+", "", joined)
        for site in CORP_MAP:
            if site in joined or re.sub(r"\s+", "", site) in compact_joined:
                return site

        digits = re.sub(r"[^0-9]", "", joined)
        for biz_no, site in FACTORY_MAP.items():
            clean_biz = biz_no.replace("-", "")
            if clean_biz and clean_biz in digits:
                return site

        return current or "사업장미상"

    @staticmethod
    def _normalize_issue_date(value):
        text = str(value or "").strip()
        if not text:
            return ""
        m = re.search(r"(20\d{2})\D{0,4}(\d{1,2})\D{0,4}(\d{1,2})", text)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        digits = re.sub(r"[^0-9]", "", text)
        if len(digits) >= 8 and digits[:2] == "20":
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return ""

    def _extract_issue_date_from_invoice_data(self, raw, data):
        date_keys = (
            "invoice_date",
            "issue_date",
            "작성일자",
            "write_date",
            "written_date",
            "issueDate",
            "issueDateTime",
            "IssueDateTime",
        )
        for container in (raw, data):
            if not isinstance(container, dict):
                continue
            for key in date_keys:
                issue_date = self._normalize_issue_date(container.get(key))
                if issue_date:
                    return issue_date

        nested_paths = (
            ("raw", "content", "작성일자"),
            ("raw", "content", "issue_date"),
            ("content", "작성일자"),
            ("tax_invoice", "작성일자"),
            ("tax_invoice", "issue_date"),
        )
        for container in (raw, data):
            if not isinstance(container, dict):
                continue
            for path in nested_paths:
                cur = container
                for key in path:
                    cur = cur.get(key) if isinstance(cur, dict) else None
                issue_date = self._normalize_issue_date(cur)
                if issue_date:
                    return issue_date
        return ""

    def _extract_issue_date_from_pdf(self, pdf_path):
        path = str(pdf_path or "")
        if not path or not os.path.exists(path):
            return ""

        chunks = []
        try:
            with fitz.open(path) as doc:
                for page in doc:
                    chunks.append(page.get_text("text") or "")
        except Exception:
            pass

        if not any(chunks):
            try:
                with pdfplumber.open(path) as pdf:
                    for page in pdf.pages:
                        chunks.append(page.extract_text() or "")
            except Exception:
                pass

        text = "\n".join(chunks)
        compact = re.sub(r"\s+", " ", text)
        label_patterns = [
            r"작\s*성\s*일\s*자\D{0,30}(20\d{2})\D{0,4}(\d{1,2})\D{0,4}(\d{1,2})",
            r"발\s*행\s*일\s*자\D{0,30}(20\d{2})\D{0,4}(\d{1,2})\D{0,4}(\d{1,2})",
        ]
        for pattern in label_patterns:
            m = re.search(pattern, compact)
            if m:
                return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        # Some rendered invoices expose the approval number but not the label.
        # Tax invoice approval numbers start with the issue date: YYYYMMDD-...
        m = re.search(r"(20\d{6})[-\s]?\d{6,}", compact)
        if m:
            return self._normalize_issue_date(m.group(1))

        return ""

    def _extract_buyer_biz_no_from_invoice_data(self, raw, data):
        direct_keys = (
            "buyer_biz_no",
            "buyer_business_no",
            "invoicee_biz_no",
            "invoicee_business_no",
            "customer_biz_no",
            "customer_business_no",
            "recipient_biz_no",
        )
        for container in (raw, data):
            for key in direct_keys:
                biz_no = self._normalize_biz_no(container.get(key) if isinstance(container, dict) else "")
                if self._site_from_biz_no(biz_no):
                    return biz_no

        nested_names = ("buyer", "invoicee", "customer", "recipient", "공급받는자")
        nested_keys = ("biz_no", "business_no", "등록번호", "사업자번호", "ID", "id")
        for container in (raw, data):
            if not isinstance(container, dict):
                continue
            for name in nested_names:
                nested = container.get(name)
                if not isinstance(nested, dict):
                    continue
                for key in nested_keys:
                    biz_no = self._normalize_biz_no(nested.get(key))
                    if self._site_from_biz_no(biz_no):
                        return biz_no
        return ""

    def _extract_buyer_biz_no_from_pdf(self, pdf_path):
        path = str(pdf_path or "")
        if not path or not os.path.exists(path):
            return ""

        chunks = []
        try:
            with fitz.open(path) as doc:
                for page in doc:
                    chunks.append(page.get_text("text") or "")
        except Exception:
            pass

        if not any(chunks):
            try:
                with pdfplumber.open(path) as pdf:
                    for page in pdf.pages:
                        chunks.append(page.extract_text() or "")
            except Exception:
                pass

        text = "\n".join(chunks)
        for match in re.findall(r"\d{3}[-\s]?\d{2}[-\s]?\d{5}", text):
            biz_no = self._normalize_biz_no(match)
            if self._site_from_biz_no(biz_no):
                return biz_no
        return ""

    def _get_regular_print_choice(self):
        label = self.regular_output_var.get() if hasattr(self, "regular_output_var") else ""
        return self._get_print_choice_by_label(label) or PRINT_TARGET_OPTIONS[0]

    def _extract_regular_payload(self, invoice_data):
        raw = dict(invoice_data or {})
        data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
        pdf_path = raw.get("pdf_path") or data.get("pdf_path") or ""
        vendor = data.get("vendor_name") or data.get("supplier_name") or raw.get("vendor_name") or raw.get("supplier_name") or "매입처"
        buyer_biz_no = self._extract_buyer_biz_no_from_invoice_data(raw, data)
        if not buyer_biz_no:
            buyer_biz_no = self._extract_buyer_biz_no_from_pdf(pdf_path)
        biz_site = self._site_from_biz_no(buyer_biz_no)
        pdf_site = ""
        site_match = re.search(r"\((D[1-3]공장|P[1-4]공장|일강[12]공장|제이엠|더원)\)", os.path.basename(str(pdf_path or "")))
        if site_match:
            pdf_site = site_match.group(1)
        site_candidates = [
            biz_site,
            raw.get("_dashboard_site"),
            raw.get("site_name"),
            raw.get("buyer_site"),
            raw.get("matched_biz_name"),
            pdf_site,
            data.get("buyer_site"),
            data.get("matched_biz_name"),
            data.get("site_name"),
        ]
        site = ""
        for candidate in site_candidates:
            text = str(candidate or "").strip()
            if re.search(r"(D[1-3]|P[1-4]|공장|일강|제이엠|더원)", text, re.IGNORECASE):
                site = text
                break
        if not site:
            site = next((str(c or "").strip() for c in site_candidates if str(c or "").strip()), "사업장미상")
        issue_date = self._extract_issue_date_from_invoice_data(raw, data)
        pdf_issue_date = self._extract_issue_date_from_pdf(pdf_path)
        if pdf_issue_date:
            issue_date = pdf_issue_date
        total_tax = self._to_int(data.get("total_tax") or data.get("tax") or raw.get("total_tax"))
        total_sum = self._to_int(data.get("total_sum") or data.get("total_amount") or raw.get("total_sum"))
        target_supply = self._to_int(data.get("target_supply") or data.get("total_supply") or raw.get("target_supply"))
        if not target_supply and total_sum:
            target_supply = max(0, total_sum - total_tax)

        items = data.get("items") or raw.get("items") or []
        if not isinstance(items, list):
            items = []
        if not items:
            items = [{"name": data.get("item_name") or data.get("item") or raw.get("subject") or "정기 서비스", "qty": 1, "inc_vat": total_sum}]

        normalized_items = []
        for item in items:
            row = dict(item or {})
            row["name"] = str(row.get("name") or row.get("item_name") or "정기 서비스").strip()
            row["qty"] = max(1, self._to_int(row.get("qty") or row.get("quantity") or 1))
            row["inc_vat"] = self._to_int(row.get("inc_vat") or row.get("amount") or row.get("total") or total_sum)
            # 정기 계산서는 품목/업체 기준 회계 규칙을 우선한다.
            # 크롤러가 임시 기본값으로 넘긴 "소모품비"가 그대로 전표에 들어가는 것을 막는다.
            row["account"] = self._guess_regular_account(row["name"], vendor)
            normalized_items.append(row)

        items_total = sum(self._to_int(item.get("inc_vat")) for item in normalized_items)
        if not self._is_sane_amount(total_sum):
            total_sum = items_total if self._is_sane_amount(items_total) else 0
        if not self._is_sane_amount(target_supply):
            target_supply = max(0, total_sum - total_tax)

        vendor_display = re.sub(r"\(주\)|㈜|\(유\)|유한회사|주식회사", "", str(vendor)).strip() or "매입처"
        if re.search(r"\bkt\b|케이티", vendor_display, re.IGNORECASE):
            vendor_display = "KT"

        return {
            "pdf_path": pdf_path,
            "site_name": str(site).strip() or "사업장미상",
            "vendor_name": vendor_display,
            "buyer_biz_no": buyer_biz_no,
            "invoice_date": issue_date,
            "target_supply": target_supply,
            "total_tax": total_tax,
            "total_sum": total_sum,
            "items": normalized_items,
        }

    def _guess_regular_account(self, item_name, vendor_name=""):
        text = f"{item_name} {vendor_name}".lower()
        compact = re.sub(r"\s+", "", f"{item_name}{vendor_name}")
        if "동양정보통신" in compact or "대신아이씨티" in compact:
            return "지급수수료"
        if any(key in text for key in ["kt", "케이티", "통신", "vpn", "sdwan", "오토에버", "autoever", "704100", "w001"]):
            return "통신비"
        if any(key.lower() in text for key in ["nac", "dlp", "watching-on", "watchingon", "acronis", "그룹웨어", "다우오피스", "k-system", "ksystem", "helpu", "원격지원", "자산관리", "acrobat", "adobe", "cloudoc", "문서중앙화"]):
            return "지급수수료"
        return "지급수수료"

    def _regular_period_label(self, data):
        pdf_name = os.path.basename(data.get("pdf_path", ""))
        m = re.search(r"_(\d{4}년\s*\d{1,2}월(?:\s*\d차)?|\d{4}년\s*\d{1,2}~\d{1,2}월\s*\d차)(?:_\d+)?\.pdf$", pdf_name)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
        issue_date = data.get("invoice_date", "")
        digits = re.sub(r"[^0-9]", "", str(issue_date))
        if len(digits) >= 6:
            return f"{digits[:4]}년 {digits[4:6]}월"
        return "미확인"

    def _regular_month_text(self, period_label):
        m = re.search(r"(\d{1,2})월", str(period_label or ""))
        if m:
            return f"{int(m.group(1))}월"
        return "해당월"

    def _regular_year_month_text(self, period_label):
        m = re.search(r"(\d{4})년\s*(\d{1,2})월", str(period_label or ""))
        if m:
            return f"{m.group(1)}년 {int(m.group(2))}월"
        return str(period_label or "").strip() or "해당월"

    def _regular_round_text(self, period_label):
        m = re.search(r"(\d차)", str(period_label or ""))
        return m.group(1) if m else ""

    def _regular_vendor_display(self, vendor):
        raw = str(vendor or "").strip()
        compact = re.sub(r"\s+", "", re.sub(r"\([^)]*\)", "", raw).lower())
        rules = [
            ("다우", "다우기술"),
            ("대신아이씨티", "대신아이씨티"),
            ("에티버스", "에티버스"),
            ("이테크", "이테크시스템"),
            ("시큐어포인트", "시큐어포인트"),
            ("피플러스", "피플러스"),
            ("헬프유", "헬프유"),
            ("유비플러스", "유비플러스"),
            ("adobe", "Adobe"),
            ("어도비", "Adobe"),
            ("케이티", "KT"),
            ("kt", "KT"),
            ("오토에버", "현대오토에버시스템즈"),
            ("autoever", "현대오토에버시스템즈"),
            ("비엔아이", "비엔아이"),
        ]
        for key, label in rules:
            if key in compact:
                return label
        return re.sub(r"\([^)]*\)|\(주\)|㈜|\(유\)|유한회사|주식회사", "", raw).strip() or "업체명"

    def _regular_summary_text(self, item, account, total_supply=0, qty=1):
        name = str(item.get("name") or item.get("raw_desc") or "").strip()
        vendor = self._regular_vendor_display(self.regular_data.get("vendor_name", ""))
        site = str(self.regular_data.get("site_name", "") or "")
        period = self._regular_period_label(self.regular_data)
        month = self._regular_month_text(period)
        year_month = self._regular_year_month_text(period)
        text = f"{name} {vendor}".lower()

        if ("동양정보통신" in text or "대신아이씨티" in text) and "보수료" in text and total_supply == 250000:
            site_short = site.split("-")[-1].strip() if "-" in site else site
            s_clean = site.replace(" ", "")
            if "제1공장" in s_clean: site_short = "D1공장"
            elif "제2공장" in s_clean: site_short = "D2공장"
            elif "제5공장" in s_clean: site_short = "D3공장"
            elif "P1" in s_clean: site_short = "P1공장"
            elif "P2" in s_clean: site_short = "P2공장"
            elif "P3" in s_clean: site_short = "P3공장"
            elif "P4" in s_clean: site_short = "P4공장"
            
            ym_formatted = year_month.replace(" 0", " ") # 2026년 04월 -> 2026년 4월
            return f"{site_short} {ym_formatted} 통합유지보수료 - {vendor}"

        if "다우오피스" in text or "그룹웨어" in text or "daou" in text:
            return f"{year_month} 다우오피스 월 사용료 - {vendor}"
        if "watching-on" in text or "watchingon" in text or "watching" in text:
            return f"{month}분 Watching-On 모니터링 서비스 사용료 - {vendor}"
        if "acronis" in text:
            return f"{month}분 Acronis Cloud 사용료 - {vendor}"
        if "k-system" in text or "ksystem" in text:
            return f"K-System 유지보수 {month}분 - {vendor}"
        if "nac" in text or "genian" in text:
            return f"NAC 유지보수 {month} - {vendor}"
        if "dlp" in text or "gradius" in text:
            round_text = self._regular_round_text(period)
            return f"GRADIUS DLP 연간 유지보수 {round_text} - {vendor}".strip()
        if "helpu" in text or "원격지원" in text:
            return f"HelpU 원격지원 프로그램 구독({total_supply:,} - 2Y) - {vendor}"
        if "자산관리" in text:
            return f"자산관리 프로그램 구독(전산)({total_supply:,} - {qty}User) - {vendor}"
        if "acrobat" in text:
            return f"Acrobat Pro 구독(영업,인사총무,기획,전산)({total_supply:,} - {qty}EA) - {vendor}"
        if "cloudoc" in text or "문서중앙화" in text:
            return f"문서중앙화(Cloudoc) 라이선스 {qty}user 구매 - {vendor}"
        if "vpn" in text or "sdwan" in text or "오토에버" in text:
            return f"{month}분 현대자동차VPN사용료(2007010097) - {vendor}"
        if account == "통신비" or "kt" in text or "케이티" in text:
            if "일강" in site:
                return f"{month}분 인터넷 전용선비, 보안시스템 시큐어넷(일강-W0011501)-(주)케이티"
            if "P1" in site:
                return f"{month}분 P3공장 인터넷 전용선비 (704100003954) - 케이티"
            if "P4" in site:
                return f"{month}분 인터넷 전용선비, biz managed 보안 ( 704100003983 ) - 케이티"
            return f"{month}분 인터넷 전용선비, 보안시스템 시큐어넷-(주)케이티"

        clean_name = re.sub(r"\s+", " ", name).strip() or "정기 서비스"
        return f"{year_month} {clean_name} - {vendor}"

    def _refresh_regular_action_buttons(self):
        has_data = bool(getattr(self, "regular_data", {}).get("items"))
        has_tax = bool(self.tax_path and os.path.exists(self.tax_path))
        state_data = "normal" if has_data else "disabled"
        state_tax = "normal" if has_tax else "disabled"
        if hasattr(self, "btn_regular_erp"):
            self.btn_regular_erp.config(state=state_data)
            self.btn_regular_set.config(state="normal" if has_data and has_tax else "disabled")
            if hasattr(self, "btn_regular_tax_preview"):
                self.btn_regular_tax_preview.config(state=state_tax)
            self.btn_regular_tax_print.config(state=state_tax)

    def refresh_regular_dashboard(self):
        if not hasattr(self, "regular_tv"):
            return
        try:
            res = requests.get(f"{SERVER_BASE}/api/invoices?mode=regular", timeout=3)
            if res.status_code == 200:
                self.regular_tv.delete(*self.regular_tv.get_children())
                for row_no, i in enumerate(res.json(), start=1):
                    stat = i["status"]
                    tag = "wait" if stat == "대기중" else ("proc" if stat == "처리중" else "done")
                    dt = i["received_at"][2:16] if i["received_at"] else ""
                    amount = self._to_int(i.get("total_sum"))
                    amount_text = f"{amount:,}" if amount else ""
                    subject = i.get("display_subject") or i.get("subject") or ""
                    self.regular_tv.insert(
                        "",
                        "end",
                        iid=str(i["id"]),
                        values=(row_no, stat, dt, i.get("site_name", ""), i.get("vendor_name", ""), amount_text, subject, i["processor"]),
                        tags=(tag,),
                    )
                self.regular_tv.tag_configure("wait", background="white")
                self.regular_tv.tag_configure("proc", background="#FFF59D")
                self.regular_tv.tag_configure("done", background="#C8E6C9", foreground="gray")
        except Exception as e:
            self.logger.error(f"정기 대시보드 통신 에러: {e}")

    def lock_and_process_regular(self):
        selected = self.regular_tv.selection()
        if not selected:
            messagebox.showwarning("안내", "리스트에서 처리할 정기 계산서를 선택해주세요.", parent=self.root)
            return
        inv_id = int(selected[0])
        selected_item = self.regular_tv.item(selected[0])
        selected_values = selected_item.get("values", []) if selected_item else []
        dashboard_site = str(selected_values[3]).strip() if len(selected_values) > 3 else ""
        try:
            res = requests.post(f"{SERVER_BASE}/api/invoice/lock", json={"id": inv_id, "user_name": self.user_name}, timeout=3)
            data = res.json()
            if res.status_code == 200 and data.get("status") == "success":
                self.current_invoice_id = inv_id
                self.refresh_dashboard()
                self.refresh_regular_dashboard()
                if isinstance(data.get("invoice_data"), dict) and dashboard_site:
                    data["invoice_data"]["_dashboard_site"] = dashboard_site
                self.load_regular_invoice(data["invoice_data"])
            elif res.status_code == 403:
                messagebox.showwarning("접근 제한", data.get("msg"), parent=self.root)
                self.refresh_regular_dashboard()
            else:
                messagebox.showerror("오류", "데이터를 가져오는데 실패했습니다.", parent=self.root)
        except Exception as e:
            messagebox.showerror("통신 오류", str(e), parent=self.root)

    def complete_regular_invoice_manually(self):
        selected = self.regular_tv.selection()
        if not selected:
            messagebox.showwarning("안내", "리스트에서 처리완료할 계산서를 선택해주세요.", parent=self.root)
            return

        targets = []
        skipped = 0
        for iid in selected:
            item = self.regular_tv.item(iid)
            values = item.get("values", []) if item else []
            stat = values[1] if len(values) > 1 else ""
            title = values[6] if len(values) > 6 else str(iid)
            if stat == "처리완료":
                skipped += 1
                continue
            targets.append((iid, title))

        if not targets:
            messagebox.showinfo("안내", "선택한 계산서는 모두 이미 처리완료 상태입니다.", parent=self.root)
            return

        preview = "\n".join(f"- {title}" for _, title in targets[:5])
        more = f"\n외 {len(targets) - 5}건" if len(targets) > 5 else ""
        if not messagebox.askyesno("확인", f"선택한 정기 계산서 {len(targets)}건을 수동으로 처리완료 하시겠습니까?\n\n{preview}{more}", parent=self.root):
            return

        try:
            success = []
            failures = []
            for inv_id, _title in targets:
                try:
                    res = requests.post(f"{SERVER_BASE}/api/invoice/complete", json={"id": inv_id, "user_name": self.user_name, "manual": True}, timeout=3)
                    data = res.json()
                    if res.status_code == 200 and data.get("status") == "success":
                        success.append(inv_id)
                        if str(self.current_invoice_id or "") == str(inv_id):
                            self.current_invoice_id = None
                    else:
                        failures.append(f"{inv_id}: {data.get('msg', '처리 실패')}")
                except Exception as e:
                    failures.append(f"{inv_id}: {e}")

            self.refresh_dashboard()
            self.refresh_regular_dashboard()
            if success:
                self.regular_log(f"수동 처리완료 반영: {len(success)}건 ({', '.join(map(str, success))})")
            if failures:
                messagebox.showerror("일부 실패", "일부 계산서 처리완료에 실패했습니다.\n\n" + "\n".join(failures[:10]), parent=self.root)
            else:
                suffix = f"\n이미 처리완료라 제외된 항목: {skipped}건" if skipped else ""
                messagebox.showinfo("완료", f"선택한 정기 계산서 {len(success)}건을 처리완료로 반영했습니다.{suffix}", parent=self.root)
        except Exception as e:
            messagebox.showerror("통신 오류", str(e), parent=self.root)

    def delete_regular_invoice(self):
        selected = self.regular_tv.selection()
        if not selected:
            messagebox.showwarning("안내", "삭제할 계산서를 선택해주세요.", parent=self.root)
            return

        targets = []
        for iid in selected:
            item = self.regular_tv.item(iid)
            values = item.get("values", []) if item else []
            title = values[6] if len(values) > 6 else str(iid)
            targets.append((iid, title))

        preview = "\n".join(f"- {title}" for _, title in targets[:5])
        more = f"\n외 {len(targets) - 5}건" if len(targets) > 5 else ""
        if not messagebox.askyesno("확인", f"선택한 정기 계산서 {len(targets)}건을 수신내역에서 삭제하시겠습니까?\n\n{preview}{more}", parent=self.root):
            return

        try:
            success = []
            failures = []
            for inv_id, _title in targets:
                try:
                    res = requests.post(f"{SERVER_BASE}/api/invoice/delete", json={"id": inv_id, "user_name": self.user_name}, timeout=3)
                    data = res.json()
                    if res.status_code == 200 and data.get("status") == "success":
                        success.append(inv_id)
                        if str(self.current_invoice_id or "") == str(inv_id):
                            self.current_invoice_id = None
                    else:
                        failures.append(f"{inv_id}: {data.get('msg', '삭제 실패')}")
                except Exception as e:
                    failures.append(f"{inv_id}: {e}")

            self.refresh_regular_dashboard()
            self.refresh_dashboard()
            if success:
                self.regular_log(f"수신내역 삭제 완료: {len(success)}건 ({', '.join(map(str, success))})")
            if failures:
                messagebox.showerror("일부 실패", "일부 계산서 삭제에 실패했습니다.\n\n" + "\n".join(failures[:10]), parent=self.root)
            else:
                messagebox.showinfo("완료", f"선택한 정기 계산서 {len(success)}건을 삭제했습니다.", parent=self.root)
        except Exception as e:
            messagebox.showerror("통신 오류", str(e), parent=self.root)

    def delete_purchase_invoice(self):
        selected = self.tv.selection()
        if not selected:
            messagebox.showwarning("안내", "삭제할 계산서를 선택해주세요.", parent=self.root)
            return

        targets = []
        for iid in selected:
            item = self.tv.item(iid)
            values = item.get("values", []) if item else []
            title = values[3] if len(values) > 3 else str(iid)
            targets.append((iid, title))

        preview = "\n".join(f"- {title}" for _, title in targets[:5])
        more = f"\n외 {len(targets) - 5}건" if len(targets) > 5 else ""
        if not messagebox.askyesno("확인", f"선택한 구매 계산서 {len(targets)}건을 수신내역에서 삭제하시겠습니까?\n\n{preview}{more}", parent=self.root):
            return

        try:
            success = []
            failures = []
            for inv_id, _title in targets:
                try:
                    res = requests.post(f"{SERVER_BASE}/api/invoice/delete", json={"id": inv_id, "user_name": self.user_name}, timeout=3)
                    data = res.json()
                    if res.status_code == 200 and data.get("status") == "success":
                        success.append(inv_id)
                        if str(self.current_invoice_id or "") == str(inv_id):
                            self.current_invoice_id = None
                    else:
                        failures.append(f"{inv_id}: {data.get('msg', '삭제 실패')}")
                except Exception as e:
                    failures.append(f"{inv_id}: {e}")

            self.refresh_dashboard()
            self.refresh_regular_dashboard()
            if success:
                self.log(f"수신내역 삭제 완료: {len(success)}건 ({', '.join(map(str, success))})")
            if failures:
                messagebox.showerror("일부 실패", "일부 계산서 삭제에 실패했습니다.\n\n" + "\n".join(failures[:10]), parent=self.root)
            else:
                messagebox.showinfo("완료", f"선택한 구매 계산서 {len(success)}건을 삭제했습니다.", parent=self.root)
        except Exception as e:
            messagebox.showerror("통신 오류", str(e), parent=self.root)


    def load_regular_invoice(self, invoice_data):
        data = self._extract_regular_payload(invoice_data)
        pdf_path = data.get("pdf_path", "")
        if not pdf_path:
            messagebox.showerror("오류", "세금계산서 PDF 경로가 없습니다.", parent=self.root)
            return
        filename = os.path.basename(pdf_path)
        try:
            dl_url = f"{SERVER_BASE}/downloads/{urllib.parse.quote(filename)}"
            local_path = os.path.join(tempfile.gettempdir(), filename)
            urllib.request.urlretrieve(dl_url, local_path)
            data["pdf_path"] = local_path
            pdf_issue_date = self._extract_issue_date_from_pdf(local_path)
            if pdf_issue_date:
                data["invoice_date"] = pdf_issue_date
            self.tax_path = local_path
            self.quote_path = ""
            self.approval_pdf_paths = []
            self.regular_data = data
            self.data = data
            self.lbl_regular_tax.config(text=f"[자동첨부 완료] {filename}", fg="blue")
            self.lbl_regular_summary.config(text=f"사업장: {data['site_name']} / 업체: {data['vendor_name']} / 합계: {data['total_sum']:,}원")
            self.lbl_regular_period.config(text=f"처리 기준월: {self._regular_period_label(data)}")
            self.regular_log_box.config(state="normal")
            self.regular_log_box.delete("1.0", "end")
            self.regular_log_box.config(state="disabled")
            self.regular_log(f"정기 세금계산서 확보: {filename}")
            self.create_regular_item_fields()
            self._refresh_tax_action_buttons()
            self._refresh_regular_action_buttons()
        except Exception as e:
            self.regular_log(f"계산서 불러오기 실패: {e}")
            messagebox.showerror("오류", f"계산서 불러오기 실패:\n{e}", parent=self.root)

    def create_regular_item_fields(self):
        self.regular_entries = {}
        for w in self.regular_sf.winfo_children():
            w.destroy()
        for i, h in enumerate(["계정과목", "품목명", "수량/공급가"]):
            tk.Label(self.regular_sf, text=h, font=("맑은 고딕", 9, "bold")).grid(row=0, column=i, pady=5)
        raw_list = self.regular_data.get("items", [])
        t_inc = sum(self._to_int(i.get("inc_vat")) for i in raw_list)
        if t_inc > 0:
            for item in raw_list:
                item["supply"] = int(self.regular_data.get("target_supply", 0) * (self._to_int(item.get("inc_vat")) / t_inc))
            if raw_list:
                max_item = max(raw_list, key=lambda x: self._to_int(x.get("inc_vat")))
                max_item["supply"] += self.regular_data.get("target_supply", 0) - sum(self._to_int(i.get("supply")) for i in raw_list)
        for idx, item in enumerate(raw_list):
            r = idx + 1
            cb_acc = ttk.Combobox(self.regular_sf, values=["지급수수료", "통신비", "소모품비", "컴퓨터소프트웨어", "집기비품"], width=18, state="readonly")
            cb_acc.set(item.get("account") or self._guess_regular_account(item.get("name", ""), self.regular_data.get("vendor_name", "")))
            cb_acc.grid(row=r, column=0, padx=5, pady=3)
            ent_name = tk.Entry(self.regular_sf, width=42)
            ent_name.insert(0, item.get("name", "정기 서비스"))
            ent_name.grid(row=r, column=1, padx=5, pady=3)
            qty = max(1, self._to_int(item.get("qty") or 1))
            supply = self._to_int(item.get("supply"))
            tk.Label(self.regular_sf, text=f"{qty}EA / {supply:,}원", fg="grey").grid(row=r, column=2, padx=5)
            self.regular_entries[idx] = (item, cb_acc, ent_name)
        self._refresh_regular_action_buttons()

    def copy_regular_erp(self):
        if not getattr(self, "regular_data", None) or not getattr(self, "regular_entries", None):
            messagebox.showwarning("안내", "먼저 정기 계산서를 선택해 주세요.", parent=self.root)
            return
        rows = []
        items = []
        for _, (item, cb_acc, ent_name) in self.regular_entries.items():
            row = item.copy()
            row["account"] = cb_acc.get().strip() or row.get("account") or "지급수수료"
            row["name"] = ent_name.get().strip() or row.get("name") or "정기 서비스"
            row["supply"] = self._to_int(row.get("supply"))
            row["qty"] = max(1, self._to_int(row.get("qty") or 1))
            items.append(row)

        grouped = {}
        for item in items:
            grouped.setdefault(item["account"], []).append(item)
        for account, group in grouped.items():
            supply = sum(self._to_int(i.get("supply")) for i in group)
            qty = sum(self._to_int(i.get("qty") or 1) for i in group)
            summary = self._regular_summary_text(group[0], account, supply, qty)
            rows.append(f"{account}\t\t{supply}\t0\t{summary}")

        total_tax = self._to_int(self.regular_data.get("total_tax"))
        total_sum = self._to_int(self.regular_data.get("total_sum"))
        total_supply = self._to_int(self.regular_data.get("target_supply"))
        slip_summary = self._regular_summary_text(items[0] if items else {"name": "정기 서비스"}, items[0].get("account", "지급수수료") if items else "지급수수료", total_supply, sum(i.get("qty", 1) for i in items) or 1)
        rows.append(f"부가세대급금\t\t{total_tax}\t0\tV.A.T - {slip_summary}")
        rows.append(f"미지급금(원화)\t\t0\t{total_sum}\t{slip_summary}")

        pyperclip.copy("\r\n".join(rows))
        self.data = self.regular_data
        self.data["erp_row_count"] = len(rows)
        self.data["erp_clipboard_rows"] = rows
        self.regular_log(f"ERP 분개 데이터 생성 완료: {len(rows)}줄")
        self.root.update()

        corp_name = CORP_MAP.get(self.data.get("site_name", ""), "㈜대승")
        install_key = self.manager.config_mgr.config.get("COMMON", "default_install", fallback="DAESEUNG")
        corp_code = self.manager.config_mgr.config.get("COMMON", "default_corp", fallback="DS")
        if "대승정밀" in corp_name:
            install_key = "DSJM"; corp_code = "DSJM"
        elif "일강" in corp_name:
            install_key = "ILGANG"; corp_code = "ILGANG"
        elif "제이엠" in corp_name:
            install_key = "JM"; corp_code = "JM"
        elif "더원" in corp_name:
            install_key = "TO"; corp_code = "TO"

        bot = ERPLoginBot(self.manager.config_mgr.get_install_info(install_key), self.manager.config_mgr.get_corp_info(corp_code), corp_code, self.manager, self.manager.logger)
        bot_result = bot.run()
        if bot_result is True:
            self.regular_log("ERP 자동입력/저장/전표출력 호출 흐름 완료")
            if self.current_invoice_id:
                try:
                    requests.post(f"{SERVER_BASE}/api/invoice/complete", json={"id": self.current_invoice_id, "user_name": self.user_name}, timeout=3)
                    self.refresh_dashboard()
                    self.refresh_regular_dashboard()
                except Exception:
                    pass
        else:
            err_msg = f"데이터는 복사되었으나 ERP 활성화에 실패했습니다.\n({bot_result})\n\n수동으로 ERP를 열고 빈 행을 [ {len(rows)}개 ] 추가하여\n[ Ctrl + V ] 로 붙여넣으세요."
            messagebox.showwarning("ERP 실행 실패", err_msg, parent=self.root)

    def run_regular_print_set(self):
        if not getattr(self, "regular_data", None):
            messagebox.showwarning("안내", "먼저 정기 계산서를 선택해 주세요.", parent=self.root)
            return
        if not self.tax_path or not os.path.exists(self.tax_path):
            messagebox.showwarning("안내", "세금계산서가 없습니다.", parent=self.root)
            return
        choice = self._get_regular_print_choice()
        self.print_choice_override = dict(choice)
        self.batch_erp_pdf_path = ""
        self.last_erp_print_output = ""
        try:
            if choice["kind"] == "pdf_merge":
                out_path = filedialog.asksaveasfilename(
                    parent=self.root,
                    title="정기 전표 세트 병합 PDF 저장",
                    defaultextension=".pdf",
                    filetypes=[("PDF 파일", "*.pdf")],
                    initialfile=self._build_oneclick_pdf_filename(),
                )
                if not out_path:
                    return
                batch_dir = os.path.join(tempfile.gettempdir(), f"regular_set_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                os.makedirs(batch_dir, exist_ok=True)
                self.batch_erp_pdf_path = os.path.join(batch_dir, "01_전표.pdf")
                self.print_choice_override["save_path"] = self.batch_erp_pdf_path
                self.copy_regular_erp()
                erp_pdf = self.last_erp_print_output if os.path.exists(self.last_erp_print_output or "") else self.batch_erp_pdf_path
                if not os.path.exists(erp_pdf):
                    raise RuntimeError("전표 PDF 저장본을 찾지 못했습니다.")
                self._merge_pdf_documents([erp_pdf, self.tax_path], out_path)
                messagebox.showinfo("완료", f"정기 전표 세트 병합 PDF를 저장했습니다.\n{out_path}", parent=self.root)
            else:
                self.copy_regular_erp()
                self.print_tax_invoice(choice=choice, show_message=False)
                messagebox.showinfo("완료", f"전표 + 세금계산서 출력 요청을 완료했습니다.\n대상: {choice['label']}", parent=self.root)
        finally:
            self.print_choice_override = None
            self.batch_erp_pdf_path = ""

    def refresh_dashboard(self):
        try:
            res = requests.get(f"{SERVER_BASE}/api/invoices?mode=purchase", timeout=3)
            if res.status_code == 200:
                self.tv.delete(*self.tv.get_children())
                for row_no, i in enumerate(res.json(), start=1):
                    stat = i["status"]
                    if stat == "대기중": tag = "wait"
                    elif stat == "처리중": tag = "proc"
                    else: tag = "done"
                    dt = i["received_at"][2:16] if i["received_at"] else ""
                    subject = i.get("display_subject") or i.get("subject") or ""
                    self.tv.insert("", "end", iid=str(i["id"]), values=(row_no, stat, dt, subject, i["processor"]), tags=(tag,))
                self.tv.tag_configure("wait", background="white")
                self.tv.tag_configure("proc", background="#FFF59D") 
                self.tv.tag_configure("done", background="#C8E6C9", foreground="gray") 
        except Exception as e: 
            self.logger.error(f"대시보드 통신 에러: {e}")

    def poll_dashboard(self):
        self.refresh_dashboard()
        self.refresh_regular_dashboard()
        self.root.after(10000, self.poll_dashboard) 

    def lock_and_process(self):
        selected = self.tv.selection()
        if not selected: 
            messagebox.showwarning("안내", "리스트에서 처리할 계산서를 선택해주세요.", parent=self.root)
            return
        
        item = self.tv.item(selected[0])
        inv_id = int(selected[0])
        
        try:
            res = requests.post(f"{SERVER_BASE}/api/invoice/lock", json={"id": inv_id, "user_name": self.user_name}, timeout=3)
            data = res.json()
            if res.status_code == 200 and data.get("status") == "success":
                self.current_invoice_id = inv_id
                self.refresh_dashboard() 
                self.load_server_invoice(data["invoice_data"]) 
            elif res.status_code == 403:
                messagebox.showwarning("접근 제한", data.get("msg"), parent=self.root)
                self.refresh_dashboard()
            else:
                messagebox.showerror("오류", "데이터를 가져오는데 실패했습니다.", parent=self.root)
        except Exception as e:
            messagebox.showerror("통신 오류", str(e), parent=self.root)

    def complete_invoice_manually(self):
        selected = self.tv.selection()
        if not selected:
            messagebox.showwarning("안내", "리스트에서 처리완료할 계산서를 선택해주세요.", parent=self.root)
            return

        targets = []
        skipped = 0
        for iid in selected:
            item = self.tv.item(iid)
            values = item.get("values", []) if item else []
            stat = values[1] if len(values) > 1 else ""
            title = values[3] if len(values) > 3 else str(iid)
            if stat == "처리완료":
                skipped += 1
                continue
            targets.append((iid, title))

        if not targets:
            messagebox.showinfo("안내", "선택한 계산서는 모두 이미 처리완료 상태입니다.", parent=self.root)
            return

        preview = "\n".join(f"- {title}" for _, title in targets[:5])
        more = f"\n외 {len(targets) - 5}건" if len(targets) > 5 else ""
        if not messagebox.askyesno("확인", f"선택한 구매 계산서 {len(targets)}건을 수동으로 처리완료 하시겠습니까?\n\n{preview}{more}", parent=self.root):
            return

        try:
            success = []
            failures = []
            for inv_id, _title in targets:
                try:
                    res = requests.post(
                        f"{SERVER_BASE}/api/invoice/complete",
                        json={"id": inv_id, "user_name": self.user_name, "manual": True},
                        timeout=3
                    )
                    data = res.json()
                    if res.status_code == 200 and data.get("status") == "success":
                        success.append(inv_id)
                        if str(self.current_invoice_id or "") == str(inv_id):
                            self.current_invoice_id = None
                    else:
                        failures.append(f"{inv_id}: {data.get('msg', '처리 실패')}")
                except Exception as e:
                    failures.append(f"{inv_id}: {e}")

            self.refresh_dashboard()
            self.refresh_regular_dashboard()
            if success:
                self.log(f"☑ 수동 처리완료 반영: {len(success)}건 ({', '.join(map(str, success))})")
            if failures:
                messagebox.showerror("일부 실패", "일부 계산서 처리완료에 실패했습니다.\n\n" + "\n".join(failures[:10]), parent=self.root)
            else:
                suffix = f"\n이미 처리완료라 제외된 항목: {skipped}건" if skipped else ""
                messagebox.showinfo("완료", f"선택한 구매 계산서 {len(success)}건을 처리완료로 반영했습니다.{suffix}", parent=self.root)
        except Exception as e:
            messagebox.showerror("통신 오류", str(e), parent=self.root)

    def load_server_invoice(self, invoice_data):
        pdf_path = invoice_data.get("pdf_path", "")
        if not pdf_path: return
        filename = os.path.basename(pdf_path)
        try:
            dl_url = f"{SERVER_BASE}/downloads/{urllib.parse.quote(filename)}"
            local_path = os.path.join(tempfile.gettempdir(), filename)
            urllib.request.urlretrieve(dl_url, local_path)
            
            self.tax_path = local_path
            self.loaded_invoice_data = dict(invoice_data or {})
            self.lbl_tax.config(text=f"📁 [자동첨부 완료] {filename}", fg="blue", font=("맑은 고딕", 9, "bold"))
            self.log_box.config(state="normal")
            self.log_box.delete("1.0", "end")
            self.log_box.config(state="disabled")
            self.approval_pdf_paths = []
            self.approval_order_number = ""
            self.approval_fetching = False
            self.lbl_approval.config(text="품의결재본: 분석 후 자동 확보", fg="#607d8b")
            self._refresh_approval_action_buttons()
            self.log(f"✅ 서버에서 세금계산서({filename})를 확보했습니다. (Lock 완료)")
            self.log("▶ 다음 단계: 견적서를 수동 첨부하고 '분석 시작'을 누르세요.")
            self.btn_analyze.config(state="normal")
            self._refresh_tax_action_buttons()
            self._refresh_batch_button_state()
        except Exception as e:
            self.log(f"❌ 계산서 불러오기 실패: {e}")

    def select_f(self, file_type):
        p = filedialog.askopenfilename(
            title="분석할 서류 선택",
            filetypes=[("문서 파일", "*.pdf;*.png;*.jpg;*.jpeg"), ("모든 파일", "*.*")]
        )
        if not p:
            return

        if file_type == 'tax':
            self.tax_path = p
            self.current_invoice_id = None
            self.loaded_invoice_data = {}
            self.lbl_tax.config(text=os.path.basename(p), fg="blue", font=("맑은 고딕", 9, "bold"))
            self.log(f"[수동첨부] 세금계산서 선택: {os.path.basename(p)}")
            self._refresh_tax_action_buttons()
        elif file_type == 'quote':
            self.quote_path = p
            self.lbl_quote.config(text=os.path.basename(p), fg="blue")
            self.approval_pdf_paths = []
            self.approval_order_number = ""
            self.approval_fetching = False
            self.lbl_approval.config(text="품의결재본: 분석 후 자동 확보", fg="#607d8b")
            self._refresh_approval_action_buttons()
            self.log(f"[수동첨부] 견적서/명세서 선택: {os.path.basename(p)}")

        if self.tax_path and self.quote_path:
            self.btn_analyze.config(text="🧠 지능형 문서 분석 시작", state="normal", bg="#9C27B0")
        self._refresh_batch_button_state()

    def _refresh_tax_action_buttons(self):
        state = "normal" if self.tax_path and os.path.exists(self.tax_path) else "disabled"
        try:
            self.btn_tax_download.config(
                state=state,
                bg="#1e88e5" if state == "normal" else "#b0bec5",
                activebackground="#1976d2" if state == "normal" else "#b0bec5",
                cursor="hand2" if state == "normal" else "arrow",
            )
            if hasattr(self, "btn_tax_preview"):
                self.btn_tax_preview.config(
                    state=state,
                    bg="#546e7a" if state == "normal" else "#b0bec5",
                    activebackground="#455a64" if state == "normal" else "#b0bec5",
                    cursor="hand2" if state == "normal" else "arrow",
                )
            self.btn_tax_print.config(
                state=state,
                bg="#fb8c00" if state == "normal" else "#b0bec5",
                activebackground="#ef6c00" if state == "normal" else "#b0bec5",
                cursor="hand2" if state == "normal" else "arrow",
            )
        except Exception:
            pass
        self._refresh_batch_button_state()

    def _refresh_approval_action_buttons(self):
        has_files = any(os.path.exists(p) for p in self.approval_pdf_paths)
        state = "normal" if has_files else "disabled"
        try:
            self.btn_approval_download.config(
                state=state,
                bg="#8e24aa" if state == "normal" else "#b0bec5",
                activebackground="#7b1fa2" if state == "normal" else "#b0bec5",
                cursor="hand2" if state == "normal" else "arrow",
            )
            self.btn_approval_print.config(
                state=state,
                bg="#6a1b9a" if state == "normal" else "#b0bec5",
                activebackground="#4a148c" if state == "normal" else "#b0bec5",
                cursor="hand2" if state == "normal" else "arrow",
            )
        except Exception:
            pass
        self._refresh_batch_button_state()

    def _find_local_python(self):
        candidates = [
            shutil.which("python"),
            r"C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe",
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return ""

    def _get_approval_output_dir(self):
        target_dir = os.path.join(BASE_EXE_DIR, "품의결재본")
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    def _fetch_approval_document_async(self, quote_path):
        if not quote_path or not os.path.exists(quote_path):
            return
        if self.approval_fetching:
            self.log("[APPROVAL] 품의결재본 확보가 이미 진행 중입니다.")
            return
        self.approval_fetching = True
        self.approval_pdf_paths = []
        self.approval_order_number = ""
        self.root.after(0, lambda: self.lbl_approval.config(text="품의결재본: 주문번호 분석 및 자동 다운로드 중...", fg="#7b1fa2"))
        self.root.after(0, self._refresh_approval_action_buttons)
        threading.Thread(target=self._approval_fetch_worker, args=(quote_path,), daemon=True).start()

    def _approval_fetch_worker(self, quote_path):
        helper_path = ""
        cfg_path = ""
        result_path = ""
        try:
            python_exe = self._find_local_python()
            if not python_exe:
                raise RuntimeError("로컬 Python 실행 파일을 찾지 못했습니다.")

            out_dir = self._get_approval_output_dir()
            helper_fd, helper_path = tempfile.mkstemp(prefix="approval_helper_", suffix=".py")
            os.close(helper_fd)
            cfg_fd, cfg_path = tempfile.mkstemp(prefix="approval_cfg_", suffix=".json")
            os.close(cfg_fd)
            result_fd, result_path = tempfile.mkstemp(prefix="approval_result_", suffix=".json")
            os.close(result_fd)
            Path(helper_path).write_text(APPROVAL_HELPER_SOURCE, encoding="utf-8")
            cfg = {
                "quote_path": quote_path,
                "output_dir": out_dir,
                "username": APPROVAL_DEFAULT_USER,
                "password": APPROVAL_DEFAULT_PASSWORD,
                "headless": True,
                "result_path": result_path,
            }
            Path(cfg_path).write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

            creationflags = 0x08000000 if os.name == "nt" else 0
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            proc = subprocess.Popen(
                [python_exe, "-X", "utf8", helper_path, cfg_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="ignore",
                creationflags=creationflags,
                env=env,
            )

            saved = []
            order_number = ""
            result_line = ""
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("LOG:"):
                    self.root.after(0, lambda m=line[4:]: self.log(f"[APPROVAL] {m}"))
                elif line.startswith("ORDER:"):
                    order_number = line[6:].strip()
                    self.root.after(0, lambda o=order_number: self.lbl_approval.config(text=f"품의결재본: 주문번호 ({o}) 검색 중", fg="#7b1fa2"))
                elif line.startswith("FILE:"):
                    saved.append(line[5:].strip())
                elif line.startswith("RESULT_JSON:"):
                    result_line = line[len("RESULT_JSON:"):].strip()
                else:
                    self.root.after(0, lambda m=line: self.log(f"[APPROVAL] {m}"))

            rc = proc.wait(timeout=5)
            if rc != 0:
                raise RuntimeError("품의결재본 다운로드 헬퍼가 비정상 종료되었습니다.")

            if result_path and os.path.exists(result_path):
                payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
                saved = payload.get("saved", saved) or saved
                order_number = payload.get("order_number", order_number) or order_number
            elif result_line:
                payload = json.loads(result_line)
                saved = payload.get("saved", saved) or saved
                order_number = payload.get("order_number", order_number) or order_number

            saved = [p for p in saved if p and os.path.exists(p)]
            if not saved:
                raise RuntimeError("품의결재본 PDF를 찾지 못했습니다.")

            self.approval_pdf_paths = saved
            self.approval_order_number = order_number
            label = f"품의결재본: {os.path.basename(saved[0])}"
            if len(saved) > 1:
                label = f"품의결재본: {len(saved)}건 확보 ({order_number})"
            self.root.after(0, lambda t=label: self.lbl_approval.config(text=t, fg="#1565c0"))
            for saved_path in saved:
                self.root.after(0, lambda p=saved_path: self.log(f"[APPROVAL] 저장 위치: {p}"))
            self.root.after(0, self._refresh_approval_action_buttons)
        except Exception as e:
            self.approval_pdf_paths = []
            self.approval_order_number = ""
            self.root.after(0, lambda msg=str(e): self.lbl_approval.config(text=f"품의결재본: 확보 실패 - {msg}", fg="#d32f2f"))
            self.root.after(0, lambda msg=str(e): self.log(f"[APPROVAL] 품의결재본 확보 실패: {msg}"))
            self.root.after(0, self._refresh_approval_action_buttons)
        finally:
            self.approval_fetching = False
            for temp_path in [helper_path, cfg_path, result_path]:
                try:
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception:
                    pass

    def download_approval_pdf(self):
        files = [p for p in self.approval_pdf_paths if os.path.exists(p)]
        if not files:
            messagebox.showwarning("안내", "다운로드할 품의결재본이 없습니다.", parent=self.root)
            return

        if len(files) == 1:
            src = Path(files[0])
            dst = filedialog.asksaveasfilename(
                parent=self.root,
                title="품의결재본 저장",
                initialfile=src.name,
                defaultextension=src.suffix or ".pdf",
                filetypes=[("PDF 파일", "*.pdf"), ("모든 파일", "*.*")]
            )
            if not dst:
                return
            targets = [(files[0], dst)]
        else:
            dst_dir = filedialog.askdirectory(parent=self.root, title="품의결재본 저장 폴더 선택")
            if not dst_dir:
                return
            targets = [(src, os.path.join(dst_dir, os.path.basename(src))) for src in files]

        try:
            for src, dst in targets:
                shutil.copy2(src, dst)
            self.log(f"✅ 품의결재본 저장 완료: {len(targets)}건")
            messagebox.showinfo("완료", "품의결재본 저장을 완료했습니다.", parent=self.root)
        except Exception as e:
            messagebox.showerror("오류", f"품의결재본 저장 실패:\n{e}", parent=self.root)

    def print_approval_pdf(self, choice=None, show_message=True):
        files = [p for p in self.approval_pdf_paths if os.path.exists(p)]
        if not files:
            messagebox.showwarning("안내", "출력할 품의결재본이 없습니다.", parent=self.root)
            return

        choice = self._resolve_print_choice(choice) if choice else self._ask_print_target_for_expense()
        if not choice:
            self.log("[APPROVAL-PRINT] 담당자가 출력안함을 선택했습니다.")
            return
        if choice.get("kind") == "pdf_merge":
            messagebox.showinfo("안내", "병합 PDF 저장은 One-Click 전표 SET 복사에서만 지원합니다.", parent=self.root)
            return

        printer_name = self._resolve_excel_printer_name(choice)
        if not printer_name:
            messagebox.showerror("오류", "선택한 프린터를 찾지 못했습니다.", parent=self.root)
            return

        original_printer = win32print.GetDefaultPrinter()
        try:
            win32print.SetDefaultPrinter(printer_name)
            for pdf_path in files:
                os.startfile(pdf_path, "print")
                time.sleep(1.5)
            self.log(f"✅ 품의결재본 출력 요청 완료: {len(files)}건 / {choice.get('label', printer_name)}")
            if show_message:
                messagebox.showinfo("완료", f"품의결재본 {len(files)}건을 {choice.get('label', printer_name)}로 출력 요청했습니다.", parent=self.root)
        except Exception as e:
            messagebox.showerror("오류", f"품의결재본 출력 실패:\n{e}", parent=self.root)
        finally:
            try:
                win32print.SetDefaultPrinter(original_printer)
            except Exception:
                pass

    def download_tax_invoice(self):
        if not self.tax_path or not os.path.exists(self.tax_path):
            messagebox.showwarning("안내", "다운로드할 세금계산서가 없습니다.", parent=self.root)
            return

        src = Path(self.tax_path)
        dst = filedialog.asksaveasfilename(
            parent=self.root,
            title="세금계산서 저장",
            initialfile=src.name,
            defaultextension=src.suffix or ".pdf",
            filetypes=[("문서 파일", "*.pdf;*.png;*.jpg;*.jpeg"), ("모든 파일", "*.*")]
        )
        if not dst:
            return

        try:
            shutil.copy2(self.tax_path, dst)
            self.log(f"✅ 세금계산서 저장 완료: {os.path.basename(dst)}")
            messagebox.showinfo("완료", "세금계산서를 저장했습니다.", parent=self.root)
        except Exception as e:
            messagebox.showerror("오류", f"세금계산서 저장 실패:\n{e}", parent=self.root)

    def preview_tax_invoice(self):
        if not self.tax_path or not os.path.exists(self.tax_path):
            messagebox.showwarning("안내", "미리보기할 세금계산서가 없습니다.", parent=self.root)
            return
        try:
            os.startfile(self.tax_path)
            msg = f"세금계산서 미리보기 열기: {os.path.basename(self.tax_path)}"
            if hasattr(self, "regular_log_box") and getattr(self, "regular_data", None):
                self.regular_log(msg)
            else:
                self.log(f"✅ {msg}")
        except Exception as e:
            messagebox.showerror("오류", f"세금계산서 미리보기 실패:\n{e}", parent=self.root)

    def print_tax_invoice(self, choice=None, show_message=True):
        if not self.tax_path or not os.path.exists(self.tax_path):
            messagebox.showwarning("안내", "출력할 세금계산서가 없습니다.", parent=self.root)
            return

        choice = self._resolve_print_choice(choice) if choice else self._ask_print_target_for_expense()
        if not choice:
            self.log("  [TAX-PRINT] 담당자가 출력안함을 선택했습니다.")
            return
        if choice.get("kind") == "pdf_merge":
            messagebox.showinfo("안내", "병합 PDF 저장은 One-Click 전표 SET 복사에서만 지원합니다.", parent=self.root)
            return

        printer_name = self._resolve_excel_printer_name(choice)
        if not printer_name:
            messagebox.showerror("오류", "선택한 프린터를 찾지 못했습니다.", parent=self.root)
            return

        original_printer = win32print.GetDefaultPrinter()
        try:
            win32print.SetDefaultPrinter(printer_name)
            os.startfile(self.tax_path, "print")
            time.sleep(1.5)
            self.log(f"✅ 세금계산서 출력 요청 완료: {choice.get('label', printer_name)}")
            if show_message:
                messagebox.showinfo("완료", f"세금계산서를 {choice.get('label', printer_name)}로 출력 요청했습니다.", parent=self.root)
        except Exception as e:
            messagebox.showerror("오류", f"세금계산서 출력 실패:\n{e}", parent=self.root)
        finally:
            try:
                win32print.SetDefaultPrinter(original_printer)
            except Exception:
                pass

    def process_ai_data(self, ai_data):
        site_raw = str(ai_data.get('site_name', '')).strip()
        site_name = ""
        raw_digits = re.sub(r'[^0-9\*]', '', site_raw)
        for full_num, f_name in FACTORY_MAP.items():
            clean_full = full_num.replace('-', '')
            if raw_digits == clean_full: 
                site_name = f_name
                break
            if '*' in raw_digits and len(raw_digits) == 10:
                match = True
                for idx, char in enumerate(raw_digits):
                    if char != '*' and char != clean_full[idx]: 
                        match = False
                        break
                if match: 
                    site_name = f_name
                    break
                    
        if not site_name: 
            site_name = "사업장미상" if re.match(r'\d{3}-?\d{2}-?\d{5}', site_raw) else (site_raw or "사업장미상")
            
        vn = str(ai_data.get('vendor_name', '매입처'))
        vn = re.sub(r'\(주\)|㈜|\(유\)|유한회사|주식회사', '', vn).strip()
        normalized_items = self._normalize_items_for_display(ai_data.get('items', []))
        items_total = sum(self._to_int(item.get('inc_vat')) for item in normalized_items)
        total_sum = self._to_int(ai_data.get('total_sum', 0))
        target_supply = self._to_int(ai_data.get('target_supply', 0))
        total_tax = self._to_int(ai_data.get('total_tax', 0))
        if not total_sum and items_total:
            total_sum = items_total
        if not target_supply and total_sum and total_tax:
            target_supply = max(0, total_sum - total_tax)
        if not total_tax and total_sum and target_supply:
            total_tax = max(0, total_sum - target_supply)

        loaded_invoice = getattr(self, "loaded_invoice_data", {}) or {}
        preserved_invoice_date = self._extract_issue_date_from_invoice_data(loaded_invoice, loaded_invoice)
        if not preserved_invoice_date:
            preserved_invoice_date = self._extract_issue_date_from_pdf(self.tax_path)

        site_name = self._recover_site_name(
            site_name,
            site_raw,
            self.tax_path,
            os.path.basename(str(self.tax_path or "")),
            loaded_invoice,
            ai_data,
        )

        self.data = {
            'site_name': site_name, 
            'vendor_name': vn, 
            'invoice_date': ai_data.get('invoice_date', '') or preserved_invoice_date,
            'total_sum': total_sum, 
            'target_supply': target_supply, 
            'total_tax': total_tax, 
            'items': normalized_items
        }
        self.log(f"[DEBUG] 분석 데이터 저장: site={site_name}, invoice_date={self.data.get('invoice_date')}, items={len(self.data.get('items', []))}")
        self.create_dept_fields()

    def _handle_analysis_success(self, ai_data, log_message):
        self.log(log_message)
        self.process_ai_data(ai_data)
        self._fetch_approval_document_async(self.quote_path)

    def start_analysis(self):
        if not self.tax_path or not self.quote_path: 
            messagebox.showwarning("필수 서류 누락", "세금계산서와 견적서를 모두 첨부해 주십시오.", parent=self.root)
            return
        for w in self.sf.winfo_children(): 
            w.destroy()
        self.btn_analyze.config(text="⏳ 문서 분석 중... 잠시만 기다려주세요.", state="disabled", bg="#9E9E9E")
        self.root.update()
        threading.Thread(target=self.analyze_pdfs, daemon=True).start()

    def analyze_pdfs(self):
        try:
            self.root.after(0, lambda: self.log("▶ 학습 DB 우선 탐색을 시작합니다..."))
            
            paths = [self.tax_path, self.quote_path]
            files_payload1 = [('files', (os.path.basename(p), open(p, 'rb'), 'application/octet-stream')) for p in paths]
            
            r1 = requests.post(ANALYZE_DB_URL, files=files_payload1, timeout=10)
            d1 = r1.json()
            for _, f_tuple in files_payload1: 
                f_tuple[1].close()

            if d1.get("status") == "success":
                ai_data = d1["data"]
                cnt = len(ai_data.get('items', []))
                msg = f"☑ 학습 DB 탐색 완료: 총 {cnt}건 발견, {cnt}건 반영 완료."
                self.root.after(0, lambda d=ai_data, m=msg: self._handle_analysis_success(d, m))
            elif d1.get("status") == "need_ai":
                self.root.after(0, lambda: self.log("▶ 견적서 판독 불가. AI 시각 엔진으로 추출 후 학습DB 매칭 진행..."))
                
                files_payload2 = [('files', (os.path.basename(p), open(p, 'rb'), 'application/octet-stream')) for p in paths]
                r2 = requests.post(ANALYZE_AI_URL, files=files_payload2, timeout=120)
                for _, f_tuple in files_payload2: 
                    f_tuple[1].close()

                if r2.status_code == 200:
                    ai_data = r2.json()
                    cnt = len(ai_data.get('items', []))
                    msg = f"☑ AI 문자 추출 및 DB 매칭 완료: 총 {cnt}건 성공."
                    self.root.after(0, lambda d=ai_data, m=msg: self._handle_analysis_success(d, m))
                else:
                    err_msg = r2.json().get('error', 'AI 분석 에러')
                    self.root.after(0, lambda: self.log(f"❌ Gemini 분석 실패: {err_msg}"))
                    self.root.after(0, lambda: messagebox.showerror("AI 에러", err_msg, parent=self.root))
            else: 
                self.root.after(0, lambda: messagebox.showerror("서버 에러", d1.get('error', 'DB 탐색 실패'), parent=self.root))
        except Exception as e: 
            self.root.after(0, lambda: messagebox.showerror("통신 오류", str(e), parent=self.root))
        finally: 
            self.root.after(0, lambda: self.btn_analyze.config(text="🧠 학습 DB 및 제미나이(AI) 분석 시작", state="normal", bg="#9C27B0"))

    def create_dept_fields(self):
        self.dept_entries = {}
        for w in self.sf.winfo_children(): 
            w.destroy()
            
        for i, h in enumerate(["계정과목", "품목명", "수량/단가", "부서 지정"]): 
            tk.Label(self.sf, text=h, font=("맑은 고딕", 9, "bold")).grid(row=0, column=i, pady=5)
            
        raw_list = self.data.get('items', [])
        t_inc = sum(i.get('inc_vat', 0) for i in raw_list)
        
        if t_inc > 0:
            for i in raw_list: 
                i['supply'] = int(self.data.get('target_supply', 0) * (i.get('inc_vat', 0) / t_inc))
            if raw_list: 
                max_item = max(raw_list, key=lambda x: x.get('inc_vat', 0))
                max_item['supply'] += (self.data.get('target_supply', 0) - sum(i.get('supply', 0) for i in raw_list))

        for idx, item in enumerate(raw_list):
            r = idx + 1
            ca = ttk.Combobox(self.sf, values=["집기비품", "컴퓨터소프트웨어", "소모품비"], width=16, state="readonly")
            ca.set(item.get('account', '소모품비'))
            ca.grid(row=r, column=0, padx=5, pady=3)
            
            en = tk.Entry(self.sf, width=30)
            en.insert(0, item.get('name', ''))
            en.grid(row=r, column=1, padx=5, pady=3)
            
            qty = max(1, item.get('qty', 1))
            unit_price = int(item.get('inc_vat', 0) / qty)
            tk.Label(self.sf, text=f"{qty}EA / {unit_price:,}원", fg="grey").grid(row=r, column=2, padx=5)
            
            ed = tk.Entry(self.sf, width=12)
            if not item.get('is_a', False): 
                ed.insert(0, "소모품")
                ed.config(state="disabled")
            ed.grid(row=r, column=3, padx=5, pady=3)
            
            def hdl(e_d):
                def _inner(ev):
                    if ev.widget.get() == "소모품비": 
                        e_d.config(state="normal")
                        e_d.delete(0, "end")
                        e_d.insert(0, "소모품")
                        e_d.config(state="disabled")
                    else:
                        e_d.config(state="normal")
                        if e_d.get() == "소모품": 
                            e_d.delete(0, "end")
                return _inner
                
            ca.bind("<<ComboboxSelected>>", hdl(ed))
            self.dept_entries[idx] = (item, ca, en, ed)
            
        self.btn_erp.config(state="normal")
        self.btn_cash.config(state="normal")
        self._refresh_batch_button_state()

    def save_all_to_db(self, items_to_save):
        for raw_desc, name, is_asset in items_to_save:
            if not raw_desc: continue
            try: 
                requests.post(DEV_SERVER_URL, json={"original_text": raw_desc, "corrected_name": name, "is_asset": is_asset}, timeout=5)
                time.sleep(0.5) 
            except: pass

    def get_unit_price(self, item):
        try: 
            return float(item.get('inc_vat', 0)) / max(1, int(item.get('qty', 1)))
        except: 
            return 0

    def _purchase_summary_name(self, name):
        text = re.sub(r'\s+', ' ', str(name or '').strip())
        text = text.replace("터치 모니터", "터치모니터")
        text = text.replace("모니터 암", "모니터암")
        return text

    def copy_erp(self):
        up = []
        items_to_save = []
        
        for k, (it, cb_acc, ent_name, ent_dept) in self.dept_entries.items():
            new_acc = cb_acc.get().strip()
            new_name = ent_name.get().strip()
            new_dept = ent_dept.get().strip()
            new_is_a = (new_acc != "소모품비")
            
            if new_is_a and not new_dept: 
                messagebox.showerror("확인 요망", f"[{new_name}] 부서를 기입해 주십시오.", parent=self.root)
                return
                
            items_to_save.append((it.get('raw_desc', ''), new_name, new_is_a))
            it_copy = it.copy()
            it_copy['account'] = new_acc
            it_copy['name'] = new_name
            it_copy['is_a'] = new_is_a
            it_copy['dept'] = new_dept
            up.append(it_copy)
            
        threading.Thread(target=self.save_all_to_db, args=(items_to_save,), daemon=True).start()
            
        as_l = [i for i in up if i['is_a']]
        su_l = [i for i in up if not i['is_a']]
        
        rs = []
        md = ""
        vn = self.data.get('vendor_name', '')
        
        for a in as_l:
            if not md: md = a['dept']
            supply = a.get('supply', 0)
            qty = a.get('qty', 1)
            site = self.data.get('site_name', '')
            rs.append(f"{a['account']}\t\t{supply}\t0\t{site} {a['name']}({a['dept']})({supply:,} - {qty}EA) - {vn}")
            
        sn = ""
        if su_l:
            rp = max(su_l, key=self.get_unit_price)
            sn = f"{rp['name']} 외 {len(su_l)-1}건" if len(su_l) > 1 else rp['name']
            sq = sum(s.get('qty', 1) for s in su_l)
            ss = sum(s.get('supply', 0) for s in su_l)
            site = self.data.get('site_name', '')
            rs.append(f"소모품비\t\t{ss}\t0\t{site} {sn}({ss:,} - {sq}EA) - {vn}")
            
        total_qty = sum(i.get('qty', 1) for i in up)
        target_sup = self.data.get('target_supply', 0)
        site = self.data.get('site_name', '')
        summary_names = []
        for item in up:
            name = self._purchase_summary_name(item.get('name', ''))
            if name and name not in summary_names:
                summary_names.append(name)
        summary_label = ", ".join(summary_names) if summary_names else (sn or "구매품")
        sumy = f"{site} {summary_label}({target_sup:,} - {total_qty}EA) - {vn}"
        
        rs.append(f"부가세대급금\t\t{self.data.get('total_tax', 0)}\t0\tV.A.T - {sumy}")
        rs.append(f"가지급금(업체)\t\t0\t{self.data.get('total_sum', 0)}\t{sumy}")

        invoice_date = str(self.data.get('invoice_date', '') or '').strip()
        if not invoice_date:
            invoice_date = self._extract_issue_date_from_pdf(self.tax_path)
            if invoice_date:
                self.data['invoice_date'] = invoice_date
                self.log(f"✅ 세금계산서 작성일자 복구: {invoice_date}")
        if not invoice_date:
            msg = "세금계산서 작성일자를 찾지 못해 ERP 전표 입력을 중단합니다. 오늘 날짜로 자동 입력하지 않습니다."
            self.log(f"❌ {msg}")
            messagebox.showerror("작성일자 확인 필요", msg, parent=self.root)
            return
        
        pyperclip.copy("\r\n".join(rs))
        needed_rows = len(rs)
        self.data['erp_row_count'] = needed_rows
        self.data['erp_clipboard_rows'] = rs
        self.log(f"[DEBUG] ERP rows={needed_rows}, invoice_date={self.data.get('invoice_date')}, site={self.data.get('site_name')}")

        if self.current_invoice_id:
            try: 
                requests.post(f"{SERVER_BASE}/api/invoice/complete", json={"id": self.current_invoice_id}, timeout=3)
                self.refresh_dashboard()
            except: pass

        self.log(f"✅ V4.1 규격 ERP 분개 데이터 생성 (총 {needed_rows}줄)")
        self.log("🚀 K-System(ERP) 활성화를 시작합니다...")
        self.root.update()

        corp_name = CORP_MAP.get(self.data.get('site_name', ''), "㈜대승")
        install_key = self.manager.config_mgr.config.get("COMMON", "default_install", fallback="DAESEUNG")
        corp_code = self.manager.config_mgr.config.get("COMMON", "default_corp", fallback="DS")
        
        if "대승정밀" in corp_name: 
            install_key = "DSJM"
            corp_code = "DSJM"
        elif "일강" in corp_name: 
            install_key = "ILGANG"
            corp_code = "ILGANG"
        elif "제이엠" in corp_name: 
            install_key = "JM"
            corp_code = "JM"
        elif "더원" in corp_name: 
            install_key = "TO"
            corp_code = "TO"

        bot = ERPLoginBot(self.manager.config_mgr.get_install_info(install_key), self.manager.config_mgr.get_corp_info(corp_code), corp_code, self.manager, self.manager.logger)
        bot_result = bot.run()

        if bot_result is True:
            self.log("✅ ERP 자동입력/저장/전표출력 호출 흐름을 완료했습니다.")
        else:
            err_msg = f"데이터는 복사되었으나 ERP 활성화에 실패했습니다.\n({bot_result})\n\n수동으로 ERP를 열고 빈 행을 [ {needed_rows}개 ] 추가하여\n[ Ctrl + V ] 로 붙여넣으세요."
            messagebox.showwarning("ERP 실행 실패", err_msg, parent=self.root)

    def _expense_items_from_entries(self):
        source_items = [dict(item) for item in list(self.data.get('items', []) or [])]
        items_by_idx = {idx: item for idx, item in enumerate(source_items)}

        for idx, (it, cb_acc, ent_name, ent_dept) in self.dept_entries.items():
            row = dict(items_by_idx.get(idx, it.copy()))
            row['account'] = cb_acc.get().strip() or row.get('account', '소모품비')
            row['name'] = ent_name.get().strip() or row.get('name', '품목')
            if ent_dept is not None:
                try:
                    row['dept'] = ent_dept.get().strip() or row.get('dept', '')
                except Exception:
                    pass
            items_by_idx[idx] = row

        items = [items_by_idx[idx] for idx in sorted(items_by_idx)]
        for row in items:
            row['qty'] = max(1, int(row.get('qty', 1) or 1))
            row['inc_vat'] = int(row.get('inc_vat', 0) or 0)
            row['account'] = (row.get('account') or '소모품비').strip()
            row['name'] = (row.get('name') or '품목').strip()
        return items

    def _extract_model_name(self, item):
        candidates = [str(item.get('raw_desc', '') or ''), str(item.get('name', '') or '')]
        pattern = r'\b[A-Z]{1,6}[A-Z0-9-]*\d[A-Z0-9-]*\b'
        for src in candidates:
            matches = re.findall(pattern, src.upper())
            matches = [m for m in matches if len(m) >= 4]
            if matches:
                return max(matches, key=len)
        return ""

    def _build_expense_report_text(self):
        items = self._expense_items_from_entries()
        sum_val = self._to_int(self.data.get('total_sum', 0))
        if not sum_val:
            sum_val = sum(self._to_int(item.get('inc_vat')) for item in items)

        account_order = ["집기비품", "컴퓨터소프트웨어", "소모품비"]
        account_alias = {
            "전산비품": "집기비품",
            "비품": "집기비품",
            "소프트웨어": "컴퓨터소프트웨어",
            "컴퓨터SW": "컴퓨터소프트웨어",
            "소모품": "소모품비",
        }
        grouped = {acc: [] for acc in account_order}
        for item in items:
            raw_account = (item.get('account') or '소모품비').strip()
            account = account_alias.get(raw_account, raw_account)
            if account not in grouped:
                account = "소모품비"
            grouped[account].append(item)
        dominant_account = max(
            account_order,
            key=lambda acc: (len(grouped.get(acc, [])), sum(int(i.get('inc_vat', 0) or 0) for i in grouped.get(acc, [])))
        )

        title_map = {
            "소모품비": "소모품 구매 건",
            "집기비품": "집기비품 구매 건",
            "컴퓨터소프트웨어": "컴퓨터소프트웨어 구매 건",
        }
        header_map = {
            "소모품비": "소모품 구매",
            "집기비품": "집기비품 구매",
            "컴퓨터소프트웨어": "컴퓨터소프트웨어 구매",
        }

        body_lines = ["* 내 용 *"]
        section_no = 1
        for account in account_order:
            account_items = grouped.get(account, [])
            if not account_items:
                continue
            body_lines.append(f"{section_no}. {header_map.get(account, '구매')}")
            if account == "소모품비":
                top_item = max(account_items, key=lambda item: int(item.get('inc_vat', 0) or 0))
                top_name = top_item.get('name', '품목')
                suffix = f" 외 {len(account_items) - 1}건" if len(account_items) > 1 else ""
                group_total = sum(int(it.get('inc_vat', 0) or 0) for it in account_items)
                body_lines.append(f"   └ {top_name}{suffix} : {group_total:,}원")
            else:
                for it in account_items:
                    name = it.get('name', '품목')
                    model = self._extract_model_name(it)
                    qty = max(1, int(it.get('qty', 1) or 1))
                    line_total = int(it.get('inc_vat', 0) or 0)
                    item_text = f"{name}({model})" if model and model not in str(name).upper() else name
                    body_lines.append(f"   └ {item_text} {qty}EA : {line_total:,}원")
            section_no += 1

        if section_no == 1:
            body_lines.append("1. 구매")
            for it in items:
                name = it.get('name', '품목')
                qty = max(1, int(it.get('qty', 1) or 1))
                line_total = int(it.get('inc_vat', 0) or 0)
                body_lines.append(f"   └ {name} {qty}EA : {line_total:,}원")
            section_no = 2

        body_lines.append(f"{section_no}. 총합 : {sum_val:,}원")
        return dominant_account, "\n".join(body_lines)

    def _expense_footer_text(self, site_name):
        corp = CORP_MAP.get(site_name, "㈜대승")
        if "대승정밀" in corp:
            return EXPENSE_FOOTER_MAP["DSJM"]
        if "일강" in corp:
            return EXPENSE_FOOTER_MAP["ILGANG"]
        return EXPENSE_FOOTER_MAP["DAESEUNG"]

    def _expense_author_name(self):
        raw_name = str(self.user_name or "").strip()
        cleaned = re.sub(r"\s*(매니저|님|사원|주임|대리|과장|차장|부장|이사|상무|전무|대표)$", "", raw_name)
        return cleaned.strip() or raw_name

    def _expense_excel_payload(self):
        sn = self.data.get('site_name', '사업장미상')
        expense_items = self._expense_items_from_entries()
        sum_val = self._to_int(self.data.get('total_sum', 0))
        if not sum_val:
            sum_val = sum(self._to_int(item.get('inc_vat')) for item in expense_items)
        dominant_account, body = self._build_expense_report_text()
        title_map = {
            "소모품비": "소모품 구매 건",
            "집기비품": "집기비품 구매 건",
            "컴퓨터소프트웨어": "컴퓨터소프트웨어 구매 건",
        }
        return {
            "date": datetime.now().strftime("%Y. %m. %d"),
            "dept": "전산팀",
            "author": self._expense_author_name(),
            "title": f"{title_map.get(dominant_account, '구매 건')}({sn})",
            "basis": "품의 결재본",
            "amount": f"₩{sum_val:,}",
            "body": body,
            "footer": self._expense_footer_text(sn),
        }

    def _expense_slot_is_empty(self, ws, slot):
        cells = slot["cells"]
        check_cells = [cells["title"], cells["amount"], cells["body"]]
        for addr in check_cells:
            value = ws.Range(addr).Value
            if value is not None and str(value).strip():
                return False
        return True

    def _write_expense_slot(self, ws, slot, payload):
        cells = slot["cells"]
        ws.Range(cells["date"]).Value = payload["date"]
        ws.Range(cells["dept"]).Value = payload["dept"]
        ws.Range(cells["author"]).Value = payload["author"]
        ws.Range(cells["title"]).Value = payload["title"]
        ws.Range(cells["basis"]).Value = payload["basis"]
        ws.Range(cells["amount"]).Value = payload["amount"]
        ws.Range(cells["body"]).Value = payload["body"]
        ws.Range(cells["footer"]).Value = payload["footer"]
        ws.Range(cells["body"]).WrapText = True

    def _clear_expense_slot(self, ws, slot):
        cells = slot["cells"]
        for key in ("date", "dept", "author", "title", "basis", "amount", "body", "footer"):
            ws.Range(cells[key]).Value = ""

    def _open_expense_workbook(self):
        target_path = os.path.normcase(os.path.abspath(EXPENSE_XLSX_PATH))
        try:
            app = win32.GetActiveObject("Excel.Application")
        except Exception:
            app = win32.DispatchEx("Excel.Application")

        app.Visible = True
        app.DisplayAlerts = False

        workbook = None
        for idx in range(1, app.Workbooks.Count + 1):
            book = app.Workbooks(idx)
            try:
                full_name = os.path.normcase(os.path.abspath(book.FullName))
            except Exception:
                continue
            if full_name == target_path:
                workbook = book
                break

        if workbook is None:
            workbook = app.Workbooks.Open(EXPENSE_XLSX_PATH)

        return app, workbook, workbook.Worksheets("출력용")

    def _ask_print_target_for_expense(self):
        result = {"choice": None}
        dialog = tk.Toplevel(self.root)
        dialog.title("출력 프린터 선택")
        dialog.geometry("360x250")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="어떤 프린터로 출력할까요?",
            font=("맑은 고딕", 12, "bold")
        ).pack(pady=(18, 10))

        def choose(choice):
            result["choice"] = choice
            dialog.destroy()

        buttons = [(f"{opt['label']} 출력", dict(opt)) for opt in PRINT_TARGET_OPTIONS]
        buttons.append(("닫기 : 출력안함", None))

        for text, choice in buttons:
            tk.Button(dialog, text=text, width=24, height=1, command=lambda c=choice: choose(c)).pack(pady=4)

        dialog.protocol("WM_DELETE_WINDOW", lambda: choose(None))
        dialog.focus_force()
        dialog.wait_window()
        return result["choice"]

    def _resolve_excel_printer_name(self, choice):
        target = str((choice or {}).get("match", "")).strip()
        if not target:
            return ""

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        try:
            for info in win32print.EnumPrinters(flags, None, 2):
                name = str(info.get("pPrinterName", "") or "")
                port = str(info.get("pPortName", "") or "")
                if target == "Microsoft Print To PDF":
                    if name == target:
                        return name
                elif port == target:
                    return name
        except Exception:
            pass
        return ""

    def _print_expense_workbook(self, app, workbook, sheet, choice=None):
        choice = self._resolve_print_choice(choice) if choice else self._ask_print_target_for_expense()
        if not choice:
            return False, "출력안함"
        if choice.get("kind") == "pdf_merge":
            raise RuntimeError("병합 PDF 저장은 One-Click 전표 SET 복사에서만 지원합니다.")

        printer_name = self._resolve_excel_printer_name(choice)
        if not printer_name:
            raise RuntimeError(f"프린터를 찾지 못했습니다. ({choice.get('match')})")

        original_printer = win32print.GetDefaultPrinter()
        try:
            win32print.SetDefaultPrinter(printer_name)
            app.Visible = True
            workbook.Activate()
            sheet.Activate()
            sheet.PrintOut(Copies=1)
        finally:
            try:
                win32print.SetDefaultPrinter(original_printer)
            except Exception:
                pass
        return True, choice.get("label", printer_name)

    def _prepare_expense_report_sheet(self):
        payload = self._expense_excel_payload()
        app, workbook, sheet = self._open_expense_workbook()
        target_slot = EXPENSE_FORM_SLOTS[0]
        self._clear_expense_slot(sheet, target_slot)
        self._write_expense_slot(sheet, target_slot, payload)
        workbook.Save()
        return app, workbook, sheet

    def _export_expense_workbook_pdf(self, sheet, output_path):
        sheet.ExportAsFixedFormat(0, output_path)

    def create_expense_report(self, choice=None, show_message=True):
        pythoncom.CoInitialize()
        try:
            app, workbook, sheet = self._prepare_expense_report_sheet()
            printed, label = self._print_expense_workbook(app, workbook, sheet, choice=choice)
            if printed:
                if show_message:
                    messagebox.showinfo("완료", f"현금출금정산서 양식 상단에 반영 후 {label}로 출력했습니다.", parent=self.root)
            else:
                if show_message:
                    messagebox.showinfo("완료", "현금출금정산서 양식 상단에 반영했습니다.", parent=self.root)
        except Exception as e:
            messagebox.showerror("엑셀 반영 오류", f"현금출금정산서 양식 반영 중 오류가 발생했습니다.\n{e}", parent=self.root)
        finally:
            pythoncom.CoUninitialize()

    def run_oneclick_set(self):
        if not self.dept_entries:
            messagebox.showwarning("안내", "먼저 분석을 완료해 주세요.", parent=self.root)
            return
        if not self.tax_path or not os.path.exists(self.tax_path):
            messagebox.showwarning("안내", "세금계산서가 없습니다.", parent=self.root)
            return
        if not self.approval_pdf_paths or not any(os.path.exists(p) for p in self.approval_pdf_paths):
            messagebox.showwarning("안내", "품의결재본이 아직 확보되지 않았습니다.", parent=self.root)
            return

        choice = self._get_selected_oneclick_choice()
        self.log(f"[SET] 원클릭 출력 시작: {choice['label']}")
        self.print_choice_override = dict(choice)
        self.batch_erp_pdf_path = ""
        self.last_erp_print_output = ""

        try:
            if choice["kind"] == "pdf_merge":
                out_path = filedialog.asksaveasfilename(
                    parent=self.root,
                    title="전표 SET 병합 PDF 저장",
                    initialfile=self._build_oneclick_pdf_filename(),
                    defaultextension=".pdf",
                    filetypes=[("PDF 파일", "*.pdf")],
                )
                if not out_path:
                    self.log("[SET] 병합 PDF 저장이 취소되었습니다.")
                    return
                batch_dir = os.path.join(tempfile.gettempdir(), f"erp_set_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                os.makedirs(batch_dir, exist_ok=True)
                self.batch_erp_pdf_path = os.path.join(batch_dir, "01_전표.pdf")
                self.print_choice_override["save_path"] = self.batch_erp_pdf_path

                self.copy_erp()
                erp_pdf = self.last_erp_print_output if os.path.exists(self.last_erp_print_output or "") else self.batch_erp_pdf_path
                if not os.path.exists(erp_pdf):
                    raise RuntimeError("전표 PDF 저장본을 찾지 못했습니다.")

                pythoncom.CoInitialize()
                try:
                    app, workbook, sheet = self._prepare_expense_report_sheet()
                    expense_pdf = os.path.join(batch_dir, "04_현금출금결의서.pdf")
                    self._export_expense_workbook_pdf(sheet, expense_pdf)
                finally:
                    pythoncom.CoUninitialize()

                merge_sources = [erp_pdf, self.tax_path]
                merge_sources.extend([p for p in self.approval_pdf_paths if os.path.exists(p)])
                merge_sources.append(expense_pdf)
                self._merge_pdf_documents(merge_sources, out_path)
                self.log(f"✅ 원클릭 SET 병합 PDF 저장 완료: {out_path}")
                messagebox.showinfo("완료", f"전표 SET 병합 PDF를 저장했습니다.\n{out_path}", parent=self.root)
            else:
                self.copy_erp()
                self.print_tax_invoice(choice=choice, show_message=False)
                self.print_approval_pdf(choice=choice, show_message=False)
                self.create_expense_report(choice=choice, show_message=False)
                self.log(f"✅ 원클릭 SET 출력 완료: {choice['label']}")
                messagebox.showinfo("완료", f"전표 1세트 출력을 완료했습니다.\n대상: {choice['label']}", parent=self.root)
        finally:
            self.print_choice_override = None
            self.batch_erp_pdf_path = ""

if __name__ == "__main__":
    root = tk.Tk()
    AppManager(root)
    root.mainloop()
