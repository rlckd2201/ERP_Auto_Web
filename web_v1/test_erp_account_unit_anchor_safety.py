from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER_PATH = ROOT / "manager_server" / "전표 자동화 프로그램(담당자용)_v6.2.py"
if not MANAGER_PATH.exists():
    MANAGER_PATH = Path(__file__).parent / "manager.py"


def _load_helper(name: str):
    source = MANAGER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(MANAGER_PATH), "exec"), namespace)
    return namespace[name]


def test_exact_account_unit_anchor_is_recognized() -> None:
    helper = _load_helper("_erp_account_unit_anchor_flags")
    assert helper("cboAccUnit", "ComboBox", 167, 28, -257, 0) == (True, False)


def test_song_anonymous_account_unit_horizontal_drift_is_kept() -> None:
    helper = _load_helper("_erp_account_unit_anchor_flags")
    assert helper("", "ComboBox", 167, 28, -76, 0) == (False, True)


def test_243_unrelated_anonymous_combo_is_rejected() -> None:
    helper = _load_helper("_erp_account_unit_anchor_flags")
    assert helper("", "ComboBox", 167, 28, -257, 0) == (False, False)


def test_anonymous_combo_on_another_row_is_rejected() -> None:
    helper = _load_helper("_erp_account_unit_anchor_flags")
    assert helper("", "ComboBox", 167, 28, 0, 18) == (False, False)


def test_verified_shift_uses_combo_right_edge_not_combo_center() -> None:
    helper = _load_helper("_erp_verified_account_unit_form_x_shift")
    assert helper(501, 0) == 0
    assert helper(320, 0) == -181


def test_unreasonable_verified_shift_is_rejected() -> None:
    helper = _load_helper("_erp_verified_account_unit_form_x_shift")
    assert helper(120, 0) is None


def test_far_verified_combo_enables_anchor_mode() -> None:
    helper = _load_helper("_erp_account_unit_requires_anchor_mode")
    assert helper(False, False, True) is True


def test_normal_or_exact_combo_keeps_proven_coordinates() -> None:
    helper = _load_helper("_erp_account_unit_requires_anchor_mode")
    assert helper(False, True, True) is False
    assert helper(True, False, True) is False


def test_verified_243_management_cells_are_centered_in_shifted_grid() -> None:
    helper = _load_helper("_erp_shifted_management_cell")
    assert helper(1118, 797, -181) == (937, 807)
    assert helper(1118, 817, -181) == (937, 827)
    assert helper(1118, 837, -181) == (937, 847)
    assert helper(1118, 857, -181) == (937, 867)


def test_unverified_management_shift_fails_closed() -> None:
    helper = _load_helper("_erp_shifted_management_cell")
    try:
        helper(1118, 817, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("unverified shift must not click management grid")
