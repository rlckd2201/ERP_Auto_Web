from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .models import JobCreateRequest, JobEventResponse, JobResponse, JobStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobEvent:
    seq: int
    status: JobStatus
    progress: int
    message: str
    created_at: datetime = field(default_factory=utc_now)

    def to_response(self) -> JobEventResponse:
        return JobEventResponse(
            seq=self.seq,
            status=self.status,
            progress=self.progress,
            message=self.message,
            created_at=self.created_at,
        )


@dataclass
class JobRecord:
    id: str
    job_type: str
    title: str
    payload: dict[str, Any]
    status: JobStatus = "queued"
    progress: int = 0
    message: str = "queued"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    events: list[JobEvent] = field(default_factory=list)

    def to_response(self) -> JobResponse:
        return JobResponse(
            id=self.id,
            job_type=self.job_type,
            title=self.title,
            status=self.status,
            progress=self.progress,
            message=self.message,
            created_at=self.created_at,
            updated_at=self.updated_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            payload=self.payload,
            result=self.result,
            error=self.error,
            events=[event.to_response() for event in self.events],
        )


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, JobRecord] = {}

    def create(self, request: JobCreateRequest) -> JobRecord:
        job = JobRecord(
            id=str(uuid.uuid4()),
            job_type=request.job_type,
            title=request.title,
            payload=dict(request.payload or {}),
        )
        with self._lock:
            self._jobs[job.id] = job
            self.add_event(job.id, "queued", 0, "Job queued")
        return job

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_recent(self, limit: int = 10) -> list[JobRecord]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_at, reverse=True)
            return jobs[:limit]

    def add_event(self, job_id: str, status: JobStatus, progress: int, message: str) -> JobEvent:
        with self._lock:
            job = self._jobs[job_id]
            progress = max(0, min(100, int(progress)))
            event = JobEvent(
                seq=len(job.events),
                status=status,
                progress=progress,
                message=message,
            )
            job.status = status
            job.progress = progress
            job.message = message
            job.updated_at = event.created_at
            if status == "running" and job.started_at is None:
                job.started_at = event.created_at
            if status in {"done", "error"}:
                job.finished_at = event.created_at
            job.events.append(event)
            return event

    def set_result(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            self._jobs[job_id].result = dict(result or {})

    def set_error(self, job_id: str, error: str) -> None:
        with self._lock:
            self._jobs[job_id].error = str(error or "")

    def events_after(self, job_id: str, last_seq: int) -> list[JobEvent]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return []
            return [event for event in job.events if event.seq > last_seq]


job_store = JobStore()
