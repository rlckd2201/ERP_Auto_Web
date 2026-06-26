from __future__ import annotations

import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .accounts import AccountStore, AccountUser, make_temporary_password
from .data_server import data_server_target_url, forward_job_to_data_server
from .groupware_directory import fetch_finance_users, groupware_enabled
from .models import (
    AgentCompleteRequest,
    AgentEventRequest,
    AgentHeartbeat,
    ChangePasswordRequest,
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
            current_location = "자동처리 PC가 아직 서버에 접속한 기록이 없습니다."
            recommended_action = "172.17.30.243에서 Agent 실행 여부와 서버 주소를 확인하세요."
        elif not agent_online:
            current_location = "자동처리 PC 연결이 끊겼거나 Agent가 멈춘 상태입니다."
            recommended_action = "172.17.30.243 PowerShell Agent 창을 확인하고 필요하면 다시 실행하세요."
        else:
            current_location = "자동처리 PC가 연결되어 있고 작업 가져가기를 기다리는 중입니다."
            recommended_action = "몇 초 후에도 진행되지 않으면 Agent 창의 오류 메시지를 확인하세요."
    elif job.status == "claimed":
        current_location = "자동처리 PC가 작업을 가져갔고 전표 처리 준비 중입니다."
        recommended_action = "진행률이 그대로면 172.17.30.243 Agent 창을 확인하세요."
    elif job.status == "running":
        current_location = "자동처리 PC에서 전표 자료 생성 또는 출력 처리가 진행 중입니다."
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
        **job.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in store.list_events(job_id)],
    }
    if include_diagnostics:
        response["diagnostics"] = _job_diagnostics(job)
    return response


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


@app.post("/api/uploads/voucher")
def api_upload_voucher(
    request: Request,
    file: UploadFile = File(...),
    accounting_date: str = Form(default=""),
    requester: str = Form(default=""),
    company_key: str = Form(default="daeseung"),
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
    return [job.model_dump(mode="json") for job in store.list_jobs(limit)]


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
        return store.get_job(job_id).payload
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
    return {"ok": bool(forward_result.get("ok")), "forward": forward_result, "job": updated.model_dump(mode="json")}


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
            "job_type": "excel_voucher",
            "download_url": f"/api/jobs/{job.id}/source",
            "voucher_url": f"/api/jobs/{job.id}/voucher",
        },
    }


@app.post("/api/agent/jobs/{job_id}/event")
def api_agent_job_event(job_id: str, event: AgentEventRequest) -> dict[str, Any]:
    try:
        job = store.update_job(
            job_id,
            status=event.status,
            progress=event.progress,
            message=event.message or "Agent 진행 중",
            result=event.result or None,
            error=event.error or None,
        )
        return {"ok": True, "job": job.model_dump(mode="json")}
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
        if complete.ok and complete.result.get("print_submitted"):
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
        return {"ok": True, "job": job.model_dump(mode="json")}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.") from exc
