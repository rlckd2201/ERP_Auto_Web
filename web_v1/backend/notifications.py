import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Any

from .config import settings
from .invoice_db import get_invoice


log = logging.getLogger(__name__)


def _invoice_data(invoice: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(invoice, dict):
        return {}
    merged = dict(invoice)
    data = invoice.get("data")
    if isinstance(data, dict):
        merged.update(data)
    return merged


def _fmt_amount(value: Any) -> str:
    try:
        number = int(str(value or "0").replace(",", "").strip() or "0")
    except Exception:
        return str(value or "-")
    return f"{number:,}" if number else "-"


def _invoice_summary_line(invoice_id: int) -> str:
    invoice = get_invoice(invoice_id)
    data = _invoice_data(invoice)
    vendor = str(data.get("vendor_name") or data.get("supplier_name") or "-").strip() or "-"
    site = str(data.get("site_name") or data.get("buyer_name") or "-").strip() or "-"
    date = str(data.get("invoice_date") or data.get("issue_date") or "-").strip() or "-"
    amount = _fmt_amount(data.get("total_sum") or data.get("total_amount") or data.get("amount"))
    pdf_name = Path(str(data.get("pdf_path") or (invoice or {}).get("pdf_path") or "")).name or "-"
    return f"- #{invoice_id} / {vendor} / {site} / {date} / {amount}원 / {pdf_name}"


def _regular_auto_sender() -> str:
    from_addr = settings.regular_auto_result_from or settings.password_reset_from
    if "<" in from_addr and ">" in from_addr:
        return from_addr
    from_name = str(settings.regular_auto_result_from_name or "").strip()
    if not from_name:
        return from_addr
    return formataddr((from_name, from_addr))


def _send_mail(to_addr: str, subject: str, body: str) -> None:
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = _regular_auto_sender()
    msg["To"] = to_addr
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    with smtplib.SMTP(settings.regular_auto_result_smtp_server, settings.regular_auto_result_smtp_port, timeout=10) as smtp:
        smtp.ehlo()
        if smtp.has_extn("STARTTLS"):
            smtp.starttls()
            smtp.ehlo()
        if settings.regular_auto_result_smtp_user and settings.regular_auto_result_smtp_pw:
            smtp.login(settings.regular_auto_result_smtp_user, settings.regular_auto_result_smtp_pw)
        smtp.send_message(msg)


def notify_regular_auto_result(
    *,
    job: Any,
    ok: bool,
    message: str,
    invoice_ids: list[int],
    agent_id: str = "",
    phase: str = "",
    source_job: Any = None,
) -> dict[str, Any]:
    root_job = source_job or job
    job_payload = getattr(job, "payload", {}) if job is not None else {}
    root_payload = getattr(root_job, "payload", {}) if root_job is not None else {}
    if not (bool(job_payload.get("regular_auto")) or bool(root_payload.get("regular_auto"))):
        return {"ok": False, "skipped": True, "reason": "not_regular_auto"}
    if not settings.regular_auto_result_email_enabled:
        return {"ok": False, "skipped": True, "reason": "disabled"}
    recipient = str(settings.regular_auto_result_email or "").strip()
    if not recipient:
        return {"ok": False, "skipped": True, "reason": "missing_recipient"}
    dedupe_phase = "".join(ch if ch.isalnum() else "_" for ch in str(phase or "result")).strip("_") or "result"
    dedupe_status = "ok" if ok else "error"
    dedupe_key = f"regular_auto_result_email_sent_{dedupe_phase}_{dedupe_status}"
    if root_payload.get(dedupe_key):
        return {"ok": True, "skipped": True, "reason": "already_sent"}
    clean_invoice_ids = [int(item) for item in invoice_ids if str(item).isdigit()]
    status_label = "성공" if ok else "실패"
    phase_label = phase or "처리"
    subject = f"[회계업무 WEB] 정기 자동처리 {status_label} - {len(clean_invoice_ids)}건"
    lines = [
        f"정기 자동처리 {phase_label} 결과: {status_label}",
        "",
        f"작업ID: {getattr(job, 'id', '')}",
        f"원클릭 작업ID: {getattr(root_job, 'id', '')}",
        f"Agent: {agent_id or root_payload.get('target_agent_id') or job_payload.get('target_agent_id') or '-'}",
        f"대상 PC: {root_payload.get('target_client_ip') or job_payload.get('target_client_ip') or settings.regular_auto_agent_ip or '-'}",
        f"프린터: {root_payload.get('printer_name') or job_payload.get('printer_name') or settings.print_target_pyeongtaek or '-'}",
        f"시간: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"메시지: {message or '-'}",
        "",
        "대상 계산서:",
    ]
    if clean_invoice_ids:
        lines.extend(_invoice_summary_line(invoice_id) for invoice_id in clean_invoice_ids)
    else:
        lines.append("- 없음")
    body = "\n".join(lines)

    try:
        _send_mail(recipient, subject, body)
        if isinstance(root_payload, dict):
            root_payload[dedupe_key] = datetime.now().isoformat(timespec="seconds")
            root_payload["regular_auto_result_email_sent"] = datetime.now().isoformat(timespec="seconds")
            root_payload["regular_auto_result_email_to"] = recipient
            root_payload["regular_auto_result_email_status"] = "sent"
        return {"ok": True, "to": recipient}
    except Exception as exc:
        if isinstance(root_payload, dict):
            root_payload["regular_auto_result_email_status"] = "error"
            root_payload["regular_auto_result_email_error"] = str(exc)
        log.exception("regular auto result email failed: %s", exc)
        return {"ok": False, "error": str(exc)}
