from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from .config import PROJECT_ROOT, settings
from .invoice_db import add_invoice_log, get_invoice, update_invoice_json

Progress = Callable[[str, int, str], None]


OUTPUT_DOCS: dict[str, list[dict[str, Any]]] = {
    "purchase": [
        {"key": "erp_voucher", "label": "전표", "filename": "01_전표.pdf", "required": True},
        {"key": "tax_invoice", "label": "세금계산서", "filename": "02_세금계산서.pdf", "required": True},
        {"key": "approval_docs", "label": "전자결재 품의", "filename": "03_전자결재품의.pdf", "required": True},
        {"key": "expense_report", "label": "현금출금결의서", "filename": "04_현금출금결의서.pdf", "required": True},
    ],
    "regular": [
        {"key": "erp_voucher", "label": "전표", "filename": "01_전표.pdf", "required": True},
        {"key": "tax_invoice", "label": "세금계산서", "filename": "02_세금계산서.pdf", "required": True},
    ],
}

STATUS_LABELS = {
    "exists": "있음",
    "missing": "누락",
    "generate_needed": "생성필요",
    "failed": "실패",
}

EXPENSE_FOOTER_MAP = {
    "DAESEUNG": "DSSP-CO2-09 Rev.4('13. 01. 07)                   ㈜대승                            (200X143)",
    "DSJM": "DSSP-CO2-09 Rev.4('13. 01. 07)               대승정밀㈜                            (200X143)",
    "ILGANG": "DSSP-CO2-09 Rev.4('13. 01. 07)                   ㈜일강                            (200X143)",
}

CS_EXPENSE_TEMPLATE_PATH = Path(
    r"Y:\관리총괄\경영지원본부\전산팀\2파트\2파트 개인 자료\김기창\현금출금결의서 양식\양식_현금출금정산서.xlsx"
)
EXPENSE_EXCEL_EXPORT_TIMEOUT = int(os.environ.get("EXPENSE_REPORT_EXCEL_TIMEOUT", "30") or "30")
EXPENSE_APPDATA_ROOT = Path(os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming"))
EXPENSE_APPDATA_DIR = Path(os.getenv("EXPENSE_REPORT_APPDATA_DIR") or EXPENSE_APPDATA_ROOT / "AccountingWeb")
EXPENSE_APPDATA_TEMPLATE = Path(os.getenv("EXPENSE_REPORT_TEMPLATE_PATH") or EXPENSE_APPDATA_ROOT / "양식_현금출금정산서.xlsx")
EXPENSE_APPDATA_WORK_DIR = EXPENSE_APPDATA_DIR / "expense_reports"


def _invoice_data(invoice: dict[str, Any]) -> dict[str, Any]:
    raw = invoice.get("raw") if isinstance(invoice.get("raw"), dict) else {}
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    merged: dict[str, Any] = {}
    merged.update(raw)
    merged.update(data)
    if isinstance(invoice.get("data"), dict):
        merged.update(invoice["data"])
    merged.update(invoice)
    return merged


def _clean_path(value: Any) -> str:
    text = str(value or "").strip().strip('"')
    return text if text else ""


def _path_exists(path: str) -> bool:
    return bool(path) and Path(path).exists()


def _status(status: str, message: str = "") -> tuple[str, str]:
    return status, message or STATUS_LABELS.get(status, status)


def _expense_report_path(invoice_id: int) -> Path:
    return settings.erp_db_dir / "expense_reports" / str(invoice_id) / "04_현금출금결의서.pdf"


def _output_set_dir(invoice_id: int, mode: str) -> Path:
    return settings.erp_db_dir / "output_sets" / mode / str(invoice_id)


def _sorted_existing(paths: list[Path]) -> list[str]:
    existing: list[Path] = []
    for path in paths:
        try:
            if path.exists() and path.is_file():
                existing.append(path)
        except OSError:
            continue
    existing.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return [str(path) for path in existing]


def _voucher_candidate_paths(invoice_id: int) -> list[str]:
    if not invoice_id:
        return []
    candidates: list[Path] = []
    search_patterns = [
        settings.erp_db_dir / "erp_vouchers" / str(invoice_id) / "*.pdf",
        settings.erp_output_dir / f"erp_voucher_*_{invoice_id}.pdf",
        settings.erp_output_dir / f"*voucher*{invoice_id}*.pdf",
        settings.erp_output_dir / f"*전표*{invoice_id}*.pdf",
        settings.erp_db_dir / "output_sets" / "purchase" / str(invoice_id) / "01_*.pdf",
        settings.erp_db_dir / "output_sets" / "regular" / str(invoice_id) / "01_*.pdf",
    ]
    for pattern in search_patterns:
        try:
            candidates.extend(pattern.parent.glob(pattern.name))
        except OSError:
            continue
    return list(dict.fromkeys(_sorted_existing(candidates)))


def _source_paths(invoice: dict[str, Any], key: str) -> list[str]:
    data = _invoice_data(invoice)
    invoice_id = int(invoice.get("id") or 0)
    if key == "erp_voucher":
        return list(dict.fromkeys([
            _clean_path(data.get("erp_pdf_path")),
            _clean_path(data.get("erp_voucher_pdf_path")),
            _clean_path(data.get("voucher_pdf_path")),
            *_voucher_candidate_paths(invoice_id),
        ]))
    if key == "tax_invoice":
        return [_clean_path(invoice.get("pdf_path") or data.get("pdf_path"))]
    if key == "approval_docs":
        paths = data.get("approval_pdf_paths")
        if isinstance(paths, list):
            return [_clean_path(path) for path in paths]
        return [_clean_path(data.get("approval_pdf_path"))]
    if key == "expense_report":
        return [
            _clean_path(data.get("expense_report_pdf_path")),
            str(_expense_report_path(invoice_id)),
        ]
    return []


def build_output_set_status(invoice: dict[str, Any], *, persist: bool = False) -> dict[str, Any]:
    invoice_id = int(invoice.get("id") or 0)
    mode = "purchase" if str(invoice.get("invoice_type") or "").lower() == "purchase" else "regular"
    data = _invoice_data(invoice)
    output_docs_data = data.get("output_docs") if isinstance(data.get("output_docs"), dict) else {}
    prior_docs = output_docs_data.get("docs") if isinstance(output_docs_data.get("docs"), list) else []
    prior_by_key = {str(doc.get("key")): doc for doc in prior_docs if isinstance(doc, dict)}

    docs: list[dict[str, Any]] = []
    for spec in OUTPUT_DOCS[mode]:
        key = str(spec["key"])
        paths = [path for path in _source_paths(invoice, key) if path]
        existing = [path for path in paths if _path_exists(path)]
        prior = prior_by_key.get(key, {})
        status = "exists" if existing else "missing"
        message = ""
        if key == "expense_report" and not existing:
            prior_status = str(prior.get("status") or "")
            if prior_status == "failed":
                status = "failed"
                message = str(prior.get("message") or prior.get("status_label") or "현금출금결의서 생성 실패")
            else:
                status = "generate_needed"
                message = "출력 세트 생성 시 자동 생성"
        elif not existing:
            message = "파일 없음"
        status, status_label = _status(status, message)
        docs.append(
            {
                "key": key,
                "label": spec["label"],
                "filename": spec["filename"],
                "required": bool(spec.get("required", True)),
                "status": status,
                "status_label": status_label,
                "path": existing[0] if existing else (paths[0] if paths else ""),
                "paths": existing if existing else paths,
                "message": message,
            }
        )

    missing_blockers = [
        doc
        for doc in docs
        if doc["required"] and doc["status"] not in {"exists", "generate_needed"}
    ]
    ready = all(doc["status"] == "exists" for doc in docs if doc["required"])
    can_output = not missing_blockers
    result = {
        "invoice_id": invoice_id,
        "mode": mode,
        "docs": docs,
        "ready": ready,
        "can_output": can_output,
        "missing": [doc for doc in docs if doc["required"] and doc["status"] != "exists"],
        "blockers": missing_blockers,
        "output_dir": str(_output_set_dir(invoice_id, mode)),
    }
    if persist and invoice_id:
        updates: dict[str, Any] = {"output_docs": result}
        voucher_doc = next((doc for doc in docs if doc["key"] == "erp_voucher" and doc["status"] == "exists"), None)
        if voucher_doc:
            voucher_path = str(voucher_doc.get("path") or "").strip()
            stored_paths = [
                _clean_path(data.get("erp_pdf_path")),
                _clean_path(data.get("erp_voucher_pdf_path")),
                _clean_path(data.get("voucher_pdf_path")),
            ]
            if voucher_path and voucher_path not in stored_paths:
                updates.update(
                    {
                        "erp_pdf_path": voucher_path,
                        "erp_voucher_pdf_path": voucher_path,
                        "voucher_pdf_path": voucher_path,
                    }
                )
        update_invoice_json(invoice_id, updates)
    return result


def _safe_filename_part(text: Any, fallback: str = "invoice") -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "_", str(text or "").strip())
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:80] or fallback


def _int_value(value: Any) -> int:
    try:
        if isinstance(value, (int, float)):
            return int(value)
        text = re.sub(r"[^0-9-]", "", str(value or ""))
        return int(text) if text not in {"", "-"} else 0
    except Exception:
        return 0


def _expense_items(invoice: dict[str, Any]) -> list[dict[str, Any]]:
    data = _invoice_data(invoice)
    source_items = data.get("items") if isinstance(data.get("items"), list) else []
    items: list[dict[str, Any]] = []
    for source in source_items:
        if not isinstance(source, dict):
            continue
        row = dict(source)
        row["qty"] = max(1, _int_value(row.get("qty") or 1))
        row["supply"] = _int_value(row.get("supply"))
        row["inc_vat"] = _int_value(row.get("inc_vat") or row.get("amount") or row.get("total"))
        if not row["inc_vat"] and row["supply"]:
            row["inc_vat"] = round(row["supply"] * 1.1)
        row["account"] = str(row.get("account") or "소모품비").strip() or "소모품비"
        row["name"] = str(row.get("name") or row.get("item_name") or row.get("raw_desc") or "품목").strip() or "품목"
        items.append(row)
    return items


def _expense_account(account: Any) -> str:
    raw = str(account or "소모품비").strip()
    aliases = {
        "전산비품": "집기비품",
        "비품": "집기비품",
        "소프트웨어": "컴퓨터소프트웨어",
        "컴퓨터SW": "컴퓨터소프트웨어",
        "소모품": "소모품비",
    }
    normalized = aliases.get(raw, raw)
    return normalized if normalized in {"집기비품", "컴퓨터소프트웨어", "소모품비"} else "소모품비"


def _extract_model_name(item: dict[str, Any]) -> str:
    pattern = r"\b[A-Z]{1,6}[A-Z0-9-]*\d[A-Z0-9-]*\b"
    for source in (str(item.get("raw_desc") or ""), str(item.get("name") or "")):
        matches = [match for match in re.findall(pattern, source.upper()) if len(match) >= 4]
        if matches:
            return max(matches, key=len)
    return ""


def _clean_expense_item_name(value: Any) -> str:
    text = str(value or "").strip() or "품목"
    text = re.sub(r"\s+", " ", text)
    return text


def _aggregate_expense_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in items:
        name = _clean_expense_item_name(item.get("name") or item.get("item_name") or item.get("raw_desc"))
        key = name.casefold()
        if key not in grouped:
            grouped[key] = {
                "name": name,
                "qty": 0,
                "inc_vat": 0,
                "raw_desc": item.get("raw_desc") or "",
            }
            order.append(key)
        grouped[key]["qty"] += max(1, _int_value(item.get("qty") or 1))
        grouped[key]["inc_vat"] += _int_value(item.get("inc_vat"))
        if not grouped[key].get("raw_desc") and item.get("raw_desc"):
            grouped[key]["raw_desc"] = item.get("raw_desc")
    return [grouped[key] for key in order]


def _build_expense_report_text(items: list[dict[str, Any]], total: int) -> tuple[str, str]:
    account_order = ["집기비품", "컴퓨터소프트웨어", "소모품비"]
    grouped: dict[str, list[dict[str, Any]]] = {account: [] for account in account_order}
    for item in items:
        grouped[_expense_account(item.get("account"))].append(item)

    dominant_account = max(
        account_order,
        key=lambda account: (
            len(grouped.get(account, [])),
            sum(_int_value(item.get("inc_vat")) for item in grouped.get(account, [])),
        ),
    )
    header_map = {
        "소모품비": "소모품 구매",
        "집기비품": "집기비품 구매",
        "컴퓨터소프트웨어": "컴퓨터소프트웨어 구매",
    }

    lines = ["* 내 용 *"]
    section_no = 1
    for account in account_order:
        account_items = grouped.get(account, [])
        if not account_items:
            continue
        lines.append(f"{section_no}. {header_map.get(account, '구매')}")
        if account == "소모품비":
            top_item = max(account_items, key=lambda item: _int_value(item.get("inc_vat")))
            suffix = f" 외 {len(account_items) - 1}건" if len(account_items) > 1 else ""
            group_total = sum(_int_value(item.get("inc_vat")) for item in account_items)
            lines.append(f"   └ {top_item.get('name', '품목')}{suffix} : {group_total:,}원")
        else:
            for item in _aggregate_expense_items(account_items):
                name = _clean_expense_item_name(item.get("name") or "품목")
                model = _extract_model_name(item)
                qty = max(1, _int_value(item.get("qty") or 1))
                amount = _int_value(item.get("inc_vat"))
                item_text = f"{name}({model})" if model and model not in name.upper() else name
                lines.append(f"   └ {item_text} {qty}EA : {amount:,}원")
        section_no += 1

    if section_no == 1:
        lines.append("1. 구매")
        for item in items:
            qty = max(1, _int_value(item.get("qty") or 1))
            lines.append(f"   └ {item.get('name', '품목')} {qty}EA : {_int_value(item.get('inc_vat')):,}원")
        section_no = 2

    lines.append(f"{section_no}. 총합 : {total:,}원")
    return dominant_account, "\n".join(lines)


def _expense_footer(site_name: str) -> str:
    if "일강" in site_name:
        return EXPENSE_FOOTER_MAP["ILGANG"]
    if "정밀" in site_name or re.search(r"\bP[1-4]\b", site_name, re.IGNORECASE):
        return EXPENSE_FOOTER_MAP["DSJM"]
    return EXPENSE_FOOTER_MAP["DAESEUNG"]


def _template_seed_candidates() -> list[Path]:
    return [
        settings.erp_db_dir / "templates" / "expense_template.xlsx",
        settings.erp_db_dir / "templates" / "양식_현금출금정산서_공통.xlsx",
        settings.erp_db_dir / "templates" / "양식_현금출금정산서.xlsx",
        PROJECT_ROOT / "support" / "expense_template.xlsx",
        PROJECT_ROOT / "support" / "양식_현금출금정산서_공통.xlsx",
        PROJECT_ROOT / "support" / "양식_현금출금정산서.xlsx",
    ]


def _appdata_template_candidates() -> list[Path]:
    candidates = [EXPENSE_APPDATA_TEMPLATE]
    if not os.getenv("EXPENSE_REPORT_TEMPLATE_PATH"):
        candidates.extend(
            [
                EXPENSE_APPDATA_ROOT / "양식_현금출금정산서.xlsx",
                EXPENSE_APPDATA_ROOT / "expense_template.xlsx",
                EXPENSE_APPDATA_DIR / "templates" / "양식_현금출금정산서.xlsx",
                EXPENSE_APPDATA_DIR / "templates" / "expense_template.xlsx",
            ]
        )
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _ensure_appdata_expense_template() -> Path | None:
    try:
        existing = next((path for path in _appdata_template_candidates() if _is_readable_template(path)), None)
        if existing:
            return existing
    except OSError:
        pass

    source = next((path for path in _template_seed_candidates() if _is_readable_template(path)), None)
    if not source:
        return None
    try:
        EXPENSE_APPDATA_TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, EXPENSE_APPDATA_TEMPLATE)
        return EXPENSE_APPDATA_TEMPLATE if _is_readable_template(EXPENSE_APPDATA_TEMPLATE) else None
    except OSError:
        return None


def _template_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("EXPENSE_REPORT_TEMPLATE_PATH", "CASH_EXPENSE_TEMPLATE_PATH"):
        env_path = os.environ.get(env_name)
        if env_path:
            candidates.append(Path(env_path))
    appdata_template = _ensure_appdata_expense_template()
    if appdata_template:
        candidates.append(appdata_template)
    candidates.extend([
        CS_EXPENSE_TEMPLATE_PATH,
        *_template_seed_candidates(),
        settings.erp_db_dir / "templates" / "expense_template.xlsx",
        settings.erp_db_dir / "templates" / "양식_현금출금정산서_공통.xlsx",
        settings.erp_db_dir / "templates" / "양식_현금출금정산서.xlsx",
        PROJECT_ROOT / "support" / "expense_template.xlsx",
        PROJECT_ROOT / "support" / "양식_현금출금정산서_공통.xlsx",
        PROJECT_ROOT / "support" / "양식_현금출금정산서.xlsx",
    ])
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def _is_readable_template(path: Path) -> bool:
    try:
        if not path.exists() or not path.is_file():
            return False
        with path.open("rb") as handle:
            handle.read(1)
        return True
    except OSError:
        return False


def _excel_process_ids() -> set[int]:
    try:
        import psutil

        return {
            int(proc.info["pid"])
            for proc in psutil.process_iter(["pid", "name"])
            if str(proc.info.get("name") or "").lower() == "excel.exe"
        }
    except Exception:
        return set()


def _kill_new_excel_processes(existing_pids: set[int]) -> None:
    try:
        import psutil

        for proc in psutil.process_iter(["pid", "name"]):
            pid = int(proc.info.get("pid") or 0)
            if pid in existing_pids:
                continue
            if str(proc.info.get("name") or "").lower() == "excel.exe":
                try:
                    proc.kill()
                except Exception:
                    pass
    except Exception:
        return


def _export_expense_report_with_excel(work_xlsx: Path, output_pdf: Path, payload: dict[str, str]) -> None:
    payload_path = output_pdf.parent / "현금출금결의서_payload.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    helper = Path(__file__).with_name("expense_excel_export.py")
    if not helper.exists():
        raise RuntimeError(f"현금출금결의서 Excel 변환 헬퍼가 없습니다: {helper}")

    before_excel = _excel_process_ids()
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [sys.executable, str(helper), str(work_xlsx), str(output_pdf), str(payload_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=EXPENSE_EXCEL_EXPORT_TIMEOUT,
            creationflags=creationflags,
        )
    except subprocess.TimeoutExpired as exc:
        _kill_new_excel_processes(before_excel)
        raise RuntimeError(
            f"현금출금결의서 Excel PDF 변환 시간이 초과되었습니다({EXPENSE_EXCEL_EXPORT_TIMEOUT}초)."
        ) from exc
    finally:
        try:
            payload_path.unlink(missing_ok=True)
        except OSError:
            pass

    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"현금출금결의서 Excel PDF 변환 실패: {message or completed.returncode}")


def _expense_payload(invoice: dict[str, Any]) -> dict[str, str]:
    data = _invoice_data(invoice)
    site = str(data.get("site_name") or invoice.get("site_name") or "").strip()
    items = _expense_items(invoice)
    total = _int_value(
        data.get("total_sum")
        or data.get("total")
        or data.get("amount")
        or invoice.get("total_sum")
        or invoice.get("total")
        or invoice.get("amount")
    )
    if not total:
        total = sum(_int_value(item.get("inc_vat")) for item in items)
    dominant_account, body = _build_expense_report_text(items, total)
    title_map = {
        "소모품비": "소모품 구매 건",
        "집기비품": "집기비품 구매 건",
        "컴퓨터소프트웨어": "컴퓨터소프트웨어 구매 건",
    }
    title = f"{title_map.get(dominant_account, '구매 건')}({site or '사업장미상'})"
    return {
        "date": time.strftime("%Y. %m. %d"),
        "dept": "전산팀",
        "author": str(data.get("processor") or invoice.get("processor") or "").strip(),
        "title": title,
        "basis": "품의 결재본",
        "amount": f"￦{total:,}",
        "body": body,
        "footer": _expense_footer(site),
    }


def _insert_pdf_textbox(page: Any, rect: Any, text: Any, fontname: str, fontsize: float = 10, align: int = 0) -> None:
    page.insert_textbox(rect, str(text or ""), fontname=fontname, fontsize=fontsize, color=(0, 0, 0), align=align)


def _generate_expense_report_pdf_plain(output_pdf: Path, payload: dict[str, str], note: str = "") -> str:
    import fitz

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    if output_pdf.exists():
        output_pdf.unlink()

    doc = fitz.open()
    try:
        page = doc.new_page(width=595, height=842)
        fontname = "korea"

        def draw_cell(
            x0: float,
            y0: float,
            x1: float,
            y1: float,
            text: Any = "",
            *,
            size: float = 9,
            align: int = 1,
        ) -> None:
            page.draw_rect(fitz.Rect(x0, y0, x1, y1), color=(0, 0, 0), width=0.45)
            if text not in {None, ""}:
                _insert_pdf_textbox(page, fitz.Rect(x0 + 3, y0 + 4, x1 - 3, y1 - 3), text, fontname, size, align)

        left = 50
        right = 545
        top = 58
        page.draw_rect(fitz.Rect(left, top, right, 700), color=(0, 0, 0), width=0.9)

        _insert_pdf_textbox(page, fitz.Rect(70, 78, 270, 106), "현금출금결의서(정산서)", fontname, 18, 0)
        page.draw_line(fitz.Point(72, 104), fitz.Point(264, 104), color=(0, 0, 0), width=0.6)

        # Approval area follows the old CS Excel form closely enough when Excel COM is unavailable.
        ax0, ay0, ax1, ay1 = 315, 58, 545, 168
        page.draw_rect(fitz.Rect(ax0, ay0, ax1, ay1 + 110), color=(0, 0, 0), width=0.45)
        draw_cell(ax0, ay0, ax0 + 28, ay1, "작\n성\n부\n서", size=8)
        col_w = (ax1 - ax0 - 28) / 5
        for idx, label in enumerate(["작성", "검토", "검토", "검토", "승인"]):
            x0 = ax0 + 28 + idx * col_w
            draw_cell(x0, ay0, x0 + col_w, ay0 + 24, label, size=8)
            draw_cell(x0, ay0 + 24, x0 + col_w, ay1, "", size=8)
        draw_cell(ax0, ay1, ax0 + 28, ay1 + 110, "재\n경\n부\n서", size=8)
        for idx, label in enumerate(["작성", "검토", "검토", "검토", "승인"]):
            x0 = ax0 + 28 + idx * col_w
            draw_cell(x0, ay1, x0 + col_w, ay1 + 24, label, size=8)
            draw_cell(x0, ay1 + 24, x0 + col_w, ay1 + 110, "", size=8)

        y = 118
        label_w = 84
        value_w = 190
        row_h = 28
        draw_cell(left, y, left + label_w, y + row_h, "작성일자", size=9)
        draw_cell(left + label_w, y, ax0, y + row_h, payload.get("date", ""), size=9)
        y += row_h
        draw_cell(left, y, left + label_w, y + row_h, "청구부서", size=9)
        draw_cell(left + label_w, y, left + label_w + 90, y + row_h, payload.get("dept", ""), size=9)
        draw_cell(left + label_w + 90, y, left + label_w + 145, y + row_h, "작성자", size=9)
        draw_cell(left + label_w + 145, y, ax0, y + row_h, payload.get("author", ""), size=9)
        y += row_h
        draw_cell(left, y, left + label_w, y + row_h, "제    목", size=9)
        draw_cell(left + label_w, y, ax0, y + row_h, payload.get("title", ""), size=9, align=0)
        y += row_h
        draw_cell(left, y, left + label_w, y + row_h, "근    거", size=9)
        draw_cell(left + label_w, y, ax0, y + row_h, payload.get("basis", ""), size=9, align=0)
        y += row_h
        draw_cell(left, y, left + 42, y + 50, "청\n구\n금\n액", size=8)
        draw_cell(left + 42, y, left + value_w, y + 50, payload.get("amount", ""), size=10)
        draw_cell(left + value_w, y, left + value_w + 55, y + 25, "사후정산요", size=8)
        draw_cell(left + value_w + 55, y, ax0, y + 25, "정산\n금액", size=8)
        draw_cell(ax0, y, right, y + 25, "지  출  처", size=8)
        draw_cell(left + value_w, y + 25, left + value_w + 55, y + 50, "사후정산불요", size=8)
        draw_cell(left + value_w + 55, y + 25, ax0, y + 50, "", size=8)
        draw_cell(ax0, y + 25, right, y + 50, "출금시기", size=8)
        y += 50

        body_top = y
        body_bottom = 650
        draw_cell(left, body_top, left + 32, body_bottom, "내\n\n용", size=9)
        page.draw_rect(fitz.Rect(left + 32, body_top, right, body_bottom), color=(0, 0, 0), width=0.45)
        _insert_pdf_textbox(
            page,
            fitz.Rect(left + 50, body_top + 12, right - 15, body_bottom - 12),
            payload.get("body", ""),
            fontname,
            10.5,
            0,
        )

        _insert_pdf_textbox(page, fitz.Rect(left, 662, right, 690), payload.get("footer", ""), fontname, 8, 1)
        if note:
            doc.set_metadata({"subject": f"fallback: {note[:180]}"})
        doc.save(str(output_pdf))
    finally:
        doc.close()

    if not output_pdf.exists() or output_pdf.stat().st_size <= 0:
        raise RuntimeError("현금출금결의서 WEB PDF 생성 결과 파일이 생성되지 않았습니다.")
    return str(output_pdf)


def generate_expense_report_pdf(invoice: dict[str, Any], *, force: bool = False) -> str:
    invoice_id = int(invoice.get("id") or 0)
    output_pdf = _expense_report_path(invoice_id)
    if output_pdf.exists() and not force:
        return str(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    if output_pdf.exists() and force:
        output_pdf.unlink()
    payload = _expense_payload(invoice)
    template = next((path for path in _template_candidates() if _is_readable_template(path)), None)
    if not template:
        raise RuntimeError(
            r"현금출금결의서 Excel 양식 파일을 찾지 못했습니다. "
            r"%APPDATA%\양식_현금출금정산서.xlsx 또는 C:\ERP_DB\templates에 양식을 배치해 주세요."
        )

    work_xlsx = output_pdf.parent / "현금출금결의서_작업.xlsx"
    shutil.copy2(template, work_xlsx)
    excel_error: Exception | None = None
    try:
        _export_expense_report_with_excel(work_xlsx, output_pdf, payload)
    except Exception as exc:
        excel_error = exc
    if not output_pdf.exists() or output_pdf.stat().st_size <= 0:
        if excel_error:
            raise RuntimeError(f"현금출금결의서 Excel PDF 변환 실패: {excel_error}") from excel_error
        raise RuntimeError("현금출금결의서 PDF 변환 결과 파일이 생성되지 않았습니다.")
    return str(output_pdf)


def _generate_expense_report_pdf_appdata(invoice: dict[str, Any], *, force: bool = False) -> str:
    invoice_id = int(invoice.get("id") or 0)
    output_pdf = _expense_report_path(invoice_id)
    if output_pdf.exists() and not force:
        return str(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    if output_pdf.exists() and force:
        output_pdf.unlink()

    payload = _expense_payload(invoice)
    template = next((path for path in _template_candidates() if _is_readable_template(path)), None)
    if not template:
        raise RuntimeError(
            r"현금출금결의서 Excel 양식 파일을 찾지 못했습니다. "
            r"%APPDATA%\양식_현금출금정산서.xlsx 또는 C:\ERP_DB\templates에 양식을 배치해 주세요."
        )

    appdata_work_dir = EXPENSE_APPDATA_WORK_DIR / str(invoice_id)
    appdata_work_dir.mkdir(parents=True, exist_ok=True)
    work_xlsx = appdata_work_dir / "expense_report_work.xlsx"
    temp_pdf = appdata_work_dir / "04_expense_report.pdf"
    for path in (work_xlsx, temp_pdf):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    shutil.copy2(template, work_xlsx)
    excel_error: Exception | None = None
    try:
        _export_expense_report_with_excel(work_xlsx, temp_pdf, payload)
    except Exception as exc:
        excel_error = exc

    if temp_pdf.exists() and temp_pdf.stat().st_size > 0:
        try:
            shutil.move(str(temp_pdf), str(output_pdf))
        except OSError:
            shutil.copy2(temp_pdf, output_pdf)

    if not output_pdf.exists() or output_pdf.stat().st_size <= 0:
        if excel_error:
            raise RuntimeError(f"현금출금결의서 Excel PDF 변환 실패: {excel_error}") from excel_error
        raise RuntimeError("현금출금결의서 PDF 변환 결과 파일이 생성되지 않았습니다.")
    return str(output_pdf)


def generate_expense_report_pdf(invoice: dict[str, Any], *, force: bool = False) -> str:
    return _generate_expense_report_pdf_appdata(invoice, force=force)


def merge_pdfs(paths: list[str], output_path: str | Path) -> str:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    import fitz

    merged = fitz.open()
    try:
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists():
                raise RuntimeError(f"병합 대상 PDF가 없습니다: {path}")
            with fitz.open(str(path)) as source:
                merged.insert_pdf(source)
        merged.save(str(output))
    finally:
        merged.close()
    return str(output)


def _copy_or_merge_doc(doc: dict[str, Any], target_dir: Path) -> str:
    target = target_dir / str(doc["filename"])
    paths = [path for path in doc.get("paths") or [] if _path_exists(str(path))]
    if not paths:
        raise RuntimeError(f"{doc['label']} 파일이 없습니다.")
    target.parent.mkdir(parents=True, exist_ok=True)
    if len(paths) == 1:
        source = Path(paths[0])
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
    else:
        merge_pdfs([str(path) for path in paths], target)
    return str(target)


def prepare_output_documents(invoice: dict[str, Any]) -> dict[str, Any]:
    invoice_id = int(invoice.get("id") or 0)
    status = build_output_set_status(invoice)
    if not status["can_output"]:
        missing = ", ".join(doc["label"] for doc in status["blockers"])
        raise RuntimeError(f"필수 문서가 없습니다: {missing}")

    expense_doc = next((doc for doc in status["docs"] if doc["key"] == "expense_report"), None)
    if expense_doc and expense_doc["status"] == "generate_needed":
        try:
            path = generate_expense_report_pdf(invoice)
            update_invoice_json(
                invoice_id,
                {"expense_report_pdf_path": path},
                message=f"현금출금결의서 PDF 생성: {path}",
            )
        except Exception as exc:
            refreshed = build_output_set_status(invoice)
            for doc in refreshed["docs"]:
                if doc["key"] == "expense_report":
                    doc["status"] = "failed"
                    doc["status_label"] = "실패"
                    doc["message"] = str(exc)
            update_invoice_json(invoice_id, {"output_docs": refreshed})
            raise RuntimeError(f"현금출금결의서 생성 실패: {exc}") from exc

    invoice = get_invoice(invoice_id) or invoice
    status = build_output_set_status(invoice)
    if not status["can_output"]:
        missing = ", ".join(doc["label"] for doc in status["blockers"])
        raise RuntimeError(f"필수 문서가 없습니다: {missing}")

    target_dir = _output_set_dir(invoice_id, status["mode"])
    target_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for doc in status["docs"]:
        files.append(_copy_or_merge_doc(doc, target_dir))
    final_status = build_output_set_status(get_invoice(invoice_id) or invoice)
    final_status["individual_files"] = files
    final_status["output_dir"] = str(target_dir)
    update_invoice_json(invoice_id, {"output_docs": final_status, "output_set_dir": str(target_dir)})
    return final_status


def _merged_filename(invoice: dict[str, Any], mode: str) -> str:
    data = _invoice_data(invoice)
    vendor = _safe_filename_part(data.get("vendor_name") or invoice.get("vendor_name") or "거래처")
    site = _safe_filename_part(data.get("site_name") or invoice.get("site_name") or mode)
    return f"{int(invoice.get('id') or 0):04d}_{site}_{vendor}_전표세트.pdf"


def _print_pdf(path: str, printer_name: str) -> None:
    if not printer_name:
        raise RuntimeError("출력 프린터 매핑이 없습니다.")
    if not _path_exists(path):
        raise RuntimeError(f"출력 대상 PDF가 없습니다: {path}")
    import win32api

    win32api.ShellExecute(0, "printto", str(Path(path)), f'"{printer_name}"', ".", 0)


def run_output_set_job(
    invoice_ids: list[int],
    *,
    action: str,
    printer_name: str = "",
    job_id: str = "",
    progress: Progress | None = None,
) -> dict[str, Any]:
    if action not in {"merged_pdf", "individual_pdf", "print_individual"}:
        raise RuntimeError(f"지원하지 않는 출력 방식입니다: {action}")
    if not invoice_ids:
        raise RuntimeError("출력 세트를 만들 건을 선택해야 합니다.")

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    total = len(invoice_ids)
    for index, invoice_id in enumerate(invoice_ids, start=1):
        base = 10 + int(index / max(total, 1) * 70)
        try:
            invoice = get_invoice(int(invoice_id))
            if not invoice:
                raise RuntimeError(f"계산서 건을 찾지 못했습니다: #{invoice_id}")
            if progress:
                progress("printing", min(95, base), f"문서 세트 준비: #{invoice_id}")
            status = prepare_output_documents(invoice)
            files = [str(path) for path in status.get("individual_files") or []]
            merged_path = ""
            if action == "merged_pdf":
                invoice = get_invoice(int(invoice_id)) or invoice
                merged_path = str(Path(status["output_dir"]) / _merged_filename(invoice, status["mode"]))
                merge_pdfs(files, merged_path)
                update_invoice_json(
                    int(invoice_id),
                    {"output_set_merged_pdf_path": merged_path},
                    message=f"통합본 PDF 저장: {merged_path}",
                )
                add_invoice_log(int(invoice_id), f"문서 세트 통합본 PDF 저장 완료: {merged_path}", job_id=job_id)
            elif action == "individual_pdf":
                add_invoice_log(int(invoice_id), f"문서 세트 개별 PDF 저장 완료: {status['output_dir']}", job_id=job_id)
            else:
                if not printer_name:
                    raise RuntimeError("개별 출력용 프린터가 선택되지 않았습니다.")
                for file_path in files:
                    _print_pdf(file_path, printer_name)
                    time.sleep(0.8)
                add_invoice_log(int(invoice_id), f"문서 세트 개별 출력 전송 완료: {printer_name}", job_id=job_id)
            results.append(
                {
                    "invoice_id": int(invoice_id),
                    "mode": status["mode"],
                    "output_dir": status["output_dir"],
                    "individual_files": files,
                    "merged_pdf_path": merged_path,
                }
            )
            if progress:
                progress("printing", min(98, base + 8), f"문서 세트 처리 완료: #{invoice_id}")
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            failures.append({"invoice_id": int(invoice_id), "error": message})
            add_invoice_log(int(invoice_id), f"문서 세트 처리 실패: {message}", level="error", job_id=job_id)
            if progress:
                progress("error", min(98, base + 8), f"문서 세트 처리 실패: #{invoice_id} / {message}")

    if failures:
        raise RuntimeError(f"문서 세트 처리 실패: 성공 {len(results)}건, 실패 {len(failures)}건")
    action_label = {
        "merged_pdf": "통합본 PDF 저장",
        "individual_pdf": "개별 PDF 저장",
        "print_individual": "개별 출력",
    }[action]
    return {
        "job_type": "output_set",
        "action": action,
        "results": results,
        "notification": f"문서 세트 {action_label} 완료: {len(results)}건",
    }
