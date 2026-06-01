from __future__ import annotations

import json
import re
import difflib
from pathlib import Path
from typing import Any

import pdfplumber

from .config import settings
from .erp_runner import FACTORY_MAP, _site_from_biz_no, _to_int


ACCOUNT_CHOICES = {"소모품비", "집기비품", "컴퓨터소프트웨어"}


def safe_filename(name: str, fallback: str = "purchase_file.pdf") -> str:
    clean = re.sub(r'[\\/:*?"<>|]+', "_", str(name or "").strip())
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or fallback


def purchase_quote_dir(invoice_id: int) -> Path:
    path = settings.erp_db_dir / "purchase_quotes" / str(invoice_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def purchase_approval_dir(invoice_id: int) -> Path:
    path = settings.erp_db_dir / "purchase_approvals" / str(invoice_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clean_text(value: Any, fallback: str = "") -> str:
    return re.sub(r"\s+", " ", str(value or fallback).strip())


def _strip_vendor_name(value: Any) -> str:
    text = _clean_text(value, "매입처")
    text = re.sub(r"\(주\)|㈜|\(유\)|유한회사|주식회사", "", text)
    return _clean_text(text, "매입처")


def _clean_match_text(value: Any) -> str:
    return re.sub(r"[^가-힣A-Z0-9]+", "", str(value or "").upper())


def _extract_models(text: str) -> set[str]:
    return set(re.findall(r"[A-Z]+[0-9]+[A-Z0-9]*|[0-9]+[A-Z]+[A-Z0-9]*", str(text or "")))


def _load_dictionary_rows() -> list[tuple[str, str, bool, str]]:
    try:
        from .invoice_db import get_conn, init_db

        init_db()
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT original_text, corrected_name, is_asset, account
                FROM dictionary
                WHERE id IN (SELECT MAX(id) FROM dictionary GROUP BY original_text)
                """
            )
            return [(str(row[0] or ""), str(row[1] or ""), bool(row[2]), str(row[3] or "")) for row in cur.fetchall()]
    except Exception:
        return []


def _extract_pdf_text(path: str | Path) -> str:
    chunks: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    text = "\n".join(chunks)
    if text.strip():
        return text
    try:
        import fitz

        with fitz.open(str(path)) as doc:
            return "\n".join(page.get_text() or "" for page in doc)
    except Exception:
        return text


def _extract_amounts_from_tax(text: str) -> tuple[int, int, int]:
    money = r"\d{1,3}(?:,\d{3})+|\d{5,13}"
    date_label = "\uc791\uc131\uc77c\uc790"
    supply_label = "\uacf5\uae09\uac00\uc561"
    tax_label = "\uc138\uc561"
    total_label = "\ud569\uacc4\uae08\uc561"
    flat = re.sub(r"\s+", " ", str(text or ""))

    header_match = re.search(
        rf"{date_label}\s+{supply_label}\s+{tax_label}.*?"
        rf"20\d{{2}}[./\-\s]*(?:0?[1-9]|1[0-2])[./\-\s]*(?:[0-3]?\d)\s+({money})\s+({money})",
        flat,
        re.DOTALL,
    )
    if header_match:
        supply = _to_int(header_match.group(1))
        tax = _to_int(header_match.group(2))
        total = 0
        total_match = re.search(rf"{total_label}.{{0,120}}?({money})", flat, re.DOTALL)
        if total_match:
            total = _to_int(total_match.group(1))
        total = total or supply + tax
        return supply, tax, total

    label_total = 0
    total_match = re.search(rf"{total_label}.{{0,120}}?({money})", flat, re.DOTALL)
    if total_match:
        label_total = _to_int(total_match.group(1))

    nums = sorted({_to_int(n) for n in re.findall(rf"(?<!\d)({money})(?!\d)", flat)}, reverse=True)
    nums = [value for value in nums if 1000 <= value <= 999_999_999]
    for candidate_total in nums:
        for supply in nums:
            if supply >= candidate_total:
                continue
            tax = candidate_total - supply
            if tax in nums or abs(round(supply * 0.1) - tax) <= 10:
                return supply, tax, candidate_total
    if label_total:
        for supply in nums:
            tax = label_total - supply
            if 0 < tax <= label_total and (tax in nums or abs(round(supply * 0.1) - tax) <= 10):
                return supply, tax, label_total
    return 0, 0, 0


def _extract_order_no_from_tax(text: str) -> str:
    source = str(text or "")
    flat = re.sub(r"\s+", " ", source)
    patterns = [
        r"\bTax\s*No\s*[:：]?\s*[A-Z]\s*-\s*(\d{8})\b",
        r"\bTaxNo\s*[:：]?\s*[A-Z]\s*-\s*(\d{8})\b",
        r"(?:책번호|일련번호).{0,80}?\b[A-Z]\s*-\s*(\d{8})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, flat, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _extract_order_no_from_quote(text: str) -> str:
    source = str(text or "")
    flat = re.sub(r"\s+", " ", source)
    patterns = [
        r"(?:견적\s*번호|견적번호)\s*[:：]?\s*(\d{8})\b",
        r"(?:Quote\s*No|Quotation\s*No)\s*[:：]?\s*(\d{8})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, flat, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _extract_date(text: str, fallback_path: str = "") -> str:
    def _format(match: re.Match[str]) -> str:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"

    generic_patterns = [
        r"(20\d{2})[-./년\s]*(0?[1-9]|1[0-2])[-./월\s]*([0-3]?\d)",
        r"(20\d{2})(0[1-9]|1[0-2])([0-3]\d)",
    ]

    # The tax-invoice body can contain old certificate/legal dates such as 2002-02-06.
    # Prefer the crawler filename and explicit invoice-date labels, then stop.
    filename = Path(fallback_path or "").name
    for pattern in generic_patterns:
        match = re.search(pattern, filename)
        if match:
            return _format(match)

    label_patterns = [
        r"(?:작성일자|작성\s*일자|발행일자|발행\s*일자|공급일자|공급\s*일자).{0,80}?(20\d{2})[-./년\s]*(0?[1-9]|1[0-2])[-./월\s]*([0-3]?\d)",
        r"(?:작성일자|작성\s*일자|발행일자|발행\s*일자|공급일자|공급\s*일자).{0,80}?(20\d{2})(0[1-9]|1[0-2])([0-3]\d)",
    ]
    for pattern in label_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return _format(match)

    for value in re.findall(r"(?:승인번호|관리번호).{0,30}?(20\d{2})(0[1-9]|1[0-2])([0-3]\d)", text, re.DOTALL):
        try:
            return f"{int(value[0]):04d}-{int(value[1]):02d}-{int(value[2]):02d}"
        except Exception:
            pass

    return ""


def extract_purchase_date_from_path(pdf_path: str) -> str:
    return _extract_date("", pdf_path)


def _extract_site(text: str, existing: dict[str, Any]) -> tuple[str, str]:
    for value in (
        existing.get("buyer_biz_no"),
        existing.get("buyer_business_no"),
        existing.get("matched_biz_no"),
    ):
        site = _site_from_biz_no(value)
        if site:
            return site, str(value)
    for raw in re.findall(r"\d{3}[-\s]?\d{2}[-\s]?\d{5}", text):
        digits = re.sub(r"\D", "", raw)
        biz_no = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        if biz_no in FACTORY_MAP:
            return FACTORY_MAP[biz_no], biz_no
    for site in FACTORY_MAP.values():
        if site in text:
            return site, ""
    return _clean_text(existing.get("site_name")), ""


def _is_cad_pc_text(value: Any) -> bool:
    compact = re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())
    return "CADPC" in compact


def _is_graphics_card_text(value: Any) -> bool:
    text = str(value or "")
    upper = text.upper()
    compact = re.sub(r"[^A-Z0-9가-힣]+", "", upper)
    if any(token in compact for token in ("그래픽카드", "지포스", "GEFORCE", "RADEON")):
        return True
    if any(token in compact for token in ("RTX", "GTX")):
        return True
    return bool(re.search(r"\b(?:VGA|RX)\s*[-]?\s*\d{3,5}\b", upper))


def _guess_account(name: str) -> str:
    text = name.lower()
    if _is_cad_pc_text(name):
        return "집기비품"
    if _is_graphics_card_text(name):
        return "집기비품"
    if any(token in text for token in ("office", "adobe", "cad", "라이선스", "소프트웨어", "백신", "프로그램")):
        return "컴퓨터소프트웨어"
    if any(token in text for token in ("모니터", "pc", "컴퓨터", "노트북", "프린터", "스캐너", "장비", "키보드")):
        return "집기비품"
    return "소모품비"


def _is_monitor_accessory(text: str) -> bool:
    compact = re.sub(r"\s+", "", str(text or ""))
    return any(token in compact for token in ("모니터암", "모니터받침", "모니터스탠드", "모니터거치대"))


def _simplify_purchase_item_name(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    stripped = re.sub(r"\[[^\]]+\]\s*", " ", text)
    stripped = re.sub(r"\([^)]*\)\s*", " ", stripped)
    stripped = re.sub(r"\{[^}]*\}\s*", " ", stripped)
    stripped = re.sub(r"\b(?:화이트|블랙|실버|그레이|그린|레드|블루|색상선택|색상|옵션|벌크)\b.*$", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s+", " ", stripped).strip(" -_/.,")
    compact = re.sub(r"\s+", "", stripped)
    upper = stripped.upper()

    if _is_graphics_card_text(text):
        return "그래픽카드"
    if "멀티탭" in compact and "USB" in upper:
        outlet = re.search(r"(\d+)\s*구", stripped)
        return f"USB {outlet.group(1)}구 멀티탭" if outlet else "USB 멀티탭"
    if any(token in compact for token in ("복합기", "프린터", "잉크젯")) or any(token in upper for token in ("PIXMA", "CANON", "INKJET")):
        if any(token in compact for token in ("복합기", "잉크젯")) or "PIXMA" in upper:
            return "잉크젯복합기"
        if "잉크" in compact:
            return "프린터 잉크"
        return "프린터"
    if "블루투스" in compact and "스피커" in compact:
        return "블루투스 스피커"
    if "차량용" in compact and "공기청정" in compact:
        return "차량용 공기청정기"
    if "차량용" in compact and "무선충전" in compact and "거치대" in compact:
        return "차량용 무선충전 거치대"
    if "모니터" in compact and "받침" in compact:
        return "모니터 받침대"
    if "충전기" in compact and "차량용" in compact:
        return "차량용 충전기"
    if "마우스" in compact:
        return "마우스"
    if "키보드" in compact:
        return "키보드"
    return ""


def _process_items_with_db(items: list[dict[str, Any]], db_rows: list[tuple[str, str, bool, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    db = [
        {
            "key": _clean_match_text(row[0]),
            "original_text": row[0],
            "name": row[1],
            "is_a": bool(row[2]),
            "account": row[3] if len(row) > 3 and row[3] in ACCOUNT_CHOICES else ("집기비품" if bool(row[2]) else "소모품비"),
            "models": _extract_models(row[0]),
        }
        for row in db_rows
        if len(_clean_match_text(row[0])) >= 2
    ]
    db.sort(key=lambda entry: len(entry["key"]), reverse=True)
    final: list[dict[str, Any]] = []
    unknown: list[str] = []

    for source in items:
        item = dict(source or {})
        target_clean = _clean_match_text(item.get("raw_desc", "")) + _clean_match_text(item.get("name", ""))
        if any(token in target_clean for token in ("운송료", "배송비", "택배", "골드회원", "회원할인")):
            continue

        target_models = _extract_models(target_clean)
        best_match = None
        highest_score = 0.0
        exact_match = False
        for entry in db:
            key = entry["key"]
            if key in target_clean or target_clean in key:
                best_match = entry
                highest_score = 1.0
                exact_match = True
                break
            score = difflib.SequenceMatcher(None, key, target_clean).ratio()
            db_models = set(entry.get("models") or set())
            if target_models and db_models and not target_models.intersection(db_models):
                score *= 0.5
            if score > highest_score:
                highest_score = score
                best_match = entry

        model_match = bool(best_match and target_models and set(best_match.get("models") or set()).intersection(target_models))
        if best_match and (exact_match or highest_score >= 0.78 or (model_match and highest_score >= 0.45)):
            item["name"] = best_match["name"]
            item["is_a"] = best_match["is_a"]
            item["account"] = best_match["account"]
            item["raw_desc"] = best_match["original_text"]
            item["learned_match"] = True
        else:
            original_name = str(item.get("name") or item.get("raw_desc") or "")
            simplified_name = _simplify_purchase_item_name(original_name)
            if simplified_name:
                item.setdefault("raw_desc", original_name)
                item["name"] = simplified_name
                item["system_adjustment"] = True
            else:
                unknown.append(original_name)
        final.append(item)

    processed: list[dict[str, Any]] = []
    for item in final:
        name = str(item.get("name", "") or "")
        name_upper = name.upper()
        qty = max(1, _to_int(item.get("qty") or 1))
        inc_vat_value = _to_int(item.get("inc_vat") or item.get("total") or item.get("amount"))
        if not inc_vat_value and _to_int(item.get("supply") or item.get("supply_amount")):
            inc_vat_value = round(_to_int(item.get("supply") or item.get("supply_amount")) * 1.1)
            item["inc_vat"] = inc_vat_value
        unit_price = float(inc_vat_value) / qty if qty else 0
        if unit_price >= 100000:
            if "데스크탑" in name:
                name = name.replace("데스크탑", "PC")
                name_upper = name.upper()
        item["name"] = name

        business_text = f"{name} {item.get('raw_desc', '')} {item.get('quote_category', '')}".upper()
        cad_pc_item = _is_cad_pc_text(name)
        graphics_card_item = _is_graphics_card_text(business_text)
        is_monitor_accessory = _is_monitor_accessory(business_text)
        force_asset = any(token in business_text for token in ("PC", "NOTEBOOK", "LAPTOP", "노트북", "랩탑", "복합기", "빔프로젝터"))
        if graphics_card_item:
            force_asset = True
        if "모니터" in business_text and not is_monitor_accessory:
            force_asset = True
        display_like = (
            ("크로스오버" in business_text or "CROSSOVER" in business_text)
            and any(token in business_text for token in ("IPS", "FHD", "QHD", "UHD", "무결점"))
        )
        if display_like and not is_monitor_accessory:
            force_asset = True
        if cad_pc_item:
            force_asset = True
        if force_asset:
            item["is_a"] = True
            item["account"] = "집기비품"
        force_sw = any(
            token in business_text
            for token in ("소프트", "OFFICE", "오피스", "한글", "CAD", "캐드", "SKETCHUP", "포토샵", "ADOBE", "어도비", "WINDOWS", "윈도우", "소프트웨어", "라이선스")
        ) and not cad_pc_item
        if force_sw:
            item["is_a"] = True
            item["account"] = "컴퓨터소프트웨어"
        if cad_pc_item:
            item["is_a"] = True
            item["account"] = "집기비품"
        if unit_price < 100000 and not (force_asset or force_sw) and not item.get("learned_match"):
            item["is_a"] = False
            item["account"] = "소모품비"
        if item.get("account") in {"집기비품", "컴퓨터소프트웨어"} and qty > 1:
            line_supply_value = _to_int(item.get("supply") or item.get("supply_amount"))
            already_unit_amount = (
                bool(line_supply_value and inc_vat_value)
                and abs(round(line_supply_value * 1.1) - inc_vat_value) <= max(10, int(abs(inc_vat_value) * 0.02))
            )
            if already_unit_amount:
                calc_unit_price = inc_vat_value
                calc_unit_supply = line_supply_value
            else:
                calc_unit_price = round(float(inc_vat_value) / qty) if inc_vat_value else 0
                calc_unit_supply = round(float(line_supply_value) / qty) if line_supply_value else round(calc_unit_price / 1.1)
            for _ in range(qty):
                split = dict(item)
                split["qty"] = 1
                split["inc_vat"] = calc_unit_price
                split["supply"] = calc_unit_supply
                split["split_from_qty"] = qty
                processed.append(split)
        else:
            processed.append(item)
    return _normalize_items_for_display(processed), sorted({value for value in unknown if value})


def _recover_qty_from_item_text(item: dict[str, Any]) -> dict[str, Any]:
    repaired = dict(item or {})
    if repaired.get("split_from_qty"):
        repaired["qty"] = max(1, _to_int(repaired.get("qty") or 1))
        return repaired
    text = f"{repaired.get('raw_desc', '')}\n{repaired.get('name', '')}"
    current_qty = max(1, _to_int(repaired.get("qty") or 1))
    fixed_qty = current_qty
    patterns = [
        r"(?<!\d)(\d{1,3})\s*(?:EA|개|PCS?|SET)\b",
        r"(?<!\d)(\d{1,3})\s*/\s*\d{1,3}(?:,\d{3})*\s*원",
        r"수량\s*[:：]?\s*(\d{1,3})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fixed_qty = max(1, int(match.group(1)))
            break
    repaired["qty"] = fixed_qty
    return repaired


def _normalize_items_for_display(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fixed: list[dict[str, Any]] = []
    for item in list(items or []):
        repaired = _recover_qty_from_item_text(dict(item or {}))
        item_text = " ".join(str(repaired.get(key, "") or "") for key in ("name", "raw_desc", "original_text", "desc"))
        if _is_cad_pc_text(repaired.get("name")):
            repaired["account"] = "집기비품"
            repaired["is_a"] = True
        elif _is_graphics_card_text(item_text):
            repaired["account"] = "집기비품"
            repaired["is_a"] = True
            current_name = str(repaired.get("name") or "").strip()
            if not current_name or len(current_name) > 30 or _is_graphics_card_text(current_name):
                repaired["name"] = "그래픽카드"
        elif _is_monitor_accessory(item_text):
            repaired["account"] = "소모품비"
            repaired["is_a"] = False
            if not str(repaired.get("name", "")).strip():
                repaired["name"] = "모니터암"
        elif "모니터" in item_text:
            repaired["account"] = "집기비품"
            repaired["is_a"] = True
        fixed.append(repaired)
    return fixed


def _collapse_duplicate_total_prices(items: list[dict[str, Any]], target_supply: int) -> list[dict[str, Any]]:
    if not target_supply or not items:
        return items
    total_supply = sum(_to_int(item.get("supply")) for item in items)
    if total_supply <= target_supply + max(10_000, int(target_supply * 0.05)):
        return items

    grouped: dict[tuple[str, str, int], list[int]] = {}
    for idx, item in enumerate(items):
        qty = max(1, _to_int(item.get("qty") or 1))
        supply = _to_int(item.get("supply"))
        if qty != 1 or supply <= 0 or item.get("split_from_qty"):
            continue
        key = (
            _clean_match_text(item.get("raw_desc") or item.get("name")),
            str(item.get("account") or ""),
            supply,
        )
        grouped.setdefault(key, []).append(idx)

    repaired = [dict(item) for item in items]
    changed = False
    for indexes in grouped.values():
        if len(indexes) <= 1:
            continue
        original_supply = _to_int(repaired[indexes[0]].get("supply"))
        original_inc_vat = _to_int(repaired[indexes[0]].get("inc_vat"))
        unit_supply = max(1, round(original_supply / len(indexes)))
        unit_inc_vat = max(1, round(original_inc_vat / len(indexes))) if original_inc_vat else round(unit_supply * 1.1)
        for idx in indexes:
            repaired[idx]["supply"] = unit_supply
            repaired[idx]["inc_vat"] = unit_inc_vat
            repaired[idx]["split_from_qty"] = len(indexes)
        changed = True

    return repaired if changed else items


def _extract_compuzone_quote_items(text: str) -> list[dict[str, Any]]:
    lines = [_clean_text(line) for line in str(text or "").splitlines() if _clean_text(line)]
    start_idx = -1
    for idx, line in enumerate(lines):
        compact = line.replace(" ", "")
        if all(token in compact for token in ("번호", "제품명", "판매가", "수량")):
            start_idx = idx + 1
            break
    if start_idx < 0:
        return []

    table_lines: list[str] = []
    for line in lines[start_idx:]:
        compact = line.replace(" ", "")
        if any(token in compact for token in ("총견적금액", "빠른상담", "입금계좌", "결제방법", "유의사항")):
            break
        table_lines.append(line)

    blocks: list[str] = []
    current: list[str] = []
    row_start = re.compile(r"^(\d{1,3}(?:-\d{1,3})?)\s+\S+")
    expected_base = 1
    for line in table_lines:
        row_match = row_start.match(line)
        is_row_start = False
        if row_match:
            row_id = row_match.group(1)
            base_no = int(row_id.split("-", 1)[0])
            if "-" in row_id:
                is_row_start = base_no in {expected_base - 1, expected_base}
            else:
                is_row_start = base_no == expected_base
                if is_row_start:
                    expected_base = base_no + 1
        if is_row_start:
            if current:
                blocks.append(" ".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(" ".join(current))

    items: list[dict[str, Any]] = []
    tail_pattern = re.compile(
        r"(?P<unit>-?\d{1,3}(?:,\d{3})+)\s*원?\s+"
        r"(?P<qty>-?\d{1,3})\s+"
        r"(?P<total>-?\d{1,3}(?:,\d{3})+)\s*원?\s*$"
    )
    for block in blocks:
        match = tail_pattern.search(block)
        if not match:
            continue
        qty = int(match.group("qty"))
        inc_vat = _to_int(match.group("total"))
        if qty <= 0 or inc_vat <= 0:
            continue

        desc = tail_pattern.sub("", block)
        desc = re.sub(r"^\d{1,3}(?:-\d{1,3})?\s+", "", desc)
        desc = _clean_text(desc)
        if any(token in desc for token in ("운송료", "배송비", "택배", "골드회원")):
            continue
        items.append(
            {
                "raw_desc": desc,
                "name": desc,
                "qty": qty,
                "inc_vat": inc_vat,
                "account": "소모품비",
                "is_a": False,
                "dept": "",
            }
        )
    return items


def _group_pdf_words_to_lines(words: list[dict[str, Any]], tolerance: float = 3.2) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for word in sorted(words, key=lambda item: (float(item.get("top") or 0), float(item.get("x0") or 0))):
        top = float(word.get("top") or 0)
        if not lines or abs(top - lines[-1]["top"]) > tolerance:
            lines.append({"top": top, "words": [word]})
        else:
            lines[-1]["words"].append(word)
            count = len(lines[-1]["words"])
            lines[-1]["top"] = ((lines[-1]["top"] * (count - 1)) + top) / count
    for line in lines:
        line["words"].sort(key=lambda item: float(item.get("x0") or 0))
        line["text"] = _clean_text(" ".join(str(word.get("text") or "") for word in line["words"]))
    return lines


def _extract_compuzone_quote_items_from_pdf(path: str | Path) -> list[dict[str, Any]]:
    try:
        with pdfplumber.open(str(path)) as pdf:
            words: list[dict[str, Any]] = []
            offset = 0.0
            for page in pdf.pages:
                for word in page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False) or []:
                    item = dict(word)
                    item["top"] = float(item.get("top") or 0) + offset
                    item["bottom"] = float(item.get("bottom") or 0) + offset
                    words.append(item)
                offset += float(page.height or 0) + 40.0
    except Exception:
        return []
    if not words:
        return []

    lines = _group_pdf_words_to_lines(words)
    header_idx = -1
    for idx, line in enumerate(lines):
        compact = str(line.get("text") or "").replace(" ", "")
        if all(token in compact for token in ("번호", "분류", "제품명", "판매가", "수량", "합계")):
            header_idx = idx
            break
    if header_idx < 0:
        return []

    table_lines: list[dict[str, Any]] = []
    for line in lines[header_idx + 1 :]:
        compact = str(line.get("text") or "").replace(" ", "")
        if any(token in compact for token in ("총견적금액", "빠른상담", "입금계좌", "결제방법", "유의사항")):
            break
        table_lines.append(line)

    def _is_row_line(line: dict[str, Any]) -> bool:
        line_words = list(line.get("words") or [])
        if not line_words:
            return False
        first = line_words[0]
        first_text = str(first.get("text") or "")
        if float(first.get("x0") or 0) > 95 or not re.fullmatch(r"\d{1,3}(?:-\d{1,3})?", first_text):
            return False
        amount_words = [
            word for word in line_words
            if float(word.get("x0") or 0) >= 390
            and re.search(r"-?\d{1,3}(?:,\d{3})+", str(word.get("text") or ""))
        ]
        return len(amount_words) >= 2

    row_indexes = [idx for idx, line in enumerate(table_lines) if _is_row_line(line)]
    if not row_indexes:
        return []

    items: list[dict[str, Any]] = []
    for pos, row_index in enumerate(row_indexes):
        row = table_lines[row_index]
        row_words = list(row.get("words") or [])
        row_text = str(row.get("text") or "")
        prev_index = row_indexes[pos - 1] if pos else None
        next_index = row_indexes[pos + 1] if pos + 1 < len(row_indexes) else None

        context_indexes = {row_index}
        before_start = (prev_index + 1) if prev_index is not None else 0
        for idx in range(before_start, row_index):
            prev_dist = (idx - prev_index) if prev_index is not None else 999
            current_dist = row_index - idx
            if prev_index is None or current_dist <= prev_dist:
                context_indexes.add(idx)
        after_end = next_index if next_index is not None else len(table_lines)
        for idx in range(row_index + 1, after_end):
            current_dist = idx - row_index
            next_dist = (next_index - idx) if next_index is not None else 999
            if next_index is None or current_dist < next_dist:
                context_indexes.add(idx)

        amount_words = [
            word for word in row_words
            if float(word.get("x0") or 0) >= 390
            and re.search(r"-?\d{1,3}(?:,\d{3})+", str(word.get("text") or ""))
        ]
        if len(amount_words) < 2:
            continue
        unit_word = amount_words[-2]
        total_word = amount_words[-1]
        if str(total_word.get("text") or "").strip().startswith("-"):
            continue
        total = _to_int(total_word.get("text"))
        unit = _to_int(unit_word.get("text"))
        qty_words = [
            word for word in row_words
            if 455 <= float(word.get("x0") or 0) <= 510
            and re.fullmatch(r"-?\d{1,3}", str(word.get("text") or ""))
        ]
        qty = _to_int(qty_words[-1].get("text")) if qty_words else 0
        if qty <= 0 and unit > 0:
            qty = max(1, round(total / unit))
        if qty <= 0 or total <= 0:
            continue

        desc_parts: list[str] = []
        for idx in sorted(context_indexes):
            product_words = [
                str(word.get("text") or "")
                for word in table_lines[idx].get("words") or []
                if 150 <= float(word.get("x0") or 0) < 410
            ]
            part = _clean_text(" ".join(product_words))
            if part:
                desc_parts.append(part)
        desc = _clean_text(" ".join(desc_parts))
        if not desc:
            desc = _clean_text(row_text)
        desc = re.sub(r"-?\d{1,3}(?:,\d{3})+\s*원?", " ", desc)
        desc = re.sub(r"-(\d{4,})\s+(\d{1,3})(?=\s|$)", r"-\1\2", desc)
        desc = _clean_text(desc)
        category_words = [
            str(word.get("text") or "")
            for word in row_words
            if 92 <= float(word.get("x0") or 0) < 155
        ]
        category = _clean_text(" ".join(category_words))
        skip_text = f"{category} {desc}"
        if any(token in skip_text for token in ("운송료", "배송비", "택배", "골드회원", "회원할인")):
            continue

        items.append(
            {
                "raw_desc": desc,
                "name": desc,
                "qty": qty,
                "inc_vat": total,
                "account": "소모품비",
                "is_a": False,
                "dept": "",
                "quote_category": category,
            }
        )
    return items[:30]


def _extract_quote_items(text: str, target_supply: int, total_sum: int) -> list[dict[str, Any]]:
    compuzone_items = _extract_compuzone_quote_items(text)
    if compuzone_items:
        return compuzone_items[:30]

    items: list[dict[str, Any]] = []
    all_lines = [_clean_text(line) for line in text.splitlines() if _clean_text(line)]
    start_idx = 0
    for idx, line in enumerate(all_lines):
        compact = line.replace(" ", "")
        if "품명" in compact or "제품명" in compact or "단가" in compact or "판매가" in compact:
            start_idx = idx + 1
            break
    end_idx = len(all_lines)
    for idx, line in enumerate(all_lines[start_idx:]):
        compact = line.replace(" ", "")
        if any(token in compact for token in ("총견적", "합계", "입금계좌", "견적금액", "부가세", "배송비", "운송료")):
            end_idx = start_idx + idx
            break
    target_lines = all_lines[start_idx:end_idx]

    expected_no = 1
    anchors: list[int] = []
    for idx, line in enumerate(target_lines):
        if re.match(rf"^{expected_no}(?:\s|$|\.|\)|\|)", line):
            anchors.append(idx)
            expected_no += 1

    if anchors:
        bounds = [0]
        for idx in range(len(anchors) - 1):
            bounds.append(((anchors[idx] + anchors[idx + 1]) // 2) + 1)
        bounds.append(len(target_lines))
        blocks = [" ".join(target_lines[bounds[idx] : bounds[idx + 1]]) for idx in range(len(anchors))]
    else:
        blocks = target_lines

    for index, block_text in enumerate(blocks, start=1):
        source_text = re.sub(rf"^\s*{index}(?:\s|\.|\)|\|)+", "", block_text)
        comma_amounts = re.findall(r"\d{1,3}(?:,\d{3})+", source_text)
        if comma_amounts:
            inc_vat = _to_int(comma_amounts[-1])
        else:
            won_amounts = re.findall(r"(\d+)\s*원", source_text.replace(",", ""))
            if won_amounts:
                inc_vat = _to_int(won_amounts[-1])
            else:
                plain_amounts = re.findall(r"\b(\d{4,})\b", source_text)
                inc_vat = _to_int(plain_amounts[-1]) if plain_amounts else 0
        if inc_vat <= 0:
            continue

        total_token = f"{inc_vat:,}"
        qty = 1
        triple_patterns = [
            rf"(\d{{1,3}}(?:,\d{{3}})+)\s*원?\s+(\d{{1,3}})\s+{re.escape(total_token)}\s*원?",
            rf"(\d{{1,3}}(?:,\d{{3}})+)\s*원?\s*[xX*]\s*(\d{{1,3}})\s*=\s*{re.escape(total_token)}\s*원?",
            rf"(\d{{1,3}})\s+{re.escape(total_token)}\s*원?",
        ]
        qty_match = None
        for pattern in triple_patterns:
            qty_match = re.search(pattern, source_text, re.IGNORECASE)
            if qty_match:
                break
        if qty_match:
            qty = max(1, int(qty_match.group(2 if len(qty_match.groups()) >= 2 else 1)))
        else:
            qty_match = re.search(r"(?<![0-9A-Za-z가-힣])(\d{1,3})\s*(?:EA|개|PCS?|SET)\b", source_text, re.IGNORECASE)
            if not qty_match:
                qty_match = re.search(r"(?<![0-9A-Za-z가-힣])(\d{1,3})\s*/\s*\d{1,3}(?:,\d{3})*\s*원", source_text, re.IGNORECASE)
            if qty_match:
                qty = max(1, int(qty_match.group(1)))

        clean_block = re.sub(r"\b\d{1,3}(?:,\d{3})+\s*원\b|\b\d{4,}\s*원\b", "", block_text)
        clean_block = _clean_text(clean_block)
        items.append(
            {
                "raw_desc": clean_block,
                "name": clean_block,
                "qty": qty,
                "inc_vat": inc_vat,
                "account": "소모품비",
                "is_a": False,
                "dept": "",
            }
        )
    if not items:
        amount = total_sum or (target_supply + round(target_supply * 0.1))
        items.append(
            {
                "raw_desc": "견적서 품목 자동 추출 필요",
                "name": "구매품",
                "qty": 1,
                "inc_vat": amount,
                "supply": target_supply or round(amount / 1.1),
                "account": "소모품비",
                "is_a": False,
                "dept": "",
            }
        )
    return items[:30]


def _normalize_items(items: list[dict[str, Any]], target_supply: int) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        account = _clean_text(item.get("account"), "소모품비")
        if account not in ACCOUNT_CHOICES:
            account = _guess_account(_clean_text(item.get("name") or item.get("raw_desc")))
        qty = max(1, _to_int(item.get("qty") or item.get("quantity") or 1))
        inc_vat = _to_int(item.get("inc_vat") or item.get("total") or item.get("amount"))
        supply = _to_int(item.get("supply") or item.get("supply_amount"))
        if not supply and inc_vat:
            supply = round(inc_vat / 1.1)
        is_asset = bool(item.get("is_a")) if "is_a" in item else account != "소모품비"
        if not is_asset:
            account = "소모품비"
        dept = _clean_text(item.get("dept"))
        if account == "소모품비":
            dept = "소모품"
            is_asset = False
        normalized.append(
            {
                "raw_desc": _clean_text(item.get("raw_desc") or item.get("original_text") or item.get("desc")),
                "name": _clean_text(item.get("name") or item.get("item_name"), "구매품"),
                "qty": qty,
                "inc_vat": inc_vat,
                "supply": supply,
                "account": account,
                "is_a": is_asset,
                "dept": dept,
            }
        )
    if target_supply and normalized:
        normalized = _collapse_duplicate_total_prices(normalized, target_supply)
        remainder = target_supply - sum(_to_int(item.get("supply")) for item in normalized)
        if remainder and abs(remainder) <= max(10_000, int(target_supply * 0.05)):
            indexes = [idx for idx, item in enumerate(normalized) if _to_int(item.get("supply")) > 0]
            base = sum(_to_int(normalized[idx].get("supply")) for idx in indexes)
            if indexes and base:
                applied = 0
                for idx in indexes:
                    current_supply = _to_int(normalized[idx].get("supply"))
                    delta = round(remainder * (current_supply / base))
                    adjusted = current_supply + delta
                    if adjusted > 0:
                        normalized[idx]["supply"] = adjusted
                        applied += delta
                diff = remainder - applied
                if diff:
                    target_idx = max(indexes, key=lambda i: _to_int(normalized[i].get("supply")))
                    adjusted = _to_int(normalized[target_idx].get("supply")) + diff
                    if adjusted > 0:
                        normalized[target_idx]["supply"] = adjusted
    return normalized


def _fast_parse(tax_path: str, quote_path: str, existing: dict[str, Any]) -> dict[str, Any]:
    tax_text = _extract_pdf_text(tax_path)
    quote_text = _extract_pdf_text(quote_path)
    tax_supply, tax, total = _extract_amounts_from_tax(tax_text)
    tax_order_no = _extract_order_no_from_tax(tax_text)
    quote_order_no = _extract_order_no_from_quote(quote_text)
    order_no = tax_order_no or quote_order_no or _clean_text(
        existing.get("order_no") or existing.get("purchase_order_no") or existing.get("tax_order_no")
    )
    target_supply = tax_supply or _to_int(
        existing.get("target_supply")
        or existing.get("total_supply")
        or existing.get("supply_amount")
        or existing.get("supply")
    )
    total_tax = tax or _to_int(
        existing.get("total_tax")
        or existing.get("tax")
        or existing.get("tax_amount")
        or existing.get("vat")
    )
    total_sum = total or _to_int(
        existing.get("total_sum")
        or existing.get("total_amount")
        or existing.get("amount")
        or existing.get("grand_total")
    )
    if not target_supply and total_sum and total_tax:
        target_supply = max(0, total_sum - total_tax)
    if not total_tax and target_supply and total_sum:
        total_tax = max(0, total_sum - target_supply)
    if not total_sum and target_supply:
        total_sum = target_supply + total_tax
    site, buyer_biz_no = _extract_site(tax_text, existing)
    vendor = _strip_vendor_name(existing.get("vendor_name") or existing.get("supplier_name"))
    invoice_date = _extract_date(tax_text, tax_path) or _clean_text(existing.get("invoice_date") or existing.get("issue_date"))
    parsed_items = _extract_compuzone_quote_items_from_pdf(quote_path) or _extract_quote_items(quote_text, target_supply, total_sum)
    items, unknown = _process_items_with_db(parsed_items, _load_dictionary_rows())
    items = _normalize_items(items, target_supply)
    return {
        "site_name": site,
        "buyer_biz_no": buyer_biz_no or _clean_text(existing.get("buyer_biz_no") or existing.get("buyer_business_no")),
        "vendor_name": vendor,
        "invoice_date": invoice_date,
        "order_no": order_no,
        "tax_order_no": tax_order_no,
        "quote_order_no": quote_order_no,
        "target_supply": target_supply,
        "total_tax": total_tax,
        "total_sum": total_sum,
        "items": items,
        "analysis_source": "fast_parse",
        "analysis_unknown_items": unknown,
    }


def _ai_parse(tax_path: str, quote_path: str, fast_data: dict[str, Any]) -> dict[str, Any] | None:
    fast_data["analysis_ai_attempted"] = True
    fast_data["analysis_ai_error"] = ""
    api_key = settings.gemini_api_key
    if not api_key:
        message = "GEMINI_API_KEY missing"
        fast_data["analysis_ai_error"] = message
        fast_data["analysis_warning"] = message
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        prompt = """
세금계산서와 견적서를 함께 분석해 JSON만 반환하세요.
필드: site_name, buyer_biz_no, vendor_name, invoice_date, target_supply, total_tax, total_sum,
items 배열(raw_desc, name, qty, inc_vat, supply, account, is_a, dept).
account는 소모품비, 집기비품, 컴퓨터소프트웨어 중 하나만 사용하세요.
items[].name은 ERP 입력용 품목명으로 짧게 정리하세요. 브랜드, 모델명, 옵션, 상품코드, 대괄호/괄호 문구를 그대로 쓰지 마세요.
예: "[Canon] PIXMA TS3690 잉크젯복합기 (잉크포함) -1148112" -> name "잉크젯복합기", raw_desc는 원문 유지.
부서는 알 수 없으면 빈 문자열로 두세요.
"""
        model = genai.GenerativeModel("gemini-2.5-flash", generation_config={"response_mime_type": "application/json"})
        files = [genai.upload_file(tax_path), genai.upload_file(quote_path)]
        try:
            response = model.generate_content([prompt, f"기본 파싱값: {json.dumps(fast_data, ensure_ascii=False)}"] + files)
            parsed = json.loads(response.text)
        finally:
            for file in files:
                try:
                    file.delete()
                except Exception:
                    pass
        if isinstance(parsed, dict):
            parsed["analysis_source"] = "gemini"
            parsed["analysis_ai_attempted"] = True
            parsed["analysis_ai_error"] = ""
            if parsed.get("vendor_name"):
                parsed["vendor_name"] = _strip_vendor_name(parsed.get("vendor_name"))
            return parsed
    except Exception as exc:
        message = f"AI analysis failed, using fast parse: {exc}"
        fast_data["analysis_ai_error"] = message
        fast_data["analysis_warning"] = message
    return None


def analyze_purchase_documents(invoice: dict[str, Any]) -> dict[str, Any]:
    raw = dict(invoice.get("raw") or {})
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    existing = {**raw, **data}
    for key in ("target_supply", "total_supply", "supply_amount", "total_tax", "tax", "tax_amount", "total_sum", "total_amount", "amount", "order_no"):
        if not existing.get(key) and invoice.get(key):
            existing[key] = invoice.get(key)
    tax_path = str(invoice.get("pdf_path") or existing.get("pdf_path") or "")
    quote_path = str(existing.get("quote_path") or existing.get("quote_pdf_path") or "")
    if not tax_path or not Path(tax_path).exists():
        raise RuntimeError("세금계산서 PDF 파일을 찾지 못했습니다.")
    if not quote_path or not Path(quote_path).exists():
        raise RuntimeError("구매 분석을 위해 견적서 PDF를 먼저 첨부해야 합니다.")
    fast_data = _fast_parse(tax_path, quote_path, existing)
    fast_unknown = [value for value in list(fast_data.get("analysis_unknown_items") or []) if str(value).strip()]
    fast_data["analysis_ai_attempted"] = bool(fast_unknown)
    ai_data = _ai_parse(tax_path, quote_path, fast_data) if fast_unknown else None
    result = {**fast_data, **(ai_data or {})}
    if ai_data:
        prepared_items, unknown = _process_items_with_db(list(result.get("items") or []), _load_dictionary_rows())
        result["items"] = _normalize_items(prepared_items, _to_int(result.get("target_supply")))
        if unknown:
            merged_unknown = list(result.get("analysis_unknown_items") or [])
            result["analysis_unknown_items"] = sorted({str(value) for value in merged_unknown + unknown if value})
    else:
        result["items"] = _normalize_items(list(fast_data.get("items") or []), _to_int(fast_data.get("target_supply")))
        result["analysis_source"] = "learned_fast_parse" if not fast_unknown else "fast_parse"
        result["analysis_unknown_items"] = fast_unknown
    result["analysis_ai_used"] = bool(ai_data)
    result["analysis_ai_attempted"] = bool(fast_unknown)
    result["vendor_name"] = _strip_vendor_name(result.get("vendor_name"))
    result["quote_path"] = quote_path
    result["quote_pdf_path"] = quote_path
    result["purchase_analysis_ready"] = True
    approval_paths = existing.get("approval_pdf_paths") if isinstance(existing.get("approval_pdf_paths"), list) else []
    result["approval_pdf_paths"] = approval_paths
    result["erp_ready"] = bool(result.get("items"))
    return result
