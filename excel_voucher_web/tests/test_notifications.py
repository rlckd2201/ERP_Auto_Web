from __future__ import annotations

import json
from datetime import datetime
from email.utils import getaddresses
from types import SimpleNamespace

from app import notifications
from app.models import JobEvent, JobRecord


def _fake_settings(tmp_path, outbox):
    return SimpleNamespace(
        data_dir=tmp_path / "data",
        mail_outbox_dir=outbox,
        smtp_from="sender@example.com",
        smtp_user="",
        smtp_host="",
        smtp_port=25,
        smtp_starttls=False,
        smtp_password="",
        admin_name="관리자",
        admin_email="ds1501@dae-seung.co.kr; another@example.com",
        support_email="ds1501@dae-seung.co.kr",
        smtp_from_name="재정전표자동화 시스템",
    )


def test_send_mail_outbox_records_pdf_attachment(tmp_path, monkeypatch):
    pdf = tmp_path / "voucher.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    outbox = tmp_path / "outbox"

    monkeypatch.setattr(notifications, "settings", _fake_settings(tmp_path, outbox))

    result = notifications.send_mail(
        "requester@example.com",
        "done",
        "completed",
        attachments=[pdf],
    )

    assert result["queued"] is True
    outbox_files = list(outbox.glob("*.json"))
    assert len(outbox_files) == 1
    payload = json.loads(outbox_files[0].read_text(encoding="utf-8"))
    assert "재정전표자동화 시스템" in payload["from"]
    assert payload["attachments"] == [{"filename": "voucher.pdf", "content_type": "application/pdf"}]


def test_failure_notification_goes_to_admin_and_requester_with_debug_files(tmp_path, monkeypatch):
    outbox = tmp_path / "outbox"
    source = tmp_path / "upload.xlsx"
    source.write_bytes(b"xlsx")
    log = tmp_path / "agent.log"
    log.write_text("ERP detailed log", encoding="utf-8")
    pdf = tmp_path / "voucher.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(notifications, "settings", _fake_settings(tmp_path, outbox))

    now = datetime(2026, 7, 2, 10, 0, 0)
    job = JobRecord(
        id="job123",
        title="대승 2026-05-20 수시결제 전표",
        requester="김기창",
        company_key="daeseung",
        accounting_date="2026-05-20",
        source_filename="upload.xlsx",
        status="error",
        progress=95,
        message="PDF 저장 실패",
        target_agent_id="finance-agent-172-17-30-243",
        target_client_ip="172.17.30.243",
        created_at=now,
        updated_at=now,
        payload={
            "requester": "김기창",
            "requester_email": "requester@example.com",
            "company_name": "대승",
            "line_count": 209,
            "debit_total": 1042607680,
            "credit_total": 1042607680,
            "erp_credentials": {
                "user_id": "12240413",
                "password": "As4908524!",
                "password_blob": "secret-blob",
            },
        },
        result={
            "error": "PDF 저장 실패",
            "agent_log_server_path": str(log),
            "erp_pdf_server_path": str(pdf),
        },
        error="PDF 저장 실패",
    )
    events = [
        JobEvent(id=1, job_id=job.id, status="queued", progress=5, message="서버 작업 큐 등록", created_at=now),
        JobEvent(id=2, job_id=job.id, status="running", progress=82, message="ERP 전표 저장이 완료되었습니다.", created_at=now),
    ]

    result = notifications.notify_job_failed(job, events=events, source_path=source)

    assert result["queued"] is True
    outbox_files = list(outbox.glob("*.json"))
    assert len(outbox_files) == 1
    payload = json.loads(outbox_files[0].read_text(encoding="utf-8"))
    assert payload["cc"] == ""
    assert "재정전표자동화 시스템" in payload["from"]
    # 오류 메일은 재정 자동화 관리자와 업로드 담당자에게 함께 간다.
    assert [address for _name, address in getaddresses([payload["to"]])] == [
        "ds1501@dae-seung.co.kr",
        "requester@example.com",
    ]
    assert payload["cc"] == ""
    attachment_names = {item["filename"] for item in payload["attachments"]}
    assert "upload.xlsx" in attachment_names
    assert "agent.log" in attachment_names
    assert "voucher.pdf" in attachment_names
    assert any(name.endswith("_diagnostic.txt") for name in attachment_names)
    assert "작업시작" in payload["body"]
    assert "출력완료" in payload["html_body"]

    diagnostic = next((tmp_path / "data" / "diagnostics").glob("*_diagnostic.txt"))
    diagnostic_text = diagnostic.read_text(encoding="utf-8")
    assert "As4908524!" not in diagnostic_text
    assert "secret-blob" not in diagnostic_text


def test_failure_notification_falls_back_when_requester_email_missing(tmp_path, monkeypatch):
    outbox = tmp_path / "outbox"
    monkeypatch.setattr(notifications, "settings", _fake_settings(tmp_path, outbox))
    now = datetime(2026, 7, 21, 15, 0, 0)
    job = JobRecord(
        id="admin-only-error",
        title="대승 전표 오류",
        requester="",
        company_key="daeseung",
        accounting_date="2026-07-21",
        source_filename="upload.xlsx",
        status="error",
        progress=95,
        message="ERP 오류",
        target_agent_id="finance-agent-172-17-30-243",
        target_client_ip="172.17.30.243",
        created_at=now,
        updated_at=now,
        payload={"requester_email": ""},
        result={"error": "ERP 오류"},
        error="ERP 오류",
    )

    result = notifications.notify_job_failed(job)

    assert result["queued"] is True
    payload = json.loads(next(outbox.glob("*.json")).read_text(encoding="utf-8"))
    # 담당자 주소가 없으면 관리자 설정 주소로 대체된다(중복은 제거).
    assert [address for _name, address in getaddresses([payload["to"]])] == [
        "ds1501@dae-seung.co.kr",
        "another@example.com",
    ]
    assert payload["cc"] == ""


def test_completion_notification_goes_only_to_requester(tmp_path, monkeypatch):
    # 성공 메일은 업로드한 담당자에게만 간다(관리자 주소를 넣지 않는다).
    outbox = tmp_path / "outbox"
    monkeypatch.setattr(notifications, "settings", _fake_settings(tmp_path, outbox))
    now = datetime(2026, 7, 27, 11, 0, 0)
    job = JobRecord(
        id="ok-job",
        title="대승 2026-07-20 수시결제 전표",
        requester="김기창",
        company_key="daeseung",
        accounting_date="2026-07-20",
        source_filename="upload.xlsx",
        status="done",
        progress=100,
        message="처리 완료",
        target_agent_id="finance-agent-172-17-30-243",
        target_client_ip="172.17.30.243",
        created_at=now,
        updated_at=now,
        payload={
            "requester": "김기창",
            "requester_email": "requester@example.com",
            "company_name": "대승",
        },
        result={},
    )

    result = notifications.notify_job_completed(job)

    assert result["queued"] is True
    payload = json.loads(next(outbox.glob("*.json")).read_text(encoding="utf-8"))
    assert [address for _name, address in getaddresses([payload["to"]])] == [
        "requester@example.com"
    ]
    assert payload["cc"] == ""
    assert "ds1501@dae-seung.co.kr" not in payload["to"]


def test_failure_recipients_dedupe_when_requester_is_admin(tmp_path, monkeypatch):
    # 담당자가 곧 관리자면 한 번만 보낸다.
    outbox = tmp_path / "outbox"
    monkeypatch.setattr(notifications, "settings", _fake_settings(tmp_path, outbox))
    now = datetime(2026, 7, 27, 11, 0, 0)
    job = JobRecord(
        id="dup-job",
        title="중복 수신자",
        requester="관리자",
        company_key="daeseung",
        accounting_date="2026-07-27",
        source_filename="upload.xlsx",
        status="error",
        progress=95,
        message="오류",
        target_agent_id="finance-agent-172-17-30-243",
        target_client_ip="172.17.30.243",
        created_at=now,
        updated_at=now,
        payload={"requester_email": "DS1501@dae-seung.co.kr"},
        result={"error": "오류"},
        error="오류",
    )

    assert notifications._failure_recipients(job) == ["ds1501@dae-seung.co.kr"]
