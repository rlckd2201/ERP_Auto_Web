from __future__ import annotations

import json
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from web_v1.backend import purchase_analysis


class _FakeFile:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeFilesService:
    def __init__(self) -> None:
        self.uploaded: list[str] = []
        self.deleted: list[str] = []

    def upload(self, *, file: str) -> _FakeFile:
        self.uploaded.append(file)
        return _FakeFile(f"files/{len(self.uploaded)}")

    def delete(self, *, name: str) -> None:
        self.deleted.append(name)


class _FakeModelsService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            text=json.dumps(
                {
                    "vendor_name": "주식회사 테스트상사",
                    "items": [{"name": "마우스", "qty": 1, "inc_vat": 11000}],
                },
                ensure_ascii=False,
            )
        )


class _FakeClient:
    instances: list["_FakeClient"] = []

    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key
        self.files = _FakeFilesService()
        self.models = _FakeModelsService()
        self.closed = False
        self.instances.append(self)

    def close(self) -> None:
        self.closed = True


class PurchaseGeminiSdkTests(unittest.TestCase):
    """Verify the maintained Google GenAI SDK integration without network calls."""

    def setUp(self) -> None:
        _FakeClient.instances.clear()

    def test_ai_parse_uses_configured_model_and_cleans_up_files(self) -> None:
        fake_genai = types.ModuleType("google.genai")
        fake_genai.Client = _FakeClient
        fake_google = types.ModuleType("google")
        fake_google.genai = fake_genai
        fake_settings = SimpleNamespace(
            gemini_api_key="test-key",
            gemini_model="gemini-3.7-flash",
        )
        fast_data = {"analysis_unknown_items": ["unknown"]}

        with (
            patch.object(purchase_analysis, "settings", fake_settings),
            patch.dict(sys.modules, {"google": fake_google, "google.genai": fake_genai}),
        ):
            result = purchase_analysis._ai_parse("tax.pdf", "quote.pdf", fast_data)

        self.assertIsNotNone(result)
        self.assertEqual(result["analysis_source"], "gemini")
        self.assertEqual(result["analysis_ai_model"], "gemini-3.7-flash")
        self.assertEqual(result["vendor_name"], "테스트상사")
        client = _FakeClient.instances[0]
        self.assertEqual(client.files.uploaded, ["tax.pdf", "quote.pdf"])
        self.assertEqual(client.files.deleted, ["files/1", "files/2"])
        self.assertTrue(client.closed)
        call = client.models.calls[0]
        self.assertEqual(call["model"], "gemini-3.7-flash")
        self.assertEqual(
            call["config"],
            {
                "response_mime_type": "application/json",
                "automatic_function_calling": {"disable": True},
            },
        )

    def test_ai_parse_falls_back_without_api_key(self) -> None:
        fake_settings = SimpleNamespace(
            gemini_api_key="",
            gemini_model="gemini-3.7-flash",
        )
        fast_data: dict[str, object] = {}

        with patch.object(purchase_analysis, "settings", fake_settings):
            result = purchase_analysis._ai_parse("tax.pdf", "quote.pdf", fast_data)

        self.assertIsNone(result)
        self.assertEqual(fast_data["analysis_ai_error"], "GEMINI_API_KEY missing")
        self.assertEqual(fast_data["analysis_ai_model"], "gemini-3.7-flash")


if __name__ == "__main__":
    unittest.main()
