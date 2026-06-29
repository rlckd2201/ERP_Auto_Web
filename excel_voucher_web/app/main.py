from __future__ import annotations

import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .accounts import AccountStore, AccountUser, make_temporary_password, protect_secret, unprotect_secret
from .data_server import data_server_target_url, forward_job_to_data_server
from .groupware_directory import fetch_finance_users, groupware_enabled
from .models import (
    AgentCompleteRequest,
    AgentAdminCommandCompleteRequest,
    AgentEventRequest,
    AgentHeartbeat,
    AdminAgentCommandRequest,
    AdminResetJobsRequest,
    ChangePasswordRequest,
    ErpCredentialRequest,
    ForgotPasswordRequest,
    LoginRequest,
)
from .notifications import notify_job_completed, notify_password_reset
from .settings import BASE_DIR, default_accounting_date, manager_profile, manager_profiles, settings
from .storage import JobStore
from .voucher_builder import build_voucher_payload


app = FastAPI(title="Excel Voucher Web")
store = JobStore(settings.db_path)
account_store = AccountStore(settings.db_path, initial_password=settings.initial_password)
STATIC_DIR = BASE_DIR / "app" / "static"
DEFAULT_REPO_ZIP_URL = "https://github.com/rlckd2201/ERP_Auto_Web/archive/refs/heads/main.zip"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _legacy_admin_user() -> dict[str, Any] | None:
    path = settings.legacy_auth_db_path
    if not path.exists():
        return None
    try:
        with sqlite3.connect(str(path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, name, pw, is_initial FROM users WHERE id = ?",
                (settings.admin_user_id,),
            ).fetchone()
    except sqlite3.Error:
        return None
    if not row or not row["pw"]:
        return None
    return {
        "user_id": str(row["id"]),
        "name": str(row["name"] or row["id"]),
        "password": str(row["pw"]),
        "must_change_password": bool(row["is_initial"]),
    }


def _sync_admin_user_from_legacy() -> None:
    legacy_admin = _legacy_admin_user()
    account_store.upsert_admin_user(
        user_id=(legacy_admin or {}).get("user_id") or settings.admin_user_id,
        name=(legacy_admin or {}).get("name") or settings.admin_name,
        password=(legacy_admin or {}).get("password") or settings.admin_password,
        email=settings.admin_email,
        must_change_password=bool((legacy_admin or {}).get("must_change_password", True)),
        overwrite_password=bool(legacy_admin),
    )


def _update_server_files(zip_url: str = DEFAULT_REPO_ZIP_URL) -> dict[str, Any]:
    repo_root = BASE_DIR.parent
    with tempfile.TemporaryDirectory(prefix="excel_voucher_server_update_") as temp_name:
        temp = Path(temp_name)
        zip_path = temp / "ERP_Auto_Web.zip"
        response = requests.get(zip_url, timeout=300)
        response.raise_for_status()
        zip_path.write_bytes(response.content)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(temp)
        extracted = temp / "ERP_Auto_Web-main"
        if not extracted.exists():
            raise RuntimeError("GitHub ZIP 압축 해제 결과에서 ERP_Auto_Web-main 폴더를 찾지 못했습니다.")
        shutil.copytree(extracted / "excel_voucher_web", BASE_DIR, dirs_exist_ok=True)
        manager_source = extracted / "manager_server"
        if manager_source.exists():
            shutil.copytree(manager_source, repo_root / "manager_server", dirs_exist_ok=True)
    return {
        "message": "서버 파일 최신 적용 완료. 실행 중인 서버 프로세스는 재시작 후 새 코드가 반영됩니다.",
        "updated_root": str(repo_root),
        "zip_url": zip_url,
    }


@app.on_event("startup")
def startup_sync_groupware_users() -> None:
    _sync_admin_user_from_legacy()
    if not settings.groupware_sync_on_start:
        return
    if not groupware_enabled():
        return
    for user in fetch_finance_users():
        account_store.upsert_groupware_user(user)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else ""


def _safe_filename(filename: str, fallback: str = "upload.xlsx") -> str:
    name = Path(filename or fallback).name.strip() or fallback
    blocked = '<>:"/\\|?*'
    clean = "".join("_" if ch in blocked else ch for ch in name)
    if not clean.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="xlsx 또는 xlsm 파일만 업로드할 수 있습니다.")
    return clean


def _seconds_since_iso(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return max(0, int((datetime.now() - datetime.fromisoformat(str(value))).total_seconds()))
    except ValueError:
        return None


def _job_diagnostics(job: Any) -> dict[str, Any]:
    profile = store.get_agent_profile(job.target_agent_id) if job.target_agent_id else None
    last_seen_age = _seconds_since_iso(profile.get("last_seen") if profile else None)
    agent_online = last_seen_age is not None and last_seen_age <= 20
    forward_result = (job.result or {}).get("data_server_forward") or {}

    if job.status == "queued":
        if not profile:
            current_location = "자동 전표처리 PC가 아직 서버에 접속한 기록이 없습니다."
            recommended_action = "172.17.30.243에서 Agent 프로그램 실행 여부와 서버 주소를 확인하세요."
        elif not agent_online:
            current_location = "자동 전표처리 PC 연결이 끊겼거나 Agent 프로그램이 멈춘 상태입니다."
            recommended_action = "172.17.30.243 PowerShell Agent 창을 확인하고 필요하면 다시 실행하세요."
        else:
            current_location = "자동 전표처리 PC가 연결되어 있고 작업 가져가기를 기다리는 중입니다."
            recommended_action = "몇 초 후에도 진행되지 않으면 Agent 창의 오류 메시지를 확인하세요."
    elif job.status == "claimed":
        current_location = "자동 전표처리 PC가 작업을 가져갔고 전표 처리 준비 중입니다."
        recommended_action = "진행률이 그대로면 172.17.30.243 자동 전표처리 PC의 Agent 창을 확인하세요."
    elif job.status == "running":
        current_location = "자동 전표처리 PC에서 전표 자료 생성 또는 출력 처리가 진행 중입니다."
        recommended_action = "진행률이 멈추면 Agent 창과 ERP 화면 상태를 확인하세요."
    elif job.status == "done":
        current_location = "출력 요청까지 완료되었습니다."
        recommended_action = "출력물과 완료 메일 수신 여부만 확인하면 됩니다."
    elif job.status == "error":
        current_location = "처리 중 오류가 발생했습니다."
        recommended_action = job.error or "작업 상세 로그와 Agent 창 오류를 확인하세요."
    else:
        current_location = "작업 상태 확인이 필요합니다."
        recommended_action = "작업 로그를 확인하세요."

    if forward_result and not forward_result.get("ok"):
        recommended_action += " 18080 데이터 서버 전달은 실패했지만 서버 큐에는 보관되어 있습니다."

    return {
        "current_location": current_location,
        "recommended_action": recommended_action,
        "target_agent_id": job.target_agent_id,
        "target_client_ip": job.target_client_ip,
        "agent_profile": profile,
        "agent_online": agent_online,
        "agent_last_seen_age_seconds": last_seen_age,
        "data_server_forward": forward_result,
    }


def _job_response(job_id: str, *, include_diagnostics: bool = False) -> dict[str, Any]:
    job = store.get_job(job_id)
    response = {
        **_public_job_dump(job),
        "events": [event.model_dump(mode="json") for event in store.list_events(job_id)],
    }
    if include_diagnostics:
        response["diagnostics"] = _job_diagnostics(job)
    return response


def _public_payload(payload: dict[str, Any]) -> dict[str, Any]:
    public = dict(payload or {})
    credentials = public.get("erp_credentials")
    if isinstance(credentials, dict):
        public["erp_credentials"] = {
            "user_id": credentials.get("user_id") or "",
            "saved": bool(credentials.get("password_blob") or credentials.get("password")),
        }
    return public


def _public_job_dump(job: Any) -> dict[str, Any]:
    data = job.model_dump(mode="json")
    data["payload"] = _public_payload(data.get("payload") or {})
    return data


def _form_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _credential_payload(user_id: str, password: str, *, source: str) -> dict[str, str]:
    user_id = str(user_id or "").strip()
    password = str(password or "")
    if not user_id or not password:
        raise HTTPException(status_code=400, detail="ERP 계정과 비밀번호를 입력해 주세요.")
    return {
        "user_id": user_id,
        "password_blob": protect_secret(password),
        "source": source,
    }


def _resolve_erp_credentials_for_upload(
    *,
    user: AccountUser | None,
    company_key: str,
    erp_user_id: str,
    erp_password: str,
    use_saved: bool,
    remember: bool,
) -> dict[str, str]:
    if use_saved:
        if not user:
            raise HTTPException(status_code=401, detail="저장된 ERP 계정을 사용하려면 로그인이 필요합니다.")
        saved = account_store.get_erp_credential(user.user_id, company_key)
        if not saved:
            raise HTTPException(status_code=400, detail="저장된 ERP 계정이 없습니다. ERP 계정을 입력해 주세요.")
        return _credential_payload(saved["user_id"], saved["password"], source="saved")

    erp_user_id = str(erp_user_id or "").strip()
    erp_password = str(erp_password or "")
    if not erp_user_id or not erp_password:
        raise HTTPException(status_code=400, detail="ERP 계정과 비밀번호를 입력해 주세요.")
    if remember and user:
        account_store.save_erp_credential(user.user_id, company_key, erp_user_id, erp_password)
    return _credential_payload(erp_user_id, erp_password, source="input")


def _agent_payload(payload: dict[str, Any]) -> dict[str, Any]:
    agent_payload = dict(payload or {})
    credentials = agent_payload.get("erp_credentials")
    if isinstance(credentials, dict):
        password = str(credentials.get("password") or "")
        if not password and credentials.get("password_blob"):
            password = unprotect_secret(str(credentials.get("password_blob") or ""))
        agent_payload["erp_credentials"] = {
            "user_id": str(credentials.get("user_id") or ""),
            "password": password,
            "source": str(credentials.get("source") or ""),
        }
    return agent_payload


def _current_user(request: Request) -> AccountUser | None:
    token = request.cookies.get(settings.session_cookie_name, "")
    return account_store.user_for_session(token)


def _require_user(request: Request) -> AccountUser:
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    if not user.active:
        raise HTTPException(status_code=403, detail="비활성 계정입니다.")
    return user


def _require_admin(request: Request) -> AccountUser:
    user = _require_user(request)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="전산 관리자만 사용할 수 있습니다.")
    return user


def _auth_status(request: Request) -> dict[str, Any]:
    user = _current_user(request)
    return {
        "auth_required": settings.auth_required,
        "authenticated": bool(user),
        "user": user.public_dict() if user else None,
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/settings")
def api_settings(request: Request) -> dict[str, Any]:
    profiles = manager_profiles()
    return {
        "default_accounting_date": default_accounting_date(),
        "managers": [profile.__dict__ for profile in profiles.values()],
        "target_agent_id": settings.target_agent_id,
        "target_agent_ip": settings.target_agent_ip,
        "web_public_origin": settings.web_public_origin,
        "data_server_url": settings.data_server_url,
        "data_server_endpoint": settings.data_server_endpoint,
        "data_server_target_url": data_server_target_url(),
        "forward_to_data_server": settings.forward_to_data_server,
        "auth": _auth_status(request),
    }


@app.get("/api/auth/status")
def api_auth_status(request: Request) -> dict[str, Any]:
    return _auth_status(request)


@app.post("/api/auth/login")
def api_auth_login(payload: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
    if payload.user_id.strip() == settings.admin_user_id:
        _sync_admin_user_from_legacy()
    user = account_store.authenticate(payload.user_id, payload.password)
    if not user and groupware_enabled():
        for groupware_user in fetch_finance_users():
            account_store.upsert_groupware_user(groupware_user)
        user = account_store.authenticate(payload.user_id, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="ID 또는 비밀번호가 맞지 않습니다.")
    token = account_store.create_session(user.user_id)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )
    return {"ok": True, "user": user.public_dict()}


@app.post("/api/auth/logout")
def api_auth_logout(request: Request, response: Response) -> dict[str, Any]:
    account_store.delete_session(request.cookies.get(settings.session_cookie_name, ""))
    response.delete_cookie(settings.session_cookie_name)
    return {"ok": True}


@app.post("/api/auth/change-password")
def api_auth_change_password(payload: ChangePasswordRequest, request: Request) -> dict[str, Any]:
    user = _require_user(request)
    if payload.new_password == settings.initial_password:
        raise HTTPException(status_code=400, detail="초기 비밀번호와 다른 비밀번호를 사용해 주세요.")
    if not account_store.change_password(user.user_id, payload.old_password, payload.new_password):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 맞지 않습니다.")
    return {"ok": True, "user": account_store.get_user(user.user_id).public_dict()}


@app.post("/api/auth/forgot-password")
def api_auth_forgot_password(payload: ForgotPasswordRequest) -> dict[str, Any]:
    user_id = payload.user_id.strip()
    if groupware_enabled():
        for groupware_user in fetch_finance_users():
            account_store.upsert_groupware_user(groupware_user)
    temporary_password = make_temporary_password()
    user = account_store.set_temporary_password(user_id, temporary_password)
    if not user:
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다.")
    mail_result = notify_password_reset(user.email, user.user_id, temporary_password)
    return {"ok": True, "mail": mail_result}


@app.get("/api/erp-credentials/{company_key}")
def api_erp_credential_status(company_key: str, request: Request) -> dict[str, Any]:
    user = _require_user(request)
    manager = manager_profile(company_key)
    meta = account_store.get_erp_credential_meta(user.user_id, manager.key)
    return {
        "saved": bool(meta),
        "company_key": manager.key,
        "company_name": manager.company_name,
        "erp_user_id": (meta or {}).get("erp_user_id", ""),
        "updated_at": (meta or {}).get("updated_at", ""),
    }


@app.post("/api/erp-credentials/{company_key}")
def api_save_erp_credential(company_key: str, payload: ErpCredentialRequest, request: Request) -> dict[str, Any]:
    user = _require_user(request)
    manager = manager_profile(company_key)
    if not manager.enabled:
        raise HTTPException(status_code=400, detail=f"{manager.company_name} 전표 처리는 개발 예정입니다.")
    account_store.save_erp_credential(user.user_id, manager.key, payload.erp_user_id, payload.erp_password)
    meta = account_store.get_erp_credential_meta(user.user_id, manager.key)
    return {"ok": True, "credential": meta}


@app.post("/api/uploads/voucher")
def api_upload_voucher(
    request: Request,
    file: UploadFile = File(...),
    accounting_date: str = Form(default=""),
    requester: str = Form(default=""),
    company_key: str = Form(default="daeseung"),
    erp_user_id: str = Form(default=""),
    erp_password: str = Form(default=""),
    use_saved_erp_credentials: str = Form(default="0"),
    remember_erp_credentials: str = Form(default="1"),
) -> dict[str, Any]:
    user = _current_user(request)
    if settings.auth_required and not user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    if settings.auth_required and user and user.must_change_password:
        raise HTTPException(status_code=403, detail="비밀번호 변경 후 업로드할 수 있습니다.")
    if user and not user.is_admin:
        company_key = user.company_key or company_key
        requester = user.name or user.user_id
    elif user:
        requester = user.name or user.user_id
    manager = manager_profile(company_key)
    if not manager.enabled:
        raise HTTPException(
            status_code=400,
            detail=f"{manager.company_name} 전표 처리는 개발 예정입니다. {manager.disabled_reason}".strip(),
        )
    erp_credentials = _resolve_erp_credentials_for_upload(
        user=user,
        company_key=manager.key,
        erp_user_id=erp_user_id,
        erp_password=erp_password,
        use_saved=_form_bool(use_saved_erp_credentials),
        remember=_form_bool(remember_erp_credentials),
    )
    filename = _safe_filename(file.filename or "upload.xlsx")
    accounting_date = (accounting_date or default_accounting_date()).strip()
    requester = (requester or "담당자").strip()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    temp_path = settings.upload_dir / f"_incoming_{filename}"
    try:
        with temp_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        payload = build_voucher_payload(
            temp_path,
            accounting_date=accounting_date,
            requester=requester,
            source_filename=filename,
            manager=manager,
        )
        payload = payload.model_copy(update={"erp_credentials": erp_credentials})
        if user:
            payload = payload.model_copy(
                update={
                    "requester_id": user.user_id,
                    "requester_email": user.email,
                    "requester": user.name or user.user_id,
                }
            )
        job_path = settings.upload_dir / f"{payload.company_key}_{payload.accounting_date}_{temp_path.name}".replace(":", "_")
        if job_path.exists():
            job_path = settings.upload_dir / f"{payload.company_key}_{payload.accounting_date}_{uuid.uuid4().hex[:8]}_{filename}"
        temp_path.replace(job_path)
        job = store.create_job(payload=payload, source_path=job_path, manager=manager)
        if settings.forward_to_data_server:
            forward_result = forward_job_to_data_server(job)
            message = "데이터 서버 전달 완료" if forward_result.get("ok") else "데이터 서버 전달 실패, 서버 큐에는 보관됨"
            job = store.update_job(
                job.id,
                progress=10 if forward_result.get("ok") else 7,
                message=message,
                result={**job.result, "data_server_forward": forward_result},
            )
    except HTTPException:
        raise
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _job_response(job.id, include_diagnostics=bool(user and user.is_admin))


@app.get("/api/jobs")
def api_jobs(limit: int = 100) -> list[dict[str, Any]]:
    return [_public_job_dump(job) for job in store.list_jobs(limit)]


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str, request: Request) -> dict[str, Any]:
    try:
        user = _current_user(request)
        return _job_response(job_id, include_diagnostics=bool(user and user.is_admin))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.") from exc


@app.get("/api/jobs/{job_id}/voucher")
def api_job_voucher(job_id: str) -> dict[str, Any]:
    try:
        return _public_payload(store.get_job(job_id).payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.") from exc


@app.get("/api/jobs/{job_id}/source")
def api_job_source(job_id: str) -> FileResponse:
    try:
        path = store.get_source_path(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="원본 파일이 없습니다.")
    return FileResponse(path, filename=path.name)


@app.post("/api/jobs/{job_id}/forward")
def api_forward_job(job_id: str) -> dict[str, Any]:
    try:
        job = store.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.") from exc
    forward_result = forward_job_to_data_server(job)
    message = "데이터 서버 전달 완료" if forward_result.get("ok") else "데이터 서버 전달 실패"
    updated = store.update_job(
        job_id,
        progress=12 if forward_result.get("ok") else job.progress,
        message=message,
        result={**job.result, "data_server_forward": forward_result},
    )
    return {"ok": bool(forward_result.get("ok")), "forward": forward_result, "job": _public_job_dump(updated)}


@app.get("/api/admin/agent-commands")
def api_admin_agent_commands(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return {"ok": True, "commands": store.list_agent_commands(10)}


@app.post("/api/admin/jobs/reset")
def api_admin_reset_jobs(payload: AdminResetJobsRequest, request: Request) -> dict[str, Any]:
    _require_admin(request)
    cleared = store.clear_jobs()
    upload_count = 0
    if payload.clear_uploads and settings.upload_dir.exists():
        for item in settings.upload_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
            upload_count += 1
    return {"ok": True, "cleared": {**cleared, "uploads": upload_count}}


@app.post("/api/admin/server-update")
def api_admin_server_update(request: Request) -> dict[str, Any]:
    _require_admin(request)
    try:
        result = _update_server_files()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"서버 최신 적용 실패: {exc}") from exc
    return {"ok": True, "result": result}


@app.post("/api/admin/agent-commands")
def api_admin_create_agent_command(payload: AdminAgentCommandRequest, request: Request) -> dict[str, Any]:
    user = _require_admin(request)
    target_agent_id = payload.target_agent_id.strip() or settings.target_agent_id
    command = store.create_agent_command(
        command=payload.command,
        target_agent_id=target_agent_id,
        payload=payload.payload,
        created_by=user.user_id,
    )
    return {"ok": True, "command": command}


@app.post("/api/agent/heartbeat")
def api_agent_heartbeat(heartbeat: AgentHeartbeat, request: Request) -> dict[str, Any]:
    profile = store.record_heartbeat(heartbeat, _client_ip(request))
    return {"ok": True, "profile": profile}


@app.post("/api/agent/voucher/next")
def api_agent_next(heartbeat: AgentHeartbeat, request: Request) -> dict[str, Any]:
    store.record_heartbeat(heartbeat, _client_ip(request))
    job = store.claim_next(heartbeat, _client_ip(request))
    if not job:
        return {"ok": True, "task": None}
    return {
        "ok": True,
        "task": {
            **job.model_dump(mode="json"),
            "payload": _agent_payload(job.payload),
            "job_type": "excel_voucher",
            "download_url": f"/api/jobs/{job.id}/source",
            "voucher_url": f"/api/jobs/{job.id}/voucher",
        },
    }


@app.post("/api/agent/admin/next")
def api_agent_admin_next(heartbeat: AgentHeartbeat, request: Request) -> dict[str, Any]:
    store.record_heartbeat(heartbeat, _client_ip(request))
    command = store.claim_next_agent_command(heartbeat, _client_ip(request))
    return {"ok": True, "command": command}


@app.post("/api/agent/admin/{command_id}/complete")
def api_agent_admin_complete(command_id: str, complete: AgentAdminCommandCompleteRequest) -> dict[str, Any]:
    try:
        command = store.complete_agent_command(
            command_id,
            ok=complete.ok,
            result=complete.result,
            error=complete.error,
        )
        return {"ok": True, "command": command}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Agent 명령을 찾을 수 없습니다.") from exc


@app.post("/api/agent/jobs/{job_id}/event")
def api_agent_job_event(job_id: str, event: AgentEventRequest) -> dict[str, Any]:
    try:
        job = store.update_job(
            job_id,
            status=event.status,
            progress=event.progress,
            message=event.message or "자동 전표처리 PC 진행 중",
            result=event.result or None,
            error=event.error or None,
        )
        return {"ok": True, "job": _public_job_dump(job)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.") from exc


@app.post("/api/agent/jobs/{job_id}/complete")
def api_agent_job_complete(job_id: str, complete: AgentCompleteRequest) -> dict[str, Any]:
    try:
        status = "done" if complete.ok else "error"
        message = complete.message or ("ERP 전표 처리 완료" if complete.ok else "ERP 전표 처리 실패")
        job = store.update_job(
            job_id,
            status=status,
            progress=100 if complete.ok else 95,
            message=message,
            result=complete.result,
            error="" if complete.ok else complete.error,
            finished=True,
        )
        if (
            complete.ok
            and complete.result.get("erp_saved")
            and complete.result.get("voucher_no")
            and complete.result.get("print_submitted")
        ):
            try:
                notification = notify_job_completed(job)
            except Exception as exc:
                notification = {"sent": False, "queued": False, "error": str(exc)}
            job = store.update_job(
                job_id,
                status=status,
                progress=100,
                message=message,
                result={**job.result, "notification": notification},
            )
        return {"ok": True, "job": _public_job_dump(job)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.") from exc
