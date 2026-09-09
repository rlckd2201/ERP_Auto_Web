from __future__ import annotations

import json
from pathlib import Path

from web_v1.backend import agent_queue


def _write_task(path: Path, *, status: str, target: str = "other-agent") -> None:
    path.write_text(
        json.dumps(
            {
                "job_id": path.stem,
                "job_type": "output_print",
                "agent_status": status,
                "target_agent_id": target,
                "target_client_ip": "10.0.0.1",
                "created_at": "2026-09-09T12:00:00",
                "print_files": [{"path": "document.pdf"}],
            }
        ),
        encoding="utf-8",
    )


def test_task_index_reopens_only_actionable_files_after_initial_scan(tmp_path, monkeypatch):
    for index in range(120):
        _write_task(tmp_path / f"done_{index:03d}.json", status="done")
    pending = tmp_path / "pending.json"
    _write_task(pending, status="pending")

    monkeypatch.setattr(agent_queue, "queue_dir", lambda: tmp_path)
    agent_queue._reset_task_index(tmp_path)
    original_read = agent_queue._read_task
    reads: list[str] = []

    def tracked_read(path: Path):
        reads.append(path.name)
        return original_read(path)

    monkeypatch.setattr(agent_queue, "_read_task", tracked_read)

    assert agent_queue.claim_next_erp_task("no-match", {}, "10.0.0.2") is None
    assert len(reads) == 122

    reads.clear()
    assert agent_queue.claim_next_erp_task("no-match", {}, "10.0.0.2") is None
    assert reads == ["pending.json"]


def test_task_index_discovers_new_file_without_reopening_history(tmp_path, monkeypatch):
    old_done = tmp_path / "old_done.json"
    _write_task(old_done, status="error")
    monkeypatch.setattr(agent_queue, "queue_dir", lambda: tmp_path)
    agent_queue._reset_task_index(tmp_path)

    assert agent_queue._task_files() == []

    new_pending = tmp_path / "new_pending.json"
    _write_task(new_pending, status="pending")
    assert agent_queue._task_files() == [new_pending]


def test_claimed_output_print_remains_indexed_for_stale_recovery(tmp_path, monkeypatch):
    claimed = tmp_path / "claimed.json"
    _write_task(claimed, status="claimed")
    payload = json.loads(claimed.read_text(encoding="utf-8"))
    payload["claimed_at"] = "2026-09-09T11:00:00"
    claimed.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(agent_queue, "queue_dir", lambda: tmp_path)
    monkeypatch.setattr(agent_queue, "now_text", lambda: "2026-09-09 12:00:00")
    monkeypatch.setattr(agent_queue, "_age_seconds", lambda value: 3600.0)
    agent_queue._reset_task_index(tmp_path)

    task = agent_queue.claim_next_erp_task(
        "other-agent",
        {"output_print": True},
        "10.0.0.1",
    )

    assert task is not None
    assert task["agent_status"] == "claimed"
    assert task["stale_reason"] == "Output print Agent claim expired; resume unconfirmed files"
