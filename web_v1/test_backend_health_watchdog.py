from __future__ import annotations

from pathlib import Path


DEPLOY = Path(__file__).resolve().parent / "deploy"


def test_watchdog_checks_health_before_targeted_backend_restart() -> None:
    source = (DEPLOY / "backend_health_watchdog.ps1").read_text(encoding="utf-8")
    assert "https://127.0.0.1:8080/health" in source
    assert '[int]$FailureThreshold = 2' in source
    assert "-m\\s+web_v1\\.backend" in source
    assert "Stop-Process -Id $process.ProcessId" in source
    assert "taskkill /IM python" not in source


def test_watchdog_install_is_minutely_and_non_overlapping() -> None:
    source = (DEPLOY / "install_backend_health_watchdog.ps1").read_text(encoding="utf-8")
    assert "New-TimeSpan -Minutes 1" in source
    assert "-MultipleInstances IgnoreNew" in source
    assert 'UserId "SYSTEM"' in source


def test_server_runner_uses_the_explicit_production_root() -> None:
    source = (DEPLOY / "run_server121_backend.ps1").read_text(encoding="utf-8")
    assert "전표 자동화 프로그램_WEB_Version" in source
    assert "Sort-Object LastWriteTime" not in source
    assert '@("-u", "-m", "web_v1.backend")' in source
