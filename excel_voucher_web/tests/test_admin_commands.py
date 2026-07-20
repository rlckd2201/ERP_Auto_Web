from __future__ import annotations

from pathlib import Path

from app.models import AgentHeartbeat
from app.storage import JobStore


ROOT = Path(__file__).resolve().parents[1]


def test_agent_admin_command_lifecycle(tmp_path):
    store = JobStore(tmp_path / "admin_commands.sqlite3")

    created = store.create_agent_command(
        command="tail-log",
        target_agent_id="finance-agent-172-17-30-243",
        payload={},
        created_by="admin",
    )

    assert created["status"] == "queued"

    claimed = store.claim_next_agent_command(
        AgentHeartbeat(agent_id="finance-agent-172-17-30-243", client_ip="172.17.30.243"),
        "172.17.30.243",
    )

    assert claimed is not None
    assert claimed["id"] == created["id"]
    assert claimed["status"] == "running"

    completed = store.complete_agent_command(
        created["id"],
        ok=True,
        result={"message": "ok"},
    )

    assert completed["status"] == "done"
    assert completed["result"]["message"] == "ok"


def test_clear_jobs_preserves_agent_admin_commands(tmp_path):
    store = JobStore(tmp_path / "admin_commands.sqlite3")
    store.create_agent_command(
        command="restart-agent",
        target_agent_id="finance-agent-172-17-30-243",
        payload={},
        created_by="admin",
    )

    cleared = store.clear_jobs()

    assert cleared == {"jobs": 0, "events": 0}
    assert len(store.list_agent_commands()) == 1


def test_agent_admin_command_claim_can_filter_by_command(tmp_path):
    store = JobStore(tmp_path / "admin_commands.sqlite3")
    store.create_agent_command(
        command="update-agent",
        target_agent_id="finance-agent-172-17-30-243",
        payload={},
        created_by="admin",
    )
    tail = store.create_agent_command(
        command="tail-log",
        target_agent_id="finance-agent-172-17-30-243",
        payload={},
        created_by="admin",
    )

    claimed = store.claim_next_agent_command(
        AgentHeartbeat(
            agent_id="finance-agent-172-17-30-243",
            client_ip="172.17.30.243",
            capabilities={"admin_commands": ["tail-log"]},
        ),
        "172.17.30.243",
    )

    assert claimed is not None
    assert claimed["id"] == tail["id"]
    assert claimed["command"] == "tail-log"
    remaining = store.list_agent_commands()
    update_command = next(command for command in remaining if command["command"] == "update-agent")
    assert update_command["status"] == "queued"


def test_agent_update_verifies_manager_hash_and_admin_ui_waits_for_completion():
    worker_source = (ROOT / "agent" / "agent_worker.py").read_text(encoding="utf-8")
    storage_source = (ROOT / "app" / "storage.py").read_text(encoding="utf-8")
    app_source = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'headers={"Cache-Control": "no-cache"}' in worker_source
    assert "expected_manager_sha256" in worker_source
    assert '"manager_sha256": actual_manager_sha256' in worker_source
    assert "if updated.rowcount != 1:" in storage_source
    assert "async function waitForAdminCommand" in app_source
    assert 'current?.status === "done"' in app_source
    assert "result.manager_sha256" in app_source
