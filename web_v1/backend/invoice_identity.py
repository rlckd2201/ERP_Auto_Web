"""Stable tax-document identity; filenames and repeated amounts are not identities."""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

_NUMBER = re.compile(r"[12][0-9]{7}[0-9A-Z]{16}")
_LABELLED_NUMBER = re.compile(
    r"승\s*인\s*번\s*호\s*[:：]?\s*"
    r"([12][0-9]{7}\s*-?\s*[0-9A-Z]{8}\s*-?\s*[0-9A-Z]{8})"
    r"(?![0-9A-Z])", re.IGNORECASE,
)
_NUMBER_FIELDS = {
    "taxapprovalnumber", "taxapprovalno", "approvalnumber", "approvalno",
    "ntsapprovalnumber", "ntsapprovalno", "issueid", "승인번호", "국세청승인번호",
}


def normalize_approval_number(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).upper()
    text = re.sub(r"[\s-]+", "", text)
    if not _NUMBER.fullmatch(text):
        return ""
    try:
        datetime.strptime(text[:8], "%Y%m%d")
    except ValueError:
        return ""
    return text


def numbers_from_text(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text or "")
    return {number for match in _LABELLED_NUMBER.finditer(normalized)
            if (number := normalize_approval_number(match.group(1)))}


def _metadata_numbers(value: Any, depth: int = 0) -> set[str]:
    if not isinstance(value, dict) or depth > 6:
        return set()
    found = set()
    for key, item in value.items():
        field = re.sub(r"[\s_:-]+", "", str(key)).lower()
        if field in _NUMBER_FIELDS:
            number = normalize_approval_number(item)
            if number:
                found.add(number)
        if key in {"data", "raw"}:
            found.update(_metadata_numbers(item, depth + 1))
    return found


@lru_cache(maxsize=2048)
def _pdf_numbers(path: str, modified_ns: int, size: int) -> frozenset[str]:
    import fitz
    with fitz.open(path) as document:
        if len(document) > 10:
            return frozenset()
        numbers = set()
        for page in document:
            numbers.update(numbers_from_text(page.get_text()))
        return frozenset(numbers)


def tax_approval_number(invoice: dict[str, Any]) -> str:
    numbers = _metadata_numbers(invoice)
    raw = invoice.get("raw") if isinstance(invoice.get("raw"), dict) else {}
    data = invoice.get("data") if isinstance(invoice.get("data"), dict) else {}
    source = invoice.get("pdf_path") or raw.get("pdf_path") or data.get("pdf_path")
    if source:
        try:
            path = Path(str(source))
            stat = path.stat()
            if path.suffix.lower() == ".pdf" and 0 < stat.st_size <= 20 * 1024 * 1024:
                numbers.update(_pdf_numbers(str(path.resolve()), stat.st_mtime_ns, stat.st_size))
        except Exception:
            # A transient read exception is not cached. Previously verified
            # structured numbers remain usable when the original PDF is offline.
            pass
    return next(iter(numbers)) if len(numbers) == 1 else ""


def is_csbill_invoice(invoice: dict[str, Any]) -> bool:
    for value in (invoice, invoice.get("raw"), invoice.get("data")):
        if isinstance(value, dict):
            if str(value.get("portal") or "").strip().lower() == "csbill":
                return True
    return False


def _stored_invoice(row) -> dict[str, Any]:
    try:
        raw = json.loads(row["json_data"] or "{}")
    except (TypeError, ValueError):
        raw = {}
    return {"id": row["id"], "pdf_path": row["pdf_path"],
            "raw": raw if isinstance(raw, dict) else {}}


def warm_stored_identities(conn) -> None:
    # Do expensive legacy-PDF reads before BEGIN IMMEDIATE acquires a write lock.
    rows = conn.execute("SELECT id, pdf_path, json_data FROM invoices").fetchall()
    for row in rows:
        tax_approval_number(_stored_invoice(row))


def find_tax_duplicate(conn, number: str) -> int | None:
    if not number:
        return None
    for row in conn.execute("SELECT id, pdf_path, json_data FROM invoices ORDER BY id"):
        if tax_approval_number(_stored_invoice(row)) == number:
            return int(row["id"])
    return None
