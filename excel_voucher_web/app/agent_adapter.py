from __future__ import annotations

import html
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any


def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _find_browser_for_pdf() -> Path | None:
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


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


def _render_print_text(payload: dict[str, Any], output_path: Path) -> None:
    lines = payload.get("lines") or []
    rows = [
        f"{payload.get('company_name') or ''} 수시결제 전표",
        f"회계일: {payload.get('accounting_date') or ''}",
        f"작성자: {payload.get('requester') or ''}",
        f"합계: {int(payload.get('debit_total') or 0):,}원",
        "",
        "No\t계정과목\t차변\t대변\t적요",
    ]
    for line in lines:
        debit = int(line.get("amount") or 0) if line.get("side") == "debit" else 0
        credit = int(line.get("amount") or 0) if line.get("side") == "credit" else 0
        rows.append(
            "\t".join(
                [
                    str(line.get("seq") or ""),
                    str(line.get("account_name") or ""),
                    f"{debit:,}",
                    f"{credit:,}",
                    str(line.get("summary") or ""),
                ]
            )
        )
    output_path.write_text("\r\n".join(rows), encoding="utf-8")


def _archive_pdf(html_path: Path, pdf_path: Path) -> dict[str, Any]:
    browser = _find_browser_for_pdf()
    if not browser:
        return {"pdf_archived": False, "pdf_archive_error": "Edge/Chrome executable was not found."}
    command = [
        str(browser),
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        _file_uri(html_path),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    except Exception as exc:
        return {"pdf_archived": False, "pdf_archive_error": str(exc)}
    if completed.returncode != 0 or not pdf_path.exists():
        message = (completed.stderr or completed.stdout or "PDF archive failed.").strip()
        return {"pdf_archived": False, "pdf_archive_error": message}
    return {"pdf_archived": True, "pdf_archive_path": str(pdf_path)}


def _submit_print(path: Path, fallback_text_path: Path, *, print_mode: str, printer_name: str, wait_seconds: float) -> dict[str, Any]:
    if print_mode == "off":
        return {"print_submitted": False, "print_mode": print_mode, "print_file": str(path)}
    if os.name != "nt":
        raise RuntimeError("default-printer print mode is only supported on Windows.")
    printer_name = (printer_name or "").strip()
    if printer_name:
        try:
            subprocess.Popen(["notepad.exe", "/pt", str(fallback_text_path), printer_name])
        except OSError as exc:
            raise RuntimeError(f"Named printer output failed for {printer_name}: {exc}") from exc
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        return {
            "print_submitted": True,
            "print_mode": "named-printer",
            "printer_name": printer_name,
            "print_file": str(fallback_text_path),
        }
    primary_error = ""
    try:
        os.startfile(str(path), "print")  # type: ignore[attr-defined]
        print_file = path
        effective_mode = print_mode
    except OSError as exc:
        primary_error = str(exc)
        try:
            subprocess.Popen(["notepad.exe", "/p", str(fallback_text_path)])
        except OSError as fallback_exc:
            raise RuntimeError(f"HTML print failed: {primary_error}; text print failed: {fallback_exc}") from fallback_exc
        print_file = fallback_text_path
        effective_mode = "notepad-text-fallback"
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    result = {"print_submitted": True, "print_mode": effective_mode, "print_file": str(print_file)}
    if primary_error:
        result["primary_print_error"] = primary_error
    return result


def run_erp_voucher_task(
    task: dict[str, Any],
    *,
    output_dir: Path,
    print_mode: str = "default-printer",
    printer_name: str = "",
    print_wait_seconds: float = 3.0,
) -> dict[str, Any]:
    """Placeholder for the real ERP UI automation run on the automatic voucher PC Agent."""
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
    print_text_path = output_dir / f"{job_id}_voucher_print.txt"
    _render_print_text(payload, print_text_path)
    pdf_path = output_dir / f"{job_id}_voucher_archive.pdf"
    pdf_result = _archive_pdf(print_path, pdf_path)
    print_result = _submit_print(
        print_path,
        print_text_path,
        print_mode=print_mode,
        printer_name=printer_name,
        wait_seconds=print_wait_seconds,
    )
    return {
        "dry_run": True,
        "preview_path": str(preview_path),
        "clipboard_rows_path": str(clipboard_path),
        "print_text_path": str(print_text_path),
        "erp_clipboard_row_count": len(clipboard_rows),
        "line_count": int(payload.get("line_count") or 0),
        "debit_total": int(payload.get("debit_total") or 0),
        **pdf_result,
        **print_result,
        "message": "ERP 자동입력 연결 전 dry-run payload 생성 및 출력 제출 완료"
        if print_result.get("print_submitted")
        else "ERP 자동입력 연결 전 dry-run payload 생성 완료",
    }
