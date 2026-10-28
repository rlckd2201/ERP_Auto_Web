"""Approval fallback safety tests; no real DB, ERP, printer or groupware calls."""
import copy
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from web_v1.backend import approval_matching as matching
from web_v1.backend import approval_fetcher as fetcher
from web_v1.backend import approval_service as service
from web_v1.backend import invoice_db
from web_v1.test_purchase_shared_execution import load, RequestError


def invoice():
    return {"id": 277, "invoice_type": "purchase", "data": {"total_sum": 413120, "buyer_biz_no": "125-81-51622",
        "site_name": "일강1공장", "vendor_name": "컴퓨존", "order_no": "28929687", "quote_path": ""}}


def candidate(**changes):
    return {"doc_id": "180287", "doc_no": "기안2610-0000877", "title": "전산 소모품 구매 건(일강1공장)",
        "form_name": "일강 - (경영)기안용지", "drafter_name": "김산울", "drafter_account": "kimsanul",
        "approved_date": (date.today() - timedelta(days=6)).isoformat(), "status": "완료",
        "body": "5. 금액 : 413,120원 (V.A.T 포함)\n업체 : (주)컴퓨존\n일강1공장 견적서 (28929687)", **changes}


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.context = matching.invoice_context(invoice(), date.today().isoformat())

    def decide(self, rows, **kw):
        return matching.decide(rows, self.context, {"kimsanul"}, **kw)

    def test_exact_verified_single_candidate(self):
        result = self.decide([candidate()])
        self.assertEqual(result["status"], "matched")
        self.assertTrue(result["selected"]["matched_order"])

    def test_comma_and_plain_amount(self):
        for text in ("총 금액: 413,120원", "합계\n413120", "계\n413,120원", "5. 금액 : 413,120원"):
            self.assertIn(413120, matching.stated_totals(text))
        self.assertEqual(matching.amount_variants(413120), ["413,120", "413120"])

    def test_unit_price_or_account_number_is_not_total(self):
        for text in ("단가 413,120원", "계좌번호 413120", "총 금액 1413120원"):
            self.assertNotIn(413120, matching.stated_totals(text))

    def test_unknown_total_requires_review(self):
        self.assertEqual(self.decide([candidate(body="단가 413120원 · 일강1공장 · 컴퓨존")])["status"], "review")

    def test_price_duplicates_never_choose_first_newest_or_order_match(self):
        result = self.decide([candidate(), candidate(doc_id="2", body="합계 413120원 일강1공장 컴퓨존")])
        self.assertEqual(result["status"], "review")
        self.assertEqual(len(result["candidates"]), 2)

    def test_wrong_company_form_requires_review(self):
        self.assertEqual(self.decide([candidate(form_name="대승 - 기안용지")])["status"], "review")

    def test_missing_or_multiple_sites_require_review(self):
        for title, body in (("구매", "합계 413120원 컴퓨존"), ("일강1공장 일강2공장", "합계 413120원 컴퓨존")):
            self.assertEqual(self.decide([candidate(title=title, body=body)])["status"], "review")

    def test_wrong_site_total_order_and_account_are_excluded(self):
        for change in ({"title": "D1공장", "body": "합계 413120원 D1공장 컴퓨존"},
                       {"body": "합계 413121원 일강1공장 컴퓨존"},
                       {"body": "합계 413120원 일강1공장 컴퓨존 (11111111)"},
                       {"drafter_account": "outsider"}, {"drafter_account": ""}, {"status": "진행"}):
            with self.subTest(change=change):
                self.assertEqual(self.decide([candidate(**change)])["status"], "not_found")

    def test_completed_date_inclusive_thirty_days_not_drafted_date(self):
        for age, expected in ((7, "matched"), (9, "matched"), (17, "matched"), (30, "matched"), (31, "not_found"), (-1, "not_found")):
            self.assertEqual(self.decide([candidate(approved_date=(date.today()-timedelta(days=age)).isoformat(), drafted_date=date.today().isoformat())])["status"], expected)
        self.assertEqual(self.decide([candidate(approved_date="")])["status"], "not_found")

    def test_same_amount_candidate_from_extended_window_still_requires_choice(self):
        older = candidate(doc_id="older", approved_date=(date.today()-timedelta(days=17)).isoformat())
        self.assertEqual(self.decide([candidate(), older])["status"], "review")

    def test_exact_day_window_across_month_and_leap_year_boundaries(self):
        from urllib.parse import parse_qs, urlsplit
        from web_v1.backend.approval_browser import approval_search_url
        url = "https://gw.dae-seung.co.kr/app/approval/search?dateType=completedAt&docBody=413%2C120&searchOption=AND&page=2"
        for anchor, start in (("2026-03-01", "2026-01-30"), ("2024-03-01", "2024-01-31"), ("2026-01-01", "2025-12-02")):
            params = parse_qs(urlsplit(approval_search_url(url, anchor)).query)
            self.assertEqual(params["fromDate"], [start+"T00:00:00.000+09:00"])
            self.assertEqual(params["toDate"], [anchor+"T23:59:59.000+09:00"])
            self.assertEqual(params["docBody"], ["413,120"])
            self.assertEqual(params["dateType"], ["completedAt"])
            self.assertEqual(params["page"], ["0"])

    def test_truncated_and_conflicting_totals_never_auto_match(self):
        self.assertEqual(self.decide([candidate()], truncated=True)["status"], "review")
        self.assertEqual(self.decide([candidate(body=candidate()["body"]+"\n합계 900000원")])["status"], "review")

    def test_unknown_buyer_and_conflicting_site_reject_context(self):
        for changes in ({"buyer_biz_no": "000-00-00000"}, {"site_name": "D1공장"}, {"total_sum": -413120}):
            inv=invoice();inv["data"].update(changes)
            with self.assertRaises(ValueError): matching.validate_context(matching.invoice_context(inv,date.today().isoformat()))

    def test_public_metadata_excludes_body_and_bank_information(self):
        row=candidate(bank="private",body="private",result_url="private")
        result=matching.public_candidate(row)
        self.assertFalse({"body","bank","result_url"} & set(result))


class FallbackAndChoiceTests(unittest.TestCase):
    def setUp(self):
        self.inv=invoice()
        self.inv["data"].update(approval_fetch_status="review", approval_search_id="a"*32,
            approval_search_context=matching.invoice_context(self.inv,date.today().isoformat()), approval_candidates=[candidate()])

    def test_choice_rechecks_fingerprint_id_reference_and_truncation(self):
        self.assertEqual(service.validate_choice(self.inv,"180287","a"*32)["total"],413120)
        for field,value in (("total_sum",999), ("approval_search_id","b"*32), ("approval_search_truncated",True), ("approval_fetch_status","running")):
            inv=copy.deepcopy(self.inv);inv["data"][field]=value
            with self.assertRaises(ValueError): service.validate_choice(inv,"180287","a"*32)
        with self.assertRaises(ValueError): service.validate_choice(self.inv,"999","a"*32)
        self.inv["data"]["approval_search_context"]["reference_date"]="2020-01-01"
        with self.assertRaises(ValueError): service.validate_choice(self.inv,"180287","a"*32)

    def test_order_success_does_not_run_fallback(self):
        with patch.object(invoice_db,"get_invoice",return_value=self.inv), patch.object(fetcher,"_fetch_order_documents",return_value={"approval_pdf_paths":["old.pdf"]}), patch.object(fetcher,"fetch_amount_documents") as fallback:
            self.assertEqual(fetcher.fetch_approval_documents(277,"quote.pdf")["approval_pdf_paths"],["old.pdf"])
            fallback.assert_not_called()

    def test_only_actual_order_miss_runs_fallback(self):
        with patch.object(invoice_db,"get_invoice",return_value=self.inv), patch.object(fetcher,"_fetch_order_documents",side_effect=fetcher.OrderSearchMiss("missing")), patch.object(fetcher,"fetch_amount_documents",return_value={"ok":True}) as fallback:
            self.assertTrue(fetcher.fetch_approval_documents(277,"quote.pdf")["ok"]);fallback.assert_called_once()
        with patch.object(invoice_db,"get_invoice",return_value=self.inv), patch.object(fetcher,"_fetch_order_documents",side_effect=RuntimeError("authentication failed")), patch.object(fetcher,"fetch_amount_documents") as fallback:
            with self.assertRaises(RuntimeError): fetcher.fetch_approval_documents(277,"quote.pdf")
            fallback.assert_not_called()

    def test_endpoint_requires_session_and_uses_verified_requester(self):
        identity=Mock(return_value=None);start=Mock(return_value=True)
        ns=load("web_v1/backend/app.py", {"_start_requested_approval"}, {"Request":object,"_browser_identity":identity,"start_approval_lookup":start,"HTTPException":RequestError})
        with self.assertRaises(RequestError) as ctx: ns["_start_requested_approval"](object(),277)
        self.assertEqual(ctx.exception.status_code,401);start.assert_not_called()
        identity.return_value={"user_id":"hah4627"};ns["_start_requested_approval"](object(),277,doc_id="180287",search_id="a"*32)
        self.assertEqual(start.call_args.kwargs["requested_by"],"hah4627")


class AtomicMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.addCleanup(patch.stopall)
        patch.object(invoice_db,"settings",SimpleNamespace(sqlite_db_path=self.root/'test.db',download_dir=self.root)).start()
        connections=[]; original=invoice_db.get_conn
        def tracked():
            connection=original();connections.append(connection);return connection
        patch.object(invoice_db,"get_conn",side_effect=tracked).start()
        self.addCleanup(lambda: [c.close() for c in connections])
        patch.object(invoice_db,"_repair_purchase_amounts",side_effect=lambda raw,_:raw).start()
        invoice_db.init_db();raw=invoice();raw.pop("id")
        with invoice_db.get_conn() as c:
            c.execute("INSERT INTO invoices(id,subject,json_data,status,last_error) VALUES(277,'test',?,'처리완료','[ERP_SAVE_CONFIRM_REQUIRED] original')",(json.dumps(raw),));c.commit()
        self.context=matching.invoice_context(invoice_db.get_invoice(277),date.today().isoformat())

    def test_atomic_update_preserves_erp_status_error_and_unrelated_data(self):
        self.assertTrue(invoice_db.update_approval_lookup(277,self.context,{"approval_search_id":"run","approval_fetch_status":"running"}))
        inv=invoice_db.get_invoice(277);self.assertEqual(inv["status"],"처리완료");self.assertEqual(inv["last_error"],"[ERP_SAVE_CONFIRM_REQUIRED] original")
        self.assertEqual(inv["data"]["total_sum"],413120)
        self.assertFalse(invoice_db.update_approval_lookup(277,self.context,{"approval_fetch_status":"done"},expected_search_id="wrong"))

    def test_changed_invoice_or_manual_attachment_wins(self):
        stale={**self.context,"fingerprint":"wrong"}
        self.assertFalse(invoice_db.update_approval_lookup(277,stale,{"approval_fetch_status":"done"}))
        pdf=self.root/'manual.pdf';pdf.write_bytes(b'existing')
        self.assertTrue(invoice_db.update_approval_lookup(277,self.context,{"approval_pdf_paths":[str(pdf)]}))
        self.assertFalse(invoice_db.update_approval_lookup(277,self.context,{"approval_pdf_paths":["replacement"]}))

    def test_quote_revision_invalidates_previous_search(self):
        inv=invoice();quote=self.root/'quote.pdf';quote.write_bytes(b'old');inv["data"]["quote_path"]=str(quote)
        first=matching.invoice_context(inv,date.today().isoformat());quote.write_bytes(b'new-content')
        self.assertNotEqual(first["fingerprint"],matching.invoice_context(inv,date.today().isoformat())["fingerprint"])


if __name__ == "__main__": unittest.main()
