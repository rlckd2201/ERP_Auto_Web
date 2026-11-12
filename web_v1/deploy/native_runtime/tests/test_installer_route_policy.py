"""Exercise the real native guard with an inert downstream app and no identity tokens."""
import argparse
import asyncio
import runpy
import types
import unittest
from urllib.parse import quote, unquote


HOST = None


class InstallerRouteTests(unittest.TestCase):
    def setUp(self):
        self.ns = runpy.run_path(str(HOST), run_name="native_route_fixture")
        self.routes = [
            {"method": "GET", "path": "/api/setup/installers/{company}"},
            {"method": "GET", "path": "/api/version"},
            {"method": "POST", "path": "/api/agent/heartbeat"},
            {"method": "GET", "path": "/api/agent/jobs/{job_id}/print-file/{invoice_id}/{file_index}"},
        ]
        policy = self.ns["AccessPolicy"](self.ns["CANONICAL_URL"], self.routes)
        self.forwarded = []

        async def downstream(scope, receive, send):
            self.forwarded.append(scope["path"])
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"fixture"})

        def reject_identity(*args, **kwargs):
            raise PermissionError("No signed browser identity in this fixture")

        reader = types.SimpleNamespace(check_cohort=lambda cohort: None)
        context = types.SimpleNamespace(HEADER=self.ns["HEADER"], verify_identity=reject_identity)
        cohort = {"members": [{} for _ in range(6)], "referenceNativeId": "fixture"}
        self.guard = self.ns["NativeGuard"](
            downstream, context=context, native_key="k" * 43,
            cohort=cohort, reader=reader, policy=policy,
        )

    def request(self, path, method="GET", headers=()):
        messages = []
        scope = {"type": "http", "method": method, "path": unquote(path),
                 "raw_path": path.encode("ascii"), "query_string": b"",
                 "headers": list(headers), "client": ("127.0.0.1", 12345)}

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        asyncio.run(self.guard(scope, receive, send))
        return next(m["status"] for m in messages if m["type"] == "http.response.start")

    def test_three_existing_company_downloads(self):
        for company in ("대승", "대승정밀", "일강"):
            with self.subTest(company=company):
                self.assertEqual(self.request("/api/setup/installers/" + quote(company)), 200)
        self.assertEqual(len(self.forwarded), 3)

    def test_other_unicode_company_names_rejected(self):
        for company in ("다른회사", "대승추가", "앞대승", "대승 정밀", "大承"):
            with self.subTest(company=company):
                self.assertIn(self.request("/api/setup/installers/" + quote(company)), (400, 403))
        self.assertEqual(self.forwarded, [])

    def test_encoded_separators_and_traversal_rejected(self):
        for suffix in ("%2e%2e", "%2Fsecret", "%5Csecret", "%252fsecret", "a%2F..%2Fsecret", "%00x"):
            with self.subTest(suffix=suffix):
                self.assertIn(self.request("/api/setup/installers/" + suffix), (400, 403))
        self.assertEqual(self.forwarded, [])

    def test_unicode_not_enabled_for_other_service_parameters(self):
        path = "/api/agent/jobs/" + quote("대승") + "/print-file/1/0"
        self.assertEqual(self.request(path), 403)
        self.assertEqual(self.forwarded, [])

    def test_browser_headers_still_require_identity(self):
        for headers in (((b"origin", b"https://portal.dae-seung.co.kr"),),
                        ((b"sec-fetch-site", b"same-origin"),)):
            self.assertEqual(self.request("/api/setup/installers/" + quote("대승"), headers=headers), 403)
        self.assertEqual(self.forwarded, [])

    def test_install_download_remains_get_only(self):
        for method in ("HEAD", "POST", "PUT", "DELETE"):
            self.assertEqual(self.request("/api/setup/installers/" + quote("일강"), method), 403)
        self.assertEqual(self.forwarded, [])

    def test_existing_ascii_services_preserved(self):
        self.assertEqual(self.request("/api/version"), 200)
        self.assertEqual(self.request("/api/agent/heartbeat", "POST"), 200)
        self.assertEqual(self.request("/api/agent/jobs/job-1/print-file/293/0"), 200)
        self.assertEqual(self.request("/api/setup/installers/legacy_ascii"), 200)

    def test_unregistered_routes_remain_protected(self):
        for path in ("/api/login", "/api/setup/private", "/api/admin-db", "/api/users"):
            self.assertEqual(self.request(path), 403)
        self.assertEqual(self.forwarded, [])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-host", required=True)
    args, remaining = parser.parse_known_args()
    HOST = args.native_host
    unittest.main(argv=[__file__] + remaining)
