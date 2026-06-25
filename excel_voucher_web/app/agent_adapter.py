from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def run_erp_voucher_task(task: dict[str, Any], *, output_dir: Path) -> dict[str, Any]:
    """Placeholder for the real ERP UI automation run on the 담당자 PC Agent."""
    output_dir.mkdir(parents=True, exist_ok=True)
    job_id = str(task.get("id") or task.get("job_id") or "unknown")
    payload = task.get("payload") or {}
    preview_path = output_dir / f"{job_id}_voucher_payload.json"
    preview_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "dry_run": True,
        "preview_path": str(preview_path),
        "line_count": int(payload.get("line_count") or 0),
        "debit_total": int(payload.get("debit_total") or 0),
        "message": "ERP 자동입력 연결 전 dry-run payload 생성 완료",
    }
