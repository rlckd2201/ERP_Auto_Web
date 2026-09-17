from __future__ import annotations

from datetime import datetime

from app.main import _public_job_dump
from app.models import JobRecord
from app.storage import JobStore


def test_verification_request_visible_without_exposing_code(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    now = datetime(2026, 9, 17, 9, 0)
    job = JobRecord(
        id="verification-job",
        title="ERP voucher",
        requester="requester",
        company_key="daeseung",
        accounting_date="2026-09-20",
        source_filename="source.xlsx",
        status="running",
        progress=40,
        message="ERP email verification code required",
        target_agent_id="finance-agent",
        target_client_ip="127.0.0.1",
        created_at=now,
        updated_at=now,
        result={"verification_required": True},
    )
    public = _public_job_dump(job)
    assert public["result"]["verification_required"] is True

    stored = {**job.result, "verification_code": "12345"}
    public_with_code = _public_job_dump(job.model_copy(update={"result": stored}))
    assert "verification_code" not in public_with_code["result"]

    with store.connect() as conn:
        conn.execute(
            "INSERT INTO jobs (id, title, status, progress, message, result_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (job.id, job.title, job.status, job.progress, job.message, '{"verification_required":true}', now.isoformat(), now.isoformat()),
        )
    store.set_verification_code(job.id, "12345")
    assert store.consume_verification_code(job.id) == "12345"
    assert store.consume_verification_code(job.id) == ""
    assert store.get_job(job.id).result["verification_required"] is False
