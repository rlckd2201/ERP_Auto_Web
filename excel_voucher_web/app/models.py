from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


JobStatus = Literal["queued", "claimed", "running", "done", "error", "cancelled"]


class VoucherLine(BaseModel):
    seq: int
    side: Literal["debit", "credit"]
    account_name: str
    amount: int
    summary: str
    vendor_name: str = ""
    vendor_code: str = ""
    source_row: int | None = None


class VoucherPayload(BaseModel):
    job_type: Literal["excel_voucher"] = "excel_voucher"
    accounting_date: str
    company_key: str
    company_name: str
    requester: str
    source_filename: str
    debit_total: int
    credit_total: int
    line_count: int
    lines: list[VoucherLine]
    source_columns: dict[str, str] = Field(default_factory=dict)


class JobRecord(BaseModel):
    id: str
    title: str
    requester: str
    company_key: str
    accounting_date: str
    source_filename: str
    status: JobStatus
    progress: int
    message: str
    target_agent_id: str
    target_client_ip: str
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None = None
    finished_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class JobEvent(BaseModel):
    id: int
    job_id: str
    status: JobStatus
    progress: int
    message: str
    created_at: datetime


class AgentHeartbeat(BaseModel):
    agent_id: str = Field(default="", max_length=160)
    agent_host: str = Field(default="", max_length=160)
    agent_user: str = Field(default="", max_length=160)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    client_ip: str = Field(default="", max_length=80)


class AgentEventRequest(BaseModel):
    agent_id: str = Field(default="", max_length=160)
    status: JobStatus = "running"
    progress: int = Field(default=50, ge=0, le=100)
    message: str = Field(default="", max_length=500)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = Field(default="", max_length=2000)


class AgentCompleteRequest(BaseModel):
    agent_id: str = Field(default="", max_length=160)
    ok: bool = True
    message: str = Field(default="", max_length=500)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = Field(default="", max_length=2000)
