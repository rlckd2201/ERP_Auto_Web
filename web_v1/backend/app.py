from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import re
import shutil
import sqlite3
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent_queue import claim_next_erp_task, update_erp_task
from .approval_fetcher import fetch_approval_documents
from .compuzone_quote import auto_attach_compuzone_quote
from .config import WEB_ROOT, settings
from .invoice_db import DONE, ERROR, PROCESSING, WAITING, add_invoice_log, delete_invoice, get_invoice, init_db, insert_manual_invoice, learn_dictionary_items, list_invoice_logs, list_invoices, normalize_processor, reset_invoice, set_invoice_status, update_invoice_json, update_invoice_pdf_path
from .job_store import job_store
from .models import InvoiceIdsRequest, JobCreateRequest, JobResponse, OutputSetRequest, PurchaseAnalysisUpdate, RegularDataUpdate
from .notifications import notify_regular_auto_result
from .output_set import build_output_set_status, generate_expense_report_pdf
from .regular_due_monitor import regular_due_history, regular_due_status, send_regular_due_report, start_regular_due_scheduler
from .erp_queue import queue_dir, write_expense_report_queue
from .erp_runner import build_regular_erp_payload
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
    change_initial_password,
    claim_install_job,
    complete_install_job,
    create_install_job,
    ensure_auto_install_job,
    find_installer,
    init_auth_db,
    init_setup_db,
    latest_agent_profile,
    record_agent_heartbeat,
    request_password_reset_code,
    reset_password_with_code,
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
UPDATE_NOTES_PATH = WEB_ROOT / "backend" / "UPDATE_NOTES.txt"
_MAIL_COLLECT_INTERVAL_SECONDS = 60
_mail_collect_scheduler_started = False
_mail_collect_scheduler_lock = threading.RLock()
_mail_collect_last_job_id = ""
_REGULAR_AUTO_AGENT_MAX_AGE_SECONDS = 120
_regular_auto_scheduler_started = False
_regular_auto_scheduler_lock = threading.RLock()
_regular_auto_last_job_id = ""


def _invoice_data(invoice: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(invoice, dict):
        return {}
    data = invoice.get("data")
    merged = dict(invoice)
    if isinstance(data, dict):
        merged.update(data)
    return merged


def _edit_text(value: Any) -> str:
    return str(value or "").strip()


def _edit_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value or "").strip()
    if not text:
        return 0
    text = "".join(ch for ch in text if ch.isdigit() or ch == "-")
    try:
        return int(text or 0)
    except Exception:
        return 0


def _edit_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _record_regular_auto_mail_result(job_id: str, invoice_ids: list[int], result: dict[str, Any], phase: str) -> None:
    if not job_id or not isinstance(result, dict) or result.get("skipped"):
        return
    if result.get("ok"):
        message = f"regular auto result email sent ({phase}): {result.get('to') or settings.regular_auto_result_email}"
        level = "info"
    else:
        message = f"regular auto result email failed ({phase}): {result.get('error') or result.get('reason') or 'unknown'}"
        level = "error"
    job = job_store.get(job_id)
    if job:
        job_store.add_event(job_id, job.status, job.progress, message)
    for invoice_id in invoice_ids:
        add_invoice_log(invoice_id, message, level=level, job_id=job_id)

def _start_purchase_approval_fetch_background(invoice_id: int, quote_path: str) -> bool:
    quote_path = str(quote_path or "").strip()
    if not quote_path:
        return False
    invoice = get_invoice(invoice_id)
    data = _invoice_data(invoice)
    existing_paths = [str(path) for path in data.get("approval_pdf_paths") or [] if str(path or "").strip()]
    if any(Path(path).exists() for path in existing_paths):
        return False
    if str(data.get("approval_fetch_status") or "").strip().lower() == "running":
        return False

    def _worker() -> None:
        update_invoice_json(
            invoice_id,
            {
                "approval_fetch_status": "running",
                "approval_fetch_error": "",
                "approval_fetch_started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            message="전자결재 품의 자동 확보 시작",
        )
        try:
            payload = fetch_approval_documents(
                invoice_id,
                quote_path,
                progress=lambda message: add_invoice_log(invoice_id, f"[품의] {message}"),
            )
            update_invoice_json(
                invoice_id,
                {
                    **payload,
                    "approval_fetch_status": "done",
                    "approval_fetch_error": "",
                    "approval_fetch_finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "erp_ready": True,
                },
                message=f"전자결재 품의 자동 확보 완료: {len(payload.get('approval_pdf_paths') or [])}건",
            )
        except Exception as exc:
            update_invoice_json(
                invoice_id,
                {
                    "approval_fetch_status": "error",
                    "approval_fetch_error": str(exc),
                    "approval_fetch_finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "erp_ready": True,
                },
                message=f"전자결재 품의 자동 확보 실패: {exc}",
            )

    threading.Thread(target=_worker, name=f"approval-fetch-{invoice_id}", daemon=True).start()
    return True

def _purchase_edit_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for source in data.get("items") or []:
        if not isinstance(source, dict):
            continue
        items.append(
            {
                "account": _edit_text(source.get("account")),
                "dept": _edit_text(source.get("dept") or source.get("department")),
                "name": _edit_text(source.get("name") or source.get("item_name")),
                "qty": _edit_int(source.get("qty") or source.get("quantity")),
                "supply": _edit_int(source.get("supply") or source.get("supply_amount")),
                "inc_vat": _edit_int(source.get("inc_vat") or source.get("total") or source.get("amount")),
            }
        )
    return {
        "site_name": _edit_text(data.get("site_name")),
        "vendor_name": _edit_text(data.get("vendor_name")),
        "invoice_date": _edit_text(data.get("invoice_date")),
        "order_no": _edit_text(data.get("order_no")),
        "target_supply": _edit_int(data.get("target_supply")),
        "total_tax": _edit_int(data.get("total_tax")),
        "total_sum": _edit_int(data.get("total_sum")),
        "approval_pdf_paths": tuple(sorted(_edit_text(path) for path in data.get("approval_pdf_paths") or [] if _edit_text(path))),
        "items": items,
    }


def _regular_edit_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for source in data.get("items") or []:
        if not isinstance(source, dict):
            continue
        items.append(
            {
                "account": _edit_text(source.get("account")),
                "account_manual": _edit_bool(source.get("account_manual") or source.get("manual_account")),
                "name": _edit_text(source.get("name") or source.get("item_name")),
                "qty": _edit_int(source.get("qty") or source.get("quantity")),
                "supply": _edit_int(source.get("supply") or source.get("supply_amount")),
                "inc_vat": _edit_int(source.get("inc_vat") or source.get("total") or source.get("amount")),
            }
        )
    return {
        "site_name": _edit_text(data.get("site_name")),
        "vendor_name": _edit_text(data.get("vendor_name")),
        "invoice_date": _edit_text(data.get("invoice_date")),
        "target_supply": _edit_int(data.get("target_supply")),
        "total_tax": _edit_int(data.get("total_tax")),
        "total_sum": _edit_int(data.get("total_sum")),
        "items": items,
    }


def _expense_report_exists(invoice: dict[str, Any] | None) -> bool:
    data = _invoice_data(invoice)
    path = str(data.get("expense_report_pdf_path") or "").strip()
    return bool(path and Path(path).exists())


def _invoice_output_set_ready(invoice: dict[str, Any] | None, expected_type: str = "") -> bool:
    invoice_type = str((invoice or {}).get("invoice_type") or "").lower()
    if not invoice:
        return False
    if expected_type and invoice_type != expected_type:
        return False
    status = build_output_set_status(invoice, persist=True)
    return bool(status.get("ready")) and not status.get("blockers")


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


def _output_print_task(job_id: str) -> dict[str, Any]:
    path = queue_dir() / f"output_print_{job_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="출력 큐 파일을 찾을 수 없습니다.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"출력 큐 파일을 읽을 수 없습니다: {exc}") from exc
    if str(payload.get("job_type") or "") != "output_print":
        raise HTTPException(status_code=404, detail="출력 큐 작업이 아닙니다.")
    return payload if isinstance(payload, dict) else {}


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


def _regular_auto_age_seconds(value: Any) -> int | None:
    try:
        return int((datetime.now() - datetime.fromisoformat(str(value))).total_seconds())
    except Exception:
        return None


def _regular_auto_printer_key() -> str:
    key = str(settings.regular_auto_printer_key or "pyeongtaek").strip().lower()
    if key != "pyeongtaek":
        logging.warning("REGULAR_AUTO_PRINTER_KEY=%s ignored; regular auto output is fixed to pyeongtaek", key)
    return "pyeongtaek"


def _regular_auto_target_profile() -> dict[str, Any] | None:
    target_ip = str(settings.regular_auto_agent_ip or "").strip()
    if not settings.regular_auto_enabled or not target_ip:
        return None
    profile = latest_agent_profile(client_ip=target_ip)
    if not profile or not str(profile.get("agent_id") or "").strip():
        return None
    age = _regular_auto_age_seconds(profile.get("last_seen"))
    if age is None or age > _REGULAR_AUTO_AGENT_MAX_AGE_SECONDS:
        return None
    return profile


def _regular_auto_printer_name(profile: dict[str, Any], printer_key: str) -> str:
    mapping = profile.get("printer_mapping") if isinstance(profile.get("printer_mapping"), dict) else {}
    printer_name = str(mapping.get(printer_key) or "").strip()
    if printer_name:
        return printer_name
    capabilities = profile.get("capabilities") if isinstance(profile.get("capabilities"), dict) else {}
    setup = capabilities.get("setup") if isinstance(capabilities.get("setup"), dict) else {}
    setup_mapping = setup.get("printer_mapping") if isinstance(setup.get("printer_mapping"), dict) else {}
    printer_name = str(setup_mapping.get(printer_key) or "").strip()
    if printer_name:
        return printer_name
    return str(settings.print_target_pyeongtaek or "평택 프린터 (172.16.10.172)").strip()


def _regular_auto_normalize_path(value: Any) -> str:
    text = str(value or "").strip().strip('"')
    if not text:
        return ""
    return re.sub(r"[\\/]+", r"\\", text).lower()


def _regular_auto_clean_number(value: Any) -> str:
    text = re.sub(r"[^0-9A-Za-z]", "", str(value or "")).upper()
    return text if len(text) >= 8 else ""


def _regular_auto_is_number_key(key: Any) -> bool:
    raw = str(key or "")
    compact = re.sub(r"[\s_\-:]+", "", raw).lower()
    markers = (
        "approvalno",
        "approvalnumber",
        "invoiceno",
        "invoicenumber",
        "taxinvoiceno",
        "taxinvoicenumber",
        "issueid",
        "issueno",
        "serialno",
        "serialnumber",
    )
    return (
        any(marker in compact for marker in markers)
        or ("승인" in raw and "번호" in raw)
        or ("일련" in raw and "번호" in raw)
    )


def _regular_auto_xml_issue_id(path: str) -> str:
    try:
        import xml.etree.ElementTree as ET

        xml_path = Path(path)
        if not xml_path.exists() or not xml_path.is_file():
            return ""
        root = ET.parse(str(xml_path)).getroot()
        for node in root.iter():
            local_name = str(node.tag).rsplit("}", 1)[-1]
            if local_name == "IssueID":
                return _regular_auto_clean_number(node.text)
    except Exception:
        return ""
    return ""


def _regular_auto_number_values(value: Any, *, depth: int = 0) -> set[str]:
    if depth > 6:
        return set()
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if _regular_auto_is_number_key(key):
                number = _regular_auto_clean_number(item)
                if number:
                    found.add(number)
            if isinstance(item, (dict, list)):
                found.update(_regular_auto_number_values(item, depth=depth + 1))
    elif isinstance(value, list):
        for item in value:
            found.update(_regular_auto_number_values(item, depth=depth + 1))
    return found


def _regular_auto_path_values(value: Any, *, depth: int = 0) -> set[str]:
    if depth > 6:
        return set()
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key or "").lower()
            if isinstance(item, str):
                text = item.strip()
                lower = text.lower()
                if ("path" in key_text or lower.endswith((".pdf", ".xml"))) and lower.endswith((".pdf", ".xml")):
                    path = _regular_auto_normalize_path(text)
                    if path:
                        found.add(path)
            if isinstance(item, (dict, list)):
                found.update(_regular_auto_path_values(item, depth=depth + 1))
    elif isinstance(value, list):
        for item in value:
            found.update(_regular_auto_path_values(item, depth=depth + 1))
    return found


def _regular_auto_dedupe_keys(invoice: dict[str, Any]) -> set[str]:
    data = _invoice_data(invoice)
    raw = invoice.get("raw") if isinstance(invoice.get("raw"), dict) else {}
    root = {"invoice": invoice, "raw": raw, "data": data}
    keys: set[str] = set()
    invoice_id = int(invoice.get("id") or 0)
    if invoice_id:
        keys.add(f"id:{invoice_id}")
    for number in _regular_auto_number_values(root):
        keys.add(f"number:{number}")
    for path in _regular_auto_path_values(root):
        keys.add(f"path:{path}")
        if path.endswith(".xml"):
            number = _regular_auto_xml_issue_id(path)
            if number:
                keys.add(f"number:{number}")
    return keys


def _regular_auto_output_ready(invoice: dict[str, Any]) -> bool:
    try:
        status = build_output_set_status(invoice, persist=False)
        return bool(status.get("ready")) and not status.get("blockers")
    except Exception:
        return False


def _regular_auto_mark_skip(invoice: dict[str, Any], reason: str, detail: str) -> None:
    invoice_id = int(invoice.get("id") or 0)
    if not invoice_id:
        return
    data = _invoice_data(invoice)
    signature = f"{reason}:{detail[:240]}"
    if str(data.get("regular_auto_skip_signature") or "") == signature:
        return
    update_invoice_json(
        invoice_id,
        {
            "regular_auto_skip_signature": signature,
            "regular_auto_skip_reason": reason,
            "regular_auto_skip_detail": detail,
            "regular_auto_skip_at": datetime.now().isoformat(timespec="seconds"),
        },
        message=f"정기 자동처리 제외: {reason} / {detail}",
    )


def _regular_auto_candidate_invoices() -> list[tuple[dict[str, Any], set[str]]]:
    limit = max(1, min(int(settings.regular_auto_scan_limit or 200), 200))
    summaries = list_invoices(mode="regular", limit=limit)
    invoices = [get_invoice(int(item.get("id") or 0)) for item in summaries]
    regulars = [invoice for invoice in invoices if invoice and str(invoice.get("invoice_type") or "").strip().lower() == "regular"]
    blocked_keys: set[str] = set()
    for invoice in regulars:
        data = _invoice_data(invoice)
        status = str(invoice.get("status") or "")
        already_done = bool(
            str(invoice.get("processed_at") or "").strip()
            or str(data.get("regular_auto_completed_at") or "").strip()
            or str(data.get("regular_auto_output_printed_at") or "").strip()
            or _regular_auto_output_ready(invoice)
        )
        if status != WAITING or already_done:
            blocked_keys.update(_regular_auto_dedupe_keys(invoice))

    selected: list[tuple[dict[str, Any], set[str]]] = []
    max_batch = max(1, int(settings.regular_auto_max_batch or 20))
    for invoice in reversed(regulars):
        if len(selected) >= max_batch:
            break
        invoice_id = int(invoice.get("id") or 0)
        if not invoice_id or str(invoice.get("status") or "") != WAITING:
            continue
        data = _invoice_data(invoice)
        if str(data.get("regular_auto_completed_at") or data.get("regular_auto_output_printed_at") or "").strip():
            _regular_auto_mark_skip(invoice, "already_completed", f"invoice #{invoice_id}")
            blocked_keys.update(_regular_auto_dedupe_keys(invoice))
            continue
        if _regular_auto_output_ready(invoice):
            _regular_auto_mark_skip(invoice, "output_set_ready", f"invoice #{invoice_id}")
            blocked_keys.update(_regular_auto_dedupe_keys(invoice))
            continue
        keys = _regular_auto_dedupe_keys(invoice)
        duplicate_keys = sorted(key for key in keys if key in blocked_keys and not key.startswith("id:"))
        if duplicate_keys:
            _regular_auto_mark_skip(invoice, "duplicate", ", ".join(duplicate_keys[:5]))
            blocked_keys.update(keys)
            continue
        try:
            build_regular_erp_payload(invoice)
        except Exception as exc:
            _regular_auto_mark_skip(invoice, "payload_not_ready", str(exc) or exc.__class__.__name__)
            continue
        selected.append((invoice, keys))
        blocked_keys.update(keys)
    return selected


def _queue_regular_auto_job() -> Any:
    global _regular_auto_last_job_id
    if not settings.regular_auto_enabled:
        return None
    with _regular_auto_scheduler_lock:
        current = job_store.get(_regular_auto_last_job_id) if _regular_auto_last_job_id else None
        if _mail_collect_job_running(current):
            return current
        profile = _regular_auto_target_profile()
        if not profile:
            return None
        printer_key = _regular_auto_printer_key()
        printer_name = _regular_auto_printer_name(profile, printer_key)
        if not printer_name:
            return None
        selected = _regular_auto_candidate_invoices()
        if not selected:
            return None
        invoice_ids = [int(invoice["id"]) for invoice, _keys in selected]
        job = job_store.create(
            JobCreateRequest(
                job_type="regular_one_click",
                title=f"정기 자동 ERP/평택 출력 {len(invoice_ids)}건",
                payload={
                    "invoice_ids": invoice_ids,
                    "erp_invoice_ids": invoice_ids,
                    "ready_output_invoice_ids": [],
                    "processor": "REGULAR_AUTO",
                    "target_agent_id": str(profile.get("agent_id") or ""),
                    "target_client_ip": str(settings.regular_auto_agent_ip or "").strip(),
                    "one_click": True,
                    "one_click_mode": "regular",
                    "regular_auto": True,
                    "output_target": printer_key,
                    "output_action": "print_individual",
                    "printer_key": printer_key,
                    "printer_name": printer_name,
                },
            )
        )
        _regular_auto_last_job_id = job.id
        for invoice, keys in selected:
            update_invoice_json(
                int(invoice["id"]),
                {
                    "regular_auto_queued_at": datetime.now().isoformat(timespec="seconds"),
                    "regular_auto_job_id": job.id,
                    "regular_auto_target_client_ip": str(settings.regular_auto_agent_ip or "").strip(),
                    "regular_auto_printer_key": printer_key,
                    "regular_auto_dedupe_keys": sorted(keys),
                    "regular_auto_skip_signature": "",
                    "regular_auto_skip_reason": "",
                    "regular_auto_skip_detail": "",
                },
                message=f"정기 자동처리 ERP/평택 출력 큐 등록: {job.id}",
            )
    worker.submit(job)
    return job


def _regular_auto_status() -> dict[str, Any]:
    with _regular_auto_scheduler_lock:
        job_id = _regular_auto_last_job_id
    job = job_store.get(job_id) if job_id else None
    profile = latest_agent_profile(client_ip=str(settings.regular_auto_agent_ip or "").strip()) if settings.regular_auto_agent_ip else {}
    return {
        "enabled": bool(settings.regular_auto_enabled),
        "target_client_ip": str(settings.regular_auto_agent_ip or "").strip(),
        "printer_key": _regular_auto_printer_key(),
        "printer_name": _regular_auto_printer_name(profile, "pyeongtaek") if profile else str(settings.print_target_pyeongtaek or "평택 프린터 (172.16.10.172)").strip(),
        "interval_seconds": int(settings.regular_auto_interval_seconds or 60),
        "running": _mail_collect_job_running(job),
        "job_id": job_id,
        "status": getattr(job, "status", "idle") if job else "idle",
        "agent_id": str((profile or {}).get("agent_id") or ""),
        "agent_client_ip": str((profile or {}).get("client_ip") or ""),
        "last_seen": str((profile or {}).get("last_seen") or ""),
        "last_seen_age_seconds": _regular_auto_age_seconds((profile or {}).get("last_seen")) if profile else None,
    }


def _start_regular_auto_scheduler() -> None:
    global _regular_auto_scheduler_started
    if not settings.regular_auto_enabled:
        return
    with _regular_auto_scheduler_lock:
        if _regular_auto_scheduler_started:
            return
        _regular_auto_scheduler_started = True

    def _loop() -> None:
        interval = max(10, int(settings.regular_auto_interval_seconds or 60))
        while True:
            try:
                _queue_regular_auto_job()
            except Exception:
                logging.exception("Automatic regular ERP/output queue failed")
            time.sleep(interval)

    threading.Thread(target=_loop, name="regular-auto-processor", daemon=True).start()


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
    one_click_mode = str(source_job.payload.get("one_click_mode") or "purchase").strip().lower()
    if one_click_mode == "regular":
        missing = [invoice_id for invoice_id in invoice_ids if not _invoice_output_set_ready(get_invoice(invoice_id), "regular")]
        if missing:
            if job_store.get(source_job_id):
                job_store.add_event(source_job_id, "printing", 97, f"정기 문서 세트 준비 대기: {len(missing)}건")
            return
    else:
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
                "target_agent_id": str(source_job.payload.get("target_agent_id") or ""),
                "target_client_ip": str(source_job.payload.get("target_client_ip") or ""),
                "existing_only": True,
                "regular_auto": bool(source_job.payload.get("regular_auto")),
            },
        )
    )
    source_job.payload["one_click_output_job_id"] = job.id
    job_store.add_event(source_job_id, "printing", 98, f"원클릭 출력 작업 등록: {job.id}")
    worker.submit(job)


def _maybe_queue_regular_output_from_context(
    source_job_id: str,
    invoice_ids: list[int],
    context: dict[str, Any],
) -> bool:
    if not bool(context.get("one_click")):
        return False
    if str(context.get("one_click_mode") or "").strip().lower() != "regular":
        return False
    clean_ids = [int(item) for item in invoice_ids if str(item).isdigit()]
    if not clean_ids:
        return False
    duplicate_markers = 0
    for invoice_id in clean_ids:
        invoice = get_invoice(invoice_id)
        data = _invoice_data(invoice)
        if str(data.get("regular_output_source_job_id") or "") == source_job_id:
            duplicate_markers += 1
    if duplicate_markers == len(clean_ids):
        return False
    missing = [invoice_id for invoice_id in clean_ids if not _invoice_output_set_ready(get_invoice(invoice_id), "regular")]
    if missing:
        return False
    printer_key = str(context.get("printer_key") or ("pyeongtaek" if context.get("regular_auto") else "pdf")).strip().lower()
    action = str(context.get("output_action") or ("print_individual" if printer_key != "pdf" else "merged_pdf"))
    printer_name = str(context.get("printer_name") or "").strip()
    if action == "print_individual" and not printer_name and printer_key == "pyeongtaek":
        printer_name = str(settings.print_target_pyeongtaek or "평택 프린터 (172.16.10.172)").strip()
    if action == "print_individual" and not printer_name:
        return False
    job = job_store.create(
        JobCreateRequest(
            job_type="output_set",
            title=f"정기 ERP 완료 후 문서 출력 {len(clean_ids)}건",
            payload={
                "invoice_ids": clean_ids,
                "action": action,
                "printer_key": printer_key,
                "printer_name": printer_name,
                "processor": str(context.get("processor") or "WEB v1.0"),
                "source_job_id": source_job_id,
                "target_agent_id": str(context.get("target_agent_id") or ""),
                "target_client_ip": str(context.get("target_client_ip") or settings.regular_auto_agent_ip or ""),
                "existing_only": True,
                "regular_auto": bool(context.get("regular_auto")),
            },
        )
    )
    for invoice_id in clean_ids:
        update_invoice_json(
            invoice_id,
            {
                "regular_output_source_job_id": source_job_id,
                "regular_output_job_id": job.id,
                "regular_output_queued_at": datetime.now().isoformat(timespec="seconds"),
            },
            message=f"정기 ERP 완료 후 문서 출력 큐 등록: {job.id}",
        )
    worker.submit(job)
    return True


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
    $candidates = @($env:PYTHON_EXE, "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe", "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "python", "py")
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
if (-not $Python) { throw "Python 3.11 이상을 찾지 못했습니다. Python 설치 후 이 파일을 다시 실행하세요." }

Write-Host "[회계업무 WEB] Python 패키지를 확인합니다."
$RequirementsPath = Join-Path $InstallRoot "web_v1\backend\requirements.txt"
if (-not (Test-Path $RequirementsPath)) { throw "requirements.txt not found after setup copy: $RequirementsPath" }
& $Python -m pip install -r $RequirementsPath
if ($LASTEXITCODE -ne 0) { throw "Python package install failed. ExitCode=$LASTEXITCODE" }

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
foreach ($Item in $Store.Certificates) { if ($Item.Thumbprint -eq $Cert.Thumbprint) { $AlreadyTrusted = $true; break } }
$Store.Close()
if (-not $AlreadyTrusted) {
    & certutil.exe -user -addstore Root $CertPath | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "WEB HTTPS 인증서 등록 실패: certutil exit code $LASTEXITCODE" }
}

$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$RunScript = Join-Path $InstallRoot "담당자PC_필수프로그램_실행.ps1"
@"
`$ErrorActionPreference = "Stop"
`$Root = "$InstallRoot"
`$env:WEB_SERVER_URL = "$ServerUrl"
`$env:PYTHON_EXE = "$Python"
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "`$Root\web_v1\deploy\start_user_erp_agent.ps1"
"@ | Set-Content -Path $RunScript -Encoding UTF8
$RunCommand = "`"$PowerShellExe`" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RunScript`""

try {
    $ProtocolKey = "HKCU:\Software\Classes\accountingweb"
    $CommandKey = Join-Path $ProtocolKey "shell\open\command"
    New-Item -Path $CommandKey -Force | Out-Null
    Set-Item -Path $ProtocolKey -Value "URL:Accounting WEB 필수 프로그램"
    New-ItemProperty -Path $ProtocolKey -Name "URL Protocol" -Value "" -PropertyType String -Force | Out-Null
    Set-Item -Path $CommandKey -Value $RunCommand
} catch { Write-Host "[회계업무 WEB] 로그인 자동 실행 연결 등록은 건너뜁니다: $($_.Exception.Message)" }

try {
    $RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    New-Item -Path $RunKey -Force | Out-Null
    Set-ItemProperty -Path $RunKey -Name "AccountingWebAgent" -Value $RunCommand -Force
} catch { Write-Host "[회계업무 WEB] Windows 로그인 자동 실행 등록은 건너뜁니다: $($_.Exception.Message)" }

try {
    $ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "회계업무 WEB 필수프로그램 실행.lnk"
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $PowerShellExe
    $Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RunScript`""
    $Shortcut.WorkingDirectory = $InstallRoot
    $Shortcut.WindowStyle = 7
    $Shortcut.Save()
} catch { Write-Host "[회계업무 WEB] 바탕화면 아이콘 생성은 건너뜁니다: $($_.Exception.Message)" }

Write-Host "[회계업무 WEB] 설치 완료. 필수 프로그램을 실행합니다."
Start-Process -FilePath $PowerShellExe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RunScript`"" -WindowStyle Hidden
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
$Curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if ($Curl) {
    & $Curl.Source -k -L --fail --output $PayloadZip "$ServerUrl/api/setup/user-pc-payload.zip"
    if ($LASTEXITCODE -ne 0) {
        throw "payload download failed: curl exit code $LASTEXITCODE"
    }
} else {
    Invoke-WebRequest -Uri "$ServerUrl/api/setup/user-pc-payload.zip" -OutFile $PayloadZip -UseBasicParsing
}
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
            "웹 화면에서 받은 EXE 설치 파일이 이 압축 내용을 자동으로 사용합니다.\r\n"
            "설치가 끝나면 담당자 PC 필수 프로그램은 트레이 아이콘으로 실행됩니다.\r\n"
            "압축 파일을 직접 열어 설치하지 말고 웹 화면의 EXE 설치 파일을 사용하세요.\r\n"
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




def _agent_update_notes() -> str:
    try:
        if UPDATE_NOTES_PATH.exists():
            return UPDATE_NOTES_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        logging.exception("Failed to read update notes")
    return "담당자 PC 필수 프로그램 최신 패치입니다."

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
    _start_regular_auto_scheduler()
    start_regular_due_scheduler()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "version": settings.app_version,
        "env": settings.app_env,
        "erp_execution_mode": settings.erp_execution_mode,
    }



@app.get("/api/regular-due/status")
def api_regular_due_status(date: str = Query(default="", max_length=20)) -> dict[str, Any]:
    return regular_due_status(date or None)


@app.get("/api/regular-due/history")
def api_regular_due_history(limit: int = Query(default=500, ge=1, le=1000)) -> dict[str, Any]:
    return regular_due_history(limit=limit)


@app.post("/api/regular-due/check")
def api_regular_due_check(
    date: str = Query(default="", max_length=20),
    send: bool = Query(default=False),
    force: bool = Query(default=False),
) -> dict[str, Any]:
    if send:
        return send_regular_due_report(date or None, force=force)
    return regular_due_status(date or None)

@app.get("/api/mail-collect/status")
def api_mail_collect_status() -> dict[str, Any]:
    return _mail_collect_status()


@app.get("/api/regular-auto/status")
def api_regular_auto_status() -> dict[str, Any]:
    return _regular_auto_status()


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
    return {
        "ok": True,
        "user": user,
        "password_change_required": bool(user.get("is_initial")),
        "setup_required": not status["ready"],
        "setup": status,
    }


@app.post("/api/password/find")
async def api_password_find(request: Request) -> dict[str, Any]:
    payload = await request.json()
    user_id = str(payload.get("user_id") or payload.get("id") or "").strip()
    try:
        user = request_password_reset_code(user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"인증코드 메일 발송에 실패했습니다: {exc}") from exc
    if not user:
        raise HTTPException(status_code=404, detail="등록된 아이디를 찾지 못했습니다.")
    return {
        "ok": True,
        "user": user,
        "message": f"인증코드를 사내 메일({user.get('email')})로 발송했습니다.",
    }


@app.post("/api/password/reset-with-code")
async def api_password_reset_with_code(request: Request) -> dict[str, Any]:
    payload = await request.json()
    try:
        user = reset_password_with_code(
            str(payload.get("user_id") or payload.get("id") or "").strip(),
            str(payload.get("code") or "").strip(),
            str(payload.get("new_password") or "").strip(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "user": user,
        "message": "비밀번호를 변경했습니다. 새 비밀번호로 로그인하세요.",
    }


@app.post("/api/password/change-initial")
async def api_password_change_initial(request: Request) -> dict[str, Any]:
    payload = await request.json()
    try:
        user = change_initial_password(
            str(payload.get("user_id") or payload.get("id") or "").strip(),
            str(payload.get("current_password") or payload.get("password") or "").strip(),
            str(payload.get("new_password") or "").strip(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        job_type = str(task.get("job_type") or "")
        if job_type == "expense_report":
            job_store.add_event(job_id, "erp", 80, f"담당자 PC Agent 현금출금결의서 생성 시작: {task.get('agent_id')}")
        elif job_type == "output_print":
            job_store.add_event(job_id, "printing", 92, f"담당자 PC Agent 출력 시작: {task.get('agent_id')}")
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


@app.get("/api/agent/jobs/{job_id}/print-file/{invoice_id}/{file_index}")
def api_agent_output_print_file(job_id: str, invoice_id: int, file_index: int) -> FileResponse:
    task = _output_print_task(job_id)
    matched = None
    for item in task.get("print_files") or []:
        if not isinstance(item, dict):
            continue
        if int(item.get("invoice_id") or 0) == int(invoice_id) and int(item.get("file_index") or 0) == int(file_index):
            matched = item
            break
    if not matched:
        raise HTTPException(status_code=404, detail="출력 대상 파일이 큐에 없습니다.")
    path = Path(str(matched.get("path") or ""))
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"출력 대상 PDF가 없습니다: {path}")
    return FileResponse(path, filename=path.name, media_type="application/pdf")


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
    source_context = task_payload.get("source_job_payload") if isinstance(task_payload.get("source_job_payload"), dict) else {}
    if job_type == "output_print":
        output_job = job_store.get(job_id)
        output_payload = output_job.payload if output_job else {}
        source_job_id = str(output_payload.get("source_job_id") or task_payload.get("source_job_id") or "")
        regular_auto_output = bool(output_payload.get("regular_auto") or task_payload.get("regular_auto"))
        output_printer_key = str(output_payload.get("printer_key") or task_payload.get("printer_key") or "pyeongtaek")
        output_printer_name = str(output_payload.get("printer_name") or task_payload.get("printer_name") or "")
        for invoice_id in invoice_ids:
            add_invoice_log(invoice_id, message, level="info" if ok else "error", job_id=job_id)
            if ok:
                refreshed_invoice = get_invoice(invoice_id)
                if refreshed_invoice and str(refreshed_invoice.get("status") or "") == WAITING:
                    try:
                        output_status = build_output_set_status(refreshed_invoice, persist=True)
                    except Exception:
                        output_status = {}
                    if output_status.get("ready"):
                        set_invoice_status(
                            invoice_id,
                            DONE,
                            processor=normalize_processor(agent_id) or "ERP Agent",
                            job_id=job_id,
                            processed=True,
                        )
            if ok and regular_auto_output:
                update_invoice_json(
                    invoice_id,
                    {
                        "regular_auto_output_printed_at": datetime.now().isoformat(timespec="seconds"),
                        "regular_auto_output_print_job_id": job_id,
                        "regular_auto_printer_key": output_printer_key,
                        "regular_auto_printer_name": output_printer_name,
                    },
                    message=f"정기 자동처리 평택 출력 완료: {output_printer_name}",
                )
        result_payload = dict(payload)
        result_payload["job_type"] = "output_print"
        if output_job:
            merged_result = dict(output_job.result or {})
            merged_result["agent_print"] = result_payload
            job_store.set_result(job_id, merged_result)
            if ok:
                job_store.add_event(job_id, "done", 100, message)
            else:
                job_store.set_error(job_id, message)
                job_store.add_event(job_id, "error", 100, message)
        if source_job_id and job_store.get(source_job_id):
            source = job_store.get(source_job_id)
            source_result = dict(source.result if source else {})
            source_result["one_click_output"] = job_store.get(job_id).result if job_store.get(job_id) else result_payload
            job_store.set_result(source_job_id, source_result)
            if ok:
                job_store.add_event(source_job_id, "done", 100, message)
            else:
                job_store.set_error(source_job_id, message)
                job_store.add_event(source_job_id, "error", 100, f"원클릭 출력 실패: {message}")
        if regular_auto_output:
            mail_result = notify_regular_auto_result(
                job=output_job or job_store.get(job_id),
                source_job=job_store.get(source_job_id) if source_job_id else None,
                ok=ok,
                message=message,
                invoice_ids=invoice_ids,
                agent_id=agent_id,
                phase="Pyeongtaek output",
            )
            _record_regular_auto_mail_result(source_job_id or job_id, invoice_ids, mail_result, "Pyeongtaek output")
        return {"ok": True}
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
    source_job = job_store.get(job_id)
    if source_job:
        source_context = {**source_context, **source_job.payload}
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
        if invoice_ok and bool(source_context.get("regular_auto")):
            update_invoice_json(
                invoice_id,
                {
                    "regular_auto_completed_at": datetime.now().isoformat(timespec="seconds"),
                    "regular_auto_completed_job_id": job_id,
                    "regular_auto_agent_id": agent_id,
                },
                message=f"정기 자동처리 ERP 입력 완료: {agent_id}",
            )
        add_invoice_log(invoice_id, message, level="info" if invoice_ok else "error", job_id=job_id)
        if invoice_ok:
            _queue_expense_report_after_erp(
                invoice_id,
                agent_id=agent_id,
                target_client_ip=str(task_payload.get("target_client_ip") or client_ip(request)).strip(),
                source_job_id=job_id,
            )
    source_job = job_store.get(job_id)
    if ok and source_job and bool(source_job.payload.get("one_click")) and str(source_job.payload.get("one_click_mode") or "").lower() == "regular":
        _maybe_queue_one_click_output(job_id)
    elif ok:
        _maybe_queue_regular_output_from_context(job_id, invoice_ids, source_context)
    if job_store.get(job_id):
        job_store.set_result(job_id, dict(payload))
        if ok:
            job_store.add_event(job_id, "done", 100, message)
        else:
            job_store.set_error(job_id, message)
            job_store.add_event(job_id, "error", 100, message)
    if not ok and bool(source_context.get("regular_auto")):
        mail_result = notify_regular_auto_result(
            job=job_store.get(job_id),
            ok=False,
            message=message,
            invoice_ids=invoice_ids,
            agent_id=agent_id,
            phase="ERP input",
        )
        _record_regular_auto_mail_result(job_id, invoice_ids, mail_result, "ERP input")
    return {"ok": True}


@app.get("/api/version")
def version() -> dict[str, Any]:
    return {
        "product": "회계업무 자동화 WEB",
        "version": settings.app_version,
        "agent_bundle_hash": expected_agent_bundle_hash(),
        "agent_update_notes": _agent_update_notes(),
    }


@app.get("/regular-due-history", include_in_schema=False)
def regular_due_history_page() -> HTMLResponse:
    return HTMLResponse("""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>&#51221;&#44592; &#49464;&#44552;&#44228;&#49328;&#49436; &#49688;&#49888;&#51060;&#47141;</title>
  <style>
    *{box-sizing:border-box;}
    body{margin:0;font-family:Malgun Gothic,Arial,sans-serif;color:#111827;background:#f8fafc;}
    main{padding:20px;}
    h1{font-size:20px;margin:0 0 14px 0;}
    .panel{border:1px solid #cbd5e1;background:#ffffff;padding:12px;margin-bottom:12px;}
    .filters{display:grid;grid-template-columns:repeat(6,minmax(140px,1fr));gap:10px;align-items:end;}
    label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:#475569;font-weight:700;}
    input,select{height:34px;border:1px solid #cbd5e1;border-radius:4px;padding:0 9px;background:#ffffff;color:#111827;font:inherit;font-size:13px;min-width:0;}
    input[type=number]{text-align:right;}
    .wide{grid-column:span 2;}
    .actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
    button{height:34px;border:0;border-radius:4px;background:#0f766e;color:white;padding:0 12px;font-weight:700;cursor:pointer;}
    button.secondary{background:#475569;}
    button.ghost{background:#e2e8f0;color:#111827;}
    .count{color:#475569;font-size:13px;font-weight:700;}
    .table-wrap{overflow:auto;border:1px solid #cbd5e1;background:white;}
    table{width:100%;border-collapse:collapse;background:white;font-size:13px;min-width:1180px;}
    th,td{border:1px solid #cbd5e1;padding:8px;vertical-align:top;}
    th{background:#f1f5f9;text-align:center;white-space:nowrap;position:sticky;top:0;z-index:1;}
    th.sortable{cursor:pointer;user-select:none;}
    th.sortable:hover{background:#e2e8f0;}
    td.center{text-align:center;white-space:nowrap;}
    td.amount{text-align:right;white-space:nowrap;}
    td.vendor{font-weight:700;white-space:nowrap;}
    td.content{min-width:240px;}
    td.file{min-width:320px;word-break:break-all;}
    .sortmark{display:inline-block;min-width:18px;color:#0f766e;font-weight:700;}
    @media (max-width:1200px){.filters{grid-template-columns:repeat(3,minmax(140px,1fr));}.wide{grid-column:span 3;}}
  </style>
</head>
<body>
<main>
  <h1>&#51221;&#44592; &#49464;&#44552;&#44228;&#49328;&#49436; &#49688;&#49888;&#51060;&#47141;</h1>
  <section class="panel">
    <div class="filters">
      <label class="wide">&#53685;&#54633;&#44160;&#49353;
        <input id="q" placeholder="&#50629;&#52404;&#47749;, &#45236;&#50857;, &#54028;&#51068;&#47749;, ID">
      </label>
      <label>&#50629;&#52404;&#47749;
        <select id="vendor"><option value="">&#51204;&#52404;</option></select>
      </label>
      <label>&#51221;&#47148;&#44592;&#51456;
        <select id="sortBy">
          <option value="received_at">&#49688;&#49888;&#51068;</option>
          <option value="issue_date">&#48156;&#54665;&#51068;</option>
          <option value="vendor_name">&#50629;&#52404;&#47749;</option>
          <option value="amount">&#44552;&#50529;</option>
          <option value="content">&#45236;&#50857;</option>
          <option value="file_name">&#54028;&#51068;&#47749;</option>
          <option value="invoice_id">ID</option>
        </select>
      </label>
      <label>&#51221;&#47148;&#48169;&#54693;
        <select id="sortDir">
          <option value="desc">&#45236;&#47548;&#52264;&#49692;</option>
          <option value="asc">&#50724;&#47492;&#52264;&#49692;</option>
        </select>
      </label>
      <div class="actions">
        <button id="apply">&#51312;&#54924;</button>
        <button id="reset" class="ghost">&#52488;&#44592;&#54868;</button>
        <button id="reload" class="secondary">&#49352;&#47196;&#44256;&#52840;</button>
      </div>
      <label>&#48156;&#54665;&#51068; &#49884;&#51089;
        <input id="issueFrom" type="date">
      </label>
      <label>&#48156;&#54665;&#51068; &#51333;&#47308;
        <input id="issueTo" type="date">
      </label>
      <label>&#49688;&#49888;&#51068; &#49884;&#51089;
        <input id="receivedFrom" type="date">
      </label>
      <label>&#49688;&#49888;&#51068; &#51333;&#47308;
        <input id="receivedTo" type="date">
      </label>
      <label>&#44552;&#50529; &#51060;&#49345;
        <input id="amountMin" type="number" min="0" step="1" placeholder="0">
      </label>
      <label>&#44552;&#50529; &#51060;&#54616;
        <input id="amountMax" type="number" min="0" step="1" placeholder="0">
      </label>
      <label class="wide">&#45236;&#50857;
        <input id="contentQ" placeholder="&#54408;&#47785;/&#49436;&#48708;&#49828;&#47749;">
      </label>
      <label class="wide">&#54028;&#51068;&#47749;
        <input id="fileQ" placeholder="PDF &#54028;&#51068;&#47749;">
      </label>
      <div class="actions"><span class="count" id="count"></span></div>
    </div>
  </section>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>&#49692;&#48264;</th>
          <th class="sortable" data-sort="invoice_id">ID <span class="sortmark"></span></th>
          <th class="sortable" data-sort="vendor_name">&#50629;&#52404;&#47749; <span class="sortmark"></span></th>
          <th class="sortable" data-sort="issue_date">&#48156;&#54665;&#51068; <span class="sortmark"></span></th>
          <th class="sortable" data-sort="received_at">&#49688;&#49888;&#51068; <span class="sortmark"></span></th>
          <th class="sortable" data-sort="amount">&#44552;&#50529; <span class="sortmark"></span></th>
          <th class="sortable" data-sort="content">&#45236;&#50857; <span class="sortmark"></span></th>
          <th class="sortable" data-sort="file_name">&#54028;&#51068;&#47749; <span class="sortmark"></span></th>
        </tr>
      </thead>
      <tbody id="rows"><tr><td colspan="8" class="center">&#48520;&#47084;&#50724;&#45716; &#51473;</td></tr></tbody>
    </table>
  </div>
</main>
<script>
let allRows=[];
let viewRows=[];
const rowsEl=document.getElementById('rows');
const ids=['q','vendor','sortBy','sortDir','issueFrom','issueTo','receivedFrom','receivedTo','amountMin','amountMax','contentQ','fileQ'];
const el=Object.fromEntries(ids.map(id=>[id,document.getElementById(id)]));
const countEl=document.getElementById('count');
function esc(v){return String(v??'').replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));}
function norm(v){return String(v??'').toLowerCase().trim();}
function dateKey(v){const s=String(v??'').slice(0,10);return /^\d{4}-\d{2}-\d{2}$/.test(s)?s:'';}
function num(v){const n=Number(String(v??'').replace(/[^0-9.-]/g,''));return Number.isFinite(n)?n:0;}
function includes(v,q){return !q||norm(v).includes(q);}
function inDateRange(value,from,to){const d=dateKey(value); if(!d)return !(from||to); return (!from||d>=from)&&(!to||d<=to);}
function inAmountRange(value,min,max){const n=num(value); return (!min||n>=Number(min))&&(!max||n<=Number(max));}
function rowText(r){return [r.invoice_id,r.vendor_name,r.content,r.file_name,r.issue_date,r.received_at,r.amount].join(' ');}
function compareValue(r,key){
  if(key==='amount'||key==='invoice_id')return num(r[key]);
  if(key==='issue_date'||key==='received_at')return dateKey(r[key]);
  return norm(r[key]);
}
function sortRows(rows){
  const key=el.sortBy.value;
  const dir=el.sortDir.value==='asc'?1:-1;
  return [...rows].sort((a,b)=>{
    const av=compareValue(a,key), bv=compareValue(b,key);
    const ae=av===''||av===0, be=bv===''||bv===0;
    if(ae&&be)return 0;
    if(ae)return 1;
    if(be)return -1;
    if(av>bv)return dir;
    if(av<bv)return -dir;
    return num(b.invoice_id)-num(a.invoice_id);
  });
}
function fillVendors(){
  const vendors=[...new Set(allRows.map(r=>String(r.vendor_name||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'ko'));
  el.vendor.innerHTML='<option value="">&#51204;&#52404;</option>'+vendors.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('');
}
function updateSortMarks(){
  document.querySelectorAll('th.sortable').forEach(th=>{
    const mark=th.querySelector('.sortmark');
    mark.textContent=th.dataset.sort===el.sortBy.value?(el.sortDir.value==='asc'?'\u25B2':'\u25BC'):'';
  });
}
function applyFilters(){
  const q=norm(el.q.value), contentQ=norm(el.contentQ.value), fileQ=norm(el.fileQ.value), vendor=el.vendor.value;
  viewRows=allRows.filter(r=>{
    if(vendor&&String(r.vendor_name||'')!==vendor)return false;
    if(q&&!norm(rowText(r)).includes(q))return false;
    if(!includes(r.content,contentQ))return false;
    if(!includes(r.file_name,fileQ))return false;
    if(!inDateRange(r.issue_date,el.issueFrom.value,el.issueTo.value))return false;
    if(!inDateRange(r.received_at,el.receivedFrom.value,el.receivedTo.value))return false;
    if(!inAmountRange(r.amount,el.amountMin.value,el.amountMax.value))return false;
    return true;
  });
  viewRows=sortRows(viewRows);
  render();
}
function render(){
  countEl.textContent='\uC870\uD68C '+viewRows.length+'\uAC74 / \uC804\uCCB4 '+allRows.length+'\uAC74';
  updateSortMarks();
  rowsEl.innerHTML=viewRows.length?viewRows.map((r,i)=>`<tr><td class="center">${i+1}</td><td class="center">${esc(r.invoice_id)}</td><td class="vendor">${esc(r.vendor_name)}</td><td class="center">${esc(r.issue_date)}</td><td class="center">${esc(r.received_at)}</td><td class="amount">${esc(r.amount)}</td><td class="content">${esc(r.content)}</td><td class="file">${esc(r.file_name)}</td></tr>`).join(''):'<tr><td colspan="8" class="center">&#51312;&#54924; &#44208;&#44284; &#50630;&#51020;</td></tr>';
}
function resetFilters(){
  ['q','issueFrom','issueTo','receivedFrom','receivedTo','amountMin','amountMax','contentQ','fileQ'].forEach(id=>el[id].value='');
  el.vendor.value='';
  el.sortBy.value='received_at';
  el.sortDir.value='desc';
  applyFilters();
}
async function load(){
  rowsEl.innerHTML='<tr><td colspan="8" class="center">&#48520;&#47084;&#50724;&#45716; &#51473;</td></tr>';
  const res=await fetch('/api/regular-due/history?limit=1000',{cache:'no-store'});
  const data=await res.json();
  allRows=data.items||[];
  fillVendors();
  applyFilters();
}
document.getElementById('apply').addEventListener('click',applyFilters);
document.getElementById('reset').addEventListener('click',resetFilters);
document.getElementById('reload').addEventListener('click',load);
['q','contentQ','fileQ'].forEach(id=>el[id].addEventListener('keydown',e=>{if(e.key==='Enter')applyFilters();}));
['vendor','sortBy','sortDir','issueFrom','issueTo','receivedFrom','receivedTo','amountMin','amountMax'].forEach(id=>el[id].addEventListener('change',applyFilters));
document.querySelectorAll('th.sortable').forEach(th=>th.addEventListener('click',()=>{
  const key=th.dataset.sort;
  if(el.sortBy.value===key){el.sortDir.value=el.sortDir.value==='asc'?'desc':'asc';}
  else{el.sortBy.value=key;el.sortDir.value=(key==='vendor_name'||key==='content'||key==='file_name')?'asc':'desc';}
  applyFilters();
}));
load();
</script>
</body>
</html>""")


@app.get("/admin-db", include_in_schema=False)
def admin_db_page() -> FileResponse:
    page = FRONTEND_DIR / "admin_db.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="DB viewer page not found")
    return FileResponse(page)


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
    ready_output_ids: list[int] = []
    erp_invoice_ids: list[int] = []
    for raw_id in body.invoice_ids:
        invoice_id = int(raw_id)
        invoice = get_invoice(invoice_id)
        if _invoice_output_set_ready(invoice, "purchase"):
            ready_output_ids.append(invoice_id)
            add_invoice_log(invoice_id, "기존 문서 세트가 모두 준비되어 원클릭 ERP/현금결의서 생성 단계를 건너뜁니다.")
        else:
            erp_invoice_ids.append(invoice_id)
    if ready_output_ids and not erp_invoice_ids:
        job = job_store.create(
            JobCreateRequest(
                job_type="output_set",
                title=f"기존 문서 출력 {len(ready_output_ids)}건",
                payload={
                    "invoice_ids": ready_output_ids,
                    "action": output["action"],
                    "printer_key": output["printer_key"],
                    "printer_name": output["printer_name"],
                    "processor": body.processor or "WEB v1.0",
                    "target_agent_id": setup.get("agent_id") or "",
                    "target_client_ip": setup.get("client_ip") or client_ip(request),
                    "existing_only": True,
                    "one_click_existing_only": True,
                },
            )
        )
        worker.submit(job)
        return job.to_response()
    job = job_store.create(
        JobCreateRequest(
            job_type="purchase_one_click",
            title=f"구매 원클릭 처리 {len(body.invoice_ids)}건",
            payload={
                "invoice_ids": body.invoice_ids,
                "erp_invoice_ids": erp_invoice_ids,
                "ready_output_invoice_ids": ready_output_ids,
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


@app.post("/api/jobs/regular-one-click", response_model=JobResponse, status_code=202)
def create_regular_one_click_job(body: InvoiceIdsRequest, request: Request) -> JobResponse:
    if not body.invoice_ids:
        raise HTTPException(status_code=400, detail="원클릭 처리할 정기 건을 선택해야 합니다.")
    setup = require_setup_ready(request)
    output = _one_click_output_payload(body.output_target, setup)
    ready_output_ids: list[int] = []
    erp_invoice_ids: list[int] = []
    for raw_id in body.invoice_ids:
        invoice_id = int(raw_id)
        invoice = get_invoice(invoice_id)
        if not invoice:
            continue
        if str(invoice.get("invoice_type") or "").strip().lower() != "regular":
            raise HTTPException(status_code=400, detail=f"정기 처리 대상이 아닌 계산서가 포함되어 있습니다: #{invoice_id}")
        if _invoice_output_set_ready(invoice, "regular"):
            ready_output_ids.append(invoice_id)
            add_invoice_log(invoice_id, "기존 정기 문서 세트가 모두 준비되어 ERP 전표 생성 단계를 건너뜁니다.")
        else:
            erp_invoice_ids.append(invoice_id)
    if not ready_output_ids and not erp_invoice_ids:
        raise HTTPException(status_code=400, detail="처리할 정기 계산서를 찾지 못했습니다.")
    if ready_output_ids and not erp_invoice_ids:
        job = job_store.create(
            JobCreateRequest(
                job_type="output_set",
                title=f"기존 정기 문서 출력 {len(ready_output_ids)}건",
                payload={
                    "invoice_ids": ready_output_ids,
                    "action": output["action"],
                    "printer_key": output["printer_key"],
                    "printer_name": output["printer_name"],
                    "processor": body.processor or "WEB v1.0",
                    "target_agent_id": setup.get("agent_id") or "",
                    "target_client_ip": setup.get("client_ip") or client_ip(request),
                    "existing_only": True,
                    "one_click_existing_only": True,
                },
            )
        )
        worker.submit(job)
        return job.to_response()
    job = job_store.create(
        JobCreateRequest(
            job_type="regular_one_click",
            title=f"정기 원클릭 처리 {len(body.invoice_ids)}건",
            payload={
                "invoice_ids": body.invoice_ids,
                "erp_invoice_ids": erp_invoice_ids,
                "ready_output_invoice_ids": ready_output_ids,
                "processor": body.processor or "WEB v1.0",
                "target_agent_id": setup.get("agent_id") or "",
                "target_client_ip": setup.get("client_ip") or client_ip(request),
                "one_click": True,
                "one_click_mode": "regular",
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


@app.post("/api/jobs/regular-erp-input", response_model=JobResponse, status_code=202)
def create_regular_erp_input_job(body: InvoiceIdsRequest, request: Request) -> JobResponse:
    if not body.invoice_ids:
        raise HTTPException(status_code=400, detail="ERP 입력할 정기 건을 선택해야 합니다.")
    setup = require_setup_ready(request)
    for invoice_id in body.invoice_ids:
        invoice = get_invoice(int(invoice_id))
        if not invoice:
            raise HTTPException(status_code=404, detail=f"Invoice not found: #{invoice_id}")
        if str(invoice.get("invoice_type") or "").strip().lower() != "regular":
            raise HTTPException(status_code=400, detail=f"정기 처리 대상이 아닌 계산서가 포함되어 있습니다: #{invoice_id}")
    job = job_store.create(
        JobCreateRequest(
            job_type="regular_erp_input",
            title=f"정기 ERP 입력 실행 {len(body.invoice_ids)}건",
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
    selected_doc_keys = [str(key).strip() for key in body.selected_doc_keys if str(key).strip()]
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
                "target_agent_id": setup.get("agent_id") or "",
                "target_client_ip": setup.get("client_ip") or client_ip(request),
                "existing_only": body.existing_only,
                "selected_doc_keys": selected_doc_keys,
            },
        )
    )
    worker.submit(job)
    return job.to_response()


def _admin_db_conn() -> sqlite3.Connection:
    if not settings.sqlite_db_path.exists():
        raise HTTPException(status_code=404, detail=f"DB file not found: {settings.sqlite_db_path}")
    conn = sqlite3.connect(str(settings.sqlite_db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _admin_table_names(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    return [str(row["name"]) for row in cur.fetchall()]


@app.get("/api/admin/db/overview")
def api_admin_db_overview() -> dict[str, Any]:
    with _admin_db_conn() as conn:
        tables = []
        for table_name in _admin_table_names(conn):
            quoted = _quote_identifier(table_name)
            count = int(conn.execute(f"SELECT COUNT(*) AS count FROM {quoted}").fetchone()["count"])
            columns = [
                {"name": str(row["name"]), "type": str(row["type"] or "")}
                for row in conn.execute(f"PRAGMA table_info({quoted})").fetchall()
            ]
            tables.append({"name": table_name, "count": count, "columns": columns})
    return {"db_path": str(settings.sqlite_db_path), "tables": tables}


@app.get("/api/admin/db/table")
def api_admin_db_table(
    table: str = Query(..., min_length=1, max_length=80),
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    with _admin_db_conn() as conn:
        table_names = set(_admin_table_names(conn))
        if table not in table_names:
            raise HTTPException(status_code=404, detail="Unknown table")
        quoted = _quote_identifier(table)
        column_rows = conn.execute(f"PRAGMA table_info({quoted})").fetchall()
        columns = [str(row["name"]) for row in column_rows]
        where = ""
        params: list[Any] = []
        keyword = q.strip()
        if keyword and columns:
            where = " WHERE " + " OR ".join(f"CAST({_quote_identifier(col)} AS TEXT) LIKE ?" for col in columns)
            params = [f"%{keyword}%"] * len(columns)
        total = int(conn.execute(f"SELECT COUNT(*) AS count FROM {quoted}{where}", params).fetchone()["count"])
        order_column = "id" if "id" in columns else (columns[0] if columns else "rowid")
        rows = conn.execute(
            f"SELECT * FROM {quoted}{where} ORDER BY {_quote_identifier(order_column)} DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
    return {
        "db_path": str(settings.sqlite_db_path),
        "table": table,
        "columns": columns,
        "rows": [{column: row[column] for column in columns} for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


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
    ai_note = "AI 분석 사용" if analysis.get("analysis_ai_used") else ("AI 분석 시도 후 빠른 파싱 사용" if analysis.get("analysis_ai_attempted") else "학습 DB/빠른 파싱 사용")
    updated = update_invoice_json(invoice_id, analysis, message=f"구매 세금계산서/견적서 분석 결과가 저장되었습니다. ({ai_note})")
    _start_purchase_approval_fetch_background(invoice_id, str(analysis.get("quote_path") or analysis.get("quote_pdf_path") or ""))
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
    before_snapshot = _purchase_edit_snapshot(_invoice_data(invoice))
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
    changed = before_snapshot != _purchase_edit_snapshot(payload)
    if not changed:
        refreshed = get_invoice(invoice_id) or invoice
        if isinstance(refreshed, dict):
            refreshed["output_docs"] = build_output_set_status(refreshed, persist=True)
        return refreshed
    learned_count = learn_dictionary_items(list(payload.get("items") or []))
    updated = update_invoice_json(invoice_id, payload, message="구매 분석 결과를 화면에서 수정 저장했습니다.")
    if learned_count:
        from .invoice_db import add_invoice_log

        add_invoice_log(invoice_id, f"구매 품목 학습 DB 반영: {learned_count}건")
    _start_purchase_approval_fetch_background(invoice_id, str(quote_path or ""))
    reset_invoice(invoice_id)
    return get_invoice(invoice_id) or updated or {"ok": True, "invoice_id": invoice_id}


@app.patch("/api/invoices/{invoice_id}/regular-data")
def api_update_regular_data(invoice_id: int, request: RegularDataUpdate) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if str(invoice.get("invoice_type") or "").strip().lower() != "regular":
        raise HTTPException(status_code=400, detail="정기 처리 건만 수정 저장할 수 있습니다.")
    before_snapshot = _regular_edit_snapshot(_invoice_data(invoice))
    payload = request.model_dump()
    clean_items: list[dict[str, Any]] = []
    allowed_accounts = {"지급수수료", "통신비", "소모품비", "컴퓨터소프트웨어", "집기비품"}
    for source in payload.get("items") or []:
        if not isinstance(source, dict):
            continue
        account = str(source.get("account") or "지급수수료").strip()
        row = {
            "account": account if account in allowed_accounts else "지급수수료",
            "account_manual": bool(source.get("account_manual") or source.get("manual_account")),
            "name": str(source.get("name") or source.get("item_name") or "정기 서비스").strip() or "정기 서비스",
            "qty": max(1, int(source.get("qty") or source.get("quantity") or 1)),
            "supply": int(source.get("supply") or source.get("supply_amount") or 0),
            "inc_vat": int(source.get("inc_vat") or source.get("total") or source.get("amount") or 0),
        }
        if not row["inc_vat"] and row["supply"]:
            row["inc_vat"] = round(row["supply"] * 1.1)
        clean_items.append(row)
    payload["items"] = clean_items
    payload["invoice_type"] = "regular"
    payload["erp_ready"] = bool(clean_items or payload.get("total_sum"))
    changed = before_snapshot != _regular_edit_snapshot(payload)
    if not changed:
        refreshed = get_invoice(invoice_id) or invoice
        if isinstance(refreshed, dict):
            refreshed["output_docs"] = build_output_set_status(refreshed, persist=True)
        return refreshed
    updated = update_invoice_json(invoice_id, payload, message="정기 처리 전표 데이터가 화면에서 수정 저장되었습니다.")
    reset_invoice(invoice_id)
    refreshed = get_invoice(invoice_id) or updated or {"id": invoice_id}
    if isinstance(refreshed, dict):
        refreshed["output_docs"] = build_output_set_status(refreshed, persist=True)
    return refreshed


@app.get("/api/invoices/{invoice_id}/logs")
def api_get_invoice_logs(invoice_id: int, limit: int = Query(default=100, ge=1, le=300)) -> list[dict[str, Any]]:
    if not get_invoice(invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return list_invoice_logs(invoice_id, limit=limit)


@app.post("/api/invoices/{invoice_id}/retry")
def api_retry_invoice(invoice_id: int) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    status = str(invoice.get("status") or "")
    if status == DONE:
        raise HTTPException(status_code=400, detail='처리완료 건은 재시도 대신 기존 문서 출력으로 다시 출력하세요.')
    if status != ERROR:
        return {"ok": True, "invoice_id": invoice_id, "status": status or WAITING, "skipped": True}
    if not reset_invoice(invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"ok": True, "invoice_id": invoice_id, "status": WAITING}


@app.delete("/api/invoices/{invoice_id}")
def api_delete_invoice(invoice_id: int) -> dict[str, Any]:
    if not delete_invoice(invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"ok": True, "invoice_id": invoice_id}


@app.get("/api/jobs", response_model=list[JobResponse])
def list_jobs(limit: int = Query(default=10, ge=1, le=200)) -> list[JobResponse]:
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
