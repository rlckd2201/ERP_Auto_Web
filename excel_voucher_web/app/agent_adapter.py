from __future__ import annotations

import html
import json
import logging
import os
import subprocess
import sys
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


def _pdf_print_app_candidates() -> list[Path]:
    roots = [
        os.getenv("ProgramFiles"),
        os.getenv("ProgramFiles(x86)"),
        os.getenv("LOCALAPPDATA"),
    ]
    rels = [
        r"Adobe\Acrobat DC\Acrobat\Acrobat.exe",
        r"Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        r"Adobe\Acrobat Reader\Reader\AcroRd32.exe",
    ]
    candidates: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not root:
            continue
        for rel in rels:
            path = Path(root) / rel
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            if path.is_file():
                candidates.append(path)
    return candidates


def _print_pdf_with_direct_app(path: Path, printer_name: str, wait_seconds: float) -> str:
    errors: list[str] = []
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for exe in _pdf_print_app_candidates():
        try:
            proc = subprocess.Popen(
                [str(exe), "/t", str(path), printer_name],
                cwd=str(path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=creationflags,
            )
            time.sleep(max(wait_seconds, 0.5))
            code = proc.poll()
            if code not in (None, 0):
                errors.append(f"{exe.name}: exit {code}")
                continue
            return str(exe)
        except Exception as exc:
            errors.append(f"{exe.name}: {exc}")
    if errors:
        raise RuntimeError("; ".join(errors))
    raise RuntimeError("Adobe/Reader PDF print app not found")


def _print_pdf_to_printer(path: Path, *, print_mode: str, printer_name: str, wait_seconds: float) -> dict[str, Any]:
    if print_mode == "off":
        return {"print_submitted": False, "print_mode": print_mode, "print_file": str(path)}
    if os.name != "nt":
        raise RuntimeError("PDF print mode is only supported on Windows.")
    if not path.is_file():
        raise RuntimeError(f"PDF print target was not found: {path}")
    printer_name = (printer_name or "").strip()
    if not printer_name:
        os.startfile(str(path), "print")  # type: ignore[attr-defined]
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        return {"print_submitted": True, "print_mode": "default-printer-pdf", "print_file": str(path)}

    direct_error = ""
    try:
        app_path = _print_pdf_with_direct_app(path, printer_name, wait_seconds)
        return {
            "print_submitted": True,
            "print_mode": "pdf-direct-app",
            "printer_name": printer_name,
            "print_file": str(path),
            "pdf_print_app": app_path,
        }
    except Exception as exc:
        direct_error = str(exc) or exc.__class__.__name__

    try:
        import win32api

        win32api.ShellExecute(0, "printto", str(path), f'"{printer_name}"', str(path.parent), 0)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        return {
            "print_submitted": True,
            "print_mode": "pdf-printto",
            "printer_name": printer_name,
            "print_file": str(path),
            "direct_print_error": direct_error,
        }
    except Exception as exc:
        shell_error = str(exc) or exc.__class__.__name__
        raise RuntimeError(f"PDF print failed: {path.name} / direct={direct_error} / printto={shell_error}") from exc


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


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_web_erp_runner() -> Any:
    project_root = _project_root()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from web_v1.backend import erp_runner

    return erp_runner


def _legacy_site_name(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("erp_site_name") or "").strip()
    if explicit:
        return explicit
    company_key = str(payload.get("company_key") or "").strip().lower()
    company_name = str(payload.get("company_name") or "").strip()
    if company_key == "daeseung" or company_name == "대승":
        return "D1공장"
    return ""


def _is_payable_account(account_name: Any) -> bool:
    return "미지급금" in str(account_name or "").replace(" ", "")


def _is_bank_account(account_name: Any) -> bool:
    return "보통예금" in str(account_name or "").replace(" ", "")


def _fallback_bank_management_items(payload: dict[str, Any]) -> dict[str, str]:
    company_key = str(payload.get("company_key") or "").strip().lower()
    company_name = str(payload.get("company_name") or "").strip()
    if company_key == "daeseung" or company_name == "대승":
        return {
            "계좌번호": "140-000-948562",
            "금융기관지점": "신한 수원금융센터",
            "거래처": "",
        }
    return {}


def _fallback_line_management_items(payload: dict[str, Any]) -> list[dict[str, str]]:
    existing = payload.get("erp_line_management_items") or payload.get("line_management_items")
    if isinstance(existing, list) and any(isinstance(item, dict) and item for item in existing):
        return [dict(item) if isinstance(item, dict) else {} for item in existing]

    lines = payload.get("lines") or []
    if not isinstance(lines, list):
        return []

    fallback: list[dict[str, str]] = []
    for line in lines:
        if not isinstance(line, dict):
            fallback.append({})
            continue
        explicit = line.get("management_items")
        if isinstance(explicit, dict) and explicit:
            fallback.append(dict(explicit))
            continue
        account_name = line.get("account_name") or ""
        if _is_payable_account(account_name):
            vendor_value = str(line.get("vendor_code") or line.get("vendor_name") or "").strip()
            fallback.append({"거래처": vendor_value} if vendor_value else {})
            continue
        if _is_bank_account(account_name):
            fallback.append(_fallback_bank_management_items(payload))
            continue
        fallback.append({})
    return fallback


def _legacy_form_data(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [str(row) for row in payload.get("erp_clipboard_rows") or []]
    if not rows:
        raise RuntimeError("ERP input rows are empty.")
    site_name = _legacy_site_name(payload)
    if not site_name:
        raise RuntimeError("ERP 회계단위가 설정되지 않았습니다. 담당자별 erp_site_name을 먼저 확정해야 합니다.")
    line_management_items = _fallback_line_management_items(payload)
    data = dict(payload)
    data.update(
        {
            "pdf_path": "",
            "site_name": site_name,
            "invoice_date": str(payload.get("accounting_date") or ""),
            "vendor_name": str(payload.get("company_name") or ""),
            "supplier_name": str(payload.get("company_name") or ""),
            "item_name": str(payload.get("source_filename") or "수시결제"),
            "subject": str(payload.get("source_filename") or "수시결제"),
            "total_tax": 0,
            "target_supply": int(payload.get("debit_total") or 0),
            "total_sum": int(payload.get("credit_total") or payload.get("debit_total") or 0),
            "erp_row_count": int(payload.get("line_count") or len(rows)),
            "erp_clipboard_rows": rows,
            "erp_line_management_items": line_management_items,
            "cash_processing_enabled": bool(payload.get("cash_processing_enabled")),
        }
    )
    return data


def _run_real_erp_voucher_task(
    task: dict[str, Any],
    *,
    output_dir: Path,
    print_mode: str,
    printer_name: str,
    print_wait_seconds: float,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    job_id = str(task.get("id") or task.get("job_id") or "unknown")
    payload = task.get("payload") or {}
    if not isinstance(payload, dict):
        raise RuntimeError("ERP payload is invalid.")

    data = _legacy_form_data(payload)
    rows = [str(row) for row in data.get("erp_clipboard_rows") or []]
    preview_path = output_dir / f"{job_id}_voucher_payload.json"
    preview_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    clipboard_path = output_dir / f"{job_id}_erp_clipboard_rows.txt"
    clipboard_path.write_text("\r\n".join(rows), encoding="utf-8")

    print_path = output_dir / f"{job_id}_voucher_print.html"
    _render_print_html(payload, print_path)
    print_text_path = output_dir / f"{job_id}_voucher_print.txt"
    _render_print_text(payload, print_text_path)

    os.environ.setdefault("ERP_OUTPUT_DIR", str(output_dir / "erp_outputs"))
    os.environ.setdefault("ERP_PRINT_TARGET", "Microsoft Print to PDF")

    erp_runner = _load_web_erp_runner()
    import pyperclip

    pyperclip.copy("\r\n".join(rows))
    legacy = erp_runner._load_legacy_module()

    erp_pdf_dir = output_dir / "erp_outputs"
    erp_pdf_dir.mkdir(parents=True, exist_ok=True)
    erp_pdf_path = erp_pdf_dir / f"{job_id}_erp_voucher.pdf"
    print_choice = {
        "label": "엑셀 전표 PDF 보관",
        "match": os.getenv("ERP_PRINT_TARGET", "Microsoft Print to PDF"),
        "kind": "pdf_merge",
        "save_path": str(erp_pdf_path),
    }

    log_path = output_dir / f"{job_id}_erp_input.log"
    logger = logging.getLogger(f"EXCEL_VOUCHER_ERP_{job_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(handler)
    try:
        main_app = erp_runner._MainAppShim(data, print_choice)
        manager = erp_runner._ManagerShim(legacy, main_app, logger)
        install_key, corp_code = erp_runner._corp_codes(str(data.get("site_name") or ""))
        install_info, corp_info = erp_runner._validate_install_info(manager, install_key, corp_code)
        erp_runner._configure_pyautogui_for_server(legacy)
        main_app.erp_job_id = job_id
        bot = legacy.ERPLoginBot(install_info, corp_info, corp_code, manager, logger)
        result = bot.run()
        if result is not True:
            raise RuntimeError(str(result))
        saved_pdf = Path(str(getattr(main_app, "last_erp_print_output", "") or erp_pdf_path))
        if not saved_pdf.is_file():
            raise RuntimeError(f"ERP 전표 PDF 저장 실패: {saved_pdf}")
        pdf_print_result = _print_pdf_to_printer(
            saved_pdf,
            print_mode=print_mode,
            printer_name=printer_name,
            wait_seconds=print_wait_seconds,
        )
        voucher_no = str(getattr(main_app, "last_erp_voucher_no", "") or "").strip()
        return {
            "dry_run": False,
            "preview_path": str(preview_path),
            "clipboard_rows_path": str(clipboard_path),
            "print_text_path": str(print_text_path),
            "erp_clipboard_row_count": len(rows),
            "line_count": int(payload.get("line_count") or len(rows)),
            "debit_total": int(payload.get("debit_total") or 0),
            "erp_saved": True,
            "voucher_no": voucher_no,
            "erp_pdf_path": str(saved_pdf),
            "erp_log_path": str(log_path),
            **pdf_print_result,
            "message": "ERP 전표 저장 및 출력 제출 완료" if pdf_print_result.get("print_submitted") else "ERP 전표 저장 완료",
        }
    finally:
        logger.removeHandler(handler)
        handler.close()


def run_erp_voucher_task(
    task: dict[str, Any],
    *,
    output_dir: Path,
    print_mode: str = "default-printer",
    printer_name: str = "",
    print_wait_seconds: float = 3.0,
    erp_mode: str = "dry-run",
) -> dict[str, Any]:
    """Run a dry-run print preview or the real legacy ERP automation on the voucher PC Agent."""
    normalized_mode = str(os.getenv("EXCEL_VOUCHER_ERP_MODE") or erp_mode or "dry-run").strip().lower().replace("_", "-")
    if normalized_mode == "real":
        return _run_real_erp_voucher_task(
            task,
            output_dir=output_dir,
            print_mode=print_mode,
            printer_name=printer_name,
            print_wait_seconds=print_wait_seconds,
        )

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
        "erp_saved": False,
        "voucher_no": "",
        **pdf_result,
        **print_result,
        "message": "ERP 자동입력 연결 전 dry-run payload 생성 및 출력 제출 완료"
        if print_result.get("print_submitted")
        else "ERP 자동입력 연결 전 dry-run payload 생성 완료",
    }
