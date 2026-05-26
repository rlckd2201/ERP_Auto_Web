from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
WEB_ROOT = BACKEND_DIR.parent
PROJECT_ROOT = WEB_ROOT.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(BACKEND_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    value = _env(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name, "1" if default else "0").lower()
    return value not in {"0", "false", "no", "off"}


def _version_file_default() -> str:
    try:
        value = (WEB_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        if value:
            return value
    except Exception:
        pass
    return "1.0.0"


def _app_version() -> str:
    env_value = _env("APP_VERSION")
    file_value = _version_file_default()
    if not env_value or env_value == "1.0.0":
        return file_value
    return env_value


def _legacy_manager_path() -> Path:
    manager_dir = PROJECT_ROOT / "manager_server"
    candidates: list[Path] = []
    env_value = _env("LEGACY_MANAGER_PATH")
    if env_value:
        candidates.append(Path(env_value))
    candidates.append(manager_dir / "전표 자동화 프로그램(담당자용)_v6.2.py")
    if manager_dir.exists():
        candidates.extend(sorted(manager_dir.glob("*v6.2.py")))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else manager_dir / "전표 자동화 프로그램(담당자용)_v6.2.py"


@dataclass(frozen=True)
class Settings:
    app_version: str = _app_version()
    app_env: str = _env("APP_ENV", "development")
    web_host: str = _env("WEB_HOST", "127.0.0.1")
    web_port: int = _env_int("WEB_PORT", 8080)
    web_public_origin: str = _env("WEB_PUBLIC_ORIGIN", "http://127.0.0.1:8080")
    ssl_cert_file: Path | None = Path(_env("SSL_CERT_FILE")) if _env("SSL_CERT_FILE") else None
    ssl_key_file: Path | None = Path(_env("SSL_KEY_FILE")) if _env("SSL_KEY_FILE") else None
    erp_db_dir: Path = Path(_env("ERP_DB_DIR", r"C:\ERP_DB"))
    download_dir: Path = Path(_env("DOWNLOAD_DIR", r"C:\ERP_DB\downloads"))
    chrome_profile_dir: Path = Path(_env("CHROME_PROFILE_DIR", r"C:\ERP_DB\chrome_profile"))
    sqlite_db_path: Path = Path(_env("SQLITE_DB_PATH", r"C:\ERP_DB\learned_data.db"))
    imap_server: str = _env("IMAP_SERVER", "imap.gmail.com")
    email_id: str = _env("EMAIL_ID")
    email_pw: str = _env("EMAIL_PW")
    password_reset_mail_domain: str = _env("PASSWORD_RESET_MAIL_DOMAIN", "dae-seung.co.kr")
    password_reset_smtp_server: str = _env("PASSWORD_RESET_SMTP_SERVER", "35.216.76.148")
    password_reset_smtp_port: int = _env_int("PASSWORD_RESET_SMTP_PORT", 25)
    password_reset_smtp_user: str = _env("PASSWORD_RESET_SMTP_USER", _env("EMAIL_ID").split("@")[0])
    password_reset_smtp_pw: str = _env("PASSWORD_RESET_SMTP_PW", _env("EMAIL_PW"))
    password_reset_from: str = _env("PASSWORD_RESET_FROM", _env("EMAIL_ID") or "noreply@dae-seung.co.kr")
    gemini_api_key: str = _env("GEMINI_API_KEY")
    print_target_pyeongtaek: str = _env("PRINT_TARGET_PYEONGTAEK")
    print_target_gimje: str = _env("PRINT_TARGET_GIMJE")
    print_target_pdf: str = _env("PRINT_TARGET_PDF", "Microsoft Print to PDF")
    worker_gui_concurrency: int = _env_int("WORKER_GUI_CONCURRENCY", 1)
    legacy_manager_path: Path = _legacy_manager_path()
    erp_output_dir: Path = Path(_env("ERP_OUTPUT_DIR", r"C:\ERP_DB\erp_outputs"))
    erp_print_target: str = _env("ERP_PRINT_TARGET", _env("PRINT_TARGET_PDF", "Microsoft Print to PDF"))
    erp_execute_enabled: bool = _env("ERP_EXECUTE_ENABLED", "1").lower() not in {"0", "false", "no", "off"}
    erp_execution_mode: str = _env("ERP_EXECUTION_MODE", "agent").lower()  # agent | server
    regular_auto_agent_ip: str = _env("REGULAR_AUTO_AGENT_IP")
    regular_auto_printer_key: str = _env("REGULAR_AUTO_PRINTER_KEY", "pyeongtaek").lower()
    regular_auto_enabled: bool = _env_bool("REGULAR_AUTO_ENABLED", bool(_env("REGULAR_AUTO_AGENT_IP")))
    regular_auto_interval_seconds: int = _env_int("REGULAR_AUTO_INTERVAL_SECONDS", 60)
    regular_auto_scan_limit: int = _env_int("REGULAR_AUTO_SCAN_LIMIT", 200)
    regular_auto_max_batch: int = _env_int("REGULAR_AUTO_MAX_BATCH", 20)
    regular_auto_result_email: str = _env("REGULAR_AUTO_RESULT_EMAIL", "ds1501@dae-seung.co.kr")
    regular_auto_result_email_enabled: bool = _env_bool("REGULAR_AUTO_RESULT_EMAIL_ENABLED", True)
    regular_auto_result_from: str = _env("REGULAR_AUTO_RESULT_FROM", _env("PASSWORD_RESET_FROM", _env("EMAIL_ID") or "noreply@dae-seung.co.kr"))
    regular_auto_result_smtp_server: str = _env("REGULAR_AUTO_RESULT_SMTP_SERVER", _env("PASSWORD_RESET_SMTP_SERVER", "35.216.76.148"))
    regular_auto_result_smtp_port: int = _env_int("REGULAR_AUTO_RESULT_SMTP_PORT", _env_int("PASSWORD_RESET_SMTP_PORT", 25))
    regular_auto_result_smtp_user: str = _env("REGULAR_AUTO_RESULT_SMTP_USER", _env("PASSWORD_RESET_SMTP_USER", _env("EMAIL_ID").split("@")[0]))
    regular_auto_result_smtp_pw: str = _env("REGULAR_AUTO_RESULT_SMTP_PW", _env("PASSWORD_RESET_SMTP_PW", _env("EMAIL_PW")))
    compuzone_id: str = _env("COMPUZONE_ID")
    compuzone_pw: str = _env("COMPUZONE_PW")
    compuzone_auto_quote_enabled: bool = _env_bool("COMPUZONE_AUTO_QUOTE_ENABLED", True)
    compuzone_headless: bool = _env_bool("COMPUZONE_HEADLESS", True)
    compuzone_login_url: str = _env("COMPUZONE_LOGIN_URL", "https://www.compuzone.co.kr/login/login.htm")
    compuzone_quote_url_template: str = _env(
        "COMPUZONE_QUOTE_URL_TEMPLATE",
        "https://www.compuzone.co.kr/form/form_assemble.htm?wd=&tb=iorder&from_where=internet_manager&order_state_no={order_no}&settle=settle",
    )
    compuzone_profile_dir: Path = Path(_env("COMPUZONE_PROFILE_DIR", r"C:\ERP_DB\compuzone_chrome_profile"))
    compuzone_timeout_ms: int = _env_int("COMPUZONE_TIMEOUT_MS", 30000)


settings = Settings()
