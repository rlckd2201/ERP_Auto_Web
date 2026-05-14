from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import shutil
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent_queue import claim_next_erp_task, update_erp_task
from .compuzone_quote import auto_attach_compuzone_quote
from .config import WEB_ROOT, settings
from .invoice_db import DONE, ERROR, PROCESSING, add_invoice_log, delete_invoice, get_invoice, init_db, insert_manual_invoice, learn_dictionary_items, list_invoice_logs, list_invoices, normalize_processor, reset_invoice, set_invoice_status, update_invoice_json, update_invoice_pdf_path
from .job_store import job_store
from .models import InvoiceIdsRequest, JobCreateRequest, JobResponse, OutputSetRequest, PurchaseAnalysisUpdate
from .output_set import build_output_set_status, generate_expense_report_pdf
from .erp_queue import write_expense_report_queue
from .purchase_analysis import (
    _extract_amounts_from_tax,
    _extract_date,
    _extract_order_no_from_quote,
    _extract_order_no_from_tax,
    _extract_pdf_text,
    _normalize_items_for_display,
    analyze_purchase_documents,
    extract_purchase_date_from_path,
    purchase_approval_dir,
    purchase_quote_dir,
    safe_filename,
)
from .setup_state import (
    authenticate_user,
    claim_install_job,
    complete_install_job,
    create_install_job,
    ensure_auto_install_job,
    find_installer,
    init_auth_db,
    init_setup_db,
    record_agent_heartbeat,
    save_printer_mapping,
    setup_status,
    touch_agent_seen,
)
from .versioning import expected_agent_bundle_hash
from .worker import JobWorker

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

app = FastAPI(
    title="Accounting Automation WEB v1.0",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def no_cache_frontend_assets(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/assets/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.exception_handler(Exception)
async def api_unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.exception("Unhandled API error: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다. 관리자에게 화면을 전달하세요."},
    )


worker = JobWorker(job_store)
FRONTEND_DIR = WEB_ROOT / "frontend"
INSTALLER_EXE_PATH = WEB_ROOT / "backend" / "tools" / "AccountingWebRequiredSetup.exe"
INSTALLER_EXE_OVERLAY_BEGIN = b"\r\n--ACCOUNTING-WEB-SERVER-URL-BEGIN--\r\n"
INSTALLER_EXE_OVERLAY_END = b"\r\n--ACCOUNTING-WEB-SERVER-URL-END--\r\n"
_MAIL_COLLECT_INTERVAL_SECONDS = 60
_mail_collect_scheduler_started = False
_mail_collect_scheduler_lock = threading.RLock()
_mail_collect_last_job_id = ""


def _invoice_data(invoice: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(invoice, dict):
        return {}
    data = invoice.get("data")
    merged = dict(invoice)
    if isinstance(data, dict):
        merged.update(data)
    return merged


def _expense_report_exists(invoice: dict[str, Any] | None) -> bool:
    data = _invoice_data(invoice)
    path = str(data.get("expense_report_pdf_path") or "").strip()
    return bool(path and Path(path).exists())


def _queue_expense_report_after_erp(
    invoice_id: int,
    *,
    agent_id: str,
    target_client_ip: str,
    source_job_id: str,
) -> bool:
    invoice = get_invoice(invoice_id)
    if not invoice or str(invoice.get("invoice_type") or "").lower() != "purchase":
        return False
    if _expense_report_exists(invoice):
        build_output_set_status(invoice, persist=True)
        _maybe_queue_one_click_output(source_job_id)
        return False
    if not str(agent_id or "").strip() or not str(target_client_ip or "").strip():
        add_invoice_log(invoice_id, "ERP 완료 후 현금출금결의서 자동 생성 보류: 담당자 PC Agent 식별 정보 없음", level="error", job_id=source_job_id)
        return False

    job = job_store.create(
        JobCreateRequest(
            job_type="expense_report",
            title=f"현금출금결의서 자동 생성 #{invoice_id}",
            payload={
                "invoice_id": invoice_id,
                "source_job_id": source_job_id,
                "auto_after_erp": True,
                "target_agent_id": agent_id,
                "target_client_ip": target_client_ip,
            },
        )
    )
    queue_path = write_expense_report_queue(
        job.id,
        invoice,
        target_agent_id=agent_id,
        target_client_ip=target_client_ip,
    )
    job_store.add_event(job.id, "erp", 72, f"ERP 완료 후 현금출금결의서 자동 생성 요청: #{invoice_id}")
    add_invoice_log(invoice_id, f"ERP 완료 후 현금출금결의서 자동 생성 요청: 담당자 PC Agent ({queue_path})", level="info", job_id=job.id)
    if job_store.get(source_job_id):
        job_store.add_event(source_job_id, "erp", 98, f"현금출금결의서 자동 생성 큐 등록: #{invoice_id}")
    return True


def _job_time(value: Any) -> str:
    return value.isoformat(timespec="seconds") if hasattr(value, "isoformat") else ""


def _mail_collect_job_running(job: Any) -> bool:
    return bool(job and getattr(job, "status", "") not in {"done", "error"})


def _queue_mail_collect_job(*, auto: bool) -> Any:
    global _mail_collect_last_job_id
    with _mail_collect_scheduler_lock:
        current = job_store.get(_mail_collect_last_job_id) if _mail_collect_last_job_id else None
        if _mail_collect_job_running(current):
            return current
        job = job_store.create(
            JobCreateRequest(
                job_type="purchase_mail_collect",
                title="구매 메일 자동 수집" if auto else "구매 메일 수집",
                payload={"auto": auto},
            )
        )
        _mail_collect_last_job_id = job.id
    worker.submit(job)
    return job


def _mail_collect_status() -> dict[str, Any]:
    with _mail_collect_scheduler_lock:
        job_id = _mail_collect_last_job_id
    job = job_store.get(job_id) if job_id else None
    result = job.result if job else {}
    return {
        "enabled": True,
        "interval_seconds": _MAIL_COLLECT_INTERVAL_SECONDS,
        "running": _mail_collect_job_running(job),
        "job_id": job_id,
        "status": getattr(job, "status", "idle") if job else "idle",
        "last_started_at": _job_time(getattr(job, "started_at", None) or getattr(job, "created_at", None)) if job else "",
        "last_finished_at": _job_time(getattr(job, "finished_at", None)) if job else "",
        "saved_count": int(result.get("saved_count") or 0) if isinstance(result, dict) else 0,
        "duplicate_count": int(result.get("duplicate_count") or 0) if isinstance(result, dict) else 0,
        "failed_count": int(result.get("failed_count") or 0) if isinstance(result, dict) else 0,
        "auto_analyzed_count": int(result.get("auto_analyzed_count") or 0) if isinstance(result, dict) else 0,
        "errors": result.get("errors", []) if isinstance(result, dict) and isinstance(result.get("errors"), list) else [],
    }


def _start_mail_collect_scheduler() -> None:
    global _mail_collect_scheduler_started
    with _mail_collect_scheduler_lock:
        if _mail_collect_scheduler_started:
            return
        _mail_collect_scheduler_started = True

    def _loop() -> None:
        while True:
            try:
                _queue_mail_collect_job(auto=True)
            except Exception:
                logging.exception("Automatic purchase mail collection failed to queue")
            time.sleep(_MAIL_COLLECT_INTERVAL_SECONDS)

    threading.Thread(target=_loop, name="purchase-mail-collector", daemon=True).start()


def _one_click_output_payload(output_target: str, setup: dict[str, Any]) -> dict[str, str]:
    target = output_target if output_target in {"pdf", "pyeongtaek", "gimje"} else "pdf"
    if target == "pdf":
        return {"action": "merged_pdf", "printer_key": "pdf", "printer_name": ""}
    mapping = setup.get("capabilities", {}).get("printer_mapping", {})
    printer_name = str(mapping.get(target) or "").strip() if isinstance(mapping, dict) else ""
    if not printer_name:
        label = "평택 프린터" if target == "pyeongtaek" else "김제 프린터"
        raise HTTPException(status_code=400, detail=f"{label} 매핑이 없습니다. 프린터 설정을 먼저 저장해야 합니다.")
    return {"action": "print_individual", "printer_key": target, "printer_name": printer_name}


def _maybe_queue_one_click_output(source_job_id: str) -> None:
    source_job = job_store.get(source_job_id)
    if not source_job or not bool(source_job.payload.get("one_click")):
        return
    if str(source_job.payload.get("one_click_output_job_id") or ""):
        return
    invoice_ids = [int(item) for item in source_job.payload.get("invoice_ids") or [] if str(item).isdigit()]
    if not invoice_ids:
        return
    missing = []
    for invoice_id in invoice_ids:
        if not _expense_report_exists(get_invoice(invoice_id)):
            missing.append(invoice_id)
    if missing:
        if job_store.get(source_job_id):
            job_store.add_event(source_job_id, "printing", 97, f"현금출금결의서 생성 대기: {len(missing)}건")
        return
    job = job_store.create(
        JobCreateRequest(
            job_type="output_set",
            title=f"원클릭 문서 출력 {len(invoice_ids)}건",
            payload={
                "invoice_ids": invoice_ids,
                "action": str(source_job.payload.get("output_action") or "merged_pdf"),
                "printer_key": str(source_job.payload.get("printer_key") or "pdf"),
                "printer_name": str(source_job.payload.get("printer_name") or ""),
                "processor": str(source_job.payload.get("processor") or "WEB v1.0"),
                "source_job_id": source_job_id,
            },
        )
    )
    source_job.payload["one_click_output_job_id"] = job.id
    job_store.add_event(source_job_id, "printing", 98, f"원클릭 출력 작업 등록: {job.id}")
    worker.submit(job)


def _installer_server_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _agent_installer_script(server_url: str) -> str:
    return r'''
$ErrorActionPreference = "Stop"
$ServerUrl = "__SERVER_URL__"
$InstallRoot = Join-Path $env:USERPROFILE "Desktop\개발파일\회계업무 자동화_WEB_Version"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PayloadRoot = Join-Path $PackageRoot "payload"

Write-Host "[회계업무 WEB] 담당자 PC 필수 프로그램 설치를 시작합니다."
Write-Host "[회계업무 WEB] 서버: $ServerUrl"
Write-Host "[회계업무 WEB] 설치 폴더: $InstallRoot"

New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
$CleanTargets = @("web_v1", "manager_server")
foreach ($Relative in $CleanTargets) {
    $Target = Join-Path $InstallRoot $Relative
    if (Test-Path $Target) {
        Write-Host "[Accounting WEB] Removing old runtime folder: $Relative"
        Remove-Item -LiteralPath $Target -Recurse -Force
    }
}
foreach ($Name in @("web_v1", "manager_server", "support")) {
    $Source = Join-Path $PayloadRoot $Name
    $Target = Join-Path $InstallRoot $Name
    if (Test-Path $Source) {
        New-Item -ItemType Directory -Path $Target -Force | Out-Null
        Get-ChildItem -LiteralPath $Source -Force | Copy-Item -Destination $Target -Recurse -Force
    }
}

function Resolve-PythonExe {
    $candidates = @(
        $env:PYTHON_EXE,
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "python",
        "py"
    )
    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        try {
            if ($candidate -like "*\*" -and -not (Test-Path $candidate)) { continue }
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch {}
    }
    return ""
}

$Python = Resolve-PythonExe
if (-not $Python -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "[회계업무 WEB] Python이 없어 자동 설치를 시도합니다."
    winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements
    $Python = Resolve-PythonExe
}
if (-not $Python) {
    throw "Python 3.11 이상을 찾지 못했습니다. Python 설치 후 이 파일을 다시 실행하세요."
}

Write-Host "[회계업무 WEB] Python 패키지를 확인합니다."
$RequirementsPath = Join-Path $InstallRoot "web_v1\backend\requirements.txt"
if (-not (Test-Path $RequirementsPath)) {
    throw "requirements.txt not found after setup copy: $RequirementsPath"
}
& $Python -m pip install -r $RequirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "Python package install failed. ExitCode=$LASTEXITCODE"
}

Write-Host "[회계업무 WEB] WEB HTTPS 인증서를 신뢰 저장소에 등록합니다."
$CertDir = "C:\ERP_DB\certs"
$CertPath = Join-Path $CertDir "web_v1.cert.pem"
$LocalCertPath = Join-Path $PackageRoot "web_v1.cert.pem"
New-Item -ItemType Directory -Path $CertDir -Force | Out-Null
if (Test-Path $LocalCertPath) {
    Copy-Item -LiteralPath $LocalCertPath -Destination $CertPath -Force
} else {
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
    Invoke-WebRequest -Uri "$ServerUrl/api/setup/certificate" -OutFile $CertPath -UseBasicParsing
}
$Cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertPath)
$Store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
$Store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
$AlreadyTrusted = $false
foreach ($Item in $Store.Certificates) {
    if ($Item.Thumbprint -eq $Cert.Thumbprint) {
        $AlreadyTrusted = $true
        break
    }
}
$Store.Close()
if ($AlreadyTrusted) {
    Write-Host "[회계업무 WEB] WEB HTTPS 인증서가 이미 등록되어 있습니다."
} else {
    & certutil.exe -user -addstore Root $CertPath | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "WEB HTTPS 인증서 등록 실패: certutil exit code $LASTEXITCODE"
    }
}

$RunScript = Join-Path $InstallRoot "담당자PC_필수프로그램_실행.ps1"
@"
`$ErrorActionPreference = "Stop"
`$Root = "$InstallRoot"
`$env:WEB_SERVER_URL = "$ServerUrl"
`$env:PYTHON_EXE = "$Python"
powershell -ExecutionPolicy Bypass -File "`$Root\web_v1\deploy\start_user_erp_agent.ps1"
"@ | Set-Content -Path $RunScript -Encoding UTF8

try {
    $ProtocolKey = "HKCU:\Software\Classes\accountingweb"
    $CommandKey = Join-Path $ProtocolKey "shell\open\command"
    New-Item -Path $CommandKey -Force | Out-Null
    Set-Item -Path $ProtocolKey -Value "URL:Accounting WEB 필수 프로그램"
    New-ItemProperty -Path $ProtocolKey -Name "URL Protocol" -Value "" -PropertyType String -Force | Out-Null
    $PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $ProtocolCommand = "`"$PowerShellExe`" -NoProfile -ExecutionPolicy Bypass -File `"$RunScript`""
    Set-Item -Path $CommandKey -Value $ProtocolCommand
    Write-Host "[회계업무 WEB] 로그인 자동 실행 연결을 등록했습니다: accountingweb://start"
} catch {
    Write-Host "[회계업무 WEB] 로그인 자동 실행 연결 등록은 건너뜁니다: $($_.Exception.Message)"
}

try {
    $ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "회계업무 WEB 필수프로그램 실행.lnk"
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$RunScript`""
    $Shortcut.WorkingDirectory = $InstallRoot
    $Shortcut.Save()
    Write-Host "[회계업무 WEB] 바탕화면 실행 아이콘을 만들었습니다: $ShortcutPath"
} catch {
    Write-Host "[회계업무 WEB] 바탕화면 아이콘 생성은 건너뜁니다: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[회계업무 WEB] 설치 완료. 필수 프로그램을 실행합니다."
Write-Host "[회계업무 WEB] 이 창은 업무 중 닫지 마세요."
& powershell -ExecutionPolicy Bypass -File $RunScript
if ($LASTEXITCODE -ne 0) {
    throw "Accounting WEB agent exited with error. ExitCode=$LASTEXITCODE"
}
'''.strip().replace("__SERVER_URL__", server_url)


def _agent_bootstrap_script(server_url: str) -> str:
    return r'''
$ErrorActionPreference = "Stop"
$ServerUrl = "__SERVER_URL__"
$TempRoot = Join-Path $env:TEMP ("accounting_web_required_setup_" + [Guid]::NewGuid().ToString("N"))
$PayloadZip = Join-Path $TempRoot "payload.zip"

Write-Host "[회계업무 WEB] 필수 프로그램 설치 파일을 내려받습니다."
Write-Host "[회계업무 WEB] 서버: $ServerUrl"
New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null

[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
Invoke-WebRequest -Uri "$ServerUrl/api/setup/user-pc-payload.zip" -OutFile $PayloadZip -UseBasicParsing
Expand-Archive -Path $PayloadZip -DestinationPath $TempRoot -Force

$InstallScript = Join-Path $TempRoot "setup.ps1"
if (-not (Test-Path $InstallScript)) {
    $InstallScript = Join-Path $TempRoot "1_필수프로그램_설치_실행.ps1"
}
if (-not (Test-Path $InstallScript)) {
    throw "필수 프로그램 설치 스크립트를 찾지 못했습니다: $InstallScript"
}

Write-Host "[회계업무 WEB] 설치를 시작합니다."
& powershell -ExecutionPolicy Bypass -File $InstallScript
'''.strip().replace("__SERVER_URL__", server_url)


def _agent_cmd_launcher(server_url: str) -> str:
    return f'''@echo off
setlocal
set "SERVER_URL={server_url}"
set "TMPDIR=%TEMP%\\accounting_web_setup_%RANDOM%%RANDOM%"
set "ZIP=%TMPDIR%\\payload.zip"
echo [Accounting WEB] Required setup is starting.
echo [Accounting WEB] Please do not close this window.
mkdir "%TMPDIR%" >nul 2>nul
where curl.exe >nul 2>nul
if errorlevel 1 (
  echo.
  echo [Accounting WEB] curl.exe was not found on this PC.
  echo [Accounting WEB] Send this screen to administrator.
  pause
  exit /b 1
)
curl.exe -k -L --fail --output "%ZIP%" "%SERVER_URL%/api/setup/user-pc-payload.zip"
if errorlevel 1 (
  echo.
  echo [Accounting WEB] Setup download failed. Send this screen to administrator.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -Path $env:ZIP -DestinationPath $env:TMPDIR -Force"
if errorlevel 1 (
  echo.
  echo [Accounting WEB] Setup unpack failed. Send this screen to administrator.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%TMPDIR%\\setup.ps1"
if errorlevel 1 (
  echo.
  echo [Accounting WEB] Setup failed. Send this screen to administrator.
  pause
  exit /b 1
)
endlocal
'''


def _agent_exe_launcher(server_url: str) -> bytes:
    if not INSTALLER_EXE_PATH.exists():
        raise HTTPException(status_code=404, detail="담당자 PC 필수 프로그램 EXE 설치 파일이 서버에 없습니다.")
    return (
        INSTALLER_EXE_PATH.read_bytes()
        + INSTALLER_EXE_OVERLAY_BEGIN
        + server_url.encode("utf-8")
        + INSTALLER_EXE_OVERLAY_END
    )


def _agent_self_contained_cmd(server_url: str) -> str:
    payload = base64.b64encode(_build_user_pc_payload_zip(server_url)).decode("ascii")
    chunks = [payload[index : index + 76] for index in range(0, len(payload), 76)]
    lines = [
        "@echo off",
        "setlocal",
        "set \"TMPDIR=%TEMP%\\accounting_web_setup_%RANDOM%%RANDOM%\"",
        "set \"B64=%TMPDIR%\\payload.b64\"",
        "set \"ZIP=%TMPDIR%\\payload.zip\"",
        "echo [Accounting WEB] Required setup is starting.",
        "echo [Accounting WEB] Please do not close this window.",
        "mkdir \"%TMPDIR%\" >nul 2>nul",
        "> \"%B64%\" (",
    ]
    lines.extend(f"echo {chunk}" for chunk in chunks)
    lines.extend(
        [
            ")",
            "powershell -NoProfile -ExecutionPolicy Bypass -Command \"$ErrorActionPreference='Stop'; $b64 = Get-Content -Raw -Path $env:B64; [IO.File]::WriteAllBytes($env:ZIP, [Convert]::FromBase64String($b64))\"",
            "if errorlevel 1 (",
            "  echo.",
            "  echo [Accounting WEB] Setup decode failed. Send this screen to administrator.",
            "  pause",
            "  exit /b 1",
            ")",
            "powershell -NoProfile -ExecutionPolicy Bypass -Command \"$ErrorActionPreference='Stop'; Expand-Archive -Path $env:ZIP -DestinationPath $env:TMPDIR -Force\"",
            "if errorlevel 1 (",
            "  echo.",
            "  echo [Accounting WEB] Setup unpack failed. Send this screen to administrator.",
            "  pause",
            "  exit /b 1",
            ")",
            "powershell -NoProfile -ExecutionPolicy Bypass -File \"%TMPDIR%\\setup.ps1\"",
            "if errorlevel 1 (",
            "  echo.",
            "  echo [Accounting WEB] Setup failed. Send this screen to administrator.",
            "  pause",
            "  exit /b 1",
            ")",
            "endlocal",
        ]
    )
    return "\r\n".join(lines) + "\r\n"


def _add_installer_file(archive: zipfile.ZipFile, source, arcname: str) -> None:
    if not source.exists() or not source.is_file():
        return
    archive.write(source, arcname)


def _add_installer_tree(archive: zipfile.ZipFile, source, arc_root: str, suffixes: set[str] | None = None) -> None:
    if not source.exists():
        return
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        lowered = path.name.lower()
        if "__pycache__" in path.parts or lowered.endswith((".pyc", ".pyo")):
            continue
        if ".backup_" in lowered or lowered.endswith((".bak", ".tmp", ".log")):
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        archive.write(path, f"{arc_root}/{path.relative_to(source).as_posix()}")


def _build_user_pc_payload_zip(server_url: str) -> bytes:
    project_root = WEB_ROOT.parent
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("0_먼저_읽어주세요.txt", (
            "회계업무 WEB 담당자 PC 필수 프로그램 설치 파일입니다.\r\n\r\n"
            "이 파일은 웹에서 내려받은 설치 스크립트가 자동으로 사용합니다.\r\n"
            "수동으로 받은 경우 1_필수프로그램_설치_실행.ps1 파일을 우클릭 후 PowerShell에서 실행하세요.\r\n"
            "설치가 끝나면 열린 PowerShell 창은 업무 중 닫지 마세요.\r\n"
        ).encode("utf-8-sig"))
        installer_script = _agent_installer_script(server_url).encode("utf-8-sig")
        archive.writestr("setup.ps1", installer_script)
        archive.writestr("1_필수프로그램_설치_실행.ps1", installer_script)
        _add_installer_file(archive, WEB_ROOT / "__init__.py", "payload/web_v1/__init__.py")
        _add_installer_file(archive, WEB_ROOT / "VERSION", "payload/web_v1/VERSION")
        _add_installer_tree(archive, WEB_ROOT / "agent", "payload/web_v1/agent", {".py"})
        _add_installer_tree(archive, WEB_ROOT / "backend", "payload/web_v1/backend", {".py", ".txt", ".ps1"})
        _add_installer_tree(archive, WEB_ROOT / "deploy", "payload/web_v1/deploy", {".ps1", ".md"})
        _add_installer_tree(archive, project_root / "support", "payload/support", {".py", ".ini", ".json", ".xlsx"})
        legacy_manager = settings.legacy_manager_path
        _add_installer_file(archive, legacy_manager, f"payload/manager_server/{legacy_manager.name}")
        if settings.ssl_cert_file and settings.ssl_cert_file.exists():
            _add_installer_file(archive, settings.ssl_cert_file, "web_v1.cert.pem")
    return buffer.getvalue()


def client_ip(request: Request) -> str:
    forwarded = str(request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else "")


def require_setup_ready(request: Request) -> dict[str, Any]:
    status = setup_status(client_ip=client_ip(request))
    if not status["ready"]:
        missing = ", ".join(status.get("missing_items") or [])
        raise HTTPException(status_code=409, detail=f"필수 프로그램 점검이 완료되지 않았습니다: {missing}")
    return status


@app.on_event("startup")
def on_startup() -> None:
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    settings.chrome_profile_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    init_auth_db()
    init_setup_db()
    worker.start()
    _start_mail_collect_scheduler()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "version": settings.app_version,
        "env": settings.app_env,
        "erp_execution_mode": settings.erp_execution_mode,
    }


@app.get("/api/mail-collect/status")
def api_mail_collect_status() -> dict[str, Any]:
    return _mail_collect_status()


@app.post("/api/agent/heartbeat")
async def api_agent_heartbeat(request: Request) -> dict[str, Any]:
    payload = await request.json()
    agent_id = str(payload.get("agent_id") or "")
    request_client_ip = client_ip(request)
    profile = record_agent_heartbeat(
        agent_id,
        payload.get("capabilities") if isinstance(payload.get("capabilities"), dict) else {},
        client_ip=request_client_ip,
    )
    install_job = claim_install_job(agent_id)
    if not install_job:
        auto_job = ensure_auto_install_job(agent_id=agent_id, client_ip=request_client_ip)
        if auto_job:
            logging.info("Auto setup install job queued for %s: %s", agent_id, auto_job.get("companies"))
            install_job = claim_install_job(agent_id)
    return {
        "ok": True,
        "agent_id": agent_id,
        "agent_host": profile.get("agent_host", ""),
        "agent_user": profile.get("agent_user", ""),
        "server_time": datetime.now().isoformat(timespec="seconds"),
        "erp_execution_mode": settings.erp_execution_mode,
        "setup": setup_status(agent_id=agent_id, client_ip=request_client_ip),
        "install_job": install_job,
    }


@app.post("/api/login")
async def api_login(request: Request) -> dict[str, Any]:
    payload = await request.json()
    user_id = str(payload.get("user_id") or payload.get("id") or "").strip()
    password = str(payload.get("password") or payload.get("pw") or "").strip()
    user = authenticate_user(user_id, password)
    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    status = setup_status(user_id=user["id"], client_ip=client_ip(request))
    return {"ok": True, "user": user, "setup_required": not status["ready"], "setup": status}


@app.get("/api/setup/status")
def api_setup_status(request: Request, user_id: str = Query(default="", max_length=80), agent_id: str = Query(default="", max_length=160)) -> dict[str, Any]:
    return setup_status(user_id=user_id, agent_id=agent_id, client_ip=client_ip(request))


@app.post("/api/setup/printers")
async def api_setup_printers(request: Request) -> dict[str, Any]:
    payload = await request.json()
    try:
        saved = save_printer_mapping(
            payload.get("mapping") if isinstance(payload.get("mapping"), dict) else payload,
            agent_id=str(payload.get("agent_id") or ""),
            client_ip=client_ip(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, **saved, "setup": setup_status(agent_id=saved.get("agent_id", ""), client_ip=client_ip(request))}


@app.post("/api/setup/install")
async def api_setup_install(request: Request) -> dict[str, Any]:
    payload = await request.json()
    companies = payload.get("companies") if isinstance(payload.get("companies"), list) else None
    install_certificate = bool(payload.get("install_certificate"))
    try:
        job = create_install_job(
            [str(item) for item in companies] if companies is not None else None,
            agent_id=str(payload.get("agent_id") or ""),
            client_ip=client_ip(request),
            install_certificate=install_certificate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "job": job}


@app.get("/api/setup/certificate")
def api_setup_certificate() -> FileResponse:
    if not settings.ssl_cert_file or not settings.ssl_cert_file.exists():
        raise HTTPException(status_code=404, detail="WEB HTTPS 인증서 파일을 찾지 못했습니다.")
    return FileResponse(settings.ssl_cert_file, filename=settings.ssl_cert_file.name, media_type="application/x-pem-file")


@app.get("/api/setup/user-pc-installer.cmd")
@app.get("/api/setup/user-pc-installer")
def api_setup_user_pc_installer(request: Request) -> Response:
    server_url = _installer_server_url(request)
    filename = "accounting_web_v1_user_pc_required_setup.cmd"
    return Response(
        content=_agent_cmd_launcher(server_url).encode("ascii"),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/setup/user-pc-installer.exe")
def api_setup_user_pc_installer_exe(request: Request) -> Response:
    server_url = _installer_server_url(request)
    filename = "AccountingWebRequiredSetup.exe"
    return Response(
        content=_agent_exe_launcher(server_url),
        media_type="application/vnd.microsoft.portable-executable",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/setup/user-pc-bootstrap.ps1")
def api_setup_user_pc_bootstrap(request: Request) -> Response:
    server_url = _installer_server_url(request)
    filename = "accounting_web_v1_user_pc_required_bootstrap.ps1"
    return Response(
        content=_agent_bootstrap_script(server_url).encode("utf-8-sig"),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/setup/user-pc-payload.zip")
def api_setup_user_pc_payload(request: Request) -> Response:
    server_url = _installer_server_url(request)
    filename = "accounting_web_v1_user_pc_required_payload.zip"
    return Response(
        content=_build_user_pc_payload_zip(server_url),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/setup/installers/{company}")
def api_setup_installer(company: str) -> FileResponse:
    installer = find_installer(company)
    if not installer:
        raise HTTPException(status_code=404, detail=f"{company} 설치 파일을 찾지 못했습니다.")
    return FileResponse(installer, filename=installer.name)


@app.post("/api/agent/setup/install/{job_id}/complete")
async def api_agent_setup_install_complete(job_id: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    return complete_install_job(job_id, ok=bool(payload.get("ok")), result=payload)


@app.post("/api/agent/erp/next", response_model=None)
async def api_agent_next_task(request: Request) -> Any:
    payload = await request.json()
    task = claim_next_erp_task(
        agent_id=str(payload.get("agent_id") or ""),
        capabilities=payload.get("capabilities") if isinstance(payload.get("capabilities"), dict) else {},
        client_ip=client_ip(request),
    )
    if not task:
        return Response(status_code=204)
    job_id = str(task.get("job_id") or "")
    if job_store.get(job_id):
        if str(task.get("job_type") or "") == "expense_report":
            job_store.add_event(job_id, "erp", 80, f"담당자 PC Agent 현금출금결의서 생성 시작: {task.get('agent_id')}")
        else:
            job_store.add_event(job_id, "erp", 80, f"ERP Agent claimed task: {task.get('agent_id')}")
    return task


@app.post("/api/agent/jobs/{job_id}/event")
async def api_agent_job_event(job_id: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    touch_agent_seen(str(payload.get("agent_id") or ""), client_ip=client_ip(request))
    status = str(payload.get("status") or "erp")
    if status not in {"queued", "running", "crawling", "analyzing", "erp", "printing", "done", "error"}:
        status = "erp"
    progress = int(payload.get("progress") or 90)
    message = str(payload.get("message") or "")
    if job_store.get(job_id):
        job_store.add_event(job_id, status, progress, message)
    for invoice_id in payload.get("invoice_ids") or []:
        try:
            add_invoice_log(int(invoice_id), message, level="error" if status == "error" else "info", job_id=job_id)
        except Exception:
            pass
    return {"ok": True}


@app.post("/api/agent/jobs/{job_id}/voucher")
def api_agent_job_voucher_upload(
    job_id: str,
    request: Request,
    invoice_id: int = Form(...),
    agent_id: str = Form(""),
    local_path: str = Form(""),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    touch_agent_seen(agent_id, client_ip=client_ip(request))
    filename = safe_filename(file.filename or f"erp_voucher_{invoice_id}.pdf", fallback=f"erp_voucher_{invoice_id}.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="전표는 PDF 파일만 업로드할 수 있습니다.")

    target_dir = settings.erp_db_dir / "erp_vouchers" / str(invoice_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "01_전표.pdf"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    updated = update_invoice_json(
        invoice_id,
        {
            "erp_pdf_path": str(target),
            "erp_voucher_pdf_path": str(target),
            "voucher_pdf_path": str(target),
            "erp_pdf_local_path": str(local_path or ""),
            "erp_voucher_original_filename": filename,
            "erp_voucher_uploaded_by_agent": agent_id,
            "erp_voucher_upload_job_id": job_id,
            "erp_voucher_uploaded_at": datetime.now().isoformat(timespec="seconds"),
        },
        message=f"ERP 전표 PDF 서버 보관 완료: {target}",
    )
    refreshed = get_invoice(invoice_id) or updated or invoice
    output_docs = build_output_set_status(refreshed, persist=True)
    if job_store.get(job_id):
        job_store.add_event(job_id, "erp", 96, f"ERP 전표 PDF 서버 보관 완료: #{invoice_id}")
    return {
        "ok": True,
        "invoice_id": invoice_id,
        "erp_pdf_path": str(target),
        "server_path": str(target),
        "local_path": str(local_path or ""),
        "output_docs": output_docs,
    }


@app.post("/api/agent/jobs/{job_id}/expense-report")
def api_agent_job_expense_report_upload(
    job_id: str,
    request: Request,
    invoice_id: int = Form(...),
    agent_id: str = Form(""),
    local_path: str = Form(""),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    touch_agent_seen(agent_id, client_ip=client_ip(request))
    filename = safe_filename(file.filename or f"expense_report_{invoice_id}.pdf", fallback=f"expense_report_{invoice_id}.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="현금출금결의서는 PDF 파일만 업로드할 수 있습니다.")

    target_dir = settings.erp_db_dir / "expense_reports" / str(invoice_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "04_현금출금결의서.pdf"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    updated = update_invoice_json(
        invoice_id,
        {
            "expense_report_pdf_path": str(target),
            "expense_report_local_path": str(local_path or ""),
            "expense_report_original_filename": filename,
            "expense_report_uploaded_by_agent": agent_id,
            "expense_report_upload_job_id": job_id,
            "expense_report_uploaded_at": datetime.now().isoformat(timespec="seconds"),
        },
        message=f"현금출금결의서 PDF 서버 보관 완료: {target}",
    )
    refreshed = get_invoice(invoice_id) or updated or invoice
    output_docs = build_output_set_status(refreshed, persist=True)
    if job_store.get(job_id):
        job_store.add_event(job_id, "erp", 96, f"현금출금결의서 PDF 서버 보관 완료: #{invoice_id}")
    return {
        "ok": True,
        "invoice_id": invoice_id,
        "expense_report_pdf_path": str(target),
        "server_path": str(target),
        "local_path": str(local_path or ""),
        "output_docs": output_docs,
    }


@app.post("/api/agent/jobs/{job_id}/complete")
async def api_agent_job_complete(job_id: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    ok = bool(payload.get("ok"))
    invoice_ids = [int(item) for item in payload.get("invoice_ids") or [] if str(item).isdigit()]
    agent_id = str(payload.get("agent_id") or "")
    touch_agent_seen(agent_id, client_ip=client_ip(request))
    message = str(payload.get("message") or ("ERP Agent completed" if ok else "ERP Agent failed"))
    successes = payload.get("successes") if isinstance(payload.get("successes"), list) else []
    success_by_invoice_id = {
        int(item.get("invoice_id")): item
        for item in successes
        if isinstance(item, dict) and str(item.get("invoice_id")).isdigit()
    }
    task_payload = update_erp_task(
        job_id,
        "done" if ok else "error",
        {
            "agent_id": agent_id,
            "agent_result": payload,
            "completed_at": payload.get("completed_at") or "",
        },
    )
    job_type = str(task_payload.get("job_type") or payload.get("job_type") or "")
    if job_type == "expense_report":
        expense_job = job_store.get(job_id)
        expense_payload = expense_job.payload if expense_job else {}
        source_job_id = str(expense_payload.get("source_job_id") or task_payload.get("source_job_id") or "")
        for invoice_id in invoice_ids:
            refreshed_invoice = get_invoice(invoice_id)
            if refreshed_invoice:
                build_output_set_status(refreshed_invoice, persist=True)
            add_invoice_log(invoice_id, message, level="info" if ok else "error", job_id=job_id)
        if job_store.get(job_id):
            job_store.set_result(job_id, dict(payload))
            if ok:
                job_store.add_event(job_id, "done", 100, message)
            else:
                job_store.set_error(job_id, message)
                job_store.add_event(job_id, "error", 100, message)
        if ok and source_job_id:
            _maybe_queue_one_click_output(source_job_id)
        return {"ok": True}
    for index, invoice_id in enumerate(invoice_ids):
        result = success_by_invoice_id.get(invoice_id)
        if result is None and index < len(successes) and isinstance(successes[index], dict):
            result = successes[index]
        invoice_ok = ok or invoice_id in success_by_invoice_id
        erp_pdf_path = str((result or {}).get("erp_pdf_server_path") or (result or {}).get("erp_pdf_path") or "").strip()
        erp_pdf_local_path = str((result or {}).get("erp_pdf_local_path") or "").strip()
        erp_pdf_uploaded = bool((result or {}).get("erp_pdf_uploaded") or (result or {}).get("erp_pdf_server_path"))
        if invoice_ok and erp_pdf_path and erp_pdf_uploaded and Path(erp_pdf_path).exists():
            update_invoice_json(
                invoice_id,
                {"erp_pdf_path": erp_pdf_path, "erp_voucher_pdf_path": erp_pdf_path},
                message=f"ERP 전표 PDF 경로 저장: {erp_pdf_path}",
            )
            refreshed_invoice = get_invoice(invoice_id)
            if refreshed_invoice:
                build_output_set_status(refreshed_invoice, persist=True)
        elif invoice_ok and erp_pdf_path:
            add_invoice_log(
                invoice_id,
                f"ERP 전표 PDF 서버 보관 누락: server_path={erp_pdf_path}, agent_local_path={erp_pdf_local_path}",
                level="error",
                job_id=job_id,
            )
        if invoice_ok:
            refreshed_invoice = get_invoice(invoice_id)
            if refreshed_invoice:
                build_output_set_status(refreshed_invoice, persist=True)
        display_processor = normalize_processor(agent_id) or "ERP Agent"
        set_invoice_status(invoice_id, DONE if invoice_ok else ERROR, processor=display_processor, job_id=job_id, processed=invoice_ok, error="" if invoice_ok else message)
        add_invoice_log(invoice_id, message, level="info" if invoice_ok else "error", job_id=job_id)
        if invoice_ok:
            _queue_expense_report_after_erp(
                invoice_id,
                agent_id=agent_id,
                target_client_ip=str(task_payload.get("target_client_ip") or client_ip(request)).strip(),
                source_job_id=job_id,
            )
    if job_store.get(job_id):
        job_store.set_result(job_id, dict(payload))
        if ok:
            job_store.add_event(job_id, "done", 100, message)
        else:
            job_store.set_error(job_id, message)
            job_store.add_event(job_id, "error", 100, message)
    return {"ok": True}


@app.get("/api/version")
def version() -> dict[str, Any]:
    return {
        "product": "회계업무 자동화 WEB",
        "version": settings.app_version,
        "agent_bundle_hash": expected_agent_bundle_hash(),
    }


@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/jobs", response_model=JobResponse, status_code=202)
def create_job(request: JobCreateRequest) -> JobResponse:
    job = job_store.create(request)
    worker.submit(job)
    return job.to_response()


@app.post("/api/jobs/demo", response_model=JobResponse, status_code=202)
def create_demo_job() -> JobResponse:
    job = job_store.create(
        JobCreateRequest(
            job_type="demo",
            title="WEB v1.0 progress demo",
            payload={"delay_seconds": 0.7},
        )
    )
    worker.submit(job)
    return job.to_response()


@app.post("/api/jobs/purchase-mail-collect", response_model=JobResponse, status_code=202)
def create_purchase_mail_collect_job(request: Request) -> JobResponse:
    require_setup_ready(request)
    job = _queue_mail_collect_job(auto=False)
    return job.to_response()


@app.post("/api/jobs/purchase-one-click", response_model=JobResponse, status_code=202)
def create_purchase_one_click_job(body: InvoiceIdsRequest, request: Request) -> JobResponse:
    if not body.invoice_ids:
        raise HTTPException(status_code=400, detail="원클릭 처리할 구매 건을 선택해야 합니다.")
    setup = require_setup_ready(request)
    output = _one_click_output_payload(body.output_target, setup)
    job = job_store.create(
        JobCreateRequest(
            job_type="purchase_one_click",
            title=f"구매 원클릭 처리 {len(body.invoice_ids)}건",
            payload={
                "invoice_ids": body.invoice_ids,
                "processor": body.processor or "WEB v1.0",
                "target_agent_id": setup.get("agent_id") or "",
                "target_client_ip": setup.get("client_ip") or client_ip(request),
                "one_click": True,
                "output_target": body.output_target,
                "output_action": output["action"],
                "printer_key": output["printer_key"],
                "printer_name": output["printer_name"],
            },
        )
    )
    worker.submit(job)
    return job.to_response()


@app.post("/api/jobs/purchase-analyze", response_model=JobResponse, status_code=202)
def create_purchase_analyze_job(body: InvoiceIdsRequest, request: Request) -> JobResponse:
    require_setup_ready(request)
    if len(body.invoice_ids) != 1:
        raise HTTPException(status_code=400, detail="구매 분석은 1건씩 실행해야 합니다.")
    invoice_id = int(body.invoice_ids[0])
    job = job_store.create(
        JobCreateRequest(
            job_type="purchase_analyze",
            title=f"구매 분석 #{invoice_id}",
            payload={"invoice_id": invoice_id},
        )
    )
    worker.submit(job)
    return job.to_response()


@app.post("/api/jobs/purchase-erp-input", response_model=JobResponse, status_code=202)
def create_purchase_erp_input_job(body: InvoiceIdsRequest, request: Request) -> JobResponse:
    if not body.invoice_ids:
        raise HTTPException(status_code=400, detail="ERP 입력할 구매 건을 선택해야 합니다.")
    setup = require_setup_ready(request)
    job = job_store.create(
        JobCreateRequest(
            job_type="purchase_erp_input",
            title=f"구매 ERP 입력 실행 {len(body.invoice_ids)}건",
            payload={
                "invoice_ids": body.invoice_ids,
                "processor": body.processor or "WEB v1.0",
                "target_agent_id": setup.get("agent_id") or "",
                "target_client_ip": setup.get("client_ip") or client_ip(request),
            },
        )
    )
    worker.submit(job)
    return job.to_response()


@app.post("/api/jobs/output-set", response_model=JobResponse, status_code=202)
def create_output_set_job(body: OutputSetRequest, request: Request) -> JobResponse:
    if not body.invoice_ids:
        raise HTTPException(status_code=400, detail="출력 세트를 만들 건을 선택해야 합니다.")
    setup = require_setup_ready(request)
    printer_name = ""
    if body.action == "print_individual":
        mapping = setup.get("capabilities", {}).get("printer_mapping", {})
        printer_name = str(mapping.get(body.printer_key) or "").strip()
        if not printer_name:
            raise HTTPException(status_code=400, detail="선택한 출력 대상 프린터 매핑이 없습니다.")
    action_label = {
        "merged_pdf": "통합본 PDF 저장",
        "individual_pdf": "개별 PDF 저장",
        "print_individual": "개별 출력",
    }[body.action]
    job = job_store.create(
        JobCreateRequest(
            job_type="output_set",
            title=f"문서 세트 {action_label} {len(body.invoice_ids)}건",
            payload={
                "invoice_ids": body.invoice_ids,
                "action": body.action,
                "printer_key": body.printer_key,
                "printer_name": printer_name,
                "processor": body.processor or "WEB v1.0",
            },
        )
    )
    worker.submit(job)
    return job.to_response()


@app.get("/api/invoices")
def api_list_invoices(mode: str = Query(default="", max_length=30), limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
    return list_invoices(mode=mode, limit=limit)


def _save_pdf_upload(upload: UploadFile, target_dir: Path, fallback_filename: str, *, fixed_filename: str = "") -> tuple[Path, str]:
    filename = safe_filename(upload.filename or fallback_filename, fallback=fallback_filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (fixed_filename or f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{filename}")
    with target.open("wb") as out:
        shutil.copyfileobj(upload.file, out)
    return target, filename


@app.post("/api/invoices/manual-purchase")
def api_create_manual_purchase_invoice(
    tax_invoice: UploadFile = File(...),
    quote: UploadFile | None = File(default=None),
) -> dict[str, Any]:
    tax_target, tax_filename = _save_pdf_upload(
        tax_invoice,
        settings.erp_db_dir / "manual_uploads" / "purchase_tax",
        "tax_invoice.pdf",
    )

    tax_text = ""
    tax_order_no = ""
    invoice_date = ""
    supply_amount = 0
    vat_amount = 0
    total_amount = 0
    try:
        tax_text = _extract_pdf_text(tax_target)
        tax_order_no = _extract_order_no_from_tax(tax_text)
        invoice_date = _extract_date(tax_text, str(tax_target)) or extract_purchase_date_from_path(str(tax_target))
        supply_amount, vat_amount, total_amount = _extract_amounts_from_tax(tax_text)
    except Exception as exc:
        logging.warning("Manual purchase tax parse failed: %s", exc)

    data: dict[str, Any] = {
        "invoice_type": "purchase",
        "manual_upload": True,
        "pdf_path": str(tax_target),
        "tax_invoice_pdf_path": str(tax_target),
        "tax_invoice_original_filename": tax_filename,
        "purchase_analysis_ready": False,
        "erp_ready": False,
    }
    if invoice_date:
        data["invoice_date"] = invoice_date
    if tax_order_no:
        data["tax_order_no"] = tax_order_no
        data["order_no"] = tax_order_no
        data["purchase_order_no"] = tax_order_no
    if supply_amount:
        data["supply_amount"] = supply_amount
    if vat_amount:
        data["vat_amount"] = vat_amount
        data["tax_amount"] = vat_amount
    if total_amount:
        data["total_amount"] = total_amount

    subject = f"수동 업로드: {Path(tax_filename).stem}"
    invoice_id = insert_manual_invoice(
        subject,
        {**data, "subject": subject, "data": dict(data)},
        log_message="수동 업로드로 구매 세금계산서가 등록되었습니다.",
    )

    quote_path = ""
    if quote is not None and str(quote.filename or "").strip():
        quote_target, quote_filename = _save_pdf_upload(
            quote,
            purchase_quote_dir(invoice_id),
            f"quote_{invoice_id}.pdf",
        )
        quote_path = str(quote_target)
        quote_order_no = ""
        try:
            quote_order_no = _extract_order_no_from_quote(_extract_pdf_text(quote_target))
        except Exception as exc:
            logging.warning("Manual purchase quote parse failed: %s", exc)
        order_no = tax_order_no or quote_order_no
        updates: dict[str, Any] = {
            "quote_path": quote_path,
            "quote_pdf_path": quote_path,
            "quote_original_filename": quote_filename,
            "quote_order_no": quote_order_no,
            "purchase_analysis_ready": False,
            "erp_ready": False,
        }
        if order_no:
            updates["order_no"] = order_no
            updates["purchase_order_no"] = order_no
        update_invoice_json(invoice_id, updates, message=f"수동 업로드 견적서 첨부: {quote_target}")

    invoice = get_invoice(invoice_id)
    if invoice and quote_path:
        try:
            analysis = analyze_purchase_documents(invoice)
            update_invoice_json(invoice_id, analysis, message="수동 업로드 자료 분석 결과가 저장되었습니다.")
            reset_invoice(invoice_id)
        except Exception as exc:
            add_invoice_log(invoice_id, f"수동 업로드 자료 자동 분석 보류: {exc}", level="error")

    refreshed = get_invoice(invoice_id) or {"id": invoice_id}
    if isinstance(refreshed, dict):
        refreshed["output_docs"] = build_output_set_status(refreshed, persist=True)
    return refreshed


@app.get("/api/invoices/{invoice_id}")
def api_get_invoice(invoice_id: int) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@app.get("/api/invoices/{invoice_id}/output-set")
def api_get_invoice_output_set(invoice_id: int) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return build_output_set_status(invoice, persist=True)


@app.post("/api/invoices/{invoice_id}/tax-invoice")
def api_upload_tax_invoice(invoice_id: int, file: UploadFile = File(...)) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    filename = safe_filename(file.filename or f"tax_invoice_{invoice_id}.pdf", fallback=f"tax_invoice_{invoice_id}.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="세금계산서는 PDF 파일로 첨부해 주세요.")
    target_dir = settings.erp_db_dir / "tax_invoices" / str(invoice_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "02_세금계산서.pdf"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    updated = update_invoice_pdf_path(
        invoice_id,
        str(target),
        {"tax_invoice_original_filename": filename},
        message=f"세금계산서 PDF 첨부: {target}",
    )
    refreshed = get_invoice(invoice_id) or updated or invoice
    output_docs = build_output_set_status(refreshed, persist=True)
    refreshed = get_invoice(invoice_id) or refreshed
    if isinstance(refreshed, dict):
        refreshed["output_docs"] = output_docs
    return refreshed or {"ok": True, "invoice_id": invoice_id, "pdf_path": str(target), "output_docs": output_docs}


@app.post("/api/invoices/{invoice_id}/voucher")
def api_upload_erp_voucher(invoice_id: int, file: UploadFile = File(...)) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    filename = safe_filename(file.filename or f"erp_voucher_{invoice_id}.pdf", fallback=f"erp_voucher_{invoice_id}.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="전표는 PDF 파일로 첨부해 주세요.")
    target_dir = settings.erp_db_dir / "erp_vouchers" / str(invoice_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "01_전표.pdf"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    updated = update_invoice_json(
        invoice_id,
        {
            "erp_pdf_path": str(target),
            "erp_voucher_pdf_path": str(target),
            "voucher_pdf_path": str(target),
            "erp_voucher_original_filename": filename,
        },
        message=f"전표 PDF 첨부: {target}",
    )
    refreshed = get_invoice(invoice_id) or updated or invoice
    output_docs = build_output_set_status(refreshed, persist=True)
    refreshed = get_invoice(invoice_id) or refreshed
    if isinstance(refreshed, dict):
        refreshed["output_docs"] = output_docs
    return refreshed or {"ok": True, "invoice_id": invoice_id, "erp_pdf_path": str(target), "output_docs": output_docs}


@app.post("/api/invoices/{invoice_id}/quote")
def api_upload_purchase_quote(invoice_id: int, file: UploadFile = File(...)) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if str(invoice.get("invoice_type") or "").lower() != "purchase":
        raise HTTPException(status_code=400, detail="구매 처리 건에만 견적서를 첨부할 수 있습니다.")
    filename = safe_filename(file.filename or f"quote_{invoice_id}.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="견적서는 PDF 파일로 첨부해 주세요.")
    target = purchase_quote_dir(invoice_id) / filename
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    quote_order_no = ""
    try:
        quote_order_no = _extract_order_no_from_quote(_extract_pdf_text(target))
    except Exception:
        quote_order_no = ""
    raw = dict(invoice.get("raw") or {})
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    existing_order_no = str(
        data.get("order_no")
        or raw.get("order_no")
        or data.get("purchase_order_no")
        or raw.get("purchase_order_no")
        or ""
    ).strip()
    order_no = existing_order_no or quote_order_no
    updated = update_invoice_json(
        invoice_id,
        {
            "quote_path": str(target),
            "quote_pdf_path": str(target),
            "quote_order_no": quote_order_no,
            "order_no": order_no,
            "purchase_order_no": order_no,
            "purchase_analysis_ready": False,
            "erp_ready": False,
        },
        message=f"견적서 첨부: {target}",
    )
    reset_invoice(invoice_id)
    return get_invoice(invoice_id) or updated or {"ok": True, "invoice_id": invoice_id, "quote_path": str(target)}


@app.post("/api/invoices/{invoice_id}/analyze-purchase")
def api_analyze_purchase(invoice_id: int) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if str(invoice.get("invoice_type") or "").lower() != "purchase":
        raise HTTPException(status_code=400, detail="구매 처리 건만 분석할 수 있습니다.")
    try:
        analysis = analyze_purchase_documents(invoice)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ai_note = "AI 분석 사용" if analysis.get("analysis_ai_used") else "학습 DB/빠른 파싱 사용"
    updated = update_invoice_json(invoice_id, analysis, message=f"구매 세금계산서/견적서 분석 결과가 저장되었습니다. ({ai_note})")
    reset_invoice(invoice_id)
    return get_invoice(invoice_id) or updated or {"ok": True, "invoice_id": invoice_id, "analysis": analysis}


@app.post("/api/invoices/{invoice_id}/approval")
def api_upload_purchase_approval(
    invoice_id: int,
    files: list[UploadFile] = File(...),
    replace: bool = Form(default=False),
) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if str(invoice.get("invoice_type") or "").lower() != "purchase":
        raise HTTPException(status_code=400, detail="구매 처리 건에만 품의결재본을 첨부할 수 있습니다.")
    raw = dict(invoice.get("raw") or {})
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    approval_pdf_paths = [] if replace else list(data.get("approval_pdf_paths") or raw.get("approval_pdf_paths") or [])
    saved_paths: list[str] = []
    target_dir = purchase_approval_dir(invoice_id)
    if replace:
        for existing in target_dir.glob("*.pdf"):
            try:
                existing.unlink()
            except OSError:
                pass
    for upload in files:
        filename = safe_filename(upload.filename or f"approval_{invoice_id}.pdf", fallback=f"approval_{invoice_id}.pdf")
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="품의결재본은 PDF 파일로 첨부해 주세요.")
        target = target_dir / filename
        with target.open("wb") as out:
            shutil.copyfileobj(upload.file, out)
        saved_paths.append(str(target))
    approval_pdf_paths.extend(saved_paths)
    approval_pdf_paths = list(dict.fromkeys(path for path in approval_pdf_paths if path))
    updated = update_invoice_json(
        invoice_id,
        {
            "approval_pdf_paths": approval_pdf_paths,
            "approval_fetch_status": "done",
            "approval_fetch_error": "",
        },
        message=f"품의결재본 {'교체' if replace else '첨부'}: {len(saved_paths)}건",
    )
    refreshed = get_invoice(invoice_id) or updated or invoice
    output_docs = build_output_set_status(refreshed, persist=True)
    refreshed = get_invoice(invoice_id) or refreshed
    if isinstance(refreshed, dict):
        refreshed["output_docs"] = output_docs
    return refreshed or {"ok": True, "invoice_id": invoice_id, "approval_pdf_paths": approval_pdf_paths, "output_docs": output_docs}


@app.post("/api/invoices/{invoice_id}/expense-report-file")
def api_upload_expense_report_file(invoice_id: int, file: UploadFile = File(...)) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if str(invoice.get("invoice_type") or "").lower() != "purchase":
        raise HTTPException(status_code=400, detail="구매 처리 건에만 현금출금결의서를 첨부할 수 있습니다.")
    filename = safe_filename(file.filename or f"expense_report_{invoice_id}.pdf", fallback=f"expense_report_{invoice_id}.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="현금출금결의서는 PDF 파일로 첨부해 주세요.")
    target_dir = settings.erp_db_dir / "expense_reports" / str(invoice_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "04_현금출금결의서.pdf"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    updated = update_invoice_json(
        invoice_id,
        {
            "expense_report_pdf_path": str(target),
            "expense_report_original_filename": filename,
        },
        message=f"현금출금결의서 PDF 첨부: {target}",
    )
    refreshed = get_invoice(invoice_id) or updated or invoice
    output_docs = build_output_set_status(refreshed, persist=True)
    refreshed = get_invoice(invoice_id) or refreshed
    if isinstance(refreshed, dict):
        refreshed["output_docs"] = output_docs
    return refreshed or {"ok": True, "invoice_id": invoice_id, "expense_report_pdf_path": str(target), "output_docs": output_docs}


@app.post("/api/invoices/{invoice_id}/expense-report")
def api_generate_expense_report(invoice_id: int, request: Request) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if str(invoice.get("invoice_type") or "").lower() != "purchase":
        raise HTTPException(status_code=400, detail="구매 처리 건에만 현금출금결의서를 생성할 수 있습니다.")
    setup = require_setup_ready(request)
    target_agent_id = str(setup.get("agent_id") or "").strip()
    target_client_ip = str(setup.get("client_ip") or client_ip(request)).strip()
    if not target_agent_id or not target_client_ip:
        raise HTTPException(status_code=409, detail="담당자 PC 필수 프로그램이 연결되어야 현금출금결의서를 생성할 수 있습니다.")

    job = job_store.create(
        JobCreateRequest(
            job_type="expense_report",
            title=f"현금출금결의서 생성 #{invoice_id}",
            payload={
                "invoice_id": invoice_id,
                "target_agent_id": target_agent_id,
                "target_client_ip": target_client_ip,
            },
        )
    )
    queue_path = write_expense_report_queue(
        job.id,
        invoice,
        target_agent_id=target_agent_id,
        target_client_ip=target_client_ip,
    )
    job_store.add_event(job.id, "erp", 72, f"담당자 PC 현금출금결의서 생성 요청: #{invoice_id}")
    add_invoice_log(invoice_id, f"현금출금결의서 생성 요청: 담당자 PC Agent ({queue_path})", level="info", job_id=job.id)

    deadline = time.monotonic() + 120
    last_error = ""
    while time.monotonic() < deadline:
        refreshed = get_invoice(invoice_id) or invoice
        report_path = str(refreshed.get("expense_report_pdf_path") or "").strip()
        if report_path and Path(report_path).exists():
            output_docs = build_output_set_status(refreshed, persist=True)
            refreshed = get_invoice(invoice_id) or refreshed
            if isinstance(refreshed, dict):
                refreshed["output_docs"] = output_docs
            return refreshed or {
                "ok": True,
                "invoice_id": invoice_id,
                "expense_report_pdf_path": report_path,
                "output_docs": output_docs,
            }
        current_job = job_store.get(job.id)
        if current_job and current_job.status == "error":
            last_error = current_job.error or current_job.message or ""
            break
        time.sleep(1.0)

    output_docs = build_output_set_status(invoice, persist=True)
    for doc in output_docs.get("docs", []):
        if doc.get("key") == "expense_report":
            doc["status"] = "failed"
            doc["status_label"] = "실패"
            doc["message"] = last_error or "담당자 PC Agent의 현금출금결의서 생성 응답을 기다리다 시간이 초과되었습니다."
    update_invoice_json(invoice_id, {"output_docs": output_docs})
    message = last_error or "담당자 PC Agent의 현금출금결의서 생성 응답을 기다리다 시간이 초과되었습니다."
    add_invoice_log(invoice_id, f"현금출금결의서 생성 실패: {message}", level="error", job_id=job.id)
    raise HTTPException(status_code=408, detail=f"현금출금결의서 생성 실패: {message}")

    try:
        path = generate_expense_report_pdf(invoice, force=True)
    except Exception as exc:
        output_docs = build_output_set_status(invoice, persist=True)
        for doc in output_docs.get("docs", []):
            if doc.get("key") == "expense_report":
                doc["status"] = "failed"
                doc["status_label"] = "실패"
                doc["message"] = str(exc)
        update_invoice_json(invoice_id, {"output_docs": output_docs})
        add_invoice_log(invoice_id, f"현금출금결의서 생성 실패: {exc}", level="error")
        raise HTTPException(status_code=400, detail=f"현금출금결의서 생성 실패: {exc}") from exc
    update_invoice_json(
        invoice_id,
        {"expense_report_pdf_path": path},
        message=f"현금출금결의서 PDF 생성: {path}",
    )
    refreshed = get_invoice(invoice_id) or invoice
    output_docs = build_output_set_status(refreshed, persist=True)
    refreshed = get_invoice(invoice_id) or refreshed
    if isinstance(refreshed, dict):
        refreshed["output_docs"] = output_docs
    return refreshed or {"ok": True, "invoice_id": invoice_id, "expense_report_pdf_path": path, "output_docs": output_docs}


@app.patch("/api/invoices/{invoice_id}/purchase-analysis")
def api_update_purchase_analysis(invoice_id: int, request: PurchaseAnalysisUpdate) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    raw = dict(invoice.get("raw") or {})
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    quote_path = data.get("quote_path") or raw.get("quote_path") or ""
    approval_pdf_paths = request.approval_pdf_paths or data.get("approval_pdf_paths") or raw.get("approval_pdf_paths") or []
    payload = request.model_dump()
    date_digits = "".join(ch for ch in str(payload.get("invoice_date") or "") if ch.isdigit())
    if len(date_digits) >= 4 and int(date_digits[:4]) < 2020:
        repaired_date = extract_purchase_date_from_path(str(invoice.get("pdf_path") or raw.get("pdf_path") or data.get("pdf_path") or ""))
        if repaired_date:
            payload["invoice_date"] = repaired_date
    items = payload.get("items")
    if isinstance(items, list):
        payload["items"] = _normalize_items_for_display(items)
    payload.update(
        {
            "quote_path": quote_path,
            "quote_pdf_path": quote_path,
            "purchase_analysis_ready": True,
            "approval_pdf_paths": approval_pdf_paths,
            "erp_ready": bool(payload.get("items")),
        }
    )
    learned_count = learn_dictionary_items(list(payload.get("items") or []))
    updated = update_invoice_json(invoice_id, payload, message="구매 분석 결과를 화면에서 수정 저장했습니다.")
    if learned_count:
        from .invoice_db import add_invoice_log

        add_invoice_log(invoice_id, f"구매 품목 학습 DB 반영: {learned_count}건")
    reset_invoice(invoice_id)
    return get_invoice(invoice_id) or updated or {"ok": True, "invoice_id": invoice_id}


@app.get("/api/invoices/{invoice_id}/logs")
def api_get_invoice_logs(invoice_id: int, limit: int = Query(default=100, ge=1, le=300)) -> list[dict[str, Any]]:
    if not get_invoice(invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return list_invoice_logs(invoice_id, limit=limit)


@app.post("/api/invoices/{invoice_id}/retry")
def api_retry_invoice(invoice_id: int) -> dict[str, Any]:
    if not reset_invoice(invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"ok": True, "invoice_id": invoice_id, "status": "대기중"}


@app.delete("/api/invoices/{invoice_id}")
def api_delete_invoice(invoice_id: int) -> dict[str, Any]:
    if not delete_invoice(invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"ok": True, "invoice_id": invoice_id}


@app.get("/api/jobs", response_model=list[JobResponse])
def list_jobs(limit: int = Query(default=50, ge=1, le=200)) -> list[JobResponse]:
    return [job.to_response() for job in job_store.list_recent(limit=limit)]


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_response()


@app.get("/api/jobs/{job_id}/events")
async def stream_job_events(request: Request, job_id: str, after: int = Query(default=-1)) -> StreamingResponse:
    if not job_store.get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_stream():
        last_seq = after
        try:
            while True:
                if await request.is_disconnected():
                    break
                events = job_store.events_after(job_id, last_seq)
                for event in events:
                    last_seq = event.seq
                    payload = event.to_response().model_dump(mode="json")
                    yield f"id: {event.seq}\nevent: job-progress\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                job = job_store.get(job_id)
                if job and job.status in {"done", "error"} and not job_store.events_after(job_id, last_seq):
                    break
                await asyncio.sleep(0.5)
        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            return

    return StreamingResponse(event_stream(), media_type="text/event-stream")


app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="frontend-assets")
