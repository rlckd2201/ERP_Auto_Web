from __future__ import annotations

import argparse
import configparser
import ctypes
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import ssl
import time
import zipfile
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

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
REQUIRED_PACKAGES = ["pyautogui", "pyperclip", "pywinauto", "psutil", "win32gui", "win32con", "win32print"]
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
HASH_DIRS = ("web_v1/agent", "web_v1/backend", "web_v1/deploy")
HASH_FILES = ("web_v1/VERSION",)
AGENT_BUNDLE_VERSION = "1.0.89"


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[{now_text()}] {message}", flush=True)


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


def _package_check() -> list[dict[str, Any]]:
    rows = []
    for name in REQUIRED_PACKAGES:
        try:
            __import__(name)
            rows.append({"name": name, "ok": True, "message": "installed"})
        except Exception as exc:
            rows.append({"name": name, "ok": False, "message": str(exc)})
    return rows


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
    if platform.system().lower() != "windows":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


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
        usable = width >= 1920 and height >= 1080 and scale <= 125
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
    selected = recommended[0] if recommended else (usable[0] if usable else None)
    return {
        "ok": bool(selected),
        "recommended": bool(recommended),
        "selected": selected,
        "monitors": monitors,
        "message": "1920x1080 100% display found" if recommended else ("usable display found" if selected else "no usable ERP display"),
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


def run_task(server: str, task: dict[str, Any], agent_id: str, verify: bool) -> None:
    os.environ.setdefault("LEGACY_MANAGER_PATH", str(LEGACY_MANAGER))
    os.environ.setdefault("ERP_EXECUTION_MODE", "agent")
    os.environ.setdefault("ERP_AGENT_FRESH_START", "1")
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from web_v1.backend.erp_runner import run_invoice_erp_input

    job_id = str(task.get("job_id") or "")
    invoices = list(task.get("invoices") or [])
    invoice_ids = [int(item.get("id")) for item in invoices if str(item.get("id")).isdigit()]
    log(f"ERP task claimed: job={job_id}, invoices={invoice_ids}")
    _post(server, f"/api/agent/jobs/{job_id}/event", {"agent_id": agent_id, "status": "erp", "progress": 82, "message": "담당자 PC Agent ERP 입력 시작", "invoice_ids": invoice_ids}, verify=verify)
    successes = []
    try:
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
                    "[FORM-GRID]",
                    "[MGMT-XY]",
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
                _post(
                    server,
                    f"/api/agent/jobs/{job_id}/event",
                    {
                        "agent_id": agent_id,
                        "status": "erp",
                        "progress": min(96, progress_value),
                        "message": message,
                        "invoice_ids": [invoice_id],
                    },
                    verify=verify,
                    timeout=10,
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Accounting WEB v1.0 local ERP Agent")
    parser.add_argument("--server", default=os.getenv("WEB_SERVER_URL", "https://172.17.39.121:8080"))
    parser.add_argument("--agent-id", default=os.getenv("ERP_AGENT_ID", f"{socket.gethostname()}-{os.getenv('USERNAME', 'user')}"))
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--insecure", action="store_true", help="Skip HTTPS certificate verification for internal self-signed WEB server")
    args = parser.parse_args()

    verify = not args.insecure
    log(f"ERP Agent started: {args.agent_id} -> {args.server}")
    if args.preflight_only:
        capabilities = preflight(args.server)
        print(json.dumps(capabilities, ensure_ascii=False, indent=2))
        return 0 if capabilities["ok"] else 2
    while True:
        capabilities = preflight(args.server)
        heartbeat_payload: dict[str, Any] = {}
        try:
            heartbeat = _post(args.server, "/api/agent/heartbeat", {"agent_id": args.agent_id, "capabilities": capabilities}, verify=verify, timeout=10)
            heartbeat.raise_for_status()
            heartbeat_payload = heartbeat.json() if heartbeat.content else {}
            _apply_server_setup_config(heartbeat_payload)
        except Exception as exc:
            log(f"heartbeat failed: {exc}")
        install_job = heartbeat_payload.get("install_job") if isinstance(heartbeat_payload.get("install_job"), dict) else None
        if install_job:
            run_install_job(args.server, install_job, args.agent_id, verify)
        elif not capabilities["ok"]:
            log("preflight failed; ERP task claim paused")
            log(json.dumps(capabilities, ensure_ascii=False))
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
                    if str(task.get("job_type") or "") == "expense_report":
                        run_expense_report_task(args.server, task, args.agent_id, verify)
                    else:
                        run_task(args.server, task, args.agent_id, verify)
            except Exception as exc:
                log(f"agent loop error: {exc}")
        if args.once:
            return 0
        time.sleep(max(1.0, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
