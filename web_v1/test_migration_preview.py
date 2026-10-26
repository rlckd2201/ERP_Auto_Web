import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from web_v1.backend.migration_preview import configure_migration_preview, preview_page
from web_v1.test_server_migration import load_handler


class PreviewAccessTests(unittest.IsolatedAsyncioTestCase):
    def make_app(self, enabled=True):
        app = FastAPI()
        self.calls = []
        configure_migration_preview(app, SimpleNamespace(migration_preview=enabled))

        @app.api_route('/{path:path}', methods=['GET', 'POST', 'PATCH', 'DELETE'])
        async def endpoint(path):
            self.calls.append(path)
            return {'ok': True}
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://test')

    async def test_preview_blocks_every_business_write_before_the_handler_runs(self):
        async with self.make_app() as client:
            for method, path in [('POST', '/api/jobs/purchase-one-click'), ('POST', '/api/jobs/regular-one-click'),
                                 ('POST', '/api/invoices/272/expense-report'), ('POST', '/api/regular-due/check'),
                                 ('POST', '/api/agent/heartbeat'), ('POST', '/api/agent/erp/next'),
                                 ('PATCH', '/api/invoices/272/status'), ('DELETE', '/api/invoices/272'),
                                 ('POST', '/api/password/find')]:
                result = await client.request(method, path, json={})
                self.assertEqual(result.status_code, 423, path)
                self.assertTrue(result.json()['read_only'])
        self.assertEqual(self.calls, [])

    async def test_preview_denies_gets_that_install_agents_or_persist_output_state(self):
        async with self.make_app() as client:
            for path in ['/api/setup/status', '/api/setup/user-pc-installer', '/api/setup/user-pc-payload.zip',
                         '/api/agent/jobs/id/print-file/1/0', '/api/invoices/272/output-set', '/api/version']:
                self.assertEqual((await client.get(path)).status_code, 423, path)
        self.assertEqual(self.calls, [])

    async def test_read_paths_and_login_work_without_agent_installation(self):
        async with self.make_app() as client:
            for path in ['/', '/health', '/api/invoices?limit=200', '/api/invoices/272', '/api/invoices/272/logs',
                         '/api/migration-preview/status', '/api/migration-preview/invoices/272/pdf']:
                result = await client.get(path)
                self.assertEqual(result.status_code, 200, path)
                self.assertEqual(result.headers['x-accounting-mode'], 'migration-preview')
                self.assertEqual(result.headers['cache-control'], 'no-store')
            self.assertEqual((await client.post('/api/login', json={})).status_code, 200)

    async def test_default_mode_preserves_existing_business_routes(self):
        async with self.make_app(False) as client:
            result = await client.post('/api/jobs/purchase-one-click', json={})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.calls, ['api/jobs/purchase-one-click'])

    async def test_preview_login_does_not_rebind_the_copied_agent_profile(self):
        class Request:
            async def json(self):
                return {'user_id': 'existing-user', 'password': 'test-password'}
        bind = Mock(side_effect=AssertionError('Must not bind a preview login to a production Agent'))
        namespace = dict(settings=SimpleNamespace(migration_preview=True), authenticate_user=Mock(return_value={'id': 'existing-user'}),
                         setup_status=bind, client_ip=Mock(), HTTPException=HTTPException, Request=Request, Any=object)
        # The shared loader supports synchronous handlers; compile this async route separately.
        import ast
        tree = ast.parse((Path(__file__).parent / 'backend/app.py').read_text(encoding='utf-8-sig'))
        node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'api_login')
        node.decorator_list = []
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'app.py', 'exec'), namespace)
        result = await namespace['api_login'](Request())
        self.assertTrue(result['read_only'])
        bind.assert_not_called()


class PreviewIsolationTests(unittest.TestCase):
    def test_preview_forces_schedulers_off_even_when_background_flag_is_enabled(self):
        namespace = dict(settings=SimpleNamespace(download_dir=Mock(), chrome_profile_dir=Mock(),
                                                 backend_background_enabled=True, migration_preview=True),
                         init_db=Mock(), init_auth_db=Mock(), init_setup_db=Mock(), worker=SimpleNamespace(start=Mock()),
                         _start_mail_collect_scheduler=Mock(), _start_regular_auto_scheduler=Mock(), start_regular_due_scheduler=Mock())
        load_handler('on_startup', namespace)()
        namespace['worker'].start.assert_not_called()
        for name in ('_start_mail_collect_scheduler', '_start_regular_auto_scheduler', 'start_regular_due_scheduler'):
            namespace[name].assert_not_called()

    def test_preview_pdf_only_serves_invoice_files_inside_accounting_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inside = root / 'data/invoice.pdf'
            inside.parent.mkdir()
            inside.write_bytes(b'%PDF-test')
            outside = root / 'private.pdf'
            outside.write_bytes(b'private')
            invoice = {'pdf_path': str(inside)}
            namespace = dict(settings=SimpleNamespace(migration_preview=True, erp_db_dir=inside.parent),
                             get_invoice=lambda _: invoice, Path=Path, HTTPException=HTTPException, FileResponse=FileResponse)
            handler = load_handler('migration_preview_invoice_pdf', namespace)
            self.assertEqual(handler(272).path, inside)
            invoice['pdf_path'] = str(outside)
            with self.assertRaises(HTTPException):
                handler(272)
            namespace['settings'].migration_preview = False
            with self.assertRaises(HTTPException):
                handler(272)

    def test_preview_page_clearly_names_the_only_operating_server(self):
        page = preview_page().body.decode()
        self.assertIn('조회 전용', page)
        self.assertIn('https://172.17.39.121:8080', page)
        self.assertNotIn('user-pc-installer', page)


if __name__ == '__main__':
    unittest.main()
