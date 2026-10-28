"""Exercise purchase routing without starting the backend or touching an ERP."""
import ast
import json
import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
MARKER = "[ERP_SAVE_CONFIRM_REQUIRED]"


def load(relative, names, namespace, class_name=""):
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8-sig"))
    body = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name).body if class_name else tree.body
    nodes = [n for n in body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(nodes) == len(names)
    for node in nodes:
        node.decorator_list = []
    namespace.update(Any=Any, Path=Path)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), relative, "exec"), namespace)
    return namespace


class RequestError(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.caller = dict(ready=True, user_id="tuy1120", agent_id="song", client_ip="172.17.30.15")
        self.executor = dict(ready=True, agent_id="shared243", client_ip="172.17.30.243")
        self.settings = SimpleNamespace(purchase_shared_user_ids="tuy1120", purchase_shared_agent_ip="172.17.30.243", purchase_shared_agent_id="shared243")
        self.lookup = Mock(return_value=self.executor)
        self.ns = load("web_v1/backend/purchase_execution.py", {"resolve_purchase_execution", "purchase_routing_payload"},
                       dict(re=re, settings=self.settings, setup_status=self.lookup, HTTPException=RequestError))

    def resolve(self):
        return self.ns["resolve_purchase_execution"](self.caller)

    def test_selected_user_runs_on_shared_agent(self):
        self.assertIs(self.resolve(), self.executor)
        self.lookup.assert_called_once_with(agent_id="shared243", client_ip="172.17.30.243")

    def test_unselected_users_keep_local_behavior(self):
        self.caller["user_id"] = "another-user"
        self.assertIs(self.resolve(), self.caller)
        self.lookup.assert_not_called()

    def test_user_match_is_exact_not_prefix_or_ip(self):
        for user in ("", "tuy", "tuy11200"):
            with self.subTest(user=user):
                self.caller["user_id"] = user
                self.assertIs(self.resolve(), self.caller)

    def test_user_list_accepts_case_and_separators(self):
        self.settings.purchase_shared_user_ids = "other; TUY1120,another"
        self.assertIs(self.resolve(), self.executor)

    def test_empty_allowlist_keeps_local(self):
        self.settings.purchase_shared_user_ids = ""
        self.assertIs(self.resolve(), self.caller)

    def test_wildcard_routes_every_named_and_future_user_to_shared_pc(self):
        self.settings.purchase_shared_user_ids = "*"
        for user_id in ("tuy1120", "hah4627", "rlckd9646", "reum0009", "future-user"):
            with self.subTest(user_id=user_id):
                self.caller.update(user_id=user_id, ready=False, missing_items=["local ERP"])
                self.assertIs(self.resolve(), self.executor)

    def test_wildcard_accepts_the_existing_separator_format(self):
        self.settings.purchase_shared_user_ids = "tuy1120; *\n hah4627"
        self.caller["user_id"] = " RLCKD9646 "
        self.assertIs(self.resolve(), self.executor)

    def test_all_users_still_requires_an_identified_caller(self):
        self.settings.purchase_shared_user_ids = "*"
        for value in ("", " ", None):
            with self.subTest(value=value):
                self.caller["user_id"] = value
                with self.assertRaises(RequestError) as caught:
                    self.resolve()
                self.assertEqual(caught.exception.status_code, 409)
        self.lookup.assert_not_called()

    def test_wildcard_is_a_whole_token_not_a_username_pattern(self):
        self.settings.purchase_shared_user_ids = "tuy*"
        self.assertIs(self.resolve(), self.caller)

    def test_all_users_never_falls_back_when_shared_pc_is_unavailable(self):
        self.settings.purchase_shared_user_ids = "*"
        self.caller["user_id"] = "rlckd9646"
        for changes in (dict(ready=False), dict(agent_id="other"), dict(client_ip="172.17.30.99")):
            with self.subTest(changes=changes):
                self.lookup.return_value = {**self.executor, **changes}
                with self.assertRaises(RequestError):
                    self.resolve()

    def test_all_users_requires_both_target_settings(self):
        self.settings.purchase_shared_user_ids = "*"
        self.caller["user_id"] = "rlckd9646"
        for field in ("purchase_shared_agent_ip", "purchase_shared_agent_id"):
            value = getattr(self.settings, field)
            setattr(self.settings, field, "")
            with self.assertRaises(RequestError):
                self.resolve()
            setattr(self.settings, field, value)

    def test_shared_execution_does_not_require_local_erp(self):
        self.caller.update(ready=False, missing_items=["local ERP"])
        self.assertIs(self.resolve(), self.executor)

    def test_unselected_local_setup_still_required(self):
        self.caller.update(ready=False, user_id="another", missing_items=["local ERP"])
        with self.assertRaises(RequestError) as caught:
            self.resolve()
        self.assertEqual(caught.exception.status_code, 409)

    def test_missing_shared_configuration_never_falls_back(self):
        for field in ("purchase_shared_agent_ip", "purchase_shared_agent_id"):
            old = getattr(self.settings, field)
            setattr(self.settings, field, "")
            with self.assertRaises(RequestError):
                self.resolve()
            setattr(self.settings, field, old)

    def test_offline_or_wrong_shared_agent_never_falls_back(self):
        for changes in (dict(ready=False), dict(agent_id="other"), dict(client_ip="172.17.30.99")):
            with self.subTest(changes=changes):
                self.lookup.return_value = {**self.executor, **changes}
                with self.assertRaises(RequestError) as caught:
                    self.resolve()
                self.assertEqual(caught.exception.status_code, 409)

    def test_output_owner_is_original_caller(self):
        result = self.ns["purchase_routing_payload"](self.caller, self.executor)
        self.assertEqual(result, dict(purchase_shared=True, output_agent_id="song", output_client_ip="172.17.30.15"))
        self.assertEqual(self.ns["purchase_routing_payload"](self.caller, self.caller), {})


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.caller = dict(ready=True, user_id="tuy1120", agent_id="song", client_ip="172.17.30.15",
                           capabilities={"printer_mapping": {"gimje": "Song chosen printer"}})
        self.executor = dict(ready=True, agent_id="shared243", client_ip="172.17.30.243")
        self.jobs = []
        def create(request):
            job = SimpleNamespace(**request, id=str(len(self.jobs)), to_response=lambda: request)
            self.jobs.append(job)
            return job
        self.store = SimpleNamespace(create=create, get=lambda _: self.jobs[0], add_event=Mock())
        self.invoice = dict(id=900, invoice_type="purchase")
        self.ns = load("web_v1/backend/app.py", {"create_purchase_one_click_job", "create_purchase_erp_input_job", "_one_click_output_payload", "_maybe_queue_one_click_output"}, dict(
            InvoiceIdsRequest=object, Request=object, JobResponse=object, HTTPException=RequestError,
            _purchase_execution_setup=lambda _: (self.caller, self.executor),
            _request_processor_name=lambda *args: "Song actual author", client_ip=lambda _: "172.17.30.15",
            get_invoice=lambda _: self.invoice, requires_erp_save_confirmation=lambda _: False,
            _require_purchase_departments=Mock(),
            _apply_purchase_analysis_payload=Mock(), _invoice_output_set_ready=Mock(return_value=False),
            _expense_report_exists=lambda _: True, add_invoice_log=Mock(), job_store=self.store,
            JobCreateRequest=lambda **kw: kw, worker=SimpleNamespace(submit=Mock())))
        routing = load("web_v1/backend/purchase_execution.py", {"purchase_routing_payload"}, {})
        self.ns["purchase_routing_payload"] = routing["purchase_routing_payload"]
        self.body = SimpleNamespace(invoice_ids=[900], processor="browser", output_target="gimje", analysis={})

    def test_one_click_routes_erp_but_keeps_author_and_printer(self):
        result = self.ns["create_purchase_one_click_job"](self.body, object())["payload"]
        self.assertEqual(result["target_agent_id"], "shared243")
        self.assertEqual(result["target_client_ip"], "172.17.30.243")
        self.assertEqual(result["processor"], "Song actual author")
        self.assertEqual(result["printer_name"], "Song chosen printer")
        self.assertEqual(result["output_agent_id"], "song")

    def test_all_user_policy_preserves_each_callers_author_and_selected_printer(self):
        routing = load("web_v1/backend/purchase_execution.py", {"resolve_purchase_execution"}, dict(
            re=re, HTTPException=RequestError,
            settings=SimpleNamespace(purchase_shared_user_ids="*", purchase_shared_agent_id="shared243",
                                     purchase_shared_agent_ip="172.17.30.243"),
            setup_status=Mock(return_value=self.executor)))
        self.ns["resolve_purchase_execution"] = routing["resolve_purchase_execution"]
        self.ns["_request_setup"] = lambda _: self.caller
        load("web_v1/backend/app.py", {"_purchase_execution_setup"}, self.ns)
        for user_id in ("tuy1120", "hah4627", "rlckd9646", "new-user"):
            with self.subTest(user_id=user_id):
                self.jobs.clear()
                printer = user_id + " selected printer"
                self.caller.update(user_id=user_id, agent_id=user_id + "-pc", ready=False,
                    capabilities={"printer_mapping": {"gimje": printer}})
                self.ns["_request_processor_name"] = lambda *args: user_id
                payload = self.ns["create_purchase_one_click_job"](self.body, object())["payload"]
                self.assertEqual(payload["target_agent_id"], "shared243")
                self.assertEqual(payload["processor"], user_id)
                self.assertEqual(payload["output_agent_id"], user_id + "-pc")
                self.assertEqual(payload["printer_name"], printer)
                self.ns["_maybe_queue_one_click_output"]("0")
                self.assertEqual(self.jobs[1].payload["target_agent_id"], user_id + "-pc")
                self.assertEqual(self.jobs[1].payload["printer_name"], printer)

    def test_direct_erp_routes_to_same_shared_agent(self):
        result = self.ns["create_purchase_erp_input_job"](self.body, object())["payload"]
        self.assertEqual(result["target_agent_id"], "shared243")
        self.assertTrue(result["purchase_shared"])

    def test_completed_documents_only_output_on_caller(self):
        self.ns["_invoice_output_set_ready"].return_value = True
        result = self.ns["create_purchase_one_click_job"](self.body, object())
        self.assertEqual(result["job_type"], "output_set")
        self.assertEqual(result["payload"]["target_agent_id"], "song")

    def test_post_save_guard_precedes_analysis_mutation_and_job_creation(self):
        self.ns["requires_erp_save_confirmation"] = lambda _: True
        self.body.analysis = {"items": [{}]}
        with self.assertRaises(RequestError):
            self.ns["create_purchase_one_click_job"](self.body, object())
        self.assertEqual(self.jobs, [])
        self.ns["_apply_purchase_analysis_payload"].assert_not_called()

    def test_followup_output_returns_to_requesting_pc(self):
        self.ns["create_purchase_one_click_job"](self.body, object())
        self.ns["_maybe_queue_one_click_output"]("0")
        result = self.jobs[1].payload
        self.assertEqual(result["target_agent_id"], "song")
        self.assertEqual(result["printer_name"], "Song chosen printer")
        self.assertEqual(result["processor"], "Song actual author")

    def test_ordinary_user_pipeline_remains_local(self):
        self.executor = self.caller
        result = self.ns["create_purchase_one_click_job"](self.body, object())["payload"]
        self.assertEqual(result["target_agent_id"], "song")
        self.assertNotIn("purchase_shared", result)
        self.ns["_maybe_queue_one_click_output"]("0")
        self.assertEqual(self.jobs[1].payload["target_agent_id"], "song")

    def test_worker_persists_execution_and_output_context_separately(self):
        self.ns["create_purchase_one_click_job"](self.body, object())
        job = self.jobs[0]
        queue_writer = Mock(return_value=Path("task.json"))
        worker_ns = load("web_v1/backend/worker.py", {"_run_purchase_erp_input"}, dict(
            JobRecord=object, resolve_user_display_name=lambda x: x, get_invoice=lambda _: self.invoice,
            validate_purchase_invoice_for_erp=Mock(), build_regular_erp_payload=Mock(), set_invoice_status=Mock(),
            ERROR="error", PROCESSING="processing", ERP_QUEUED="queued", settings=SimpleNamespace(erp_execution_mode="agent"),
            write_regular_erp_queue=Mock(), write_purchase_erp_queue=queue_writer), class_name="JobWorker")
        worker_ns["_run_purchase_erp_input"](SimpleNamespace(store=self.store), job)
        kwargs = queue_writer.call_args.kwargs
        self.assertEqual(kwargs["target_agent_id"], "shared243")
        self.assertTrue(kwargs["source_job_payload"]["purchase_shared"])
        self.assertEqual(kwargs["source_job_payload"]["output_agent_id"], "song")
        self.assertFalse(kwargs["source_job_payload"]["regular_auto"])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.ns = load("web_v1/agent/erp_agent.py", {"_erp_task_runtime_profile", "_apply_erp_runtime_profile", "_restore_erp_runtime_profile"},
                       dict(os=os, ERP_RUNTIME_PROFILE_FORCE_KEYS={"ERP_FAST_INPUT"}))

    def test_shared_purchase_uses_purchase_checks_and_longer_pdf_wait(self):
        profile, env = self.ns["_erp_task_runtime_profile"]({"job_type": "purchase_erp_input", "source_job_payload": {"purchase_shared": True}})
        self.assertEqual(profile, "purchase-shared")
        self.assertEqual(env["ERP_STRICT_VENDOR_SELECTION"], "1")
        self.assertEqual(env["ERP_FAST_INPUT"], "0")
        self.assertEqual(env["ERP_PRINT_VIEWER_TIMEOUT_SEC"], "15.0")

    def test_normal_purchase_and_regular_profiles_are_unchanged(self):
        name, env = self.ns["_erp_task_runtime_profile"]({"job_type": "purchase_erp_input"})
        self.assertEqual(name, "purchase-interactive")
        self.assertEqual(env["ERP_PRINT_VIEWER_TIMEOUT_SEC"], "4.0")
        name, env = self.ns["_erp_task_runtime_profile"]({"source_job_payload": {"regular_auto": True}})
        self.assertEqual(name, "regular-auto")
        self.assertEqual(env["ERP_FAST_MANAGEMENT"], "1")

    def test_shared_overrides_are_restored_before_the_next_regular_job(self):
        with patch.dict(os.environ, {"ERP_PRINT_VIEWER_TIMEOUT_SEC": "2"}, clear=True):
            old = self.ns["_apply_erp_runtime_profile"]({"ERP_PRINT_VIEWER_TIMEOUT_SEC": "15", "ERP_FAST_INPUT": "0"}, force=True)
            self.assertEqual(os.environ["ERP_PRINT_VIEWER_TIMEOUT_SEC"], "15")
            self.ns["_restore_erp_runtime_profile"](old)
            self.assertEqual(dict(os.environ), {"ERP_PRINT_VIEWER_TIMEOUT_SEC": "2"})


class SaveGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.job = "12345678-1234-1234-1234-123456789abc"
        self.invoice = dict(id=900, status="오류", erp_job_id=self.job, last_error="")
        self.ns = load("web_v1/backend/erp_runner.py", {"requires_erp_save_confirmation", "validate_purchase_invoice_for_erp"},
                       dict(json=json, re=re, settings=SimpleNamespace(erp_db_dir=self.root), ERP_SAVE_CONFIRM_REQUIRED=MARKER))
        queue = self.root / "erp_queue"
        queue.mkdir()
        self.path = queue / f"purchase_erp_{self.job}.json"
        self.task = dict(job_id=self.job, invoices=[dict(id=900)], agent_result=dict(message=MARKER + " PDF failed"))
        self.path.write_text(json.dumps(self.task), encoding="utf-8")

    def test_erased_error_is_recovered_from_current_failed_queue(self):
        self.assertTrue(self.ns["requires_erp_save_confirmation"](self.invoice))
        with self.assertRaisesRegex(RuntimeError, "ERP_SAVE_CONFIRM_REQUIRED"):
            self.ns["validate_purchase_invoice_for_erp"](self.invoice)

    def test_explicit_waiting_reset_does_not_reuse_old_failure(self):
        self.invoice["status"] = "대기중"
        self.assertFalse(self.ns["requires_erp_save_confirmation"](self.invoice))

    def test_another_invoice_or_job_cannot_supply_save_evidence(self):
        for key, value in (("job_id", "other"), ("invoices", [dict(id=901)])):
            task = {**self.task, key: value}
            self.path.write_text(json.dumps(task), encoding="utf-8")
            self.assertFalse(self.ns["requires_erp_save_confirmation"](self.invoice))

    def test_pre_save_error_does_not_get_post_save_guard(self):
        self.task["agent_result"]["message"] = "before save: vendor popup failed"
        self.path.write_text(json.dumps(self.task), encoding="utf-8")
        self.assertFalse(self.ns["requires_erp_save_confirmation"](self.invoice))

    def test_metadata_and_pdf_updates_preserve_only_save_confirmation_error(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.execute("create table invoices(id integer primary key,json_data text,pdf_path text,last_error text)")
        conn.execute("insert into invoices values(900,'{}','old.pdf',?)", (MARKER + " failed",))
        conn.commit()
        ns = load("web_v1/backend/invoice_db.py", {"update_invoice_json", "update_invoice_pdf_path"},
                  dict(init_db=Mock(), get_conn=lambda: conn, json=json, get_invoice=Mock(), add_invoice_log=Mock()))
        for fn, args in (("update_invoice_json", (900, {"analysis": True})), ("update_invoice_pdf_path", (900, "new.pdf"))):
            with self.subTest(fn=fn):
                ns[fn](*args)
                self.assertIn(MARKER, conn.execute("select last_error from invoices").fetchone()[0])
        conn.execute("update invoices set last_error='ordinary old error'")
        conn.commit()
        ns["update_invoice_json"](900, {"analysis": False})
        self.assertEqual(conn.execute("select last_error from invoices").fetchone()[0], "")


class QueueBindingTests(unittest.TestCase):
    def test_shared_purchase_and_regular_tasks_keep_the_same_agent_binding(self):
        from web_v1.backend import agent_queue
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for index, task_type in enumerate(("regular_erp_input", "purchase_erp_input"), start=1):
                payload = dict(job_id=str(index), job_type=task_type, agent_status="pending",
                               target_agent_id="shared243", target_client_ip="172.17.30.243",
                               created_at="2026-10-22T08:00:00", invoices=[dict(id=index)])
                (root / f"task{index}.json").write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(agent_queue, "queue_dir", return_value=root), patch.object(
                agent_queue, "get_invoice", side_effect=lambda i: dict(status=agent_queue.ERP_QUEUED, erp_job_id=str(i))
            ):
                agent_queue._reset_task_index(root)
                self.addCleanup(agent_queue._reset_task_index, Path("unused-test-index"))
                self.assertIsNone(agent_queue.claim_next_erp_task("song", {}, "172.17.30.15"))
                first = agent_queue.claim_next_erp_task("shared243", {}, "172.17.30.243")
                self.assertEqual(first["job_id"], "1")
                self.assertEqual(first["job_type"], "regular_erp_input")
                agent_queue.update_erp_task("1", "done", {})
                second = agent_queue.claim_next_erp_task("shared243", {}, "172.17.30.243")
                self.assertEqual(second["job_id"], "2")
                self.assertEqual(second["job_type"], "purchase_erp_input")
                self.assertIsNone(agent_queue.claim_next_erp_task("shared243", {}, "172.17.30.243"))


if __name__ == "__main__":
    unittest.main()
