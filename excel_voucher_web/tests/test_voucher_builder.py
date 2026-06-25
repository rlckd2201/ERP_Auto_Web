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
