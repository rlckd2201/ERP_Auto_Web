import ctypes
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageGrab

from agent import agent_worker as worker


def _geometry(**overrides):
    return {
        "coordinate_space": "agent-desktop-physical-pixels",
        "foreground_title": "\ub300\uc2b9",
        "window_rect": [-1920, 0, 0, 1040],
        "window_dpi": 144,
        "minimized": False,
        **overrides,
    }


def test_capture_preserves_native_pixels_and_origin(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "_native_erp_screen_geometry", _geometry)
    calls = []

    def grab(**kwargs):
        calls.append(kwargs)
        return Image.new("RGB", (1920, 1040), "white")

    monkeypatch.setattr(ImageGrab, "grab", grab)
    result = worker._save_native_erp_screen(tmp_path)

    assert calls == [{"bbox": (-1920, 0, 0, 1040), "all_screens": True}]
    assert result["screenshot_origin"] == [-1920, 0]
    assert result["screenshot_size"] == [1920, 1040]
    assert result["window_dpi"] == 144
    path = Path(result["screenshot_path"])
    assert path.is_file()
    assert json.loads(path.with_suffix(".json").read_text(encoding="utf-8")) == result


@pytest.mark.parametrize("changes", [
    {"foreground_title": "Login"},
    {"foreground_title": "Chrome"},
    {"minimized": True},
    {"window_rect": [0, 0, 400, 300]},
])
def test_capture_skips_login_and_unrelated_windows(tmp_path, monkeypatch, changes):
    monkeypatch.setattr(worker, "_native_erp_screen_geometry", lambda: _geometry(**changes))
    monkeypatch.setattr(ImageGrab, "grab", lambda **kwargs: pytest.fail("must not capture"))

    result = worker._save_native_erp_screen(tmp_path)

    assert result["capture_skipped"]
    assert "screenshot_path" not in result
    assert list(tmp_path.iterdir()) == []


def test_capture_rejects_scaled_bitmap(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "_native_erp_screen_geometry", _geometry)
    monkeypatch.setattr(ImageGrab, "grab", lambda **kwargs: Image.new("RGB", (1280, 720)))

    with pytest.raises(RuntimeError, match="physical window rectangle"):
        worker._save_native_erp_screen(tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fail", [False, True])
def test_diagnostic_restores_thread_dpi_context(tmp_path, monkeypatch, fail):
    calls = []

    def setter(value):
        calls.append(value)
        return 123

    monkeypatch.setattr(worker.sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(
        user32=SimpleNamespace(SetThreadDpiAwarenessContext=setter)
    ), raising=False)

    def capture(_path):
        if fail:
            raise RuntimeError("capture failed")
        return {"ok": True}

    monkeypatch.setattr(worker, "_save_native_erp_screen", capture)
    if fail:
        with pytest.raises(RuntimeError, match="capture failed"):
            worker._native_erp_screen_diagnostics(tmp_path)
    else:
        assert worker._native_erp_screen_diagnostics(tmp_path) == {"ok": True}
    assert len(calls) == 2
    assert calls[-1] == 123


@pytest.mark.parametrize("fail", [False, True])
def test_tail_log_includes_diagnostic_without_touching_job(tmp_path, monkeypatch, fail):
    monkeypatch.setattr(worker, "_latest_agent_log", lambda _: {"tail": "existing log"})

    def diagnostic(_path):
        if fail:
            raise RuntimeError("capture failed")
        return {"window_rect": [0, 0, 1920, 1040]}

    monkeypatch.setattr(worker, "_native_erp_screen_diagnostics", diagnostic)
    monkeypatch.setattr(worker, "_upload_job_artifact", lambda *a, **k: pytest.fail("must not change job status"))
    monkeypatch.setattr(worker, "run_erp_voucher_task", lambda *a, **k: pytest.fail("must not run ERP"))
    result = worker._execute_admin_command(
        {"command": "tail-log"}, server="https://example.invalid", agent_id="agent",
        client_ip="", verify_tls=True, print_mode="off", printer_name="",
        print_wait_seconds=0, erp_mode="real", output_dir=tmp_path,
    )
    assert result["tail"].startswith("existing log\n[ERP-SCREEN] ")
    assert json.loads(result["tail"].split("[ERP-SCREEN] ")[1]) == result["screen_diagnostic"]
    assert ("error" in result["screen_diagnostic"]) is fail
