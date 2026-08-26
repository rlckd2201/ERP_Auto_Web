from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from web_v1.backend.config import settings
from web_v1.backend.erp_runner import _load_legacy_module


LEGACY_MANAGER = Path(settings.legacy_manager_path)


class LegacyCoordinateGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _load_legacy_module()
        cls.source = LEGACY_MANAGER.read_text(encoding="utf-8-sig")
        cls.monitor = {
            "left": 0,
            "top": 0,
            "right": 1920,
            "bottom": 1080,
            "work_left": 0,
            "work_top": 0,
            "work_right": 1920,
            "work_bottom": 1032,
        }

    @staticmethod
    def _window(left: int, top: int, right: int, bottom: int):
        rect = SimpleNamespace(left=left, top=top, right=right, bottom=bottom)
        return SimpleNamespace(rectangle=lambda: rect)

    def test_maximized_dwm_frame_drift_uses_work_area_origin(self) -> None:
        window = self._window(-8, -8, 1928, 1040)
        rect = self.legacy._erp_coordinate_reference_rect(window, monitor=self.monitor)
        self.assertEqual((rect.left, rect.top, rect.right, rect.bottom), (0, 0, 1920, 1032))

    def test_windowed_erp_keeps_its_own_origin(self) -> None:
        window = self._window(120, 80, 1720, 980)
        rect = self.legacy._erp_coordinate_reference_rect(window, monitor=self.monitor)
        self.assertEqual((rect.left, rect.top, rect.right, rect.bottom), (120, 80, 1720, 980))

    def test_runtime_refresh_and_form_anchor_calibration_are_wired(self) -> None:
        self.assertIn("def _detect_erp_target_monitor(logger=None, force_refresh=False)", self.source)
        self.assertIn("_detect_erp_target_monitor(self.logger, force_refresh=True)", self.source)
        self.assertIn('def _calibrate_form_coordinate_offset(reason="ERP form")', self.source)
        self.assertIn("_calibrate_form_coordinate_offset(", self.source)
        self.assertIn("r.left + x + form_coord_offset_x", self.source)
        self.assertIn("r.top + y + form_coord_offset_y", self.source)


if __name__ == "__main__":
    unittest.main()
