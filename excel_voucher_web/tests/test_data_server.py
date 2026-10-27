from dataclasses import replace
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from openpyxl import Workbook

from app import data_server, main
from app.models import AgentHeartbeat
from app.storage import JobStore


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    config = replace(main.settings, data_dir=tmp_path, forward_to_data_server=False,
                     data_server_url="http://172.17.39.121:18080")
    monkeypatch.setattr(main, "settings", config)
    monkeypatch.setattr(data_server, "settings", config)
    store = JobStore(config.db_path)
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(data_server.requests, "post", lambda *a, **k: pytest.fail("Unexpected external request"))
    return store


def _upload_sample(monkeypatch):
    user = SimpleNamespace(user_id="finance-test", name="Finance", email="finance@example.invalid",
                           company_key="daeseung", is_admin=True, must_change_password=False)
    monkeypatch.setattr(main, "_current_user", lambda _: user)
    monkeypatch.setattr(main, "_resolve_erp_credentials_for_upload", lambda **kw: {})
    book = Workbook()
    book.active.append(["\uc5c5\uccb4\uba85", "\uc5c5\uccb4\ucf54\ub4dc", "\uae08\uc561"])
    book.active.append(["Test vendor", "A001", 12000])
    source = BytesIO()
    book.save(source)
    source.seek(0)
    with source:
        return main.api_upload_voucher(
            None, file=UploadFile(file=source, filename="sample.xlsx"), accounting_date="2026-10-20",
            requester="Finance", company_key="daeseung", erp_user_id="", erp_password="",
            use_saved_erp_credentials="0", remember_erp_credentials="0",
            resume_print_only="0", resume_management_save_print="0")


def test_disabled_forwarder_never_makes_request_even_with_legacy_url(isolated_store):
    assert data_server.forward_job_to_data_server(None) == {"ok": False, "skipped": True, "reason": "disabled"}


def test_empty_target_does_not_form_a_relative_endpoint(isolated_store, monkeypatch):
    monkeypatch.setattr(data_server, "settings", replace(data_server.settings, data_server_url="", forward_to_data_server=True))
    assert data_server.data_server_target_url() == ""
    assert data_server.forward_job_to_data_server(None)["reason"] == "unconfigured"


def test_upload_is_stored_and_claimed_locally_without_data_server(isolated_store, monkeypatch):
    response = _upload_sample(monkeypatch)
    job = isolated_store.get_job(response["id"])
    assert job.status == "queued"
    assert "data_server_forward" not in job.result
    assert isolated_store.get_source_path(job.id).is_file()
    claimed = isolated_store.claim_next(
        AgentHeartbeat(agent_id=job.target_agent_id, client_ip=job.target_client_ip), job.target_client_ip)
    assert claimed.id == job.id
    assert claimed.payload["debit_total"] == 12000
    assert claimed.status == "claimed"


def test_disabled_manual_forward_does_not_change_job_or_events(isolated_store, monkeypatch):
    response = _upload_sample(monkeypatch)
    before = isolated_store.get_job(response["id"])
    events = isolated_store.list_events(before.id)
    with pytest.raises(HTTPException) as error:
        main.api_forward_job(before.id)
    assert error.value.status_code == 409
    assert isolated_store.get_job(before.id) == before
    assert isolated_store.list_events(before.id) == events


def test_historical_failure_is_not_an_active_dependency_warning(isolated_store, monkeypatch):
    response = _upload_sample(monkeypatch)
    job = isolated_store.update_job(response["id"], result={"data_server_forward": {"ok": False}})
    diagnostics = main._job_diagnostics(job)
    assert diagnostics["data_server_forward_enabled"] is False
    assert "18080" not in diagnostics["recommended_action"]
    assert "\ub370\uc774\ud130 \uc11c\ubc84" not in diagnostics["recommended_action"]
    assert diagnostics["data_server_forward"] == {"ok": False}


def test_explicitly_configured_forwarding_still_strips_erp_credentials(isolated_store, monkeypatch):
    monkeypatch.setattr(data_server, "settings", replace(data_server.settings, forward_to_data_server=True,
                                                       data_server_url="https://archive.example.invalid"))
    sent = []
    def post(url, **kwargs):
        sent.append((url, kwargs))
        return SimpleNamespace(status_code=200, text="ok")
    monkeypatch.setattr(data_server.requests, "post", post)
    job = SimpleNamespace(id="job", status="queued", accounting_date="2026-10-20", requester="Finance",
                          company_key="daeseung", source_filename="sample.xlsx", target_agent_id="agent",
                          target_client_ip="172.17.30.243", payload={"erp_credentials": {"password": "test"}, "lines": []})
    assert data_server.forward_job_to_data_server(job)["ok"] is True
    assert sent[0][0] == "https://archive.example.invalid/api/excel-voucher/jobs"
    assert "erp_credentials" not in sent[0][1]["json"]["voucher"]
