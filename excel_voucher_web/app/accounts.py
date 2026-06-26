from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


PBKDF2_ITERATIONS = 260_000


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        method, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)
        if method != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(digest_text)
    except Exception:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def make_temporary_password(length: int = 12) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@dataclass(frozen=True)
class AccountUser:
    user_id: str
    emp_no: str
    name: str
    dept_code: str
    dept_name: str
    email: str
    company_key: str
    active: bool
    must_change_password: bool
    is_admin: bool

    def public_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "emp_no": self.emp_no,
            "name": self.name,
            "dept_code": self.dept_code,
            "dept_name": self.dept_name,
            "email": self.email,
            "company_key": self.company_key,
            "active": self.active,
            "must_change_password": self.must_change_password,
            "is_admin": self.is_admin,
        }


class AccountStore:
    def __init__(self, db_path: Path, *, initial_password: str) -> None:
        self.db_path = db_path
        self.initial_password = initial_password
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_users (
                    user_id TEXT PRIMARY KEY,
                    emp_no TEXT NOT NULL DEFAULT '',
                    name TEXT NOT NULL DEFAULT '',
                    dept_code TEXT NOT NULL DEFAULT '',
                    dept_name TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    company_key TEXT NOT NULL DEFAULT 'daeseung',
                    active INTEGER NOT NULL DEFAULT 1,
                    password_hash TEXT NOT NULL DEFAULT '',
                    must_change_password INTEGER NOT NULL DEFAULT 1,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login_at TEXT
                )
                """
            )
            self._ensure_column(conn, "app_users", "is_admin", "is_admin INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)")

    def _row_to_user(self, row: sqlite3.Row) -> AccountUser:
        return AccountUser(
            user_id=row["user_id"],
            emp_no=row["emp_no"] or "",
            name=row["name"] or row["user_id"],
            dept_code=row["dept_code"] or "",
            dept_name=row["dept_name"] or "",
            email=row["email"] or "",
            company_key=row["company_key"] or "daeseung",
            active=bool(row["active"]),
            must_change_password=bool(row["must_change_password"]),
            is_admin=bool(row["is_admin"]),
        )

    def _ensure_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, ddl: str) -> None:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = {str(row["name"]) for row in rows}
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")

    def get_user(self, user_id: str) -> AccountUser | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM app_users WHERE user_id = ?", (user_id.strip(),)).fetchone()
        return self._row_to_user(row) if row else None

    def upsert_groupware_user(self, user: dict[str, Any]) -> None:
        user_id = str(user.get("user_id") or "").strip()
        if not user_id:
            return
        timestamp = now_text()
        with self.connect() as conn:
            existing = conn.execute("SELECT password_hash, is_admin FROM app_users WHERE user_id = ?", (user_id,)).fetchone()
            password_hash = existing["password_hash"] if existing else hash_password(self.initial_password)
            must_change = 1 if not existing else None
            is_admin = 1 if user.get("is_admin", False) else (int(existing["is_admin"]) if existing else 0)
            if existing:
                conn.execute(
                    """
                    UPDATE app_users
                    SET emp_no = ?, name = ?, dept_code = ?, dept_name = ?, email = ?,
                        company_key = ?, active = ?, is_admin = ?, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (
                        str(user.get("emp_no") or ""),
                        str(user.get("name") or user_id),
                        str(user.get("dept_code") or ""),
                        str(user.get("dept_name") or ""),
                        str(user.get("email") or ""),
                        str(user.get("company_key") or "daeseung"),
                        1 if user.get("active", True) else 0,
                        is_admin,
                        timestamp,
                        user_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO app_users (
                        user_id, emp_no, name, dept_code, dept_name, email, company_key,
                        active, password_hash, must_change_password, is_admin, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        str(user.get("emp_no") or ""),
                        str(user.get("name") or user_id),
                        str(user.get("dept_code") or ""),
                        str(user.get("dept_name") or ""),
                        str(user.get("email") or ""),
                        str(user.get("company_key") or "daeseung"),
                        1 if user.get("active", True) else 0,
                        password_hash,
                        must_change,
                        is_admin,
                        timestamp,
                        timestamp,
                    ),
                )

    def upsert_admin_user(
        self,
        *,
        user_id: str,
        name: str,
        password: str,
        email: str = "",
        must_change_password: bool = True,
        overwrite_password: bool = False,
    ) -> None:
        user_id = str(user_id or "").strip()
        if not user_id:
            return
        timestamp = now_text()
        with self.connect() as conn:
            existing = conn.execute("SELECT user_id FROM app_users WHERE user_id = ?", (user_id,)).fetchone()
            if existing:
                password_sql = ", password_hash = ?, must_change_password = ?" if overwrite_password else ""
                password_values = (
                    (hash_password(password), 1 if must_change_password else 0) if overwrite_password else ()
                )
                conn.execute(
                    f"""
                    UPDATE app_users
                    SET name = ?, dept_code = 'IT', dept_name = '전산', email = ?,
                        company_key = 'daeseung', active = 1, is_admin = 1{password_sql}, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (name or user_id, email, *password_values, timestamp, user_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO app_users (
                        user_id, emp_no, name, dept_code, dept_name, email, company_key,
                        active, password_hash, must_change_password, is_admin, created_at, updated_at
                    )
                    VALUES (?, '', ?, 'IT', '전산', ?, 'daeseung', 1, ?, ?, 1, ?, ?)
                    """,
                    (
                        user_id,
                        name or user_id,
                        email,
                        hash_password(password),
                        1 if must_change_password else 0,
                        timestamp,
                        timestamp,
                    ),
                )

    def authenticate(self, user_id: str, password: str) -> AccountUser | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM app_users WHERE user_id = ?", (user_id.strip(),)).fetchone()
            if not row or not bool(row["active"]) or not verify_password(password, row["password_hash"]):
                return None
            conn.execute("UPDATE app_users SET last_login_at = ? WHERE user_id = ?", (now_text(), row["user_id"]))
        return self._row_to_user(row)

    def create_session(self, user_id: str, *, days: int = 7) -> str:
        token = secrets.token_urlsafe(32)
        created = datetime.now()
        expires = created + timedelta(days=days)
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO user_sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user_id, created.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")),
            )
        return token

    def user_for_session(self, token: str) -> AccountUser | None:
        if not token:
            return None
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT u.*
                FROM user_sessions s
                JOIN app_users u ON u.user_id = s.user_id
                WHERE s.token = ? AND s.expires_at > ?
                """,
                (token, now_text()),
            ).fetchone()
        return self._row_to_user(row) if row else None

    def delete_session(self, token: str) -> None:
        if not token:
            return
        with self.connect() as conn:
            conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM app_users WHERE user_id = ?", (user_id,)).fetchone()
            if not row or not verify_password(old_password, row["password_hash"]):
                return False
            conn.execute(
                """
                UPDATE app_users
                SET password_hash = ?, must_change_password = 0, updated_at = ?
                WHERE user_id = ?
                """,
                (hash_password(new_password), now_text(), user_id),
            )
        return True

    def set_temporary_password(self, user_id: str, temporary_password: str) -> AccountUser | None:
        user = self.get_user(user_id)
        if not user:
            return None
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE app_users
                SET password_hash = ?, must_change_password = 1, updated_at = ?
                WHERE user_id = ?
                """,
                (hash_password(temporary_password), now_text(), user_id),
            )
        return self.get_user(user_id)
