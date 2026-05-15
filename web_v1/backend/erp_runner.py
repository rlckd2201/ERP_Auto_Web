from __future__ import annotations

import importlib.util
import logging
import re
import sys
import types
from pathlib import Path
from typing import Any, Callable

from .config import PROJECT_ROOT, settings


FACTORY_MAP = {
    "125-81-05619": "D1공장",
    "403-85-07607": "D2공장",
    "125-81-32697": "P1공장",
    "403-85-15640": "P2공장",
    "403-85-23311": "D3공장",
    "844-85-00770": "P3공장",
    "125-81-51622": "일강1공장",
    "403-85-20895": "일강2공장",
    "125-81-54876": "제이엠",
    "118-85-07029": "P4공장",
    "421-86-02723": "더원",
}
VALID_SITE_NAMES = set(FACTORY_MAP.values())

CORP_MAP = {
    "D1공장": "㈜대승",
    "D2공장": "㈜대승",
    "D3공장": "㈜대승",
    "P1공장": "대승정밀㈜",
    "P2공장": "대승정밀㈜",
    "P3공장": "대승정밀㈜",
    "P4공장": "대승정밀㈜",
    "일강1공장": "㈜일강",
    "일강2공장": "㈜일강",
    "더원": "㈜더원",
    "제이엠": "㈜제이엠",
}


Progress = Callable[[str], None]


def _to_int(value: Any) -> int:
    try:
        if isinstance(value, (int, float)):
            return int(value)
        text = re.sub(r"[^0-9-]", "", str(value or ""))
        return int(text) if text not in {"", "-"} else 0
    except Exception:
        return 0


def _clean_text(value: Any, fallback: str = "") -> str:
    return re.sub(r"\s+", " ", str(value or fallback).strip())


def _site_from_biz_no(value: Any) -> str:
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    if len(digits) == 10:
        return FACTORY_MAP.get(f"{digits[:3]}-{digits[3:5]}-{digits[5:]}", "")
    return ""


def _site_from_known_text(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    for site in VALID_SITE_NAMES:
        if site in text:
            return site
    match = re.search(r"\b(D[1-3]공장|P[1-4]공장)\b", text, re.IGNORECASE)
    if match:
        return match.group(1).upper().replace("공장", "공장")
    return ""


def _resolve_site(data: dict[str, Any], raw: dict[str, Any], invoice: dict[str, Any], pdf_path: str) -> str:
    explicit_site_candidates = [
        data.get("site_name"),
        invoice.get("site_name"),
        raw.get("site_name"),
    ]
    for candidate in explicit_site_candidates:
        site = _site_from_known_text(candidate)
        if site:
            return site

    biz_candidates = [
        data.get("buyer_biz_no"),
        data.get("buyer_business_no"),
        data.get("receiver_biz_no"),
        data.get("recipient_biz_no"),
        data.get("matched_biz_no"),
        raw.get("buyer_biz_no"),
        raw.get("buyer_business_no"),
        raw.get("matched_biz_no"),
        invoice.get("buyer_biz_no"),
    ]
    for candidate in biz_candidates:
        site = _site_from_biz_no(candidate)
        if site:
            return site

    text_candidates = [
        data.get("buyer_site"),
        data.get("matched_biz_name"),
        raw.get("buyer_site"),
        raw.get("matched_biz_name"),
        Path(pdf_path or "").name,
        invoice.get("subject"),
    ]
    for candidate in text_candidates:
        site = _site_from_known_text(candidate)
        if site:
            return site
    return ""


def _purchase_analysis_ready(data: dict[str, Any], raw: dict[str, Any]) -> bool:
    items = data.get("items") or raw.get("items") or []
    return bool(data.get("purchase_analysis_ready") or raw.get("purchase_analysis_ready")) and isinstance(items, list) and bool(items)


def _purchase_erp_ready(data: dict[str, Any], raw: dict[str, Any]) -> bool:
    return _purchase_analysis_ready(data, raw)


def validate_purchase_invoice_for_erp(invoice: dict[str, Any]) -> None:
    raw = dict(invoice.get("raw") or {})
    data = dict(raw)
    if isinstance(raw.get("data"), dict):
        data.update(raw.get("data") or {})
    if isinstance(invoice.get("data"), dict):
        data.update(invoice.get("data") or {})
    pdf_path = str(invoice.get("pdf_path") or data.get("pdf_path") or raw.get("pdf_path") or "")

    if not _purchase_analysis_ready(data, raw):
        raise RuntimeError(
            "구매 ERP 입력은 세금계산서만으로 실행할 수 없습니다. "
            "견적서 첨부 및 분석 완료 데이터가 필요합니다."
        )
    if not _resolve_site(data, raw, invoice, pdf_path):
        raise RuntimeError(
            "구매 ERP 입력 회계단위를 특정하지 못했습니다. "
            "세금계산서의 매입자 사업자번호 또는 D/P/일강 사업장 정보가 필요합니다."
        )
    if _to_int(data.get("target_supply") or data.get("total_supply") or raw.get("target_supply")) <= 0:
        raise RuntimeError("구매 ERP 입력 공급가액이 0원입니다. 견적서 분석 결과를 먼저 확인해야 합니다.")


def _extract_invoice_date(data: dict[str, Any], pdf_path: str = "") -> str:
    candidates = [
        data.get("invoice_date"),
        data.get("issue_date"),
        data.get("write_date"),
        data.get("작성일자"),
        data.get("date"),
    ]
    for value in candidates:
        digits = re.sub(r"[^0-9]", "", str(value or ""))
        if len(digits) >= 8:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    filename = Path(pdf_path or "").name
    filename_patterns = [
        r"(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?([0-3]\d)",
        r"(20\d{2})\s*\ub144\s*(0?[1-9]|1[0-2])\s*\uc6d4\s*([0-3]?\d)\s*\uc77c",
    ]
    for pattern in filename_patterns:
        match = re.search(pattern, filename)
        if match:
            return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    pdf_text = _extract_pdf_text_for_date(pdf_path)
    if pdf_text:
        return _extract_invoice_date_from_text(pdf_text)
    return ""


def _extract_pdf_text_for_date(pdf_path: str = "") -> str:
    path = Path(pdf_path or "")
    if not path.exists() or not path.is_file():
        return ""
    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            return text
    except Exception as exc:
        logging.warning("Regular tax invoice date pdfplumber fallback failed: %s", exc)
    try:
        import fitz

        with fitz.open(str(path)) as doc:
            return "\n".join(page.get_text() or "" for page in doc)
    except Exception as exc:
        logging.warning("Regular tax invoice date pymupdf fallback failed: %s", exc)
    return ""


def _extract_invoice_date_from_text(text: str) -> str:
    def _format(year: str, month: str, day: str) -> str:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    label = (
        r"(?:"
        r"\uc791\s*\uc131\s*\uc77c\s*\uc790|"
        r"\ubc1c\s*\ud589\s*\uc77c\s*\uc790|"
        r"\uacf5\s*\uae09\s*\uc77c\s*\uc790"
        r")"
    )
    labeled_patterns = [
        label + r"[\s\S]{0,220}?(20\d{2})\D{0,8}(0?[1-9]|1[0-2])\D{0,8}([0-3]?\d)",
        label + r"[\s\S]{0,220}?(20\d{2})(0[1-9]|1[0-2])([0-3]\d)",
    ]
    for pattern in labeled_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _format(match.group(1), match.group(2), match.group(3))

    generic_patterns = [
        r"\b(20\d{2})\s+(0?[1-9]|1[0-2])\s+([0-3]?\d)\b",
        r"\b(20\d{2})[-./](0?[1-9]|1[0-2])[-./]([0-3]?\d)\b",
        r"\b(20\d{2})(0[1-9]|1[0-2])([0-3]\d)\b",
    ]
    for pattern in generic_patterns:
        match = re.search(pattern, text)
        if match:
            return _format(match.group(1), match.group(2), match.group(3))
    return ""


def _guess_account(item_name: str, vendor_name: str = "") -> str:
    text = f"{item_name} {vendor_name}".lower()
    compact = re.sub(r"\s+", "", f"{item_name}{vendor_name}")
    if "동양정보통신" in compact or "대신아이씨티" in compact:
        return "지급수수료"
    if any(key in text for key in ["kt", "케이티", "통신", "vpn", "sdwan", "오토에버", "autoever", "704100", "w001"]):
        return "통신비"
    if any(
        key.lower() in text
        for key in [
            "nac",
            "dlp",
            "watching-on",
            "watchingon",
            "acronis",
            "그룹웨어",
            "다우오피스",
            "k-system",
            "ksystem",
            "helpu",
            "원격지원",
            "자산관리",
            "acrobat",
            "adobe",
            "cloudoc",
            "문서중앙화",
        ]
    ):
        return "지급수수료"
    return "지급수수료"


def _regular_account_from_item(item: dict[str, Any], item_name: str, vendor_name: str) -> str:
    guessed = _guess_account(item_name, vendor_name)
    account = _clean_text(item.get("account"))
    manual = bool(
        item.get("account_manual")
        or item.get("manual_account")
        or str(item.get("account_source") or "").strip().lower() == "manual"
    )
    allowed = {"지급수수료", "통신비", "소모품비", "컴퓨터소프트웨어", "집기비품"}
    if manual and account in allowed:
        return account
    return guessed


def _regular_period_label(data: dict[str, Any]) -> str:
    pdf_name = Path(str(data.get("pdf_path") or "")).name
    match = re.search(r"_(\d{4}년\s*\d{1,2}월(?:\s*\d차)?|\d{4}년\s*\d{1,2}~\d{1,2}월\s*\d차)(?:_\d+)?\.pdf$", pdf_name)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    digits = re.sub(r"[^0-9]", "", str(data.get("invoice_date") or data.get("issue_date") or ""))
    if len(digits) >= 6:
        return f"{digits[:4]}년 {digits[4:6]}월"
    return "미확인"


def _regular_month_text(period_label: str) -> str:
    match = re.search(r"(\d{1,2})월", str(period_label or ""))
    if match:
        return f"{int(match.group(1))}월"
    return "해당월"


def _regular_year_month_text(period_label: str) -> str:
    match = re.search(r"(\d{4})년\s*(\d{1,2})월", str(period_label or ""))
    if match:
        return f"{match.group(1)}년 {int(match.group(2))}월"
    return str(period_label or "").strip() or "해당월"


def _regular_round_text(period_label: str) -> str:
    match = re.search(r"(\d차)", str(period_label or ""))
    return match.group(1) if match else ""


def _regular_vendor_display(vendor: Any) -> str:
    raw = str(vendor or "").strip()
    compact = re.sub(r"\s+", "", raw.lower())
    rules = [
        ("다우", "다우기술"),
        ("에티버스", "에티버스"),
        ("이테크", "이테크시스템"),
        ("시큐어포인트", "시큐어포인트"),
        ("피플러스", "피플러스"),
        ("헬프유", "헬프유"),
        ("유비플러스", "유비플러스"),
        ("adobe", "Adobe"),
        ("어도비", "Adobe"),
        ("케이티", "KT"),
        ("kt", "KT"),
        ("오토에버", "현대오토에버시스템즈"),
        ("비엔아이", "비엔아이"),
    ]
    for key, label in rules:
        if key in compact:
            return label
    return re.sub(r"\(주\)|㈜|\(유\)|유한회사|주식회사", "", raw).strip() or "업체명"


def _site_short_name(site: str) -> str:
    site_short = site.split("-")[-1].strip() if "-" in site else site
    compact = site.replace(" ", "")
    if "제1공장" in compact:
        return "D1공장"
    if "제2공장" in compact:
        return "D2공장"
    if "제5공장" in compact:
        return "D3공장"
    for key in ("P1", "P2", "P3", "P4"):
        if key in compact:
            return f"{key}공장"
    return site_short


def _summary(site: str, vendor: str, item: dict[str, Any], supply: int, qty: int, *, account: str = "", data: dict[str, Any] | None = None) -> str:
    data = data or {}
    name = _clean_text(item.get("name") or item.get("item_name") or item.get("raw_desc"), "정기 서비스")
    vendor_display = _regular_vendor_display(vendor)
    period = _regular_period_label(data)
    month = _regular_month_text(period)
    year_month = _regular_year_month_text(period)
    text = f"{name} {vendor_display}".lower()

    if ("동양정보통신" in text or "대신아이씨티" in text) and "보수료" in text and supply == 250000:
        return f"{_site_short_name(site)} {year_month.replace(' 0', ' ')} 통합유지보수료 - {vendor_display}"
    if "다우오피스" in text or "그룹웨어" in text or "daou" in text:
        return f"{year_month} 다우오피스 월 사용료 - {vendor_display}"
    if "watching-on" in text or "watchingon" in text or "watching" in text:
        return f"{month}분 Watching-On 모니터링 서비스 사용료 - {vendor_display}"
    if "acronis" in text:
        return f"{month}분 Acronis Cloud 사용료 - {vendor_display}"
    if "k-system" in text or "ksystem" in text:
        return f"K-System 유지보수 {month}분 - {vendor_display}"
    if "nac" in text or "genian" in text:
        return f"NAC 유지보수 {month} - {vendor_display}"
    if "dlp" in text or "gradius" in text:
        return f"GRADIUS DLP 연간 유지보수 {_regular_round_text(period)} - {vendor_display}".strip()
    if "helpu" in text or "원격지원" in text:
        return f"HelpU 원격지원 프로그램 구독({supply:,} - 2Y) - {vendor_display}"
    if "자산관리" in text:
        return f"자산관리 프로그램 구독(전산)({supply:,} - {qty}User) - {vendor_display}"
    if "acrobat" in text:
        return f"Acrobat Pro 구독(영업,인사총무,기획,전산)({supply:,} - {qty}EA) - {vendor_display}"
    if "cloudoc" in text or "문서중앙화" in text:
        return f"문서중앙화(Cloudoc) 라이선스 {qty}user 구매 - {vendor_display}"
    if "vpn" in text or "sdwan" in text or "오토에버" in text or "autoever" in text:
        return f"{month}분 현대자동차VPN사용료(2007010097) - {vendor_display}"
    if account == "통신비" or "kt" in text or "케이티" in text:
        if "일강" in site:
            return f"{month}분 인터넷 전용선비, 보안시스템 시큐어넷(일강-W0011501)-(주)케이티"
        if "P1" in site:
            return f"{month}분 P3공장 인터넷 전용선비 (704100003954) - 케이티"
        if "P4" in site:
            return f"{month}분 인터넷 전용선비, biz managed 보안 ( 704100003983 ) - 케이티"
        return f"{month}분 인터넷 전용선비, 보안시스템 시큐어넷-(주)케이티"
    return f"{year_month} {name} - {vendor_display}"


def _purchase_account(value: Any) -> str:
    text = _clean_text(value)
    aliases = {
        "전산비품": "집기비품",
        "비품": "집기비품",
        "소프트웨어": "컴퓨터소프트웨어",
        "컴퓨터SW": "컴퓨터소프트웨어",
        "소모품": "소모품비",
    }
    account = aliases.get(text, text)
    return account if account in {"집기비품", "컴퓨터소프트웨어", "소모품비"} else "소모품비"


def _purchase_summary_name(value: Any) -> str:
    text = _clean_text(value, "구매품")
    text = text.replace("터치 모니터", "터치모니터")
    text = text.replace("모니터 암", "모니터암")
    return text


def _purchase_summary_label(items: list[dict[str, Any]]) -> tuple[str, int]:
    cleaned = [item for item in items if isinstance(item, dict)]
    if not cleaned:
        return "구매품", 1

    labels: list[str] = []
    seen_names: set[str] = set()
    supply_items: list[tuple[int, dict[str, Any]]] = []

    for index, item in enumerate(cleaned):
        name = _purchase_summary_name(item.get("name") or item.get("item_name"))
        account = _purchase_account(item.get("account"))
        if account == "소모품비":
            supply_items.append((index, item))
            continue
        if name:
            if name in seen_names:
                continue
            seen_names.add(name)
            labels.append(name)

    if supply_items:
        representative = max(
            (item for _, item in supply_items),
            key=lambda item: (
                _to_int(item.get("inc_vat") or item.get("total") or item.get("amount")),
                _to_int(item.get("supply") or item.get("supply_amount")),
            ),
        )
        supply_label = _purchase_summary_name(representative.get("name") or representative.get("item_name"))
        if len(supply_items) > 1:
            supply_label = f"{supply_label} 외 {len(supply_items) - 1}건"
        if supply_label:
            labels.append(supply_label)

    if not labels:
        labels = ["구매품"]
    qty = sum(max(1, _to_int(item.get("qty") or item.get("quantity") or 1)) for item in cleaned) or 1
    return ", ".join(labels), qty


def build_purchase_erp_payload(invoice: dict[str, Any]) -> dict[str, Any]:
    raw = dict(invoice.get("raw") or {})
    data = dict(raw)
    if isinstance(raw.get("data"), dict):
        data.update(raw.get("data") or {})
    data.update({key: value for key, value in invoice.items() if key not in {"raw", "data"}})
    if isinstance(invoice.get("data"), dict):
        data.update(invoice.get("data") or {})

    pdf_path = str(invoice.get("pdf_path") or data.get("pdf_path") or raw.get("pdf_path") or "")
    vendor = _clean_text(
        data.get("vendor_name")
        or data.get("supplier_name")
        or invoice.get("vendor_name")
        or invoice.get("subject"),
        "매입처",
    )
    vendor = re.sub(r"\(주\)|㈜|\(유\)|유한회사|주식회사", "", vendor).strip() or "매입처"
    validate_purchase_invoice_for_erp(invoice)
    buyer_biz_no = data.get("buyer_biz_no") or data.get("buyer_business_no") or raw.get("buyer_biz_no")
    site = _resolve_site(data, raw, invoice, pdf_path)
    invoice_date = _extract_invoice_date(data, pdf_path)
    if not invoice_date:
        raise RuntimeError("세금계산서 작성일자를 찾지 못해 ERP 입력을 중단했습니다.")

    total_tax = _to_int(data.get("total_tax") or data.get("tax") or raw.get("total_tax"))
    total_sum = _to_int(data.get("total_sum") or data.get("total_amount") or invoice.get("total_sum"))
    target_supply = _to_int(data.get("target_supply") or data.get("total_supply") or raw.get("target_supply"))
    if not target_supply and total_sum:
        target_supply = max(0, total_sum - total_tax)

    source_items = data.get("items") or raw.get("items") or []
    if not isinstance(source_items, list):
        source_items = []
    if not source_items:
        source_items = [
            {
                "name": data.get("item_name") or data.get("item") or invoice.get("subject") or "구매품",
                "qty": 1,
                "inc_vat": total_sum,
            }
        ]

    items: list[dict[str, Any]] = []
    items_inc_vat = sum(
        _to_int(item.get("inc_vat") or item.get("amount") or item.get("total"))
        for item in source_items
        if isinstance(item, dict)
    )
    supply_remainder = target_supply
    max_item_index = 0
    max_inc_vat = -1
    for index, source in enumerate(source_items):
        item = dict(source or {})
        name = _clean_text(item.get("name") or item.get("item_name"), "구매품")
        qty = max(1, _to_int(item.get("qty") or item.get("quantity") or 1))
        inc_vat = _to_int(item.get("inc_vat") or item.get("total") or item.get("amount"))
        supply = _to_int(item.get("supply") or item.get("supply_amount"))
        if not supply and target_supply and items_inc_vat:
            supply = int(target_supply * (inc_vat / items_inc_vat))
        if not supply and inc_vat:
            supply = round(inc_vat / 1.1)
        account = _purchase_account(item.get("account"))
        is_asset = bool(item.get("is_a")) if "is_a" in item else account != "소모품비"
        if not is_asset:
            account = "소모품비"
        normalized = {
            "name": name,
            "qty": qty,
            "inc_vat": inc_vat,
            "supply": supply,
            "account": account,
            "is_a": is_asset,
            "dept": _clean_text(item.get("dept")),
            "raw_desc": item.get("raw_desc") or "",
        }
        if inc_vat > max_inc_vat:
            max_inc_vat = inc_vat
            max_item_index = index
        supply_remainder -= supply
        items.append(normalized)

    if items and supply_remainder:
        items[max_item_index]["supply"] = _to_int(items[max_item_index].get("supply")) + supply_remainder
    if not target_supply:
        target_supply = sum(_to_int(item.get("supply")) for item in items)
    if not total_sum:
        total_sum = target_supply + total_tax

    rows: list[str] = []
    asset_items = [item for item in items if item.get("is_a")]
    supply_items = [item for item in items if not item.get("is_a")]

    for item in asset_items:
        dept = _clean_text(item.get("dept"))
        if not dept:
            raise RuntimeError(f"구매 품목 [{item.get('name')}]은 {item.get('account')} 계정이라 부서 지정 후 ERP 입력해야 합니다.")
        supply = _to_int(item.get("supply"))
        qty = max(1, _to_int(item.get("qty") or 1))
        rows.append(f"{item['account']}\t\t{supply}\t0\t{site} {item['name']}({dept})({supply:,} - {qty}EA) - {vendor}")

    if supply_items:
        representative = max(supply_items, key=lambda item: _to_int(item.get("inc_vat")))
        label = representative.get("name") or "구매품"
        if len(supply_items) > 1:
            label = f"{label} 외 {len(supply_items) - 1}건"
        qty = sum(max(1, _to_int(item.get("qty") or 1)) for item in supply_items)
        supply = sum(_to_int(item.get("supply")) for item in supply_items)
        rows.append(f"소모품비\t\t{supply}\t0\t{site} {label}({supply:,} - {qty}EA) - {vendor}")

    summary_label, total_qty = _purchase_summary_label(items)
    slip_summary = f"{site} {summary_label}({target_supply:,} - {total_qty}EA) - {vendor}"
    rows.append(f"부가세대급금\t\t{total_tax}\t0\tV.A.T - {slip_summary}")
    rows.append(f"가지급금(업체)\t\t0\t{total_sum}\t{slip_summary}")

    data_for_erp = {
        "pdf_path": pdf_path,
        "site_name": site,
        "vendor_name": vendor,
        "vendor_biz_no": vendor_biz_no or "",
        "supplier_biz_no": vendor_biz_no or "",
        "buyer_biz_no": buyer_biz_no or "",
        "invoice_date": invoice_date,
        "target_supply": target_supply,
        "total_tax": total_tax,
        "total_sum": total_sum,
        "items": items,
        "erp_row_count": len(rows),
        "erp_clipboard_rows": rows,
    }
    return {"data": data_for_erp, "rows": rows}


def build_regular_erp_payload(invoice: dict[str, Any]) -> dict[str, Any]:
    raw = dict(invoice.get("raw") or {})
    data = dict(raw)
    if isinstance(raw.get("data"), dict):
        data.update(raw.get("data") or {})
    data.update({key: value for key, value in invoice.items() if key not in {"raw", "data"}})
    if isinstance(invoice.get("data"), dict):
        data.update(invoice.get("data") or {})

    pdf_path = str(invoice.get("pdf_path") or data.get("pdf_path") or raw.get("pdf_path") or "")
    vendor = _clean_text(
        data.get("vendor_name")
        or data.get("supplier_name")
        or invoice.get("vendor_name")
        or invoice.get("subject"),
        "매입처",
    )
    buyer_biz_no = data.get("buyer_biz_no") or data.get("buyer_business_no") or raw.get("buyer_biz_no")
    vendor_biz_no = (
        data.get("vendor_biz_no")
        or data.get("supplier_biz_no")
        or data.get("supplier_business_no")
        or data.get("supplier_business_number")
        or raw.get("vendor_biz_no")
        or raw.get("supplier_biz_no")
        or raw.get("supplier_business_no")
    )
    site = _resolve_site(data, raw, invoice, pdf_path) or "사업장미확인"
    invoice_date = _extract_invoice_date(data, pdf_path)
    if not invoice_date:
        raise RuntimeError("세금계산서 작성일자를 찾지 못해 ERP 입력을 중단했습니다.")

    total_tax = _to_int(data.get("total_tax") or data.get("tax") or raw.get("total_tax"))
    total_sum = _to_int(data.get("total_sum") or data.get("total_amount") or invoice.get("total_sum"))
    target_supply = _to_int(data.get("target_supply") or data.get("total_supply") or raw.get("target_supply"))
    if not target_supply and total_sum:
        target_supply = max(0, total_sum - total_tax)

    source_items = data.get("items") or raw.get("items") or []
    if not isinstance(source_items, list):
        source_items = []
    if not source_items:
        source_items = [
            {
                "name": data.get("item_name") or data.get("item") or invoice.get("subject") or "정기 서비스",
                "qty": 1,
                "inc_vat": total_sum,
            }
        ]

    items: list[dict[str, Any]] = []
    items_inc_vat = sum(
        _to_int(item.get("inc_vat") or item.get("amount") or item.get("total"))
        for item in source_items
        if isinstance(item, dict)
    )
    supply_remainder = target_supply
    max_item_index = 0
    max_inc_vat = -1
    for source in source_items:
        if not isinstance(source, dict):
            continue
        item = dict(source or {})
        name = _clean_text(item.get("name") or item.get("item_name"), "정기 서비스")
        qty = max(1, _to_int(item.get("qty") or item.get("quantity") or 1))
        inc_vat = _to_int(item.get("inc_vat") or item.get("total") or item.get("amount"))
        supply = _to_int(item.get("supply") or item.get("supply_amount"))
        if not supply and target_supply and items_inc_vat:
            supply = int(target_supply * (inc_vat / items_inc_vat))
        if not supply and inc_vat:
            supply = round(inc_vat / 1.1)
        if not supply and len(source_items) == 1:
            supply = target_supply
        if inc_vat > max_inc_vat:
            max_inc_vat = inc_vat
            max_item_index = len(items)
        supply_remainder -= supply
        items.append(
            {
                "name": name,
                "qty": qty,
                "inc_vat": inc_vat,
                "supply": supply,
                "account": _regular_account_from_item(item, name, vendor),
                "account_manual": bool(item.get("account_manual") or item.get("manual_account")),
            }
        )

    if items and supply_remainder:
        items[max_item_index]["supply"] = _to_int(items[max_item_index].get("supply")) + supply_remainder
    if not target_supply:
        target_supply = sum(_to_int(item.get("supply")) for item in items)
    if not total_sum:
        total_sum = target_supply + total_tax

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(str(item["account"]), []).append(item)

    rows: list[str] = []
    for account, group in grouped.items():
        supply = sum(_to_int(item.get("supply")) for item in group)
        qty = sum(max(1, _to_int(item.get("qty") or 1)) for item in group)
        rows.append(f"{account}\t\t{supply}\t0\t{_summary(site, vendor, group[0], supply, qty, account=account, data=data)}")

    first_item = items[0] if items else {"name": "정기 서비스", "qty": 1}
    first_account = str(first_item.get("account") or "지급수수료")
    slip_summary = _summary(
        site,
        vendor,
        first_item,
        target_supply,
        sum(_to_int(item.get("qty") or 1) for item in items) or 1,
        account=first_account,
        data=data,
    )
    rows.append(f"부가세대급금\t\t{total_tax}\t0\tV.A.T - {slip_summary}")
    rows.append(f"미지급금(원화)\t\t0\t{total_sum}\t{slip_summary}")

    data_for_erp = {
        "pdf_path": pdf_path,
        "site_name": site,
        "vendor_name": vendor,
        "vendor_biz_no": vendor_biz_no or "",
        "supplier_biz_no": vendor_biz_no or "",
        "buyer_biz_no": buyer_biz_no or "",
        "invoice_date": invoice_date,
        "target_supply": target_supply,
        "total_tax": total_tax,
        "total_sum": total_sum,
        "items": items,
        "erp_row_count": len(rows),
        "erp_clipboard_rows": rows,
    }
    return {"data": data_for_erp, "rows": rows}


class _ProgressHandler(logging.Handler):
    def __init__(self, progress: Progress | None) -> None:
        super().__init__()
        self.progress = progress

    def emit(self, record: logging.LogRecord) -> None:
        if self.progress:
            self.progress(self.format(record))


class _MainAppShim:
    def __init__(self, data: dict[str, Any], print_choice: dict[str, Any]) -> None:
        self.data = data
        self.tax_path = str(data.get("pdf_path") or "")
        self.print_choice_override = print_choice
        self.batch_erp_pdf_path = str(print_choice.get("save_path") or "")
        self.last_erp_print_output = ""

    def _extract_issue_date_from_pdf(self, pdf_path: str) -> str:
        return _extract_invoice_date({}, pdf_path)


class _ManagerShim:
    def __init__(self, legacy: Any, main_app: _MainAppShim, logger: logging.Logger) -> None:
        self.root = None
        self.main_app = main_app
        self.logger = logger
        self.erp_pids: dict[str, int] = {}
        self.config_path = _resolve_erp_config_path(legacy)
        self.config_mgr = legacy.ERPConfig(str(self.config_path))


def _resolve_erp_config_path(legacy: Any) -> Path:
    primary = Path(getattr(legacy, "CONFIG_FILE", "") or settings.legacy_manager_path.parent / "config.ini")
    candidates = [
        primary,
        settings.legacy_manager_path.parent / "config.ini",
        PROJECT_ROOT / "support" / "config.ini",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return primary


def _validate_install_info(manager: _ManagerShim, install_key: str, corp_code: str) -> tuple[dict[str, Any], dict[str, Any]]:
    install_info = manager.config_mgr.get_install_info(install_key)
    corp_info = manager.config_mgr.get_corp_info(corp_code)
    exe_path = str(install_info.get("exe_path") or "").strip()
    if not exe_path:
        raise RuntimeError(
            f"K-System 실행파일 경로가 비어 있습니다. "
            f"config={manager.config_path} section=INSTALL_{install_key} key=exe_path"
        )
    if not Path(exe_path).exists():
        raise RuntimeError(
            f"K-System 실행파일을 찾지 못했습니다. "
            f"config={manager.config_path} section=INSTALL_{install_key} exe_path={exe_path}"
        )
    if not str(corp_info.get("user_id") or "").strip():
        raise RuntimeError(f"K-System 로그인 ID가 비어 있습니다. config={manager.config_path} section=CORP_{corp_code}")
    if not str(corp_info.get("password") or "").strip():
        raise RuntimeError(f"K-System 로그인 비밀번호가 비어 있습니다. config={manager.config_path} section=CORP_{corp_code}")
    return install_info, corp_info


def _load_legacy_module() -> Any:
    path = settings.legacy_manager_path
    if not path.exists():
        raise RuntimeError(f"기존 ERP 자동입력 파일을 찾지 못했습니다: {path}")
    fitz_stubbed = _install_fitz_stub_if_needed()
    spec = importlib.util.spec_from_file_location("legacy_manager_v62", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"기존 ERP 자동입력 파일을 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        if fitz_stubbed and getattr(sys.modules.get("fitz"), "__web_v1_stub__", False):
            sys.modules.pop("fitz", None)
    return module


def _install_fitz_stub_if_needed() -> bool:
    """The legacy UI module imports fitz at module load, but ERP input does not use it here."""
    if "fitz" in sys.modules:
        return False
    try:
        __import__("fitz")
        return False
    except Exception:
        stub = types.ModuleType("fitz")
        stub.__web_v1_stub__ = True  # type: ignore[attr-defined]

        def _unavailable(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("PyMuPDF(fitz)는 WEB ERP 입력 경로에서 사용하지 않도록 우회되었습니다.")

        stub.open = _unavailable  # type: ignore[attr-defined]
        sys.modules["fitz"] = stub
        return True


def _corp_codes(site_name: str) -> tuple[str, str]:
    corp_name = CORP_MAP.get(site_name, "㈜대승")
    if "대승정밀" in corp_name:
        return "DSJM", "DSJM"
    if "일강" in corp_name:
        return "ILGANG", "ILGANG"
    if "제이엠" in corp_name:
        return "JM", "JM"
    if "더원" in corp_name:
        return "TO", "TO"
    return "DAESEUNG", "DS"


def _configure_pyautogui_for_server(legacy: Any, progress: Progress | None = None) -> None:
    try:
        import pyautogui

        pyautogui.FAILSAFE = False
        legacy_pyautogui = getattr(legacy, "pyautogui", None)
        if legacy_pyautogui is not None:
            legacy_pyautogui.FAILSAFE = False
        if progress:
            progress("PyAutoGUI fail-safe disabled for server ERP automation")
    except Exception as exc:
        if progress:
            progress(f"PyAutoGUI fail-safe setup warning: {exc}")


def run_invoice_erp_input(invoice: dict[str, Any], *, job_id: str, progress: Progress | None = None) -> dict[str, Any]:
    raw_meta = invoice.get("raw") if isinstance(invoice.get("raw"), dict) else {}
    invoice_type = str(invoice.get("invoice_type") or raw_meta.get("invoice_type") or "").strip().lower()
    if invoice_type == "purchase":
        payload = build_purchase_erp_payload(invoice)
    else:
        payload = build_regular_erp_payload(invoice)
    data = payload["data"]
    rows = payload["rows"]
    if not rows:
        raise RuntimeError("ERP에 입력할 분개 행이 없습니다.")

    import pyperclip

    settings.erp_output_dir.mkdir(parents=True, exist_ok=True)
    invoice_id = invoice.get("id") or "unknown"
    save_path = settings.erp_output_dir / f"erp_voucher_{job_id}_{invoice_id}.pdf"
    if not settings.erp_print_target:
        raise RuntimeError("ERP_PRINT_TARGET 또는 PRINT_TARGET_PDF가 설정되어 있지 않습니다.")
    print_choice = {
        "label": "WEB v1.0 ERP PDF 저장",
        "match": settings.erp_print_target,
        "kind": "pdf_merge",
        "save_path": str(save_path),
    }

    pyperclip.copy("\r\n".join(rows))
    if progress:
        progress(f"ERP 분개 데이터 생성 완료: {len(rows)}줄")

    legacy = _load_legacy_module()
    logger = logging.getLogger(f"WEB_V1_ERP_{job_id}_{invoice_id}")
    logger.setLevel(logging.INFO)
    handler = _ProgressHandler(progress)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    try:
        main_app = _MainAppShim(data, print_choice)
        manager = _ManagerShim(legacy, main_app, logger)
        install_key, corp_code = _corp_codes(str(data.get("site_name") or ""))
        install_info, corp_info = _validate_install_info(manager, install_key, corp_code)
        if progress:
            progress(f"K-System 자동입력 시작: site={data.get('site_name')} corp={corp_code} config={manager.config_path}")
        _configure_pyautogui_for_server(legacy, progress)
        main_app.erp_job_id = job_id
        main_app.erp_invoice_id = invoice_id
        bot = legacy.ERPLoginBot(
            install_info,
            corp_info,
            corp_code,
            manager,
            logger,
        )
        result = bot.run()
        if result is not True:
            raise RuntimeError(str(result))
        erp_pdf_path = main_app.last_erp_print_output or str(save_path)
        erp_pdf = Path(str(erp_pdf_path))
        if not erp_pdf.exists():
            raise RuntimeError(f"ERP 전표 PDF 자동 저장 실패: {erp_pdf}")
        if progress:
            progress(f"ERP 전표 PDF 자동 저장 완료: {erp_pdf}")
        return {
            "invoice_id": invoice_id,
            "site_name": data.get("site_name"),
            "rows": len(rows),
            "erp_pdf_path": str(erp_pdf),
        }
    finally:
        logger.removeHandler(handler)

