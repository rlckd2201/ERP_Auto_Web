from __future__ import annotations

from app.models import AgentHeartbeat
from app.storage import JobStore


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
