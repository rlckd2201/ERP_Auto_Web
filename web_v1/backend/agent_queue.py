from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from .erp_queue import queue_dir
from .invoice_db import ERP_QUEUED, get_invoice


OUTPUT_PRINT_CLAIM_STALE_SECONDS = 120
TASK_TYPES = {"purchase_erp_input", "regular_erp_input", "expense_report", "output_print"}
ACTIONABLE_AGENT_STATUSES = {"", "pending", "retry"}

# Completed/error queue JSON files are retained as audit records.  Keep a
# process-local index so every Agent poll does not reopen the entire history.
# The lock also preserves the old single-event-loop claim serialization after
# task discovery is moved to FastAPI's worker thread pool.
_task_index_lock = threading.RLock()
_task_index_root: Path | None = None
_task_index_known_names: set[str] = set()
_task_index_candidates: dict[str, tuple[Path, int]] = {}


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _age_seconds(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return max(0.0, (datetime.now() - datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)).total_seconds())
    except Exception:
        return None


def _is_task_index_candidate(payload: dict[str, Any]) -> bool:
    job_type = str(payload.get("job_type") or "")
    if job_type not in TASK_TYPES:
        return False
    agent_status = str(payload.get("agent_status") or "pending")
    if agent_status in ACTIONABLE_AGENT_STATUSES:
        return True
    # Claimed print jobs remain indexed so the existing stale-claim recovery
    # can make them retryable after OUTPUT_PRINT_CLAIM_STALE_SECONDS.
    return job_type == "output_print" and agent_status == "claimed"


def _reset_task_index(root: Path) -> None:
    global _task_index_root
    _task_index_root = root
    _task_index_known_names.clear()
    _task_index_candidates.clear()


def _sorted_task_candidates() -> list[Path]:
    return [
        item[0]
        for _, item in sorted(
            _task_index_candidates.items(),
            key=lambda pair: (pair[1][1], pair[0].lower()),
        )
    ]


def _task_files() -> list[Path]:
    root = queue_dir()
    with _task_index_lock:
        if _task_index_root != root:
            _reset_task_index(root)

        entries: dict[str, Path] = {}
        try:
            with os.scandir(root) as iterator:
                for entry in iterator:
                    if not entry.name.lower().endswith(".json") or not entry.is_file():
                        continue
                    entries[entry.name] = Path(entry.path)
        except FileNotFoundError:
            return []

        current_names = set(entries)
        removed_names = _task_index_known_names - current_names
        for name in removed_names:
            _task_index_known_names.discard(name)
            _task_index_candidates.pop(name, None)

        # On the first call this classifies the historical queue once.  Later
        # calls open only newly created files plus the few actionable files.
        new_names = current_names - _task_index_known_names
        for name in new_names:
            path = entries[name]
            payload = _read_task(path)
            if str(payload.get("job_type") or "") not in TASK_TYPES:
                # A writer may have created the file but not finished its JSON
                # yet.  Do not mark it known; retry on the next Agent poll.
                continue
            _task_index_known_names.add(name)
            if _is_task_index_candidate(payload):
                try:
                    mtime_ns = path.stat().st_mtime_ns
                except OSError:
                    mtime_ns = 0
                _task_index_candidates[name] = (path, mtime_ns)

        return _sorted_task_candidates()


def _forget_task(path: Path) -> None:
    _task_index_candidates.pop(path.name, None)


def _read_task(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_task(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _active_invoice_items(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    job_id = str(payload.get("job_id") or "")
    active: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    for item in list(payload.get("invoices") or []):
        try:
            invoice_id = int(item.get("id") or 0)
        except Exception:
            invoice_id = 0
        current = get_invoice(invoice_id) if invoice_id else None
        status = str((current or {}).get("status") or "")
        current_job_id = str((current or {}).get("erp_job_id") or "")
        if current and status == ERP_QUEUED and current_job_id == job_id:
            active.append(item)
        else:
            stale.append({"id": invoice_id, "status": status or "missing", "erp_job_id": current_job_id})
    return active, stale


def claim_next_erp_task(agent_id: str, capabilities: dict[str, Any] | None = None, client_ip: str = "") -> dict[str, Any] | None:
    with _task_index_lock:
        agent_id = str(agent_id or "").strip() or "unknown-agent"
        client_ip = str(client_ip or "").strip()
        capabilities = capabilities or {}
        for path in _task_files():
            payload = _read_task(path)
            job_type = str(payload.get("job_type") or "")
            if job_type not in TASK_TYPES:
                _forget_task(path)
                continue
            agent_status = str(payload.get("agent_status") or "pending")
            if job_type == "output_print" and agent_status == "claimed":
                age = _age_seconds(payload.get("updated_at") or payload.get("claimed_at"))
                if age is not None and age >= OUTPUT_PRINT_CLAIM_STALE_SECONDS:
                    payload["agent_status"] = "retry"
                    payload["updated_at"] = now_text()
                    payload["stale_reason"] = "Output print Agent claim expired; resume unconfirmed files"
                    _write_task(path, payload)
                    agent_status = "retry"
            if agent_status not in ACTIONABLE_AGENT_STATUSES:
                # Keep a claimed print task for its bounded stale retry; every
                # other terminal/non-actionable file leaves the hot index.
                if not (job_type == "output_print" and agent_status == "claimed"):
                    _forget_task(path)
                continue
            if not str(payload.get("created_at") or "").strip():
                payload["agent_status"] = "stale"
                payload["updated_at"] = now_text()
                payload["stale_reason"] = "Legacy queue file has no created_at; requeue from WEB to run"
                _write_task(path, payload)
                _forget_task(path)
                continue
            target_agent_id = str(payload.get("target_agent_id") or "").strip()
            target_client_ip = str(payload.get("target_client_ip") or "").strip()
            if not target_agent_id or not target_client_ip:
                payload["agent_status"] = "stale"
                payload["updated_at"] = now_text()
                payload["stale_reason"] = "Queue has no target_agent_id/target_client_ip; requeue from WEB to bind target PC"
                _write_task(path, payload)
                _forget_task(path)
                continue
            if target_agent_id != agent_id or target_client_ip != client_ip:
                continue
            if job_type == "expense_report":
                invoice_id = int(payload.get("invoice_id") or 0)
                if not invoice_id or not get_invoice(invoice_id):
                    payload["agent_status"] = "stale"
                    payload["updated_at"] = now_text()
                    payload["stale_reason"] = "Expense report invoice is missing"
                    _write_task(path, payload)
                    _forget_task(path)
                    continue
                payload["agent_status"] = "claimed"
                payload["agent_id"] = agent_id
                payload["claimed_at"] = now_text()
                payload["capabilities"] = capabilities or {}
                payload["queue_path"] = str(path)
                _write_task(path, payload)
                _forget_task(path)
                return payload
            if job_type == "output_print":
                if not bool(capabilities.get("output_print")):
                    continue
                if not payload.get("print_files"):
                    payload["agent_status"] = "stale"
                    payload["updated_at"] = now_text()
                    payload["stale_reason"] = "Output print task has no files"
                    _write_task(path, payload)
                    _forget_task(path)
                    continue
                payload["agent_status"] = "claimed"
                payload["agent_id"] = agent_id
                payload["claimed_at"] = now_text()
                payload["capabilities"] = capabilities
                payload["queue_path"] = str(path)
                _write_task(path, payload)
                return payload
            active_invoices, stale_invoices = _active_invoice_items(payload)
            if not active_invoices:
                payload["agent_status"] = "stale"
                payload["updated_at"] = now_text()
                payload["stale_reason"] = "No ERP_QUEUED invoices remain"
                payload["stale_invoices"] = stale_invoices
                _write_task(path, payload)
                _forget_task(path)
                continue
            if stale_invoices:
                payload["invoices"] = active_invoices
                payload["stale_invoices"] = stale_invoices
            payload["agent_status"] = "claimed"
            payload["agent_id"] = agent_id
            payload["claimed_at"] = now_text()
            payload["capabilities"] = capabilities or {}
            payload["queue_path"] = str(path)
            _write_task(path, payload)
            _forget_task(path)
            return payload
        return None


def update_erp_task(job_id: str, status: str, update: dict[str, Any] | None = None) -> dict[str, Any]:
    candidates = [
        queue_dir() / f"purchase_erp_{job_id}.json",
        queue_dir() / f"regular_erp_{job_id}.json",
        queue_dir() / f"expense_report_{job_id}.json",
        queue_dir() / f"output_print_{job_id}.json",
    ]
    path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    payload = _read_task(path) if path.exists() else {"job_id": job_id, "job_type": "purchase_erp_input"}
    payload["agent_status"] = status
    payload["updated_at"] = now_text()
    if update:
        payload.update(update)
    _write_task(path, payload)
    return payload
