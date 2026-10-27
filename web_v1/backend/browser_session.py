"""Verified accounting-login ownership for browsers behind a shared portal IP."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from contextlib import closing
from datetime import datetime

from fastapi import HTTPException

from .setup_state import RECENT_HEARTBEAT_SECONDS, get_conn

SESSION_HEADER = "x-accounting-session"
SESSION_SECONDS = 12 * 60 * 60


def _schema(conn) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS browser_sessions (
        token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
        credential_tag TEXT NOT NULL, agent_id TEXT NOT NULL DEFAULT '',
        expires_at REAL NOT NULL
    )""")


def _credential_tag(digest: str, password: str) -> str:
    # A password change invalidates existing sessions without storing credentials.
    return hmac.new(digest.encode(), str(password).encode(), hashlib.sha256).hexdigest()


def _owned_agent(conn, user_id: str, preferred_ip: str = ""):
    rows = conn.execute("SELECT agent_id, client_ip, last_seen FROM agent_profiles WHERE user_id = ?",
                        (user_id,)).fetchall()
    recent = []
    for row in rows:
        try:
            age = (datetime.now() - datetime.fromisoformat(row["last_seen"])).total_seconds()
        except (ValueError, TypeError):
            continue
        if row["client_ip"] and 0 <= age <= RECENT_HEARTBEAT_SECONDS:
            recent.append(row)
    # An identified local PC stays selected even while its Agent is restarting;
    # do not silently reroute a direct login to the user's other online PC.
    at_ip = [row for row in rows if preferred_ip and row["client_ip"] == preferred_ip]
    candidates = at_ip or recent
    # Never choose the most recent of multiple PCs or another user's PC.
    return candidates[0] if len(candidates) == 1 else None


def create_browser_session(user_id: str, preferred_ip: str = "") -> str:
    """Call only after accounting password verification (including initial change)."""
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    with closing(get_conn()) as conn, conn:
        _schema(conn)
        user = conn.execute("SELECT pw, is_initial FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user or user["is_initial"]:
            raise HTTPException(401, "회계 계정의 비밀번호 확인이 필요합니다.")
        profile = _owned_agent(conn, user_id, preferred_ip)
        now = time.time()
        conn.execute("DELETE FROM browser_sessions WHERE expires_at <= ?", (now,))
        conn.execute("INSERT INTO browser_sessions VALUES (?, ?, ?, ?, ?)",
                     (digest, user_id, _credential_tag(digest, user["pw"]),
                      profile["agent_id"] if profile else "", now + SESSION_SECONDS))
        conn.commit()
    return token


def resolve_browser_session(token: str) -> dict:
    if not isinstance(token, str) or len(token) != 43 or any(c not in
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in token):
        raise HTTPException(401, "회계 계정으로 다시 로그인해 주세요.")
    digest = hashlib.sha256(token.encode()).hexdigest()
    with closing(get_conn()) as conn, conn:
        _schema(conn)
        row = conn.execute("""SELECT s.*, u.pw, u.is_initial FROM browser_sessions s
            JOIN users u ON u.id = s.user_id WHERE token_hash = ?""", (digest,)).fetchone()
        if (not row or row["expires_at"] <= time.time() or row["is_initial"] or
                not hmac.compare_digest(row["credential_tag"], _credential_tag(digest, row["pw"]))):
            raise HTTPException(401, "회계 로그인 시간이 만료되었습니다. 다시 로그인해 주세요.")
        agent_id = row["agent_id"]
        if not agent_id:
            candidate = _owned_agent(conn, row["user_id"])
            if candidate:
                agent_id = candidate["agent_id"]
                conn.execute("UPDATE browser_sessions SET agent_id = ? WHERE token_hash = ? AND agent_id = ''",
                             (agent_id, digest))
                conn.commit()
                agent_id = conn.execute("SELECT agent_id FROM browser_sessions WHERE token_hash = ?",
                                        (digest,)).fetchone()[0]
        # Pin the chosen Agent; never silently switch to a different PC later.
        profile = conn.execute("SELECT agent_id, client_ip FROM agent_profiles WHERE agent_id = ? AND user_id = ?",
                               (agent_id, row["user_id"])).fetchone()
        return {"user_id": row["user_id"], "agent_id": profile["agent_id"] if profile else "",
                "client_ip": profile["client_ip"] if profile else ""}


def revoke_browser_session(token: str) -> None:
    with closing(get_conn()) as conn, conn:
        _schema(conn)
        conn.execute("DELETE FROM browser_sessions WHERE token_hash = ?",
                     (hashlib.sha256(str(token).encode()).hexdigest(),))
        conn.commit()
