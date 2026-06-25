from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data_server import data_server_target_url, forward_job_to_data_server
from .models import AgentCompleteRequest, AgentEventRequest, AgentHeartbeat
from .settings import BASE_DIR, default_accounting_date, manager_profile, manager_profiles, settings
from .storage import JobStore
from .voucher_builder import build_voucher_payload


app = FastAPI(title="Excel Voucher Web")
store = JobStore(settings.db_path)
STATIC_DIR = BASE_DIR / "app" / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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


def _job_response(job_id: str) -> dict[str, Any]:
    job = store.get_job(job_id)
    return {
        **job.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in store.list_events(job_id)],
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/settings")
def api_settings() -> dict[str, Any]:
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
    }


@app.post("/api/uploads/voucher")
def api_upload_voucher(
    file: UploadFile = File(...),
    accounting_date: str = Form(default=""),
    requester: str = Form(default=""),
    company_key: str = Form(default="daeseung"),
) -> dict[str, Any]:
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
    return _job_response(job.id)


@app.get("/api/jobs")
def api_jobs(limit: int = 100) -> list[dict[str, Any]]:
    return [job.model_dump(mode="json") for job in store.list_jobs(limit)]


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str) -> dict[str, Any]:
    try:
        return _job_response(job_id)
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
        return {"ok": True, "job": job.model_dump(mode="json")}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.") from exc
