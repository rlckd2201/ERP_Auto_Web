import ast
import io
import os
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from web_v1.deploy.migration_bridge import create_app, create_redirect_app
from web_v1.backend.versioning import compute_agent_bundle_hash, _iter_bundle_files

ROOT = Path(__file__).resolve().parents[1]


def load_handler(name, namespace):
    tree = ast.parse((ROOT / "web_v1/backend/app.py").read_text(encoding="utf-8-sig"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), "app.py", "exec"), namespace)
    return namespace[name]


class MigrationStartupTests(unittest.TestCase):
    def test_installer_from_old_address_uses_configured_public_endpoint(self):
        namespace = dict(os=os, Request=object)
        origin = load_handler('_installer_server_url', namespace)
        installer = load_handler('_agent_installer_script', namespace)
        with patch.dict(os.environ, {'WEB_PUBLIC_ORIGIN': ' https://172.16.19.105:3010/ '}):
            for old in ('https://172.17.39.121:8080/', 'https://172.16.19.105:8081/'):
                script = installer(origin(SimpleNamespace(base_url=old)))
                self.assertIn('$ServerUrl = "https://172.16.19.105:3010"', script)
                self.assertNotIn(old.rstrip('/'), script)

    def test_installer_without_explicit_public_origin_keeps_request_endpoint(self):
        namespace = dict(os=os, Request=object)
        origin = load_handler('_installer_server_url', namespace)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(origin(SimpleNamespace(base_url='https://custom.internal:443/')),
                             'https://custom.internal:443')

    def test_agent_payload_contains_every_hashed_file_including_deployment_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {'web_v1/VERSION': 'test-version', 'web_v1/__init__.py': '',
                     'web_v1/agent/erp_agent.py': '# agent', 'web_v1/backend/config.py': '# config',
                     'web_v1/deploy/start_agent.ps1': '# launcher',
                     'web_v1/deploy/migration_bridge.py': '# server deployment helper',
                     'manager_server/main.py': '# manager'}
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
            namespace = dict(WEB_ROOT=root / 'web_v1', io=io, zipfile=zipfile,
                             settings=SimpleNamespace(legacy_manager_path=root / 'manager_server/main.py', ssl_trust_cert_file=None),
                             _agent_installer_script=lambda _: '# setup')
            for name in ('_add_installer_file', '_add_installer_tree', '_build_user_pc_payload_zip'):
                load_handler(name, namespace)
            payload = namespace['_build_user_pc_payload_zip']('https://172.16.19.105:8081')
            import hashlib
            digest = hashlib.sha256()
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                for path in _iter_bundle_files(root):
                    relative = path.relative_to(root).as_posix()
                    self.assertIn('payload/' + relative, archive.namelist(), relative)
                    digest.update(relative.lower().encode())
                    digest.update(b'\0')
                    digest.update(archive.read('payload/' + relative))
                    digest.update(b'\0')
            self.assertEqual(digest.hexdigest(), compute_agent_bundle_hash(root))

    def test_staging_initializes_data_without_starting_any_worker_or_scheduler(self):
        settings = SimpleNamespace(download_dir=Mock(), chrome_profile_dir=Mock(), backend_background_enabled=False)
        namespace = dict(settings=settings, init_db=Mock(), init_auth_db=Mock(), init_setup_db=Mock(),
                         worker=SimpleNamespace(start=Mock()), _start_mail_collect_scheduler=Mock(),
                         _start_regular_auto_scheduler=Mock(), start_regular_due_scheduler=Mock())
        load_handler("on_startup", namespace)()
        for key in ("init_db", "init_auth_db", "init_setup_db"):
            namespace[key].assert_called_once()
        namespace["worker"].start.assert_not_called()
        for key in ("_start_mail_collect_scheduler", "_start_regular_auto_scheduler", "start_regular_due_scheduler"):
            namespace[key].assert_not_called()
        settings.backend_background_enabled = True
        namespace["on_startup"]()
        namespace["worker"].start.assert_called_once()
        for key in ("_start_mail_collect_scheduler", "_start_regular_auto_scheduler", "start_regular_due_scheduler"):
            namespace[key].assert_called_once()

    def test_certificate_download_serves_existing_ca_instead_of_server_leaf(self):
        with tempfile.TemporaryDirectory() as folder:
            ca = Path(folder) / "old-ca.pem"
            leaf = Path(folder) / "new-leaf.pem"
            ca.write_text("public CA")
            leaf.write_text("new server certificate")
            response = Mock()
            namespace = dict(settings=SimpleNamespace(ssl_trust_cert_file=ca, ssl_cert_file=leaf),
                             FileResponse=response, HTTPException=RuntimeError)
            load_handler("api_setup_certificate", namespace)()
            self.assertEqual(response.call_args.args[0], ca)


class Chunks(httpx.AsyncByteStream):
    def __init__(self, *chunks):
        self.chunks = chunks
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk

    async def aclose(self):
        self.closed = True


class MigrationBridgeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.ca = Path(cls.temp.name) / "ca.pem"
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test CA")])
        now = datetime.now(timezone.utc)
        certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                       .public_key(key.public_key()).serial_number(x509.random_serial_number())
                       .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
                       .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                       .sign(key, hashes.SHA256()))
        cls.ca.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    async def request(self, handler, method="GET", path="/health", **kwargs):
        app = create_app("https://172.16.19.105:8081", self.ca, transport=httpx.MockTransport(handler))
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("172.16.10.18", 1234)),
                                        base_url="https://172.17.39.121:8080") as client:
                return await client.request(method, path, **kwargs)

    async def test_upload_preserves_method_query_body_and_requesting_pc(self):
        seen = []
        async def handler(request):
            seen.append(request)
            return httpx.Response(202, headers={"content-type": "application/json"}, stream=Chunks(b'{"ok":true}'))
        result = await self.request(handler, "POST", "/api/jobs/purchase-one-click?mode=x", content=b'[{"id":276}]',
                                    headers={"content-type": "application/json", "connection": "x-private", "x-private": "drop"})
        outgoing = seen[0]
        self.assertEqual(str(outgoing.url), "https://172.16.19.105:8081/api/jobs/purchase-one-click?mode=x")
        self.assertEqual(outgoing.method, "POST")
        self.assertEqual(outgoing.content, b'[{"id":276}]')
        self.assertEqual(outgoing.headers["host"], "172.16.19.105:8081")
        self.assertEqual(outgoing.headers["x-forwarded-for"], "172.16.10.18")
        self.assertNotIn("x-private", outgoing.headers)
        self.assertEqual(result.status_code, 202)

    async def test_existing_forwarded_client_identity_is_retained(self):
        async def handler(request):
            self.assertEqual(request.headers["x-forwarded-for"], "172.17.30.243")
            return httpx.Response(204, stream=Chunks())
        result = await self.request(handler, "POST", "/api/agent/erp/next", headers={"x-forwarded-for": "172.17.30.243"})
        self.assertEqual(result.status_code, 204)

    async def test_pdf_bytes_and_response_cookies_are_not_rewritten(self):
        stream = Chunks(b"%PDF-", b"1.4\x00\xff")
        async def handler(request):
            return httpx.Response(200, stream=stream, headers=[("content-type", "application/pdf"),
                ("set-cookie", "first=1"), ("set-cookie", "second=2"),
                ("connection", "x-internal"), ("x-internal", "drop")])
        result = await self.request(handler, path="/api/invoices/272/pdf")
        self.assertEqual(result.content, b"%PDF-1.4\x00\xff")
        self.assertEqual(result.headers.get_list("set-cookie"), ["first=1", "second=2"])
        self.assertNotIn("x-internal", result.headers)
        self.assertEqual(result.headers["x-accounting-backend"], "172.16.19.105:8081")
        self.assertTrue(stream.closed)

    async def test_job_events_keep_sse_format_and_stream_cleanup(self):
        stream = Chunks(b"event: job-progress\n", b"data: done\n\n")
        async def handler(request):
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=stream)
        result = await self.request(handler, path="/api/jobs/current/events")
        self.assertEqual(result.headers["content-type"], "text/event-stream")
        self.assertEqual(result.content, b"event: job-progress\ndata: done\n\n")
        self.assertTrue(stream.closed)

    async def test_unavailable_backend_returns_503_without_starting_old_app(self):
        async def handler(request):
            raise httpx.ConnectError("offline", request=request)
        result = await self.request(handler)
        self.assertEqual(result.status_code, 503)

    async def test_redirect_migrates_agent_post_with_same_body_and_new_client_ip(self):
        old = httpx.ASGITransport(app=create_redirect_app("https://172.16.19.105:8081"))
        seen = []
        async def dispatch(request):
            if request.url.host == "172.17.39.121":
                return await old.handle_async_request(request)
            seen.append(request)
            return httpx.Response(200, json={"ok": True})
        async with httpx.AsyncClient(transport=httpx.MockTransport(dispatch), follow_redirects=True) as client:
            response = await client.post("https://172.17.39.121:8080/api/agent/heartbeat?x=1",
                                         content=b'{"agent_id":"243"}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(seen), 1)
        self.assertEqual(str(seen[0].url), "https://172.16.19.105:8081/api/agent/heartbeat?x=1")
        self.assertEqual(seen[0].method, "POST")
        self.assertEqual(seen[0].content, b'{"agent_id":"243"}')
        self.assertNotIn("x-forwarded-for", seen[0].headers)

    async def test_redirect_retains_encoded_document_path_and_does_not_cache(self):
        transport = httpx.ASGITransport(app=create_redirect_app("https://172.16.19.105:8081"))
        async with httpx.AsyncClient(transport=transport, base_url="https://172.17.39.121:8080") as client:
            result = await client.get("/documents/a%20b.pdf?download=1")
        self.assertEqual(result.status_code, 307)
        self.assertEqual(result.headers["location"], "https://172.16.19.105:8081/documents/a%20b.pdf?download=1")
        self.assertEqual(result.headers["cache-control"], "no-store")

    def test_bridge_requires_verified_https_origin(self):
        for origin in ("http://172.16.19.105:8081", "https://user:password@172.16.19.105", "https://172.16.19.105?x=1", "https://172.16.19.105/subpath"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                create_app(origin, self.ca)
            with self.subTest(redirect_origin=origin), self.assertRaises(ValueError):
                create_redirect_app(origin)


if __name__ == "__main__":
    unittest.main()
