from __future__ import annotations

import json
import random
import sqlite3
import smtplib
import string
import uuid
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any

from .config import settings
from .versioning import expected_agent_bundle_hash


RECENT_HEARTBEAT_SECONDS = 20
ERP_BASE_DIR = Path(r"C:\Users\Public\AppData\Local\Younglimwon\KSystem ver.5 Genuine")
REQUIRED_COMPANIES = ["대승", "대승정밀", "일강"]
CERT_INSTALL_TOKEN = "__https_certificate__"
PRINTER_KEYS = {
    "pyeongtaek": "평택 프린터",
    "gimje": "김제 프린터",
    "pdf": "PDF 저장 프린터",
}
DEFAULT_USERS = [
    ("arci", "담당자", "eotmd12!@", 1),
    ("reum0009", "담당자", "eotmd12!@", 1),
    ("kimsanul", "담당자", "eotmd12!@", 1),
    ("hah4627", "담당자", "eotmd12!@", 1),
    ("tuy1120", "담당자", "eotmd12!@", 1),
    ("rlckd9646", "김기창", "eotmd12!@", 1),
]
INITIAL_PASSWORD = "eotmd12!@"
AUTH_RESET_MARKER = "fix120_initial_password_reset_eotmd12"


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_conn() -> sqlite3.Connection:
    settings.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.sqlite_db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, ddl: str) -> None:
    if column_name not in _columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def init_auth_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT,
                pw TEXT,
                is_initial BOOLEAN
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_codes (
                user_id TEXT PRIMARY KEY,
                code TEXT,
                expires_at TEXT,
                created_at TEXT
            )
            """
        )
        for user_id, name, password, is_initial in DEFAULT_USERS:
            conn.execute(
                "INSERT OR IGNORE INTO users (id, name, pw, is_initial) VALUES (?, ?, ?, ?)",
                (user_id, name, password, is_initial),
            )
        marker = conn.execute("SELECT value FROM auth_meta WHERE key = 'initial_password_reset_marker'").fetchone()
        if not marker or marker["value"] != AUTH_RESET_MARKER:
            conn.execute("UPDATE users SET pw = ?, is_initial = 1", (INITIAL_PASSWORD,))
            conn.execute(
                """
                INSERT INTO auth_meta (key, value, updated_at)
                VALUES ('initial_password_reset_marker', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (AUTH_RESET_MARKER, now_text()),
            )
        conn.commit()


def init_setup_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_profiles (
                agent_id TEXT PRIMARY KEY,
                user_id TEXT DEFAULT '',
                client_ip TEXT DEFAULT '',
                agent_host TEXT DEFAULT '',
                agent_user TEXT DEFAULT '',
                last_seen TEXT DEFAULT '',
                capabilities_json TEXT DEFAULT '{}',
                printer_mapping_json TEXT DEFAULT '{}',
                local_config_json TEXT DEFAULT '{}'
            )
            """
        )
        _ensure_column(conn, "agent_profiles", "client_ip", "client_ip TEXT DEFAULT ''")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS setup_install_jobs (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                companies_json TEXT DEFAULT '[]',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT '',
                result_json TEXT DEFAULT '{}'
            )
            """
        )
        conn.commit()


def authenticate_user(user_id: str, password: str) -> dict[str, Any] | None:
    init_auth_db()
    user_id = str(user_id or "").strip()
    password = str(password or "").strip()
    if not user_id or not password:
        return None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, is_initial FROM users WHERE id = ? AND pw = ?",
            (user_id, password),
        ).fetchone()
    if not row:
        return None
    return {"id": row["id"], "name": row["name"] or row["id"], "is_initial": bool(row["is_initial"])}


def _password_reset_email(user_id: str) -> str:
    if "@" in user_id:
        return user_id
    return f"{user_id}@{settings.password_reset_mail_domain}"


def _send_password_reset_code(email: str, code: str) -> None:
    msg = MIMEText(
        f"회계업무 자동화 WEB 비밀번호 변경 인증코드입니다.\n\n인증코드: {code}\n\n10분 안에 화면에 입력하고 새 비밀번호로 변경하세요.",
        _charset="utf-8",
    )
    msg["Subject"] = "[전산팀] 회계업무 자동화 WEB 비밀번호 변경 인증코드"
    msg["From"] = settings.password_reset_from
    msg["To"] = email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    with smtplib.SMTP(settings.password_reset_smtp_server, settings.password_reset_smtp_port, timeout=10) as smtp:
        smtp.ehlo()
        if smtp.has_extn("STARTTLS"):
            smtp.starttls()
            smtp.ehlo()
        if settings.password_reset_smtp_user and settings.password_reset_smtp_pw:
            smtp.login(settings.password_reset_smtp_user, settings.password_reset_smtp_pw)
        smtp.send_message(msg)


def request_password_reset_code(user_id: str) -> dict[str, Any] | None:
    init_auth_db()
    user_id = str(user_id or "").strip()
    if not user_id:
        return None
    code = "".join(random.choices(string.digits, k=6))
    created_at = now_text()
    expires_at = (datetime.now() + timedelta(minutes=10)).isoformat(timespec="seconds")
    with get_conn() as conn:
        row = conn.execute("SELECT id, name FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        email = _password_reset_email(str(row["id"]))
        conn.execute(
            """
            INSERT INTO password_reset_codes (user_id, code, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                code = excluded.code,
                expires_at = excluded.expires_at,
                created_at = excluded.created_at
            """,
            (user_id, code, expires_at, created_at),
        )
        conn.commit()
    _send_password_reset_code(email, code)
    return {"id": row["id"], "name": row["name"] or row["id"], "email": email}


def reset_password_with_code(user_id: str, code: str, new_password: str) -> dict[str, Any]:
    init_auth_db()
    user_id = str(user_id or "").strip()
    code = str(code or "").strip()
    new_password = str(new_password or "").strip()
    if not user_id or not code or not new_password:
        raise ValueError("아이디, 인증코드, 새 비밀번호를 모두 입력하세요.")
    if len(new_password) < 8:
        raise ValueError("새 비밀번호는 8자 이상으로 입력하세요.")
    if new_password == INITIAL_PASSWORD:
        raise ValueError("초기 비밀번호와 다른 새 비밀번호를 입력하세요.")
    with get_conn() as conn:
        row = conn.execute("SELECT id, name FROM users WHERE id = ?", (user_id,)).fetchone()
        reset = conn.execute("SELECT code, expires_at FROM password_reset_codes WHERE user_id = ?", (user_id,)).fetchone()
        if not row or not reset:
            raise ValueError("인증코드를 먼저 받아주세요.")
        try:
            expired = datetime.fromisoformat(str(reset["expires_at"])) < datetime.now()
        except Exception:
            expired = True
        if expired:
            raise ValueError("인증코드 유효시간이 지났습니다. 다시 받아주세요.")
        if str(reset["code"]) != code:
            raise ValueError("인증코드가 맞지 않습니다.")
        conn.execute("UPDATE users SET pw = ?, is_initial = 0 WHERE id = ?", (new_password, user_id))
        conn.execute("DELETE FROM password_reset_codes WHERE user_id = ?", (user_id,))
        conn.commit()
    return {"id": row["id"], "name": row["name"] or row["id"], "is_initial": False}


def change_initial_password(user_id: str, current_password: str, new_password: str) -> dict[str, Any]:
    init_auth_db()
    user_id = str(user_id or "").strip()
    current_password = str(current_password or "").strip()
    new_password = str(new_password or "").strip()
    if not user_id or not current_password or not new_password:
        raise ValueError("아이디, 현재 비밀번호, 새 비밀번호를 모두 입력하세요.")
    if len(new_password) < 8:
        raise ValueError("새 비밀번호는 8자 이상으로 입력하세요.")
    if new_password == INITIAL_PASSWORD:
        raise ValueError("초기 비밀번호와 다른 새 비밀번호를 입력하세요.")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, is_initial FROM users WHERE id = ? AND pw = ?",
            (user_id, current_password),
        ).fetchone()
        if not row:
            raise ValueError("현재 비밀번호가 맞지 않습니다.")
        conn.execute("UPDATE users SET pw = ?, is_initial = 0 WHERE id = ?", (new_password, user_id))
        conn.commit()
    return {"id": row["id"], "name": row["name"] or row["id"], "is_initial": False}


def record_agent_heartbeat(agent_id: str, capabilities: dict[str, Any] | None, client_ip: str = "") -> dict[str, Any]:
    init_setup_db()
    agent_id = str(agent_id or "").strip() or "unknown-agent"
    client_ip = str(client_ip or "").strip()
    capabilities = capabilities if isinstance(capabilities, dict) else {}
    agent_host = str(capabilities.get("agent_host") or "")
    agent_user = str(capabilities.get("agent_user") or "")
    seen = now_text()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO agent_profiles (
                agent_id, client_ip, agent_host, agent_user, last_seen, capabilities_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                client_ip = excluded.client_ip,
                agent_host = excluded.agent_host,
                agent_user = excluded.agent_user,
                last_seen = excluded.last_seen,
                capabilities_json = excluded.capabilities_json
            """,
            (agent_id, client_ip, agent_host, agent_user, seen, _json_dumps(capabilities)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM agent_profiles WHERE agent_id = ?", (agent_id,)).fetchone()
    return _row_to_profile(row) if row else {}


def touch_agent_seen(agent_id: str, client_ip: str = "") -> None:
    init_setup_db()
    agent_id = str(agent_id or "").strip()
    client_ip = str(client_ip or "").strip()
    if not agent_id:
        return
    seen = now_text()
    with get_conn() as conn:
        if client_ip:
            conn.execute(
                "UPDATE agent_profiles SET last_seen = ?, client_ip = ? WHERE agent_id = ?",
                (seen, client_ip, agent_id),
            )
        else:
            conn.execute("UPDATE agent_profiles SET last_seen = ? WHERE agent_id = ?", (seen, agent_id))
        conn.commit()


def _row_to_profile(row: sqlite3.Row | None) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "agent_id": row["agent_id"],
        "user_id": row["user_id"] or "",
        "client_ip": row["client_ip"] or "",
        "agent_host": row["agent_host"] or "",
        "agent_user": row["agent_user"] or "",
        "last_seen": row["last_seen"] or "",
        "capabilities": _json_loads(row["capabilities_json"], {}),
        "printer_mapping": _json_loads(row["printer_mapping_json"], {}),
        "local_config": _json_loads(row["local_config_json"], {}),
    }


def latest_agent_profile(agent_id: str = "", client_ip: str = "") -> dict[str, Any]:
    init_setup_db()
    agent_id = str(agent_id or "").strip()
    client_ip = str(client_ip or "").strip()
    with get_conn() as conn:
        if agent_id and client_ip:
            row = conn.execute(
                "SELECT * FROM agent_profiles WHERE agent_id = ? AND client_ip = ?",
                (agent_id, client_ip),
            ).fetchone()
        elif agent_id:
            row = conn.execute("SELECT * FROM agent_profiles WHERE agent_id = ?", (agent_id,)).fetchone()
        elif client_ip:
            row = conn.execute(
                "SELECT * FROM agent_profiles WHERE client_ip = ? ORDER BY last_seen DESC LIMIT 1",
                (client_ip,),
            ).fetchone()
        else:
            row = conn.execute("SELECT * FROM agent_profiles ORDER BY last_seen DESC LIMIT 1").fetchone()
    return _row_to_profile(row)


def _age_seconds(value: str) -> int | None:
    try:
        return int((datetime.now() - datetime.fromisoformat(value)).total_seconds())
    except Exception:
        return None


def _add_check(checks: list[dict[str, Any]], key: str, label: str, ok: bool, status: str, message: str, details: dict[str, Any] | None = None) -> None:
    checks.append(
        {
            "key": key,
            "label": label,
            "ok": bool(ok),
            "status": "정상" if ok else status,
            "message": message,
            "details": details or {},
        }
    )


def _printer_names(capabilities: dict[str, Any]) -> list[str]:
    setup = capabilities.get("setup") if isinstance(capabilities.get("setup"), dict) else {}
    names = setup.get("printers") if isinstance(setup.get("printers"), list) else []
    return [str(name) for name in names if str(name).strip()]


def _merged_printer_mapping(profile: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    capabilities = profile.get("capabilities") if isinstance(profile.get("capabilities"), dict) else {}
    setup = capabilities.get("setup") if isinstance(capabilities.get("setup"), dict) else {}
    cap_mapping = setup.get("printer_mapping") if isinstance(setup.get("printer_mapping"), dict) else {}
    stored_mapping = profile.get("printer_mapping") if isinstance(profile.get("printer_mapping"), dict) else {}
    for key in PRINTER_KEYS:
        value = stored_mapping.get(key) or cap_mapping.get(key) or ""
        if value:
            mapping[key] = str(value)
    return mapping


def setup_status(user_id: str = "", agent_id: str = "", client_ip: str = "") -> dict[str, Any]:
    client_ip = str(client_ip or "").strip()
    profile = latest_agent_profile(agent_id, client_ip)
    capabilities = profile.get("capabilities") if isinstance(profile.get("capabilities"), dict) else {}
    setup = capabilities.get("setup") if isinstance(capabilities.get("setup"), dict) else {}
    checks: list[dict[str, Any]] = []
    age = _age_seconds(str(profile.get("last_seen") or ""))
    agent_ok = bool(profile) and age is not None and age <= RECENT_HEARTBEAT_SECONDS
    _add_check(
        checks,
        "agent",
        "담당자 PC 필수 프로그램 연결",
        agent_ok,
        "미연결",
        "담당자 PC 필수 프로그램이 연결되어 있습니다." if agent_ok else "필수 프로그램 설치 파일을 다운로드해 실행해야 합니다.",
        {
            "age_seconds": age,
            "agent_host": profile.get("agent_host", ""),
            "agent_user": profile.get("agent_user", ""),
            "agent_client_ip": profile.get("client_ip", ""),
            "request_client_ip": client_ip,
        },
    )

    expected_hash = expected_agent_bundle_hash()
    current_hash = str(capabilities.get("agent_bundle_hash") or "")
    current_version = str(capabilities.get("agent_bundle_version") or "")
    agent_update_ok = agent_ok and bool(current_hash) and current_hash == expected_hash
    _add_check(
        checks,
        "agent_update",
        "\ub2f4\ub2f9\uc790 PC \ud544\uc218 \ud504\ub85c\uadf8\ub7a8 \ucd5c\uc2e0\ubc84\uc804",
        agent_update_ok,
        "\uc5c5\ub370\uc774\ud2b8\ud544\uc694",
        "\ub2f4\ub2f9\uc790 PC \ud544\uc218 \ud504\ub85c\uadf8\ub7a8\uc774 \ucd5c\uc2e0\uc785\ub2c8\ub2e4."
        if agent_update_ok
        else "\ud544\uc218 \ud504\ub85c\uadf8\ub7a8\uc774 \uc11c\ubc84 \ubc84\uc804\uacfc \ub2e4\ub985\ub2c8\ub2e4. \uc124\uce58 EXE \ud30c\uc77c\uc744 \uc2e4\ud589\ud558\uba74 \uc790\ub3d9\uc73c\ub85c \ucd5c\uc2e0 \ubc84\uc804\uc774 \ubc18\uc601\ub429\ub2c8\ub2e4.",
        {
            "current_hash": current_hash,
            "expected_hash": expected_hash,
            "current_version": current_version,
            "server_version": settings.app_version,
        },
    )

    packages = capabilities.get("packages") if isinstance(capabilities.get("packages"), list) else []
    package_failures = [str(item.get("name") or "") for item in packages if isinstance(item, dict) and not item.get("ok")]
    packages_ok = agent_ok and bool(packages) and not package_failures
    _add_check(
        checks,
        "agent_packages",
        "담당자 PC 필수 패키지",
        packages_ok,
        "설정필요",
        "필수 Python 패키지가 준비되었습니다." if packages_ok else f"필수 패키지 확인 필요: {', '.join(package_failures) or '필수 프로그램 업데이트 필요'}",
        {"failures": package_failures},
    )

    cert = setup.get("https_certificate") if isinstance(setup.get("https_certificate"), dict) else {}
    cert_ok = agent_ok and bool(cert.get("trusted_current_user") or cert.get("trusted_local_machine"))
    _add_check(
        checks,
        "https_certificate",
        "WEB HTTPS 인증서 신뢰",
        cert_ok,
        "설정필요",
        "현재 Windows 사용자 인증서 저장소에서 신뢰됩니다." if cert_ok else "WEB HTTPS 인증서를 현재 Windows 사용자 신뢰 저장소에 등록해야 합니다.",
        {
            "thumbprint": str(cert.get("thumbprint") or ""),
            "trusted_current_user": bool(cert.get("trusted_current_user")),
            "trusted_local_machine": bool(cert.get("trusted_local_machine")),
            "server_url": str(cert.get("server_url") or ""),
        },
    )

    erp_base = setup.get("erp_base") if isinstance(setup.get("erp_base"), dict) else {}
    erp_base_ok = agent_ok and bool(erp_base.get("exists"))
    _add_check(
        checks,
        "erp_base",
        "ERP 루트 폴더",
        erp_base_ok,
        "누락",
        str(erp_base.get("path") or ERP_BASE_DIR),
        {"path": str(erp_base.get("path") or ERP_BASE_DIR)},
    )

    companies = setup.get("companies") if isinstance(setup.get("companies"), dict) else {}
    for company in REQUIRED_COMPANIES:
        item = companies.get(company) if isinstance(companies.get(company), dict) else {}
        ok = agent_ok and bool(item.get("updater_exists"))
        _add_check(
            checks,
            f"company_{company}",
            f"ERP 법인 설치: {company}",
            ok,
            "누락",
            "ClientUpdater.exe 확인" if ok else f"{company}\\Updater\\ClientUpdater.exe가 없습니다.",
            {"path": str(item.get("updater_path") or "")},
        )

    erp_config = setup.get("config") if isinstance(setup.get("config"), dict) else {}
    if not erp_config:
        erp_config = capabilities.get("erp") if isinstance(capabilities.get("erp"), dict) else {}
    config_ok = agent_ok and bool(erp_config.get("ok"))
    _add_check(
        checks,
        "erp_config",
        "ERP config.ini 로그인 설정",
        config_ok,
        "설정필요",
        "INSTALL_* / CORP_* 설정 확인" if config_ok else "config.ini의 INSTALL_* / CORP_* 설정이 필요합니다.",
        {"config_path": str(erp_config.get("config_path") or "")},
    )

    expense_template = setup.get("expense_template") if isinstance(setup.get("expense_template"), dict) else {}
    expense_template_ok = agent_ok and bool(expense_template.get("ok"))
    _add_check(
        checks,
        "expense_template",
        "현금출금결의서 Excel 양식",
        expense_template_ok,
        "설정필요",
        str(expense_template.get("path") or r"%APPDATA%\양식_현금출금정산서.xlsx")
        if expense_template_ok
        else str(expense_template.get("message") or r"담당자 PC Roaming 경로에 양식_현금출금정산서.xlsx를 배치해야 합니다."),
        {
            "path": str(expense_template.get("path") or ""),
            "source": str(expense_template.get("source") or ""),
            "installed": bool(expense_template.get("installed")),
            "checked_paths": expense_template.get("checked_paths") if isinstance(expense_template.get("checked_paths"), list) else [],
        },
    )

    printer_names = _printer_names(capabilities)
    printer_mapping = _merged_printer_mapping(profile)
    default_printer = str(setup.get("default_printer") or capabilities.get("default_printer") or "").strip()
    for key, label in PRINTER_KEYS.items():
        selected = printer_mapping.get(key, "")
        installed = bool(selected) and (not printer_names or selected in printer_names)
        ok = agent_ok and installed
        _add_check(
            checks,
            f"printer_{key}",
            label,
            ok,
            "설정필요",
            selected if ok else f"{label} 매핑이 필요합니다.",
            {"selected": selected, "installed": installed},
        )

    output_dir = setup.get("output_dir") if isinstance(setup.get("output_dir"), dict) else {}
    output_ok = agent_ok and bool(output_dir.get("write_ok"))
    _add_check(
        checks,
        "output_dir",
        "PDF/전표 출력 저장 폴더",
        output_ok,
        "설정필요",
        str(output_dir.get("path") or settings.erp_output_dir),
        {"path": str(output_dir.get("path") or settings.erp_output_dir)},
    )

    display = setup.get("display") if isinstance(setup.get("display"), dict) else {}
    if not display:
        display = capabilities.get("display") if isinstance(capabilities.get("display"), dict) else {}
    display_ready = bool(display.get("ok") or display.get("recommended") or display.get("usable"))
    display_ok = agent_ok and display_ready
    display_message = (
        "권장 화면입니다."
        if display.get("recommended")
        else (
            "사용 가능한 1920x1080 이상 모니터가 감지되었습니다."
            if display_ready
            else "1920x1080 / 배율 100% 권장 환경이 필요합니다."
        )
    )
    _add_check(
        checks,
        "display",
        "화면 해상도 1920x1080 100%",
        display_ok,
        "설정필요",
        display_message,
        {"selected": display.get("selected") or {}, "monitors": display.get("monitors") or []},
    )

    missing_items = [check["label"] for check in checks if not check["ok"]]
    ready = not missing_items
    return {
        "ready": ready,
        "setup_required": not ready,
        "checks": checks,
        "agent_id": profile.get("agent_id", ""),
        "client_ip": client_ip,
        "agent_client_ip": profile.get("client_ip", ""),
        "last_seen": profile.get("last_seen", ""),
        "last_seen_age_seconds": age,
        "missing_items": missing_items,
        "required_companies": REQUIRED_COMPANIES,
        "printer_keys": [{"key": key, "label": label} for key, label in PRINTER_KEYS.items()],
        "capabilities": {
            "printers": printer_names,
            "default_printer": default_printer,
            "printer_mapping": printer_mapping,
            "erp_base": erp_base,
            "expense_template": expense_template,
            "installers": installers_status(),
            "agent_bundle": {
                "current_hash": current_hash,
                "expected_hash": expected_hash,
                "current_version": current_version,
                "server_version": settings.app_version,
            },
        },
        "user_id": user_id,
    }


def save_printer_mapping(mapping: dict[str, Any], agent_id: str = "", client_ip: str = "") -> dict[str, Any]:
    profile = latest_agent_profile(agent_id, client_ip)
    if not profile:
        raise ValueError("연결된 담당자 PC 필수 프로그램이 없습니다.")
    clean = {}
    for key in PRINTER_KEYS:
        value = str(mapping.get(key) or "").strip()
        if value:
            clean[key] = value
    with get_conn() as conn:
        conn.execute(
            "UPDATE agent_profiles SET printer_mapping_json = ? WHERE agent_id = ?",
            (_json_dumps(clean), profile["agent_id"]),
        )
        conn.commit()
    return {"agent_id": profile["agent_id"], "printer_mapping": clean}


def installers_dir() -> Path:
    return settings.erp_db_dir / "installers"


def _installer_candidates(company: str) -> list[Path]:
    base = installers_dir()
    return [
        base / f"{company}.zip",
        base / f"KSystem_{company}.zip",
        base / f"{company}_KSystem.zip",
        base / company / f"{company}.zip",
    ]


def find_installer(company: str) -> Path | None:
    for path in _installer_candidates(company):
        if path.exists() and path.is_file():
            return path
    return None


def installers_status() -> dict[str, Any]:
    return {
        "dir": str(installers_dir()),
        "companies": {company: bool(find_installer(company)) for company in REQUIRED_COMPANIES},
    }


def create_install_job(
    companies: list[str] | None = None,
    agent_id: str = "",
    client_ip: str = "",
    install_certificate: bool = False,
) -> dict[str, Any]:
    profile = latest_agent_profile(agent_id, client_ip)
    if not profile:
        raise ValueError("연결된 담당자 PC 필수 프로그램이 없습니다.")
    allowed = set(REQUIRED_COMPANIES)
    requested_companies = REQUIRED_COMPANIES if companies is None else companies
    selected = [company for company in requested_companies if company in allowed]
    if install_certificate:
        selected.append(CERT_INSTALL_TOKEN)
    if not selected and not install_certificate:
        selected = REQUIRED_COMPANIES[:]
    job_id = str(uuid.uuid4())
    created = now_text()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO setup_install_jobs (
                id, agent_id, companies_json, status, created_at, updated_at, result_json
            ) VALUES (?, ?, ?, 'pending', ?, ?, '{}')
            """,
            (job_id, profile["agent_id"], _json_dumps(selected), created, created),
        )
        conn.commit()
    return {"id": job_id, "agent_id": profile["agent_id"], "companies": selected, "status": "pending"}


def _active_install_job(conn: sqlite3.Connection, agent_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT * FROM setup_install_jobs
        WHERE agent_id = ? AND status IN ('pending', 'running')
        ORDER BY created_at ASC
        LIMIT 1
        """,
        (agent_id,),
    ).fetchone()


def ensure_auto_install_job(agent_id: str = "", client_ip: str = "") -> dict[str, Any] | None:
    profile = latest_agent_profile(agent_id, client_ip)
    if not profile:
        return None
    capabilities = profile.get("capabilities") if isinstance(profile.get("capabilities"), dict) else {}
    setup = capabilities.get("setup") if isinstance(capabilities.get("setup"), dict) else {}
    companies = setup.get("companies") if isinstance(setup.get("companies"), dict) else {}
    selected: list[str] = []
    for company in REQUIRED_COMPANIES:
        item = companies.get(company) if isinstance(companies.get(company), dict) else {}
        if not item.get("updater_exists") and find_installer(company):
            selected.append(company)
    cert = setup.get("https_certificate") if isinstance(setup.get("https_certificate"), dict) else {}
    if cert and not (cert.get("trusted_current_user") or cert.get("trusted_local_machine")):
        selected.append(CERT_INSTALL_TOKEN)
    if not selected:
        return None
    now = now_text()
    with get_conn() as conn:
        active = _active_install_job(conn, profile["agent_id"])
        if active:
            active_age = _age_seconds(str(active["updated_at"] or active["created_at"] or ""))
            if active["status"] == "running" and active_age is not None and active_age > 1800:
                conn.execute(
                    "UPDATE setup_install_jobs SET status = 'error', updated_at = ?, result_json = ? WHERE id = ?",
                    (now, _json_dumps({"ok": False, "message": "stale auto install job reset"}), active["id"]),
                )
                conn.commit()
            else:
                return {
                    "id": active["id"],
                    "agent_id": active["agent_id"],
                    "companies": _json_loads(active["companies_json"], []),
                    "status": active["status"],
                    "created_at": active["created_at"],
                    "updated_at": active["updated_at"],
                    "auto": False,
                }
        job_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO setup_install_jobs (
                id, agent_id, companies_json, status, created_at, updated_at, result_json
            ) VALUES (?, ?, ?, 'pending', ?, ?, '{}')
            """,
            (job_id, profile["agent_id"], _json_dumps(selected), now, now),
        )
        conn.commit()
    return {"id": job_id, "agent_id": profile["agent_id"], "companies": selected, "status": "pending", "created_at": now, "updated_at": now, "auto": True}


def claim_install_job(agent_id: str) -> dict[str, Any] | None:
    init_setup_db()
    agent_id = str(agent_id or "").strip()
    if not agent_id:
        return None
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM setup_install_jobs
            WHERE agent_id = ? AND status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (agent_id,),
        ).fetchone()
        if not row:
            return None
        updated = now_text()
        conn.execute(
            "UPDATE setup_install_jobs SET status = 'running', updated_at = ? WHERE id = ?",
            (updated, row["id"]),
        )
        conn.commit()
    return {
        "id": row["id"],
        "agent_id": row["agent_id"],
        "companies": _json_loads(row["companies_json"], []),
        "status": "running",
        "created_at": row["created_at"],
        "updated_at": updated,
    }


def complete_install_job(job_id: str, ok: bool, result: dict[str, Any] | None = None) -> dict[str, Any]:
    status = "done" if ok else "error"
    updated = now_text()
    with get_conn() as conn:
        conn.execute(
            "UPDATE setup_install_jobs SET status = ?, updated_at = ?, result_json = ? WHERE id = ?",
            (status, updated, _json_dumps(result or {}), job_id),
        )
        conn.commit()
    return {"ok": ok, "id": job_id, "status": status, "updated_at": updated}
