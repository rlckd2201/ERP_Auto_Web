"""Regression checks for fixed-width groupware approval print views."""
import ast
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[1]


def renderer_trees():
    browser = ast.parse((ROOT / "web_v1/backend/approval_browser.py").read_text(encoding="utf-8-sig"))
    legacy = ast.parse((ROOT / "manager_server/전표 자동화 프로그램(담당자용)_v6.2.py").read_text(encoding="utf-8-sig"))
    source = next(ast.literal_eval(n.value) for n in legacy.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "APPROVAL_HELPER_SOURCE" for t in n.targets))
    return [browser, ast.parse(source)]


def load_scale(tree):
    node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "_approval_pdf_scale")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "approval_scale", "exec"), namespace)
    return namespace["_approval_pdf_scale"]


class ApprovalWidthTests(unittest.IsolatedAsyncioTestCase):
    def page(self, width):
        page = Mock()
        page.locator.return_value.first.wait_for = AsyncMock()
        page.emulate_media = AsyncMock()
        page.set_viewport_size = AsyncMock()
        page.evaluate = AsyncMock(side_effect=[True, width])
        return page

    async def test_narrow_forms_keep_original_scale(self):
        for tree in renderer_trees():
            self.assertEqual(await load_scale(tree)(self.page(718)), 1.0)

    async def test_real_1100_pixel_table_fits_printable_width(self):
        for tree in renderer_trees():
            page = self.page(1124)
            scale = await load_scale(tree)(page)
            self.assertAlmostEqual(scale * 1124, 716)
            page.emulate_media.assert_awaited_once_with(media="print")
            page.set_viewport_size.assert_awaited_once_with({"width": 718, "height": 1047})

    async def test_invalid_or_unreadably_wide_document_is_rejected(self):
        for tree in renderer_trees():
            for width in (0, -1, float("nan"), float("inf"), 7161):
                with self.assertRaises(RuntimeError):
                    await load_scale(tree)(self.page(width))

    async def test_missing_approval_form_cannot_be_saved(self):
        for tree in renderer_trees():
            page = self.page(1124)
            page.locator.return_value.first.wait_for.side_effect = TimeoutError("No approval document")
            with self.assertRaises(TimeoutError):
                await load_scale(tree)(page)
            page.evaluate.assert_not_awaited()

    def test_both_isolated_renderers_use_identical_width_fit(self):
        trees = renderer_trees()
        functions = [next(n for n in t.body if isinstance(n, ast.AsyncFunctionDef)
                          and n.name == "_approval_pdf_scale") for t in trees]
        self.assertEqual(ast.dump(functions[0]), ast.dump(functions[1]))
        for tree in trees:
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Attribute) and n.func.attr == "pdf"]
            self.assertEqual(len(calls), 1)
            scale = next(k.value for k in calls[0].keywords if k.arg == "scale")
            self.assertIsInstance(scale, ast.Await)
            self.assertEqual(scale.value.func.id, "_approval_pdf_scale")


if __name__ == "__main__":
    unittest.main()
