from __future__ import annotations

import argparse
import getpass
import hashlib
import mimetypes
import os
import shutil
import socket
import subprocess
import sys
import time
import tempfile
import threading
import urllib3
import zipfile
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent_adapter import run_erp_voucher_task


DEFAULT_REPO_ZIP_URL = os.getenv(
    "EXCEL_VOUCHER_REPO_ZIP_URL",
    "https://github.com/rlckd2201/ERP_Auto_Web/archive/refs/heads/main.zip",
)
DEFAULT_PRINTER_NAME = "재정 프린터 (172.16.10.173)"
TEST_PRINTER_NAMES = {"김제 프린터 (172.17.30.162)", "172.17.30.162"}


def _normalize_printer_name(value: str) -> str:
    printer_name = str(value or "").strip()
    if not printer_name or printer_name in TEST_PRINTER_NAMES:
        return DEFAULT_PRINTER_NAME
    return printer_name


def _post(session: requests.Session, server: str, path: str, payload: dict[str, Any], *, verify_tls: bool) -> dict[str, Any]:
    response = session.post(f"{server.rstrip('/')}{path}", json=payload, timeout=30, verify=verify_tls)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {}


def _connection_error_message(server: str, exc: Exception) -> str:
    return f"server unreachable: {server} ({exc.__class__.__name__}: {exc})"


def _safe_filename(value: str, default: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in (" ", ".", "_", "-", "(", ")") else "_" for ch in value)
    cleaned = cleaned.strip(" .")
    return cleaned or default


def _download_job_source(
    session: requests.Session,
    server: str,
    task: dict[str, Any],
    output_dir: Path,
    *,
    verify_tls: bool,
) -> Path:
    job_id = str(task.get("id") or task.get("job_id") or "unknown")
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    source_name = _safe_filename(str(payload.get("source_filename") or ""), f"{job_id}.xlsx")
    source_suffix = Path(source_name).suffix.lower()
    if source_suffix not in (".xlsx", ".xlsm", ".xls"):
        source_name = f"{Path(source_name).stem or job_id}.xlsx"
    source_dir = output_dir / "source_files"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = source_dir / f"{_safe_filename(job_id, 'job')}_{source_name}"

    response = session.get(
        f"{server.rstrip('/')}/api/jobs/{job_id}/source",
        timeout=90,
        verify=verify_tls,
    )
    response.raise_for_status()
    source_path.write_bytes(response.content)
    return source_path


def _upload_job_artifact(
    session: requests.Session,
    server: str,
    job_id: str,
    agent_id: str,
    path: Path,
    artifact_type: str,
    *,
    verify_tls: bool,
) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"artifact file was not found: {path}")
    content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    with path.open("rb") as fp:
        response = session.post(
            f"{server.rstrip('/')}/api/agent/jobs/{job_id}/artifacts",
            data={"agent_id": agent_id, "artifact_type": artifact_type},
            files={"file": (path.name, fp, content_type)},
            timeout=180,
            verify=verify_tls,
        )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {}


def _heartbeat(agent_id: str, client_ip: str = "", print_mode: str = "default-printer", printer_name: str = "", erp_mode: str = "dry-run") -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "agent_host": socket.gethostname(),
        "agent_user": getpass.getuser(),
        "client_ip": client_ip,
        "capabilities": {
            "excel_voucher": True,
            "voucher_print": print_mode != "off",
            "printer_name": printer_name,
            "erp_mode": erp_mode,
        },
    }


def _tail_text(path: Path, max_lines: int = 160) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return ""
    return "\n".join(lines[-max(1, max_lines):])


def _latest_agent_log(output_dir: Path) -> dict[str, Any]:
    candidates = sorted(output_dir.glob("*_erp_input.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return {"message": "Agent ERP 입력 로그가 아직 없습니다.", "path": "", "tail": ""}
    latest = candidates[0]
    return {
        "message": "최신 Agent 로그를 가져왔습니다.",
        "path": str(latest),
        "modified_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(latest.stat().st_mtime)),
        "tail": _tail_text(latest),
    }


def _top_level_window_diagnostics() -> dict[str, Any]:
    """Return read-only top-level window metadata for ERP connection diagnosis."""
    snapshot: dict[str, Any] = {
        "agent_pid": os.getpid(),
        "user": getpass.getuser(),
        "backends": {},
    }
    try:
        import ctypes
        import psutil
        from pywinauto import Desktop
    except Exception as exc:
        snapshot["error"] = f"diagnostic imports failed: {exc}"
        return snapshot

    def _session_id(process_id: int) -> int | None:
        try:
            session_id = ctypes.c_uint(0)
            if ctypes.windll.kernel32.ProcessIdToSessionId(
                int(process_id), ctypes.byref(session_id)
            ):
                return int(session_id.value)
        except Exception:
            pass
        return None

    agent_session_id = _session_id(os.getpid())
    snapshot["agent_session_id"] = agent_session_id
    process_names: dict[int, str] = {}
    for backend in ("uia", "win32"):
        records: list[dict[str, Any]] = []
        try:
            windows = Desktop(backend=backend).windows()
        except Exception as exc:
            snapshot["backends"][backend] = {
                "error": f"top-level enumeration failed: {exc}",
                "windows": [],
            }
            continue
        for win in windows:
            try:
                visible = bool(win.is_visible())
                title = str(win.window_text() or "").strip()
                rect = win.rectangle()
                width = max(0, int(rect.right) - int(rect.left))
                height = max(0, int(rect.bottom) - int(rect.top))
                try:
                    process_id = int(win.process_id() or 0)
                except Exception:
                    process_id = int(
                        getattr(getattr(win, "element_info", None), "process_id", 0)
                        or 0
                    )
                if process_id not in process_names:
                    try:
                        process_names[process_id] = psutil.Process(process_id).name()
                    except Exception:
                        process_names[process_id] = ""
                try:
                    auto_id = str(
                        getattr(win.element_info, "automation_id", "") or ""
                    ).strip()
                except Exception:
                    auto_id = ""
                try:
                    class_name = str(win.class_name() or "").strip()
                except Exception:
                    class_name = ""
                records.append(
                    {
                        "title": title,
                        "automation_id": auto_id,
                        "class_name": class_name,
                        "process_id": process_id,
                        "process_name": process_names.get(process_id, ""),
                        "visible": visible,
                        "rect": [
                            int(rect.left),
                            int(rect.top),
                            int(rect.right),
                            int(rect.bottom),
                        ],
                        "width": width,
                        "height": height,
                    }
                )
            except Exception as exc:
                records.append({"error": str(exc)})
        records.sort(
            key=lambda item: (
                bool(item.get("visible")),
                int(item.get("width", 0)) * int(item.get("height", 0)),
            ),
            reverse=True,
        )
        snapshot["backends"][backend] = {
            "count": len(records),
            "windows": records[:80],
        }

    process_records: list[dict[str, Any]] = []
    likely_tokens = ("angkor", "ylw", "mainwin", "k-system", "ksystem")
    for proc in psutil.process_iter(["pid", "name", "username"]):
        try:
            process_id = int(proc.info.get("pid") or 0)
            process_name = str(proc.info.get("name") or "")
            username = str(proc.info.get("username") or "")
            session_id = _session_id(process_id)
            likely_erp = any(token in process_name.lower() for token in likely_tokens)
            other_interactive_session = (
                session_id is not None
                and agent_session_id is not None
                and session_id != agent_session_id
                and username
                and not username.upper().endswith(("SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE"))
            )
            if not likely_erp and not other_interactive_session:
                continue
            process_records.append(
                {
                    "process_id": process_id,
                    "process_name": process_name,
                    "username": username,
                    "session_id": session_id,
                    "likely_erp": likely_erp,
                }
            )
        except Exception:
            continue
    process_records.sort(
        key=lambda item: (
            not bool(item.get("likely_erp")),
            int(item.get("session_id") or -1),
            str(item.get("process_name") or "").lower(),
            int(item.get("process_id") or 0),
        )
    )
    snapshot["processes"] = process_records[:250]
    return snapshot


def _popen_hidden(args: list[str]) -> subprocess.Popen:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(args, creationflags=creationflags)


def _schedule_agent_restart(output_dir: Path, delay_seconds: int = 3) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    script = output_dir / f"restart_agent_{int(time.time())}.ps1"
    script.write_text(
        "\n".join(
            [
                '$TaskName = "Excel Voucher Agent"',
                f"Start-Sleep -Seconds {max(1, int(delay_seconds))}",
                'Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue',
                "Get-CimInstance Win32_Process |",
                '  Where-Object { $_.CommandLine -match "excel_voucher_web\\\\run_agent.ps1|agent_worker.py" } |',
                "  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }",
                "Start-Sleep -Seconds 1",
                'Start-ScheduledTask -TaskName $TaskName',
            ]
        ),
        encoding="utf-8",
    )
    _popen_hidden(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ]
    )
    return script


def _install_agent_task(
    *,
    server: str,
    agent_id: str,
    client_ip: str,
    verify_tls: bool,
    print_mode: str,
    printer_name: str,
    print_wait_seconds: float,
    erp_mode: str,
) -> dict[str, Any]:
    script = ROOT / "install_agent_task.ps1"
    if not script.exists():
        raise RuntimeError(f"install_agent_task.ps1 not found: {script}")
    args = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Server",
        server,
        "-AgentId",
        agent_id,
        "-ClientIp",
        client_ip,
        "-PrintMode",
        print_mode,
        "-PrinterName",
        printer_name,
        "-PrintWaitSeconds",
        str(print_wait_seconds),
        "-ErpMode",
        erp_mode,
    ]
    if not verify_tls:
        args.append("-InsecureSkipTlsVerify")
    install_timeout = max(120, int(os.getenv("EXCEL_VOUCHER_AGENT_INSTALL_TIMEOUT_SECONDS", "300") or "300"))
    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=install_timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "install_agent_task.ps1 failed").strip())
    return {"stdout": completed.stdout[-2000:], "stderr": completed.stderr[-2000:]}


def _update_agent_files(zip_url: str) -> dict[str, Any]:
    repo_root = ROOT.parent
    with tempfile.TemporaryDirectory(prefix="excel_voucher_update_") as temp_name:
        temp = Path(temp_name)
        zip_path = temp / "ERP_Auto_Finance.zip"
        download_timeout = max(180, int(os.getenv("EXCEL_VOUCHER_AGENT_UPDATE_DOWNLOAD_TIMEOUT_SECONDS", "300") or "300"))
        separator = "&" if "?" in zip_url else "?"
        download_url = f"{zip_url}{separator}cache_bust={int(time.time())}"
        response = requests.get(
            download_url,
            timeout=download_timeout,
            headers={"Cache-Control": "no-cache"},
        )
        response.raise_for_status()
        zip_path.write_bytes(response.content)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(temp)
        candidates = [
            path
            for path in temp.iterdir()
            if path.is_dir()
            and (path / "excel_voucher_web").is_dir()
            and (path / "manager_server").is_dir()
        ]
        if len(candidates) != 1:
            raise RuntimeError("GitHub ZIP 압축 해제 결과에서 재정 자동화 저장소 루트를 찾지 못했습니다.")
        extracted = candidates[0]
        manager_sources = list((extracted / "manager_server").glob("*v6.2.py"))
        if len(manager_sources) != 1:
            raise RuntimeError("업데이트 ZIP에서 ERP Manager 원본을 하나로 확정하지 못했습니다.")
        manager_source = manager_sources[0]
        expected_manager_sha256 = hashlib.sha256(manager_source.read_bytes()).hexdigest().upper()
        shutil.copytree(extracted / "excel_voucher_web", ROOT, dirs_exist_ok=True)
        shutil.copytree(extracted / "manager_server", repo_root / "manager_server", dirs_exist_ok=True)
        manager_target = repo_root / "manager_server" / manager_source.name
        actual_manager_sha256 = hashlib.sha256(manager_target.read_bytes()).hexdigest().upper()
        if actual_manager_sha256 != expected_manager_sha256:
            raise RuntimeError(
                "ERP Manager 파일 교체 검증 실패: "
                f"expected={expected_manager_sha256}, actual={actual_manager_sha256}"
            )
    return {
        "updated_root": str(repo_root),
        "zip_url": zip_url,
        "download_url": download_url,
        "manager_path": str(manager_target),
        "manager_sha256": actual_manager_sha256,
    }


def _execute_admin_command(
    command: dict[str, Any],
    *,
    server: str,
    agent_id: str,
    client_ip: str,
    verify_tls: bool,
    print_mode: str,
    printer_name: str,
    print_wait_seconds: float,
    erp_mode: str,
    output_dir: Path,
) -> dict[str, Any]:
    command_type = str(command.get("command") or "")
    payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
    if command_type == "tail-log":
        result = _latest_agent_log(output_dir)
        if payload.get("inspect_erp_windows") is True:
            result["top_level_windows"] = _top_level_window_diagnostics()
        return result
    if command_type == "restart-agent":
        script = _schedule_agent_restart(output_dir)
        return {"message": "Agent 재시작을 예약했습니다.", "restart_script": str(script)}
    if command_type == "update-agent":
        zip_url = str(payload.get("zip_url") or DEFAULT_REPO_ZIP_URL)
        update_result = _update_agent_files(zip_url)
        install_result = _install_agent_task(
            server=server,
            agent_id=agent_id,
            client_ip=client_ip,
            verify_tls=verify_tls,
            print_mode=print_mode,
            printer_name=printer_name,
            print_wait_seconds=print_wait_seconds,
            erp_mode=erp_mode,
        )
        script = _schedule_agent_restart(output_dir)
        return {
            "message": "Agent 최신 적용 후 재시작을 예약했습니다.",
            **update_result,
            "install": install_result,
            "restart_script": str(script),
        }
    raise RuntimeError(f"지원하지 않는 Agent 명령입니다: {command_type}")


def _tail_log_admin_loop(
    *,
    server: str,
    agent_id: str,
    client_ip: str,
    verify_tls: bool,
    print_mode: str,
    printer_name: str,
    print_wait_seconds: float,
    erp_mode: str,
    output_dir: Path,
    interval: int,
) -> None:
    session = requests.Session()
    while True:
        heartbeat = _heartbeat(agent_id, client_ip, print_mode, printer_name, erp_mode)
        heartbeat["capabilities"]["admin_commands"] = ["tail-log", "update-agent", "restart-agent"]
        heartbeat["capabilities"]["admin_worker"] = "background"
        try:
            _post(session, server, "/api/agent/heartbeat", heartbeat, verify_tls=verify_tls)
            admin_payload = _post(session, server, "/api/agent/admin/next", heartbeat, verify_tls=verify_tls)
            admin_command = admin_payload.get("command")
            if admin_command:
                command_id = str(admin_command.get("id") or "")
                try:
                    result = _execute_admin_command(
                        admin_command,
                        server=server,
                        agent_id=agent_id,
                        client_ip=client_ip,
                        verify_tls=verify_tls,
                        print_mode=print_mode,
                        printer_name=printer_name,
                        print_wait_seconds=print_wait_seconds,
                        erp_mode=erp_mode,
                        output_dir=output_dir,
                    )
                    _post(
                        session,
                        server,
                        f"/api/agent/admin/{command_id}/complete",
                        {"agent_id": agent_id, "ok": True, "result": result},
                        verify_tls=verify_tls,
                    )
                    print(f"admin background command completed {command_id}: {admin_command.get('command')}")
                except Exception as exc:
                    try:
                        _post(
                            session,
                            server,
                            f"/api/agent/admin/{command_id}/complete",
                            {"agent_id": agent_id, "ok": False, "error": str(exc)},
                            verify_tls=verify_tls,
                        )
                    except requests.RequestException as report_exc:
                        print(_connection_error_message(server, report_exc), file=sys.stderr)
                    print(f"admin background command failed {command_id}: {exc}", file=sys.stderr)
        except requests.RequestException as exc:
            print(_connection_error_message(server, exc), file=sys.stderr)
        except Exception as exc:
            print(f"admin background worker failed: {exc}", file=sys.stderr)
        time.sleep(max(2, interval))


def run_loop(
    server: str,
    agent_id: str,
    client_ip: str,
    interval: int,
    once: bool,
    verify_tls: bool,
    print_mode: str,
    printer_name: str,
    print_wait_seconds: float,
    erp_mode: str,
) -> None:
    if not verify_tls:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    session = requests.Session()
    output_dir = ROOT / "data" / "agent_results"
    if not once:
        threading.Thread(
            target=_tail_log_admin_loop,
            kwargs={
                "server": server,
                "agent_id": agent_id,
                "client_ip": client_ip,
                "verify_tls": verify_tls,
                "print_mode": print_mode,
                "printer_name": printer_name,
                "print_wait_seconds": print_wait_seconds,
                "erp_mode": erp_mode,
                "output_dir": output_dir,
                "interval": interval,
            },
            daemon=True,
        ).start()
    while True:
        heartbeat = _heartbeat(agent_id, client_ip, print_mode, printer_name, erp_mode)
        try:
            _post(session, server, "/api/agent/heartbeat", heartbeat, verify_tls=verify_tls)
            admin_payload = _post(session, server, "/api/agent/admin/next", heartbeat, verify_tls=verify_tls)
            admin_command = admin_payload.get("command")
            if admin_command:
                command_id = str(admin_command.get("id") or "")
                try:
                    result = _execute_admin_command(
                        admin_command,
                        server=server,
                        agent_id=agent_id,
                        client_ip=client_ip,
                        verify_tls=verify_tls,
                        print_mode=print_mode,
                        printer_name=printer_name,
                        print_wait_seconds=print_wait_seconds,
                        erp_mode=erp_mode,
                        output_dir=output_dir,
                    )
                    _post(
                        session,
                        server,
                        f"/api/agent/admin/{command_id}/complete",
                        {"agent_id": agent_id, "ok": True, "result": result},
                        verify_tls=verify_tls,
                    )
                    print(f"admin command completed {command_id}: {admin_command.get('command')}")
                except Exception as exc:
                    try:
                        _post(
                            session,
                            server,
                            f"/api/agent/admin/{command_id}/complete",
                            {"agent_id": agent_id, "ok": False, "error": str(exc)},
                            verify_tls=verify_tls,
                        )
                    except requests.RequestException as report_exc:
                        print(_connection_error_message(server, report_exc), file=sys.stderr)
                    print(f"admin command failed {command_id}: {exc}", file=sys.stderr)
                if once:
                    return
                time.sleep(interval)
                continue
            next_payload = _post(session, server, "/api/agent/voucher/next", heartbeat, verify_tls=verify_tls)
        except requests.RequestException as exc:
            print(_connection_error_message(server, exc), file=sys.stderr)
            if once:
                return
            time.sleep(interval)
            continue
        task = next_payload.get("task")
        if not task:
            if once:
                print("no task")
                return
            time.sleep(interval)
            continue

        job_id = str(task.get("id") or "")
        try:
            _post(
                session,
                server,
                f"/api/agent/jobs/{job_id}/event",
                {
                    "agent_id": agent_id,
                    "status": "running",
                    "progress": 35,
                    "message": "자동 전표처리 PC 자료 처리 시작",
                },
                verify_tls=verify_tls,
            )
            if erp_mode == "real":
                source_path = _download_job_source(
                    session,
                    server,
                    task,
                    output_dir,
                    verify_tls=verify_tls,
                )
                task = dict(task)
                task["source_file_path"] = str(source_path)
                _post(
                    session,
                    server,
                    f"/api/agent/jobs/{job_id}/event",
                    {
                        "agent_id": agent_id,
                        "status": "running",
                        "progress": 38,
                        "message": "업로드 원본 엑셀을 자동 전표처리 PC로 가져왔습니다.",
                    },
                    verify_tls=verify_tls,
                )
            result = run_erp_voucher_task(
                task,
                output_dir=output_dir,
                print_mode=print_mode,
                printer_name=printer_name,
                print_wait_seconds=print_wait_seconds,
                erp_mode=erp_mode,
            )
            if erp_mode == "real" and result.get("erp_saved"):
                _post(
                    session,
                    server,
                    f"/api/agent/jobs/{job_id}/event",
                    {
                        "agent_id": agent_id,
                        "status": "running",
                        "progress": 82,
                        "message": "ERP 전표 저장이 완료되었습니다.",
                    },
                    verify_tls=verify_tls,
                )
                pdf_path = Path(str(result.get("erp_pdf_path") or ""))
                _post(
                    session,
                    server,
                    f"/api/agent/jobs/{job_id}/event",
                    {
                        "agent_id": agent_id,
                        "status": "running",
                        "progress": 90,
                        "message": "ERP 전표 PDF를 서버에 보관 중입니다.",
                    },
                    verify_tls=verify_tls,
                )
                artifact_response = _upload_job_artifact(
                    session,
                    server,
                    job_id,
                    agent_id,
                    pdf_path,
                    "erp_pdf",
                    verify_tls=verify_tls,
                )
                artifact = artifact_response.get("artifact") if isinstance(artifact_response, dict) else {}
                if isinstance(artifact, dict):
                    result = {
                        **result,
                        "server_pdf_stored": True,
                        "erp_pdf_server_path": artifact.get("path") or "",
                        "erp_pdf_filename": artifact.get("filename") or "",
                        "erp_pdf_download_url": artifact.get("download_url") or "",
                    }
                if result.get("print_submitted"):
                    _post(
                        session,
                        server,
                        f"/api/agent/jobs/{job_id}/event",
                        {
                            "agent_id": agent_id,
                            "status": "running",
                            "progress": 96,
                            "message": "출력 요청이 완료되었습니다.",
                        },
                        verify_tls=verify_tls,
                    )
            if erp_mode == "real":
                log_path = Path(str(result.get("erp_log_path") or output_dir / f"{job_id}_erp_input.log"))
                if log_path.is_file():
                    try:
                        _upload_job_artifact(
                            session,
                            server,
                            job_id,
                            agent_id,
                            log_path,
                            "agent_log",
                            verify_tls=verify_tls,
                        )
                    except Exception as log_exc:
                        result = {**result, "agent_log_upload_error": str(log_exc)}
            _post(
                session,
                server,
                f"/api/agent/jobs/{job_id}/complete",
                {
                    "agent_id": agent_id,
                    "ok": True,
                    "message": result.get("message") or "자동 전표처리 PC 처리 완료",
                    "result": result,
                },
                verify_tls=verify_tls,
            )
            print(f"completed {job_id}")
        except Exception as exc:
            error_result: dict[str, Any] = {}
            log_path = output_dir / f"{job_id}_erp_input.log"
            if log_path.is_file():
                error_result["erp_log_path"] = str(log_path)
                try:
                    _upload_job_artifact(
                        session,
                        server,
                        job_id,
                        agent_id,
                        log_path,
                        "agent_log",
                        verify_tls=verify_tls,
                    )
                except Exception as log_exc:
                    error_result["agent_log_upload_error"] = str(log_exc)
            print_screenshot_path = output_dir / "erp_outputs" / f"{job_id}_print_timeout.png"
            if print_screenshot_path.is_file():
                error_result["print_screenshot_path"] = str(print_screenshot_path)
                try:
                    screenshot_response = _upload_job_artifact(
                        session,
                        server,
                        job_id,
                        agent_id,
                        print_screenshot_path,
                        "print_screenshot",
                        verify_tls=verify_tls,
                    )
                    artifact = (
                        screenshot_response.get("artifact")
                        if isinstance(screenshot_response, dict)
                        else {}
                    )
                    if isinstance(artifact, dict):
                        error_result.update(
                            {
                                "print_screenshot_server_path": artifact.get("path") or "",
                                "print_screenshot_filename": artifact.get("filename") or "",
                                "print_screenshot_download_url": artifact.get("download_url") or "",
                            }
                        )
                except Exception as screenshot_exc:
                    error_result["print_screenshot_upload_error"] = str(screenshot_exc)
            # 관리항목(거래처/계좌) 입력 실패 순간의 화면을 서버로 올려
            # 무인 PC라도 원격에서 실제 화면으로 원인을 확인할 수 있게 한다.
            try:
                mgmt_shot_dir = output_dir / "erp_outputs"
                mgmt_shots = (
                    sorted(
                        mgmt_shot_dir.glob("mgmt_fail_*.png"),
                        key=lambda p: p.stat().st_mtime,
                    )
                    if mgmt_shot_dir.is_dir()
                    else []
                )
                if mgmt_shots:
                    newest_mgmt_shot = mgmt_shots[-1]
                    error_result["mgmt_screenshot_path"] = str(newest_mgmt_shot)
                    mgmt_resp = _upload_job_artifact(
                        session,
                        server,
                        job_id,
                        agent_id,
                        newest_mgmt_shot,
                        "mgmt_screenshot",
                        verify_tls=verify_tls,
                    )
                    mgmt_artifact = (
                        mgmt_resp.get("artifact")
                        if isinstance(mgmt_resp, dict)
                        else {}
                    )
                    if isinstance(mgmt_artifact, dict):
                        error_result.update(
                            {
                                "mgmt_screenshot_filename": mgmt_artifact.get("filename") or "",
                                "mgmt_screenshot_download_url": mgmt_artifact.get("download_url") or "",
                            }
                        )
            except Exception as mgmt_shot_exc:
                error_result["mgmt_screenshot_upload_error"] = str(mgmt_shot_exc)
            try:
                _post(
                    session,
                    server,
                    f"/api/agent/jobs/{job_id}/complete",
                    {
                        "agent_id": agent_id,
                        "ok": False,
                        "message": "자동 전표처리 PC 처리 실패",
                        "result": error_result,
                        "error": str(exc),
                    },
                    verify_tls=verify_tls,
                )
            except requests.RequestException as report_exc:
                print(_connection_error_message(server, report_exc), file=sys.stderr)
            print(f"failed {job_id}: {exc}", file=sys.stderr)
        if once:
            return
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Excel voucher ERP agent worker")
    parser.add_argument("--server", default="http://127.0.0.1:18100")
    parser.add_argument("--agent-id", default="finance-agent-172-17-30-243")
    parser.add_argument("--client-ip", default="")
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--insecure-skip-tls-verify", action="store_true")
    parser.add_argument("--print-mode", choices=["default-printer", "off"], default="default-printer")
    parser.add_argument("--printer-name", default="")
    parser.add_argument("--print-wait-seconds", type=float, default=3.0)
    parser.add_argument("--erp-mode", choices=["dry-run", "real"], default="dry-run")
    args = parser.parse_args()
    printer_name = _normalize_printer_name(args.printer_name)
    run_loop(
        args.server,
        args.agent_id,
        args.client_ip,
        max(1, args.interval),
        args.once,
        not args.insecure_skip_tls_verify,
        args.print_mode,
        printer_name,
        max(0.0, args.print_wait_seconds),
        args.erp_mode,
    )


if __name__ == "__main__":
    main()
