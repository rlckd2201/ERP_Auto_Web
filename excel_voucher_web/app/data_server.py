from __future__ import annotations

from typing import Any

import requests

from .models import JobRecord
from .settings import settings


def data_server_target_url() -> str:
    base = settings.data_server_url.rstrip("/")
    endpoint = settings.data_server_endpoint.strip() or "/api/excel-voucher/jobs"
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    return f"{base}{endpoint}"


def _voucher_for_data_server(payload: dict[str, Any]) -> dict[str, Any]:
    voucher = dict(payload or {})
    voucher.pop("erp_credentials", None)
    return voucher


def forward_job_to_data_server(job: JobRecord) -> dict[str, Any]:
    url = data_server_target_url()
    payload = {
        "job_id": job.id,
        "job_type": "excel_voucher",
        "status": job.status,
        "accounting_date": job.accounting_date,
        "requester": job.requester,
        "company_key": job.company_key,
        "source_filename": job.source_filename,
        "target_agent_id": job.target_agent_id,
        "target_client_ip": job.target_client_ip,
        "voucher": _voucher_for_data_server(job.payload),
    }
    try:
        response = requests.post(url, json=payload, timeout=settings.data_server_timeout_seconds)
        text = response.text[:1000]
        return {
            "ok": 200 <= response.status_code < 300,
            "url": url,
            "status_code": response.status_code,
            "response": text,
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "error": str(exc),
        }
