from __future__ import annotations

import ast
import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from app import main
from app.main import _public_job_dump
from app.models import AgentEventRequest, JobRecord, VerificationCodeRequest
from app.storage import JobStore


def test_verification_request_visible_without_exposing_code(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    now = datetime(2026, 9, 17, 9, 0)
    job = JobRecord(
        id="verification-job",
        title="ERP voucher",
        requester="requester",
        company_key="daeseung",
        accounting_date="2026-09-20",
        source_filename="source.xlsx",
        status="running",
        progress=40,
        message="ERP email verification code required",
        target_agent_id="finance-agent",
        target_client_ip="127.0.0.1",
        created_at=now,
        updated_at=now,
        result={"verification_required": True},
    )
    public = _public_job_dump(job)
    assert public["result"]["verification_required"] is True

    stored = {**job.result, "verification_code": "12345"}
    public_with_code = _public_job_dump(job.model_copy(update={"result": stored}))
    assert "verification_code" not in public_with_code["result"]

    with store.connect() as conn:
        conn.execute(
            "INSERT INTO jobs (id, title, status, progress, message, result_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (job.id, job.title, job.status, job.progress, job.message, '{"verification_required":true}', now.isoformat(), now.isoformat()),
        )
    store.set_verification_code(job.id, "12345")
    assert store.consume_verification_code(job.id) == "12345"
    assert store.consume_verification_code(job.id) == ""
    assert store.get_job(job.id).result["verification_required"] is False


def test_agent_event_to_web_code_submission(tmp_path, monkeypatch):
    store = JobStore(tmp_path / "jobs.sqlite3")
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(main, "_require_user", lambda request: SimpleNamespace(user_id="requester"))
    now = datetime(2026, 9, 17, 9, 0).isoformat()
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO jobs (id, title, status, progress, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("job", "ERP voucher", "running", 35, now, now),
        )

    event = AgentEventRequest(
        status="running", progress=40, message="ERP email verification required",
        result={"verification_required": True},
    )
    visible_job = main.api_agent_job_event("job", event)["job"]
    assert visible_job["result"]["verification_required"] is True

    response = main.api_job_verification_code("job", VerificationCodeRequest(code="12345"), None)
    assert response["ok"] is True
    assert "verification_code" not in response["job"]["result"]
    assert main.api_agent_verification_code("job")["code"] == "12345"
    assert main.api_agent_verification_code("job")["code"] == ""
    assert store.get_job("job").result["verification_required"] is False


def test_erp_email_notice_then_code_entry_uses_web_provider():
    source = (Path(__file__).resolve().parents[2] / "manager_server" / "전표 자동화 프로그램(담당자용)_v6.2.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {"_window_text_blob", "_is_email_verification_window", "_is_login_failure_blocker", "_try_email_verification"}
    definitions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in definitions} == names

    class Control:
        def __init__(self, name=""):
            self.name = name
            self.actions = []

        def window_text(self):
            return self.name

        def is_visible(self):
            return True

        def is_enabled(self):
            return True

        def click_input(self):
            self.actions.append("click")

        def type_keys(self, value, **kwargs):
            self.actions.append(value)

    class Window(Control):
        def __init__(self, name, handle, controls):
            super().__init__(name)
            self.handle = handle
            self.controls = controls

        def descendants(self, control_type=None):
            if control_type == "Edit":
                return self.controls.get("Edit", [])
            if control_type == "Button":
                return self.controls.get("Button", [])
            return [item for group in self.controls.values() for item in group]

    confirm = Control("확인")
    notice = Window("Message", 1, {"Text": [Control("이메일(으)로 인증번호가 발송되었습니다.")], "Button": [confirm]})
    entry = Control()
    prompt = Window("K-System Genuine", 2, {"Text": [Control("인증번호")], "Edit": [entry]})
    active = [notice]
    requested = []
    state = {"handled": False, "acknowledged": set(), "prompt_seen": False, "missing_edit_logged": set(), "code": ""}
    logger = SimpleNamespace(info=lambda msg: None, warning=lambda msg: None)
    scope = {
        "re": re,
        "time": SimpleNamespace(sleep=lambda seconds: None),
        "self": SimpleNamespace(app=SimpleNamespace(top_window=lambda: active[0], windows=lambda visible: active[:]), logger=logger),
        "verification_provider": lambda: requested.append(True) or "12345",
        "verification_state": state,
    }
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "<erp-login-functions>", "exec"), scope)

    assert scope["_try_email_verification"]() is True
    assert confirm.actions == ["click"]
    assert requested == []
    active[:] = [prompt]
    assert scope["_is_email_verification_window"](prompt) is True
    assert scope["_is_login_failure_blocker"](prompt) is False
    assert scope["_try_email_verification"]() is True
    assert requested == [True]
    assert entry.actions == ["click", "^a{BACKSPACE}", "12345"]
    assert prompt.actions == ["{ENTER}"]
    assert state["handled"] is True


def test_erp_email_code_request_does_not_wait_for_uia_edit():
    source = (Path(__file__).resolve().parents[2] / "manager_server" / "전표 자동화 프로그램(담당자용)_v6.2.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {"_window_text_blob", "_try_email_verification"}
    definitions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in names]

    class Control:
        def __init__(self, text=""):
            self.text = text
            self.actions = []

        def window_text(self):
            return self.text

        def is_visible(self):
            return True

        def is_enabled(self):
            return True

        def click_input(self):
            self.actions.append("click")

        def type_keys(self, value, **kwargs):
            self.actions.append(value)

    class Window(Control):
        handle = 3

        def __init__(self):
            super().__init__("K-System Genuine")
            self.edit = None

        def descendants(self, control_type=None):
            if control_type == "Edit":
                return [self.edit] if self.edit else []
            if control_type == "Button":
                return []
            return [Control("인증번호")]

    prompt = Window()
    requested = []
    state = {"handled": False, "acknowledged": set(), "prompt_seen": False, "missing_edit_logged": set(), "code": ""}
    scope = {
        "re": re,
        "time": SimpleNamespace(sleep=lambda seconds: None),
        "self": SimpleNamespace(
            app=SimpleNamespace(top_window=lambda: prompt, windows=lambda visible: [prompt]),
            logger=SimpleNamespace(info=lambda msg: None, warning=lambda msg: None),
        ),
        "verification_provider": lambda: requested.append(True) or "12345",
        "verification_state": state,
    }
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "<erp-login-functions>", "exec"), scope)

    assert scope["_try_email_verification"]() is False
    assert requested == [True]
    assert state["prompt_seen"] is True
    prompt.edit = Control()
    assert scope["_try_email_verification"]() is True
    assert requested == [True]
    assert prompt.edit.actions == ["click", "^a{BACKSPACE}", "12345"]
    assert state["handled"] is True
