from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return default if value is None else value


def _env_int(name: str, default: int) -> int:
    value = _env(name, str(default)).strip()
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name, "1" if default else "0").strip().lower()
    return value not in {"", "0", "false", "no", "off"}


def default_accounting_date(today: date | None = None) -> str:
    today = today or date.today()
    return date(today.year, today.month, 20).isoformat()


@dataclass(frozen=True)
class ManagerProfile:
    key: str
    label: str
    company_name: str
    agent_id: str
    agent_ip: str
    bank_account_name: str = "보통예금"
    bank_summary_name: str = "신한은행"


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(_env("EXCEL_VOUCHER_DATA_DIR", str(BASE_DIR / "data")))
    target_agent_id: str = _env("EXCEL_VOUCHER_TARGET_AGENT_ID", "finance-agent-172-17-30-243")
    target_agent_ip: str = _env("EXCEL_VOUCHER_TARGET_AGENT_IP", "172.17.30.243")
    web_host: str = _env("EXCEL_VOUCHER_WEB_HOST", "0.0.0.0")
    web_port: int = _env_int("EXCEL_VOUCHER_WEB_PORT", 8081)
    web_public_origin: str = _env("EXCEL_VOUCHER_WEB_PUBLIC_ORIGIN", "https://172.17.39.121:8081")
    data_server_url: str = _env("EXCEL_VOUCHER_DATA_SERVER_URL", "http://127.0.0.1:18080")
    data_server_endpoint: str = _env("EXCEL_VOUCHER_DATA_SERVER_ENDPOINT", "/api/excel-voucher/jobs")
    data_server_timeout_seconds: int = _env_int("EXCEL_VOUCHER_DATA_SERVER_TIMEOUT_SECONDS", 10)
    forward_to_data_server: bool = _env_bool("EXCEL_VOUCHER_FORWARD_TO_DATA_SERVER", False)
    auth_required: bool = _env_bool("EXCEL_VOUCHER_AUTH_REQUIRED", False)
    initial_password: str = _env("EXCEL_VOUCHER_INITIAL_PASSWORD", "wowjd12!@")
    session_cookie_name: str = _env("EXCEL_VOUCHER_SESSION_COOKIE", "excel_voucher_session")

    groupware_db_host: str = _env("EXCEL_VOUCHER_GROUPWARE_DB_HOST", "172.16.19.33")
    groupware_db_port: int = _env_int("EXCEL_VOUCHER_GROUPWARE_DB_PORT", 3306)
    groupware_db_name: str = _env("EXCEL_VOUCHER_GROUPWARE_DB_NAME", "ksystem_yundong")
    groupware_db_user: str = _env("EXCEL_VOUCHER_GROUPWARE_DB_USER", "dlpadmin2")
    groupware_db_password: str = _env("EXCEL_VOUCHER_GROUPWARE_DB_PASSWORD", "rlarlckd12!@")
    groupware_sync_on_start: bool = _env_bool("EXCEL_VOUCHER_GROUPWARE_SYNC_ON_START", False)
    groupware_finance_dept_codes: str = _env(
        "EXCEL_VOUCHER_FINANCE_DEPT_CODES",
        "HQ22111000,HQ22112000,HQ22113000,HQ22114000",
    )
    groupware_mail_domain: str = _env("EXCEL_VOUCHER_GROUPWARE_MAIL_DOMAIN", "dae-seung.co.kr")

    smtp_host: str = _env("EXCEL_VOUCHER_SMTP_HOST", "35.216.76.148")
    smtp_port: int = _env_int("EXCEL_VOUCHER_SMTP_PORT", 25)
    smtp_user: str = _env("EXCEL_VOUCHER_SMTP_USER", "")
    smtp_password: str = _env("EXCEL_VOUCHER_SMTP_PASSWORD", "")
    smtp_from: str = _env("EXCEL_VOUCHER_SMTP_FROM", "admpdm@dae-seung.co.kr")
    smtp_starttls: bool = _env_bool("EXCEL_VOUCHER_SMTP_STARTTLS", True)
    mail_outbox_dir: Path = Path(_env("EXCEL_VOUCHER_MAIL_OUTBOX_DIR", str(data_dir / "mail_outbox")))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "excel_voucher.sqlite3"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"


settings = Settings()


def manager_profiles() -> dict[str, ManagerProfile]:
    agent_id = settings.target_agent_id
    agent_ip = settings.target_agent_ip
    return {
        "daeseung": ManagerProfile(
            key="daeseung",
            label="대승 담당자",
            company_name="대승",
            agent_id=agent_id,
            agent_ip=agent_ip,
        ),
        "daeseung_precision": ManagerProfile(
            key="daeseung_precision",
            label="대승정밀 담당자",
            company_name="대승정밀",
            agent_id=agent_id,
            agent_ip=agent_ip,
        ),
        "ilgwang": ManagerProfile(
            key="ilgwang",
            label="일강 담당자",
            company_name="일강",
            agent_id=agent_id,
            agent_ip=agent_ip,
        ),
        "jm": ManagerProfile(
            key="jm",
            label="제이엠 담당자",
            company_name="제이엠",
            agent_id=agent_id,
            agent_ip=agent_ip,
        ),
    }


def manager_profile(key: str) -> ManagerProfile:
    profiles = manager_profiles()
    return profiles.get(key) or profiles["daeseung"]
