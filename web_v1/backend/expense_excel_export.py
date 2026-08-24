from __future__ import annotations

import json
import sys
from pathlib import Path


CELLS = {
    "date": "D5",
    "dept": "D6",
    "author": "G6",
    "title": "D7",
    "basis": "D8",
    "amount": "D9",
    "settlement_amount": "I9",
    "payee": "N9",
    "body": "C11",
    "footer": "B19",
}

EXTRA_CELLS: dict[str, tuple[str, ...]] = {}

# Excel constants are kept local so the helper does not depend on generated
# win32com constants. The cash-withdrawal form is printed on portrait A4.
XL_PORTRAIT = 1
XL_PAPER_A4 = 9
EXPENSE_PRINT_AREA = "$A$1:$R$20"
A4_WIDTH_POINTS = 595.2756
A4_HEIGHT_POINTS = 841.8898


def configure_page_setup(page_setup: object) -> list[str]:
    warnings: list[str] = []
    page_setup.PrintArea = EXPENSE_PRINT_AREA
    page_setup.Orientation = XL_PORTRAIT

    current_paper_size = None
    try:
        current_paper_size = int(page_setup.PaperSize)
    except Exception:
        pass
    if current_paper_size != XL_PAPER_A4:
        try:
            page_setup.PaperSize = XL_PAPER_A4
        except Exception as exc:
            warnings.append(
                "Excel could not apply A4 through the active printer driver; "
                f"the template paper size will be used and the PDF will be normalized to A4: {exc}"
            )

    page_setup.Zoom = False
    page_setup.FitToPagesWide = 1
    page_setup.FitToPagesTall = 1
    page_setup.CenterHorizontally = True
    page_setup.CenterVertically = False
    return warnings


def normalize_pdf_to_portrait_a4(output_pdf: Path) -> bool:
    import fitz

    source = fitz.open(str(output_pdf))
    try:
        if source.page_count != 1:
            raise RuntimeError(f"expense report must contain one page, got {source.page_count}")
        rect = source.load_page(0).rect
        already_a4 = (
            float(rect.height) > float(rect.width)
            and abs(float(rect.width) - A4_WIDTH_POINTS) <= 3.0
            and abs(float(rect.height) - A4_HEIGHT_POINTS) <= 3.0
        )
        if already_a4:
            return False

        normalized_path = output_pdf.with_name(f"{output_pdf.stem}.__a4{output_pdf.suffix or '.pdf'}")
        normalized_path.unlink(missing_ok=True)
        normalized = fitz.open()
        try:
            page = normalized.new_page(width=A4_WIDTH_POINTS, height=A4_HEIGHT_POINTS)
            page.show_pdf_page(page.rect, source, 0, keep_proportion=True)
            normalized.save(str(normalized_path), garbage=4, deflate=True)
        finally:
            normalized.close()
    finally:
        source.close()

    normalized_path.replace(output_pdf)
    return True


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: expense_excel_export.py <work_xlsx> <output_pdf> <payload_json>", file=sys.stderr)
        return 2
    work_xlsx = Path(sys.argv[1])
    output_pdf = Path(sys.argv[2])
    payload_path = Path(sys.argv[3])
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    app = None
    workbook = None
    pythoncom = None
    try:
        import pythoncom as _pythoncom
        import win32com.client as win32

        pythoncom = _pythoncom
        pythoncom.CoInitialize()
        app = win32.DispatchEx("Excel.Application")
        app.Visible = False
        app.DisplayAlerts = False
        try:
            app.EnableEvents = False
        except Exception:
            pass
        try:
            app.AskToUpdateLinks = False
        except Exception:
            pass
        try:
            app.AutomationSecurity = 3
        except Exception:
            pass
        try:
            app.Interactive = False
        except Exception:
            pass
        workbook = app.Workbooks.Open(
            str(work_xlsx),
            UpdateLinks=0,
            ReadOnly=False,
            IgnoreReadOnlyRecommended=True,
            AddToMru=False,
        )
        try:
            sheet = workbook.Worksheets("출력용")
        except Exception:
            sheet = workbook.Worksheets(1)
        for key, cell in CELLS.items():
            sheet.Range(cell).Value = payload.get(key, "")
        for key, cells in EXTRA_CELLS.items():
            value = payload.get(key, "")
            if value:
                for cell in cells:
                    try:
                        sheet.Range(cell).Value = value
                    except Exception:
                        pass
        sheet.Range(CELLS["body"]).WrapText = True
        if output_pdf.exists():
            output_pdf.unlink()
        try:
            sheet.Activate()
        except Exception:
            pass
        page_setup = sheet.PageSetup
        for warning in configure_page_setup(page_setup):
            print(f"warning: {warning}", file=sys.stderr)
        sheet.ExportAsFixedFormat(0, str(output_pdf))
        if not output_pdf.exists() or output_pdf.stat().st_size <= 0:
            raise RuntimeError(f"PDF export produced no file: {output_pdf}")
        normalize_pdf_to_portrait_a4(output_pdf)
        try:
            workbook.Saved = True
        except Exception:
            pass
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        try:
            if workbook is not None:
                workbook.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            if app is not None:
                app.Quit()
        except Exception:
            pass
        try:
            if pythoncom is not None:
                pythoncom.CoUninitialize()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
