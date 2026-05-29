from __future__ import annotations

import email
import imaplib
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .compuzone_quote import auto_attach_compuzone_quote
from .config import PROJECT_ROOT, settings
from .invoice_db import get_invoice_by_pdf_path, insert_crawler_invoice

log = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int, str], None]


@dataclass
class CollectResult:
    scanned_messages: int = 0
    target_count: int = 0
    saved_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    saved_invoice_ids: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scanned_messages": self.scanned_messages,
            "target_count": self.target_count,
            "saved_count": self.saved_count,
            "duplicate_count": self.duplicate_count,
            "failed_count": self.failed_count,
            "saved_invoice_ids": self.saved_invoice_ids,
            "errors": self.errors[-20:],
        }


def _ensure_crawler_path() -> None:
    for path in (PROJECT_ROOT / "tax_crawler", PROJECT_ROOT / "support"):
        if path.is_dir() and str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _crawler_api():
    _ensure_crawler_path()
    from crawler_main import (  # type: ignore
        crawl_invoice,
        decode_mime_header,
        extract_hometax_attachment,
        extract_kt_attachments,
        extract_links_from_mail,
        extract_xml_attachments,
        parse_mail_date,
    )

    return {
        "crawl_invoice": crawl_invoice,
        "decode_mime_header": decode_mime_header,
        "extract_hometax_attachment": extract_hometax_attachment,
        "extract_kt_attachments": extract_kt_attachments,
        "extract_links_from_mail": extract_links_from_mail,
        "extract_xml_attachments": extract_xml_attachments,
        "parse_mail_date": parse_mail_date,
    }


def _extract_mail_body(msg: email.message.Message) -> str:
    html_parts: list[str] = []
    text_parts: list[str] = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        content_type = part.get_content_type()
        if content_type not in {"text/html", "text/plain"}:
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        charset = part.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="ignore")
        if content_type == "text/html":
            html_parts.append(text)
        else:
            text_parts.append(text)
    return "\n".join(html_parts or text_parts)


def _mail_attachment_names(msg: email.message.Message, decode_mime_header) -> list[str]:
    names: list[str] = []
    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue
        try:
            filename = decode_mime_header(filename)
        except Exception:
            pass
        names.append(str(filename))
    return names


def _allow_xml_attachment_fallback(subject: str, body: str, attachment_names: list[str]) -> bool:
    text = "\n".join([subject or "", body or "", "\n".join(attachment_names or [])]).lower()
    if any(token in text for token in ("컴퓨존", "compuzone")):
        return False
    regular_markers = (
        "wehago",
        "csbill",
        "스마트빌",
        "국세청",
        "nts_etaxinvoice",
        "kt email",
        "autoever",
        "smartbill",
    )
    return any(token in text for token in regular_markers)


def _safe_subject(subject: str) -> str:
    subject = re.sub(r"\s+", " ", subject or "").strip()
    return subject[:120] if subject else "제목 없음"


_TRANSIENT_CRAWLER_ERROR_MARKERS = (
    "no such window",
    "target window already closed",
    "web view not found",
    "chrome not reachable",
    "disconnected",
    "invalid session id",
)


def _is_transient_crawler_error(message: str) -> bool:
    text = str(message or "").lower()
    return any(marker in text for marker in _TRANSIENT_CRAWLER_ERROR_MARKERS)


def _fetch_message_without_seen(mail: imaplib.IMAP4_SSL, mail_id: bytes) -> bytes | None:
    _, data = mail.fetch(mail_id, "(BODY.PEEK[])")
    if not data:
        return None
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2:
            return item[1]
    return None


def _set_mail_seen(mail: imaplib.IMAP4_SSL, mail_id: bytes, seen: bool) -> None:
    try:
        op = "+FLAGS" if seen else "-FLAGS"
        mail.store(mail_id, op, r"(\Seen)")
    except Exception as exc:
        log.warning("failed to set mail seen=%s for %r: %s", seen, mail_id, exc)


def _crawl_invoice_with_retry(
    api: dict,
    target: str,
    body: str,
    mail_date: str,
    subject: str,
    emit: Callable[[str, int, str], None],
    progress_value: int,
) -> dict:
    attempts = 2
    last_result: dict = {"ok": False, "error": "crawler failed"}
    for attempt in range(1, attempts + 1):
        try:
            last_result = api["crawl_invoice"](
                target,
                mail_text=body,
                mail_date=mail_date,
                mail_subject=subject,
            )
        except Exception as exc:
            last_result = {"ok": False, "error": str(exc)}

        if last_result.get("ok"):
            if attempt > 1:
                emit("analyzing", min(progress_value + 2, 84), "crawler retry succeeded")
            return last_result

        error = str(last_result.get("error") or "crawler failed")
        should_retry = attempt < attempts and _is_transient_crawler_error(error)
        if not should_retry:
            return last_result

        short_error = re.sub(r"\s+", " ", error).strip()[:180]
        emit(
            "crawling",
            progress_value,
            f"Chrome window closed, retry {attempt}/{attempts - 1}: {short_error}",
        )
        time.sleep(3)

    return last_result


def collect_mail_once(progress: ProgressCallback | None = None) -> dict:
    if not settings.email_id or not settings.email_pw:
        raise RuntimeError("EMAIL_ID/EMAIL_PW가 설정되지 않았습니다.")

    def emit(status: str, progress_value: int, message: str) -> None:
        if progress:
            progress(status, progress_value, message)
        log.info("[mail-collect] %s %s%% %s", status, progress_value, message)

    api = _crawler_api()
    result = CollectResult()
    settings.download_dir.mkdir(parents=True, exist_ok=True)

    emit("running", 10, "메일/크롤러 환경 준비 완료")
    mail = imaplib.IMAP4_SSL(settings.imap_server)
    try:
        emit("crawling", 15, f"{settings.imap_server} 로그인")
        mail.login(settings.email_id, settings.email_pw)
        mail.select("inbox")
        _, messages = mail.search(None, "UNSEEN")
        mail_ids = messages[0].split() if messages and messages[0] else []
        result.scanned_messages = len(mail_ids)
        emit("crawling", 20, f"읽지 않은 메일 {len(mail_ids)}건 확인")

        if not mail_ids:
            return result.to_dict()

        for index, mail_id in enumerate(mail_ids, start=1):
            base_progress = 20 + int((index - 1) / max(len(mail_ids), 1) * 55)
            raw_message = _fetch_message_without_seen(mail, mail_id)
            if not raw_message:
                continue
            msg = email.message_from_bytes(raw_message)
            subject = api["decode_mime_header"](msg.get("Subject", ""))
            body = _extract_mail_body(msg)
            mail_date = api["parse_mail_date"](msg)
            attachment_names = _mail_attachment_names(msg, api["decode_mime_header"])
            emit("crawling", base_progress, f"메일 분석: {_safe_subject(subject)}")

            targets: list[str] = []
            targets.extend(api["extract_links_from_mail"](body))
            hometax_uri = api["extract_hometax_attachment"](msg, str(settings.download_dir))
            if hometax_uri:
                targets.append(hometax_uri)
            targets.extend(api["extract_kt_attachments"](msg, str(settings.download_dir)))
            if not targets and _allow_xml_attachment_fallback(subject, body, attachment_names):
                targets.extend(api["extract_xml_attachments"](msg, str(settings.download_dir)))

            targets = list(dict.fromkeys(targets))
            result.target_count += len(targets)
            if not targets:
                emit("crawling", min(base_progress + 4, 75), "지원 가능한 세금계산서 링크/첨부 없음")
                _set_mail_seen(mail, mail_id, True)
                continue

            mail_failed = False
            for target in targets:
                crawl_progress = min(base_progress + 8, 78)
                emit("crawling", crawl_progress, f"Crawling start: {target[:80]}")
                try:
                    crawled = _crawl_invoice_with_retry(
                        api,
                        target,
                        body,
                        mail_date or time.strftime("%y%m%d"),
                        subject,
                        emit,
                        crawl_progress,
                    )
                    if crawled.get("ok"):
                        inserted = insert_crawler_invoice(subject, crawled)
                        invoice_type = str(crawled.get("invoice_type") or "regular")
                        if inserted:
                            result.saved_count += 1
                            if invoice_type == "purchase":
                                invoice = get_invoice_by_pdf_path(str(crawled.get("pdf_path") or ""))
                                if invoice:
                                    result.saved_invoice_ids.append(int(invoice["id"]))
                                    emit("analyzing", min(base_progress + 18, 86), "컴퓨존 견적서 자동첨부 확인")
                                    quote_result = auto_attach_compuzone_quote(
                                        int(invoice["id"]),
                                        progress=lambda message: emit("analyzing", min(base_progress + 20, 88), message),
                                    )
                                    if quote_result.get("ok") and not quote_result.get("skipped"):
                                        emit("analyzing", min(base_progress + 24, 90), "컴퓨존 견적서 자동첨부 완료")
                                    elif quote_result.get("reason") not in {"not compuzone", "quote already exists"}:
                                        emit("analyzing", min(base_progress + 24, 90), f"컴퓨존 견적서 자동첨부 보류: {quote_result.get('reason')}")
                            emit("analyzing", min(base_progress + 16, 84), f"DB 저장 완료: {invoice_type}")
                        else:
                            result.duplicate_count += 1
                            emit("analyzing", min(base_progress + 16, 84), f"중복 자료라 DB 저장 생략: {invoice_type}")
                    else:
                        mail_failed = True
                        result.failed_count += 1
                        error = str(crawled.get("error") or "크롤링 실패")
                        result.errors.append(error)
                        emit("analyzing", min(base_progress + 16, 84), f"크롤링 실패 기록: {error}")
                except Exception as exc:
                    mail_failed = True
                    result.failed_count += 1
                    result.errors.append(str(exc))
                    emit("analyzing", min(base_progress + 16, 84), f"대상 처리 실패 기록: {exc}")

            if mail_failed:
                _set_mail_seen(mail, mail_id, False)
                emit("analyzing", min(base_progress + 18, 86), "mail kept unread because some targets failed")
            else:
                _set_mail_seen(mail, mail_id, True)

        return result.to_dict()
    finally:
        try:
            mail.logout()
        except Exception:
            pass
