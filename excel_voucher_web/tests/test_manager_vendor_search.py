from pathlib import Path


MANAGER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "manager_server"
    / "전표 자동화 프로그램(담당자용)_v6.2.py"
)


def test_finance_vendor_search_uses_vendor_number_filter():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    assert 'if search_label == "거래처번호":' in source
    assert (
        'return _input_vendor_by_popup_keyboard(x, y, label, vendor_code, "거래처번호", 2)'
        in source
    )
    assert (
        'return _input_vendor_by_popup_keyboard(x, y, label, vendor_code, "거래처코드", 2)'
        not in source
    )
