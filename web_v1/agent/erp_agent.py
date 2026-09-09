from __future__ import annotations

import argparse
import configparser
import ctypes
import hashlib
import importlib
import json
import os
import platform
import queue
import shutil
import socket
import subprocess
import sys
import ssl
import tempfile
import threading
import time
import zipfile
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests


def _set_process_dpi_awareness_early() -> None:
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
try:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass


AGENT_DIR = Path(__file__).resolve().parent
WEB_ROOT = AGENT_DIR.parent
PROJECT_ROOT = WEB_ROOT.parent
LEGACY_MANAGER = PROJECT_ROOT / "manager_server" / "전표 자동화 프로그램(담당자용)_v6.2.py"
DEFAULT_CONFIGS = [
    PROJECT_ROOT / "manager_server" / "config.ini",
    PROJECT_ROOT / "support" / "config.ini",
]
REQUIRED_PACKAGES = [
    "pyautogui",
    "pyperclip",
    "pywinauto",
    "psutil",
    "win32gui",
    "win32con",
    "win32print",
    "fitz",
    "PIL",
]
PACKAGE_INSTALL_NAMES = {
    "fitz": "pymupdf",
    "PIL": "pillow",
    "win32gui": "pywin32",
    "win32con": "pywin32",
    "win32print": "pywin32",
}
ERP_BASE_DIR = Path(os.getenv("ERP_BASE_DIR", r"C:\Users\Public\AppData\Local\Younglimwon\KSystem ver.5 Genuine"))
ERP_OUTPUT_DIR = Path(os.getenv("ERP_OUTPUT_DIR", r"C:\ERP_DB\erp_outputs"))
AGENT_CONFIG_PATH = Path(os.getenv("ERP_AGENT_CONFIG_PATH", r"C:\ERP_DB\agent_config.json"))
INSTALL_CACHE_DIR = Path(os.getenv("ERP_INSTALL_CACHE_DIR", r"C:\ERP_DB\agent_install_cache"))
CERT_CACHE_DIR = Path(os.getenv("WEB_V1_CERT_CACHE_DIR", r"C:\ERP_DB\certs"))
CERT_INSTALL_TOKEN = "__https_certificate__"
AGENT_APPDATA_ROOT = Path(os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming"))
AGENT_APPDATA_DIR = Path(os.getenv("ACCOUNTING_WEB_APPDATA_DIR") or AGENT_APPDATA_ROOT / "AccountingWeb")
EXPENSE_TEMPLATE_DEST = Path(os.getenv("EXPENSE_REPORT_TEMPLATE_PATH") or AGENT_APPDATA_ROOT / "양식_현금출금정산서.xlsx")
EXPENSE_TEMPLATE_SOURCE_CANDIDATES = [
    PROJECT_ROOT / "support" / "expense_template.xlsx",
    PROJECT_ROOT / "support" / "양식_현금출금정산서_공통.xlsx",
    PROJECT_ROOT / "support" / "양식_현금출금정산서.xlsx",
]
REQUIRED_ERP_COMPANIES = ["대승", "대승정밀", "일강"]
PRINTER_KEYS = ["pyeongtaek", "gimje", "pdf"]
HASH_FILE_SUFFIXES = {".py", ".ps1", ".txt", ".json"}
HASH_DIRS = ("web_v1/agent", "web_v1/backend", "web_v1/deploy", "manager_server")
HASH_FILES = ("web_v1/VERSION",)
AGENT_BUNDLE_VERSION = "1.0.238"
_MUTEX_HANDLE: Any = None

ERP_RUNTIME_PROFILE_FORCE_KEYS = frozenset(
    {
        "ERP_FAST_INPUT",
        "ERP_FAST_FIELD_VERIFY",
        "ERP_FAST_MANAGEMENT",
        "ERP_STABLE_HEADER_FIELDS",
        "ERP_AGENT_FRESH_START",
        "ERP_MGMT_DOUBLE_CLICK_INTERVAL",
        "ERP_MGMT_SUMMARY_OPEN_WAIT",
        "ERP_VENDOR_POPUP_DETECT_TIMEOUT_SEC",
        "ERP_VENDOR_SEARCH_WAIT_SEC",
        "ERP_VENDOR_KEY_INTERVAL",
        "ERP_VENDOR_ENTER_INTERVAL",
        "ERP_VENDOR_VERIFY_TIMEOUT_SEC",
        "ERP_VENDOR_SELECTION_ATTEMPTS",
        "ERP_SLIP_OPEN_WAIT",
        "ERP_NEW_FORM_WAIT",
    }
)


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _erp_task_runtime_profile(task: dict[str, Any]) -> tuple[str, dict[str, str]]:
    """Return task-scoped ERP timing and safety defaults."""
    source_context = task.get("source_job_payload") if isinstance(task.get("source_job_payload"), dict) else {}
    is_regular_auto = bool(task.get("regular_auto") or source_context.get("regular_auto"))
    if is_regular_auto:
        return "regular-auto", {
            "ERP_FAST_MANAGEMENT": "1",
            "ERP_MGMT_KEY_WAIT": "0.10",
            "ERP_MGMT_COMMIT_WAIT": "0.18",
            "ERP_MGMT_FOCUS_WAIT": "0.12",
            "ERP_MGMT_CLICK_WAIT": "0.14",
            "ERP_MGMT_CLIPBOARD_WAIT": "0.04",
            "ERP_MGMT_SUMMARY_OPEN_WAIT": "0.42",
            "ERP_MGMT_AFTER_GRID_PASTE_WAIT": "0.50",
        }

    job_type = str(task.get("job_type") or "").strip().lower()
    one_click_mode = str(source_context.get("one_click_mode") or task.get("one_click_mode") or "").strip().lower()
    invoices = task.get("invoices") if isinstance(task.get("invoices"), list) else []
    is_purchase = (
        job_type in {"purchase_erp_input", "purchase_one_click"}
        or one_click_mode == "purchase"
        or any(
            str(item.get("invoice_type") or "").strip().lower() == "purchase"
            for item in invoices
            if isinstance(item, dict)
        )
    )
    if not is_purchase:
        return "", {}

    # Interactive purchase work runs on the requesting user's normal PC.
    # The slow 243 PC uses the separate regular-auto profile above.
    return "purchase-interactive", {
        "ERP_FAST_INPUT": "0",
        "ERP_FAST_FIELD_VERIFY": "0",
        "ERP_STABLE_HEADER_FIELDS": "1",
        "ERP_CRITICAL_FIELD_WAIT": "0.45",
        "ERP_PYAUTOGUI_SAFE_PAUSE": "0.10",
        "ERP_FAST_MANAGEMENT": "0",
        "ERP_MGMT_KEY_WAIT": "0.16",
        "ERP_MGMT_COMMIT_WAIT": "0.26",
        "ERP_MGMT_FOCUS_WAIT": "0.20",
        "ERP_MGMT_CLICK_WAIT": "0.24",
        "ERP_MGMT_CLIPBOARD_WAIT": "0.08",
        "ERP_MGMT_AFTER_GRID_PASTE_WAIT": "0.70",
        "ERP_FAST_NAVIGATION": "1",
        "ERP_STRICT_VENDOR_SELECTION": "1",
        "ERP_AGENT_FRESH_START": "1",
        "ERP_MGMT_DOUBLE_CLICK_INTERVAL": "0.20",
        "ERP_MGMT_SUMMARY_OPEN_WAIT": "0.90",
        "ERP_VENDOR_POPUP_DETECT_TIMEOUT_SEC": "4.0",
        "ERP_VENDOR_SEARCH_WAIT_SEC": "1.0",
        "ERP_VENDOR_KEY_INTERVAL": "0.18",
        "ERP_VENDOR_ENTER_INTERVAL": "0.28",
        "ERP_VENDOR_VERIFY_TIMEOUT_SEC": "3.0",
        "ERP_VENDOR_SELECTION_ATTEMPTS": "3",
        "ERP_NEW_FORM_WAIT": "0.80",
        "ERP_SLIP_OPEN_WAIT": "3.00",
        "ERP_PRINT_SAVE_WAIT": "0.80",
        "ERP_PRINT_VIEWER_TIMEOUT_SEC": "4.0",
        "ERP_PRINT_DIALOG_TIMEOUT_SEC": "4.0",
        "ERP_PDF_SAVE_DIALOG_TIMEOUT_SEC": "6.0",
        "ERP_PDF_CREATED_TIMEOUT_SEC": "4.0",
        "ERP_PDF_SAVE_RETRIES": "1",
        "ERP_AGENT_PROGRESS_THROTTLE_SEC": "4.0",
    }


def _apply_erp_runtime_profile(profile: dict[str, str]) -> dict[str, str | None]:
    """Apply task settings while forcing safety-critical purchase values."""
    previous: dict[str, str | None] = {}
    for key, value in profile.items():
        previous[key] = os.environ.get(key)
        if key in ERP_RUNTIME_PROFILE_FORCE_KEYS or key not in os.environ:
            os.environ[key] = value
    return previous


def _restore_erp_runtime_profile(previous: dict[str, str | None]) -> None:
    for key, old_value in previous.items():
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value


def log(message: str) -> None:
    print(f"[{now_text()}] {message}", flush=True)
    try:
        AGENT_APPDATA_DIR.mkdir(parents=True, exist_ok=True)
        with (AGENT_APPDATA_DIR / "agent.log").open("a", encoding="utf-8") as fh:
            fh.write(f"[{now_text()}] {message}\n")
    except Exception:
        pass


def _acquire_single_instance(agent_id: str, server_url: str) -> bool:
    global _MUTEX_HANDLE
    if os.name != "nt":
        return True
    name_seed = hashlib.sha1(f"{server_url}|{agent_id}".encode("utf-8", errors="ignore")).hexdigest()
    mutex_name = f"Global\\AccountingWebAgent_{name_seed}"
    kernel32 = ctypes.windll.kernel32
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, mutex_name)
    if not _MUTEX_HANDLE:
        return True
    return kernel32.GetLastError() != 183


class AgentTray:
    def __init__(self, server_url: str) -> None:
        self.server_url = server_url
        self.status = "Starting"
        self.stop_requested = False
        self.manual_update_requested = False
        self.update_message = ""
        self._hwnd = None
        self._notify_id = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if os.name != "nt":
            return
        self._thread = threading.Thread(target=self._run, name="accounting-web-tray", daemon=True)
        self._thread.start()

    def update(self, status: str) -> None:
        self.status = status
        self._modify()

    def set_update_message(self, message: str) -> None:
        self.update_message = message

    def consume_manual_update_request(self) -> bool:
        requested = self.manual_update_requested
        self.manual_update_requested = False
        return requested

    def notify(self, title: str, message: str) -> None:
        if not self._hwnd:
            return
        try:
            import win32con
            import win32gui
            data = (self._hwnd, 0, win32gui.NIF_INFO, win32con.WM_USER + 20, 0, f"Accounting WEB Agent - {self.status}"[:127], 0, 0, message[:255], title[:63], getattr(win32gui, "NIIF_INFO", 1))
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, data)
        except Exception as exc:
            log(f"tray notify failed: {exc}")

    def _message_box(self, title: str, body: str) -> None:
        try:
            ctypes.windll.user32.MessageBoxW(0, body, title, 0x40)
        except Exception as exc:
            log(f"tray message box failed: {exc}")

    def _run(self) -> None:
        try:
            import win32api
            import win32con
            import win32gui
            message_map = {
                win32con.WM_DESTROY: self._on_destroy,
                win32con.WM_COMMAND: self._on_command,
                win32con.WM_CONTEXTMENU: self._on_context_menu,
                win32con.WM_USER + 20: self._on_notify,
            }
            wc = win32gui.WNDCLASS()
            wc.hInstance = win32api.GetModuleHandle(None)
            wc.lpszClassName = "AccountingWebAgentTray"
            wc.lpfnWndProc = message_map
            class_atom = win32gui.RegisterClass(wc)
            self._hwnd = win32gui.CreateWindow(class_atom, "Accounting WEB Agent", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)
            icon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
            self._notify_id = (self._hwnd, 0, win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP, win32con.WM_USER + 20, icon, f"Accounting WEB Agent - {self.status}")
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, self._notify_id)
            win32gui.PumpMessages()
        except Exception as exc:
            log(f"tray unavailable: {exc}")

    def _modify(self) -> None:
        if not self._notify_id:
            return
        try:
            import win32gui
            data = list(self._notify_id)
            data[5] = f"Accounting WEB Agent - {self.status}"[:127]
            self._notify_id = tuple(data)
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, self._notify_id)
        except Exception:
            pass

    def _on_destroy(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        try:
            import win32gui
            if self._notify_id:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, self._notify_id)
            win32gui.PostQuitMessage(0)
        except Exception:
            pass
        return 0

    def _on_command(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        command_id = int(wparam) & 0xFFFF
        self._handle_menu_command(command_id, hwnd)
        return 0

    def _handle_menu_command(self, command_id: int, hwnd: int) -> None:
        if command_id == 1001:
            self._message_box("회계업무 WEB 내 상태", f"상태: {self.status}\n서버: {self.server_url}\nAgent 버전: {AGENT_BUNDLE_VERSION}")
        elif command_id == 1002:
            self.manual_update_requested = True
            self.notify("회계업무 WEB", "최신 버전 확인을 시작합니다.")
        elif command_id == 1003:
            message = f"Agent 버전: {AGENT_BUNDLE_VERSION}"
            if self.update_message:
                message += f"\n\n최근 업데이트 안내:\n{self.update_message}"
            self._message_box("회계업무 WEB 버전", message)
        elif command_id == 1004:
            self.stop_requested = True
            try:
                import win32gui
                win32gui.DestroyWindow(hwnd)
            except Exception:
                pass

    def _show_menu(self, hwnd: int) -> None:
        try:
            import win32con
            import win32gui

            menu = win32gui.CreatePopupMenu()
            try:
                win32gui.AppendMenu(menu, win32con.MF_STRING, 1001, "내 상태 확인")
                win32gui.AppendMenu(menu, win32con.MF_STRING, 1002, "수동 업데이트")
                win32gui.AppendMenu(menu, win32con.MF_STRING, 1003, "버전확인")
                win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
                win32gui.AppendMenu(menu, win32con.MF_STRING, 1004, "종료")
                pos = win32gui.GetCursorPos()
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception as exc:
                    log(f"tray foreground skipped: {exc}")
                flags = win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON | getattr(win32con, "TPM_RETURNCMD", 0x0100)
                command_id = win32gui.TrackPopupMenu(menu, flags, pos[0], pos[1], 0, hwnd, None)
                try:
                    win32gui.PostMessage(hwnd, win32con.WM_NULL, 0, 0)
                except Exception:
                    pass
                if command_id:
                    self._handle_menu_command(int(command_id), hwnd)
            finally:
                try:
                    win32gui.DestroyMenu(menu)
                except Exception:
                    pass
        except Exception as exc:
            log(f"tray menu failed: {exc}")

    def _on_context_menu(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        self._show_menu(hwnd)
        return 0

    def _on_notify(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        try:
            import win32con
            event = int(lparam) & 0xFFFF
            if event == win32con.WM_LBUTTONDBLCLK:
                os.startfile(self.server_url)
            elif event in {win32con.WM_RBUTTONUP, win32con.WM_CONTEXTMENU}:
                self._show_menu(hwnd)
        except Exception as exc:
            log(f"tray notify event failed: {exc}")
        return 0


def _agent_bundle_hash() -> str:
    try:
        files: list[Path] = []
        for rel in HASH_FILES:
            path = PROJECT_ROOT / rel
            if path.is_file():
                files.append(path)
        for rel in HASH_DIRS:
            root = PROJECT_ROOT / rel
            if not root.exists():
                continue
            for path in root.rglob("*"):
                name = path.name.lower()
                if not path.is_file():
                    continue
                if "__pycache__" in path.parts:
                    continue
                if ".backup_" in name or name.endswith((".bak", ".tmp", ".log", ".pyc", ".pyo")):
                    continue
                if path.suffix.lower() in HASH_FILE_SUFFIXES:
                    files.append(path)
        digest = hashlib.sha256()
        for path in sorted(files, key=lambda item: item.relative_to(PROJECT_ROOT).as_posix().lower()):
            rel = path.relative_to(PROJECT_ROOT).as_posix().lower()
            digest.update(rel.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()
    except Exception as exc:
        return f"error:{exc}"


def _post(server: str, path: str, payload: dict[str, Any], *, verify: bool, timeout: int = 20) -> requests.Response:
    return requests.post(f"{server.rstrip('/')}{path}", json=payload, verify=verify, timeout=timeout)


class _ProgressEventDispatcher:
    """Send noisy ERP progress events without blocking the desktop automation thread."""

    def __init__(
        self,
        server: str,
        job_id: str,
        agent_id: str,
        verify: bool,
        *,
        max_pending: int = 32,
        request_timeout: int = 2,
    ) -> None:
        self.server = server
        self.job_id = job_id
        self.agent_id = agent_id
        self.verify = verify
        self.request_timeout = max(1, int(request_timeout))
        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=max(1, int(max_pending)))
        self._closed = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name=f"erp-progress-{job_id[:8] or 'job'}",
            daemon=True,
        )
        self._thread.start()

    def submit(self, payload: dict[str, Any]) -> None:
        if self._closed.is_set():
            return
        event = dict(payload)
        event.setdefault("agent_id", self.agent_id)
        try:
            self._queue.put_nowait(event)
            return
        except queue.Full:
            pass
        # Preserve current desktop automation over stale diagnostic chatter.
        try:
            self._queue.get_nowait()
            self._queue.task_done()
        except queue.Empty:
            pass
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            pass

    def _run(self) -> None:
        while True:
            event = self._queue.get()
            try:
                if event is None:
                    return
                try:
                    _post(
                        self.server,
                        f"/api/agent/jobs/{self.job_id}/event",
                        event,
                        verify=self.verify,
                        timeout=self.request_timeout,
                    )
                except Exception as exc:
                    log(f"ERP progress event skipped: {exc}")
            finally:
                self._queue.task_done()

    def close(self, timeout: float = 3.0) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        # Completion/error reporting is authoritative. Drop stale queued progress
        # so it cannot arrive after the final job status.
        while True:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        self._thread.join(timeout=max(0.0, float(timeout)))


def _upload_erp_voucher(
    server: str,
    job_id: str,
    invoice_id: int,
    erp_pdf_path: Any,
    agent_id: str,
    verify: bool,
) -> dict[str, Any]:
    path_text = str(erp_pdf_path or "").strip().strip('"')
    if not path_text:
        return {"ok": False, "error": "ERP 전표 PDF 경로가 비어 있습니다."}
    pdf_path = Path(path_text).expanduser()
    if not pdf_path.exists() or not pdf_path.is_file():
        return {"ok": False, "error": f"ERP 전표 PDF 파일이 없습니다: {pdf_path}", "local_path": str(pdf_path)}
    try:
        with pdf_path.open("rb") as fh:
            response = requests.post(
                f"{server.rstrip('/')}/api/agent/jobs/{job_id}/voucher",
                data={
                    "agent_id": agent_id,
                    "invoice_id": str(invoice_id),
                    "local_path": str(pdf_path),
                },
                files={"file": (pdf_path.name, fh, "application/pdf")},
                verify=verify,
                timeout=120,
            )
        response.raise_for_status()
        payload = response.json() if response.content else {}
        server_path = str(payload.get("server_path") or payload.get("erp_pdf_path") or "").strip()
        return {"ok": True, "server_path": server_path, "local_path": str(pdf_path)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "local_path": str(pdf_path)}


def _upload_expense_report(
    server: str,
    job_id: str,
    invoice_id: int,
    pdf_path_value: Any,
    agent_id: str,
    verify: bool,
) -> dict[str, Any]:
    path_text = str(pdf_path_value or "").strip().strip('"')
    if not path_text:
        return {"ok": False, "error": "expense report PDF path is empty"}
    pdf_path = Path(path_text).expanduser()
    if not pdf_path.exists() or not pdf_path.is_file():
        return {"ok": False, "error": f"expense report PDF file is missing: {pdf_path}", "local_path": str(pdf_path)}
    try:
        with pdf_path.open("rb") as fh:
            response = requests.post(
                f"{server.rstrip('/')}/api/agent/jobs/{job_id}/expense-report",
                data={
                    "agent_id": agent_id,
                    "invoice_id": str(invoice_id),
                    "local_path": str(pdf_path),
                },
                files={"file": (pdf_path.name, fh, "application/pdf")},
                verify=verify,
                timeout=120,
            )
        response.raise_for_status()
        payload = response.json() if response.content else {}
        server_path = str(payload.get("server_path") or payload.get("expense_report_pdf_path") or "").strip()
        return {"ok": True, "server_path": server_path, "local_path": str(pdf_path)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "local_path": str(pdf_path)}


def _safe_print_filename(value: str, fallback: str) -> str:
    name = Path(str(value or fallback)).name.strip() or fallback
    for char in '<>:"/\\|?*':
        name = name.replace(char, "_")
    return name[:140] or fallback


def _output_print_file_key(invoice_id: int, file_index: int) -> str:
    return f"{int(invoice_id)}:{int(file_index)}"


def _download_output_print_file(
    server: str,
    job_id: str,
    invoice_id: int,
    file_index: int,
    filename: str,
    verify: bool,
) -> Path:
    target_dir = Path(os.getenv("TEMP") or r"C:\Windows\Temp") / "AccountingWeb" / "output_print" / job_id
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_print_filename(filename, f"{invoice_id}_{file_index}.pdf")
    target = target_dir / f"{invoice_id}_{file_index:02d}_{safe_name}"
    response = requests.get(
        f"{server.rstrip('/')}/api/agent/jobs/{job_id}/print-file/{invoice_id}/{file_index}",
        verify=verify,
        timeout=120,
        stream=True,
    )
    response.raise_for_status()
    with target.open("wb") as out:
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if chunk:
                out.write(chunk)
    return target


def _pdf_print_app_candidates() -> list[Path]:
    roots = [
        os.getenv("ProgramFiles"),
        os.getenv("ProgramFiles(x86)"),
        os.getenv("LOCALAPPDATA"),
    ]
    rels = [
        r"Adobe\Acrobat DC\Acrobat\Acrobat.exe",
        r"Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        r"Adobe\Acrobat Reader\Reader\AcroRd32.exe",
    ]
    candidates: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not root:
            continue
        for rel in rels:
            path = Path(root) / rel
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            if path.exists() and path.is_file():
                candidates.append(path)
    return candidates


def _print_pdf_with_direct_app(path: Path, printer_name: str) -> str:
    errors: list[str] = []
    wait_seconds = float(
        os.getenv(
            "ERP_AGENT_PDF_PRINT_LAUNCH_WAIT_SECONDS",
            os.getenv("ERP_AGENT_PDF_PRINT_WAIT_SECONDS", "0.8"),
        )
        or "0.8"
    )
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for exe in _pdf_print_app_candidates():
        try:
            proc = subprocess.Popen(
                [str(exe), "/t", str(path), printer_name],
                cwd=str(path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=creationflags,
            )
            time.sleep(max(wait_seconds, 0.5))
            code = proc.poll()
            if code not in (None, 0):
                errors.append(f"{exe.name}: exit {code}")
                continue
            return str(exe)
        except Exception as exc:
            errors.append(f"{exe.name}: {exc}")
    if errors:
        raise RuntimeError("; ".join(errors))
    raise RuntimeError("Adobe/Reader PDF print app not found")


def _printer_spooler_snapshot(printer_name: str) -> tuple[bool, set[int], str]:
    """Return the current local Windows spooler job ids for the selected printer."""
    try:
        import win32print

        handle = win32print.OpenPrinter(printer_name)
        try:
            jobs = win32print.EnumJobs(handle, 0, 512, 1) or []
        finally:
            win32print.ClosePrinter(handle)
        job_ids = {
            int(job.get("JobId") or 0)
            for job in jobs
            if isinstance(job, dict) and int(job.get("JobId") or 0) > 0
        }
        return True, job_ids, ""
    except Exception as exc:
        return False, set(), str(exc) or exc.__class__.__name__


def _wait_for_new_printer_job(
    printer_name: str,
    before_job_ids: set[int],
    *,
    timeout_seconds: float,
) -> tuple[bool, list[int], str]:
    """Wait until the Windows spooler exposes a job created after an output request."""
    end_at = time.monotonic() + max(0.5, timeout_seconds)
    last_error = ""
    while time.monotonic() < end_at:
        available, job_ids, error = _printer_spooler_snapshot(printer_name)
        if not available:
            last_error = error
            break
        new_job_ids = sorted(job_ids - before_job_ids)
        if new_job_ids:
            return True, new_job_ids, ""
        time.sleep(0.20)
    return False, [], last_error


class _PdfPrintSubmissionError(RuntimeError):
    def __init__(self, message: str, *, may_have_printed: bool) -> None:
        super().__init__(message)
        self.may_have_printed = bool(may_have_printed)


def _fit_pdf_page_to_printable_area(
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
) -> tuple[int, int, int, int]:
    if min(source_width, source_height, target_width, target_height) <= 0:
        raise ValueError("PDF/프린터 출력 영역 크기가 올바르지 않습니다.")
    scale = min(target_width / source_width, target_height / source_height)
    width = max(1, int(round(source_width * scale)))
    height = max(1, int(round(source_height * scale)))
    left = max(0, (target_width - width) // 2)
    top = max(0, (target_height - height) // 2)
    return left, top, left + width, top + height


def _printer_devmode(printer_name: str, *, landscape: bool):
    import win32con
    import win32print

    handle = win32print.OpenPrinter(printer_name)
    try:
        info = win32print.GetPrinter(handle, 2)
        devmode = info.get("pDevMode") if isinstance(info, dict) else None
        if devmode is None:
            raise RuntimeError("프린터 DEVMODE를 읽을 수 없습니다.")
        devmode.Orientation = (
            win32con.DMORIENT_LANDSCAPE if landscape else win32con.DMORIENT_PORTRAIT
        )
        devmode.PaperSize = win32con.DMPAPER_A4
        devmode.Copies = 1
        devmode.Scale = 100
        devmode.Fields |= (
            win32con.DM_ORIENTATION
            | win32con.DM_PAPERSIZE
            | win32con.DM_COPIES
            | win32con.DM_SCALE
        )
        if hasattr(devmode, "Nup"):
            devmode.Nup = 1
            devmode.Fields |= win32con.DM_NUP
        result = win32print.DocumentProperties(
            0,
            handle,
            printer_name,
            devmode,
            devmode,
            win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER,
        )
        if result < 0:
            raise RuntimeError(f"프린터 용지 설정 적용 실패: {result}")
        return devmode
    finally:
        win32print.ClosePrinter(handle)


def _print_pdf_with_gdi_fit(path: Path, printer_name: str) -> dict[str, Any]:
    import fitz
    import win32con
    import win32gui
    import win32ui
    from PIL import Image, ImageWin

    document = None
    dc = None
    document_started = False
    page_started = False
    submitted_pages = 0
    try:
        document = fitz.open(str(path))
        if document.page_count <= 0:
            raise RuntimeError("PDF에 출력할 페이지가 없습니다.")
        first_rect = document.load_page(0).rect
        devmode = _printer_devmode(
            printer_name,
            landscape=float(first_rect.width) > float(first_rect.height),
        )
        hdc = win32gui.CreateDC("WINSPOOL", printer_name, devmode)
        if not hdc:
            raise RuntimeError("프린터 출력 장치를 열 수 없습니다.")
        dc = win32ui.CreateDCFromHandle(hdc)
        target_width = int(dc.GetDeviceCaps(win32con.HORZRES) or 0)
        target_height = int(dc.GetDeviceCaps(win32con.VERTRES) or 0)
        printer_dpi = max(
            int(dc.GetDeviceCaps(win32con.LOGPIXELSX) or 0),
            int(dc.GetDeviceCaps(win32con.LOGPIXELSY) or 0),
            200,
        )
        render_dpi = min(printer_dpi, 300)
        job_id = int(dc.StartDoc(f"Accounting WEB - {path.name}") or 0)
        document_started = True
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(dpi=render_dpi, alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            destination = _fit_pdf_page_to_printable_area(
                image.width,
                image.height,
                target_width,
                target_height,
            )
            dc.StartPage()
            page_started = True
            ImageWin.Dib(image).draw(dc.GetHandleOutput(), destination)
            dc.EndPage()
            page_started = False
            submitted_pages += 1
        dc.EndDoc()
        document_started = False
        return {
            "method": "gdi_a4_fit",
            "application": "Windows GDI",
            "spooler_verified": True,
            "spooler_status": "submitted",
            "spooler_job_ids": [job_id] if job_id > 0 else [],
            "page_count": document.page_count,
            "paper": "A4",
            "copies": 1,
            "scale": "fit",
        }
    except Exception as exc:
        may_have_printed = bool(document_started or page_started or submitted_pages)
        if dc is not None and document_started:
            try:
                dc.AbortDoc()
            except Exception:
                pass
        message = str(exc) or exc.__class__.__name__
        raise _PdfPrintSubmissionError(message, may_have_printed=may_have_printed) from exc
    finally:
        if document is not None:
            try:
                document.close()
            except Exception:
                pass
        if dc is not None:
            try:
                dc.DeleteDC()
            except Exception:
                pass



def _browser_pdf_print_app_candidates() -> list[Path]:
    roots = [
        os.getenv("ProgramFiles"),
        os.getenv("ProgramFiles(x86)"),
        os.getenv("LOCALAPPDATA"),
    ]
    rels = [
        r"Microsoft\Edge\Application\msedge.exe",
        r"Google\Chrome\Application\chrome.exe",
    ]
    candidates: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not root:
            continue
        for rel in rels:
            path = Path(root) / rel
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            if path.exists() and path.is_file():
                candidates.append(path)
    return candidates


def _print_pdf_with_browser_default(path: Path, printer_name: str) -> dict[str, Any]:
    import win32print

    candidates = _browser_pdf_print_app_candidates()
    if not candidates:
        raise RuntimeError("Edge/Chrome PDF print app not found")
    wait_seconds = float(os.getenv("ERP_AGENT_BROWSER_PRINT_WAIT_SECONDS", "12.0") or "12.0")
    min_visible_seconds = float(os.getenv("ERP_AGENT_PDF_VIEWER_MIN_VISIBLE_SECONDS", "1.5") or "1.5")
    profile_dir = Path(tempfile.gettempdir()) / "AccountingWeb" / "browser_print" / f"{int(time.time() * 1000)}"
    profile_dir.mkdir(parents=True, exist_ok=True)
    original_printer = ""
    try:
        try:
            original_printer = str(win32print.GetDefaultPrinter() or "")
        except Exception:
            original_printer = ""
        win32print.SetDefaultPrinter(printer_name)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        errors: list[str] = []
        for exe in candidates:
            try:
                spooler_available, before_job_ids, spooler_error = _printer_spooler_snapshot(printer_name)
                started_at = time.monotonic()
                proc = subprocess.Popen(
                    [
                        str(exe),
                        "--kiosk-printing",
                        "--no-first-run",
                        "--disable-extensions",
                        f"--user-data-dir={profile_dir}",
                        path.as_uri(),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                    creationflags=creationflags,
                )
                if not spooler_available:
                    time.sleep(min(max(wait_seconds, 2.0), 4.0))
                    code = proc.poll()
                    if code not in (None, 0):
                        raise RuntimeError(f"{exe.name}: exit {code}")
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    return {
                        "method": "browser",
                        "application": str(exe),
                        "spooler_verified": False,
                        "spooler_status": f"unavailable: {spooler_error}",
                        "spooler_job_ids": [],
                    }
                confirmed, job_ids, wait_error = _wait_for_new_printer_job(
                    printer_name,
                    before_job_ids,
                    timeout_seconds=wait_seconds,
                )
                if confirmed:
                    remaining_visible = min_visible_seconds - (time.monotonic() - started_at)
                    if remaining_visible > 0:
                        time.sleep(remaining_visible)
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    return {
                        "method": "browser",
                        "application": str(exe),
                        "spooler_verified": True,
                        "spooler_status": "confirmed",
                        "spooler_job_ids": job_ids,
                    }
                if wait_error:
                    errors.append(f"{exe.name}: spooler query failed: {wait_error}")
                else:
                    errors.append(f"{exe.name}: Windows print spooler did not receive a new job")
                try:
                    proc.terminate()
                except Exception:
                    pass
            except Exception as exc:
                errors.append(f"{exe.name}: {exc}")
        raise RuntimeError("; ".join(errors) if errors else "Browser PDF print failed")
    finally:
        if original_printer:
            try:
                win32print.SetDefaultPrinter(original_printer)
            except Exception:
                pass
        try:
            shutil.rmtree(profile_dir, ignore_errors=True)
        except Exception:
            pass

def _print_pdf_to_printer_legacy(path: Path, printer_name: str) -> dict[str, Any]:
    if not printer_name:
        raise RuntimeError("출력 프린터가 비어 있습니다.")
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"출력할 PDF가 없습니다: {path}")
    import win32print

    try:
        result = _print_pdf_with_browser_default(path, printer_name)
        log(
            "PDF browser print "
            f"{('spooler confirmed' if result.get('spooler_verified') else 'requested (spooler unavailable)')}: "
            f"{path.name} -> {printer_name} via {Path(str(result.get('application') or '')).name}"
        )
        return result
    except Exception as exc:
        browser_error = str(exc) or exc.__class__.__name__

    direct_error = ""
    try:
        spooler_available, before_job_ids, spooler_error = _printer_spooler_snapshot(printer_name)
        app_path = _print_pdf_with_direct_app(path, printer_name)
        if not spooler_available:
            return {
                "method": "direct",
                "application": app_path,
                "spooler_verified": False,
                "spooler_status": f"unavailable: {spooler_error}",
                "spooler_job_ids": [],
            }
        confirmed, job_ids, wait_error = _wait_for_new_printer_job(
            printer_name,
            before_job_ids,
            timeout_seconds=float(os.getenv("ERP_AGENT_PDF_SPOOL_VERIFY_SECONDS", "8.0") or "8.0"),
        )
        if confirmed:
            result = {
                "method": "direct",
                "application": app_path,
                "spooler_verified": True,
                "spooler_status": "confirmed",
                "spooler_job_ids": job_ids,
            }
            log(f"PDF direct print spooler confirmed: {path.name} -> {printer_name} via {Path(app_path).name}")
            return result
        direct_error = wait_error or "Windows print spooler did not receive a new job"
    except Exception as exc:
        direct_error = str(exc) or exc.__class__.__name__

    original_printer = ""
    try:
        original_printer = str(win32print.GetDefaultPrinter() or "")
    except Exception:
        original_printer = ""
    first_error = ""
    try:
        spooler_available, before_job_ids, spooler_error = _printer_spooler_snapshot(printer_name)
        win32print.SetDefaultPrinter(printer_name)
        os.startfile(str(path), "print")
        if not spooler_available:
            time.sleep(1.5)
            return {
                "method": "shell_print",
                "application": "default PDF print handler",
                "spooler_verified": False,
                "spooler_status": f"unavailable: {spooler_error}",
                "spooler_job_ids": [],
            }
        confirmed, job_ids, wait_error = _wait_for_new_printer_job(
            printer_name,
            before_job_ids,
            timeout_seconds=float(os.getenv("ERP_AGENT_PDF_SPOOL_VERIFY_SECONDS", "8.0") or "8.0"),
        )
        if confirmed:
            return {
                "method": "shell_print",
                "application": "default PDF print handler",
                "spooler_verified": True,
                "spooler_status": "confirmed",
                "spooler_job_ids": job_ids,
            }
        first_error = wait_error or "Windows print spooler did not receive a new job"
    except Exception as exc:
        first_error = str(exc) or exc.__class__.__name__
    finally:
        if original_printer:
            try:
                win32print.SetDefaultPrinter(original_printer)
            except Exception:
                pass

    try:
        import win32api

        spooler_available, before_job_ids, spooler_error = _printer_spooler_snapshot(printer_name)
        win32api.ShellExecute(0, "printto", str(path), f'"{printer_name}"', str(path.parent), 0)
        if not spooler_available:
            time.sleep(1.5)
            return {
                "method": "shell_printto",
                "application": "PDF printto handler",
                "spooler_verified": False,
                "spooler_status": f"unavailable: {spooler_error}",
                "spooler_job_ids": [],
            }
        confirmed, job_ids, wait_error = _wait_for_new_printer_job(
            printer_name,
            before_job_ids,
            timeout_seconds=float(os.getenv("ERP_AGENT_PDF_SPOOL_VERIFY_SECONDS", "8.0") or "8.0"),
        )
        if confirmed:
            return {
                "method": "shell_printto",
                "application": "PDF printto handler",
                "spooler_verified": True,
                "spooler_status": "confirmed",
                "spooler_job_ids": job_ids,
            }
        second_error = wait_error or "Windows print spooler did not receive a new job"
    except Exception as exc:
        second_error = str(exc) or exc.__class__.__name__
    raise RuntimeError(
        f"PDF 출력 실패: {path.name} / browser={browser_error} / direct={direct_error} / "
        f"print={first_error} / printto={second_error}"
    )


def _print_pdf_to_printer(path: Path, printer_name: str) -> dict[str, Any]:
    if not printer_name:
        raise RuntimeError("출력 프린터가 비어 있습니다.")
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"출력할 PDF가 없습니다: {path}")
    try:
        result = _print_pdf_with_gdi_fit(path, printer_name)
        log(f"PDF A4 fit print submitted: {path.name} -> {printer_name}")
        return result
    except _PdfPrintSubmissionError as exc:
        if exc.may_have_printed:
            raise RuntimeError(
                "PDF 출력 중 오류가 발생했습니다. 중복 출력을 막기 위해 재전송하지 않습니다: "
                f"{path.name} / {exc}"
            ) from exc
        raise RuntimeError(f"PDF A4 맞춤 출력 시작 실패: {path.name} / {exc}") from exc


def run_output_print_task(
    server: str,
    task: dict[str, Any],
    agent_id: str,
    verify: bool,
    tray: AgentTray | None = None,
) -> None:
    job_id = str(task.get("job_id") or "")
    printer_name = str(task.get("printer_name") or "").strip()
    all_print_files = [item for item in task.get("print_files") or [] if isinstance(item, dict)]
    completed_file_keys = {
        str(value).strip()
        for value in (task.get("completed_file_keys") or [])
        if str(value).strip()
    }
    print_files = [
        item
        for item in all_print_files
        if _output_print_file_key(int(item.get("invoice_id") or 0), int(item.get("file_index") or 0)) not in completed_file_keys
    ]
    invoice_ids: list[int] = []
    successes_by_invoice: dict[int, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for item in all_print_files:
        invoice_id = int(item.get("invoice_id") or 0)
        if invoice_id and invoice_id not in invoice_ids:
            invoice_ids.append(invoice_id)
    log(
        f"output print task claimed: job={job_id}, files={len(print_files)}/{len(all_print_files)}, "
        f"already_confirmed={len(completed_file_keys)}, printer={printer_name}"
    )
    try:
        if not printer_name:
            raise RuntimeError("출력 프린터가 지정되지 않았습니다.")
        if not all_print_files:
            raise RuntimeError("출력할 문서 세트 PDF가 없습니다.")
        if not print_files:
            message = f"담당자 PC 출력 완료: {len(completed_file_keys)}/{len(all_print_files)}개 파일 (기확인 출력)"
            _post(
                server,
                f"/api/agent/jobs/{job_id}/complete",
                {
                    "ok": True,
                    "job_type": "output_print",
                    "agent_id": agent_id,
                    "invoice_ids": invoice_ids,
                    "successes": [],
                    "failures": [],
                    "completed_at": now_text(),
                    "message": message,
                },
                verify=verify,
                timeout=20,
            )
            if tray:
                tray.notify("회계업무 WEB 출력 완료", message)
            return
        total = len(print_files)
        for index, item in enumerate(print_files, start=1):
            invoice_id = int(item.get("invoice_id") or 0)
            file_index = int(item.get("file_index") or index)
            filename = str(item.get("filename") or f"{invoice_id}_{file_index}.pdf")
            if invoice_id and invoice_id not in invoice_ids:
                invoice_ids.append(invoice_id)
            progress_value = 92 + int(index / max(total, 1) * 6)
            _post(
                server,
                f"/api/agent/jobs/{job_id}/event",
                {
                    "agent_id": agent_id,
                    "status": "printing",
                    "progress": min(98, progress_value),
                    "message": f"담당자 PC PDF 열기/출력 시작: #{invoice_id} / {filename}",
                    "invoice_ids": [invoice_id] if invoice_id else [],
                },
                verify=verify,
                timeout=10,
            )
            try:
                local_pdf = _download_output_print_file(server, job_id, invoice_id, file_index, filename, verify)
                print_result = _print_pdf_to_printer(local_pdf, printer_name)
                row = successes_by_invoice.setdefault(
                    invoice_id,
                    {"invoice_id": invoice_id, "printed_files": [], "printed_file_keys": [], "print_results": [], "printer_name": printer_name},
                )
                row["printed_files"].append(str(local_pdf))
                row["printed_file_keys"].append(_output_print_file_key(invoice_id, file_index))
                row["print_results"].append(print_result)
                spooler_job_ids = ", ".join(str(value) for value in print_result.get("spooler_job_ids") or []) or "-"
                if print_result.get("spooler_verified"):
                    message = (
                        f"담당자 PC PDF 열기/인쇄 큐 확인: #{invoice_id} / {filename} / "
                        f"방법={print_result.get('method')} / JobId={spooler_job_ids}"
                    )
                else:
                    message = (
                        f"담당자 PC PDF 출력 요청 완료(스풀러 확인 불가): #{invoice_id} / {filename} / "
                        f"방법={print_result.get('method')} / {print_result.get('spooler_status')}"
                    )
                _post(
                    server,
                    f"/api/agent/jobs/{job_id}/event",
                    {
                        "agent_id": agent_id,
                        "status": "printing",
                        "progress": min(99, progress_value + 1),
                        "message": message,
                        "invoice_ids": [invoice_id] if invoice_id else [],
                        "completed_print_file": {
                            "invoice_id": invoice_id,
                            "file_index": file_index,
                            "filename": filename,
                        },
                    },
                    verify=verify,
                    timeout=10,
                )
            except Exception as exc:
                failures.append(
                    {
                        "invoice_id": invoice_id,
                        "file_index": file_index,
                        "filename": filename,
                        "error": str(exc) or exc.__class__.__name__,
                    }
                )
                _post(
                    server,
                    f"/api/agent/jobs/{job_id}/event",
                    {
                        "agent_id": agent_id,
                        "status": "error",
                        "progress": min(98, progress_value),
                        "message": f"담당자 PC 출력 실패 후 다음 문서 계속 진행: #{invoice_id} / {filename}",
                        "invoice_ids": [invoice_id] if invoice_id else [],
                    },
                    verify=verify,
                    timeout=10,
                )
                continue
        ok = not failures
        printed_count = sum(len(row.get("printed_files") or []) for row in successes_by_invoice.values())
        completed_count = len(completed_file_keys) + printed_count
        spooler_verified_count = sum(
            1
            for row in successes_by_invoice.values()
            for item in row.get("print_results") or []
            if isinstance(item, dict) and item.get("spooler_verified")
        )
        spooler_unverified_count = printed_count - spooler_verified_count
        message = (
            f"담당자 PC 출력 완료: {completed_count}/{len(all_print_files)}개 파일 / {printer_name} / "
            f"Windows 인쇄 큐 확인 {spooler_verified_count}개"
            + (f" / 확인 불가 {spooler_unverified_count}개" if spooler_unverified_count else "")
            if ok
            else f"담당자 PC 출력 일부 실패: 성공 {printed_count}개, 실패 {len(failures)}개 / 첫 실패: {failures[0].get('filename')} / {failures[0].get('error')}"
        )
        _post(
            server,
            f"/api/agent/jobs/{job_id}/complete",
            {
                "ok": ok,
                "job_type": "output_print",
                "agent_id": agent_id,
                "invoice_ids": invoice_ids,
                "successes": list(successes_by_invoice.values()),
                "failures": failures,
                "completed_at": now_text(),
                "message": message,
            },
            verify=verify,
            timeout=20,
        )
        if tray:
            tray.notify("회계업무 WEB 출력 완료" if ok else "회계업무 WEB 출력 재시도", message)
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        log(f"output print task failed: {message}")
        try:
            _post(
                server,
                f"/api/agent/jobs/{job_id}/complete",
                {
                    "ok": False,
                    "job_type": "output_print",
                    "agent_id": agent_id,
                    "invoice_ids": invoice_ids,
                    "successes": list(successes_by_invoice.values()),
                    "failures": failures or [{"error": message}],
                    "completed_at": now_text(),
                    "message": message,
                },
                verify=verify,
                timeout=20,
            )
            if tray:
                tray.notify("회계업무 WEB 출력 실패", message)
        except Exception as report_exc:
            log(f"output print failure report failed: {report_exc}")


def _package_check() -> list[dict[str, Any]]:
    rows = []
    for name in REQUIRED_PACKAGES:
        try:
            __import__(name)
            rows.append({"name": name, "ok": True, "message": "installed"})
        except Exception as exc:
            rows.append({"name": name, "ok": False, "message": str(exc)})
    return rows


def _repair_missing_packages() -> dict[str, Any]:
    """Install missing runtime packages into the exact Python used by the Agent."""
    missing = [item["name"] for item in _package_check() if not item["ok"]]
    if not missing:
        return {"attempted": False, "ok": True, "missing": []}

    install_names = sorted({PACKAGE_INSTALL_NAMES.get(name, name) for name in missing})
    python_exe = Path(sys.executable)
    if python_exe.name.lower() == "pythonw.exe":
        console_python = python_exe.with_name("python.exe")
        if console_python.exists():
            python_exe = console_python

    command = [
        str(python_exe),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--upgrade",
        *install_names,
    ]
    log(f"repairing missing Python packages: {', '.join(missing)}")
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
        if output:
            log("package repair output: " + output[-1500:])
        importlib.invalidate_caches()
        remaining = [item["name"] for item in _package_check() if not item["ok"]]
        ok = completed.returncode == 0 and not remaining
        log(
            "package repair completed"
            if ok
            else f"package repair failed: remaining={remaining}, rc={completed.returncode}"
        )
        return {
            "attempted": True,
            "ok": ok,
            "missing": missing,
            "remaining": remaining,
            "returncode": completed.returncode,
        }
    except Exception as exc:
        log(f"package repair failed: {exc}")
        return {
            "attempted": True,
            "ok": False,
            "missing": missing,
            "remaining": missing,
            "error": str(exc),
        }


def _config_path() -> Path | None:
    for path in DEFAULT_CONFIGS:
        if path.exists():
            return path
    return None


def _erp_install_check() -> dict[str, Any]:
    config_path = _config_path()
    if not config_path:
        return {"ok": False, "config_path": "", "items": [], "message": "config.ini not found"}
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(config_path, encoding="utf-8")
    items = []
    for section in parser.sections():
        if not section.upper().startswith("INSTALL_"):
            continue
        exe_path = parser.get(section, "exe_path", fallback="").strip()
        items.append(
            {
                "section": section,
                "exe_path": exe_path,
                "ok": bool(exe_path and Path(exe_path).exists()),
            }
        )
    corp_items = []
    for section in parser.sections():
        if not section.upper().startswith("CORP_"):
            continue
        corp_items.append(
            {
                "section": section,
                "user_id_ok": bool(parser.get(section, "user_id", fallback="").strip()),
                "password_ok": bool(parser.get(section, "password", fallback="").strip()),
            }
        )
    ok = bool(items) and all(item["ok"] for item in items) and bool(corp_items) and all(
        item["user_id_ok"] and item["password_ok"] for item in corp_items
    )
    return {"ok": ok, "config_path": str(config_path), "items": items, "corp_items": corp_items}


def _read_agent_config() -> dict[str, Any]:
    try:
        if AGENT_CONFIG_PATH.exists():
            data = json.loads(AGENT_CONFIG_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _write_agent_config(data: dict[str, Any]) -> None:
    AGENT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGENT_CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _apply_server_setup_config(payload: dict[str, Any]) -> None:
    setup = payload.get("setup") if isinstance(payload.get("setup"), dict) else {}
    capabilities = setup.get("capabilities") if isinstance(setup.get("capabilities"), dict) else {}
    mapping = capabilities.get("printer_mapping") if isinstance(capabilities.get("printer_mapping"), dict) else {}
    clean = {key: str(mapping.get(key) or "").strip() for key in PRINTER_KEYS if str(mapping.get(key) or "").strip()}
    if not clean:
        return
    config = _read_agent_config()
    if config.get("printer_mapping") == clean:
        return
    config["printer_mapping"] = clean
    _write_agent_config(config)
    log(f"server printer mapping synced to {AGENT_CONFIG_PATH}")


def _required_erp_company_check() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for company in REQUIRED_ERP_COMPANIES:
        company_dir = ERP_BASE_DIR / company
        updater = company_dir / "Updater" / "ClientUpdater.exe"
        rows[company] = {
            "company_dir": str(company_dir),
            "company_exists": company_dir.exists(),
            "updater_path": str(updater),
            "updater_exists": updater.exists(),
        }
    return {
        "path": str(ERP_BASE_DIR),
        "exists": ERP_BASE_DIR.exists(),
        "companies": rows,
        "ok": ERP_BASE_DIR.exists() and all(item["updater_exists"] for item in rows.values()),
    }


def _expense_template_dest_candidates() -> list[Path]:
    candidates = [EXPENSE_TEMPLATE_DEST, AGENT_APPDATA_ROOT / "양식_현금출금정산서.xlsx"]
    if not os.getenv("EXPENSE_REPORT_TEMPLATE_PATH"):
        bases: list[Path] = []
        for value in (os.getenv("APPDATA"), os.getenv("LOCALAPPDATA")):
            if value:
                bases.append(Path(value))
        user_profile = os.getenv("USERPROFILE")
        if user_profile:
            profile = Path(user_profile)
            bases.extend([profile / "AppData" / "Roaming", profile / "AppData" / "Local", profile / "AppData" / "LocalLow"])
        for base in bases:
            candidates.append(base / "양식_현금출금정산서.xlsx")
            candidates.append(base / "expense_template.xlsx")
            candidates.append(base / "AccountingWeb" / "templates" / "expense_template.xlsx")
            candidates.append(base / "AccountingWeb" / "templates" / "양식_현금출금정산서.xlsx")
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _valid_expense_template(path: Path) -> bool:
    try:
        return path.exists() and path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _ensure_expense_template() -> dict[str, Any]:
    candidates = _expense_template_dest_candidates()
    dest = candidates[0]
    existing = next((path for path in candidates if _valid_expense_template(path)), None)
    if existing:
        return {
            "ok": True,
            "path": str(existing),
            "installed": False,
            "source": "",
            "checked_paths": [str(path) for path in candidates],
            "message": "expense template exists",
        }

    source = next((path for path in EXPENSE_TEMPLATE_SOURCE_CANDIDATES if path.exists() and path.is_file()), None)
    if not source:
        return {
            "ok": False,
            "path": str(dest),
            "installed": False,
            "source": "",
            "checked_paths": [str(path) for path in candidates],
            "message": "expense template source file not found in support folder",
        }

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        return {
            "ok": _valid_expense_template(dest),
            "path": str(dest),
            "installed": True,
            "source": str(source),
            "checked_paths": [str(path) for path in candidates],
            "message": "expense template installed",
        }
    except Exception as exc:
        return {
            "ok": False,
            "path": str(dest),
            "installed": False,
            "source": str(source),
            "checked_paths": [str(path) for path in candidates],
            "message": str(exc),
        }


def _printer_entries() -> list[dict[str, str]]:
    if platform.system().lower() != "windows":
        return []
    try:
        import win32print

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        rows = []
        for item in win32print.EnumPrinters(flags, None, 2):
            if isinstance(item, dict):
                name = str(item.get("pPrinterName") or "")
                port = str(item.get("pPortName") or "")
                driver = str(item.get("pDriverName") or "")
            elif isinstance(item, tuple):
                name = str(item[2] if len(item) > 2 else item[-1])
                port = ""
                driver = ""
            else:
                name = str(item)
                port = ""
                driver = ""
            if name:
                rows.append({"name": name, "port": port, "driver": driver})
        return rows
    except Exception as exc:
        return [{"name": "", "port": "", "driver": "", "error": str(exc)}]


def _default_printer_name() -> str:
    if platform.system().lower() != "windows":
        return ""
    try:
        import win32print

        return str(win32print.GetDefaultPrinter() or "").strip()
    except Exception:
        return ""


def _detect_printer_mapping(printers: list[dict[str, str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}

    def find_by_tokens(tokens: tuple[str, ...]) -> str:
        for printer in printers:
            name = printer.get("name", "")
            haystack = f"{name} {printer.get('port', '')} {printer.get('driver', '')}".lower()
            if any(token.lower() in haystack for token in tokens):
                return name
        return ""

    mapping["pdf"] = find_by_tokens(("microsoft print to pdf", "pdf 저장", "pdf"))
    mapping["pyeongtaek"] = find_by_tokens(("평택", "pyeongtaek", "pyeong", "172.16.10.", "192.168.10."))
    mapping["gimje"] = find_by_tokens(("김제", "gimje", "172.17.30.", "192.168.30."))
    return {key: value for key, value in mapping.items() if value}


def _printer_check() -> dict[str, Any]:
    printers = _printer_entries()
    names = [item["name"] for item in printers if item.get("name")]
    default_printer = _default_printer_name()
    config = _read_agent_config()
    stored = config.get("printer_mapping") if isinstance(config.get("printer_mapping"), dict) else {}
    detected = _detect_printer_mapping(printers)
    mapping = {}
    source = {}
    for key in PRINTER_KEYS:
        value = str(stored.get(key) or "").strip()
        if value:
            mapping[key] = value
            source[key] = "local"
        elif detected.get(key):
            mapping[key] = detected[key]
            source[key] = "auto"
    ok = all(mapping.get(key) and mapping.get(key) in names for key in PRINTER_KEYS)
    return {
        "ok": ok,
        "printers": names,
        "default_printer": default_printer,
        "printer_details": printers,
        "printer_mapping": mapping,
        "printer_mapping_source": source,
        "config_path": str(AGENT_CONFIG_PATH),
    }


def _output_dir_check() -> dict[str, Any]:
    path = ERP_OUTPUT_DIR
    probe = path / ".agent_write_probe"
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe.write_text(now_text(), encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"ok": True, "path": str(path), "write_ok": True}
    except Exception as exc:
        return {"ok": False, "path": str(path), "write_ok": False, "message": str(exc)}


def _cert_cache_path(server_url: str) -> Path:
    digest = hashlib.sha1(server_url.rstrip("/").encode("utf-8", errors="ignore")).hexdigest()[:12]
    return CERT_CACHE_DIR / f"web_v1_{digest}.cert.pem"


def _cert_thumbprint(cert_bytes: bytes) -> str:
    text = cert_bytes.decode("ascii", errors="ignore")
    if "BEGIN CERTIFICATE" in text:
        der = ssl.PEM_cert_to_DER_cert(text)
    else:
        der = cert_bytes
    return hashlib.sha1(der).hexdigest().upper()


def _run_certutil(args: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if platform.system().lower() == "windows" else 0
    return subprocess.run(
        ["certutil", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=creationflags,
    )


def _cert_store_has_thumbprint(thumbprint: str, *, current_user: bool) -> bool:
    if platform.system().lower() != "windows" or not thumbprint:
        return False
    args = ["-store", "Root", thumbprint]
    if current_user:
        args.insert(0, "-user")
    try:
        result = _run_certutil(args, timeout=15)
    except Exception:
        return False
    output = "".join((result.stdout + result.stderr).split()).upper()
    return result.returncode == 0 and thumbprint.upper() in output


def _download_https_certificate(server_url: str, verify: bool = False) -> tuple[Path, str]:
    CERT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cert_path = _cert_cache_path(server_url)
    response = requests.get(f"{server_url.rstrip('/')}/api/setup/certificate", verify=verify, timeout=30)
    response.raise_for_status()
    cert_path.write_bytes(response.content)
    return cert_path, _cert_thumbprint(response.content)


def _https_certificate_check(server_url: str) -> dict[str, Any]:
    server_url = str(server_url or "").strip()
    if not server_url.lower().startswith("https://"):
        return {
            "ok": True,
            "server_url": server_url,
            "thumbprint": "",
            "trusted_current_user": True,
            "trusted_local_machine": False,
            "message": "HTTPS 서버가 아니므로 인증서 신뢰 검사를 건너뜁니다.",
        }
    try:
        cert_path, thumbprint = _download_https_certificate(server_url, verify=False)
    except Exception as exc:
        return {
            "ok": False,
            "server_url": server_url,
            "thumbprint": "",
            "trusted_current_user": False,
            "trusted_local_machine": False,
            "message": f"WEB HTTPS 인증서 다운로드 실패: {exc}",
        }
    trusted_current_user = _cert_store_has_thumbprint(thumbprint, current_user=True)
    trusted_local_machine = _cert_store_has_thumbprint(thumbprint, current_user=False)
    return {
        "ok": bool(trusted_current_user or trusted_local_machine),
        "server_url": server_url,
        "cert_path": str(cert_path),
        "thumbprint": thumbprint,
        "trusted_current_user": trusted_current_user,
        "trusted_local_machine": trusted_local_machine,
        "message": "WEB HTTPS 인증서 신뢰 확인" if trusted_current_user or trusted_local_machine else "WEB HTTPS 인증서 신뢰 등록 필요",
    }


def _install_https_certificate(server_url: str) -> dict[str, Any]:
    if not str(server_url or "").lower().startswith("https://"):
        return {"kind": "https_certificate", "ok": True, "message": "HTTPS 서버가 아니므로 인증서 설치를 건너뜁니다."}
    cert_path, thumbprint = _download_https_certificate(server_url, verify=False)
    current_user_result = _run_certutil(["-user", "-addstore", "Root", str(cert_path)], timeout=30)
    trusted_current_user = _cert_store_has_thumbprint(thumbprint, current_user=True)
    machine_message = ""
    trusted_local_machine = _cert_store_has_thumbprint(thumbprint, current_user=False)
    if not trusted_local_machine:
        try:
            machine_result = _run_certutil(["-addstore", "Root", str(cert_path)], timeout=30)
            machine_message = (machine_result.stdout or machine_result.stderr or "").strip()[-500:]
            trusted_local_machine = _cert_store_has_thumbprint(thumbprint, current_user=False)
        except Exception as exc:
            machine_message = str(exc)
    ok = bool(trusted_current_user or trusted_local_machine)
    return {
        "kind": "https_certificate",
        "ok": ok,
        "cert_path": str(cert_path),
        "thumbprint": thumbprint,
        "trusted_current_user": trusted_current_user,
        "trusted_local_machine": trusted_local_machine,
        "current_user_returncode": current_user_result.returncode,
        "current_user_message": (current_user_result.stdout or current_user_result.stderr or "").strip()[-500:],
        "local_machine_message": machine_message,
        "message": "WEB HTTPS 인증서 등록 완료" if ok else "WEB HTTPS 인증서 등록 실패",
    }


def _set_dpi_awareness() -> None:
    _set_process_dpi_awareness_early()


def _display_check() -> dict[str, Any]:
    _set_dpi_awareness()
    if platform.system().lower() != "windows":
        return {"ok": False, "monitors": [], "message": "Windows only"}

    monitors: list[dict[str, Any]] = []
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

    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(RECT),
        wintypes.LPARAM,
    )

    def callback(hmonitor, hdc, lprc, lparam):  # type: ignore[no-untyped-def]
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
        scale_100 = 95 <= scale <= 105
        recommended = width >= 1920 and height >= 1080 and scale_100
        usable = recommended
        monitors.append(
            {
                "device": info.szDevice,
                "left": int(info.rcMonitor.left),
                "top": int(info.rcMonitor.top),
                "right": int(info.rcMonitor.right),
                "bottom": int(info.rcMonitor.bottom),
                "width": width,
                "height": height,
                "scale": scale,
                "primary": bool(info.dwFlags & 1),
                "recommended": recommended,
                "usable": usable,
            }
        )
        return 1

    user32.EnumDisplayMonitors(0, 0, MONITORENUMPROC(callback), 0)
    recommended = [item for item in monitors if item["recommended"]]
    usable = [item for item in monitors if item["usable"]]
    selected = recommended[0] if recommended else None
    return {
        "ok": bool(selected),
        "recommended": bool(recommended),
        "selected": selected,
        "monitors": monitors,
        "message": "1920x1080 100% display found" if recommended else "no 1920x1080 100% ERP display",
    }


def preflight(server_url: str = "") -> dict[str, Any]:
    packages = _package_check()
    erp = _erp_install_check()
    display = _display_check()
    required_erp = _required_erp_company_check()
    printers = _printer_check()
    output_dir = _output_dir_check()
    https_certificate = _https_certificate_check(server_url)
    expense_template = _ensure_expense_template()
    setup = {
        "ready": bool(
            required_erp["ok"]
            and erp["ok"]
            and printers["ok"]
            and output_dir["ok"]
            and display.get("ok")
            and https_certificate["ok"]
            and expense_template["ok"]
        ),
        "erp_base": {"path": required_erp["path"], "exists": required_erp["exists"]},
        "companies": required_erp["companies"],
        "config": erp,
        "printers": printers["printers"],
        "default_printer": printers.get("default_printer") or "",
        "printer_details": printers["printer_details"],
        "printer_mapping": printers["printer_mapping"],
        "printer_mapping_source": printers["printer_mapping_source"],
        "output_dir": output_dir,
        "display": display,
        "https_certificate": https_certificate,
        "expense_template": expense_template,
        "output_print": True,
    }
    ok = all(item["ok"] for item in packages) and bool(setup["ready"])
    return {
        "ok": ok,
        "agent_host": socket.gethostname(),
        "agent_user": os.getenv("USERNAME") or os.getenv("USER") or "",
        "agent_bundle_version": AGENT_BUNDLE_VERSION,
        "agent_bundle_hash": _agent_bundle_hash(),
        "python": sys.version.split()[0],
        "packages": packages,
        "erp": erp,
        "display": display,
        "setup": setup,
        "output_print": True,
    }


def run_install_job(server: str, job: dict[str, Any], agent_id: str, verify: bool) -> None:
    job_id = str(job.get("id") or "")
    companies = [str(item) for item in job.get("companies") or [] if str(item).strip()]
    results: list[dict[str, Any]] = []
    ok = True
    INSTALL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ERP_BASE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"setup install job claimed: {job_id}, companies={companies}")
    try:
        for company in companies:
            if company == CERT_INSTALL_TOKEN:
                log("WEB HTTPS certificate trust install started")
                result = _install_https_certificate(server)
                results.append(result)
                ok = ok and bool(result.get("ok"))
                continue
            url = f"{server.rstrip('/')}/api/setup/installers/{quote(company)}"
            target = INSTALL_CACHE_DIR / f"{company}.zip"
            response = requests.get(url, verify=verify, timeout=120)
            response.raise_for_status()
            target.write_bytes(response.content)
            company_dir = ERP_BASE_DIR / company
            company_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(target) as archive:
                archive.extractall(company_dir)
            updater = company_dir / "Updater" / "ClientUpdater.exe"
            started = False
            if updater.exists():
                try:
                    subprocess.Popen([str(updater)], cwd=str(updater.parent), close_fds=True)
                    started = True
                except Exception as exc:
                    results.append({"company": company, "ok": False, "message": f"ClientUpdater 실행 실패: {exc}", "updater": str(updater)})
                    ok = False
                    continue
            results.append({"company": company, "ok": updater.exists(), "updater": str(updater), "started": started})
            ok = ok and updater.exists()
    except Exception as exc:
        ok = False
        results.append({"ok": False, "message": str(exc)})
    try:
        _post(
            server,
            f"/api/agent/setup/install/{job_id}/complete",
            {"ok": ok, "agent_id": agent_id, "companies": companies, "results": results, "completed_at": now_text()},
            verify=verify,
            timeout=20,
        )
    except Exception as exc:
        log(f"setup install report failed: {exc}")


def _cleanup_erp_processes_after_task(reason: str = "") -> None:
    if os.name != "nt":
        return
    try:
        import psutil
    except Exception as exc:
        log(f"ERP process cleanup skipped: psutil unavailable: {exc}")
        return
    current_pid = os.getpid()
    matches: list[Any] = []
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            if proc.pid == current_pid:
                continue
            name = str(proc.info.get("name") or "").lower()
            exe = str(proc.info.get("exe") or "").lower()
            cmdline = " ".join(str(item) for item in (proc.info.get("cmdline") or [])).lower()
            blob = f"{name} {exe} {cmdline}"
            if (
                "younglimwon" in blob
                or "ksystem ver.5 genuine" in blob
                or name in {"clientupdater.exe", "rdviewer_u.exe"}
                or "angkor" in name
            ):
                matches.append(proc)
        except Exception:
            continue
    if not matches:
        log("ERP process cleanup: no ERP processes left")
        return
    log(f"ERP process cleanup after task ({reason or 'task'}): {len(matches)} process(es)")
    survivors: list[Any] = []
    for proc in matches:
        try:
            log(f"terminating ERP process pid={proc.pid} name={proc.name()}")
            proc.terminate()
            survivors.append(proc)
        except Exception as exc:
            log(f"ERP process terminate failed pid={getattr(proc, 'pid', '?')}: {exc}")
    try:
        gone, alive = psutil.wait_procs(survivors, timeout=6)
    except Exception:
        alive = survivors
    for proc in alive:
        try:
            log(f"killing ERP process pid={proc.pid} name={proc.name()}")
            proc.kill()
        except Exception as exc:
            log(f"ERP process kill failed pid={getattr(proc, 'pid', '?')}: {exc}")

def run_task(server: str, task: dict[str, Any], agent_id: str, verify: bool) -> None:
    os.environ.setdefault("LEGACY_MANAGER_PATH", str(LEGACY_MANAGER))
    os.environ.setdefault("ERP_EXECUTION_MODE", "agent")
    os.environ.setdefault("ERP_AGENT_FRESH_START", "1")
    source_context = task.get("source_job_payload") if isinstance(task.get("source_job_payload"), dict) else {}
    is_regular_auto_task = bool(task.get("regular_auto") or source_context.get("regular_auto"))
    runtime_profile_name, runtime_defaults = _erp_task_runtime_profile(task)
    previous_speed_env: dict[str, str | None] = {}
    if runtime_defaults:
        previous_speed_env = _apply_erp_runtime_profile(runtime_defaults)
        log(f"ERP runtime profile applied: {runtime_profile_name}")
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from web_v1.backend.erp_runner import run_invoice_erp_input

    job_id = str(task.get("job_id") or "")
    invoices = list(task.get("invoices") or [])
    invoice_ids = [int(item.get("id")) for item in invoices if str(item.get("id")).isdigit()]
    progress_dispatcher = _ProgressEventDispatcher(server, job_id, agent_id, verify)
    log(f"ERP task claimed: job={job_id}, invoices={invoice_ids}")
    progress_dispatcher.submit(
        {
            "status": "erp",
            "progress": 82,
            "message": "담당자 PC Agent ERP 입력 시작",
            "invoice_ids": invoice_ids,
        }
    )
    successes = []
    try:
        display = _display_check()
        if not display.get("ok"):
            monitors = display.get("monitors") or []
            summary = "; ".join(
                f"{m.get('device','?')} {m.get('width')}x{m.get('height')} scale={m.get('scale')}"
                for m in monitors
            ) or "none"
            raise RuntimeError("ERP automation requires a 1920x1080 display at 100% scale. detected=" + summary)
        log(f"ERP display target verified: {display.get('selected')}")

        for index, invoice in enumerate(invoices, start=1):
            invoice_id = int(invoice.get("id") or 0)
            base_progress = 82 + int(index / max(len(invoices), 1) * 12)
            last_progress_post_at = 0.0

            def should_post_progress(message: str) -> bool:
                nonlocal last_progress_post_at
                if os.getenv("ERP_AGENT_PROGRESS_VERBOSE", "").strip() == "1":
                    last_progress_post_at = time.monotonic()
                    return True
                text = str(message or "")
                important_tokens = (
                    "실패",
                    "완료",
                    "시작",
                    "진입 확인",
                    "저장",
                    "출력",
                    "K-System",
                    "ERP 분개",
                    "task",
                )
                noisy_tokens = (
                    "[KEYSAFE]",
                    "[FORM-XY]",
                    "[FORM-FAST]",
                    "[FORM-VERIFY]",
                    "[FORM-STEP]",
                    "[FORM-GRID]",
                    "[MGMT-XY]",
                    "[MENU-",
                    "[TREE-",
                    "[SAVE]",
                    "[PRINT]",
                    "[DEBUG]",
                )
                if any(token in text for token in important_tokens) and not any(token in text for token in noisy_tokens):
                    last_progress_post_at = time.monotonic()
                    return True
                throttle = float(os.getenv("ERP_AGENT_PROGRESS_THROTTLE_SEC", "2.0") or "2.0")
                now = time.monotonic()
                if now - last_progress_post_at >= max(0.5, throttle):
                    last_progress_post_at = now
                    return True
                return False

            def progress(message: str, progress_value: int = base_progress) -> None:
                log(message)
                if not should_post_progress(message):
                    return
                progress_dispatcher.submit(
                    {
                        "status": "erp",
                        "progress": min(96, progress_value),
                        "message": message,
                        "invoice_ids": [invoice_id],
                    }
                )

            result = run_invoice_erp_input(invoice, job_id=job_id, progress=progress)
            local_erp_pdf_path = str(result.get("erp_pdf_path") or "")
            result["erp_pdf_local_path"] = local_erp_pdf_path
            upload = _upload_erp_voucher(server, job_id, invoice_id, local_erp_pdf_path, agent_id, verify)
            result["erp_pdf_upload"] = upload
            if upload.get("ok") and upload.get("server_path"):
                result["erp_pdf_uploaded"] = True
                result["erp_pdf_server_path"] = str(upload.get("server_path") or "")
                result["erp_pdf_path"] = str(upload.get("server_path") or "")
                progress(f"ERP 전표 PDF 서버 업로드 완료: #{invoice_id}", min(96, base_progress + 1))
            else:
                result["erp_pdf_uploaded"] = False
                result["erp_pdf_upload_error"] = str(upload.get("error") or "unknown upload error")
                progress(f"ERP 전표 PDF 서버 업로드 실패: {result['erp_pdf_upload_error']}", min(96, base_progress + 1))
            successes.append(result)
        progress_dispatcher.close()
        _post(
            server,
            f"/api/agent/jobs/{job_id}/complete",
            {
                "ok": True,
                "agent_id": agent_id,
                "invoice_ids": invoice_ids,
                "successes": successes,
                "completed_at": now_text(),
                "message": f"담당자 PC ERP 입력 완료: {len(successes)}건",
            },
            verify=verify,
        )
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        log(f"ERP task failed: {message}")
        progress_dispatcher.close()
        try:
            _post(
                server,
                f"/api/agent/jobs/{job_id}/complete",
                {
                    "ok": False,
                    "agent_id": agent_id,
                    "invoice_ids": invoice_ids,
                    "successes": successes,
                    "completed_at": now_text(),
                    "message": message,
                },
                verify=verify,
            )
        except Exception as report_exc:
            log(f"ERP failure report failed: {report_exc}")
    finally:
        progress_dispatcher.close()
        close_after_task = is_regular_auto_task or os.getenv("ERP_AGENT_CLOSE_ERP_AFTER_TASK", "0").strip().lower() in {"1", "true", "yes", "y"}
        if close_after_task:
            _cleanup_erp_processes_after_task("regular_auto" if is_regular_auto_task else "env")
        if runtime_defaults:
            _restore_erp_runtime_profile(previous_speed_env)


def run_expense_report_task(server: str, task: dict[str, Any], agent_id: str, verify: bool) -> None:
    os.environ.setdefault("ERP_EXECUTION_MODE", "agent")
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from web_v1.backend.output_set import generate_expense_report_pdf

    job_id = str(task.get("job_id") or "")
    invoice = dict(task.get("invoice") or {})
    invoice_id = int(task.get("invoice_id") or invoice.get("id") or 0)
    invoice["id"] = invoice_id
    log(f"expense report task claimed: job={job_id}, invoice={invoice_id}")
    try:
        _post(
            server,
            f"/api/agent/jobs/{job_id}/event",
            {
                "agent_id": agent_id,
                "status": "erp",
                "progress": 82,
                "message": "담당자 PC Excel로 현금출금결의서 생성 시작",
                "invoice_ids": [invoice_id],
            },
            verify=verify,
            timeout=10,
        )
        local_pdf_path = generate_expense_report_pdf(invoice, force=True)
        upload = _upload_expense_report(server, job_id, invoice_id, local_pdf_path, agent_id, verify)
        if not upload.get("ok"):
            raise RuntimeError(str(upload.get("error") or "expense report upload failed"))
        _post(
            server,
            f"/api/agent/jobs/{job_id}/complete",
            {
                "ok": True,
                "agent_id": agent_id,
                "invoice_ids": [invoice_id],
                "successes": [
                    {
                        "invoice_id": invoice_id,
                        "expense_report_pdf_path": str(upload.get("server_path") or ""),
                        "expense_report_local_path": str(upload.get("local_path") or local_pdf_path),
                        "expense_report_uploaded": True,
                    }
                ],
                "completed_at": now_text(),
                "message": f"담당자 PC 현금출금결의서 생성 완료: #{invoice_id}",
            },
            verify=verify,
            timeout=20,
        )
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        log(f"expense report task failed: {message}")
        try:
            _post(
                server,
                f"/api/agent/jobs/{job_id}/complete",
                {
                    "ok": False,
                    "agent_id": agent_id,
                    "invoice_ids": [invoice_id] if invoice_id else [],
                    "completed_at": now_text(),
                    "message": message,
                },
                verify=verify,
                timeout=20,
            )
        except Exception as report_exc:
            log(f"expense report failure report failed: {report_exc}")


def _server_version_payload(server: str, verify: bool) -> dict[str, Any]:
    response = requests.get(f"{server.rstrip('/')}/api/version", verify=verify, timeout=10)
    response.raise_for_status()
    return response.json() if response.content else {}


def _format_update_notes(payload: dict[str, Any]) -> str:
    version = str(payload.get("version") or "").strip()
    notes = str(payload.get("agent_update_notes") or "").strip()
    lines: list[str] = []
    if version:
        lines.append(f"서버 버전: {version}")
    if notes:
        lines.append(notes)
    return "\n".join(lines) or "담당자 PC 필수 프로그램 최신 패치가 있습니다."


def _agent_update_required(server: str, capabilities: dict[str, Any], verify: bool) -> dict[str, Any] | None:
    try:
        payload = _server_version_payload(server, verify)
    except Exception as exc:
        log(f"version check failed: {exc}")
        return None
    expected_hash = str(payload.get("agent_bundle_hash") or "")
    current_hash = str(capabilities.get("agent_bundle_hash") or "")
    if not expected_hash or not current_hash or current_hash.startswith("error:"):
        return None
    if expected_hash == current_hash:
        return None
    log(f"agent update required: current={current_hash[:12]} expected={expected_hash[:12]}")
    return payload


def _run_self_update(server: str, verify: bool) -> bool:
    try:
        temp_root = Path(tempfile.mkdtemp(prefix="accounting_web_agent_update_"))
        payload_zip = temp_root / "payload.zip"
        log(f"downloading agent update payload: {server}")
        response = requests.get(f"{server.rstrip('/')}/api/setup/user-pc-payload.zip", verify=verify, timeout=120)
        response.raise_for_status()
        payload_zip.write_bytes(response.content)
        with zipfile.ZipFile(payload_zip) as archive:
            archive.extractall(temp_root)
        setup_script = temp_root / "setup.ps1"
        if not setup_script.exists():
            setup_script = temp_root / "1_필수프로그램_설치_실행.ps1"
        if not setup_script.exists():
            raise RuntimeError(f"setup script not found in payload: {temp_root}")
        powershell = str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")
        subprocess.Popen([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(setup_script)], cwd=str(temp_root), close_fds=True, creationflags=(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)))
        log("agent self-update started; current process will exit")
        return True
    except Exception as exc:
        log(f"agent self-update failed: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Accounting WEB v1.0 local ERP Agent")
    parser.add_argument("--server", default=os.getenv("WEB_SERVER_URL", "https://172.17.39.121:8080"))
    parser.add_argument("--agent-id", default=os.getenv("ERP_AGENT_ID", f"{socket.gethostname()}-{os.getenv('USERNAME', 'user')}"))
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--update-interval", type=float, default=60.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--no-tray", action="store_true")
    parser.add_argument("--insecure", action="store_true", help="Skip HTTPS certificate verification for internal self-signed WEB server")
    args = parser.parse_args()

    verify = not args.insecure
    if not args.once and not args.preflight_only and not _acquire_single_instance(args.agent_id, args.server):
        log("another ERP Agent instance is already running; exiting")
        return 0
    _repair_missing_packages()
    tray = AgentTray(args.server)
    if not args.once and not args.preflight_only and not args.no_tray:
        tray.start()
    log(f"ERP Agent started: {args.agent_id} -> {args.server}")
    if args.preflight_only:
        capabilities = preflight(args.server)
        print(json.dumps(capabilities, ensure_ascii=False, indent=2))
        return 0 if capabilities["ok"] else 2
    next_update_check_at = 0.0
    last_notified_update_hash = ""
    while True:
        capabilities = preflight(args.server)
        tray.update("Checking")
        heartbeat_payload: dict[str, Any] = {}
        try:
            heartbeat = _post(args.server, "/api/agent/heartbeat", {"agent_id": args.agent_id, "capabilities": capabilities}, verify=verify, timeout=10)
            heartbeat.raise_for_status()
            heartbeat_payload = heartbeat.json() if heartbeat.content else {}
            _apply_server_setup_config(heartbeat_payload)
            tray.update("Connected")
        except Exception as exc:
            log(f"heartbeat failed: {exc}")
            tray.update("Disconnected")
        manual_update_requested = tray.consume_manual_update_request()
        update_check_due = time.monotonic() >= next_update_check_at
        if not args.once and (manual_update_requested or update_check_due):
            next_update_check_at = time.monotonic() + max(15.0, args.update_interval)
            update_payload = _agent_update_required(args.server, capabilities, verify)
            if update_payload:
                expected_hash = str(update_payload.get("agent_bundle_hash") or "")
                update_notes = _format_update_notes(update_payload)
                tray.set_update_message(update_notes)
                if manual_update_requested or expected_hash != last_notified_update_hash:
                    tray.notify("회계업무 WEB 업데이트", update_notes)
                    last_notified_update_hash = expected_hash
                tray.update("Updating")
                if _run_self_update(args.server, verify):
                    return 10
            elif manual_update_requested:
                tray.notify("회계업무 WEB", f"현재 최신버전입니다.\nAgent 버전: {AGENT_BUNDLE_VERSION}")
        install_job = heartbeat_payload.get("install_job") if isinstance(heartbeat_payload.get("install_job"), dict) else None
        if install_job:
            tray.update("Installing")
            run_install_job(args.server, install_job, args.agent_id, verify)
        elif not capabilities["ok"]:
            log("preflight failed; ERP task claim paused")
            log(json.dumps(capabilities, ensure_ascii=False))
            tray.update("Setup required")
        else:
            try:
                response = _post(args.server, "/api/agent/erp/next", {"agent_id": args.agent_id, "capabilities": capabilities}, verify=verify, timeout=20)
                if response.status_code == 404:
                    log("server is not updated: /api/agent/erp/next returned 404. Apply Fix26 ZIP to the WEB server and restart it.")
                    return 3
                if response.status_code == 204:
                    log("no ERP task")
                else:
                    response.raise_for_status()
                    task = response.json()
                    job_type = str(task.get("job_type") or "")
                    if job_type == "expense_report":
                        tray.update("Expense report")
                        run_expense_report_task(args.server, task, args.agent_id, verify)
                    elif job_type == "output_print":
                        tray.update("Printing")
                        run_output_print_task(args.server, task, args.agent_id, verify, tray)
                    else:
                        tray.update("ERP task")
                        run_task(args.server, task, args.agent_id, verify)
            except Exception as exc:
                log(f"agent loop error: {exc}")
                tray.update("Error")
        if args.once:
            return 0
        if tray.stop_requested:
            log("tray exit requested")
            return 0
        time.sleep(max(1.0, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
