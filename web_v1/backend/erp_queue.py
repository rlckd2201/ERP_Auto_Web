from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import settings


def queue_dir() -> Path:
    path = settings.erp_db_dir / "erp_queue"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_purchase_erp_queue(
    job_id: str,
    invoices: list[dict[str, Any]],
    *,
    target_agent_id: str = "",
    target_client_ip: str = "",
) -> Path:
    payload = {
        "job_id": job_id,
        "job_type": "purchase_erp_input",
        "agent_status": "pending",
        "agent_id": "",
        "target_agent_id": str(target_agent_id or ""),
        "target_client_ip": str(target_client_ip or ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "invoice_count": len(invoices),
        "invoices": invoices,
    }
    path = queue_dir() / f"purchase_erp_{job_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_expense_report_queue(
    job_id: str,
    invoice: dict[str, Any],
    *,
    target_agent_id: str = "",
    target_client_ip: str = "",
) -> Path:
    payload = {
        "job_id": job_id,
        "job_type": "expense_report",
        "agent_status": "pending",
        "agent_id": "",
        "target_agent_id": str(target_agent_id or ""),
        "target_client_ip": str(target_client_ip or ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "invoice_id": int(invoice.get("id") or 0),
        "invoice": invoice,
    }
    path = queue_dir() / f"expense_report_{job_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
