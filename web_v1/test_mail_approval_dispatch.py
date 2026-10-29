"""Mail-to-approval flow with real lookup guards, isolated records and no network/ERP."""
import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from web_v1.backend import approval_service as service
from web_v1.backend.approval_fetcher import ApprovalLookupResult
from web_v1.test_purchase_shared_execution import load


class MailApprovalDispatchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.quote = self.root / 'quote.pdf'
        self.quote.write_bytes(b'isolated quote fixture')
        self.records = {279: {
            'id': 279, 'invoice_type': 'purchase', 'status': '대기중',
            'erp_job_id': '', 'processed_at': None,
            'data': {'total_sum': 1, 'quote_path': str(self.quote),
                     'buyer_biz_no': '1258151622', 'site_name': '일강1공장',
                     'vendor_name': '컴퓨존', 'order_no': '28953656'},
        }}
        self.collection = {'saved_count': 1, 'saved_invoice_ids': [279], 'failed_count': 0}
        self.events = []
        self.threads = []
        self.logs = Mock()
        self.fetch = Mock(return_value={'approval_pdf_paths': [str(self.root / 'approval.pdf')]})

        def get_invoice(invoice_id):
            return copy.deepcopy(self.records.get(invoice_id))

        def save_analysis(invoice_id, data, **kwargs):
            self.events.append(('analysis_saved', invoice_id))
            self.records[invoice_id]['data'].update(copy.deepcopy(data))

        def update_lookup(invoice_id, context, payload, **kwargs):
            self.records[invoice_id]['data'].update(copy.deepcopy(payload))
            return True

        def thread_factory(**kwargs):
            self.events.append(('thread_created', kwargs['name']))
            thread = Mock()
            thread.work = kwargs['target']
            self.threads.append(thread)
            return thread

        for patcher in (
            patch.object(service, 'get_invoice', side_effect=get_invoice),
            patch.object(service, 'update_approval_lookup', side_effect=update_lookup),
            patch.object(service, 'add_invoice_log', self.logs),
            patch.object(service, 'fetch_approval_documents', self.fetch),
            patch.object(service, '_active', set()),
            patch.object(service.threading, 'Thread', side_effect=thread_factory),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

        self.analyze = Mock(side_effect=lambda inv: {'total_sum': 774740, 'items': [{'name': 'hub'}],
                                                     'quote_path': inv['data'].get('quote_path', '')})
        namespace = load('web_v1/backend/worker.py',
                         {'_run_purchase_mail_collect', '_start_approval_fetch_background'},
                         dict(JobRecord=object, collect_mail_once=Mock(side_effect=lambda **kw: copy.deepcopy(self.collection)),
                              get_invoice=get_invoice, analyze_purchase_documents=self.analyze,
                              learn_dictionary_items=Mock(), update_invoice_json=save_analysis,
                              add_invoice_log=self.logs, start_approval_lookup=service.start_approval_lookup),
                         class_name='JobWorker')
        self.worker = SimpleNamespace(store=SimpleNamespace(add_event=Mock()))
        self.worker._start_approval_fetch_background = lambda *args: namespace['_start_approval_fetch_background'](self.worker, *args)
        self.collect = lambda: namespace['_run_purchase_mail_collect'](self.worker, SimpleNamespace(id='mail-test', payload={}))

    def test_new_purchase_starts_after_analysis_commit_without_waiting_for_search(self):
        result = self.collect()
        self.assertEqual(result['auto_analyzed_count'], 1)
        self.assertEqual(result['failed_count'], 0)
        self.assertEqual(self.events[0], ('analysis_saved', 279))
        self.assertEqual(self.events[1][0], 'thread_created')
        data = self.records[279]['data']
        self.assertEqual(data['approval_search_context']['total'], 774740)
        self.assertEqual(data['approval_fetch_status'], 'running')
        self.assertEqual(len(self.threads), 1)
        self.threads[0].start.assert_called_once()
        self.fetch.assert_not_called()
        self.threads[0].work()
        self.assertEqual(data['approval_fetch_status'], 'done')
        self.assertEqual(self.records[279]['status'], '대기중')
        self.assertEqual(self.records[279]['erp_job_id'], '')
        self.assertIsNone(self.records[279]['processed_at'])

    def test_existing_pdf_is_not_replaced_or_searched(self):
        pdf = self.root / 'manual.pdf'
        pdf.write_bytes(b'previously attached')
        self.records[279]['data'].update(approval_pdf_paths=[str(pdf)], approval_fetch_status='done')
        self.collect()
        self.assertEqual(self.threads, [])
        self.assertEqual(self.records[279]['data']['approval_pdf_paths'], [str(pdf)])
        self.assertEqual(self.records[279]['data']['approval_fetch_status'], 'done')

    def test_in_process_duplicate_does_not_start_another_search(self):
        self.collect()
        self.collect()
        self.assertEqual(len(self.threads), 1)

    def test_recent_running_record_prevents_duplicate_after_process_restart(self):
        from datetime import datetime
        self.records[279]['data'].update(approval_fetch_status='running', approval_fetch_started_at=datetime.now().isoformat())
        self.collect()
        self.assertEqual(self.threads, [])

    def test_missing_quote_keeps_analysis_success_and_records_reason(self):
        self.quote.unlink()
        result = self.collect()
        self.assertEqual((result['auto_analyzed_count'], result['failed_count']), (1, 0))
        self.assertEqual(self.records[279]['data']['total_sum'], 774740)
        self.assertNotIn('approval_fetch_status', self.records[279]['data'])
        self.assertEqual(self.threads, [])
        self.assertTrue(any('견적서 파일이 없습니다' in str(c) for c in self.logs.call_args_list))

    def test_start_failure_does_not_misreport_analysis_or_stop_next_purchase(self):
        self.records[280] = copy.deepcopy(self.records[279])
        self.records[280]['id'] = 280
        self.collection.update(saved_count=2, saved_invoice_ids=[279, 280])
        original = self.worker._start_approval_fetch_background
        self.worker._start_approval_fetch_background = Mock(side_effect=[RuntimeError('thread unavailable'), None])
        result = self.collect()
        self.assertEqual((result['auto_analyzed_count'], result['failed_count']), (2, 0))
        self.assertEqual(self.worker._start_approval_fetch_background.call_count, 2)
        self.assertTrue(any('품의 검색 시작 실패' in str(c) for c in self.logs.call_args_list))
        self.worker._start_approval_fetch_background = original

    def test_search_failure_keeps_saved_purchase_and_sets_approval_error(self):
        self.fetch.side_effect = RuntimeError('groupware unavailable')
        result = self.collect()
        self.threads[0].work()
        data = self.records[279]['data']
        self.assertEqual((result['auto_analyzed_count'], result['failed_count']), (1, 0))
        self.assertTrue(data['erp_ready'])
        self.assertEqual(data['approval_fetch_status'], 'error')
        self.assertIn('groupware unavailable', data['approval_fetch_error'])
        self.assertEqual(self.records[279]['status'], '대기중')

    def test_ambiguous_candidates_remain_reviewable_instead_of_auto_attached(self):
        self.fetch.side_effect = ApprovalLookupResult({'status': 'review', 'reason': 'choose',
                                                      'candidates': [{'doc_id': '1'}, {'doc_id': '2'}]})
        self.collect()
        self.threads[0].work()
        data = self.records[279]['data']
        self.assertEqual(data['approval_fetch_status'], 'review')
        self.assertEqual(len(data['approval_candidates']), 2)
        self.assertFalse(data.get('approval_pdf_paths'))

    def test_analysis_failure_never_starts_search(self):
        self.analyze.side_effect = RuntimeError('analysis failure')
        result = self.collect()
        self.assertEqual((result['auto_analyzed_count'], result['failed_count']), (0, 1))
        self.assertEqual(self.threads, [])

    def test_regular_missing_and_duplicate_mail_records_are_not_searched(self):
        self.records[279]['invoice_type'] = 'regular'
        self.collection['saved_invoice_ids'] = [279, 999]
        result = self.collect()
        self.assertEqual(result['auto_analyzed_count'], 0)
        self.analyze.assert_not_called()
        self.assertEqual(self.threads, [])
        self.collection.update(saved_count=0, saved_invoice_ids=[], duplicate_count=1)
        self.collect()
        self.analyze.assert_not_called()
        self.assertEqual(self.threads, [])


if __name__ == '__main__':
    unittest.main()
