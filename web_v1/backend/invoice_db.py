from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import settings


WAITING = "대기중"
PROCESSING = "처리중"
ERP_QUEUED = "ERP대기"
DONE = "처리완료"
ERROR = "오류"


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    settings.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.sqlite_db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def _columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    return {str(row["name"]) for row in cur.fetchall()}


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, ddl: str) -> None:
    if column_name not in _columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def init_db() -> None:
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dictionary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_text TEXT,
                corrected_name TEXT,
                is_asset BOOLEAN,
                account TEXT DEFAULT '',
                learned_at TIMESTAMP
            )
            """
        )
        _ensure_column(conn, "dictionary", "account", "account TEXT DEFAULT ''")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                pdf_path TEXT,
                json_data TEXT,
                status TEXT DEFAULT '대기중',
                processor TEXT DEFAULT '',
                received_at TIMESTAMP,
                processed_at TIMESTAMP
            )
            """
        )
        _ensure_column(conn, "invoices", "last_error", "last_error TEXT DEFAULT ''")
        _ensure_column(conn, "invoices", "erp_job_id", "erp_job_id TEXT DEFAULT ''")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER,
                job_id TEXT DEFAULT '',
                level TEXT DEFAULT 'info',
                message TEXT,
                created_at TIMESTAMP
            )
            """
        )
        _repair_invoice_types(conn)
        conn.commit()


def _clean_int(value: Any) -> int:
    try:
        if isinstance(value, (int, float)):
            return int(value)
        text = "".join(ch for ch in str(value or "") if ch.isdigit() or ch == "-")
        return int(text) if text not in {"", "-"} else 0
    except Exception:
        return 0


def normalize_processor(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parts = [part.strip() for part in text.split("-") if part.strip()]
    if len(parts) == 2 and parts[0] == parts[1]:
        return parts[0]
    return text


def _invoice_data(record: dict[str, Any]) -> dict[str, Any]:
    data = record.get("data")
    merged: dict[str, Any] = {}
    if isinstance(record, dict):
        merged.update(record)
    if isinstance(data, dict):
        merged.update(data)
    return merged


def _repair_purchase_amounts(raw: dict[str, Any], pdf_path: str = "") -> dict[str, Any]:
    data = _invoice_data(raw)
    target_supply = _clean_int(data.get("target_supply") or data.get("total_supply") or data.get("supply_amount"))
    total_tax = _clean_int(data.get("total_tax") or data.get("tax") or data.get("tax_amount"))
    total_sum = _clean_int(data.get("total_sum") or data.get("total_amount") or data.get("amount"))
    order_no = str(data.get("order_no") or data.get("purchase_order_no") or data.get("tax_order_no") or "").strip()
    if target_supply and total_tax and total_sum and order_no:
        return raw

    path = str(pdf_path or raw.get("pdf_path") or data.get("pdf_path") or "")
    if not path or not Path(path).exists():
        return raw

    try:
        from .purchase_analysis import _extract_amounts_from_tax, _extract_order_no_from_tax, _extract_pdf_text

        pdf_text = _extract_pdf_text(path)
        supply_from_pdf, tax_from_pdf, total_from_pdf = _extract_amounts_from_tax(pdf_text)
        order_no_from_pdf = _extract_order_no_from_tax(pdf_text)
    except Exception:
        return raw

    if not (supply_from_pdf or tax_from_pdf or total_from_pdf or order_no_from_pdf):
        return raw

    fixed = dict(raw)
    nested = fixed.get("data") if isinstance(fixed.get("data"), dict) else {}
    nested = dict(nested)

    order_no = order_no_from_pdf or order_no
    target_supply = supply_from_pdf or target_supply
    total_tax = tax_from_pdf or total_tax
    total_sum = total_from_pdf or total_sum
    if not target_supply and total_sum and total_tax:
        target_supply = max(0, total_sum - total_tax)
    if not total_tax and target_supply and total_sum:
        total_tax = max(0, total_sum - target_supply)
    if not total_sum and target_supply:
        total_sum = target_supply + total_tax

    repairs = {
        "target_supply": target_supply,
        "total_supply": target_supply,
        "supply_amount": target_supply,
        "total_tax": total_tax,
        "tax_amount": total_tax,
        "total_sum": total_sum,
        "total_amount": total_sum,
    }
    for key, value in repairs.items():
        if value and not _clean_int(fixed.get(key)):
            fixed[key] = value
        if value and not _clean_int(nested.get(key)):
            nested[key] = value
    if order_no:
        fixed["order_no"] = order_no
        fixed.setdefault("purchase_order_no", order_no)
        nested["order_no"] = order_no
        nested.setdefault("purchase_order_no", order_no)

    items = nested.get("items") if isinstance(nested.get("items"), list) else fixed.get("items")
    if isinstance(items, list):
        repaired_items = []
        for item in items:
            if not isinstance(item, dict):
                repaired_items.append(item)
                continue
            repaired_item = dict(item)
            if not _clean_int(repaired_item.get("inc_vat") or repaired_item.get("amount") or repaired_item.get("total")) and total_sum:
                repaired_item["inc_vat"] = total_sum
            if not _clean_int(repaired_item.get("supply") or repaired_item.get("supply_amount")) and target_supply:
                repaired_item["supply"] = target_supply
            repaired_items.append(repaired_item)
        nested["items"] = repaired_items
        fixed["items"] = repaired_items

    fixed["data"] = nested
    return fixed


def _readiness(data: dict[str, Any], raw: dict[str, Any], *, invoice_type: str, pdf_path: str = "") -> tuple[bool, str]:
    if invoice_type == "regular":
        if not str(pdf_path or data.get("pdf_path") or raw.get("pdf_path") or "").strip():
            return False, "세금계산서 필요"
        total = (
            _clean_int(data.get("total_sum"))
            or _clean_int(data.get("total_amount"))
            or _clean_int(data.get("amount"))
        )
        if total <= 0:
            return False, "금액 확인 필요"
        return True, "ERP 입력 가능"

    quote_path = data.get("quote_path") or raw.get("quote_path") or ""
    items = data.get("items") or raw.get("items") or []
    if not quote_path:
        return False, "견적서 필요"
    if not isinstance(items, list) or not items:
        return False, "분석 필요"
    return True, "ERP 입력 가능"


def _row_to_invoice(row: sqlite3.Row) -> dict[str, Any]:
    try:
        raw = json.loads(row["json_data"] or "{}")
    except Exception:
        raw = {}
    invoice_type = str(raw.get("invoice_type") or "").strip().lower()
    if invoice_type == "purchase":
        raw = _repair_purchase_amounts(raw, str(row["pdf_path"] or ""))
    data = _invoice_data(raw)
    invoice_type = invoice_type or "regular"
    erp_ready, readiness_reason = _readiness(data, raw, invoice_type=invoice_type, pdf_path=str(row["pdf_path"] or ""))
    total = (
        _clean_int(data.get("total_sum"))
        or _clean_int(data.get("total_amount"))
        or _clean_int(data.get("amount"))
    )
    return {
        "id": row["id"],
        "subject": row["subject"],
        "pdf_path": row["pdf_path"],
        "status": row["status"],
        "processor": normalize_processor(row["processor"]),
        "received_at": row["received_at"],
        "processed_at": row["processed_at"],
        "last_error": row["last_error"] if "last_error" in row.keys() else "",
        "erp_job_id": row["erp_job_id"] if "erp_job_id" in row.keys() else "",
        "invoice_type": invoice_type,
        "site_name": data.get("site_name") or data.get("buyer_name") or "",
        "vendor_name": data.get("vendor_name") or data.get("supplier_name") or "",
        "total_sum": total,
        "purchase_analysis_ready": bool(data.get("purchase_analysis_ready") or raw.get("purchase_analysis_ready") or data.get("items")),
        "erp_ready": bool(data.get("erp_ready") or raw.get("erp_ready") or erp_ready),
        "readiness_reason": readiness_reason,
        "quote_path": data.get("quote_path") or raw.get("quote_path") or "",
        "approval_pdf_paths": data.get("approval_pdf_paths") or raw.get("approval_pdf_paths") or [],
        "approval_fetch_status": data.get("approval_fetch_status") or raw.get("approval_fetch_status") or "",
        "approval_fetch_error": data.get("approval_fetch_error") or raw.get("approval_fetch_error") or "",
        "approval_fetch_started_at": data.get("approval_fetch_started_at") or raw.get("approval_fetch_started_at") or "",
        "approval_fetch_finished_at": data.get("approval_fetch_finished_at") or raw.get("approval_fetch_finished_at") or "",
        "approval_order_number": data.get("approval_order_number") or raw.get("approval_order_number") or "",
        "data": data,
        "raw": raw,
    }


def detect_invoice_type(subject: str, result: dict[str, Any]) -> str:
    data = _invoice_data(result)
    vendor = str(data.get("vendor_name") or data.get("supplier_name") or "")
    text = f"{subject}\n{result.get('subject', '')}\n{vendor}".lower()
    purchase_tokens = ("컴퓨존", "compuzone", "쿠팡", "아이코다", "오피스디포", "가비아", "naver", "npay")
    if any(token.lower() in text for token in purchase_tokens):
        return "purchase"
    regular_tokens = (
        "대신아이씨티",
        "동양정보통신",
        "kt",
        "케이티",
        "autoever",
        "오토에버",
        "csbill",
        "wehago",
        "hometax",
        "nts_etaxinvoice",
    )
    if any(token.lower() in text for token in regular_tokens):
        return "regular"
    explicit = str(result.get("invoice_type") or "").strip().lower()
    return explicit if explicit in {"purchase", "regular"} else "regular"


def _repair_invoice_types(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT id, subject, json_data FROM invoices")
    for row in cur.fetchall():
        try:
            data = json.loads(row["json_data"] or "{}")
        except Exception:
            continue
        current = str(data.get("invoice_type") or "").strip().lower()
        detected = detect_invoice_type(str(row["subject"] or ""), data)
        if detected and detected != current:
            data["invoice_type"] = detected
            conn.execute(
                "UPDATE invoices SET json_data=? WHERE id=?",
                (json.dumps(data, ensure_ascii=False), row["id"]),
            )


def add_invoice_log(invoice_id: int | None, message: str, level: str = "info", job_id: str = "") -> None:
    init_db()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO invoice_logs (invoice_id, job_id, level, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (invoice_id, job_id, level, message, now_text()),
        )
        conn.commit()


def _is_cad_pc_text(value: Any) -> bool:
    compact = re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())
    return "CADPC" in compact


def learn_dictionary_items(items: list[dict[str, Any]]) -> int:
    init_db()
    learned = 0
    account_choices = {"소모품비", "집기비품", "컴퓨터소프트웨어"}
    with get_conn() as conn:
        for item in items or []:
            if item.get("system_adjustment"):
                continue
            original_text = str(
                item.get("raw_desc")
                or item.get("original_text")
                or item.get("desc")
                or item.get("name")
                or ""
            ).strip()
            corrected_name = str(item.get("name") or item.get("item_name") or "").strip()
            if not original_text or not corrected_name:
                continue
            account = str(item.get("account") or "").strip()
            if _is_cad_pc_text(corrected_name) or _is_cad_pc_text(original_text):
                item = dict(item)
                item["is_a"] = True
                item["account"] = "집기비품"
                account = "집기비품"
            is_asset = bool(item.get("is_a")) if "is_a" in item else account in {"집기비품", "컴퓨터소프트웨어"}
            if account not in account_choices:
                account = "집기비품" if is_asset else "소모품비"
            conn.execute("DELETE FROM dictionary WHERE original_text=?", (original_text,))
            conn.execute(
                """
                INSERT INTO dictionary (original_text, corrected_name, is_asset, account, learned_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (original_text, corrected_name, int(is_asset), account, now_text()),
            )
            learned += 1
        conn.commit()
    return learned


def _repair_regular_fields(result: dict[str, Any], pdf_path: str) -> dict[str, Any]:
    fixed = dict(result)
    nested = _invoice_data(fixed)
    has_date = any(str(source.get("invoice_date") or source.get("issue_date") or source.get("write_date") or "").strip() for source in (fixed, nested))
    if not has_date:
        try:
            from .erp_runner import _extract_invoice_date

            invoice_date = _extract_invoice_date({**fixed, **nested, "pdf_path": pdf_path}, pdf_path)
        except Exception:
            invoice_date = ""
        if invoice_date:
            fixed["invoice_date"] = invoice_date
            nested["invoice_date"] = invoice_date
    fixed["data"] = nested
    return fixed


def insert_crawler_invoice(subject: str, result: dict[str, Any]) -> bool:
    init_db()
    pdf_path = str(result.get("pdf_path") or "")
    if not pdf_path:
        return False

    stored_subject = str(result.get("subject") or subject or "세금계산서 수신")
    result["subject"] = stored_subject
    result["invoice_type"] = detect_invoice_type(stored_subject, result)
    if str(result.get("invoice_type") or "").strip().lower() == "purchase":
        result = _repair_purchase_amounts(result, pdf_path)
        result["subject"] = stored_subject
        result["invoice_type"] = "purchase"
    elif str(result.get("invoice_type") or "").strip().lower() == "regular":
        result = _repair_regular_fields(result, pdf_path)
        result["subject"] = stored_subject
        result["invoice_type"] = "regular"

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, json_data FROM invoices WHERE pdf_path=?", (pdf_path,))
        existing = cur.fetchone()
        if existing:
            if str(result.get("invoice_type") or "").strip().lower() == "purchase":
                try:
                    existing_json = json.loads(existing["json_data"] or "{}")
                except Exception:
                    existing_json = {}
                if existing_json.get("invoice_type") != "purchase":
                    existing_json["invoice_type"] = "purchase"
                    cur.execute(
                        "UPDATE invoices SET json_data=?, last_error='' WHERE id=?",
                        (json.dumps(existing_json, ensure_ascii=False), existing["id"]),
                    )
                    cur.execute(
                        """
                        INSERT INTO invoice_logs (invoice_id, job_id, level, message, created_at)
                        VALUES (?, '', 'info', ?, ?)
                        """,
                        (
                            existing["id"],
                            "구매 메일 수집 중복 확인으로 구매 처리 화면에 표시되도록 보정했습니다.",
                            now_text(),
                        ),
                    )
                    conn.commit()
            return False
        cur.execute(
            """
            INSERT INTO invoices (subject, pdf_path, json_data, status, received_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (stored_subject, pdf_path, json.dumps(result, ensure_ascii=False), WAITING, now_text()),
        )
        invoice_id = int(cur.lastrowid)
        conn.commit()
    add_invoice_log(invoice_id, "메일 수집으로 계산서가 등록되었습니다.")
    return True


def insert_manual_invoice(subject: str, result: dict[str, Any], *, log_message: str = "수동 업로드로 계산서가 등록되었습니다.") -> int:
    init_db()
    pdf_path = str(result.get("pdf_path") or "")
    if not pdf_path:
        raise ValueError("pdf_path is required")

    stored_subject = str(result.get("subject") or subject or "수동 업로드 계산서")
    result["subject"] = stored_subject
    result["invoice_type"] = detect_invoice_type(stored_subject, result)
    if str(result.get("invoice_type") or "").strip().lower() == "purchase":
        result = _repair_purchase_amounts(result, pdf_path)
        result["subject"] = stored_subject
        result["invoice_type"] = "purchase"

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, json_data FROM invoices WHERE pdf_path=?", (pdf_path,))
        existing = cur.fetchone()
        if existing:
            invoice_id = int(existing["id"])
            try:
                existing_json = json.loads(existing["json_data"] or "{}")
            except Exception:
                existing_json = {}
            existing_json.update(result)
            cur.execute(
                "UPDATE invoices SET subject=?, json_data=?, last_error='' WHERE id=?",
                (stored_subject, json.dumps(existing_json, ensure_ascii=False), invoice_id),
            )
            conn.commit()
            add_invoice_log(invoice_id, "수동 업로드 자료가 기존 계산서에 반영되었습니다.")
            return invoice_id

        cur.execute(
            """
            INSERT INTO invoices (subject, pdf_path, json_data, status, received_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (stored_subject, pdf_path, json.dumps(result, ensure_ascii=False), WAITING, now_text()),
        )
        invoice_id = int(cur.lastrowid)
        conn.commit()
    add_invoice_log(invoice_id, log_message)
    return invoice_id


def list_invoices(mode: str = "", limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    mode = (mode or "").strip().lower()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, subject, pdf_path, json_data, status, processor, received_at, processed_at, last_error, erp_job_id
            FROM invoices
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit or 50), 200)),),
        )
        rows = cur.fetchall()

    invoices: list[dict[str, Any]] = []
    for row in rows:
        invoice = _row_to_invoice(row)
        invoice_type = invoice["invoice_type"]
        if mode == "purchase" and invoice_type == "regular":
            continue
        if mode == "regular" and invoice_type != "regular":
            continue
        invoice.pop("raw", None)
        invoice.pop("data", None)
        invoices.append(invoice)
    return invoices


def get_invoice(invoice_id: int) -> dict[str, Any] | None:
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, subject, pdf_path, json_data, status, processor, received_at, processed_at, last_error, erp_job_id
            FROM invoices
            WHERE id=?
            """,
            (invoice_id,),
        )
        row = cur.fetchone()
    return _row_to_invoice(row) if row else None


def get_invoice_by_pdf_path(pdf_path: str) -> dict[str, Any] | None:
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, subject, pdf_path, json_data, status, processor, received_at, processed_at, last_error, erp_job_id
            FROM invoices
            WHERE pdf_path=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (str(pdf_path or ""),),
        )
        row = cur.fetchone()
    return _row_to_invoice(row) if row else None


def update_invoice_json(invoice_id: int, updates: dict[str, Any], *, message: str = "") -> dict[str, Any] | None:
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT json_data FROM invoices WHERE id=?", (invoice_id,))
        row = cur.fetchone()
        if not row:
            return None
        try:
            raw = json.loads(row["json_data"] or "{}")
        except Exception:
            raw = {}
        data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
        for key, value in updates.items():
            if key == "data" and isinstance(value, dict):
                data.update(value)
            else:
                raw[key] = value
                data[key] = value
        raw["data"] = data
        cur.execute(
            "UPDATE invoices SET json_data=?, last_error='' WHERE id=?",
            (json.dumps(raw, ensure_ascii=False), invoice_id),
        )
        conn.commit()
    if message:
        add_invoice_log(invoice_id, message)
    return get_invoice(invoice_id)


def update_invoice_pdf_path(invoice_id: int, pdf_path: str, updates: dict[str, Any] | None = None, *, message: str = "") -> dict[str, Any] | None:
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT json_data FROM invoices WHERE id=?", (invoice_id,))
        row = cur.fetchone()
        if not row:
            return None
        try:
            raw = json.loads(row["json_data"] or "{}")
        except Exception:
            raw = {}
        data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
        raw["pdf_path"] = pdf_path
        data["pdf_path"] = pdf_path
        for key, value in (updates or {}).items():
            if key == "data" and isinstance(value, dict):
                data.update(value)
            else:
                raw[key] = value
                data[key] = value
        raw["data"] = data
        cur.execute(
            "UPDATE invoices SET pdf_path=?, json_data=?, last_error='' WHERE id=?",
            (pdf_path, json.dumps(raw, ensure_ascii=False), invoice_id),
        )
        conn.commit()
    if message:
        add_invoice_log(invoice_id, message)
    return get_invoice(invoice_id)


def list_invoice_logs(invoice_id: int, limit: int = 100) -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, invoice_id, job_id, level, message, created_at
            FROM invoice_logs
            WHERE invoice_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (invoice_id, max(1, min(int(limit or 100), 300))),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def set_invoice_status(
    invoice_id: int,
    status: str,
    *,
    processor: str | None = None,
    job_id: str = "",
    error: str = "",
    processed: bool = False,
) -> bool:
    init_db()
    fields = ["status=?"]
    values: list[Any] = [status]
    if processor is not None:
        fields.append("processor=?")
        values.append(normalize_processor(processor))
    if error:
        fields.append("last_error=?")
        values.append(error)
    elif status not in {ERROR}:
        fields.append("last_error=''")
    if job_id:
        fields.append("erp_job_id=?")
        values.append(job_id)
    if processed:
        fields.append("processed_at=?")
        values.append(now_text())
    elif status in {WAITING, ERP_QUEUED, PROCESSING}:
        fields.append("processed_at=NULL")

    values.append(invoice_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE invoices SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()
        ok = cur.rowcount > 0
    if ok:
        message = f"상태 변경: {status}"
        if error:
            message += f" / {error}"
        add_invoice_log(invoice_id, message, "error" if status == ERROR else "info", job_id=job_id)
    return ok


def reset_invoice(invoice_id: int) -> bool:
    return set_invoice_status(invoice_id, WAITING, processor="", error="")


def delete_invoice(invoice_id: int) -> bool:
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM invoices WHERE id=?", (invoice_id,))
        conn.commit()
        return cur.rowcount > 0
