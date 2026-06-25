from __future__ import annotations

import argparse
import getpass
import socket
import sys
import time
import urllib3
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent_adapter import run_erp_voucher_task


def _post(session: requests.Session, server: str, path: str, payload: dict[str, Any], *, verify_tls: bool) -> dict[str, Any]:
    response = session.post(f"{server.rstrip('/')}{path}", json=payload, timeout=30, verify=verify_tls)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {}


def _connection_error_message(server: str, exc: Exception) -> str:
    return f"server unreachable: {server} ({exc.__class__.__name__}: {exc})"


def _heartbeat(agent_id: str, client_ip: str = "", print_mode: str = "default-printer") -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "agent_host": socket.gethostname(),
        "agent_user": getpass.getuser(),
        "client_ip": client_ip,
        "capabilities": {"excel_voucher": True, "voucher_print": print_mode != "off"},
    }


def run_loop(
    server: str,
    agent_id: str,
    client_ip: str,
    interval: int,
    once: bool,
    verify_tls: bool,
    print_mode: str,
    print_wait_seconds: float,
) -> None:
    if not verify_tls:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    session = requests.Session()
    output_dir = ROOT / "data" / "agent_results"
    while True:
        heartbeat = _heartbeat(agent_id, client_ip, print_mode)
        try:
            _post(session, server, "/api/agent/heartbeat", heartbeat, verify_tls=verify_tls)
            next_payload = _post(session, server, "/api/agent/voucher/next", heartbeat, verify_tls=verify_tls)
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
                verify_tls=verify_tls,
            )
            result = run_erp_voucher_task(
                task,
                output_dir=output_dir,
                print_mode=print_mode,
                print_wait_seconds=print_wait_seconds,
            )
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
                verify_tls=verify_tls,
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
                    verify_tls=verify_tls,
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
    parser.add_argument("--insecure-skip-tls-verify", action="store_true")
    parser.add_argument("--print-mode", choices=["default-printer", "off"], default="default-printer")
    parser.add_argument("--print-wait-seconds", type=float, default=3.0)
    args = parser.parse_args()
    run_loop(
        args.server,
        args.agent_id,
        args.client_ip,
        max(1, args.interval),
        args.once,
        not args.insecure_skip_tls_verify,
        args.print_mode,
        max(0.0, args.print_wait_seconds),
    )


if __name__ == "__main__":
    main()
