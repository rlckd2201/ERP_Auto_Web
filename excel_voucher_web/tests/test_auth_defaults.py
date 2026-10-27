from __future__ import annotations

from pathlib import Path


def test_server_script_requires_login_by_default():
    script = Path("run_server.ps1").read_text(encoding="utf-8")

    assert "[switch]$RequireLogin = $true" in script


def test_server_script_enables_operating_https_by_default():
    script = Path("run_server.ps1").read_text(encoding="utf-8")

    assert '[string]$SslCertFile = "C:\\ERP_DB\\finance_web105\\finance.cert.pem"' in script
    assert '[string]$SslKeyFile = "C:\\ERP_DB\\finance_web105\\finance.key.pem"' in script
    assert "$UsesHttps = $PublicOrigin -match '^https://'" in script
    assert "PublicOrigin uses HTTPS, but SSL certificate paths are empty." in script
    assert "Test-Path -LiteralPath $SslCertFile -PathType Leaf" in script
    assert "Test-Path -LiteralPath $SslKeyFile -PathType Leaf" in script


def test_settings_require_login_by_default():
    source = Path("app/settings.py").read_text(encoding="utf-8")

    assert 'auth_required: bool = _env_bool("EXCEL_VOUCHER_AUTH_REQUIRED", True)' in source


def test_launchers_preserve_managed_service_and_do_not_restore_legacy_server():
    for name in ("run_server.ps1", "install_server_autostart.ps1"):
        source = Path(name).read_text(encoding="utf-8")
        assert '172.17.39.121' not in source
        assert 'http://127.0.0.1:18080' not in source
        assert "Get-ScheduledTask -TaskName 'FinanceVoucher-Web-3012'" in source
        assert "if ($Task.State -ne 'Running')" in source or "if ($RunNow -and $Task.State -ne 'Running')" in source
        assert "environment.json" in source
    launcher = Path("start_server.cmd").read_text(encoding="utf-8")
    assert '-ForwardToDataServer' not in launcher
    assert '172.17.39.121' not in launcher


def test_finance_defaults_use_3012_without_moving_existing_data():
    origin = 'https://172.16.19.105:3012'
    for name in ('run_server.ps1', 'install_server_autostart.ps1'):
        source = Path(name).read_text(encoding='utf-8')
        assert '[int]$Port = 3012' in source
        assert origin in source
    for name in ('run_agent.ps1', 'install_agent_task.ps1'):
        assert origin in Path(name).read_text(encoding='utf-8')
    settings = Path('app/settings.py').read_text(encoding='utf-8')
    assert '_env_int("EXCEL_VOUCHER_WEB_PORT", 3012)' in settings
    assert origin in settings
    assert r'C:\ERP_DB\finance_3011_data' in settings
