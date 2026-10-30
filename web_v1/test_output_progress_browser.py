"""Isolated Chromium fixture: no production business requests or printer operations."""
import copy
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
FIXTURE='''<!doctype html><html lang="ko"><head><meta charset="utf-8"></head><body>
<style>body{font:14px Arial,sans-serif;background:#f3f6fa;color:#16344f;padding:25px} .outer{background:white;border:1px solid #d4dfe9;border-radius:10px;padding:20px} .invoices{width:100%;border-collapse:collapse} .invoices>tbody>tr>td{padding:12px;border-bottom:1px solid #d4dfe9}.button{padding:10px 16px;border-radius:6px;border:1px solid #c5d4e2;background:white;color:#17334e;cursor:pointer}.primary{background:#087769;color:white}.button:disabled{opacity:.5} h1{margin-top:0}</style>
<h1>구매 처리</h1><section class="outer"><h2>구매 수신 내역</h2><table class="invoices"><thead><tr><th></th><th>상태</th><th>거래처</th><th>사업장</th><th>금액</th><th>수신일</th><th>담당자</th></tr></thead>
<tbody id="invoicesTable"><tr data-invoice-id="277"><td>□</td><td>처리완료</td><td>컴퓨존</td><td>일강1공장</td><td>413,120</td><td>2026-10-23</td><td>현시훈</td></tr></tbody></table></section>
<h2 id="purchaseDetailTitle">#277 컴퓨존</h2><div id="purchaseDetailBody"><p>기존 분석 및 출력 화면</p></div></body></html>'''


def record():
    docs=[]
    for key,name,code,label in [('erp_voucher','전표','sent','프린터 전송 확인'),('tax_invoice','세금계산서','sent','프린터 전송 확인'),('approval_docs','전자결재 품의','none','전송 기록 없음'),('expense_report','현금출금결의서','failed','프린터 전송 실패')]:
        docs.append(dict(key=key,label=name,pdf_ready=key!='approval_docs',pdf_label='PDF 미준비' if key=='approval_docs' else 'PDF 준비 완료',print=dict(state=code,label=label,printer_name='Samsung M268x_M289x Series' if code!='none' else '',at='2026-10-30T11:23:20' if code!='none' else '',error='프린터에 연결할 수 없습니다.' if code=='failed' else '')))
    return dict(id=277,processing_status=dict(documents=docs,erp_label='전표 PDF 보관 완료',retry_doc_keys=['expense_report'],retry_token='a'*64,active=False,complete=True,printer_key='pyeongtaek',notice='전송 확인은 Windows 인쇄 큐 기준입니다. 실제 용지 출력은 프린터에서 확인해 주세요.'))


class OutputBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start();cls.browser=cls.pw.chromium.launch(headless=True)
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.pw.stop()
    def setUp(self):
        self.page=self.browser.new_page(viewport={'width':1440,'height':1000})
        self.addCleanup(self.page.close)
        self.page.route('http://fixture.local/**',lambda route:route.fulfill(body=FIXTURE,content_type='text/html'))
        self.page.goto('http://fixture.local/accounting-automation/')
        self.page.add_style_tag(path=str(ROOT/'frontend/output-progress.css'))
        self.page.evaluate('''() => {
          window.sent=[];window.jobs=[];window.fixture=[];
          window.state={setupStatus:{capabilities:{printer_mapping:{pyeongtaek:'Samsung M268x_M289x Series',gimje:'Gimje Office Printer'}}}};
          window.fetch=async (...args)=>{sent.push(args);return new Response(JSON.stringify(fixture),{headers:{'Content-Type':'application/json'}})};
          window.startJob=async (url,body)=>{jobs.push({url,body}); await new Promise(resolve=>setTimeout(resolve,100));};
        }''')
        self.page.add_script_tag(path=str(ROOT/'frontend/output-progress.js'))
        self.publish(record())
    def publish(self,row):
        self.page.evaluate("row=>{fixture=[row];return fetch('/accounting-automation/api/invoices?mode=purchase',{headers:{'X-Accounting-Session':'fixture'}})}",row)
        self.page.locator('#invoiceOutputProgress').wait_for()
    def screenshot(self,name):
        if os.getenv('OUTPUT_PROGRESS_SCREENSHOT_DIR'):
            folder=Path(os.environ['OUTPUT_PROGRESS_SCREENSHOT_DIR']);folder.mkdir(exist_ok=True,parents=True)
            self.page.screenshot(path=str(folder/name))
    def test_each_document_visible_and_observer_does_not_issue_requests(self):
        self.assertEqual(self.page.locator('.output-progress-chip').count(),4)
        self.assertEqual(self.page.locator('#invoiceOutputProgress tbody tr').count(),4)
        self.assertIn('Samsung',self.page.locator('.output-progress-compact').inner_text())
        self.assertIn('2026',self.page.locator('.output-progress-compact').inner_text())
        self.assertEqual(self.page.evaluate('sent.length'),1);self.assertEqual(self.page.evaluate('jobs.length'),0)
        self.assertEqual(self.page.evaluate("sent[0][1].headers['X-Accounting-Session']"),'fixture')
        self.screenshot('status-list-detail.png')
    def test_retry_confirmation_centers_and_submits_selected_printer_token_only(self):
        self.page.get_by_role('button',name='실패 문서만 다시 출력').click()
        modal=self.page.locator('#outputProgressModal');box=modal.bounding_box()
        self.assertAlmostEqual(box['x']+box['width']/2,720,delta=2)
        self.assertIn('재출력 대상: 현금출금결의서',modal.inner_text())
        self.assertEqual(self.page.evaluate('jobs.length'),0)
        self.page.locator('#outputProgressPrinter').select_option('gimje')
        self.screenshot('failed-only-retry.png')
        self.page.locator('.output-progress-confirm').click()
        self.page.wait_for_function('jobs.length===1')
        body=self.page.evaluate('jobs[0].body')
        self.assertEqual(body['invoice_ids'],[277]);self.assertEqual(body['printer_key'],'gimje')
        self.assertEqual(body['expected_printer_name'],'Gimje Office Printer');self.assertEqual(body['retry_token'],'a'*64)
        self.assertTrue(body['existing_only']);self.assertNotIn('selected_doc_keys',body)
    def test_missing_mapping_disables_submission(self):
        self.page.evaluate('state.setupStatus.capabilities.printer_mapping={}')
        self.page.get_by_role('button',name='실패 문서만 다시 출력').click()
        self.assertTrue(self.page.locator('.output-progress-confirm').is_disabled())
        self.assertIn('매핑',self.page.locator('#outputProgressModal').inner_text())
    def test_fresh_completed_status_removes_retry_and_updates_without_duplicates(self):
        row=record();row['processing_status']['retry_doc_keys']=[]
        row['processing_status']['documents'][3]['print'].update(state='sent',label='프린터 전송 확인',error='')
        self.publish(row)
        self.page.get_by_role('button',name='실패 문서만 다시 출력').wait_for(state='detached')
        self.assertEqual(self.page.locator('#invoiceOutputProgress').count(),1)
        self.assertEqual(self.page.locator('.output-progress-chip').count(),4)
    def test_untrusted_error_is_text_and_read_only_modal_does_not_start_job(self):
        row=record();row['processing_status']['documents'][3]['print']['error']='<img src=x onerror="window.pwned=true">'
        self.publish(row);self.page.get_by_role('button',name='출력 상태 보기').click()
        self.assertIn('<img',self.page.locator('#outputProgressModal').inner_text())
        self.assertEqual(self.page.locator('#outputProgressModal img').count(),0)
        self.assertEqual(self.page.evaluate('jobs.length'),0)
    def test_parent_rerender_keeps_single_status_panel(self):
        self.page.evaluate("document.getElementById('purchaseDetailBody').innerHTML='<p>분석 새로고침</p>'")
        self.page.locator('#invoiceOutputProgress').wait_for()
        self.assertEqual(self.page.locator('#invoiceOutputProgress').count(),1)


if __name__=='__main__':unittest.main()
