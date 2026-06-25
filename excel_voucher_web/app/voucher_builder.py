from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from .models import VoucherLine, VoucherPayload
from .settings import ManagerProfile


VENDOR_ALIASES = {"업체명", "거래처명", "상호", "vendor", "vendor_name", "name"}
VENDOR_CODE_ALIASES = {"업체코드", "거래처코드", "코드", "vendor_code", "code"}
AMOUNT_ALIASES = {"금액", "지급액", "결제금액", "합계", "총액", "amount", "payment_amount"}


@dataclass(frozen=True)
class ColumnMap:
    vendor_name: int
    vendor_code: int | None
    amount: int
    labels: dict[str, str]


def _clean_header(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[\s\-_()/\\[\].:]+", "", text)


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(round(value))
    text = str(value).strip()
    if not text:
        return 0
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^0-9.-]", "", text)
    if not text or text in {"-", ".", "-."}:
        return 0
    try:
        amount = int(round(float(text)))
    except ValueError:
        return 0
    return -amount if negative else amount


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("회계일은 YYYY-MM-DD 형식이어야 합니다.") from exc


def _previous_month_label(accounting_date: str) -> str:
    parsed = _parse_date(accounting_date)
    month = 12 if parsed.month == 1 else parsed.month - 1
    return f"{month}월"


def _find_column(headers: list[Any], aliases: set[str]) -> int | None:
    cleaned_aliases = {_clean_header(alias) for alias in aliases}
    for index, value in enumerate(headers):
        if _clean_header(value) in cleaned_aliases:
            return index
    return None


def _find_header_row(rows: list[tuple[Any, ...]]) -> tuple[int, ColumnMap]:
    for row_index, row in enumerate(rows[:20], start=1):
        vendor_index = _find_column(list(row), VENDOR_ALIASES)
        amount_index = _find_column(list(row), AMOUNT_ALIASES)
        if vendor_index is None or amount_index is None:
            continue
        code_index = _find_column(list(row), VENDOR_CODE_ALIASES)
        labels = {
            "vendor_name": str(row[vendor_index] or ""),
            "amount": str(row[amount_index] or ""),
        }
        if code_index is not None:
            labels["vendor_code"] = str(row[code_index] or "")
        return row_index, ColumnMap(vendor_index, code_index, amount_index, labels)
    raise ValueError("엑셀에서 업체명과 금액 컬럼을 찾지 못했습니다.")


def _vendor_summary(month_label: str, vendor_name: str, vendor_code: str) -> str:
    vendor = vendor_name.strip() or "업체명 미확인"
    code = vendor_code.strip()
    suffix = f"{vendor}({code})" if code else vendor
    return f"{month_label} 수시결제 - {suffix}"


def build_voucher_payload(
    path: Path,
    *,
    accounting_date: str,
    requester: str,
    source_filename: str,
    manager: ManagerProfile,
) -> VoucherPayload:
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
    finally:
        workbook.close()

    if not rows:
        raise ValueError("엑셀에 데이터가 없습니다.")

    header_row, columns = _find_header_row(rows)
    month_label = _previous_month_label(accounting_date)
    lines: list[VoucherLine] = []

    for source_row, row in enumerate(rows[header_row:], start=header_row + 1):
        vendor_name = str(row[columns.vendor_name] or "").strip() if len(row) > columns.vendor_name else ""
        vendor_code = ""
        if columns.vendor_code is not None and len(row) > columns.vendor_code:
            vendor_code = str(row[columns.vendor_code] or "").strip()
        amount = _to_int(row[columns.amount] if len(row) > columns.amount else None)
        if not vendor_name and not vendor_code and amount == 0:
            continue
        if amount <= 0:
            continue
        lines.append(
            VoucherLine(
                seq=len(lines) + 1,
                side="debit",
                account_name="미지급금(원화)",
                amount=amount,
                summary=_vendor_summary(month_label, vendor_name, vendor_code),
                vendor_name=vendor_name,
                vendor_code=vendor_code,
                source_row=source_row,
            )
        )

    if not lines:
        raise ValueError("전표로 변환할 금액 행이 없습니다.")

    debit_total = sum(line.amount for line in lines)
    lines.append(
        VoucherLine(
            seq=len(lines) + 1,
            side="credit",
            account_name=manager.bank_account_name,
            amount=debit_total,
            summary=f"{month_label} 수시결제 - {manager.bank_summary_name}",
        )
    )

    return VoucherPayload(
        accounting_date=accounting_date,
        company_key=manager.key,
        company_name=manager.company_name,
        requester=requester,
        source_filename=source_filename,
        debit_total=debit_total,
        credit_total=debit_total,
        line_count=len(lines),
        lines=lines,
        source_columns=columns.labels,
    )
