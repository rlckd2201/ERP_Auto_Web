from __future__ import annotations

from pathlib import Path


def test_server_script_requires_login_by_default():
    script = Path("run_server.ps1").read_text(encoding="utf-8")

    assert "[switch]$RequireLogin = $true" in script


def test_server_script_enables_operating_https_by_default():
    script = Path("run_server.ps1").read_text(encoding="utf-8")

    assert '[string]$SslCertFile = "C:\\ERP_DB\\certs\\web_v1.cert.pem"' in script
    assert '[string]$SslKeyFile = "C:\\ERP_DB\\certs\\web_v1.key.pem"' in script
    assert "$UsesHttps = $PublicOrigin -match '^https://'" in script
    assert "PublicOrigin uses HTTPS, but SSL certificate paths are empty." in script
    assert "Test-Path -LiteralPath $SslCertFile -PathType Leaf" in script
    assert "Test-Path -LiteralPath $SslKeyFile -PathType Leaf" in script


def test_settings_require_login_by_default():
    source = Path("app/settings.py").read_text(encoding="utf-8")

    assert 'auth_required: bool = _env_bool("EXCEL_VOUCHER_AUTH_REQUIRED", True)' in source
