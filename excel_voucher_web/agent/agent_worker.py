from __future__ import annotations

import argparse
import getpass
import socket
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent_adapter import run_erp_voucher_task


def _post(session: requests.Session, server: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = session.post(f"{server.rstrip('/')}{path}", json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {}


def _connection_error_message(server: str, exc: Exception) -> str:
    return f"server unreachable: {server} ({exc.__class__.__name__}: {exc})"


def _heartbeat(agent_id: str, client_ip: str = "") -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "agent_host": socket.gethostname(),
        "agent_user": getpass.getuser(),
        "client_ip": client_ip,
        "capabilities": {"excel_voucher": True},
    }


def run_loop(server: str, agent_id: str, client_ip: str, interval: int, once: bool) -> None:
    session = requests.Session()
    output_dir = ROOT / "data" / "agent_results"
    while True:
        heartbeat = _heartbeat(agent_id, client_ip)
        try:
            _post(session, server, "/api/agent/heartbeat", heartbeat)
            next_payload = _post(session, server, "/api/agent/voucher/next", heartbeat)
        except requests.RequestException as exc:
            print(_connection_error_message(server, exc), file=sys.stderr)
            if once:
                return
            time.sleep(interval)
            continue
        task = next_payload.get("task")
        if not task:
            if once:
                print("no task")
                return
            time.sleep(interval)
            continue

        job_id = str(task.get("id") or "")
        try:
            _post(
                session,
                server,
                f"/api/agent/jobs/{job_id}/event",
                {
                    "agent_id": agent_id,
                    "status": "running",
                    "progress": 35,
                    "message": "Agent ERP 전표 payload 처리 시작",
                },
            )
            result = run_erp_voucher_task(task, output_dir=output_dir)
            _post(
                session,
                server,
                f"/api/agent/jobs/{job_id}/complete",
                {
                    "agent_id": agent_id,
                    "ok": True,
                    "message": result.get("message") or "Agent 처리 완료",
                    "result": result,
                },
            )
            print(f"completed {job_id}")
        except Exception as exc:
            try:
                _post(
                    session,
                    server,
                    f"/api/agent/jobs/{job_id}/complete",
                    {
                        "agent_id": agent_id,
                        "ok": False,
                        "message": "Agent 처리 실패",
                        "error": str(exc),
                    },
                )
            except requests.RequestException as report_exc:
                print(_connection_error_message(server, report_exc), file=sys.stderr)
            print(f"failed {job_id}: {exc}", file=sys.stderr)
        if once:
            return
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Excel voucher ERP agent worker")
    parser.add_argument("--server", default="http://127.0.0.1:18100")
    parser.add_argument("--agent-id", default="finance-agent-172-17-30-243")
    parser.add_argument("--client-ip", default="")
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    run_loop(args.server, args.agent_id, args.client_ip, max(1, args.interval), args.once)


if __name__ == "__main__":
    main()
