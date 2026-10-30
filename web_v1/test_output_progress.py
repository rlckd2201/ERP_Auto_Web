"""Read-only print evidence and explicit failed-only retry; no live ERP or printing."""
import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from web_v1.backend import output_progress as progress
from web_v1.backend.job_store import JobStore
from web_v1.backend.models import OutputSetRequest, JobCreateRequest, JobResponse
from web_v1.test_purchase_shared_execution import load, RequestError


KEYS = ["erp_voucher", "tax_invoice", "approval_docs", "expense_report"]
NAMES = ["01_전표.pdf", "02_세금계산서.pdf", "03_전자결재품의.pdf", "04_현금출금결의서.pdf"]


class OutputStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); (self.root / "erp_queue").mkdir()
        self.invoice = {"id": 277, "status": "처리완료", "data": {}}
        self.docs = []
        for key, name in zip(KEYS, NAMES):
            path = self.root / name; path.write_bytes(b"fixture")
            os.utime(path, (1, 1))
            self.docs.append(dict(key=key, label=key, filename=name, status="exists", paths=[str(path)]))
        self.addCleanup(patch.stopall)
        patch.object(progress, "settings", SimpleNamespace(erp_db_dir=self.root)).start()
        self.build = patch.object(progress, "build_output_set_status", side_effect=lambda *a, **kw: {"docs":self.docs}).start()
        self.task = dict(job_id="a", job_type="output_print", created_at=datetime.now().isoformat(),
                         completed_at=datetime.now().isoformat(), agent_status="error", printer_key="gimje", printer_name="Gimje printer",
                         print_files=[dict(invoice_id=277, file_index=i+1, filename=name) for i,name in enumerate(NAMES)],
                         completed_file_keys=["277:1", "277:2"], agent_result={"successes":[dict(printed_file_keys=["277:1","277:2"], print_results=[{"spooler_verified":True},{"spooler_verified":True}])],
                         "failures":[dict(invoice_id=277,file_index=3,error="Printer unavailable")]})

    def summary(self, **kw):
        return progress.processing_status(self.invoice, tasks=[self.task], **kw)

    def write_task(self):
        (self.root/"erp_queue/output_print_a.json").write_text(json.dumps(self.task),encoding="utf-8")

    def test_success_failure_and_unknown_are_distinct_and_read_only(self):
        result = self.summary()
        self.assertEqual([d["print"]["state"] for d in result["documents"]], ["sent","sent","failed","unknown"])
        self.assertEqual(result["retry_doc_keys"], ["approval_docs"])
        self.assertIn("Windows",result["notice"])
        self.build.assert_called_once_with(self.invoice,persist=False)
        self.assertNotIn("processing_status",self.invoice)

    def test_unverified_ack_is_not_spooler_verified_or_retryable(self):
        self.task["agent_result"]["successes"][0]["print_results"][0]["spooler_verified"] = False
        self.assertEqual(self.summary()["documents"][0]["print"]["state"], "submitted")
        self.assertNotIn("erp_voucher",self.summary()["retry_doc_keys"])

    def test_optional_missing_doc_does_not_shift_expense_status(self):
        self.task["print_files"] = [dict(invoice_id=277,file_index=1,filename=NAMES[0]),dict(invoice_id=277,file_index=3,filename=NAMES[3])]
        result = self.summary()
        self.assertEqual(result["documents"][3]["print"]["state"],"failed")
        self.assertEqual(result["documents"][2]["print"]["state"],"none")

    def test_new_partial_retry_preserves_other_document_history(self):
        later=copy.deepcopy(self.task); later.update(job_id="b",created_at=(datetime.now()+timedelta(seconds=10)).isoformat(),agent_status="done",completed_file_keys=["277:1"],
            print_files=[dict(invoice_id=277,file_index=1,filename=NAMES[2])],agent_result={"successes":[dict(printed_file_keys=["277:1"],print_results=[{"spooler_verified":True}])]})
        result=progress.processing_status(self.invoice,tasks=[later,self.task])
        self.assertEqual(result["retry_doc_keys"],[])
        self.assertEqual([d["print"].get("job_id") for d in result["documents"]], ["a","a","b","a"])

    def test_missing_pdf_and_active_task_block_retry(self):
        self.docs[2]["status"]="missing"
        self.assertEqual(self.summary()["retry_doc_keys"],[])
        self.docs[2]["status"]="exists"; self.task["agent_status"]="pending"
        self.assertTrue(self.summary()["active"]);self.assertEqual(self.summary()["retry_doc_keys"],[])

    def test_pending_job_before_disk_queue_blocks_double_click(self):
        job=SimpleNamespace(job_type="output_set",status="queued",payload={"action":"print_individual","invoice_ids":[277]})
        self.assertEqual(self.summary(pending_jobs=[job])["retry_doc_keys"],[])
        self.invoice["status"]="처리중"
        self.assertTrue(self.summary()["active"])

    def test_manual_done_without_voucher_is_not_claimed_as_erp_saved(self):
        self.docs[0]["status"]="missing"
        self.assertIn("미확인",self.summary()["erp_label"])
        self.invoice["last_error"]="[ERP_SAVE_CONFIRM_REQUIRED]"
        self.assertIn("저장 여부 확인",self.summary()["erp_label"])

    def test_regenerated_pdf_requires_review(self):
        os.utime(self.root/NAMES[0],(datetime.now().timestamp()+20,)*2)
        self.assertEqual(self.summary()["documents"][0]["print"]["state"],"changed")
        self.assertNotIn("erp_voucher",self.summary()["retry_doc_keys"])

    def test_stale_token_or_no_failed_files_rejected(self):
        self.write_task(); token=progress.processing_status(self.invoice)["retry_token"]
        self.assertEqual(progress.validate_retry(self.invoice,token),["approval_docs"])
        self.task["agent_status"]="pending";self.write_task()
        with self.assertRaises(ValueError):progress.validate_retry(self.invoice,token)
        self.task["agent_status"]="done";self.task["agent_result"]={};self.write_task()
        with self.assertRaises(ValueError):progress.validate_retry(self.invoice,progress.processing_status(self.invoice)["retry_token"])

    def test_corrupt_task_never_uses_stale_success_or_allows_retry(self):
        self.write_task(); progress.print_tasks(fresh=True)
        (self.root/"erp_queue/output_print_a.json").write_text("{",encoding="utf-8")
        tasks,complete=progress.print_tasks(fresh=True)
        self.assertFalse(complete);self.assertEqual(tasks,[])
        self.assertEqual(self.summary(complete=False)["retry_doc_keys"],[])

    def test_legacy_result_does_not_infer_individual_success(self):
        self.task.update(completed_file_keys=[],agent_result={"successes":[{"printed_files":["old.pdf"]}]})
        self.assertTrue(all(d["print"]["state"]=="unknown" for d in self.summary()["documents"]))
        self.assertEqual(self.summary()["retry_doc_keys"],[])


class RetryEndpointTests(unittest.TestCase):
    def setUp(self):
        self.store=JobStore(); self.worker=Mock(); self.validate=Mock(return_value=["expense_report"])
        self.setup=dict(agent_id="requester",client_ip="172.16.10.18",capabilities={"printer_mapping":{"gimje":"Gimje printer"}})
        self.identity=Mock(return_value={"user_id":"hah4627"})
        self.queue_expense=Mock(side_effect=AssertionError("Retry must not generate expense or enter ERP"))
        self.ns=load("web_v1/backend/app.py",{"_retry_failed_output","create_output_set_job"},dict(
            OutputSetRequest=OutputSetRequest,JobResponse=JobResponse,JobCreateRequest=JobCreateRequest,Request=object,
            HTTPException=RequestError,_browser_identity=self.identity,retry_lock=progress.retry_lock,
            validate_retry=self.validate,job_store=self.store,worker=self.worker,
            get_invoice=Mock(return_value={"id":277}),require_setup_ready=Mock(return_value=self.setup),
            _request_processor_name=Mock(return_value="현시훈"),client_ip=lambda _:"172.16.10.18",
            settings=SimpleNamespace(regular_auto_agent_ip="172.17.30.243"),_invoice_is_zoom_billing=lambda _:True,
            _expense_report_exists=lambda _:False,_queue_zoom_expense_report_to_agent=self.queue_expense))
        self.body=OutputSetRequest(invoice_ids=[277],action="print_individual",printer_key="gimje",retry_token="a"*64,
            expected_printer_name="Gimje printer",selected_doc_keys=["erp_voucher","tax_invoice"])

    def call(self, **updates):
        return self.ns["create_output_set_job"](self.body.model_copy(update=updates),object())

    def test_retry_uses_only_server_failed_keys_existing_pdfs_and_selected_printer(self):
        result=self.call();payload=result.payload
        self.assertEqual(payload["selected_doc_keys"],["expense_report"])
        self.assertTrue(payload["existing_only"])
        self.assertEqual(payload["printer_name"],"Gimje printer")
        self.assertEqual(payload["target_agent_id"],"requester")
        self.queue_expense.assert_not_called();self.worker.submit.assert_called_once()

    def test_unauthenticated_wrong_scope_and_changed_mapping_never_submit(self):
        for changes in ({"invoice_ids":[277,278]},{"action":"merged_pdf"},{"expected_printer_name":""},{"expected_printer_name":"Other printer"}):
            with self.assertRaises(RequestError):self.call(**changes)
        self.identity.return_value=None
        with self.assertRaises(RequestError) as ctx:self.call()
        self.assertEqual(ctx.exception.status_code,401);self.worker.submit.assert_not_called()

    def test_stale_or_busy_validation_never_submits(self):
        self.validate.side_effect=ValueError("stale")
        with self.assertRaises(RequestError) as ctx:self.call()
        self.assertEqual(ctx.exception.status_code,409);self.worker.submit.assert_not_called()

    def test_second_request_observes_first_queued_job(self):
        self.call();self.call()
        pending=self.validate.call_args.kwargs["pending_jobs"]
        self.assertEqual(len(pending),1);self.assertEqual(pending[0].status,"queued")


class InvoiceListIntegrationTests(unittest.TestCase):
    def test_summary_sees_document_paths_before_public_payload_is_trimmed(self):
        # Actual DB list and API functions, backed by a fixture connection only.
        conn=Mock();conn.__enter__=Mock(return_value=conn);conn.__exit__=Mock(return_value=False)
        conn.cursor.return_value.fetchall.return_value=[{'id':277}]
        source={'id':277,'invoice_type':'purchase','data':{'erp_pdf_path':'actual.pdf','expense_report_pdf_path':'expense.pdf'},'raw':{'private':'fixture'}}
        dbns=load('web_v1/backend/invoice_db.py',{'list_invoices'},dict(init_db=Mock(),get_conn=lambda:conn,_row_to_invoice=lambda _:copy.deepcopy(source)))
        seen=[]
        def add(rows,**kwargs):
            seen.append(copy.deepcopy(rows[0]));rows[0]['processing_status']={'ok':True};return rows
        api=load('web_v1/backend/app.py',{'api_list_invoices'},dict(Query=lambda **kw:kw.get('default'),list_invoices=dbns['list_invoices'],add_processing_status=add,job_store=JobStore()))
        rows=api['api_list_invoices']('purchase',200)
        self.assertEqual(seen[0]['data']['erp_pdf_path'],'actual.pdf')
        self.assertEqual(rows,[{'id':277,'invoice_type':'purchase','processing_status':{'ok':True}}])
        self.assertNotIn('data',dbns['list_invoices']('purchase')[0])


if __name__ == "__main__": unittest.main()
