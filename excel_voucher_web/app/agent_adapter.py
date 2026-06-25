from __future__ import annotations

import html
import json
import os
import time
from pathlib import Path
from typing import Any


def _render_print_html(payload: dict[str, Any], output_path: Path) -> None:
    lines = payload.get("lines") or []
    body_rows = []
    for line in lines:
        debit = int(line.get("amount") or 0) if line.get("side") == "debit" else 0
        credit = int(line.get("amount") or 0) if line.get("side") == "credit" else 0
        body_rows.append(
            "<tr>"
            f"<td>{html.escape(str(line.get('seq') or ''))}</td>"
            f"<td>{html.escape(str(line.get('account_name') or ''))}</td>"
            f"<td class='amount'>{debit:,}</td>"
            f"<td class='amount'>{credit:,}</td>"
            f"<td>{html.escape(str(line.get('summary') or ''))}</td>"
            "</tr>"
        )
    output_path.write_text(
        f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>엑셀 전표 출력</title>
  <style>
    body {{ font-family: "Malgun Gothic", Arial, sans-serif; color: #111827; }}
    h1 {{ font-size: 22px; margin: 0 0 12px; }}
    .meta {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 14px; }}
    .meta div {{ border: 1px solid #d1d5db; padding: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 6px; text-align: left; }}
    th {{ background: #f3f4f6; }}
    .amount {{ text-align: right; }}
  </style>
</head>
<body>
  <h1>{html.escape(str(payload.get("company_name") or ""))} 수시결제 전표</h1>
  <section class="meta">
    <div>회계일<br /><strong>{html.escape(str(payload.get("accounting_date") or ""))}</strong></div>
    <div>작성자<br /><strong>{html.escape(str(payload.get("requester") or ""))}</strong></div>
    <div>합계<br /><strong>{int(payload.get("debit_total") or 0):,}원</strong></div>
  </section>
  <table>
    <thead><tr><th>No</th><th>계정과목</th><th>차변</th><th>대변</th><th>적요</th></tr></thead>
    <tbody>{"".join(body_rows)}</tbody>
  </table>
</body>
</html>
""",
        encoding="utf-8",
    )


def _submit_print(path: Path, *, print_mode: str, wait_seconds: float) -> dict[str, Any]:
    if print_mode == "off":
        return {"print_submitted": False, "print_mode": print_mode, "print_file": str(path)}
    if os.name != "nt":
        raise RuntimeError("default-printer print mode is only supported on Windows.")
    os.startfile(str(path), "print")  # type: ignore[attr-defined]
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    return {"print_submitted": True, "print_mode": print_mode, "print_file": str(path)}


def run_erp_voucher_task(
    task: dict[str, Any],
    *,
    output_dir: Path,
    print_mode: str = "default-printer",
    print_wait_seconds: float = 3.0,
) -> dict[str, Any]:
    """Placeholder for the real ERP UI automation run on the 담당자 PC Agent."""
    output_dir.mkdir(parents=True, exist_ok=True)
    job_id = str(task.get("id") or task.get("job_id") or "unknown")
    payload = task.get("payload") or {}
    preview_path = output_dir / f"{job_id}_voucher_payload.json"
    preview_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    clipboard_rows = [str(row) for row in payload.get("erp_clipboard_rows") or []]
    clipboard_path = output_dir / f"{job_id}_erp_clipboard_rows.txt"
    clipboard_path.write_text("\r\n".join(clipboard_rows), encoding="utf-8")
    print_path = output_dir / f"{job_id}_voucher_print.html"
    _render_print_html(payload, print_path)
    print_result = _submit_print(print_path, print_mode=print_mode, wait_seconds=print_wait_seconds)
    return {
        "dry_run": True,
        "preview_path": str(preview_path),
        "clipboard_rows_path": str(clipboard_path),
        "erp_clipboard_row_count": len(clipboard_rows),
        "line_count": int(payload.get("line_count") or 0),
        "debit_total": int(payload.get("debit_total") or 0),
        **print_result,
        "message": "ERP 자동입력 연결 전 dry-run payload 생성 및 출력 제출 완료"
        if print_result.get("print_submitted")
        else "ERP 자동입력 연결 전 dry-run payload 생성 완료",
    }
