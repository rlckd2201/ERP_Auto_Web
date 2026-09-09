from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER_PATH = ROOT / "manager_server" / "전표 자동화 프로그램(담당자용)_v6.2.py"


def _load_helpers(*names: str) -> dict[str, object]:
    source = MANAGER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(MANAGER_PATH), "exec"), namespace)
    return namespace


def test_form_anchor_can_apply_x_but_never_y() -> None:
    helper = _load_helpers("_erp_form_applied_offsets")["_erp_form_applied_offsets"]
    assert helper(-76, 7, True) == (-76, 0)
    assert helper(32, -8, True) == (32, 0)
    assert helper(32, 7, False) == (0, 0)


def test_management_retries_keep_the_same_row_y() -> None:
    helper = _load_helpers("_erp_management_summary_click_candidates")["_erp_management_summary_click_candidates"]
    assert helper([970, 930, 1010, 890, 1070]) == [
        (970, 0), (930, 0), (1010, 0), (890, 0), (1070, 0)
    ]


def test_runtime_contains_no_vertical_retry_or_anchor_application() -> None:
    source = MANAGER_PATH.read_text(encoding="utf-8")
    assert "ERP_MGMT_SUMMARY_Y_OFFSETS" not in source
    assert "form_coord_offset_y = offset_y" not in source
    assert "_erp_form_applied_offsets(" in source
    assert "_erp_management_summary_click_candidates(summary_x_candidates)" in source
