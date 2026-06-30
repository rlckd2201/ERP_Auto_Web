from __future__ import annotations

import json
from types import SimpleNamespace

from app import notifications


def test_send_mail_outbox_records_pdf_attachment(tmp_path, monkeypatch):
    pdf = tmp_path / "voucher.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    outbox = tmp_path / "outbox"

    monkeypatch.setattr(
        notifications,
        "settings",
        SimpleNamespace(
            mail_outbox_dir=outbox,
            smtp_from="sender@example.com",
            smtp_user="",
            smtp_host="",
            smtp_port=25,
            smtp_starttls=False,
            smtp_password="",
        ),
    )

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
    assert payload["attachments"] == [{"filename": "voucher.pdf", "content_type": "application/pdf"}]
