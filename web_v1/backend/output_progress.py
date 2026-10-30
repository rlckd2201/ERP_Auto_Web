"""Read-only, restart-safe document/output status from existing PDFs and print tasks."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from datetime import datetime
from pathlib import Path

from .config import settings
from .output_set import build_output_set_status

_cache_lock = threading.Lock()
retry_lock = threading.Lock()
_cache: dict = {}
_checked_at = 0.0
_cache_root = ""
_cache_complete = True
ACTIVE = {"pending", "claimed", "running", "retry"}


def print_tasks(*, fresh=False):
    """Stat only print files and re-read changed files; never scan ERP task contents."""
    global _checked_at, _cache_root, _cache_complete
    root = settings.erp_db_dir / "erp_queue"
    with _cache_lock:
        if str(root) != _cache_root:
            _cache.clear()
            _cache_root = str(root)
            _checked_at = 0
        if fresh or time.monotonic() - _checked_at >= 3:
            seen = set()
            complete = True
            try:
                for path in root.glob("output_print_*.json"):
                    seen.add(str(path))
                    try:
                        stat = path.stat()
                        signature = (stat.st_mtime_ns, stat.st_size)
                        cached = _cache.get(str(path))
                        if not cached or cached[0] != signature:
                            payload = json.loads(path.read_text(encoding="utf-8-sig"))
                            if not isinstance(payload, dict) or payload.get("job_type") != "output_print":
                                raise ValueError("Invalid print task")
                            _cache[str(path)] = (signature, payload)
                    except (OSError, ValueError):
                        complete = False
                        _cache.pop(str(path), None)
                for name in set(_cache) - seen:
                    _cache.pop(name, None)
            except OSError:
                complete = False
            _cache_complete = complete
            _checked_at = time.monotonic()
        return [v[1] for v in _cache.values()], _cache_complete


def _stamp(value):
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (ValueError, TypeError):
        return 0


def _key(item):
    try:
        return f"{int(item['invoice_id'])}:{int(item['file_index'])}"
    except (KeyError, ValueError, TypeError):
        return ""


def _file_states(task):
    result = task.get("agent_result") or {}
    done = set(str(k) for k in task.get("completed_file_keys") or [])
    verified = set()
    legacy_report = False
    for success in result.get("successes") or []:
        keys = success.get("printed_file_keys") or []
        done.update(str(k) for k in keys)
        for key, report in zip(keys, success.get("print_results") or []):
            if isinstance(report, dict) and report.get("spooler_verified") is True:
                verified.add(str(key))
        legacy_report |= bool(success.get("printed_files") and not keys)
    failures = {_key(item): str(item.get("error") or "전송 실패") for item in result.get("failures") or []}
    state = str(task.get("agent_status") or "")
    for item in task.get("print_files") or []:
        key = _key(item)
        if not key:
            continue
        if key in done:
            code, label = ("sent", "프린터 전송 확인") if key in verified else ("submitted", "전송 요청 완료·큐 확인 불가")
        elif state in ACTIVE:
            code, label = "sending", "전송 대기·진행"
        elif key in failures:
            code, label = "failed", "프린터 전송 실패"
        elif state == "done" or legacy_report:
            code, label = "unknown", "이전 전송 기록·개별 확인 필요"
        else:
            code, label = "unknown", "전송 결과 확인 필요"
        yield item, {"state": code, "label": label, "error": failures.get(key, "")[:350],
                     "job_id": str(task.get("job_id") or ""),
                     "printer_name": str(task.get("printer_name") or ""),
                     "printer_key": str(task.get("printer_key") or ""),
                     "at": str(task.get("completed_at") or task.get("updated_at") or task.get("created_at") or "")}


def processing_status(invoice, *, tasks=None, complete=True, pending_jobs=()):
    if tasks is None:
        tasks, complete = print_tasks()
    iid = int(invoice["id"])
    documents = build_output_set_status(invoice, persist=False)["docs"]
    by_name = {str(d["filename"]).casefold(): d["key"] for d in documents}
    relevant = [t for t in tasks if any(str(f.get("invoice_id")) == str(iid) for f in t.get("print_files") or [])]
    relevant.sort(key=lambda t: (_stamp(t.get("created_at")), str(t.get("job_id"))))
    active = any(str(t.get("agent_status")) in ACTIVE for t in relevant)
    for job in pending_jobs:
        payload = getattr(job, "payload", {}) or {}
        if (getattr(job, "job_type", "") in {"output_set", "purchase_one_click", "regular_one_click", "purchase_erp_input", "regular_erp_input"}
                and getattr(job, "status", "") not in {"done", "error"}
                and iid in payload.get("invoice_ids", [])):
            active = True
    latest = {}
    for task in relevant:
        for item, state in _file_states(task):
            if str(item.get("invoice_id")) != str(iid):
                continue
            # File index is selection-relative; use the actual document filename.
            key = by_name.get(str(item.get("filename") or Path(str(item.get("path") or "")).name).casefold())
            if key:
                latest[key] = state
    rows = []
    for doc in documents:
        exists = doc["status"] == "exists"
        state = dict(latest.get(doc["key"], {"state": "none", "label": "전송 기록 없음", "printer_name": "", "at": ""}))
        if state["state"] == "sent":
            try:
                if any(Path(p).stat().st_mtime > _stamp(state["at"]) + 2 for p in doc.get("paths") or [] if Path(p).is_file()):
                    state.update(state="changed", label="전송 후 파일 변경·확인 필요")
            except OSError:
                pass
        pdf_label = "PDF 준비 완료" if exists else ("PDF 생성 실패" if doc["status"] == "failed" else "PDF 미준비")
        rows.append({"key": doc["key"], "label": doc["label"], "pdf_ready": exists,
                     "pdf_label": pdf_label, "pdf_error": doc.get("message", "") if not exists else "",
                     "print": state})
    retry_keys = [d["key"] for d in rows if d["pdf_ready"] and d["print"]["state"] in {"failed", "not_sent"}]
    active = active or invoice.get("status") in {"처리중", "ERP대기"}
    token_data = [{"job": t.get("job_id"), "updated": t.get("updated_at"), "state": t.get("agent_status"),
                   "result": t.get("agent_result"), "done": t.get("completed_file_keys")} for t in relevant]
    token = hashlib.sha256(json.dumps([iid, token_data, retry_keys, active, complete], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if "[ERP_SAVE_CONFIRM_REQUIRED]" in str(invoice.get("last_error") or ""):
        erp_label = "ERP 저장 여부 확인 필요"
    elif any(d["key"] == "erp_voucher" and d["pdf_ready"] for d in rows):
        erp_label = "전표 PDF 보관 완료"
    elif invoice.get("status") in {"처리중", "ERP대기"}:
        erp_label = str(invoice["status"])
    elif invoice.get("status") == "처리완료":
        erp_label = "완료 처리됨·전표 PDF 미확인"
    else:
        erp_label = "전표 PDF 미준비"
    return {"documents": rows, "erp_label": erp_label, "active": active, "complete": complete,
            "retry_doc_keys": retry_keys if complete and not active else [], "retry_token": token,
            "printer_key": str((relevant[-1] if relevant else {}).get("printer_key") or "pyeongtaek"),
            "notice": "전송 확인은 Windows 인쇄 큐 기준입니다. 실제 용지 출력은 프린터에서 확인해 주세요."}


def add_processing_status(invoices, *, pending_jobs=()):
    tasks, complete = print_tasks()
    for invoice in invoices:
        invoice["processing_status"] = processing_status(invoice, tasks=tasks, complete=complete, pending_jobs=pending_jobs)
    return invoices


def validate_retry(invoice, token, *, pending_jobs=()):
    tasks, complete = print_tasks(fresh=True)
    summary = processing_status(invoice, tasks=tasks, complete=complete, pending_jobs=pending_jobs)
    if not complete or summary["active"] or token != summary["retry_token"]:
        raise ValueError("출력 상태가 바뀌었거나 다른 출력이 진행 중입니다. 새로고침 후 확인해 주세요.")
    if not summary["retry_doc_keys"]:
        raise ValueError("재시도할 실패 문서가 없습니다. 문서 상태를 다시 확인해 주세요.")
    return summary["retry_doc_keys"]
