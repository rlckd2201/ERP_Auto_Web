from __future__ import annotations

from pathlib import Path


def test_server_script_requires_login_by_default():
    script = Path("run_server.ps1").read_text(encoding="utf-8")

    assert "[switch]$RequireLogin = $true" in script


def test_settings_require_login_by_default():
    source = Path("app/settings.py").read_text(encoding="utf-8")

    assert 'auth_required: bool = _env_bool("EXCEL_VOUCHER_AUTH_REQUIRED", True)' in source
