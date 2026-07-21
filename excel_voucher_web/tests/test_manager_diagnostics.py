from __future__ import annotations

import ast
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
MANAGER_SOURCE = next((ROOT / "manager_server").glob("*v6.2.py"))
AGENT_WORKER_SOURCE = ROOT / "excel_voucher_web" / "agent" / "agent_worker.py"


def _load_nested_function(name: str, namespace: dict):
    tree = ast.parse(MANAGER_SOURCE.read_text(encoding="utf-8"))
    node = next(
        item
        for item in ast.walk(tree)
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    loaded = dict(namespace)
    exec(compile(module, str(MANAGER_SOURCE), "exec"), loaded)
    return loaded[name]


def test_agent_tail_log_can_include_read_only_top_level_window_diagnostics():
    source = AGENT_WORKER_SOURCE.read_text(encoding="utf-8")
    helper_start = source.index("def _top_level_window_diagnostics")
    helper_end = source.index("def _popen_hidden", helper_start)
    helper = source[helper_start:helper_end]
    command_start = source.index("def _execute_admin_command")
    command_end = source.index("def main", command_start)
    command = source[command_start:command_end]

    assert 'Desktop(backend=backend).windows()' in helper
    assert '.descendants(' not in helper
    assert 'for backend in ("uia", "win32")' in helper
    assert 'ProcessIdToSessionId' in helper
    assert 'snapshot["processes"] = process_records[:250]' in helper
    assert 'payload.get("inspect_erp_windows") is True' in command
    assert 'result["top_level_windows"] = _top_level_window_diagnostics()' in command


def test_form_diagnostics_captures_png_before_uia_dump(tmp_path):
    events: list[str] = []
    screenshot_paths: list[str] = []
    debug_dir = tmp_path / "debug"

    def _screenshot(path: str):
        events.append("screenshot")
        screenshot_paths.append(path)

    class _FailingMainWindow:
        def window_text(self):
            events.append("uia")
            raise RuntimeError("UIA unavailable")

    warnings: list[str] = []
    fake_self = SimpleNamespace(
        manager=SimpleNamespace(
            main_app=SimpleNamespace(erp_job_id="job-1", erp_invoice_id="invoice-1")
        ),
        logger=SimpleNamespace(warning=warnings.append),
    )
    dump_diagnostics = _load_nested_function(
        "_dump_form_diagnostics",
        {
            "Path": lambda _value: debug_dir,
            "datetime": datetime,
            "os": os,
            "BASE_EXE_DIR": str(tmp_path),
            "self": fake_self,
            "main_win": _FailingMainWindow(),
            "pyautogui": SimpleNamespace(screenshot=_screenshot),
            "_iter_visible": lambda _control_type: [],
            "_control_text": lambda _control: "",
        },
    )

    dump_diagnostics("forced failure")

    assert events == ["screenshot", "uia"]
    assert len(screenshot_paths) == 1
    assert Path(screenshot_paths[0]).parent == debug_dir
    assert Path(screenshot_paths[0]).name.startswith("erp_form_fail_job-1_invoice-1_")
    assert any("failure screenshot saved" in warning for warning in warnings)


def test_form_diagnostics_does_not_recapture_after_successful_uia_dump(tmp_path):
    screenshot_paths: list[str] = []
    debug_dir = tmp_path / "debug"
    fake_self = SimpleNamespace(
        manager=SimpleNamespace(
            main_app=SimpleNamespace(erp_job_id="job-2", erp_invoice_id="invoice-2")
        ),
        logger=SimpleNamespace(warning=lambda _message: None),
    )
    dump_diagnostics = _load_nested_function(
        "_dump_form_diagnostics",
        {
            "Path": lambda _value: debug_dir,
            "datetime": datetime,
            "os": os,
            "BASE_EXE_DIR": str(tmp_path),
            "self": fake_self,
            "main_win": SimpleNamespace(window_text=lambda: "ERP"),
            "pyautogui": SimpleNamespace(screenshot=screenshot_paths.append),
            "_iter_visible": lambda _control_type: [],
            "_control_text": lambda _control: "",
        },
    )

    dump_diagnostics("forced failure")

    assert len(screenshot_paths) == 1
    assert (tmp_path / "erp_ui_dump.txt").is_file()
