"""Isolated UI smoke test: real static assets, mocked API, no ERP/server calls.

Run with Python Playwright installed: python tests/browser_log_viewer.py OUTPUT_DIR
"""
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).resolve().parents[1] / 'app'


class StaticHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.path = '/static/index.html'
        super().do_GET()

    def log_message(self, *args):
        pass


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), StaticHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    api = {'posts': 0, 'admin': True, 'deny': False, 'fail': False, 'agent_error': False}
    requests = []

    def handle(route):
        request = route.request
        parsed = urlsplit(request.url)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        requests.append((request.method, parsed.path))
        status = 200
        if parsed.path == '/api/settings':
            result = {'default_accounting_date': '2026-11-20', 'managers': [
                {'key': 'daeseung', 'label': '대승 담당자', 'enabled': True}],
                'auth': {'auth_required': True, 'authenticated': True,
                         'user': {'user_id': 'test-admin', 'name': '테스트 관리자',
                                  'is_admin': api['admin'], 'company_key': 'daeseung'}}}
        elif parsed.path == '/api/jobs':
            result = []
        elif parsed.path == '/api/admin/agent-commands':
            command = {'id': 'snapshot-1', 'command': 'tail-log',
                       'status': 'error' if api['agent_error'] else 'done',
                       'error': 'Agent connection unavailable' if api['agent_error'] else ''}
            if request.method == 'POST':
                assert request.post_data_json == {'command': 'tail-log'}
                api['posts'] += 1
                result = {'command': command}
            else:
                result = {'commands': [command] if api['posts'] else []}
        elif parsed.path == '/api/admin/logs':
            source = query['source']
            entries = [{'id': str(n), 'time': '2026-11-10T09:30:00',
                        'level': 'error' if n % 7 == 0 else 'warning' if n % 9 == 0 else 'info',
                        'context': '대승 2026-11-20' if source == 'jobs' else source + ' / native-20261110.log',
                        'message': ('ERP 인증 대기 상태 확인 password=[REDACTED] ' if n % 7 == 0
                                    else '자동 전표처리 PC 연결 상태 정상, 작업 처리 이력을 조회했습니다. ') + str(n)}
                       for n in range(125)]
            if query.get('level', 'all') != 'all':
                entries = [e for e in entries if e['level'] == query['level']]
            if query.get('q'):
                entries = [e for e in entries if query['q'] in e['message']]
            size = int(query['page_size'])
            pages = max(1, (len(entries) + size - 1) // size)
            page = min(int(query['page']), pages)
            result = {'items': entries[(page - 1) * size:page * size], 'source': source,
                      'total': len(entries), 'page': page, 'pages': pages,
                      'jobs': [{'id': 'j1', 'label': '대승 2026-11-20'}],
                      'files': [] if source == 'jobs' else [{'id': 'snapshot-1', 'label': '2026-11-10 09:30:00'}],
                      'selected_file': 'snapshot-1', 'limited': False, 'fetched_at': '2026-11-10T09:31:00'}
            if api['deny'] or api['fail']:
                status = 403 if api['deny'] else 500
                result = {'detail': '로그 조회 오류'}
        else:
            raise AssertionError('Unexpected API request: ' + parsed.path)
        route.fulfill(status=status, content_type='application/json', body=json.dumps(result))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={'width': 1440, 'height': 1000})
            context.route('**/api/**', handle)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            expect(page.locator('#workspaceTabs')).to_be_visible()
            page.locator('#logsTab').click()
            expect(page.locator('#logsRows tr')).to_have_count(100)
            expect(page.locator('#appShell')).to_be_hidden()
            page.locator('#logsNext').click()
            expect(page.locator('#logsRows tr')).to_have_count(25)
            page.locator('#logsPrevious').click()
            page.locator('#logsLevel').select_option('error')
            expect(page.locator('#logsRows tr')).to_have_count(18)
            page.locator('#logsQuery').fill('인증')
            page.locator('#logsFilters').evaluate('(form) => form.requestSubmit()')
            expect(page.locator('#logsRows tr')).to_have_count(18)
            with page.expect_download() as download:
                page.locator('#logsDownload').click()
            download.value.save_as(output / 'sanitized-log-download.txt')
            assert '[REDACTED]' in (output / 'sanitized-log-download.txt').read_text(encoding='utf-8-sig')
            assert api['posts'] == 0
            page.screenshot(path=str(output / 'logs-desktop.png'))
            page.locator('#logsStart').fill('2026-11-12')
            page.locator('#logsEnd').fill('2026-11-01')
            expect(page.locator('#logsNotice')).to_contain_text('종료일')
            expect(page.locator('#logsDownload')).to_be_disabled()
            page.locator('#logsStart').fill('')
            page.locator('#logsEnd').fill('')
            page.locator('[data-log-source="agent"]').click()
            page.locator('#logsCollect').click()
            expect(page.locator('#logsNotice')).to_have_text('Agent 로그 수집 완료')
            assert api['posts'] == 1
            api['agent_error'] = True
            page.locator('#logsCollect').click()
            expect(page.locator('#logsNotice')).to_contain_text('Agent connection unavailable')
            expect(page.locator('#logsCollect')).to_be_enabled()
            page.locator('[data-log-source="server"]').click()
            expect(page.locator('#logsFileField')).to_be_visible()
            expect(page.locator('#logsJobField')).to_be_hidden()
            expect(page.locator('#logsCollect')).to_be_hidden()
            page.set_viewport_size({'width': 390, 'height': 844})
            page.screenshot(path=str(output / 'logs-mobile.png'))
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert page.locator('.logCell-message').first.bounding_box()['width'] > 300
            assert page.locator('#logsShell img').evaluate_all('(images) => images.every(img => img.complete && img.naturalWidth > 0)')
            page.locator('#logsQuery').fill('no matching entries')
            page.locator('#logsFilters').evaluate('(form) => form.requestSubmit()')
            expect(page.locator('#logsRows')).to_contain_text('조회 조건에 맞는 로그가 없습니다.')
            api['fail'] = True
            page.locator('#logsRefresh').click()
            expect(page.locator('#logsSummary')).to_have_text('조회 실패')
            api['fail'] = False
            api['deny'] = True
            page.locator('#logsRefresh').click()
            expect(page.locator('#workspaceTabs')).to_be_hidden()
            expect(page.locator('#logsShell')).to_be_hidden()
            expect(page.locator('#appShell')).to_be_visible()
            api['deny'] = False
            api['admin'] = False
            page.reload()
            expect(page.locator('#workspaceTabs')).to_be_hidden()
            expect(page.locator('#appShell')).to_be_visible()
            assert not errors, errors
            assert all(method == 'GET' or path == '/api/admin/agent-commands' for method, path in requests)
            browser.close()
        print('PASS: desktop/mobile, filters, pagination, download, Agent collection/error, empty/error/denied states, non-admin, icons, no ERP actions')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    run(Path(sys.argv[1]))
