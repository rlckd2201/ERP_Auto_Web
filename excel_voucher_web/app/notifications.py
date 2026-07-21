from __future__ import annotations

import html
import json
import mimetypes
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from pathlib import Path
from typing import Any, Iterable

from .models import JobEvent, JobRecord
from .settings import settings


STEP_LABELS = ("작업시작", "업로드완료", "ERP 입력시작", "저장완료", "출력완료")


def _recipients(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = re.split(r"[;,]", value)
    else:
        raw = [str(item or "") for item in value]
    result: list[str] = []
    for item in raw:
        address = item.strip()
        if address and address not in result:
            result.append(address)
    return result


def _email_only(value: str) -> str:
    return parseaddr(value or "")[1] or str(value or "").strip()


def _display_address(address: str, display_name: str = "") -> str:
    email_addr = _email_only(address)
    name = str(display_name or "").strip()
    return formataddr((name, email_addr)) if name else email_addr


def _message_text(message: EmailMessage) -> str:
    if not message.is_multipart():
        return message.get_content()
    for part in message.walk():
        if part.get_content_type() == "text/plain":
            return part.get_content()
    return ""


def _message_html(message: EmailMessage) -> str:
    if not message.is_multipart():
        return ""
    for part in message.walk():
        if part.get_content_type() == "text/html":
            return part.get_content()
    return ""


def _attachment_paths(message: EmailMessage) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    for part in message.iter_attachments():
        attachments.append(
            {
                "filename": part.get_filename() or "",
                "content_type": part.get_content_type(),
            }
        )
    return attachments


def _write_outbox(message: EmailMessage, *, reason: str) -> dict[str, Any]:
    settings.mail_outbox_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = settings.mail_outbox_dir / f"{stamp}.json"
    path.write_text(
        json.dumps(
            {
                "reason": reason,
                "to": message["To"],
                "cc": message["Cc"] or "",
                "from": message["From"],
                "subject": message["Subject"],
                "body": _message_text(message),
                "html_body": _message_html(message),
                "attachments": _attachment_paths(message),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"sent": False, "queued": True, "outbox_path": str(path), "reason": reason}


def _add_attachment(message: EmailMessage, path: Path) -> None:
    content_type, _encoding = mimetypes.guess_type(str(path))
    maintype, subtype = (content_type or "application/octet-stream").split("/", 1)
    message.add_attachment(
        path.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=path.name,
    )


def send_mail(
    to_addr: str | Iterable[str],
    subject: str,
    body: str,
    *,
    html_body: str = "",
    attachments: list[Path] | None = None,
    cc_addr: str | Iterable[str] | None = None,
    to_name: str = "",
    cc_name: str = "",
    from_name: str = "",
) -> dict[str, Any]:
    to_list = [_email_only(addr) for addr in _recipients(to_addr)]
    cc_list = [addr for addr in (_email_only(item) for item in _recipients(cc_addr)) if addr and addr not in to_list]
    from_addr = (settings.smtp_from or settings.smtp_user or "").strip()
    sender_name = from_name or str(getattr(settings, "smtp_from_name", "") or "재정전표자동화 시스템").strip()

    message = EmailMessage()
    message["To"] = ", ".join(
        _display_address(addr, to_name if len(to_list) == 1 else "") for addr in to_list
    )
    if cc_list:
        message["Cc"] = ", ".join(
            _display_address(addr, cc_name if len(cc_list) == 1 else "") for addr in cc_list
        )
    message["From"] = _display_address(from_addr, sender_name)
    message["Subject"] = subject
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    attached: list[str] = []
    for path in attachments or []:
        if path.is_file():
            _add_attachment(message, path)
            attached.append(str(path))

    if not to_list:
        return _write_outbox(message, reason="recipient email is empty")
    if not settings.smtp_host or not from_addr:
        return _write_outbox(message, reason="SMTP is not configured")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.ehlo()
            if settings.smtp_starttls and smtp.has_extn("STARTTLS"):
                smtp.starttls()
                smtp.ehlo()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except Exception as exc:
        return _write_outbox(message, reason=f"SMTP send failed: {exc}")
    return {
        "sent": True,
        "queued": False,
        "to": ", ".join(to_list),
        "cc": ", ".join(cc_list),
        "attachments": attached,
    }


def _job_recipient(job: JobRecord) -> str:
    payload = job.payload or {}
    return str(payload.get("requester_email") or settings.admin_email or "").strip()


def _job_recipient_name(job: JobRecord) -> str:
    payload = job.payload or {}
    return str(payload.get("requester") or job.requester or "").strip()


def _support_email() -> str:
    return str(
        getattr(settings, "support_email", "")
        or "rlckd9646@dae-seung.co.kr"
    ).strip()


def _money(value: Any) -> str:
    try:
        return f"{int(value or 0):,}원"
    except Exception:
        return "0원"


def _job_error(job: JobRecord) -> str:
    result = job.result or {}
    return str(job.error or result.get("error") or result.get("message") or "-")


def _event_lines(events: Iterable[JobEvent] | None) -> list[str]:
    lines: list[str] = []
    for event in events or []:
        created = event.created_at.isoformat(timespec="seconds") if event.created_at else ""
        lines.append(f"{created} [{event.status} {event.progress}%] {event.message}")
    return lines


def _step_statuses(job: JobRecord, events: Iterable[JobEvent] | None = None) -> list[tuple[str, str]]:
    result = job.result or {}
    progress = int(job.progress or 0)
    event_text = "\n".join(_event_lines(events))
    erp_started = progress >= 35 or "ERP" in event_text or "자료 처리 시작" in event_text
    saved = bool(result.get("erp_saved")) or bool(result.get("server_pdf_stored"))
    printed = bool(result.get("print_submitted"))

    if job.status == "done":
        erp_started = saved = printed = True

    done_map = {
        "작업시작": progress >= 5 or job.created_at is not None,
        "업로드완료": progress >= 5 or bool(job.source_filename),
        "ERP 입력시작": erp_started,
        "저장완료": saved,
        "출력완료": printed,
    }
    statuses: list[tuple[str, str]] = []
    failed_marked = False
    for label in STEP_LABELS:
        if done_map[label]:
            statuses.append((label, "done"))
            continue
        if job.status == "error" and not failed_marked:
            statuses.append((label, "failed"))
            failed_marked = True
        else:
            statuses.append((label, "pending"))
    if job.status == "running":
        for index, (label, state) in enumerate(statuses):
            if state == "pending":
                statuses[index] = (label, "active")
                break
    return statuses


def _steps_text(job: JobRecord, events: Iterable[JobEvent] | None = None) -> str:
    symbols = {"done": "[완료]", "active": "[진행]", "failed": "[오류]", "pending": "[대기]"}
    return "\n".join(f"- {symbols[state]} {label}" for label, state in _step_statuses(job, events))


def _steps_html(job: JobRecord, events: Iterable[JobEvent] | None = None) -> str:
    colors = {
        "done": ("#0f766e", "#ecfdf5", "#99f6e4"),
        "active": ("#b45309", "#fffbeb", "#fde68a"),
        "failed": ("#b91c1c", "#fef2f2", "#fecaca"),
        "pending": ("#64748b", "#f8fafc", "#e2e8f0"),
    }
    cells = []
    for label, state in _step_statuses(job, events):
        fg, bg, border = colors[state]
        mark = {"done": "✓", "active": "…", "failed": "!", "pending": "-"}.get(state, "-")
        cells.append(
            f"""
            <td style="padding:6px 4px;">
              <div style="border:1px solid {border};background:{bg};border-radius:8px;padding:10px 8px;text-align:center;min-width:92px;">
                <div style="display:inline-block;width:24px;height:24px;border-radius:999px;background:{fg};color:#fff;line-height:24px;font-weight:700;">{mark}</div>
                <div style="margin-top:6px;color:{fg};font-size:13px;font-weight:700;">{html.escape(label)}</div>
              </div>
            </td>
            """
        )
    return f'<table role="presentation" style="border-collapse:collapse;width:100%;margin:18px 0;"><tr>{"".join(cells)}</tr></table>'


def _details_table(job: JobRecord) -> str:
    payload = job.payload or {}
    result = job.result or {}
    rows = [
        ("작업", job.title),
        ("회사", payload.get("company_name") or job.company_key),
        ("회계일", job.accounting_date),
        ("전표 행", str(payload.get("line_count", 0))),
        ("차변 합계", _money(payload.get("debit_total"))),
        ("대변 합계", _money(payload.get("credit_total"))),
        ("서버 PDF", result.get("erp_pdf_server_path") or "-"),
    ]
    body = "".join(
        f"<tr><th style='text-align:left;padding:8px 10px;background:#f8fafc;border:1px solid #e2e8f0;width:120px;color:#334155;'>{html.escape(label)}</th>"
        f"<td style='padding:8px 10px;border:1px solid #e2e8f0;color:#0f172a;'>{html.escape(str(value or '-'))}</td></tr>"
        for label, value in rows
    )
    return f"<table style='border-collapse:collapse;width:100%;font-size:14px;'>{body}</table>"


def _mail_shell(title: str, subtitle: str, body_html: str, *, failed: bool = False) -> str:
    accent = "#b91c1c" if failed else "#0f766e"
    soft = "#fef2f2" if failed else "#ecfdf5"
    badge = "오류 확인 필요" if failed else "처리 완료"
    return f"""<!doctype html>
<html>
  <body style="margin:0;background:#f3f6f8;font-family:Arial,'Malgun Gothic',sans-serif;color:#0f172a;">
    <div style="max-width:760px;margin:0 auto;padding:28px 16px;">
      <div style="background:#fff;border:1px solid #dbe3ea;border-radius:10px;overflow:hidden;">
        <div style="border-top:5px solid {accent};background:{soft};border-bottom:1px solid #dbe3ea;padding:20px 24px;">
          <table role="presentation" style="border-collapse:collapse;width:100%;">
            <tr>
              <td style="font-size:12px;font-weight:700;color:{accent};letter-spacing:.04em;">재정전표자동화 시스템</td>
              <td style="text-align:right;">
                <span style="border:1px solid {accent};color:{accent};border-radius:999px;padding:4px 10px;font-size:12px;font-weight:700;">{badge}</span>
              </td>
            </tr>
          </table>
          <h2 style="margin:10px 0 6px;font-size:22px;color:#0f172a;line-height:1.35;">{html.escape(title)}</h2>
          <p style="margin:0;color:#475569;font-size:14px;line-height:1.5;">{html.escape(subtitle)}</p>
        </div>
        <div style="padding:22px 24px;">
          {body_html}
        </div>
      </div>
    </div>
  </body>
</html>"""


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", value).strip("._")
    return safe[:80] or "job"


def _redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload or {})
    credentials = clean.get("erp_credentials")
    if isinstance(credentials, dict):
        clean["erp_credentials"] = {
            "user_id": credentials.get("user_id") or "",
            "password": "***",
            "password_blob": "***" if credentials.get("password_blob") else "",
            "source": credentials.get("source") or "",
        }
    return clean


def _diagnostic_attachment(job: JobRecord, events: Iterable[JobEvent] | None, source_path: Path | None) -> Path:
    diagnostic_dir = settings.data_dir / "diagnostics"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = diagnostic_dir / f"{stamp}_{_safe_name(job.id)}_diagnostic.txt"
    lines = [
        "엑셀 전표 처리 오류 진단 로그",
        "",
        f"작업 ID: {job.id}",
        f"작업명: {job.title}",
        f"담당자: {job.requester}",
        f"회사: {job.company_key}",
        f"회계일: {job.accounting_date}",
        f"원본 파일명: {job.source_filename}",
        f"서버 원본 경로: {source_path or '-'}",
        f"상태: {job.status} / {job.progress}%",
        f"오류: {_job_error(job)}",
        "",
        "[진행 단계]",
        _steps_text(job, events),
        "",
        "[작업 이벤트]",
        *(_event_lines(events) or ["이벤트 없음"]),
        "",
        "[결과 JSON]",
        json.dumps(job.result or {}, ensure_ascii=False, indent=2),
        "",
        "[Payload JSON - 비밀번호 제거]",
        json.dumps(_redact_payload(job.payload or {}), ensure_ascii=False, indent=2),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _existing_paths(paths: Iterable[Path | None]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        if not path or not path.is_file():
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def completion_mail_body(job: JobRecord, events: Iterable[JobEvent] | None = None) -> str:
    payload = job.payload or {}
    result = job.result or {}
    requester = _job_recipient_name(job) or "담당자"
    return "\n".join(
        [
            f"{requester}님",
            "",
            "엑셀 수시결제 전표 처리가 완료되었습니다.",
            "전표 PDF 저장과 재정 프린터 출력 요청까지 정상 제출되었습니다.",
            "",
            _steps_text(job, events),
            "",
            f"- 작업: {job.title}",
            f"- 회사: {payload.get('company_name') or job.company_key}",
            f"- 회계일: {job.accounting_date}",
            f"- 전표 행: {payload.get('line_count', 0)}",
            f"- 차변 합계: {_money(payload.get('debit_total'))}",
            f"- 대변 합계: {_money(payload.get('credit_total'))}",
            f"- 출력 파일: {result.get('print_file') or '-'}",
            f"- 서버 보관 PDF: {result.get('erp_pdf_server_path') or '-'}",
            "",
            "첨부된 전표 PDF를 확인해 주세요.",
        ]
    )


def completion_mail_html(job: JobRecord, events: Iterable[JobEvent] | None = None) -> str:
    payload = job.payload or {}
    requester = _job_recipient_name(job) or "담당자"
    body = f"""
      <p style="margin:0 0 12px;font-size:15px;line-height:1.6;">{html.escape(requester)}님, 전표 PDF 저장과 재정 프린터 출력 요청까지 정상 제출되었습니다.</p>
      {_steps_html(job, events)}
      {_details_table(job)}
      <p style="margin:16px 0 0;color:#475569;font-size:13px;line-height:1.6;">첨부된 PDF는 서버에도 보관됩니다. 재출력이 필요하면 전산팀에 요청해 주세요.</p>
    """
    return _mail_shell("엑셀 수시결제 전표 처리 완료", job.title, body)


def notify_job_completed(job: JobRecord, events: Iterable[JobEvent] | None = None) -> dict[str, Any]:
    result = job.result or {}
    recipient = _job_recipient(job)
    recipient_name = _job_recipient_name(job)
    subject = f"[엑셀 전표 처리 완료] {job.title}"
    attachment = Path(str(result.get("erp_pdf_server_path") or ""))
    attachments = _existing_paths([attachment])
    return send_mail(
        recipient,
        subject,
        completion_mail_body(job, events),
        html_body=completion_mail_html(job, events),
        attachments=attachments,
        to_name=recipient_name,
    )


def failure_mail_body(job: JobRecord, events: Iterable[JobEvent] | None = None) -> str:
    payload = job.payload or {}
    requester = _job_recipient_name(job) or "담당자"
    return "\n".join(
        [
            f"{requester}님",
            "",
            "엑셀 수시결제 전표 처리 중 오류가 발생했습니다.",
            "원본 엑셀, 진단 로그, 오류 내용을 이 메일에 함께 첨부했습니다.",
            "",
            _steps_text(job, events),
            "",
            f"- 작업: {job.title}",
            f"- 회사: {payload.get('company_name') or job.company_key}",
            f"- 회계일: {job.accounting_date}",
            f"- 오류: {_job_error(job)}",
            "",
            "오류 알림은 요청자에게만 전송했습니다.",
        ]
    )


def failure_mail_html(job: JobRecord, events: Iterable[JobEvent] | None = None) -> str:
    payload = job.payload or {}
    requester = _job_recipient_name(job) or "담당자"
    body = f"""
      <p style="margin:0 0 12px;font-size:15px;line-height:1.6;">{html.escape(requester)}님, 처리 중 오류가 발생했습니다. 원본 엑셀, 진단 로그, 오류 내용을 이 메일에 함께 첨부했습니다.</p>
      {_steps_html(job, events)}
      <div style="border:1px solid #fecaca;background:#fef2f2;border-radius:8px;padding:12px 14px;margin:12px 0 18px;">
        <div style="font-weight:700;color:#991b1b;margin-bottom:4px;">오류 내용</div>
        <div style="color:#7f1d1d;font-size:14px;white-space:pre-wrap;">{html.escape(_job_error(job))}</div>
      </div>
      {_details_table(job)}
      <p style="margin:16px 0 0;color:#475569;font-size:13px;line-height:1.6;">오류 화면은 자동으로 닫지 않습니다. 전산팀 확인 전에는 243 PC의 ERP 화면을 그대로 두세요.</p>
    """
    return _mail_shell("엑셀 수시결제 전표 처리 오류", job.title, body, failed=True)


def notify_job_failed(
    job: JobRecord,
    *,
    events: Iterable[JobEvent] | None = None,
    source_path: Path | None = None,
) -> dict[str, Any]:
    recipient = _job_recipient(job)
    recipient_name = _job_recipient_name(job)
    subject = f"[엑셀 전표 처리 오류] {job.title}"
    result = job.result or {}
    diagnostic = _diagnostic_attachment(job, events, source_path)
    attachments = _existing_paths(
        [
            diagnostic,
            source_path,
            Path(str(result.get("agent_log_server_path") or "")),
            Path(str(result.get("erp_pdf_server_path") or "")),
        ]
    )
    return send_mail(
        recipient,
        subject,
        failure_mail_body(job, events),
        html_body=failure_mail_html(job, events),
        attachments=attachments,
        to_name=recipient_name,
    )


def password_reset_mail_body(user_id: str, temporary_password: str) -> str:
    return "\n".join(
        [
            f"{user_id} 계정의 임시 비밀번호가 발급되었습니다.",
            "",
            f"임시 비밀번호: {temporary_password}",
            "",
            "로그인 후 반드시 새 비밀번호로 변경해 주세요.",
        ]
    )


def notify_password_reset(email: str, user_id: str, temporary_password: str) -> dict[str, Any]:
    return send_mail(
        email,
        "[엑셀 전표 처리] 임시 비밀번호 안내",
        password_reset_mail_body(user_id, temporary_password),
    )
