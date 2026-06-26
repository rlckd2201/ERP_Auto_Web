from __future__ import annotations

import json
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from .models import JobRecord
from .settings import settings


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
                "body": message.get_content(),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"sent": False, "queued": True, "outbox_path": str(path), "reason": reason}


def send_mail(to_addr: str, subject: str, body: str) -> dict[str, Any]:
    to_addr = (to_addr or "").strip()
    from_addr = (settings.smtp_from or settings.smtp_user or "").strip()
    message = EmailMessage()
    message["To"] = to_addr
    message["From"] = from_addr
    message["Subject"] = subject
    message.set_content(body)
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
    return {"sent": True, "queued": False, "to": to_addr}


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
            "",
            "확인 부탁드립니다.",
        ]
    )


def notify_job_completed(job: JobRecord) -> dict[str, Any]:
    payload = job.payload or {}
    recipient = str(payload.get("requester_email") or "").strip()
    subject = f"[엑셀 전표 처리 완료] {job.title}"
    return send_mail(recipient, subject, completion_mail_body(job))


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
