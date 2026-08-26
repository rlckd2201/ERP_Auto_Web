from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from web_v1.agent.erp_agent import (
    _apply_erp_runtime_profile,
    _erp_task_runtime_profile,
    _restore_erp_runtime_profile,
)
from web_v1.backend.erp_runner import (
    ERP_SAVE_CONFIRM_REQUIRED,
    build_purchase_erp_payload,
    requires_erp_save_confirmation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_MANAGER = PROJECT_ROOT / "manager_server" / "전표 자동화 프로그램(담당자용)_v6.2.py"


class ErpTaskRuntimeProfileTests(unittest.TestCase):
    def test_purchase_uses_fast_noncritical_and_stable_header_profile(self) -> None:
        name, profile = _erp_task_runtime_profile(
            {
                "job_type": "purchase_erp_input",
                "invoices": [{"invoice_type": "purchase"}],
                "source_job_payload": {"one_click_mode": "purchase"},
            }
        )
        self.assertEqual(name, "purchase-interactive")
        self.assertEqual(profile["ERP_FAST_NAVIGATION"], "1")
        self.assertEqual(profile["ERP_FAST_MANAGEMENT"], "0")
        self.assertEqual(profile["ERP_FAST_INPUT"], "0")
        self.assertEqual(profile["ERP_FAST_FIELD_VERIFY"], "0")
        self.assertEqual(profile["ERP_STABLE_HEADER_FIELDS"], "1")
        self.assertEqual(profile["ERP_STRICT_VENDOR_SELECTION"], "1")

    def test_purchase_safety_profile_overrides_unsafe_ambient_values_and_restores_them(self) -> None:
        _, profile = _erp_task_runtime_profile(
            {"job_type": "purchase_erp_input", "invoices": [{"invoice_type": "purchase"}]}
        )
        with patch.dict(
            os.environ,
            {"ERP_FAST_INPUT": "1", "ERP_FAST_FIELD_VERIFY": "1", "ERP_STABLE_HEADER_FIELDS": "0"},
            clear=False,
        ):
            previous = _apply_erp_runtime_profile(profile)
            self.assertEqual(os.environ["ERP_FAST_INPUT"], "0")
            self.assertEqual(os.environ["ERP_FAST_FIELD_VERIFY"], "0")
            self.assertEqual(os.environ["ERP_STABLE_HEADER_FIELDS"], "1")
            _restore_erp_runtime_profile(previous)
            self.assertEqual(os.environ["ERP_FAST_INPUT"], "1")
            self.assertEqual(os.environ["ERP_FAST_FIELD_VERIFY"], "1")
            self.assertEqual(os.environ["ERP_STABLE_HEADER_FIELDS"], "0")

    def test_regular_auto_keeps_243_conservative_navigation(self) -> None:
        name, profile = _erp_task_runtime_profile(
            {"job_type": "regular_erp_input", "regular_auto": True, "invoices": [{"invoice_type": "regular"}]}
        )
        self.assertEqual(name, "regular-auto")
        self.assertEqual(profile["ERP_FAST_MANAGEMENT"], "1")
        self.assertNotIn("ERP_FAST_NAVIGATION", profile)
        self.assertNotIn("ERP_FAST_FIELD_VERIFY", profile)

    def test_interactive_regular_task_has_no_purchase_override(self) -> None:
        name, profile = _erp_task_runtime_profile(
            {"job_type": "regular_erp_input", "invoices": [{"invoice_type": "regular"}]}
        )
        self.assertEqual(name, "")
        self.assertEqual(profile, {})


class PurchasePayloadTests(unittest.TestCase):
    def test_compuzone_payload_carries_purchase_mode_and_correct_vendor_number(self) -> None:
        payload = build_purchase_erp_payload(
            {
                "id": 209,
                "invoice_type": "purchase",
                "site_name": "P3공장",
                "vendor_name": "컴퓨존",
                "total_sum": 1_100,
                "data": {
                    "purchase_analysis_ready": True,
                    "invoice_date": "2026-08-18",
                    "target_supply": 1_000,
                    "total_tax": 100,
                    "total_sum": 1_100,
                    "items": [{"account": "소모품비", "name": "테스트 품목", "qty": 1, "supply": 1_000, "inc_vat": 1_100, "is_a": False}],
                },
            }
        )
        self.assertEqual(payload["data"]["invoice_type"], "purchase")
        self.assertEqual(payload["data"]["vendor_biz_no"], "106-81-83458")
        self.assertTrue(payload["rows"][-1].startswith("가지급금(업체)\t"))

    def test_post_save_failure_requires_manual_erp_confirmation_before_retry(self) -> None:
        self.assertTrue(requires_erp_save_confirmation({"last_error": f"{ERP_SAVE_CONFIRM_REQUIRED} ERP 저장 후 출력 실패"}))
        self.assertFalse(requires_erp_save_confirmation({"last_error": "거래처 선택 실패"}))


class LegacyManagerSafetySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = LEGACY_MANAGER.read_text(encoding="utf-8-sig")

    def test_proven_vendor_keyboard_navigation_is_restored_without_textbox_click(self) -> None:
        self.assertIn("def _input_vendor_by_business_no_keyboard", self.source)
        self.assertIn("keeping default search-box focus", self.source)
        self.assertIn("pyautogui.press('tab', presses=4", self.source)
        self.assertIn("pyautogui.press('down', presses=5", self.source)
        self.assertIn("pyautogui.press('up', presses=1", self.source)
        self.assertIn("pyautogui.press('tab', presses=3", self.source)
        self.assertIn("pyautogui.press('enter', presses=2", self.source)
        input_value_start = self.source.index("def _input_vendor_value_xy")
        input_value_end = self.source.index("if (\"vendor_vat\" in plan", input_value_start)
        input_value_source = self.source[input_value_start:input_value_end]
        self.assertIn("_input_vendor_by_business_no_keyboard", input_value_source)
        self.assertNotIn("_input_vendor_by_business_no_exact", input_value_source)
        self.assertIn("이전 행 거래처 팝업 감지, 현재 행 입력 전 닫기", self.source)
        self.assertNotIn("def _input_vendor_by_business_no_exact", self.source)
        self.assertNotIn("def _input_vendor_popup_search_text", self.source)
        self.assertNotIn("def _select_vendor_popup_business_filter", self.source)
        self.assertNotIn("def _find_exact_vendor_result", self.source)

    def test_post_save_print_failure_is_fatal_and_marks_retry_guard(self) -> None:
        self.assertIn(ERP_SAVE_CONFIRM_REQUIRED, self.source)
        self.assertIn("raise RuntimeError(message) from e", self.source)
        self.assertIn("전표출력 후 RD Viewer가 열리지 않았습니다.", self.source)

    def test_critical_header_fields_reconnect_and_never_skip_read_back(self) -> None:
        self.assertIn('stable_header_fields = _env_flag("ERP_STABLE_HEADER_FIELDS", "1")', self.source)
        self.assertIn("[ERP_UI_DISCONNECTED]", self.source)
        self.assertIn('_reconnect_main_window("회계단위 선택 후", required=True)', self.source)
        self.assertIn('must_verify = bool(is_critical and stable_header_fields)', self.source)
        self.assertIn('_reconnect_main_window(f"{label} 입력 후", required=True)', self.source)
        self.assertNotIn("if is_critical and fast_field_verify:", self.source)


class PurchaseRetryRouteSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (PROJECT_ROOT / "web_v1" / "backend" / "app.py").read_text(encoding="utf-8")

    def test_retry_guard_runs_before_analysis_save_can_clear_last_error(self) -> None:
        route_start = self.source.index("def create_purchase_one_click_job")
        route_end = self.source.index("\n@app.", route_start)
        route_source = self.source[route_start:route_end]
        self.assertLess(
            route_source.index("requires_erp_save_confirmation(invoice)"),
            route_source.index("_apply_purchase_analysis_payload("),
        )


if __name__ == "__main__":
    unittest.main()
