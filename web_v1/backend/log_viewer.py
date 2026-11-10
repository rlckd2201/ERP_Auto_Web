"""Authenticated, read-only processing logs; raw DB access is owner-only."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from .browser_session import SESSION_HEADER, resolve_browser_session
from .config import settings
from .job_store import job_store

router = APIRouter(prefix="/api/logs")
DB_VIEWER_USER = "rlckd9646"
LogSource = Literal["all", "purchase", "regular", "jobs"]


def require_log_viewer(request: Request) -> dict:
    # Never authorize from a user_id parameter, forwarded IP, or browser storage.
    # The portal host verifies its signed identity and places it in request.state,
    # exactly as consumed by app._browser_identity. This is not an HTTP header.
    identity = getattr(request.state, "accounting_identity", None)
    if identity is not None:
        if not isinstance(identity, dict) or not isinstance(identity.get("user_id"), str) or not identity["user_id"]:
            raise HTTPException(401, "로그인이 필요합니다.")
        return identity
    identity = resolve_browser_session(request.headers.get(SESSION_HEADER, ""))
    request.state.accounting_identity = identity
    return identity


def require_db_viewer(request: Request) -> dict:
    identity = require_log_viewer(request)
    if identity["user_id"] != DB_VIEWER_USER:
        raise HTTPException(403, "DB 보기는 지정된 관리자 계정만 사용할 수 있습니다.")
    return identity


def readonly_db() -> sqlite3.Connection:
    if not settings.sqlite_db_path.is_file():
        raise HTTPException(404, "조회할 데이터가 없습니다.")
    conn = sqlite3.connect(settings.sqlite_db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


_INVOICE_TYPE = "COALESCE(json_extract(CASE WHEN json_valid(i.json_data) THEN i.json_data ELSE '{}' END, '$.invoice_type'), '')"
_LOG_COLUMNS = ["created_at", "invoice_id", "invoice_type", "subject", "level", "message", "job_id"]
_LOG_LABELS = {"created_at": "일시", "invoice_id": "전표 번호", "invoice_type": "처리 구분",
               "subject": "수신 제목", "level": "상태", "message": "내용", "job_id": "작업 번호"}
_JOB_COLUMNS = ["created_at", "title", "status", "progress", "message", "job_id"]
_JOB_LABELS = {"created_at": "일시", "title": "작업", "status": "상태", "progress": "진행률",
               "message": "내용", "job_id": "작업 번호"}


def _job_rows() -> list[dict]:
    rows = []
    for job in job_store.list_recent(limit=50):
        for event in reversed(list(job.events)):
            rows.append({"created_at": event.created_at.isoformat(), "title": job.title,
                         "status": event.status, "progress": event.progress,
                         "message": event.message, "job_id": job.id})
    return sorted(rows, key=lambda row: row["created_at"], reverse=True)


@router.get("/overview")
def log_overview(request: Request) -> dict:
    require_log_viewer(request)
    with closing(readonly_db()) as conn:
        counts = {str(row["mode"]): row["count"] for row in conn.execute(
            f"SELECT {_INVOICE_TYPE} AS mode, COUNT(*) AS count FROM invoice_logs l "
            "LEFT JOIN invoices i ON i.id = l.invoice_id GROUP BY mode")}
    return {"tables": [
        {"name": "all", "label": "전체 처리 로그", "count": sum(counts.values())},
        {"name": "purchase", "label": "구매 처리", "count": counts.get("purchase", 0)},
        {"name": "regular", "label": "정기 처리", "count": counts.get("regular", 0)},
        {"name": "jobs", "label": "최근 작업", "count": len(_job_rows())},
    ]}


@router.get("/table")
def log_table(request: Request, table: LogSource = "all",
              q: str = Query(default="", max_length=200),
              limit: int = Query(default=100, ge=1, le=500),
              offset: int = Query(default=0, ge=0)) -> dict:
    require_log_viewer(request)
    keyword = q.strip()
    if table == "jobs":
        rows = _job_rows()
        if keyword:
            rows = [row for row in rows if any(keyword.casefold() in str(v).casefold() for v in row.values())]
        return {"table": table, "columns": _JOB_COLUMNS, "column_labels": _JOB_LABELS,
                "rows": rows[offset:offset + limit], "total": len(rows), "limit": limit, "offset": offset}
    conditions, params = [], []
    if table != "all":
        conditions.append(f"{_INVOICE_TYPE} = ?")
        params.append(table)
    if keyword:
        if keyword.startswith("#") and keyword[1:].isdigit():
            conditions.append("l.invoice_id = ?")
            params.append(int(keyword[1:]))
        else:
            conditions.append("(" + " OR ".join(f"CAST({col} AS TEXT) LIKE ?" for col in
                ("l.invoice_id", "i.subject", "l.message", "l.level", "l.job_id", "l.created_at")) + ")")
            params.extend([f"%{keyword}%"] * 6)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    join = " FROM invoice_logs l LEFT JOIN invoices i ON i.id = l.invoice_id"
    with closing(readonly_db()) as conn:
        # A read transaction keeps the count and page consistent during live processing.
        conn.execute("BEGIN")
        total = conn.execute("SELECT COUNT(*)" + join + where, params).fetchone()[0]
        rows = [dict(row) for row in conn.execute(
            f"SELECT l.created_at, l.invoice_id, {_INVOICE_TYPE} AS invoice_type, "
            "COALESCE(i.subject, '') AS subject, l.level, l.message, l.job_id" + join + where +
            " ORDER BY l.id DESC LIMIT ? OFFSET ?", [*params, limit, offset])]
    return {"table": table, "columns": _LOG_COLUMNS, "column_labels": _LOG_LABELS,
            "rows": rows, "total": total, "limit": limit, "offset": offset}
