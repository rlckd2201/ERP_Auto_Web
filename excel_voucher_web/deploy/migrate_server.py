"""Offline finance migration; transfer only an authenticated encrypted bundle.

Run import under the same Windows identity as the destination web service.
The source database and files are never modified.
Requires cryptography in the migration environment, not in the web application.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import zipfile

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"FINANCE-MIGRATION-1\n"


def seal(data: bytes, public_key: bytes) -> bytes:
    public = serialization.load_pem_public_key(public_key)
    key, nonce = AESGCM.generate_key(bit_length=256), os.urandom(12)
    wrapped = public.encrypt(key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=MAGIC))
    header = MAGIC + struct.pack(">I", len(wrapped)) + wrapped + nonce
    return header + AESGCM(key).encrypt(nonce, data, header)


def unseal(data: bytes, private_key: bytes) -> bytes:
    if not data.startswith(MAGIC):
        raise ValueError("Not a finance migration bundle")
    offset = len(MAGIC)
    length = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    wrapped = data[offset:offset + length]
    offset += length
    nonce = data[offset:offset + 12]
    offset += 12
    private = serialization.load_pem_private_key(private_key, password=None)
    key = private.decrypt(wrapped, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=MAGIC))
    return AESGCM(key).decrypt(nonce, data[offset:], data[:offset])


def replace_values(value, secrets, old_root, new_root):
    if isinstance(value, dict):
        return {k: replace_values(v, secrets, old_root, new_root) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_values(v, secrets, old_root, new_root) for v in value]
    if isinstance(value, str):
        if value in secrets:
            return secrets[value]
        prefix = old_root.rstrip("\\/")
        if value.lower() == prefix.lower() or value.lower().startswith(prefix.lower() + "\\"):
            return new_root.rstrip("\\/") + value[len(prefix):]
    return value


def discover_secrets(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from discover_secrets(child)
    elif isinstance(value, list):
        for child in value:
            yield from discover_secrets(child)
    elif isinstance(value, str) and value.startswith(("dpapi:", "b64:")):
        yield value


def safe_target(root: Path, name: str) -> Path:
    destination = (root / name).resolve()
    if not destination.is_relative_to(root.resolve()) or ":" in name or "\\" in name:
        raise ValueError("Unsafe archive member")
    return destination


def keygen(args):
    private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    with args.private.open("xb") as f:
        f.write(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    with args.public.open("xb") as f:
        f.write(private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    print(json.dumps({"key_generated": True}))


def export_bundle(args):
    import psutil
    sys.path.insert(0, str(args.code / "excel_voucher_web"))
    from app.accounts import unprotect_secret

    with closing(sqlite3.connect(args.data / "excel_voucher.sqlite3")) as source:
        if source.execute("SELECT count(*) FROM jobs WHERE status NOT IN ('done','error')").fetchone()[0]:
            raise RuntimeError("Active jobs exist; migration refused")
        with tempfile.TemporaryDirectory(prefix="finance_snapshot_") as tmp:
            database = Path(tmp) / "excel_voucher.sqlite3"
            with closing(sqlite3.connect(database)) as snapshot:
                source.backup(snapshot)
                blobs = set(row[0] for row in snapshot.execute("SELECT erp_password_blob FROM erp_credentials"))
                for payload, in snapshot.execute("SELECT payload_json FROM jobs"):
                    blobs.update(discover_secrets(json.loads(payload)))
                secrets = {blob: unprotect_secret(blob) for blob in blobs if blob}
                unreadable = sum(not value for value in secrets.values())
                secrets = {blob: value for blob, value in secrets.items() if value}
                counts = {table: snapshot.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
                          for table in ("app_users", "jobs", "job_events", "erp_credentials")}
                admin_names = dict(snapshot.execute("SELECT user_id,name FROM app_users WHERE is_admin=1"))
            stream = io.BytesIO()
            manifest = {}
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                def add(name, content):
                    archive.writestr(name, content)
                    manifest[name] = hashlib.sha256(content).hexdigest()
                for folder in ("excel_voucher_web", "manager_server"):
                    for path in (args.code / folder).rglob("*"):
                        relative = path.relative_to(args.code)
                        if not path.is_file() or set(relative.parts) & {".venv", "__pycache__", ".git", ".pytest_cache", "data", "logs"}:
                            continue
                        add("code/" + relative.as_posix(), path.read_bytes())
                for path in args.data.rglob("*"):
                    if path.is_file() and not path.name.startswith("excel_voucher.sqlite3"):
                        add("data/" + path.relative_to(args.data).as_posix(), path.read_bytes())
                add("data/excel_voucher.sqlite3", database.read_bytes())
                environment = {k: v for k, v in psutil.Process(args.pid).environ().items() if k.startswith("EXCEL_VOUCHER_")}
                admin_id = environment.get("EXCEL_VOUCHER_ADMIN_USER_ID", "rlckd9646")
                if admin_id in admin_names:
                    environment["EXCEL_VOUCHER_ADMIN_NAME"] = admin_names[admin_id]
                metadata = {"source_data": str(args.data), "counts": counts, "secrets": secrets,
                            "unreadable_secrets": unreadable, "environment": environment, "sha256": manifest}
                archive.writestr("migration.json", json.dumps(metadata).encode())
            with args.bundle.open("xb") as f:
                f.write(seal(stream.getvalue(), args.public.read_bytes()))
    print(json.dumps({"exported": True, "counts": counts, "readable_secrets": len(secrets), "unreadable_secrets": unreadable,
                      "bundle_sha256": hashlib.sha256(args.bundle.read_bytes()).hexdigest()}))


def import_bundle(args):
    if args.data.exists():
        raise RuntimeError("Destination data directory exists; refusing to overwrite")
    raw = unseal(args.bundle.read_bytes(), args.private.read_bytes())
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        metadata = json.loads(archive.read("migration.json"))
        for name, digest in metadata["sha256"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("Archive content hash mismatch")
            prefix, relative = name.split("/", 1)
            root = args.code if prefix == "code" else args.data if prefix == "data" else None
            if root is None:
                raise ValueError("Unexpected archive prefix")
            safe_target(root, relative)
        for name in metadata["sha256"]:
            prefix, relative = name.split("/", 1)
            dest = safe_target(args.code if prefix == "code" else args.data, relative)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.read(name))

    sys.path.insert(0, str(args.code / "excel_voucher_web"))
    from app.accounts import protect_secret, unprotect_secret
    converted = {old: protect_secret(value) for old, value in metadata["secrets"].items()}
    for old, new in converted.items():
        if not new.startswith("dpapi:") or unprotect_secret(new) != metadata["secrets"][old]:
            raise RuntimeError("Destination DPAPI verification failed")
    with closing(sqlite3.connect(args.data / "excel_voucher.sqlite3")) as db, db:
        for old, new in converted.items():
            db.execute("UPDATE erp_credentials SET erp_password_blob=? WHERE erp_password_blob=?", (new, old))
        for job_id, source_path, payload, result in db.execute("SELECT id,source_path,payload_json,result_json FROM jobs").fetchall():
            replace = lambda v: replace_values(v, converted, metadata["source_data"], str(args.data))
            db.execute("UPDATE jobs SET source_path=?,payload_json=?,result_json=? WHERE id=?",
                       (replace(source_path), json.dumps(replace(json.loads(payload))), json.dumps(replace(json.loads(result))), job_id))
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Database integrity check failed")
        counts = {table: db.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0] for table in metadata["counts"]}
        if counts != metadata["counts"]:
            raise RuntimeError("Database record count mismatch")
    environment = metadata["environment"]
    from urllib.parse import urlsplit, urlunsplit
    upstream = urlsplit(environment.get("EXCEL_VOUCHER_DATA_SERVER_URL", ""))
    if upstream.hostname in {"127.0.0.1", "localhost"}:
        environment["EXCEL_VOUCHER_DATA_SERVER_URL"] = urlunsplit(upstream._replace(netloc="172.17.39.121:" + str(upstream.port or 80)))
    environment.update({"EXCEL_VOUCHER_DATA_DIR": str(args.data), "EXCEL_VOUCHER_MAIL_OUTBOX_DIR": str(args.data / "mail_outbox"),
                        "EXCEL_VOUCHER_WEB_HOST": "172.16.19.105", "EXCEL_VOUCHER_WEB_PORT": "3011",
                        "EXCEL_VOUCHER_WEB_PUBLIC_ORIGIN": "https://172.16.19.105:3011",
                        "EXCEL_VOUCHER_LEGACY_AUTH_DB_PATH": str(args.config.parent / "unused-legacy-auth.db"),
                        "EXCEL_VOUCHER_FAILURE_EMAIL_ENABLED": "0"})
    args.config.write_text(json.dumps(environment, indent=2), encoding="utf-8")
    report = {"imported": True, "identity": os.environ.get("USERNAME"), "counts": counts,
              "reencrypted_secrets": len(converted), "unreadable_source_secrets": metadata["unreadable_secrets"],
              "verified_files": len(metadata["sha256"])}
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["keygen", "export", "import"])
    for flag in ("code", "data", "private", "public", "bundle", "config", "report"):
        parser.add_argument("--" + flag, type=Path)
    parser.add_argument("--pid", type=int)
    args = parser.parse_args()
    {"keygen": keygen, "export": export_bundle, "import": import_bundle}[args.action](args)


if __name__ == "__main__":
    main()
