from __future__ import annotations

import calendar
import html
import json
import logging
import os
import re
import smtplib
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Any

from .config import settings
from .invoice_db import get_invoice, list_invoices


log = logging.getLogger(__name__)
_scheduler_started = False
_scheduler_lock = threading.RLock()


@dataclass(frozen=True)
class DueRule:
    key: str
    vendor_name: str
    aliases: tuple[str, ...]
    biz_no: str
    frequency: str
    issue_kind: str
    issue_day: int = 0
    receive_due_day: int = 0
    quarterly_months: tuple[int, ...] = ()
    note: str = ""
    required_tokens: tuple[str, ...] = ()
    excluded_tokens: tuple[str, ...] = ()


REGULAR_DUE_RULES: tuple[DueRule, ...] = (
    DueRule("kt", "KT", ("kt", "케이티"), "102-81-42945", "1개월", "day", 6, 12, note="명세서 작성일자는 6일, 메일 수신 기대일은 12일"),
    DueRule("autoever", "현대오토에버", ("현대오토에버", "오토에버", "autoever"), "104-81-53190", "1개월", "day", 20),
    DueRule("daou", "다우기술", ("다우기술", "다우오피스", "daou"), "220-81-02810", "1개월", "day", 11),
    DueRule("securepoint", "시큐어포인트", ("시큐어포인트", "genian", "nac"), "534-87-01726", "1개월", "last_day"),
    DueRule("dongyang", "동양정보통신", ("동양정보통신",), "402-81-23213", "1개월", "last_day"),
    DueRule("daeshinict", "대신아이씨티", ("대신아이씨티",), "504-86-20609", "1개월", "last_day"),
    DueRule("etech", "이테크시스템", ("이테크시스템", "이테크", "acronis"), "211-88-35257", "1개월", "day", 20),
    DueRule("etebus", "에티버스", ("에티버스", "watching-on", "watchingon", "watching"), "106-81-43363", "1개월", "by_day", 10, note="10일 전후 수신 기준"),
    DueRule("ahnlab", "안랩", ("안랩", "ahnlab"), "214-81-83536", "1개월", "day", 7),
    DueRule(
        "pplus_dlp",
        "피플러스",
        ("피플러스",),
        "",
        "3개월(3월부터)",
        "last_day",
        quarterly_months=(3, 6, 9, 12),
        note="DLP만 점검, Cloudoc은 무상유지보수 기간 제외",
        required_tokens=("dlp", "gradius"),
        excluded_tokens=("cloudoc", "문서중앙화"),
    ),
)


def _env_bool(name: str, default: bool) -> bool:
    value = str(os.getenv(name, "1" if default else "0")).strip().lower()
    return value not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, str(default))).strip())
    except Exception:
        return default


def _enabled() -> bool:
    return _env_bool("REGULAR_DUE_ALERT_ENABLED", True)


def _recipient() -> str:
    return str(os.getenv("REGULAR_DUE_ALERT_EMAIL") or settings.regular_auto_result_email or "ds1501@dae-seung.co.kr").strip()


def _history_url() -> str:
    override = str(os.getenv("REGULAR_DUE_HISTORY_URL") or "").strip()
    if re.match(r"^https?://[^/]+", override):
        return override.rstrip("/")

    origin = str(settings.web_public_origin or "").strip().rstrip("/")
    if re.match(r"^https?://[^/]+", origin):
        return f"{origin}/regular-due-history"

    host = str(os.getenv("WEB_SERVER_IP") or "172.17.39.121").strip()
    return f"https://{host}:{settings.web_port}/regular-due-history"

def _alert_hour() -> int:
    return max(0, min(_env_int("REGULAR_DUE_ALERT_HOUR", 12), 23))


def _alert_start_date() -> date:
    parsed = _parse_date(os.getenv("REGULAR_DUE_ALERT_START_DATE") or "2026-06-01")
    return parsed or date(2026, 6, 1)


def _scan_limit() -> int:
    return max(1, min(_env_int("REGULAR_DUE_ALERT_SCAN_LIMIT", 200), 200))


def _state_path() -> Path:
    return settings.erp_db_dir / "regular_due_monitor_state.json"


def _load_state() -> dict[str, Any]:
    path = _state_path()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
            return data if isinstance(data, dict) else {}
    except Exception:
        log.exception("regular due monitor state load failed")
    return {}


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _digits(value: Any) -> str:
    return re.sub(r"[^0-9]", "", str(value or ""))


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _compact(value: Any) -> str:
    return re.sub(r"\s+|\([^)]*\)|㈜|\(주\)|주식회사|유한회사|\(유\)", "", str(value or "").lower())


def _invoice_data(invoice: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(invoice, dict):
        return {}
    merged = dict(invoice)
    data = invoice.get("data")
    if isinstance(data, dict):
        merged.update(data)
    return merged


def _flatten_strings(value: Any, *, depth: int = 0) -> list[str]:
    if depth > 6:
        return []
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_flatten_strings(item, depth=depth + 1))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_flatten_strings(item, depth=depth + 1))
        return result
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return [text] if text else []
    return []


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    patterns = (
        r"(20\d{2})\D{0,4}(0?[1-9]|1[0-2])\D{0,4}([0-3]?\d)",
        r"\b(\d{2})(0[1-9]|1[0-2])([0-3]\d)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        year = int(match.group(1))
        if year < 100:
            year += 2000
        try:
            return date(year, int(match.group(2)), int(match.group(3)))
        except ValueError:
            continue
    digits = _digits(text)
    if len(digits) >= 8 and digits[:2] == "20":
        try:
            return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
        except ValueError:
            return None
    return None


def _invoice_issue_date(invoice: dict[str, Any]) -> date | None:
    data = _invoice_data(invoice)
    raw = invoice.get("raw") if isinstance(invoice.get("raw"), dict) else {}
    keys = ("invoice_date", "issue_date", "write_date", "작성일자", "발행일자", "tax_invoice_date")
    for source in (data, raw, invoice):
        if not isinstance(source, dict):
            continue
        for key in keys:
            parsed = _parse_date(source.get(key))
            if parsed:
                return parsed
    return _parse_date(data.get("pdf_path") or invoice.get("pdf_path") or "")


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _rule_issue_date(rule: DueRule, due_date: date) -> date:
    if rule.issue_kind == "last_day":
        return date(due_date.year, due_date.month, _last_day(due_date.year, due_date.month))
    day = max(1, min(rule.issue_day or 1, _last_day(due_date.year, due_date.month)))
    return date(due_date.year, due_date.month, day)


def _rule_receive_due_date(rule: DueRule, year: int, month: int) -> date | None:
    if rule.quarterly_months and month not in rule.quarterly_months:
        return None
    if rule.receive_due_day:
        day = max(1, min(rule.receive_due_day, _last_day(year, month)))
        return date(year, month, day)
    return _rule_issue_date(rule, date(year, month, 1))



def _due_rules_for_notify_date(reference_date: date) -> list[tuple[DueRule, date, date]]:
    due_date = reference_date - timedelta(days=1)
    result: list[tuple[DueRule, date, date]] = []
    for rule in REGULAR_DUE_RULES:
        receive_due_date = _rule_receive_due_date(rule, due_date.year, due_date.month)
        if receive_due_date == due_date:
            result.append((rule, _rule_issue_date(rule, due_date), receive_due_date))
    return result


def _due_rules_for_month(reference_date: date) -> list[tuple[DueRule, date, date]]:
    result: list[tuple[DueRule, date, date]] = []
    for rule in REGULAR_DUE_RULES:
        receive_due_date = _rule_receive_due_date(rule, reference_date.year, reference_date.month)
        if receive_due_date:
            result.append((rule, _rule_issue_date(rule, receive_due_date), receive_due_date))
    return result


def _trigger_rule_keys(reference_date: date) -> set[tuple[str, str, str]]:
    return {
        (rule.key, expected_date.isoformat(), receive_due_date.isoformat())
        for rule, expected_date, receive_due_date in _due_rules_for_notify_date(reference_date)
    }


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _due_rules_around(reference_date: date, *, past_months: int = 12, future_months: int = 12) -> list[tuple[DueRule, date, date]]:
    start_month = _add_months(date(reference_date.year, reference_date.month, 1), -past_months)
    end_month = _add_months(date(reference_date.year, reference_date.month, 1), future_months)
    result: list[tuple[DueRule, date, date]] = []
    cursor = start_month
    while cursor <= end_month:
        for rule in REGULAR_DUE_RULES:
            receive_due_date = _rule_receive_due_date(rule, cursor.year, cursor.month)
            if receive_due_date and receive_due_date + timedelta(days=1) >= _alert_start_date():
                result.append((rule, _rule_issue_date(rule, receive_due_date), receive_due_date))
        cursor = _add_months(cursor, 1)
    return sorted(result, key=lambda item: (item[2], item[0].vendor_name))


def _cycle_has_invoice(rule: DueRule, expected_date: date, invoices: list[dict[str, Any]]) -> bool:
    for invoice in invoices:
        if not _rule_matches_invoice(rule, invoice):
            continue
        issue_date = _invoice_issue_date(invoice)
        if _issue_date_ok(rule, issue_date, expected_date) or _same_period(issue_date, expected_date):
            return True
    return False


def _cycle_for_report(rule: DueRule, reference_date: date, invoices: list[dict[str, Any]]) -> tuple[DueRule, date, date] | None:
    cycles = [item for item in _due_rules_around(reference_date) if item[0].key == rule.key]
    if not cycles:
        return None

    alert_day_cycles = [item for item in cycles if item[2] + timedelta(days=1) == reference_date]
    if alert_day_cycles:
        return alert_day_cycles[-1]

    unresolved = [
        item
        for item in cycles
        if item[2] < reference_date and not _cycle_has_invoice(item[0], item[1], invoices)
    ]
    if unresolved:
        return unresolved[0]

    future_or_today = [item for item in cycles if item[2] >= reference_date]
    if future_or_today:
        return future_or_today[0]

    return cycles[-1]


def _due_rules_for_report(reference_date: date, invoices: list[dict[str, Any]]) -> list[tuple[DueRule, date, date]]:
    result: list[tuple[DueRule, date, date]] = []
    for rule in REGULAR_DUE_RULES:
        cycle = _cycle_for_report(rule, reference_date, invoices)
        if cycle:
            result.append(cycle)
    return sorted(result, key=lambda item: (item[2], item[0].vendor_name))

def _expected_label(rule: DueRule, expected_date: date, receive_due_date: date) -> str:
    if rule.issue_kind == "by_day":
        return f"{expected_date.year}-{expected_date.month:02d}-01~{expected_date.day:02d}"
    if receive_due_date != expected_date:
        return f"{expected_date.isoformat()} 발행 / {receive_due_date.isoformat()} 수신마감"
    return expected_date.isoformat()


def _invoice_text(invoice: dict[str, Any]) -> str:
    data = _invoice_data(invoice)
    raw = invoice.get("raw") if isinstance(invoice.get("raw"), dict) else {}
    return "\n".join(_flatten_strings({"invoice": invoice, "data": data, "raw": raw}))


def _pdf_supplier_name(invoice: dict[str, Any]) -> str:
    data = _invoice_data(invoice)
    pdf_name = Path(str(invoice.get("pdf_path") or data.get("pdf_path") or "")).stem
    if not pdf_name:
        return ""
    text = re.sub(r"^세금계산서\s*-\s*", "", pdf_name).strip()
    text = re.split(r"[_，,]\s*(?:\(?주\)?|주식회사)?\s*대승", text, maxsplit=1)[0].strip()
    text = re.sub(r"\((?!주\)|유\))[^)]*\)", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -_,")


def _history_rule(invoice: dict[str, Any]) -> DueRule | None:
    data = _invoice_data(invoice)
    candidates = [
        _pdf_supplier_name(invoice),
        Path(str(invoice.get("pdf_path") or data.get("pdf_path") or "")).name,
        data.get("supplier_name"),
        data.get("vendor_name"),
        invoice.get("vendor_name"),
        invoice.get("subject"),
        _invoice_item_text(invoice),
    ]
    compact = _compact("\n".join(_clean_text(candidate) for candidate in candidates if _clean_text(candidate)))
    if not compact:
        return None
    for rule in REGULAR_DUE_RULES:
        if any(_compact(alias) and _compact(alias) in compact for alias in rule.aliases):
            return rule
    return None


def _history_vendor_name(invoice: dict[str, Any]) -> str:
    rule = _history_rule(invoice)
    if rule:
        return rule.vendor_name
    data = _invoice_data(invoice)
    for candidate in (
        _pdf_supplier_name(invoice),
        data.get("supplier_name"),
        data.get("vendor_name"),
        invoice.get("vendor_name"),
    ):
        text = _clean_text(candidate)
        if text:
            return text
    return "미분류"


def _rule_matches_invoice(rule: DueRule, invoice: dict[str, Any]) -> bool:
    text = _invoice_text(invoice)
    compact = _compact(text)
    if rule.biz_no and _digits(rule.biz_no) in _digits(text):
        vendor_match = True
    else:
        vendor_match = any(_compact(alias) in compact for alias in rule.aliases)
    if not vendor_match:
        return False
    lower = text.lower()
    if rule.required_tokens and not any(token.lower() in lower for token in rule.required_tokens):
        return False
    if rule.excluded_tokens and any(token.lower() in lower for token in rule.excluded_tokens):
        return False
    return True


def _issue_date_ok(rule: DueRule, issue_date: date | None, expected_date: date) -> bool:
    if not issue_date or issue_date.year != expected_date.year or issue_date.month != expected_date.month:
        return False
    if rule.issue_kind == "by_day":
        return 1 <= issue_date.day <= expected_date.day
    return issue_date == expected_date


def _same_period(issue_date: date | None, expected_date: date) -> bool:
    return bool(issue_date and issue_date.year == expected_date.year and issue_date.month == expected_date.month)


def _amount(invoice: dict[str, Any]) -> str:
    data = _invoice_data(invoice)
    value = data.get("total_sum") or data.get("total_amount") or data.get("amount") or invoice.get("total_sum")
    try:
        number = int(str(value or "0").replace(",", "").strip() or "0")
        return f"{number:,}" if number else "-"
    except Exception:
        return str(value or "-")



def _invoice_received_text(invoice: dict[str, Any] | None) -> str:
    if not invoice:
        return "-"
    data = _invoice_data(invoice)
    received_at = _clean_text(invoice.get("received_at") or data.get("received_at") or "")
    if not received_at:
        return "-"
    parsed = _parse_date(received_at)
    return parsed.isoformat() if parsed else received_at[:16]


def _invoice_item_text(invoice: dict[str, Any]) -> str:
    data = _invoice_data(invoice)
    candidates = [
        data.get("item_name"),
        data.get("product_name"),
        data.get("summary"),
        data.get("description"),
        data.get("memo"),
    ]
    items = data.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                candidates.extend([item.get("name"), item.get("item_name"), item.get("raw_desc")])
    for candidate in candidates:
        text = _clean_text(candidate)
        if text:
            return text[:80]
    pdf_stem = Path(str(invoice.get("pdf_path") or data.get("pdf_path") or "")).stem
    return _clean_text(pdf_stem)[:80] or "-"


def _invoice_content(invoice: dict[str, Any] | None) -> str:
    if not invoice:
        return "-"
    return f"#{invoice.get('id') or '-'} / {_invoice_item_text(invoice)} / {_amount(invoice)}원"


def _days_text(reference_date: date, receive_due_date: date, status: str) -> str:
    delta = (receive_due_date - reference_date).days
    if status == "수신대기":
        if delta > 0:
            return f"{delta}일 남음"
        if delta == 0:
            return "오늘 마감"
    if status == "누락" and delta < 0:
        return f"{abs(delta)}일 지남"
    return "-"

def _load_regular_invoices() -> list[dict[str, Any]]:
    summaries = list_invoices(mode="regular", limit=_scan_limit())
    invoices: list[dict[str, Any]] = []
    for item in summaries:
        try:
            invoice = get_invoice(int(item.get("id") or 0))
        except Exception:
            invoice = None
        if invoice and str(invoice.get("invoice_type") or "").lower() == "regular":
            invoices.append(invoice)
    return invoices



def _evaluate_rule(
    rule: DueRule,
    expected_date: date,
    receive_due_date: date,
    reference_date: date,
    invoices: list[dict[str, Any]],
    trigger_keys: set[tuple[str, str, str]],
) -> dict[str, Any]:
    vendor_invoices = [invoice for invoice in invoices if _rule_matches_invoice(rule, invoice)]
    exact_matches = [invoice for invoice in vendor_invoices if _issue_date_ok(rule, _invoice_issue_date(invoice), expected_date)]
    period_mismatches = [
        invoice
        for invoice in vendor_invoices
        if not _issue_date_ok(rule, _invoice_issue_date(invoice), expected_date)
        and _same_period(_invoice_issue_date(invoice), expected_date)
    ]
    if exact_matches:
        status = "수신완료"
        severity = "ok"
        matched = exact_matches[0]
        note = rule.note or "-"
    elif period_mismatches:
        status = "일자확인"
        severity = "warning"
        matched = period_mismatches[0]
        note = f"약속일과 발행일자가 다릅니다. {rule.note}".strip()
    elif receive_due_date >= reference_date:
        status = "수신대기"
        severity = "pending"
        matched = None
        note = rule.note or "-"
    else:
        status = "누락"
        severity = "missing"
        matched = None
        note = rule.note or "-"
    actual_issue_date = _invoice_issue_date(matched) if matched else None
    trigger_key = (rule.key, expected_date.isoformat(), receive_due_date.isoformat())
    return {
        "key": rule.key,
        "vendor_name": rule.vendor_name,
        "frequency": rule.frequency,
        "expected_issue_date": expected_date.isoformat(),
        "receive_due_date": receive_due_date.isoformat(),
        "notify_date": (receive_due_date + timedelta(days=1)).isoformat(),
        "expected_label": _expected_label(rule, expected_date, receive_due_date),
        "status": status,
        "severity": severity,
        "days_text": _days_text(reference_date, receive_due_date, status),
        "actual_issue_date": actual_issue_date.isoformat() if actual_issue_date else "-",
        "actual_received_at": _invoice_received_text(matched),
        "content": _invoice_content(matched),
        "matched_invoice": _invoice_content(matched),
        "note": note,
        "is_trigger": trigger_key in trigger_keys,
    }


def build_regular_due_report(reference_date: str | date | datetime | None = None) -> dict[str, Any]:
    if reference_date:
        parsed_date = _parse_date(reference_date)
        if not parsed_date:
            raise ValueError(f"Invalid reference date: {reference_date}")
        today = parsed_date
    else:
        today = datetime.now().date()
    invoices = _load_regular_invoices()
    trigger_keys = _trigger_rule_keys(today)
    items = [
        _evaluate_rule(rule, expected_date, receive_due_date, today, invoices, trigger_keys)
        for rule, expected_date, receive_due_date in _due_rules_for_report(today, invoices)
    ]
    missing = sum(1 for item in items if item["severity"] == "missing")
    warning = sum(1 for item in items if item["severity"] == "warning")
    pending = sum(1 for item in items if item["severity"] == "pending")
    ok = sum(1 for item in items if item["severity"] == "ok")
    return {
        "enabled": _enabled(),
        "recipient": _recipient(),
        "alert_hour": _alert_hour(),
        "reference_date": today.isoformat(),
        "item_count": len(items),
        "trigger_count": sum(1 for item in items if item.get("is_trigger")),
        "missing_count": missing,
        "warning_count": warning,
        "pending_count": pending,
        "ok_count": ok,
        "items": items,
    }


def _plain_text(report: dict[str, Any]) -> str:
    alert_time = f"{int(report.get('alert_hour') or 0):02d}:00"
    lines = [
        "정기 세금계산서 수신 점검",
        f"기준일: {report['reference_date']} {alert_time}",
        (
            f"누락 {report['missing_count']} / 일자확인 {report['warning_count']} / "
            f"수신대기 {report['pending_count']} / 수신완료 {report['ok_count']}"
        ),
        f"수신이력: {_history_url()}",
        "",
    ]
    if not report["items"]:
        lines.append("- 점검 대상 없음")
    for item in report["items"]:
        lines.append(
            f"- [{item['status']}] {item['vendor_name']} / 발행예정 {item['expected_issue_date']} / "
            f"수신마감 {item['receive_due_date']} / {item['days_text']} / {item['content']}"
        )
    return "\n".join(lines)


def _html_report(report: dict[str, Any]) -> str:
    alert_time = f"{int(report.get('alert_hour') or 0):02d}:00"
    rows = []
    colors = {
        "missing": ("#fff1f2", "#b91c1c"),
        "warning": ("#fff7ed", "#c2410c"),
        "pending": ("#eff6ff", "#1d4ed8"),
        "ok": ("#ecfdf5", "#047857"),
    }
    td = "border:1px solid #d1d5db;padding:7px 8px;vertical-align:top;"
    td_center = td + "text-align:center;"
    td_nowrap = td + "text-align:center;white-space:nowrap;"
    for index, item in enumerate(report["items"], start=1):
        bg, fg = colors.get(item["severity"], ("#ffffff", "#111827"))
        rows.append(
            "<tr>"
            f"<td style=\"{td_center}width:42px;\">{index}</td>"
            f"<td style=\"{td_nowrap}min-width:92px;font-weight:700;\">{html.escape(item['vendor_name'])}</td>"
            f"<td style=\"{td_nowrap}min-width:78px;\">{html.escape(item['frequency'])}</td>"
            f"<td style=\"{td_nowrap}min-width:92px;\">{html.escape(item['expected_issue_date'])}</td>"
            f"<td style=\"{td_nowrap}min-width:92px;\">{html.escape(item['receive_due_date'])}</td>"
            f"<td style=\"{td_nowrap}min-width:86px;\">{html.escape(item['actual_issue_date'])}</td>"
            f"<td style=\"{td_nowrap}min-width:86px;\">{html.escape(item['actual_received_at'])}</td>"
            f"<td style=\"{td_center}background:{bg};color:{fg};font-weight:700;min-width:74px;\">{html.escape(item['status'])}</td>"
            f"<td style=\"{td_nowrap}min-width:72px;font-weight:700;\">{html.escape(item['days_text'])}</td>"
            f"<td style=\"{td}min-width:230px;\">{html.escape(item['content'])}</td>"
            f"<td style=\"{td}min-width:160px;\">{html.escape(item['note'])}</td>"
            "</tr>"
        )
    if not rows:
        rows.append(f"<tr><td colspan=\"11\" style=\"{td}text-align:center;\">점검 대상 없음</td></tr>")
    headline_color = "#b91c1c" if report["missing_count"] else "#c2410c" if report["warning_count"] else "#047857"
    legend = (
        '<span style="display:inline-block;margin-right:10px;"><b style="color:#1d4ed8;">수신대기</b>: 마감 전</span>'
        '<span style="display:inline-block;margin-right:10px;"><b style="color:#047857;">수신완료</b>: 수신 확인</span>'
        '<span style="display:inline-block;margin-right:10px;"><b style="color:#c2410c;">일자확인</b>: 발행일 상이</span>'
        '<span style="display:inline-block;margin-right:10px;"><b style="color:#b91c1c;">누락</b>: 마감 지남</span>'
    )
    th = "border:1px solid #d1d5db;padding:8px;text-align:center;white-space:nowrap;"
    return f'''<!doctype html>
<html>
<body style="font-family:Malgun Gothic,Arial,sans-serif;color:#111827;">
  <h2 style="margin:0 0 12px 0;">정기 세금계산서 수신 점검</h2>
  <p style="margin:0 0 8px 0;">기준일: <b>{html.escape(report['reference_date'])} {html.escape(alert_time)}</b></p>
  <p style="margin:0 0 8px 0;color:{headline_color};font-weight:700;">
    누락 {report['missing_count']}건 / 일자확인 {report['warning_count']}건 / 수신대기 {report['pending_count']}건 / 수신완료 {report['ok_count']}건
  </p>
  <p style="margin:0 0 10px 0;color:#4b5563;font-size:12px;">{legend}</p>
  <p style="margin:0 0 14px 0;">
    <a href="{html.escape(_history_url(), quote=True)}" style="display:inline-block;background:#0f766e;color:#ffffff;text-decoration:none;padding:8px 12px;border-radius:4px;font-weight:700;font-size:12px;">전체 세금계산서 수신이력 조회</a>
  </p>
  <table cellspacing="0" cellpadding="0" style="border-collapse:collapse;width:100%;font-size:13px;line-height:1.35;">
    <thead>
      <tr style="background:#f3f4f6;">
        <th style="{th}">순번</th>
        <th style="{th}">업체명</th>
        <th style="{th}">주기</th>
        <th style="{th}">발행예정일</th>
        <th style="{th}">수신마감일</th>
        <th style="{th}">발행일</th>
        <th style="{th}">수신일</th>
        <th style="{th}">상태</th>
        <th style="{th}">남은기간</th>
        <th style="{th}">내용</th>
        <th style="{th}">비고</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>'''

def _sender() -> str:
    from_addr = settings.regular_auto_result_from or settings.password_reset_from
    if "<" in from_addr and ">" in from_addr:
        return from_addr
    from_name = str(settings.regular_auto_result_from_name or "회계처리프로그램").strip()
    return formataddr((from_name, from_addr)) if from_name else from_addr


def _send_html_mail(to_addr: str, subject: str, plain: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = _sender()
    msg["To"] = to_addr
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.attach(MIMEText(plain, "plain", _charset="utf-8"))
    msg.attach(MIMEText(html_body, "html", _charset="utf-8"))
    with smtplib.SMTP(settings.regular_auto_result_smtp_server, settings.regular_auto_result_smtp_port, timeout=10) as smtp:
        smtp.ehlo()
        if smtp.has_extn("STARTTLS"):
            smtp.starttls()
            smtp.ehlo()
        if settings.regular_auto_result_smtp_user and settings.regular_auto_result_smtp_pw:
            smtp.login(settings.regular_auto_result_smtp_user, settings.regular_auto_result_smtp_pw)
        smtp.send_message(msg)



def send_regular_due_report(reference_date: str | date | datetime | None = None, *, force: bool = False) -> dict[str, Any]:
    report = build_regular_due_report(reference_date)
    report_date = _parse_date(report.get("reference_date")) or datetime.now().date()
    if not _enabled():
        return {**report, "sent": False, "skipped": True, "reason": "disabled"}
    if report_date < _alert_start_date() and not force:
        return {**report, "sent": False, "skipped": True, "reason": "before_start_date"}
    if not report["items"] and not force:
        return {**report, "sent": False, "skipped": True, "reason": "no_due_items"}
    recipient = _recipient()
    if not recipient:
        return {**report, "sent": False, "skipped": True, "reason": "missing_recipient"}
    state = _load_state()
    key_items = [
        f"{item['key']}@{item['receive_due_date']}"
        for item in report["items"]
        if item.get("is_trigger")
    ] or [f"{item['key']}@{item['receive_due_date']}" for item in report["items"]]
    key = f"{report['reference_date']}:{','.join(key_items)}"
    sent = state.get("sent") if isinstance(state.get("sent"), dict) else {}
    if sent.get(key) and not force:
        return {**report, "sent": False, "skipped": True, "reason": "already_sent", "state_key": key}
    prefix = "[누락]" if report["missing_count"] else "[확인]" if report["warning_count"] else "[정상]"
    subject = (
        f"{prefix} 정기 세금계산서 수신 점검 "
        f"- 누락 {report['missing_count']} / 확인 {report['warning_count']} / 대기 {report['pending_count']} / 완료 {report['ok_count']}"
    )
    try:
        _send_html_mail(recipient, subject, _plain_text(report), _html_report(report))
    except Exception as exc:
        log.exception("regular due alert email failed: %s", exc)
        return {**report, "sent": False, "error": str(exc)}
    sent[key] = datetime.now().isoformat(timespec="seconds")
    state["sent"] = sent
    _save_state(state)
    return {**report, "sent": True, "to": recipient, "state_key": key}


def regular_due_history(*, limit: int = 500) -> dict[str, Any]:
    limit = max(1, min(int(limit or 500), 1000))
    summaries = list_invoices(mode="regular", limit=limit)
    items: list[dict[str, Any]] = []
    for summary in summaries:
        try:
            invoice = get_invoice(int(summary.get("id") or 0))
        except Exception:
            invoice = None
        if not invoice or str(invoice.get("invoice_type") or "").lower() != "regular":
            continue
        data = _invoice_data(invoice)
        issue_date = _invoice_issue_date(invoice)
        pdf_name = Path(str(invoice.get("pdf_path") or data.get("pdf_path") or "")).name
        items.append(
            {
                "invoice_id": invoice.get("id") or summary.get("id"),
                "vendor_name": _history_vendor_name(invoice),
                "issue_date": issue_date.isoformat() if issue_date else "-",
                "received_at": _invoice_received_text(invoice),
                "amount": _amount(invoice),
                "content": _invoice_item_text(invoice),
                "file_name": pdf_name or "-",
            }
        )
    return {
        "item_count": len(items),
        "items": items,
        "history_url": _history_url(),
    }


def regular_due_status(reference_date: str | date | datetime | None = None) -> dict[str, Any]:
    report = build_regular_due_report(reference_date)
    state = _load_state()
    report["state_path"] = str(_state_path())
    report["sent_keys"] = sorted((state.get("sent") or {}).keys())[-20:] if isinstance(state.get("sent"), dict) else []
    return report


def start_regular_due_scheduler() -> None:
    global _scheduler_started
    if not _enabled():
        return
    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True

    def _loop() -> None:
        interval = max(30, _env_int("REGULAR_DUE_ALERT_INTERVAL_SECONDS", 60))
        while True:
            try:
                now = datetime.now()
                if now.hour >= _alert_hour():
                    send_regular_due_report(now.date())
            except Exception:
                log.exception("regular due scheduler failed")
            time.sleep(interval)

    threading.Thread(target=_loop, name="regular-due-monitor", daemon=True).start()