import ast
import os
import re
from types import SimpleNamespace
from pathlib import Path


MANAGER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "manager_server"
    / "전표 자동화 프로그램(담당자용)_v6.2.py"
)


def _grid_row_converter():
    tree = ast.parse(MANAGER_SOURCE.read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_grid_row_to_excel_values"
    )
    scope = {"re": re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "<erp-grid>", "exec"), scope)
    return scope[function.name]


def test_excel_paste_places_summary_in_fourth_erp_column():
    convert = _grid_row_converter()

    assert convert("미지급금(원화)\t0\t1000\t\t8월 수시결제 - 업체") == [
        "미지급금(원화)", 0, 1000, "8월 수시결제 - 업체"
    ]
    assert convert("미지급금(원화)\t\t0\t1000\t\t8월 수시결제 - 업체") == [
        "미지급금(원화)", 0, 1000, "8월 수시결제 - 업체"
    ]
    assert convert("미지급금(원화)\t0\t1000\t8월 수시결제 - 업체") == [
        "미지급금(원화)", 0, 1000, "8월 수시결제 - 업체"
    ]


def test_summary_is_verified_before_management_and_save():
    source = MANAGER_SOURCE.read_text(encoding="utf-8")
    setup = source[source.index("        def _setup_by_coordinates_only():") :]

    assert 'end_col = 4' in source
    assert 'sheet.Columns("A:D").AutoFit()' in source
    assert setup.index("_verify_grid_first_summary_or_fail()") < setup.index(
        "_fill_management_items_by_coord()"
    ) < setup.index("_save_and_open_print_dialog()")
    assert '_norm_text(copied) == _norm_text(expected)' in source
    assert 'if not used_excel_clipboard:' in setup
    assert 'Excel 4열 복사 복원에 실패' in setup


def test_missing_summary_aborts_before_save():
    tree = ast.parse(MANAGER_SOURCE.read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_verify_grid_first_summary_or_fail"
    )

    class Clipboard:
        value = ""

        def copy(self, value):
            self.value = value

        def paste(self):
            return self.value

    clipboard = Clipboard()

    def fail(message):
        raise RuntimeError(message)

    scope = {
        "original_clipboard": "미지급금(원화)\t0\t1000\t\t8월 수시결제 - 업체",
        "_grid_row_to_excel_values": _grid_row_converter(),
        "_norm_text": lambda value: value.strip(),
        "_fail_form": fail,
        "_click_form_xy": lambda *args, **kwargs: None,
        "_release_modifiers": lambda *args, **kwargs: None,
        "mgmt_click_wait": 0,
        "ERP_FORM_WAIT": 0,
        "grid_paste_state": {"verified": False},
        "os": os,
        "time": SimpleNamespace(time_ns=lambda: 1, sleep=lambda seconds: None),
        "pyperclip": clipboard,
        "pyautogui": SimpleNamespace(hotkey=lambda *args: clipboard.copy("")),
        "self": SimpleNamespace(logger=SimpleNamespace(info=lambda message: None, warning=lambda message: None)),
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), "<erp-summary-check>", "exec"), scope)

    try:
        scope[function.name]()
    except RuntimeError as exc:
        assert "적요 칸" in str(exc)
    else:
        raise AssertionError("Missing ERP summary must stop the voucher before save")
    assert scope["grid_paste_state"]["verified"] is False
