from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from app.settings import manager_profile
from app.voucher_builder import build_voucher_payload


def _write_sample(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["업체명", "업체코드", "금액"])
    sheet.append(["가나다상사", "A001", 12000])
    sheet.append(["라마정밀", "B002", "3,000"])
    sheet.append(["금액없는행", "C003", 0])
    workbook.save(path)


def _write_cash_sheet_sample(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "수시결제현금"
    sheet["A6"] = "합 계  : 15,000원 2(件)"
    sheet.append([])
    sheet.append(["구분", "NO", "거래일자", "부서", "코드", "업체명", "적         요", "금액"])
    sheet.append(["", "", "", "", "", "", "", ""])
    sheet.append(["평택", 1, 531, "구매", "A001", "가나다상사", "소모품", 12000])
    sheet.append(["", 2, 531, "물류", "B002", "라마정밀", "운반비", 3000])
    workbook.save(path)


def test_build_voucher_payload_adds_bank_credit_line(tmp_path: Path) -> None:
    source = tmp_path / "sample.xlsx"
    _write_sample(source)

    payload = build_voucher_payload(
        source,
        accounting_date="2026-06-20",
        requester="tester",
        source_filename="sample.xlsx",
        manager=manager_profile("daeseung"),
    )

    assert payload.debit_total == 15000
    assert payload.credit_total == 15000
    assert payload.line_count == 3
    assert payload.lines[0].side == "debit"
    assert payload.lines[0].account_name == "미지급금(원화)"
    assert payload.lines[0].summary == "5월 수시결제 - 가나다상사(A001)"
    assert payload.lines[-1].side == "credit"
    assert payload.lines[-1].account_name == "보통예금"
    assert payload.lines[-1].summary == "5월 수시결제 - 신한은행"


def test_build_voucher_payload_uses_cash_sheet_rows_only(tmp_path: Path) -> None:
    source = tmp_path / "cash.xlsx"
    _write_cash_sheet_sample(source)

    payload = build_voucher_payload(
        source,
        accounting_date="2026-06-20",
        requester="tester",
        source_filename="cash.xlsx",
        manager=manager_profile("daeseung"),
    )

    assert payload.source_format == "daeseung_cash_sheet_v1"
    assert payload.source_row_count == 2
    assert payload.debit_total == 15000
    assert payload.line_count == 3
    assert payload.lines[0].source_sheet == "수시결제현금"
    assert payload.lines[0].amount == 12000
    assert payload.source_columns["amount"] == "수시결제현금!H"
