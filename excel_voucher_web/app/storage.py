from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import AgentHeartbeat, JobEvent, JobRecord, JobStatus, VoucherPayload
from .settings import ManagerProfile


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class JobStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    requester TEXT NOT NULL DEFAULT '',
                    company_key TEXT NOT NULL DEFAULT '',
                    accounting_date TEXT NOT NULL DEFAULT '',
                    source_filename TEXT NOT NULL DEFAULT '',
                    source_path TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'queued',
                    progress INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT '',
                    target_agent_id TEXT NOT NULL DEFAULT '',
                    target_client_ip TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    claimed_at TEXT,
                    finished_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_profiles (
                    agent_id TEXT PRIMARY KEY,
                    client_ip TEXT NOT NULL DEFAULT '',
                    agent_host TEXT NOT NULL DEFAULT '',
                    agent_user TEXT NOT NULL DEFAULT '',
                    capabilities_json TEXT NOT NULL DEFAULT '{}',
                    last_seen TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_job_events_job_id ON job_events(job_id, id)")

    def create_job(
        self,
        *,
        payload: VoucherPayload,
        source_path: Path,
        manager: ManagerProfile,
    ) -> JobRecord:
        job_id = uuid.uuid4().hex[:12]
        created = now_text()
        title = f"{payload.company_name} {payload.accounting_date} 수시결제 전표"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, title, requester, company_key, accounting_date, source_filename,
                    source_path, status, progress, message, target_agent_id, target_client_ip,
                    payload_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', 5, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    title,
                    payload.requester,
                    payload.company_key,
                    payload.accounting_date,
                    payload.source_filename,
                    str(source_path),
                    "엑셀 업로드 완료, Agent 대기 중",
                    manager.agent_id,
                    manager.agent_ip,
                    _json_dumps(payload.model_dump(mode="json")),
                    created,
                    created,
                ),
            )
            self._add_event_conn(conn, job_id, "queued", 5, "서버 작업 큐 등록")
        return self.get_job(job_id)

    def _row_to_job(self, row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            id=row["id"],
            title=row["title"],
            requester=row["requester"] or "",
            company_key=row["company_key"] or "",
            accounting_date=row["accounting_date"] or "",
            source_filename=row["source_filename"] or "",
            status=row["status"],
            progress=int(row["progress"] or 0),
            message=row["message"] or "",
            target_agent_id=row["target_agent_id"] or "",
            target_client_ip=row["target_client_ip"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            claimed_at=datetime.fromisoformat(row["claimed_at"]) if row["claimed_at"] else None,
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            payload=_json_loads(row["payload_json"]),
            result=_json_loads(row["result_json"]),
            error=row["error"] or "",
        )

    def get_job(self, job_id: str) -> JobRecord:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise KeyError(job_id)
        return self._row_to_job(row)

    def get_source_path(self, job_id: str) -> Path:
        with self.connect() as conn:
            row = conn.execute("SELECT source_path FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise KeyError(job_id)
        return Path(row["source_path"])

    def list_jobs(self, limit: int = 100) -> list[JobRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY datetime(created_at) DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def list_events(self, job_id: str) -> list[JobEvent]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM job_events WHERE job_id = ? ORDER BY id ASC",
                (job_id,),
            ).fetchall()
        return [
            JobEvent(
                id=int(row["id"]),
                job_id=row["job_id"],
                status=row["status"],
                progress=int(row["progress"] or 0),
                message=row["message"] or "",
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def get_agent_profile(self, agent_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM agent_profiles WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "agent_id": row["agent_id"],
            "client_ip": row["client_ip"] or "",
            "agent_host": row["agent_host"] or "",
            "agent_user": row["agent_user"] or "",
            "capabilities": _json_loads(row["capabilities_json"]),
            "last_seen": row["last_seen"] or "",
        }

    def _add_event_conn(
        self,
        conn: sqlite3.Connection,
        job_id: str,
        status: JobStatus,
        progress: int,
        message: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO job_events (job_id, status, progress, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, status, max(0, min(int(progress), 100)), str(message or ""), now_text()),
        )

    def add_event(self, job_id: str, status: JobStatus, progress: int, message: str) -> None:
        with self.connect() as conn:
            self._add_event_conn(conn, job_id, status, progress, message)

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        finished: bool = False,
    ) -> JobRecord:
        current = self.get_job(job_id)
        next_status = status or current.status
        next_progress = current.progress if progress is None else max(0, min(int(progress), 100))
        next_message = current.message if message is None else str(message)
        next_result = current.result if result is None else result
        next_error = current.error if error is None else str(error)
        updated = now_text()
        finished_at = updated if finished else (current.finished_at.isoformat(timespec="seconds") if current.finished_at else None)
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, progress = ?, message = ?, result_json = ?, error = ?,
                    updated_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (
                    next_status,
                    next_progress,
                    next_message,
                    _json_dumps(next_result),
                    next_error,
                    updated,
                    finished_at,
                    job_id,
                ),
            )
            self._add_event_conn(conn, job_id, next_status, next_progress, next_message)
        return self.get_job(job_id)

    def record_heartbeat(self, heartbeat: AgentHeartbeat, client_ip: str) -> dict[str, Any]:
        agent_id = (heartbeat.agent_id or "").strip() or "unknown-agent"
        effective_ip = (heartbeat.client_ip or client_ip or "").strip()
        seen = now_text()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_profiles (
                    agent_id, client_ip, agent_host, agent_user, capabilities_json, last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    client_ip = excluded.client_ip,
                    agent_host = excluded.agent_host,
                    agent_user = excluded.agent_user,
                    capabilities_json = excluded.capabilities_json,
                    last_seen = excluded.last_seen
                """,
                (
                    agent_id,
                    effective_ip,
                    heartbeat.agent_host,
                    heartbeat.agent_user,
                    _json_dumps(heartbeat.capabilities),
                    seen,
                ),
            )
        return {
            "agent_id": agent_id,
            "client_ip": effective_ip,
            "agent_host": heartbeat.agent_host,
            "agent_user": heartbeat.agent_user,
            "last_seen": seen,
        }

    def claim_next(self, heartbeat: AgentHeartbeat, client_ip: str) -> JobRecord | None:
        agent_id = (heartbeat.agent_id or "").strip() or "unknown-agent"
        effective_ip = (heartbeat.client_ip or client_ip or "").strip()
        claimed = now_text()
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'queued'
                  AND (target_agent_id = '' OR target_agent_id = ?)
                  AND (target_client_ip = '' OR target_client_ip = ? OR target_agent_id = ?)
                ORDER BY datetime(created_at) ASC
                LIMIT 1
                """,
                (agent_id, effective_ip, agent_id),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE jobs
                SET status = 'claimed', progress = 15, message = ?, updated_at = ?, claimed_at = ?
                WHERE id = ? AND status = 'queued'
                """,
                (f"자동처리 PC 작업 시작: {agent_id}", claimed, claimed, row["id"]),
            )
            self._add_event_conn(conn, row["id"], "claimed", 15, f"자동처리 PC 작업 시작: {agent_id}")
        return self.get_job(row["id"])
