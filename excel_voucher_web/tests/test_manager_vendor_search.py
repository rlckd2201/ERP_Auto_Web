from pathlib import Path


MANAGER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "manager_server"
    / "전표 자동화 프로그램(담당자용)_v6.2.py"
)


def test_finance_vendor_search_uses_vendor_number_filter():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")

    branch_start = source.index('if search_label == "거래처번호":')
    branch_end = source.index("# ERP 거래처 팝업은", branch_start)
    first_row_branch = source[branch_start:branch_end]

    assert first_row_branch.index("_input_vendor_popup_search_text") < first_row_branch.index(
        "_select_vendor_popup_filter"
    )
    assert first_row_branch.index("_select_vendor_popup_filter") < first_row_branch.index(
        "_click_vendor_popup_search_button"
    )
    assert first_row_branch.index("_click_vendor_popup_search_button") < first_row_branch.index(
        "_select_first_vendor_popup_result"
    )
    assert "pyautogui.press('enter')" not in first_row_branch
    assert (
        'return _input_vendor_by_popup_keyboard(x, y, label, vendor_code, "거래처번호", 2)'
        in source
    )
    assert (
        'return _input_vendor_by_popup_keyboard(x, y, label, vendor_code, "거래처코드", 2)'
        not in source
    )
    assert 'finance_vendor_entry_state = {"popup_seeded": False}' in source
    assert 'if account_key == "미지급금(원화)":' in source
    assert 'if not finance_vendor_entry_state["popup_seeded"]:' in source
    assert 'finance_vendor_entry_state["popup_seeded"] = True' in source
    assert "관리항목값 셀 직접 입력 후 Enter 완료" in source
    assert "거래처번호 팝업 입력 실패, 직접 입력 fallback" in source
