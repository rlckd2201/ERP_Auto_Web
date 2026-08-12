from __future__ import annotations

import os
import re
import time
from email.header import decode_header, make_header
from email.message import Message
from pathlib import Path
from typing import Any, Callable

from .config import settings


ZOOM_ACCOUNT_NO = "3007982863"


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\x00", " ")).strip()


def _safe_filename(name: str, fallback: str = "zoom_invoice.pdf") -> str:
    clean = re.sub(r'[\\/:*?"<>|]+', "_", str(name or "").strip())
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or fallback


def _decode_filename(value: Any, decode_mime_header: Callable[[str], str] | None = None) -> str:
    text = str(value or "")
    if decode_mime_header:
        try:
            return str(decode_mime_header(text) or text)
        except Exception:
            pass
    try:
        return str(make_header(decode_header(text)))
    except Exception:
        return text


def is_zoom_billing_mail(subject: str, body: str, attachment_names: list[str] | None = None) -> bool:
    text = _clean_text(f"{subject}\n{body}\n{' '.join(attachment_names or [])}").lower()
    if ZOOM_ACCOUNT_NO not in text:
        return False
    if "zoom" not in text and "청구서" not in text:
        return False
    return "결제 처리 완료" in text or "payment" in text or "inv" in text


def _extract_pdf_text(path: str | Path) -> str:
    chunks: list[str] = []
    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                chunks.append(page.extract_text() or "")
        text = "\n".join(chunks)
        if text.strip():
            return text
    except Exception:
        pass
    try:
        import fitz

        with fitz.open(str(path)) as doc:
            return "\n".join(page.get_text() or "" for page in doc)
    except Exception:
        return "\n".join(chunks)


def _to_int(value: Any) -> int:
    try:
        if isinstance(value, (int, float)):
            return int(round(float(value)))
        text = re.sub(r"[^\d.-]+", "", str(value or ""))
        return int(round(float(text))) if text not in {"", ".", "-", "-."} else 0
    except Exception:
        return 0


def _to_float(value: Any) -> float:
    try:
        text = re.sub(r"[^\d.-]+", "", str(value or ""))
        return float(text) if text not in {"", ".", "-", "-."} else 0.0
    except Exception:
        return 0.0


def _parse_date(text: str) -> str:
    match = re.search(r"(20\d{2})[./\-\s]+(0?\d|1[0-2])[./\-\s]+([0-3]?\d)", str(text or ""))
    if not match:
        return ""
    yyyy, mm, dd = match.groups()
    return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"


def _mail_date_to_iso(mail_date: str) -> str:
    text = str(mail_date or "").strip()
    if re.fullmatch(r"\d{6}", text):
        yy = int(text[:2])
        yyyy = 2000 + yy if yy < 80 else 1900 + yy
        return f"{yyyy:04d}-{int(text[2:4]):02d}-{int(text[4:6]):02d}"
    parsed = _parse_date(text)
    if parsed:
        return parsed
    return time.strftime("%Y-%m-%d")


def _first_match(patterns: list[str], text: str, *, flags: int = re.IGNORECASE) -> re.Match[str] | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match
    return None


def _parse_zoom_pdf(pdf_path: Path, body: str, mail_date: str) -> dict[str, Any]:
    pdf_text = _extract_pdf_text(pdf_path)
    flat = _clean_text(f"{body}\n{pdf_text}")
    invoice_no = ""
    invoice_match = _first_match(
        [
            r"청구서\s*번호\s*[:：]?\s*([A-Z0-9-]+)",
            r"\b(INV\d{6,})\b",
        ],
        flat,
    )
    if invoice_match:
        invoice_no = invoice_match.group(1).strip()

    invoice_date = ""
    date_match = _first_match([r"청구서\s*날짜\s*[:：]?\s*(20\d{2}[./\-\s]+[01]?\d[./\-\s]+[0-3]?\d)"], flat)
    if date_match:
        invoice_date = _parse_date(date_match.group(1))
    invoice_date = invoice_date or _mail_date_to_iso(mail_date)

    period_start = ""
    period_end = ""
    period_match = _first_match(
        [
            r"(20\d{2}[./\-\s]+[01]?\d[./\-\s]+[0-3]?\d)\s*[-~–—]\s*(20\d{2}[./\-\s]+[01]?\d[./\-\s]+[0-3]?\d)",
            r"(20\d{2}[./\-\s]+[01]?\d[./\-\s]+[0-3]?\d)\s+(20\d{2}[./\-\s]+[01]?\d[./\-\s]+[0-3]?\d)\s+\d",
        ],
        flat,
    )
    if period_match:
        period_start = _parse_date(period_match.group(1))
        period_end = _parse_date(period_match.group(2))

    currency = "KRW"
    currency_match = _first_match([r"통화\s*[:：]?\s*([A-Z]{3})", r"\b(USD|KRW)\b"], flat)
    if currency_match:
        currency = currency_match.group(1).upper()

    total_foreign = 0.0
    total_match = _first_match(
        [
            r"청구서\s*총액\s*([\d,]+(?:\.\d+)?)\s*(USD|KRW)",
            r"총계\(.*?\)\s*([\d,]+(?:\.\d+)?)\s*(USD|KRW)",
            r"금액\s*[:：]?\s*([\d,]+(?:\.\d+)?)\s*(?:US\s*Dollar|USD)",
        ],
        flat,
    )
    if total_match:
        total_foreign = _to_float(total_match.group(1))
        if len(total_match.groups()) >= 2 and total_match.group(2):
            currency = total_match.group(2).upper().replace("US DOLLAR", "USD")

    krw_total = 0
    krw_match = _first_match(
        [
            r"청구서\s*총액\s*([\d,]+)\s*(?:원|KRW)",
            r"총계(?:\(.*?\))?\s*([\d,]+)\s*(?:원|KRW)",
            r"금액\s*[:：]?\s*([\d,]+)\s*(?:원|KRW)",
        ],
        flat,
    )
    if currency == "KRW" and total_foreign:
        krw_total = _to_int(total_foreign)
    if krw_match:
        krw_total = _to_int(krw_match.group(1))

    exchange_rate = 0.0
    amount_source = "pdf_krw" if krw_total else ""
    if not krw_total and currency == "USD" and total_foreign:
        amount_source = "foreign_currency"

    service_month = invoice_date[:7] if invoice_date else time.strftime("%Y-%m")
    yyyy, mm = (service_month.split("-") + [""])[:2]
    item_name = f"Zoom Workplace Business {int(mm):02d}월 사용료" if mm else "Zoom Workplace Business 사용료"
    if yyyy and mm:
        item_name = f"Zoom Workplace Business {yyyy}년 {int(mm):02d}월 사용료"

    foreign_text = f"{total_foreign:,.2f} {currency}" if total_foreign else currency
    body_lines = [
        "* 내 용 *",
        "1. Zoom Workplace Business 사용료",
        f"   └ {item_name} : {krw_total:,}원" if krw_total else f"   └ {item_name} : {foreign_text}",
    ]
    if krw_total:
        body_lines.append(f"2. 총합 : {krw_total:,}원")
    elif currency and total_foreign:
        body_lines.append(f"2. 총합 : {foreign_text}")

    item = {
        "name": item_name,
        "desc": item_name,
        "raw_desc": item_name,
        "qty": 1,
        "supply": krw_total,
        "inc_vat": krw_total,
        "account": "지급수수료",
        "department": "전산팀",
    }

    return {
        "portal": "zoom_billing",
        "invoice_type": "regular",
        "document_kind": "zoom_billing",
        "zoom_billing": True,
        "subject": f"Zoom 청구서 {invoice_no or invoice_date}",
        "pdf_path": str(pdf_path),
        "vendor_name": "Zoom",
        "supplier_name": "Zoom Communications, Inc.",
        "site_name": "(주)대승",
        "buyer_name": "(주)대승",
        "invoice_date": invoice_date,
        "issue_date": invoice_date,
        "write_date": invoice_date,
        "service_period_start": period_start,
        "service_period_end": period_end,
        "billing_month": service_month,
        "invoice_no": invoice_no,
        "zoom_account_no": ZOOM_ACCOUNT_NO,
        "currency": currency,
        "foreign_total_amount": total_foreign,
        "exchange_rate": exchange_rate,
        "amount_source": amount_source,
        "total_sum": krw_total,
        "total_amount": krw_total,
        "amount": krw_total,
        "target_supply": krw_total,
        "total_supply": krw_total,
        "total_tax": 0,
        "items": [item],
        "expense_basis": "Zoom 청구서",
        "expense_title": item_name,
        "expense_body": "\n".join(body_lines),
        "expense_payee": "Zoom",
        "data": {},
    }


def extract_zoom_billing_invoice(
    msg: Message,
    *,
    subject: str,
    body: str,
    mail_date: str,
    decode_mime_header: Callable[[str], str] | None = None,
) -> dict[str, Any] | None:
    attachment_names: list[str] = []
    for part in msg.walk():
        filename = part.get_filename()
        if filename:
            attachment_names.append(_decode_filename(filename, decode_mime_header))
    if not is_zoom_billing_mail(subject, body, attachment_names):
        return None

    target_part: Message | None = None
    target_name = ""
    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue
        decoded = _decode_filename(filename, decode_mime_header)
        if decoded.lower().endswith(".pdf"):
            target_part = part
            target_name = decoded
            if "inv" in decoded.lower():
                break
    if not target_part:
        raise RuntimeError("Zoom 청구서 PDF 첨부파일을 찾지 못했습니다.")

    payload = target_part.get_payload(decode=True) or b""
    if not payload:
        raise RuntimeError("Zoom 청구서 PDF 첨부파일이 비어 있습니다.")

    settings.download_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(target_name, fallback=f"Zoom_{ZOOM_ACCOUNT_NO}_{int(time.time())}.pdf")
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    pdf_path = settings.download_dir / safe_name
    pdf_path.write_bytes(payload)

    parsed = _parse_zoom_pdf(pdf_path, body, mail_date)
    parsed["mail_subject"] = subject
    parsed["attachment_name"] = target_name
    parsed["data"] = {key: value for key, value in parsed.items() if key != "data"}
    return parsed
