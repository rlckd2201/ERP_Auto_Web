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
    management_items: dict[str, str] = Field(default_factory=dict)
    vendor_name: str = ""
    vendor_code: str = ""
    department: str = ""
    original_summary: str = ""
    payment_date: str = ""
    source_sheet: str = ""
    source_row: int | None = None


class BankTransfer(BaseModel):
    seq: int
    bank_code: str = ""
    account_no: str = ""
    depositor: str = ""
    amount: int
    company_name: str = ""
    source_sheet: str = "인터넷뱅킹"
    source_row: int | None = None


class VoucherPayload(BaseModel):
    job_type: Literal["excel_voucher"] = "excel_voucher"
    accounting_date: str
    voucher_month_label: str
    company_key: str
    company_name: str
    erp_site_name: str = ""
    requester: str
    requester_id: str = ""
    requester_email: str = ""
    source_filename: str
    source_format: str = "generic_excel"
    source_row_count: int = 0
    header_total: int = 0
    debit_total: int
    credit_total: int
    line_count: int
    lines: list[VoucherLine]
    cash_processing_enabled: bool = False
    resume_print_only: bool = False
    resume_management_save_print: bool = False
    erp_line_management_items: list[dict[str, str]] = Field(default_factory=list)
    erp_credentials: dict[str, str] = Field(default_factory=dict)
    bank_transfers: list[BankTransfer] = Field(default_factory=list)
    erp_clipboard_rows: list[str] = Field(default_factory=list)
    source_columns: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


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


class AdminResetJobsRequest(BaseModel):
    clear_uploads: bool = True


class AdminAgentCommandRequest(BaseModel):
    command: Literal["tail-log", "update-agent", "restart-agent"]
    target_agent_id: str = Field(default="", max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentAdminCommandCompleteRequest(BaseModel):
    agent_id: str = Field(default="", max_length=160)
    ok: bool = True
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = Field(default="", max_length=4000)


class LoginRequest(BaseModel):
    user_id: str = Field(default="", max_length=160)
    password: str = Field(default="", max_length=200)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(default="", max_length=200)
    new_password: str = Field(default="", min_length=8, max_length=200)


class ForgotPasswordRequest(BaseModel):
    user_id: str = Field(default="", max_length=160)


class ErpCredentialRequest(BaseModel):
    erp_user_id: str = Field(default="", max_length=160)
    erp_password: str = Field(default="", max_length=200)
