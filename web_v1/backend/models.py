from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


JobStatus = Literal["queued", "running", "crawling", "analyzing", "erp", "printing", "done", "error"]


class JobCreateRequest(BaseModel):
    job_type: str = Field(default="demo", min_length=1, max_length=80)
    title: str = Field(default="WEB v1.0 demo job", max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)


class InvoiceIdsRequest(BaseModel):
    invoice_ids: list[int] = Field(default_factory=list)
    processor: str = Field(default="WEB v1.0", max_length=80)
    output_target: Literal["pdf", "pyeongtaek", "gimje"] = "pdf"


class OutputSetRequest(BaseModel):
    invoice_ids: list[int] = Field(default_factory=list)
    action: Literal["merged_pdf", "individual_pdf", "print_individual"] = "merged_pdf"
    printer_key: Literal["pyeongtaek", "gimje", "pdf"] = "pdf"
    processor: str = Field(default="WEB v1.0", max_length=80)
    existing_only: bool = False


class PurchaseAnalysisUpdate(BaseModel):
    site_name: str = Field(default="", max_length=80)
    vendor_name: str = Field(default="", max_length=120)
    invoice_date: str = Field(default="", max_length=20)
    order_no: str = Field(default="", max_length=30)
    target_supply: int = 0
    total_tax: int = 0
    total_sum: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)
    approval_pdf_paths: list[str] = Field(default_factory=list)


class RegularDataUpdate(BaseModel):
    site_name: str = Field(default="", max_length=80)
    vendor_name: str = Field(default="", max_length=120)
    invoice_date: str = Field(default="", max_length=20)
    target_supply: int = 0
    total_tax: int = 0
    total_sum: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)


class JobEventResponse(BaseModel):
    seq: int
    status: JobStatus
    progress: int
    message: str
    created_at: datetime


class JobResponse(BaseModel):
    id: str
    job_type: str
    title: str
    status: JobStatus
    progress: int
    message: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    events: list[JobEventResponse] = Field(default_factory=list)
