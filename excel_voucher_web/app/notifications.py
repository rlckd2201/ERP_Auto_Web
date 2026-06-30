from __future__ import annotations

import json
import mimetypes
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from .models import JobRecord
from .settings import settings


def _message_text(message: EmailMessage) -> str:
    if not message.is_multipart():
        return message.get_content()
    for part in message.walk():
        if part.get_content_type() == "text/plain":
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
                "from": message["From"],
                "subject": message["Subject"],
                "body": _message_text(message),
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


def send_mail(to_addr: str, subject: str, body: str, *, attachments: list[Path] | None = None) -> dict[str, Any]:
    to_addr = (to_addr or "").strip()
    from_addr = (settings.smtp_from or settings.smtp_user or "").strip()
    message = EmailMessage()
    message["To"] = to_addr
    message["From"] = from_addr
    message["Subject"] = subject
    message.set_content(body)
    attached: list[str] = []
    for path in attachments or []:
        if path.is_file():
            _add_attachment(message, path)
            attached.append(str(path))
    if not to_addr:
        return _write_outbox(message, reason="recipient email is empty")
    if not settings.smtp_host or not from_addr:
        return _write_outbox(message, reason="SMTP is not configured")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.ehlo()
        if settings.smtp_starttls and smtp.has_extn("STARTTLS"):
            smtp.starttls()
            smtp.ehlo()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
    return {"sent": True, "queued": False, "to": to_addr, "attachments": attached}


def completion_mail_body(job: JobRecord) -> str:
    payload = job.payload or {}
    result = job.result or {}
    return "\n".join(
        [
            f"{payload.get('requester') or job.requester}님,",
            "",
            "엑셀 수시결제 전표 처리가 완료되었고 출력 요청까지 정상 제출되었습니다.",
            "",
            f"- 작업: {job.title}",
            f"- 회사: {payload.get('company_name') or job.company_key}",
            f"- 회계일: {job.accounting_date}",
            f"- 전표 행: {payload.get('line_count', 0)}",
            f"- 차변 합계: {int(payload.get('debit_total') or 0):,}원",
            f"- 대변 합계: {int(payload.get('credit_total') or 0):,}원",
            f"- 출력 파일: {result.get('print_file') or '-'}",
            f"- 서버 보관 PDF: {result.get('erp_pdf_server_path') or '-'}",
            "",
            "확인 부탁드립니다.",
        ]
    )


def notify_job_completed(job: JobRecord) -> dict[str, Any]:
    payload = job.payload or {}
    result = job.result or {}
    recipient = str(payload.get("requester_email") or "").strip()
    subject = f"[엑셀 전표 처리 완료] {job.title}"
    attachment = Path(str(result.get("erp_pdf_server_path") or ""))
    attachments = [attachment] if attachment.is_file() else []
    return send_mail(recipient, subject, completion_mail_body(job), attachments=attachments)


def failure_mail_body(job: JobRecord) -> str:
    payload = job.payload or {}
    result = job.result or {}
    return "\n".join(
        [
            f"{payload.get('requester') or job.requester}님",
            "",
            "엑셀 수시결제 전표 처리 중 오류가 발생했습니다.",
            "",
            f"- 작업: {job.title}",
            f"- 회사: {payload.get('company_name') or job.company_key}",
            f"- 회계일: {job.accounting_date}",
            f"- 오류: {job.error or result.get('error') or result.get('message') or '-'}",
            "",
            "전산팀에서 확인하겠습니다.",
        ]
    )


def notify_job_failed(job: JobRecord) -> dict[str, Any]:
    payload = job.payload or {}
    recipient = str(payload.get("requester_email") or "").strip()
    subject = f"[엑셀 전표 처리 오류] {job.title}"
    return send_mail(recipient, subject, failure_mail_body(job))


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
