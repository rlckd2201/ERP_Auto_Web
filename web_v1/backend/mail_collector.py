from __future__ import annotations

import email
import imaplib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from .compuzone_quote import auto_attach_compuzone_quote
from .config import PROJECT_ROOT, settings
from .invoice_db import get_invoice_by_pdf_path, insert_crawler_invoice
from .mail_content import MailContentStore, content_fingerprint
from .zoom_billing import extract_zoom_billing_invoice, is_zoom_billing_mail

log = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int, str], None]


@dataclass
class CollectResult:
    scanned_messages: int = 0
    unread_messages: int = 0
    target_count: int = 0
    saved_count: int = 0
    duplicate_count: int = 0
    content_duplicate_count: int = 0
    failed_count: int = 0
    deferred_count: int = 0
    ignored_count: int = 0
    saved_invoice_ids: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scanned_messages": self.scanned_messages,
            "unread_messages": self.unread_messages,
            "target_count": self.target_count,
            "saved_count": self.saved_count,
            "duplicate_count": self.duplicate_count,
            "content_duplicate_count": self.content_duplicate_count,
            "failed_count": self.failed_count,
            "deferred_count": self.deferred_count,
            "ignored_count": self.ignored_count,
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


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, str(default))).strip())
    except Exception:
        return default


def _state_path() -> Path:
    return settings.erp_db_dir / "purchase_mail_collect_state.json"


def _load_state() -> dict:
    path = _state_path()
    try:
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
    except Exception:
        log.exception("purchase mail collector state load failed")
    return {}


def _save_state(state: dict) -> None:
    path = _state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)
    except Exception:
        log.exception("purchase mail collector state save failed")


def _message_state_key(msg: email.message.Message, fallback: bytes) -> str:
    message_id = str(msg.get("Message-ID") or msg.get("Message-Id") or "").strip()
    if message_id:
        return f"message-id:{message_id}"
    subject = re.sub(r"\s+", " ", str(msg.get("Subject") or "")).strip()
    date = re.sub(r"\s+", " ", str(msg.get("Date") or "")).strip()
    return f"mail:{date}:{subject}:{fallback.decode(errors='ignore')}"


def _remember_processed(state: dict, key: str, subject: str, reason: str, sender: str = "", *, fingerprint: str = "") -> None:
    processed = state.get("processed")
    if not isinstance(processed, dict):
        processed = {}
        state["processed"] = processed
    processed[key] = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reason": reason,
        "subject": _safe_subject(subject),
        "sender": _safe_subject(sender),
        "content_fingerprint": fingerprint,
    }


def _failure_records(state: dict) -> dict[str, dict]:
    failures = state.get("failures")
    if not isinstance(failures, dict):
        failures = {}
        state["failures"] = failures
    return failures


def _failure_delay_seconds(attempts: int) -> int:
    if attempts <= 1:
        return 15 * 60
    if attempts == 2:
        return 60 * 60
    if attempts == 3:
        return 6 * 60 * 60
    return 12 * 60 * 60


def _remember_failure(state: dict, key: str, subject: str, sender: str, error: str) -> dict:
    failures = _failure_records(state)
    previous = failures.get(key)
    previous_attempts = int(previous.get("attempts") or 0) if isinstance(previous, dict) else 0
    attempts = previous_attempts + 1
    now = datetime.now(timezone.utc)
    delay_seconds = _failure_delay_seconds(attempts)
    value = {
        "attempts": attempts,
        "failed_at": now.isoformat(timespec="seconds"),
        "next_retry_at": (now + timedelta(seconds=delay_seconds)).isoformat(timespec="seconds"),
        "subject": _safe_subject(subject),
        "sender": _safe_subject(sender),
        "error": _safe_subject(error),
    }
    failures[key] = value
    return value


def _clear_failure(state: dict, key: str) -> None:
    _failure_records(state).pop(key, None)


def _failure_wait_seconds(value: object) -> int:
    if not isinstance(value, dict):
        return 0
    try:
        next_retry_at = datetime.fromisoformat(str(value.get("next_retry_at") or ""))
        if next_retry_at.tzinfo is None:
            next_retry_at = next_retry_at.replace(tzinfo=timezone.utc)
    except Exception:
        return 0
    return max(0, int((next_retry_at - datetime.now(timezone.utc)).total_seconds()))


def _prune_state(state: dict, retention_hours: int = 72, max_items: int = 1000) -> None:
    processed = state.get("processed")
    if not isinstance(processed, dict):
        processed = {}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, retention_hours))
    kept: dict[str, dict] = {}
    for key, value in processed.items():
        if not isinstance(value, dict):
            continue
        try:
            at = datetime.fromisoformat(str(value.get("at") or ""))
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if at >= cutoff:
            kept[str(key)] = value
    if len(kept) > max_items:
        kept = dict(sorted(kept.items(), key=lambda item: str(item[1].get("at") or ""))[-max_items:])
    state["processed"] = kept

    failure_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    kept_failures: dict[str, dict] = {}
    for key, value in _failure_records(state).items():
        if not isinstance(value, dict):
            continue
        try:
            failed_at = datetime.fromisoformat(str(value.get("failed_at") or ""))
            if failed_at.tzinfo is None:
                failed_at = failed_at.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if failed_at >= failure_cutoff:
            kept_failures[str(key)] = value
    state["failures"] = kept_failures


def mail_collect_processed_history(limit: int = 200, query: str = "") -> list[dict]:
    state = _load_state()
    processed = state.get("processed") if isinstance(state.get("processed"), dict) else {}
    query_text = str(query or "").strip().lower()
    items: list[dict] = []
    for key, value in processed.items():
        if not isinstance(value, dict):
            continue
        row = {
            "key": str(key),
            "at": str(value.get("at") or ""),
            "reason": str(value.get("reason") or ""),
            "subject": str(value.get("subject") or ""),
            "sender": str(value.get("sender") or ""),
        }
        haystack = json.dumps(row, ensure_ascii=False).lower()
        if query_text and query_text not in haystack:
            continue
        items.append(row)
    items.sort(key=lambda item: item.get("at") or "", reverse=True)
    return items[: max(1, min(int(limit or 200), 1000))]


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






def _env_csv(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip().lower() for item in raw.split(",") if item.strip())


_UNIPOST_IGNORE_TOKENS = _env_csv(
    "PURCHASE_MAIL_UNIPOST_IGNORE_TOKENS",
    "\ub2e4\uc6b0\ub370\uc774\ud130,\ub2e4\uc6b0\ub370\uc774\ud0c0,daoudata,skup",
)

_AUTO_COLLECT_ALLOWED_TOKENS = _env_csv(
    "PURCHASE_MAIL_AUTO_ALLOW_TOKENS",
    "\ucef4\ud4e8\uc874,compuzone,\ucfe0\ud321,\uc544\uc774\ucf54\ub2e4,\uc624\ud53c\uc2a4\ub514\ud3ec,\uac00\ube44\uc544,naver,npay,"
    "\ub300\uc2e0\uc544\uc774\uc528\ud2f0,\ub300\uc2e0\ub124\ud2b8\uc6cd\uc2a4,\ub3d9\uc591\uc815\ubcf4\ud1b5\uc2e0,kt,\ucf00\uc774\ud2f0,autoever,\uc624\ud1a0\uc5d0\ubc84,"
    "\ub2e4\uc6b0\uae30\uc220,\uc548\ub7a9,\uc2dc\ud050\uc5b4\ud3ec\uc778\ud2b8,\uc774\ud14c\ud06c\uc2dc\uc2a4\ud15c,\uc5d0\ud2f0\ubc84\uc2a4,\ud53c\ud50c\ub7ec\uc2a4,zoom",
)


def _compact_text(*values: object) -> str:
    return re.sub(r"\s+", " ", "\n".join(str(value or "") for value in values)).strip().lower()


def _is_unipost_url(value: str) -> bool:
    return "etax.unipost.co.kr" in str(value or "").lower()


def _skip_auto_collect_target(subject: str, body: str, attachment_names: list[str], target: str) -> str:
    if not _is_unipost_url(target):
        return ""
    text = _compact_text(subject, body, "\n".join(attachment_names or []), target)
    if any(token and token in text for token in _UNIPOST_IGNORE_TOKENS):
        return "Unipost \uc5c5\ubb34\ub300\uc0c1 \uc678 \uacc4\uc0b0\uc11c(\ub2e4\uc6b0\ub370\uc774\ud0c0/SKUP)"
    return ""


def _crawled_invoice_text(subject: str, body: str, target: str, crawled: dict) -> str:
    data = crawled.get("data") if isinstance(crawled.get("data"), dict) else {}
    items = data.get("items") if isinstance(data.get("items"), list) else []
    item_text = " ".join(
        str((item or {}).get("name") or (item or {}).get("item_name") or "")
        for item in items
        if isinstance(item, dict)
    )
    return _compact_text(
        subject,
        crawled.get("subject"),
        data.get("vendor_name"),
        data.get("supplier_name"),
        data.get("site_name"),
        data.get("buyer_name"),
        item_text,
        target,
        body[:2000],
    )


def _skip_crawled_invoice(subject: str, body: str, target: str, crawled: dict) -> str:
    if not _is_unipost_url(target):
        return ""
    text = _crawled_invoice_text(subject, body, target, crawled)
    if any(token and token in text for token in _UNIPOST_IGNORE_TOKENS):
        return "Unipost \uc5c5\ubb34\ub300\uc0c1 \uc678 \uacc4\uc0b0\uc11c(\ub2e4\uc6b0\ub370\uc774\ud0c0/SKUP)"
    if any(token and token in text for token in _AUTO_COLLECT_ALLOWED_TOKENS):
        return ""
    return "Unipost \uc790\ub3d9\uc218\uc9d1 \ud5c8\uc6a9 \ubaa9\ub85d \uc678 \uacc4\uc0b0\uc11c"

def _uid_search(mail: imaplib.IMAP4_SSL, *criteria: str) -> list[bytes]:
    status, data = mail.uid("search", None, *criteria)
    if status != "OK" or not data or not data[0]:
        return []
    return data[0].split()


def _imap_since_date(value: datetime) -> str:
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{value.day:02d}-{months[value.month - 1]}-{value.year:04d}"


def _fetch_message_without_seen(mail: imaplib.IMAP4_SSL, mail_id: bytes) -> bytes | None:
    _, data = mail.uid("fetch", mail_id, "(BODY.PEEK[])")
    if not data:
        return None
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2:
            return item[1]
    return None


def _set_mail_seen(mail: imaplib.IMAP4_SSL, mail_id: bytes, seen: bool) -> None:
    try:
        op = "+FLAGS" if seen else "-FLAGS"
        mail.uid("store", mail_id, op, r"(\Seen)")
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
    approve_on_unapproved: bool = False,
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
                approve_on_unapproved=approve_on_unapproved,
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


def collect_mail_once(progress: ProgressCallback | None = None, *, force_recent_scan: bool = False) -> dict:
    if not settings.email_id or not settings.email_pw:
        raise RuntimeError("EMAIL_ID/EMAIL_PW가 설정되지 않았습니다.")
    scope = "\n".join((settings.imap_server, settings.email_id, "inbox"))
    with MailContentStore(settings.erp_db_dir / "mail_content_state.sqlite3", scope) as content_history:
        return _collect_mail_once(progress, force_recent_scan=force_recent_scan,
                                  content_history=content_history)


def _collect_mail_once(progress: ProgressCallback | None = None, *, force_recent_scan: bool = False,
                       content_history: MailContentStore) -> dict:
    if not settings.email_id or not settings.email_pw:
        raise RuntimeError("EMAIL_ID/EMAIL_PW가 설정되지 않았습니다.")

    def emit(status: str, progress_value: int, message: str) -> None:
        if progress:
            progress(status, progress_value, message)
        log.info("[mail-collect] %s %s%% %s", status, progress_value, message)

    api = _crawler_api()
    result = CollectResult()
    approve_on_unapproved = _env_bool("SMILEEDI_AUTO_APPROVE", False)
    settings.download_dir.mkdir(parents=True, exist_ok=True)

    emit("running", 10, "메일/크롤러 환경 준비 완료")
    mail = imaplib.IMAP4_SSL(settings.imap_server)
    try:
        emit("crawling", 15, f"{settings.imap_server} 로그인")
        mail.login(settings.email_id, settings.email_pw)
        mail.select("inbox")
        state = _load_state()
        _prune_state(state, retention_hours=72)
        processed = state.get("processed") if isinstance(state.get("processed"), dict) else {}
        state["processed"] = processed
        failures = _failure_records(state)

        all_ids = _uid_search(mail, "ALL")
        current_max_uid = max((int(item) for item in all_ids if item.isdigit()), default=0)
        try:
            last_uid = max(0, int(state.get("inbox_last_uid") or 0))
        except Exception:
            last_uid = 0

        unread_ids = _uid_search(mail, "UNSEEN")
        new_ids: list[bytes] = []
        if last_uid and current_max_uid > last_uid:
            new_ids = _uid_search(mail, "UID", f"{last_uid + 1}:{current_max_uid}")

        recent_ids: list[bytes] = []
        if force_recent_scan:
            since = datetime.now() - timedelta(hours=48)
            recent_ids = _uid_search(mail, "SINCE", _imap_since_date(since))[-500:]

        mail_ids = list(dict.fromkeys([*unread_ids, *new_ids, *recent_ids]))
        result.unread_messages = len(unread_ids)
        result.scanned_messages = len(mail_ids)
        state["inbox_last_uid"] = max(last_uid, current_max_uid)
        if force_recent_scan:
            emit(
                "crawling",
                20,
                f"읽지 않은 메일 {len(unread_ids)}건 / 최근 48시간 {len(recent_ids)}건 강제 확인",
            )
        else:
            emit(
                "crawling",
                20,
                f"읽지 않은 메일 {len(unread_ids)}건 / 신규 UID {len(new_ids)}건 확인",
            )

        if not mail_ids:
            _save_state(state)
            return result.to_dict()

        for index, mail_id in enumerate(mail_ids, start=1):
            base_progress = 20 + int((index - 1) / max(len(mail_ids), 1) * 55)
            raw_message = _fetch_message_without_seen(mail, mail_id)
            if not raw_message:
                continue
            msg = email.message_from_bytes(raw_message)
            state_key = _message_state_key(msg, mail_id)
            subject = api["decode_mime_header"](msg.get("Subject", ""))
            sender = api["decode_mime_header"](msg.get("From", ""))
            body = _extract_mail_body(msg)
            mail_date = api["parse_mail_date"](msg)
            attachment_names = _mail_attachment_names(msg, api["decode_mime_header"])
            fingerprint = content_fingerprint(msg)

            def remember_message(reason: str) -> None:
                # Commit a receipt only after every target completed. A crash or
                # partial failure must not certify an uncollected message.
                content_history.remember(fingerprint, state_key, reason)
                _remember_processed(state, state_key, subject, reason, sender,
                                    fingerprint=fingerprint)

            prior_content = content_history.find(fingerprint)
            if prior_content:
                content_history.note_duplicate(fingerprint)
                remember_message("duplicate")
                processed[state_key]["duplicate_source"] = prior_content["first_message_key"]
                _clear_failure(state, state_key)
                result.duplicate_count += 1
                result.content_duplicate_count += 1
                emit("analyzing", min(base_progress + 4, 75),
                     "본문·첨부가 동일한 메일: 크롤링/PDF 저장 생략 "
                     f"(최초 수집: {prior_content['completed_at']})")
                _set_mail_seen(mail, mail_id, True)
                continue
            prior_state = processed.get(state_key)
            if isinstance(prior_state, dict) and (
                not fingerprint or not prior_state.get("content_fingerprint")
                or prior_state["content_fingerprint"] == fingerprint
            ):
                # Preserve the existing trusted Message-ID success history while
                # learning its content for subsequent relay-generated copies.
                content_history.remember(fingerprint, state_key, str(prior_state.get("reason") or ""))
                prior_state["content_fingerprint"] = fingerprint
                _clear_failure(state, state_key)
                result.duplicate_count += 1
                emit(
                    "analyzing",
                    min(base_progress + 4, 75),
                    "이미 처리한 메일: 크롤링/PDF 저장 재시도 생략",
                )
                # The previous run was successful. Persist the Seen flag again
                # in case IMAP did not retain it on the first attempt.
                _set_mail_seen(mail, mail_id, True)
                continue
            failure_wait = _failure_wait_seconds(failures.get(state_key))
            if failure_wait > 0 and not force_recent_scan:
                result.deferred_count += 1
                wait_minutes = max(1, (failure_wait + 59) // 60)
                emit(
                    "analyzing",
                    min(base_progress + 4, 75),
                    f"메일 재시도 대기: 약 {wait_minutes}분 후 재시도",
                )
                continue
            zoom_candidate = is_zoom_billing_mail(subject, body, attachment_names)
            emit("crawling", base_progress, f"메일 분석: {_safe_subject(subject)}")

            if zoom_candidate:
                mail_success_reason = "processed"
                try:
                    zoom_invoice = extract_zoom_billing_invoice(
                        msg,
                        subject=subject,
                        body=body,
                        mail_date=mail_date,
                        decode_mime_header=api["decode_mime_header"],
                    )
                    if zoom_invoice:
                        inserted = insert_crawler_invoice(subject, zoom_invoice)
                        if inserted:
                            mail_success_reason = "saved"
                            result.saved_count += 1
                            invoice = get_invoice_by_pdf_path(str(zoom_invoice.get("pdf_path") or ""))
                            if invoice:
                                result.saved_invoice_ids.append(int(invoice["id"]))
                            emit("analyzing", min(base_progress + 16, 84), "Zoom 청구서 저장 완료")
                        else:
                            mail_success_reason = "duplicate"
                            result.duplicate_count += 1
                            emit("analyzing", min(base_progress + 16, 84), "중복 Zoom 청구서 확인: 기존 데이터 갱신/중복 처리")
                    else:
                        emit("crawling", min(base_progress + 4, 75), "Zoom 청구서 후보였지만 지원 가능한 PDF 첨부 없음")
                    _clear_failure(state, state_key)
                    remember_message(mail_success_reason)
                    _set_mail_seen(mail, mail_id, True)
                    continue
                except Exception as exc:
                    result.failed_count += 1
                    result.errors.append(str(exc))
                    emit("analyzing", min(base_progress + 16, 84), f"Zoom 청구서 처리 실패: {exc}")
                    failure = _remember_failure(state, state_key, subject, sender, str(exc))
                    _save_state(state)
                    _set_mail_seen(mail, mail_id, False)
                    emit(
                        "analyzing",
                        min(base_progress + 18, 86),
                        f"Zoom 실패 메일 읽지 않음 유지 / {int(failure['attempts'])}차 실패, 자동 재시도 대기",
                    )
                    continue

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
                _clear_failure(state, state_key)
                remember_message("no supported tax invoice target")
                _set_mail_seen(mail, mail_id, True)
                continue

            mail_failed = False
            mail_ignored = False
            mail_errors: list[str] = []
            mail_success_reason = "processed"
            for target in targets:
                skip_reason = _skip_auto_collect_target(subject, body, attachment_names, target)
                if skip_reason:
                    mail_ignored = True
                    mail_success_reason = "ignored"
                    result.ignored_count += 1
                    emit("analyzing", min(base_progress + 12, 82), f"자동수집 제외: {skip_reason}")
                    continue
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
                        approve_on_unapproved=approve_on_unapproved,
                    )
                    if crawled.get("ok"):
                        skip_reason = _skip_crawled_invoice(subject, body, target, crawled)
                        if skip_reason:
                            mail_ignored = True
                            mail_success_reason = "ignored"
                            result.ignored_count += 1
                            emit("analyzing", min(base_progress + 16, 84), f"자동수집 제외: {skip_reason}")
                            continue
                        inserted = insert_crawler_invoice(subject, crawled)
                        invoice_type = str(crawled.get("invoice_type") or "regular")
                        if inserted:
                            mail_success_reason = "saved"
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
                            if mail_success_reason != "saved":
                                mail_success_reason = "duplicate"
                            result.duplicate_count += 1
                            emit("analyzing", min(base_progress + 16, 84), f"중복 자료라 DB 저장 생략: {invoice_type}")
                    else:
                        mail_failed = True
                        result.failed_count += 1
                        error = str(crawled.get("error") or "크롤링 실패")
                        result.errors.append(error)
                        mail_errors.append(error)
                        emit("analyzing", min(base_progress + 16, 84), f"크롤링 실패 기록: {error}")
                except Exception as exc:
                    mail_failed = True
                    result.failed_count += 1
                    result.errors.append(str(exc))
                    mail_errors.append(str(exc))
                    emit("analyzing", min(base_progress + 16, 84), f"대상 처리 실패 기록: {exc}")

            if mail_failed:
                failure = _remember_failure(
                    state,
                    state_key,
                    subject,
                    sender,
                    " | ".join(mail_errors[-3:]) or "WEHAGO PDF 다운로드 실패",
                )
                _save_state(state)
                _set_mail_seen(mail, mail_id, False)
                emit(
                    "analyzing",
                    min(base_progress + 18, 86),
                    f"실패 메일 읽지 않음 유지 / {int(failure['attempts'])}차 실패, 자동 재시도 대기",
                )
            else:
                _clear_failure(state, state_key)
                remember_message("ignored" if mail_ignored else mail_success_reason)
                _set_mail_seen(mail, mail_id, True)

        _save_state(state)
        return result.to_dict()
    finally:
        try:
            mail.logout()
        except Exception:
            pass
