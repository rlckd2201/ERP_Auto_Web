"""Content identity for successful mail collection, independent of relay headers."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path


SUCCESS_OUTCOMES = frozenset({"saved", "duplicate"})


def _header(value: object) -> str:
    return str(make_header(decode_header(str(value or "")))).replace("\r\n", "\n").strip()


def _addresses(message: Message, name: str) -> list[str]:
    # Parse mailbox syntax before decoding display names. An encoded display
    # name may contain brackets/commas that are not address delimiters.
    values = [str(value) for value in message.get_all(name, [])]
    addresses = []
    for _, address in getaddresses(values):
        if not address or "@" not in address:
            raise ValueError("Unverifiable mail address")
        local, domain = address.rsplit("@", 1)
        if not local or not domain:
            raise ValueError("Incomplete mail address")
        addresses.append(local + "@" + domain.lower())
    return sorted(addresses)


def content_fingerprint(message: Message) -> str:
    """Return a conservative decoded-content identity, or '' for uncertain MIME.

    Do not remove numbers, URLs, HTML, whitespace inside text, or attachments.
    Relay headers, transfer encoding, multipart boundaries and attachment filenames
    do not identify the content. Original date and recipients remain significant.
    """
    try:
        sender = _addresses(message, "From")
        if not sender or not message.get("Date"):
            return ""
        date = parsedate_to_datetime(str(message["Date"]))
        if date.tzinfo is None:
            return ""
        bodies, attachments = [], []

        def visit(part: Message, depth: int = 0) -> None:
            if depth > 30 or part.defects:
                raise ValueError("Unverifiable MIME structure")
            content_type = part.get_content_type().lower()
            # Embedded EML has its own meaningful headers. Keep its full bytes
            # rather than accidentally comparing only the forwarded body.
            if part.get_content_maintype() == "message":
                payload = part.get_payload()
                if not isinstance(payload, list):
                    raise ValueError("Invalid embedded message")
                data = b"\0".join(item.as_bytes() for item in payload)
                attachments.append([content_type, "message", "", hashlib.sha256(data).hexdigest()])
                return
            if part.is_multipart():
                for child in part.get_payload():
                    visit(child, depth + 1)
                return
            data = part.get_payload(decode=True)
            if data is None or part.defects:
                raise ValueError("Undecodable MIME payload")
            disposition = part.get_content_disposition() or ""
            if (part.get_content_maintype() == "text"
                    and disposition != "attachment" and not part.get_filename()):
                # Strict decoding avoids collapsing different invalid bytes to
                # the same replacement character. Failure leaves normal collection.
                text = data.decode(part.get_content_charset() or "utf-8")
                text = text.replace("\r\n", "\n").replace("\r", "\n")
                bodies.append([content_type, text])
            else:
                attachments.append([content_type, disposition, str(part.get("Content-ID") or ""),
                                    hashlib.sha256(data).hexdigest()])

        visit(message)
        if not bodies and not attachments:
            return ""
        canonical = {
            "schema": 1, "from": sender, "to": _addresses(message, "To"),
            "cc": _addresses(message, "Cc"), "reply_to": _addresses(message, "Reply-To"),
            "subject": _header(message.get("Subject")),
            "date": date.astimezone(timezone.utc).isoformat(),
            "bodies": bodies, "attachments": sorted(attachments),
        }
        raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
        return "eml-v1:" + hashlib.sha256(raw).hexdigest()
    except (ValueError, TypeError, LookupError, UnicodeError, IndexError, AttributeError):
        return ""


class MailCollectionBusy(RuntimeError):
    pass


class MailContentStore:
    """Durable success receipts plus a crash-released cross-process collector lock.

    The lock covers a whole collection, including its existing JSON state, so two
    manual/automatic collectors cannot both crawl before either writes a receipt.
    No success is inferred from a pending attempt or a failed/partial collection.
    """
    def __init__(self, path: Path, scope: str):
        self.path = Path(path)
        self.scope = hashlib.sha256(scope.encode("utf-8")).hexdigest()
        self.connection = None
        self._lock_file = None
        self._locked = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._lock_file = self.path.with_suffix(".lock").open("a+b")
            self._lock_file.seek(0, 2)
            if self._lock_file.tell() == 0:
                self._lock_file.write(b"0")
                self._lock_file.flush()
            self._lock_file.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise MailCollectionBusy("다른 메일 수집 작업이 진행 중입니다. 다음 수집에서 다시 확인합니다.") from exc
            self._locked = True
            self.connection = sqlite3.connect(str(self.path), timeout=10)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS collected_content (
                    scope TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    first_message_key TEXT NOT NULL, completed_at TEXT NOT NULL,
                    outcome TEXT NOT NULL, duplicate_count INTEGER NOT NULL DEFAULT 0,
                    last_duplicate_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (scope, fingerprint)
                )
            """)
            self.connection.commit()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        try:
            if self.connection is not None:
                self.connection.close()
                self.connection = None
        finally:
            if self._lock_file is not None:
                try:
                    if self._locked:
                        self._lock_file.seek(0)
                        if os.name == "nt":
                            import msvcrt
                            msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                finally:
                    self._lock_file.close()
                    self._lock_file = None
                    self._locked = False

    def find(self, fingerprint: str) -> dict | None:
        if not fingerprint:
            return None
        row = self.connection.execute(
            "SELECT first_message_key, completed_at, outcome FROM collected_content "
            "WHERE scope=? AND fingerprint=?", (self.scope, fingerprint),
        ).fetchone()
        return dict(row) if row else None

    def remember(self, fingerprint: str, message_key: str, outcome: str) -> None:
        if not fingerprint or outcome not in SUCCESS_OUTCOMES:
            return
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO collected_content "
                "(scope, fingerprint, first_message_key, completed_at, outcome) VALUES (?, ?, ?, ?, ?)",
                (self.scope, fingerprint, message_key, datetime.now(timezone.utc).isoformat(), outcome),
            )

    def note_duplicate(self, fingerprint: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE collected_content SET duplicate_count=duplicate_count+1, last_duplicate_at=? "
                "WHERE scope=? AND fingerprint=?",
                (datetime.now(timezone.utc).isoformat(), self.scope, fingerprint),
            )
