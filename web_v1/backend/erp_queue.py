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


def _write_erp_queue(
    job_id: str,
    invoices: list[dict[str, Any]],
    *,
    job_type: str,
    filename_prefix: str,
    target_agent_id: str = "",
    target_client_ip: str = "",
    source_job_payload: dict[str, Any] | None = None,
) -> Path:
    payload = {
        "job_id": job_id,
        "job_type": job_type,
        "agent_status": "pending",
        "agent_id": "",
        "target_agent_id": str(target_agent_id or ""),
        "target_client_ip": str(target_client_ip or ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "invoice_count": len(invoices),
        "invoices": invoices,
    }
    if source_job_payload:
        payload["source_job_payload"] = dict(source_job_payload)
    path = queue_dir() / f"{filename_prefix}_{job_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_purchase_erp_queue(
    job_id: str,
    invoices: list[dict[str, Any]],
    *,
    target_agent_id: str = "",
    target_client_ip: str = "",
    source_job_payload: dict[str, Any] | None = None,
) -> Path:
    return _write_erp_queue(
        job_id,
        invoices,
        job_type="purchase_erp_input",
        filename_prefix="purchase_erp",
        target_agent_id=target_agent_id,
        target_client_ip=target_client_ip,
        source_job_payload=source_job_payload,
    )


def write_regular_erp_queue(
    job_id: str,
    invoices: list[dict[str, Any]],
    *,
    target_agent_id: str = "",
    target_client_ip: str = "",
    source_job_payload: dict[str, Any] | None = None,
) -> Path:
    return _write_erp_queue(
        job_id,
        invoices,
        job_type="regular_erp_input",
        filename_prefix="regular_erp",
        target_agent_id=target_agent_id,
        target_client_ip=target_client_ip,
        source_job_payload=source_job_payload,
    )


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


def write_output_print_queue(
    job_id: str,
    results: list[dict[str, Any]],
    *,
    printer_name: str,
    printer_key: str = "",
    target_agent_id: str = "",
    target_client_ip: str = "",
    source_job_id: str = "",
    regular_auto: bool = False,
) -> Path:
    print_files: list[dict[str, Any]] = []
    invoice_ids: list[int] = []
    for result in results:
        try:
            invoice_id = int(result.get("invoice_id") or 0)
        except Exception:
            invoice_id = 0
        if not invoice_id:
            continue
        if invoice_id not in invoice_ids:
            invoice_ids.append(invoice_id)
        for index, file_path in enumerate(result.get("individual_files") or [], start=1):
            path = Path(str(file_path))
            print_files.append(
                {
                    "invoice_id": invoice_id,
                    "file_index": index,
                    "path": str(path),
                    "filename": path.name,
                }
            )
    if not print_files:
        raise RuntimeError("출력할 문서 세트 PDF가 없습니다.")
    payload = {
        "job_id": job_id,
        "job_type": "output_print",
        "agent_status": "pending",
        "agent_id": "",
        "target_agent_id": str(target_agent_id or ""),
        "target_client_ip": str(target_client_ip or ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "invoice_ids": invoice_ids,
        "invoice_count": len(invoice_ids),
        "printer_key": str(printer_key or ""),
        "printer_name": str(printer_name or ""),
        "source_job_id": str(source_job_id or ""),
        "regular_auto": bool(regular_auto),
        "print_files": print_files,
    }
    path = queue_dir() / f"output_print_{job_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
