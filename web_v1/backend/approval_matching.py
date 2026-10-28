"""Deterministic approval matching. Search hits alone never establish identity."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from datetime import date, timedelta
from typing import Any

from .erp_runner import FACTORY_MAP, CORP_MAP


def compact(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper()


def invoice_context(invoice: dict, reference_date: str) -> dict:
    raw = invoice.get("raw") if isinstance(invoice.get("raw"), dict) else {}
    data = {**raw, **(raw.get("data") if isinstance(raw.get("data"), dict) else {}),
            **(invoice.get("data") if isinstance(invoice.get("data"), dict) else {})}
    biz = re.sub(r"\D", "", str(data.get("buyer_biz_no") or data.get("buyer_business_no") or ""))
    site = next((site for number, site in FACTORY_MAP.items() if re.sub(r"\D", "", number) == biz), "")
    declared_site = str(data.get("site_name") or invoice.get("site_name") or "")
    amount = str(data.get("total_sum") or invoice.get("total_sum") or 0).replace(",", "").strip()
    total = int(amount) if re.fullmatch(r"-?\d+", amount) else 0
    value = {
        "invoice_id": int(invoice["id"]), "total": total, "buyer_biz_no": biz,
        "site": site, "company": CORP_MAP.get(site, ""), "declared_site": declared_site,
        "vendor": str(data.get("vendor_name") or invoice.get("vendor_name") or ""),
        "order_number": str(data.get("order_no") or data.get("quote_order_no") or ""),
        "quote_path": str(data.get("quote_path") or ""), "reference_date": reference_date,
    }
    try:
        quote_stat = Path(value["quote_path"]).stat()
        value["quote_revision"] = [quote_stat.st_size, quote_stat.st_mtime_ns]
    except OSError:
        value["quote_revision"] = None
    value["fingerprint"] = context_fingerprint(value)
    return value


def context_fingerprint(context: dict) -> str:
    keys = ("invoice_id", "total", "buyer_biz_no", "site", "company", "declared_site", "vendor", "order_number", "quote_path", "quote_revision")
    return hashlib.sha256(json.dumps({key: context.get(key) for key in keys}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_context(context: dict) -> None:
    if context["total"] <= 0:
        raise ValueError("금액 보조 검색에 필요한 부가세 포함 합계가 없습니다. 견적서 분석 금액을 확인해 주세요.")
    if not context["site"] or not context["company"]:
        raise ValueError("매입자 사업자번호로 법인·사업장을 확인하지 못해 금액 보조 검색을 중단했습니다.")
    if context["declared_site"] and compact(context["declared_site"]) != compact(context["site"]):
        raise ValueError("매입자 사업자번호와 분석된 사업장이 달라 금액 보조 검색을 중단했습니다.")
    date.fromisoformat(context["reference_date"])


def amount_variants(total: int) -> list[str]:
    return list(dict.fromkeys([f"{total:,}", str(total)]))


def stated_totals(body: str) -> set[int]:
    # Require a total/amount label, not an arbitrary unit price or account number.
    pattern = r"(?:총\s*(?:구매\s*)?금액|합\s*계|총\s*계|(?:^|\n)\s*(?:\d+[.)]\s*)?금\s*액|(?:^|\n)\s*계(?=\s*\n))\s*[:：]?\s*([0-9][0-9,]*)\s*(?:원|\b)"
    return {int(m.group(1).replace(",", "")) for m in re.finditer(pattern, body, re.M)}


def form_company(form_name: str) -> str:
    text = compact(form_name)
    for name in ("대승정밀", "일강", "대승", "제이엠", "더원"):
        if name in text:
            return name
    return ""


def vendor_key(value: str) -> str:
    return re.sub(r"주식회사|유한회사|\(주\)|\(유\)|㈜|㈔|[^0-9A-Z가-힣]", "", compact(value))


def assess_candidate(candidate: dict, context: dict, accounts: set[str]) -> dict:
    c = dict(candidate)
    blocked, warnings = [], []
    if c.get("status") != "완료":
        blocked.append("결재 미완료")
    try:
        approved = date.fromisoformat(str(c.get("approved_date") or ""))
        anchor = date.fromisoformat(context["reference_date"])
        if not anchor - timedelta(days=7) <= approved <= anchor:
            blocked.append("결재일이 최근 7일 범위 밖")
    except ValueError:
        blocked.append("결재일 확인 불가")
    account = str(c.get("drafter_account") or "").lower().split("@")[0]
    if not account or account not in accounts:
        blocked.append("허용된 전산팀 기안자 계정이 아님")
    totals = stated_totals(str(c.get("body") or ""))
    if totals and context["total"] not in totals:
        blocked.append("본문 합계 금액 불일치")
    elif not totals:
        warnings.append("본문의 합계 금액을 확정하지 못함")
    elif len(totals) != 1:
        warnings.append("본문에 서로 다른 합계 금액이 있음")
    text = compact(str(c.get("title") or "") + "\n" + str(c.get("body") or ""))
    sites = {site for site in FACTORY_MAP.values() if compact(site) in text}
    if sites and context["site"] not in sites:
        blocked.append("사업장 불일치")
    elif not sites or len(sites) > 1:
        warnings.append("사업장을 하나로 확정하지 못함")
    company = form_company(str(c.get("form_name") or ""))
    if not company or company != form_company(context["company"]):
        warnings.append("결재양식의 법인 확인 필요")
    vendor = vendor_key(context["vendor"])
    if not vendor or vendor not in vendor_key(str(c.get("body") or "")):
        warnings.append("본문 거래처 확인 필요")
    orders = set(re.findall(r"\((\d{8})\)", str(c.get("body") or "")))
    expected_order = context.get("order_number")
    if orders and expected_order and expected_order not in orders:
        blocked.append("본문 주문번호 불일치")
    c.update(blocked=blocked, warnings=warnings, eligible=not blocked, verified=not blocked and not warnings,
             matched_order=bool(expected_order and expected_order in orders), matched_total=context["total"] in totals)
    return c


def decide(candidates: list[dict], context: dict, accounts: set[str], *, truncated: bool = False) -> dict:
    assessed = [assess_candidate(c, context, accounts) for c in candidates]
    eligible = [c for c in assessed if c["eligible"]]
    # Never prefer the newest/first/best-scored document when another could match.
    if not truncated and len(eligible) == 1 and eligible[0]["verified"]:
        return {"status": "matched", "selected": eligible[0], "candidates": eligible}
    if eligible:
        reason = "검색 결과가 많아 전체 후보를 확인하지 못했습니다." if truncated else ("조건에 맞는 품의가 여러 건입니다." if len(eligible) > 1 else "품의의 일부 정보가 일치하는지 확인이 필요합니다.")
        return {"status": "review", "reason": reason, "candidates": eligible}
    counts: dict[str, int] = {}
    for c in assessed:
        for reason in c["blocked"]:
            counts[reason] = counts.get(reason, 0) + 1
    explanation = ", ".join(f"{reason} {count}건" for reason, count in counts.items()) or "본문 금액 검색 결과 없음"
    return {"status": "not_found", "reason": f"금액 보조 검색에서 조건을 만족하는 품의를 찾지 못했습니다. {explanation}.", "candidates": []}


def public_candidate(candidate: dict) -> dict:
    # Exclude full body/bank data and browser implementation details from API storage.
    keys = ("doc_id", "doc_no", "title", "form_name", "drafter_name", "drafter_account", "approved_date", "status", "warnings", "matched_total", "matched_order")
    return {key: candidate.get(key) for key in keys}
