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
    "body": "C11",
    "footer": "B19",
}


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
        sheet.Range(CELLS["body"]).WrapText = True
        if output_pdf.exists():
            output_pdf.unlink()
        try:
            sheet.Activate()
        except Exception:
            pass
        sheet.ExportAsFixedFormat(0, str(output_pdf))
        if not output_pdf.exists() or output_pdf.stat().st_size <= 0:
            raise RuntimeError(f"PDF export produced no file: {output_pdf}")
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
