from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .settings import settings


EMP_NO_COLUMNS = ("emp_no", "EMP_NO", "sabun", "SABUN", "emp_cd", "EMP_CD", "employee_no")
GROUPWARE_ID_COLUMNS = ("gw_id", "GW_ID", "login_id", "LOGIN_ID", "user_id", "USER_ID", "id", "ID")
ACTIVE_COLUMNS = ("use_yn", "USE_YN", "active_yn", "ACTIVE_YN", "enabled", "ENABLED", "del_yn", "DEL_YN")
EMAIL_COLUMNS = ("email", "EMAIL", "mail", "MAIL", "email_addr", "EMAIL_ADDR")
NAME_COLUMNS = ("emp_nm", "EMP_NM", "name", "NAME", "kor_nm", "KOR_NM", "user_nm", "USER_NM")
DEPT_CODE_COLUMNS = ("dept_cd", "DEPT_CD", "dept_code", "DEPT_CODE", "org_cd", "ORG_CD")
DEPT_NAME_COLUMNS = ("dept_nm", "DEPT_NM", "dept_name", "DEPT_NAME", "org_nm", "ORG_NM")
EMPLOYMENT_COLUMNS = ("retire_yn", "RETIRE_YN", "work_yn", "WORK_YN", "status", "STATUS", "use_yn", "USE_YN")

DEPT_COMPANY = {
    "HQ22111000": "daeseung",
    "HQ22112000": "daeseung_precision",
    "HQ22113000": "ilgwang",
    "HQ22114000": "jm",
}


@dataclass(frozen=True)
class GroupwareColumnMap:
    gw_emp_no: str
    gw_user_id: str
    gw_active: str | None
    gw_email: str | None
    emp_emp_no: str
    emp_name: str
    emp_dept_code: str
    emp_dept_name: str | None
    emp_employment: str | None


def groupware_enabled() -> bool:
    return bool(settings.groupware_db_user and settings.groupware_db_password)


def _connect() -> Any:
    try:
        import pymysql
    except ImportError as exc:  # pragma: no cover - depends on runtime package state
        raise RuntimeError("PyMySQL is required for MariaDB groupware sync.") from exc
    return pymysql.connect(
        host=settings.groupware_db_host,
        port=settings.groupware_db_port,
        user=settings.groupware_db_user,
        password=settings.groupware_db_password,
        database=settings.groupware_db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        read_timeout=10,
        write_timeout=10,
    )


def _table_columns(conn: Any, table: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(f"SHOW COLUMNS FROM `{table}`")
        return {str(row.get("Field") or "") for row in cur.fetchall()}


def _pick(columns: set[str], candidates: tuple[str, ...], *, required: bool = True) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    if required:
        raise RuntimeError(f"required column not found. candidates={', '.join(candidates)}")
    return None


def _q(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def _active_value(value: Any, *, inverted: bool = False) -> bool:
    text = str(value if value is not None else "").strip().lower()
    if not text:
        return True
    positive = text in {"1", "y", "yes", "true", "active", "enabled", "use", "사용", "재직"}
    negative = text in {"0", "n", "no", "false", "inactive", "disabled", "deleted", "delete", "퇴직"}
    if inverted:
        if negative:
            return True
        if positive:
            return False
    if negative:
        return False
    return True


def _mail_from_user_id(user_id: str, email: str) -> str:
    if email:
        return email
    domain = settings.groupware_mail_domain.strip().lstrip("@")
    if domain and user_id:
        return f"{user_id}@{domain}"
    return ""


def _company_key_for_dept(dept_code: str) -> str:
    return DEPT_COMPANY.get(dept_code) or "daeseung"


def _allowed_dept_codes() -> set[str]:
    return {part.strip() for part in settings.groupware_finance_dept_codes.split(",") if part.strip()}


def inspect_columns() -> GroupwareColumnMap:
    with _connect() as conn:
        gw_columns = _table_columns(conn, "gw_emp")
        emp_columns = _table_columns(conn, "ds_t_emp")
    return GroupwareColumnMap(
        gw_emp_no=_pick(gw_columns, EMP_NO_COLUMNS) or "",
        gw_user_id=_pick(gw_columns, GROUPWARE_ID_COLUMNS) or "",
        gw_active=_pick(gw_columns, ACTIVE_COLUMNS, required=False),
        gw_email=_pick(gw_columns, EMAIL_COLUMNS, required=False),
        emp_emp_no=_pick(emp_columns, EMP_NO_COLUMNS) or "",
        emp_name=_pick(emp_columns, NAME_COLUMNS) or "",
        emp_dept_code=_pick(emp_columns, DEPT_CODE_COLUMNS) or "",
        emp_dept_name=_pick(emp_columns, DEPT_NAME_COLUMNS, required=False),
        emp_employment=_pick(emp_columns, EMPLOYMENT_COLUMNS, required=False),
    )


def fetch_finance_users(limit: int = 1000) -> list[dict[str, Any]]:
    if not groupware_enabled():
        raise RuntimeError("groupware DB credentials are not configured.")
    columns = inspect_columns()
    allowed_depts = sorted(_allowed_dept_codes())
    if not allowed_depts:
        return []
    select_parts = [
        f"g.{_q(columns.gw_emp_no)} AS emp_no",
        f"g.{_q(columns.gw_user_id)} AS user_id",
        f"e.{_q(columns.emp_name)} AS name",
        f"e.{_q(columns.emp_dept_code)} AS dept_code",
    ]
    select_parts.append(f"g.{_q(columns.gw_active)} AS gw_active" if columns.gw_active else "NULL AS gw_active")
    select_parts.append(f"g.{_q(columns.gw_email)} AS email" if columns.gw_email else "NULL AS email")
    select_parts.append(f"e.{_q(columns.emp_dept_name)} AS dept_name" if columns.emp_dept_name else "NULL AS dept_name")
    select_parts.append(
        f"e.{_q(columns.emp_employment)} AS employment" if columns.emp_employment else "NULL AS employment"
    )
    placeholders = ", ".join(["%s"] * len(allowed_depts))
    query = f"""
        SELECT {", ".join(select_parts)}
        FROM `gw_emp` g
        JOIN `ds_t_emp` e ON g.{_q(columns.gw_emp_no)} = e.{_q(columns.emp_emp_no)}
        WHERE e.{_q(columns.emp_dept_code)} IN ({placeholders})
        LIMIT %s
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [*allowed_depts, max(1, min(int(limit), 5000))])
            rows = cur.fetchall()
    users: list[dict[str, Any]] = []
    for row in rows:
        user_id = str(row.get("user_id") or "").strip()
        dept_code = str(row.get("dept_code") or "").strip()
        gw_active = _active_value(row.get("gw_active"), inverted=str(columns.gw_active or "").lower() == "del_yn")
        employed = _active_value(row.get("employment"))
        if not user_id or not gw_active or not employed:
            continue
        email = _mail_from_user_id(user_id, str(row.get("email") or "").strip())
        users.append(
            {
                "user_id": user_id,
                "emp_no": str(row.get("emp_no") or "").strip(),
                "name": str(row.get("name") or user_id).strip(),
                "dept_code": dept_code,
                "dept_name": str(row.get("dept_name") or "").strip(),
                "email": email,
                "company_key": _company_key_for_dept(dept_code),
                "active": True,
            }
        )
    return users
