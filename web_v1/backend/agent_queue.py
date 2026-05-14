from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .erp_queue import queue_dir
from .invoice_db import ERP_QUEUED, get_invoice


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _task_files() -> list[Path]:
    return sorted(queue_dir().glob("*.json"), key=lambda path: path.stat().st_mtime)


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
    agent_id = str(agent_id or "").strip() or "unknown-agent"
    client_ip = str(client_ip or "").strip()
    capabilities = capabilities or {}
    for path in _task_files():
        payload = _read_task(path)
        job_type = str(payload.get("job_type") or "")
        if job_type not in {"purchase_erp_input", "regular_erp_input", "expense_report", "output_print"}:
            continue
        if str(payload.get("agent_status") or "pending") not in {"", "pending", "retry"}:
            continue
        if not str(payload.get("created_at") or "").strip():
            payload["agent_status"] = "stale"
            payload["updated_at"] = now_text()
            payload["stale_reason"] = "Legacy queue file has no created_at; requeue from WEB to run"
            _write_task(path, payload)
            continue
        target_agent_id = str(payload.get("target_agent_id") or "").strip()
        target_client_ip = str(payload.get("target_client_ip") or "").strip()
        if not target_agent_id or not target_client_ip:
            payload["agent_status"] = "stale"
            payload["updated_at"] = now_text()
            payload["stale_reason"] = "Queue has no target_agent_id/target_client_ip; requeue from WEB to bind target PC"
            _write_task(path, payload)
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
                continue
            payload["agent_status"] = "claimed"
            payload["agent_id"] = agent_id
            payload["claimed_at"] = now_text()
            payload["capabilities"] = capabilities or {}
            payload["queue_path"] = str(path)
            _write_task(path, payload)
            return payload
        if job_type == "output_print":
            if not bool(capabilities.get("output_print")):
                continue
            if not payload.get("print_files"):
                payload["agent_status"] = "stale"
                payload["updated_at"] = now_text()
                payload["stale_reason"] = "Output print task has no files"
                _write_task(path, payload)
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
