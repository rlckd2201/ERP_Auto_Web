from types import SimpleNamespace
from pathlib import Path

import pytest
pytest.importorskip("cryptography", reason="Install deploy/requirements-migration.txt for migration tests")
from cryptography.exceptions import InvalidTag

from agent import agent_worker as worker
from deploy import migrate_server as migration


def test_encrypted_bundle_roundtrip_and_tamper_rejection(tmp_path):
    args = SimpleNamespace(private=tmp_path / "private.pem", public=tmp_path / "public.pem")
    migration.keygen(args)
    plain = b'{"secret":"never-store-plaintext"}'
    bundle = migration.seal(plain, args.public.read_bytes())
    assert plain not in bundle
    assert migration.unseal(bundle, args.private.read_bytes()) == plain
    corrupted = bundle[:-1] + bytes([bundle[-1] ^ 1])
    with pytest.raises(InvalidTag):
        migration.unseal(corrupted, args.private.read_bytes())


@pytest.mark.parametrize("member", ["../outside", "C:/outside", "data\\outside", "/absolute"])
def test_archive_paths_cannot_escape_destination(tmp_path, member):
    with pytest.raises(ValueError):
        migration.safe_target(tmp_path, member)


def test_rewrite_only_source_data_paths_and_exact_secret_blobs():
    original = {"source_path": r"C:\ERP_DB\excel_voucher_web_data\uploads\a.xlsx",
                "password_blob": "dpapi:old", "agent_path": r"C:\ERP_Auto_Web\data\file.pdf",
                "other_path": r"C:\ERP_DB\excel_voucher_web_data_backup\x"}
    result = migration.replace_values(original, {"dpapi:old": "dpapi:new"},
                                      r"C:\ERP_DB\excel_voucher_web_data", r"C:\ERP_DB\finance_3011_data")
    assert result["password_blob"] == "dpapi:new"
    assert result["source_path"] == r"C:\ERP_DB\finance_3011_data\uploads\a.xlsx"
    assert result["agent_path"] == original["agent_path"]
    assert result["other_path"] == original["other_path"]


def test_import_refuses_existing_data(tmp_path):
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        migration.import_bundle(SimpleNamespace(data=tmp_path))


def test_export_closes_sqlite_snapshot_before_temp_cleanup(tmp_path, monkeypatch):
    import sqlite3
    import psutil
    import tempfile
    source = tmp_path / "source"
    source.mkdir()
    with sqlite3.connect(source / "excel_voucher.sqlite3") as db:
        db.executescript("CREATE TABLE jobs(status TEXT,payload_json TEXT);"
                         "CREATE TABLE erp_credentials(erp_password_blob TEXT);"
                         "CREATE TABLE app_users(user_id TEXT,name TEXT,is_admin INTEGER);"
                         "CREATE TABLE job_events(id TEXT);")
        db.execute("INSERT INTO app_users VALUES ('rlckd9646','Existing Admin',1)")
    db.close()
    keys = SimpleNamespace(private=tmp_path / "private.pem", public=tmp_path / "public.pem")
    migration.keygen(keys)
    monkeypatch.setattr(psutil, "Process", lambda _: SimpleNamespace(environ=lambda: {}))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    migration.export_bundle(SimpleNamespace(code=tmp_path / "code", data=source, pid=1,
                                           public=keys.public, bundle=tmp_path / "bundle.enc"))
    assert (tmp_path / "bundle.enc").is_file()
    assert not list(tmp_path.glob("finance_snapshot_*"))
    import io
    import json
    import zipfile
    raw = migration.unseal((tmp_path / "bundle.enc").read_bytes(), keys.private.read_bytes())
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        metadata = json.loads(archive.read("migration.json"))
    assert metadata["environment"]["EXCEL_VOUCHER_ADMIN_NAME"] == "Existing Admin"


def _run_update(tmp_path, target):
    return worker._execute_admin_command(
        {"command": "update-agent", "payload": {"target_server": target}},
        server="https://172.17.39.121:8081", agent_id="finance-agent", client_ip="172.17.30.243",
        verify_tls=False, print_mode="default-printer", printer_name="existing printer",
        print_wait_seconds=3, erp_mode="real", output_dir=tmp_path)


def test_agent_migration_validates_target_and_preserves_settings(tmp_path, monkeypatch):
    target = "https://172.16.19.105:3011"
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"web_public_origin": target})
    monkeypatch.setattr(worker.requests, "get", get)
    monkeypatch.setattr(worker, "_update_agent_files", lambda _: {})
    def install(**kwargs):
        calls.append(kwargs)
        return {}
    monkeypatch.setattr(worker, "_install_agent_task", install)
    monkeypatch.setattr(worker, "_schedule_agent_restart", lambda _: Path("restart.ps1"))
    result = _run_update(tmp_path, target)
    assert result["server"] == target
    assert calls[0][0] == target + "/api/settings"
    assert calls[0][1]["allow_redirects"] is False
    assert calls[1]["server"] == target
    assert calls[1]["printer_name"] == "existing printer"
    assert calls[1]["erp_mode"] == "real"
    assert calls[1]["client_ip"] == "172.17.30.243"


@pytest.mark.parametrize("target", ["http://172.16.19.105:3011", "https://user:password@host", "https://host/path", "https://host?query=1"])
def test_agent_migration_rejects_invalid_origin_before_updating(tmp_path, monkeypatch, target):
    monkeypatch.setattr(worker, "_update_agent_files", lambda _: pytest.fail("must not update"))
    with pytest.raises(ValueError):
        _run_update(tmp_path, target)


def test_agent_migration_keeps_old_server_on_wrong_target(tmp_path, monkeypatch):
    monkeypatch.setattr(worker.requests, "get", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: {"web_public_origin": "https://other"}))
    monkeypatch.setattr(worker, "_install_agent_task", lambda **k: pytest.fail("must not replace task"))
    monkeypatch.setattr(worker, "_update_agent_files", lambda _: pytest.fail("must not update"))
    with pytest.raises(RuntimeError, match="keeping current server"):
        _run_update(tmp_path, "https://172.16.19.105:3011")
