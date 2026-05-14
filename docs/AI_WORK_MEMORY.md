# AI Work Memory

Updated: 2026-05-14

## Compact Context Snapshot - 2026-05-14 fix95 Excel PDF no-save

- User showed the cash withdrawal/expense report generator opening Excel's `다른 이름으로 저장` dialog with `.xlsx` selected.
- Root cause: `web_v1/backend/expense_excel_export.py` saved the workbook before exporting PDF. In the 담당자 PC security/document environment, `workbook.Save()` can trigger an xlsx Save As prompt and hang the helper.
- Fixed helper to skip `workbook.Save()`, activate the output sheet, export directly via `ExportAsFixedFormat`, then mark the workbook as saved before closing without saving.
- WEB/Agent version is now `1.0.87`; 담당자 PC Agent update is required.
- Verification: `py_compile` passed for `web_v1/backend/expense_excel_export.py` and `web_v1/agent/erp_agent.py`.

## Compact Context Snapshot - 2026-05-14 cash expense Agent generation fix

- User confirmed the operating server has no Excel installed, so server-side Excel COM errors such as `-2147221005 wrong class string` are expected there.
- `POST /api/invoices/{id}/expense-report` now creates an `expense_report` queue task targeted to the connected 담당자 PC Agent.
- The Agent bundle is `1.0.86`; it claims `expense_report` tasks, runs `generate_expense_report_pdf()` on the 담당자 PC using the Roaming/AppData template and local Excel, then uploads the generated PDF to the server.
- `/api/agent/jobs/{job_id}/complete` branches `expense_report` separately so generating/replacing the cash expense report does not mutate the invoice business status.

## Compact Context Snapshot - 2026-05-14 active cash expense payload fix

- User showed the regenerated `04_현금출금결의서.pdf` still had duplicate lines: `CAD PC 1EA` twice, `모니터 1EA` four times, `Windows 11 Pro 1EA` twice.
- Actual active bug was in `_build_expense_report_text()` inside `web_v1/backend/output_set.py`: non-consumables were still iterated row-by-row.
- Fixed active Excel payload aggregation:
  - non-consumables group by item name and sum quantity/amount;
  - consumables still compact to top item plus `외 N건`;
  - total now reads `total_sum`, `total`, or `amount` before falling back to row sums.
- Remaining WEB fallback return paths were removed from both expense-report generation branches.
- Verified with runtime payload sample: `CAD PC 2EA`, `모니터 4EA`, `Windows 11 Pro 2EA`, amount `￦5,118,560`.

## Compact Context Snapshot - 2026-05-14 cash expense Excel-only fix

- User rejected the WEB-drawn fallback PDF path for cash withdrawal/expense reports after preparing the Excel template/security policy.
- `web_v1/backend/output_set.py` now requires Excel-template export for cash expense reports and no longer silently creates a PyMuPDF fallback PDF when the Excel path fails.
- Duplicate non-consumable rows are aggregated before the Excel payload body is written, e.g. `CAD PC 2EA`, `모니터 4EA`, `Windows 11 Pro 2EA`.
- Consumables still use the compact representative line behavior: most expensive consumable plus `외 N건`.

## Compact Context Snapshot - 2026-05-13 fix90

- Latest fix: expense report generation no longer fails the API when Excel COM export fails.
- Root cause: active `generate_expense_report_pdf()` tried Excel export when a template existed, but raised the Excel COM error instead of falling back.
- `web_v1/backend/output_set.py` now falls back to the WEB PDF generator if Excel export fails and returns success when the fallback PDF exists.
- Verification:
  - `py_compile` passed for `web_v1/backend/output_set.py` and `web_v1/backend/app.py`.
  - Forced Excel-export failure created a valid test PDF, then the test folder was removed.
- This is server/backend only; 담당자 PC Agent update is not required for this fix.
- When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-05-13 fix89

- Latest fix: expense report Excel template setup gate.
- WEB/Agent version bumped to `1.0.84`.
- 담당자 PC Agent now installs/checks the cash withdrawal template at `%APPDATA%\양식_현금출금정산서.xlsx`.
- If that file already exists, Agent leaves it untouched and setup passes.
- Agent also checks nearby Roaming/LocalAppData/LocalLow fallback paths, but the intended primary path is the Roaming root.
- Agent/server bundle hash now covers code payload only (`web_v1/agent`, `web_v1/backend`, `web_v1/deploy`, `web_v1/VERSION`) and excludes support Excel files so changing the template does not force a version mismatch.
- Output-set expense generation now prefers the same Roaming-root template.
- When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-05-13 fix87

- Latest fix: manual upload UI consolidation.
- Current WEB/Agent version remains `1.0.81`; this is a server/frontend hotfix.
- Purchase detail now shows one visible `자료 수동업로드` button instead of separate quote/approval/voucher upload buttons.
- The chooser supports five document types: tax invoice, quote, ERP voucher, approval document, and cash withdrawal/expense report.
- New backend endpoints:
  - `POST /api/invoices/{id}/tax-invoice`
  - `POST /api/invoices/{id}/expense-report-file`
- `update_invoice_pdf_path()` was added so a manually uploaded tax invoice updates both the `invoices.pdf_path` column and JSON data.
- Verification done:
  - `node --check web_v1\frontend\app.js` passed.
  - `py_compile` passed for `web_v1/backend/app.py` and `web_v1/backend/invoice_db.py`.
- When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-05-13 fix84

- Latest fix: output-set cleanup plus expense-report fallback.
- Current WEB/Agent version remains `1.0.81`; this is a server/frontend hotfix.
- Latest deployment ZIP: `C:\Tmp\accounting_web_v1_clean_output_expense_fix84_20260513_142000.zip`.
- Important:
  - `POST /api/invoices/{id}/approval` no longer calls `reset_invoice()` and no longer rewrites `erp_ready`, so attaching/replacing approval PDFs should not send completed invoices back to waiting.
  - `generate_expense_report_pdf()` still tries Excel export first, but if Excel COM fails with `-2147221005` or the template is missing, it writes a direct PyMuPDF fallback PDF.
  - Purchase UI default is now 담당자 mode. `상세모드` reveals admin diagnostics/logs/delete/demo/recent jobs/individual output controls.
- Verification done:
  - `node --check web_v1\frontend\app.js` passed.
  - `py_compile` passed for `web_v1/backend/app.py`, `web_v1/backend/output_set.py`, and `web_v1/backend/worker.py`.
  - Fallback PDF generation test succeeded.
- When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-05-13 fix83

- Latest fix: manual approval replacement plus cash withdrawal/expense report generation restore.
- Current WEB/Agent version remains `1.0.81`; this is a server/frontend hotfix.
- Latest deployment ZIP: `C:\Tmp\accounting_web_v1_manual_approval_expense_fix83_20260513_133809.zip`.
- Important:
  - The active `web_v1/frontend` directory had been missing in the local workspace and was restored from the latest fix81 bundle before applying this change.
  - Purchase detail now has `품의 첨부/교체`; uploads use `replace=true`, clear old approval paths/files, and refresh output-set status.
  - Purchase output set now has `현금결의서 생성`; it calls `POST /api/invoices/{id}/expense-report`.
  - Expense report generation uses the existing Excel template candidates and CS-style payload: non-consumables itemized, consumables collapsed to top item plus `외 N건`.
- Verification done:
  - `node --check web_v1\frontend\app.js` passed.
  - `py_compile` passed for `web_v1/backend/app.py`, `web_v1/backend/output_set.py`, and `web_v1/backend/worker.py`.
- When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-05-13 13:10

- Latest server-side hotfix: purchase ERP slip summary label.
- Current WEB/Agent version remains `1.0.81`; do not force 담당자 PC refresh for this summary-only backend fix.
- Latest deployment ZIP: `C:\Tmp\accounting_web_v1_purchase_summary_fix82_latest.zip`.
- Latest change:
  - `web_v1/backend/erp_runner.py` no longer concatenates every purchase item name into the final `부가세대급금` / `가지급금(업체)` summaries.
  - Non-consumables remain visible by item name.
  - Only `소모품비` items are collapsed to the most expensive consumable item plus `외 N건`.
  - Verified examples:
    - Only consumables -> `싱글 광점퍼코드 10M 외 3건`
    - Mixed assets/consumables -> `CAD PC, 모니터, 마우스 외 1건`
- Verification done:
  - `py_compile` passed for `web_v1/backend/erp_runner.py`.
- When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-05-13 12:30

- Latest fix is `fix81` for ERP bottom management-item input speed.
- Current WEB version: `web_v1/VERSION = 1.0.81`.
- Latest deployment ZIP: `C:\Tmp\accounting_web_v1_mgmt_speed_fix81_latest.zip`.
- Important: 담당자 PC Agent/update payload must be refreshed after server update, because manager v6.2 changed again.
- Fix81 details:
  - User said management item entry is slower than manual entry.
  - Manager v6.2 now lowers `pyautogui.PAUSE` during fast ERP input.
  - Management-field defaults are faster but still keep small non-zero waits:
    - `ERP_MGMT_KEY_WAIT` default `0.025`
    - `ERP_MGMT_COMMIT_WAIT` default `0.06`
    - `ERP_MGMT_FOCUS_WAIT` default `0.03`
    - `ERP_MGMT_CLICK_WAIT` default `0.04`
  - Management path skips extra modifier-release sleeps and caches the last clipboard value to avoid repeated `pyperclip.copy()` calls.
  - Top-field validation and save/print paths were not relaxed.
- Verification done:
  - `py_compile` passed for manager v6.2, backend app/erp_runner, and agent.
  - `_build_user_pc_payload_zip()` contains `payload/manager_server/전표 자동화 프로그램(담당자용)_v6.2.py`.
  - Payload VERSION is `1.0.81`.
- When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-05-13 12:10

- Latest fix is `fix80` for ERP voucher PDF Save As dialog hotkeys.
- Current WEB version: `web_v1/VERSION = 1.0.80`.
- Latest deployment ZIP: `C:\Tmp\accounting_web_v1_pdf_save_hotkeys_fix80_latest.zip`.
- Important: 담당자 PC Agent/update payload must be refreshed after server update, because manager v6.2 changed again.
- Fix80 details:
  - User said the Save As dialog still had no response.
  - Manager v6.2 now uses a keyboard-first route before UIA/Edit fallback:
    `Alt+D` -> paste folder -> `Enter` -> `Alt+N` -> paste filename -> `Alt+S`.
  - This targets the Windows common file dialog directly and should handle `다음 이름으로 프린터 출력 저장` even when pywinauto Edit controls do not respond.
- Verification done:
  - `py_compile` passed for manager v6.2, backend app/erp_runner, and agent.
  - `_build_user_pc_payload_zip()` contains `payload/manager_server/전표 자동화 프로그램(담당자용)_v6.2.py`.
  - Payload VERSION is `1.0.80`.
- When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-05-13 11:55

- Latest fix is `fix79` for ERP voucher PDF Save As dialog.
- Current WEB version: `web_v1/VERSION = 1.0.79`.
- Latest deployment ZIP: `C:\Tmp\accounting_web_v1_pdf_save_dialog_fix79_latest.zip`.
- Important: this fix changes `manager_server\전표 자동화 프로그램(담당자용)_v6.2.py`, so 담당자 PC Agent/update payload must be refreshed. Server-only update is not enough.
- Fix79 details:
  - Windows Save As dialog title `다음 이름으로 프린터 출력 저장` was not detected, so ERP voucher output stopped at the filename dialog.
  - Manager v6.2 now detects broader PDF save dialog titles and generic file-save dialogs.
  - The save path is pasted via clipboard into the filename field, then Save/Enter is sent.
  - WEB payload builder now uses `settings.legacy_manager_path` so the actual Korean manager file is included in 담당자 PC installer payload.
  - Agent bundle version was bumped to `1.0.79`.
- Verification done:
  - `py_compile` passed for manager v6.2, backend app/erp_runner, and agent.
  - `_build_user_pc_payload_zip()` contains `payload/manager_server/전표 자동화 프로그램(담당자용)_v6.2.py`.
  - Payload VERSION is `1.0.79`.
- When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-05-13 11:40

- Latest server hotfix scope:
  - Latest deployment ZIP: `C:\Tmp\accounting_web_v1_cadpc_approval_path_fix78_latest.zip`.
  - `CAD PC` is a proper-name PC item and must be treated as `집기비품`, not `컴퓨터소프트웨어`.
  - `web_v1/backend/purchase_analysis.py` now forces `CAD PC -> 집기비품` before generic CAD/software rules.
  - `web_v1/backend/app.py` normalizes purchase-analysis items before manual save, so "분석 저장" does not teach the dictionary the wrong account.
  - `web_v1/backend/invoice_db.py` also protects dictionary learning from saving `CAD PC` as software.
  - `web_v1/backend/config.py` ignores a missing/mojibake `LEGACY_MANAGER_PATH` and falls back to the actual Korean v6.2 file under `manager_server`.
- Verification done:
  - `py_compile` passed for `purchase_analysis.py`, `config.py`, `app.py`, and `invoice_db.py`.
  - Runtime check: `_normalize_items_for_display([{"name": "CAD PC"}])` returns account `집기비품`.
  - Runtime check: `settings.legacy_manager_path` resolves to `manager_server\전표 자동화 프로그램(담당자용)_v6.2.py` and exists.
- This is server-side only; no Agent code/version bump is needed for this hotfix.
- When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-05-13 11:08

- User explicitly reminded: update markdown work memory/devlog after durable WEB changes. Do not skip this.
- Active WEB root: `C:\Users\user\Desktop\개발파일\회계업무 자동화_WEB_Version`.
- Current WEB version after latest change: `web_v1/VERSION = 1.0.77`.
- Latest deployment ZIP: `C:\Tmp\accounting_web_v1_agent_voucher_upload_fix77_latest.zip`.
- Latest fix scope:
  - ERP voucher PDF save is now automatic and strict.
  - User-PC Agent uploads the saved ERP voucher PDF to the operating server after ERP input completes.
  - Server stores the voucher at `C:\ERP_DB\erp_vouchers\{invoice_id}\01_전표.pdf`.
  - Server updates invoice JSON paths `erp_pdf_path`, `erp_voucher_pdf_path`, and `voucher_pdf_path`, then persists `output_docs`.
  - Output-set refresh should now detect `erp_voucher` without the user manually attaching the voucher.
  - If the local ERP PDF was not actually created, `web_v1/backend/erp_runner.py` raises `ERP 전표 PDF 자동 저장 실패`.
  - If Agent upload fails, the job logs the local path/upload error instead of pretending the server has the voucher.
- Files changed for fix77:
  - `web_v1/backend/app.py`: added `POST /api/agent/jobs/{job_id}/voucher` and safer ERP completion path handling.
  - `web_v1/agent/erp_agent.py`: added `_upload_erp_voucher()` and `AGENT_BUNDLE_VERSION = "1.0.77"`.
  - `web_v1/backend/erp_runner.py`: verifies PDF exists before returning.
  - `manager_server/전표 자동화 프로그램(담당자용)_v6.2.py`: PDF save dialog rejects empty path and removes stale same-name PDFs first.
  - `web_v1/deploy/install_operating_server.ps1`: `APP_VERSION=1.0.77`.
  - `web_v1/frontend/index.html`: static cache bust `fix77_agent_voucher_upload`.
- Verification done:
  - `python -m py_compile web_v1/backend/app.py web_v1/backend/erp_runner.py web_v1/agent/erp_agent.py manager_server/전표 자동화 프로그램(담당자용)_v6.2.py` passed.
- Deployment reminder:
  - Both server and 담당자 PC Agent must be updated for fix77. Updating only the server is not enough.
  - When user asks for commands, always provide them numbered `1, 2, 3`, even if repeated.

## Compact Context Snapshot - 2026-04-30 10:15

- User preference: keep durable context in this markdown file, not only in chat memory.
- Always read this file before meaningful work.
- Current main files:
  - Manager app: `C:\Users\user\Desktop\개발파일\회계업무 자동화\전표 자동화 프로그램(담당자용)_v6.2.py`
  - Server app: `C:\Users\user\Desktop\개발파일\회계업무 자동화\전표 자동화 프로그램(서버용)_v3.2.py`
  - Tax crawler root: `C:\Users\user\Desktop\개발파일\세금계산서 크롤링`
  - Crawler entry: `crawler_main.py`
- Latest backup before TAB1/XML and expense-report fix:
  - `C:\Users\user\Desktop\개발파일\회계업무 자동화\backup_tab1_xml_expense_fix_20260430_100831`
- Latest bugfix status:
  - TAB1 purchase invoices must prefer old/original portal PDF crawling when mail contains portal links.
  - TAB2 regular invoices must keep current behavior for WEHAGO, CSBill, HomeTax, KT.
  - XML attachment fallback is allowed only when no link/html/pdf/KT target was found.
  - Implemented in server v3.2 mail loop: `if extract_xml_attachments and not targets: ...`
  - Expense report body must include all mixed accounts: asset, software, consumables.
  - Implemented in manager v6.2:
    - `_expense_items_from_entries()` starts from `self.data["items"]` and overlays UI edits.
    - `_build_expense_report_text()` groups asset/software/consumables and includes all groups.
- Verification already done after latest fix:
  - `python -m py_compile "전표 자동화 프로그램(서버용)_v3.2.py"` passed.
  - `python -m py_compile "전표 자동화 프로그램(담당자용)_v6.2.py"` passed.
- Do not globally remove XML handling.
- Do not build EXE unless user explicitly asks.
- For crawler/server Python changes, save `.py` only.
- Server build handoff folder:
  - `C:\Users\user\Desktop\전표 자동화 프로그램_서버빌드_v3.2`
  - Structure: root server v3.2 py/spec + `세금계산서 크롤링` runtime module folder.
  - Last synced on 2026-04-30 10:15.
  - Backup before sync: `backup_before_sync_20260430_101519`.
  - Synced latest server v3.2 and crawler runtime files.
  - Spec hiddenimports includes `portal_xml` for XML-only fallback packaging.
- 2026-04-30 10:24 bugfix:
  - Problem: Compuzone TAB1 purchase mail still produced XML-rendered simplified invoice PDF.
  - Server v3.2 now blocks XML attachment fallback when subject/body/attachments contain `컴퓨존` or `compuzone`.
  - XML fallback is now allowed only for known regular markers: WEHAGO, CSBill, HomeTax/NTS, KT email, AutoEver.
  - Server build folder was re-synced with this server v3.2 change.
  - Problem: expense report showed `사업장미검출` and `0원` when analysis returned zero totals.
  - Manager v6.2 now recovers site from tax path/filename/data, e.g. `(P3공장)`, and falls back total amount to sum of item `inc_vat`.
  - Both server v3.2 and manager v6.2 passed py_compile after this fix.

## How To Use

- Start each meaningful turn by reading this file first.
- Do not rely on chat history for durable project facts.
- After code, routing, sample, or workflow changes, update this file briefly.
- Keep this file compact. Move verbose details to existing `DEVLOG.md` only when needed.
- Before editing production files, create timestamped backups of touched files.

## Project Roots

- Accounting app root: `C:\Users\user\Desktop\개발파일\회계업무 자동화`
- Tax crawler root: `C:\Users\user\Desktop\개발파일\세금계산서 크롤링`
- Server download/result root: `C:\ERP_DB\downloads`
- Main manager: `전표 자동화 프로그램(담당자용)_v6.2.py`
- Main server: `전표 자동화 프로그램(서버용)_v3.2.py`
- Crawler entry: `crawler_main.py`

## Current Architecture

- Mail arrives at server v3.2.
- Server v3.2 imports `crawler_main.py` from the tax crawler folder.
- `crawler_main.py` detects links/attachments and routes to `portal_*` handlers.
- Handler saves PDF and normalized JSON.
- Server stores result into `invoices` DB with `invoice_type=regular`.
- Manager v6.2 displays it in the regular tax invoice tab and can create ERP slip/print.

## Active Portal Handlers

- `portal_unipost.py`: Unipost.
- `portal_wehago.py`: WEHAGO, XML parsing, Chrome permission, Duzon preview PDF save.
- `portal_hometax.py`: HomeTax secure HTML, auth, XML extraction, rendered PDF save.
- `portal_csbill.py`: CSBill auth, XML parsing, invoice frame/print page PDF save.
- `portal_autoever.py`: Hyundai AutoEver one-time password, popup parse, popup PDF save.
- `portal_kt.py`: KT encrypted PDF attachment decrypt/parse/save.
- `portal_uplus.py`: kept as legacy, excluded from active automation.

## Known Test Assets

- WEHAGO URL: `https://www.wehago.com/invoice/#/eTaxMail/VFgyMDI2MDQ2OTQ5MjI3JjEyNTgxMDU2MTk=`
- CSBill URL: `https://www.csbill.co.kr/noRegIssueView.do?mode=view&mana_Bill_Numb=202640254004&mail=ds1500@dae-seung.co.kr&listYn=N&supp_Mail=N`
- AutoEver URL: `https://etax.autoever.com/?flag=noMbr`
- AutoEver sample password: `2026042098s6hv0m399p`
- HomeTax sample: `C:\Users\user\Desktop\개발파일\세금계산서 크롤링\NTS_eTaxInvoice.html`
- KT sample PDFs are in `C:\Users\user\Desktop\개발파일\세금계산서 크롤링`.

## KT Password Rules

- `(704100003***)`: Daeseung Precision. Try P1 `32697`, then P4 `07029`.
- `(W00115***)`: Ilgang 1 factory. Use `51622`.
- `(W00127***)`: manual handling; skip automation.
- `(z!23820968***)`: Daeseung corporate reg no `134711-0003577`, use last 7 digits `0003577`.

## Important Working Rules

- Do not patch Korean source through PowerShell inline heredocs.
- For external crawler edits, prefer `apply_patch` when possible.
- If a helper script is needed, create it as a UTF-8 file in the accounting app root, then execute it.
- Server/crawler files should stay as `.py`; do not build server exe unless explicitly requested.
- Manager exe can be rebuilt when manager `.py` changes and user asks for it.
- For portal failures, collect/debug with HTML dumps, JSON summaries, screenshots, or actual output files before changing logic.

## Current Verification Notes

- Manager v6.2 and server v3.2 both passed `py_compile` on 2026-04-30.
- Server v3.2 uses the new crawler interface: `crawl_invoice(target, mail_text=body, mail_date=mail_date, mail_subject=subject)`.
- Manager v6.2 has the regular tax invoice tab and KT/communication expense ERP handling.
- Some old Korean text in server v3.2 appears mojibake in shell output, but syntax currently passes.
- 2026-04-30 10:46 U+ Compuzone routing fix:
  - Problem: Compuzone purchase mail had XML attachment only in logs because U+ portal link was not extracted, then XML fallback was blocked, causing `target count: 0`.
  - Fix: `crawler_main.py` now extracts `edocu.uplus.co.kr` links and activates `portal_uplus.UplusPortalHandler`.
  - `portal_uplus.py` is now an adapter that routes to legacy `uplus_handler.UplusEDocuHandler`, so Compuzone uses the original U+ PDF flow instead of XML-rendered fallback.
  - Synced runtime files to server build handoff folder: `crawler_main.py`, `portal_uplus.py`, `uplus_handler.py`, `uplus_edocu_handler.py`, `test_xml.py`.
  - Updated server v3.2 spec hiddenimports: `portal_uplus`, `uplus_handler`, `uplus_edocu_handler`, `test_xml`.
  - Fixed a syntax error in `uplus_edocu_handler.py` f-string quote.
  - Verified: py_compile passed for server/root crawler/build files; local extraction test maps `edocu.uplus.co.kr` to handler `uplus`.

## Next Likely Work

- Continue portal-specific parsing precision work, especially KT/AutoEver/CSBill/HomeTax filename and field extraction.
- When context gets large, compress chat into this file instead of relying on conversation memory.
## 2026-04-30 TAB1 XML / 결의서 혼합 계정 버그 수정
- 수정 전 백업: `backup_tab1_xml_expense_fix_20260430_100831`
- TAB1 컴퓨존 구매 세금계산서가 XML 첨부 기준 단순 PDF로 생성되는 원인:
  - `전표 자동화 프로그램(서버용)_v3.2.py` 메일 처리에서 포털 링크가 있어도 `extract_xml_attachments()`를 무조건 targets에 추가했다.
  - 그 결과 링크 크롤링으로 받은 원본 PDF 대신 XML fallback 결과가 같이 처리될 수 있었다.
- 수정:
  - 서버용 v3.2에서 링크/홈택스 HTML/KT PDF 등 기존 타깃이 하나라도 있으면 XML 첨부를 추가하지 않는다.
  - XML 첨부 fallback은 targets가 비어 있을 때만 수행한다.
  - 의도: TAB1 구매는 예전처럼 포털 원본 PDF 크롤링 우선, TAB2 정기수신처럼 XML만 있는 메일은 현 방식 유지.
- 결의서 혼합 계정 누락 보강:
  - 담당자용 v6.2 `_expense_items_from_entries()`가 화면 입력행뿐 아니라 `self.data["items"]` 전체를 기준으로 삼고, 화면 수정값만 덮어쓰도록 변경.
  - `_build_expense_report_text()`에서 집기비품/컴퓨터소프트웨어/소모품비를 계정별로 모두 본문에 넣는다.
  - 소모품비는 가장 비싼 품목 외 N건 합계 방식, 집기비품/컴퓨터소프트웨어는 품목별 라인 방식 유지.
- 검증:
  - `python -m py_compile "전표 자동화 프로그램(서버용)_v3.2.py"` 통과.
  - `python -m py_compile "전표 자동화 프로그램(담당자용)_v6.2.py"` 통과.

## 2026-04-30 컴퓨존 U+ 크롤링 대상 중복 및 구매 탭 누락 버그 수정
- **문제 1: U+ 메일 수신 시 불필요한 푸터 링크까지 크롤링 시도 (`target count: 3`)**
  - 원인: `crawler_main.py`의 `extract_links_from_mail`에서 `edocu.uplus.co.kr` 도메인만 체크하여 `main.intro.WebtaxInfo.do` (안내), `main.Counsel.do` (고객센터) 링크까지 추출됨. 
  - 수정: `"edocu.uplus.co.kr"` 포함 시 반드시 `"main.invoiceinfo.do"`가 있어야만 추출하도록 필터링 조건 강화 (불필요한 세션 오류 해결).
- **문제 2: 담당자용 v6.2 exe의 "컴퓨존 구매 회계처리" 탭에 신규 수신 내역이 안 뜸**
  - 원인: 기존 XML 파싱(`portal_xml.py`)은 `invoice_type="purchase"`를 부여했으나, U+ 크롤러(`portal_uplus.py`)는 `invoice_type`을 부여하지 않음. 서버(`v3.2.py`)의 `_insert_crawler_invoice` 로직이 비어있는 `invoice_type`을 `"regular"`(정기)로 강제 할당하여, 구매(purchase) 탭 필터링에서 누락됨.
  - 수정: 서버(`v3.2.py`) `_insert_crawler_invoice` 로직에 `subject`나 `vendor_name`에 "컴퓨존"이 포함되어 있으면 무조건 `invoice_type="purchase"`로 강제 할당하도록 조건 추가.

## 2026-04-30 WEHAGO 인쇄 버튼 누락(최초 열람 확인 창) 대응
- **문제**: WEHAGO 메일 최초 열람 시, 상단에 [확인] 버튼을 눌러야만 [인쇄] 버튼이 노출되는 UI로 인해 WEHAGO 인쇄 버튼 없음 에러 발생.
- **해결**: portal_wehago.py의 _click_print 로직 수정.
  1. [인쇄] 버튼이 화면에 없을 경우,
  2. [확인] 버튼이 있는지 스캔하고, 있다면 클릭 후 alert창(있다면) 수락, 1.5초 대기.
  3. 다시 [인쇄] 버튼을 찾아 클릭하도록 안전하게 폴백 로직 구현.

## 2026-04-30 WEHAGO PDF 저장 다이얼로그 '새 폴더' 클릭 오작동 수정
- **문제**: 한국어 Windows '다른 이름으로 저장' 다이얼로그에서 파일명 입력란 단축키인 Alt+N이 상단의 새 폴더(&N) 버튼과 겹쳐서, 파일명이 입력되지 않고 downloads 폴더 안에 불필요한 '새 폴더'가 생성되는 문제 발생.
- **해결**: portal_wehago.py의 _save_pdf_dialog에서 파일명란에 강제 포커싱하는 로직을 견고하게 변경.
  - Alt+T를 눌러 충돌 없는 파일 형식(&T) 드롭다운을 먼저 포커싱한 후, Shift+Tab을 한 번 눌러 바로 이전 칸인 파일 이름(&N) 필드로 역이동(focus)하는 방식으로 단축키 충돌 원천 차단.

## 2026-04-30 WEHAGO PDF 저장 다이얼로그 '새 폴더' 생성 및 오작동 완벽 수정
- **원인 분석**: 
  - _paste_text에서 	kinter 클립보드 복사가 실패할 경우 pyautogui.write()가 실행되는데, 한글 텍스트(대승정밀 등)는 입력되지 않고 영어 경로명(C:\ERP_DB\downloads)만 타이핑 됨.
  - 이 과정에서 직전에 사용한 Alt 키가 OS 단축키 큐에 남아있거나, 혹은 downloads의 d와 
이 Alt+D(주소표시줄), Alt+N(새 폴더)를 연달아 트리거하면서 **'새 폴더'가 생성되고 그 안으로 진입**해버리는 참사가 발생함.
- **해결**: 
  - _paste_text: 불안정한 	kinter와 위험한 pyautogui.write() 폴백을 완전히 제거. 윈도우 네이티브 API인 win32clipboard 모듈을 최우선으로 사용하여 100% 안정적으로 유니코드 텍스트를 클립보드에 복사하도록 수정.
  - _save_pdf_dialog: Alt 키 관련 단축키(Alt+T, Alt+N 등) 조작을 아예 삭제. pyautogui.keyUp으로 꼬인 모디파이어 키를 강제 초기화한 후, pywinauto를 이용해 화면 하단부의 Edit 컨트롤(실제 파일명 입력란)을 직접 찾아 set_edit_text로 안전하게 텍스트를 주입하도록 원천 수정.

## 2026-04-30 컴퓨존(U+) PDF 저장 시 '새 폴더' 생성 버그 및 DB 누락 대응
- **문제 분석**: 
  - 관리자용 앱(v6.2.py)의 탭(TAB1 구매)에 오전 11:21 컴퓨존 수신건은 나타나고 있으나, 오후 1:08에 테스트한 컴퓨존 수신건은 나타나지 않음.
  - 로그 및 파일 상태를 점검한 결과, 컴퓨존은 uplus_edocu_handler.py를 통해 저장되는데 해당 파일 내부에 아까 WEHAGO에서 문제가 되었던 불안정한 단축키 방식(Alt+D 경로지정 후 Alt+N 파일명 지정)이 그대로 잔존하고 있었음.
  - 이 때문에 Alt+N이 윈도우의 '새 폴더' 버튼을 눌러버리고 임시 파일명(	emp_xxx.pdf)을 새 폴더 이름으로 저장한 뒤 프로그램 에러를 뱉고 뻗어버림.
  - **크롤러가 도중에 에러(RuntimeError)로 뻗었기 때문에 서버가 해당 수신건을 DB(learned_data.db)에 INSERT하지 않았음.** 결과적으로 파일(수동 다운로드 된 것 등)만 남고 관리자 화면의 구매 탭(TAB1) 목록에는 누락되는 현상이 발생.
- **해결**:
  - uplus_edocu_handler.py의 _save_pdf_via_print 함수 내부에 존재하던 pyautogui.hotkey('alt', 'n') 로직을 전부 삭제.
  - 아까 WEHAGO에서 성공한 가장 안전한 방식(pywinauto를 이용해 '다른 이름으로 저장' 창의 실제 파일명 Edit 컨트롤을 잡아 절대경로를 set_edit_text하고, 다이렉트로 {ENTER} 키를 날리는 방식)을 동일하게 이식함.

## 2026-04-30 담당자용 프로그램(v6.2.py) TAB1 구매 탭 수동 삭제 기능 추가
- **요청 내역**: 동일한 테스트 메일을 여러 번 전송하면서 서버 DB에 이전 수신건이 남아 중복(duplicate skipped) 처리되는 이슈 확인. 이를 해결하고 목록을 관리하기 위해 TAB1(구매)에도 TAB2와 동일한 수동 삭제 버튼 추가 요청.
- **수정 내역**: 
  - 전표 자동화 프로그램(담당자용)_v6.2.py 수정
  - delete_purchase_invoice 메서드를 새로 구현하여 기존의 delete_regular_invoice와 동일한 방식의 DB API 호출 및 화면 갱신 적용
  - TAB1의 버튼 프레임(tn_frame)에 '선택 항목 삭제' 버튼 UI 컴포넌트 추가 완료

## 2026-04-30 SmartBill/WEHAGO crawler fix
- SmartBill added in external crawler as `portal_smartbill.py`; server imports through `crawler_main.py`.
- Fixed SmartBill result quality:
  - `supports()` now matches smartbill URL case-insensitively.
  - Parser skips HTML junk like `br`, extracts supplier/buyer names, buyer business number, mapped site name, issue date, total amount, and item name.
  - Result JSON now includes `business_no`, `matched_biz_no`, `invoice_date`, and mapped `site_name` when possible, so manager regular tab no longer shows `[br] br` / blank amount.
- Fixed WEHAGO first-issued/unconfirmed invoice flow:
  - `portal_wehago.py` now repeatedly handles alert/DOM `확인` buttons after the top confirmation click.
  - Added real Korean `확인/인쇄/출력` selectors in addition to older mojibake selectors.
- Updated server specs to include `portal_smartbill` hiddenimport.
- Synced changed `portal_smartbill.py` and `portal_wehago.py` into server build handoff folder.
- Verified:
  - `py_compile` passed for `portal_smartbill.py`, `portal_wehago.py`, `crawler_main.py`, and server v3.2.
  - Local routing test maps `https://www.smartbill.co.kr/xDti/n_mem/test` to `smartbill`.

## 2026-04-30 WEHAGO Save As new-folder guard
- User reported WEHAGO still creating `새 폴더` from the Windows Save As dialog.
- Root cause: `_save_pdf_dialog()` set the filename Edit text and then sent Enter; when the file list/folder row had focus, Windows interpreted Enter as opening/creating the selected folder instead of saving.
- Fix in external `portal_wehago.py`:
  - Removed Enter submission from Save As flow.
  - `_save_pdf_dialog()` now sets the full target path in the filename Edit control and clicks only a real `저장`/`Save` button.
  - If the primary button remains `열기`/`Open`, the routine returns failure instead of pressing Enter.
  - Synced fixed `portal_wehago.py` to server build handoff folder.
- Verified `py_compile` passed for external `portal_wehago.py`.

## 2026-04-30 WEHAGO Save As top New Folder click hard block
- User clarified the immediate bug: the Save As dialog must never click the top `새 폴더` button.
- Updated external `portal_wehago.py` `_click_save_as_save_button()`:
  - Save button candidates are now restricted by geometry to the lower-right button area only (`dlg_rect.bottom - 90`, right-side 55%+).
  - Top toolbar buttons, including `새 폴더`, are ignored even if text matching ever goes wrong.
  - Kept blocked text markers for `열기/Open/새 폴더/New Folder`.
- Removed coordinate fallback in `_focus_save_as_filename_field()` that could click inside the Save As dialog if no edit field was found.
- Synced changed `portal_wehago.py` to server build handoff folder.
- Verified `py_compile` passed.

## 2026-04-30 WEHAGO Save As overwrite guard refinement
- Found additional risk: `_confirm_overwrite_dialog()` title regex included `저장`, which could match the Save As dialog title itself (`다른 이름으로 저장`).
- Patched `_confirm_overwrite_dialog()`:
  - Removed `저장` from title matching.
  - Explicitly skips windows titled `다른 이름으로 저장`.
  - Enter fallback only runs after overwrite/replace text is detected.
- Re-synced `portal_wehago.py` to server build handoff and verified `py_compile` passed.

## 2026-04-30 SmartBill PDF text fallback parse
- User attached bad SmartBill PDF: `C:\Users\user\Downloads\세금계산서 - 공급자미상(세금계산서)_사업장미상_2026년 04월_4.pdf`.
- Root cause: `portal_smartbill.py` built the final filename from original page HTML before saving PDF. In some SmartBill states the original DOM did not expose invoice fields, but the saved/print PDF text contained the correct values.
- Fix:
  - After `_save_pdf()`, parse the saved PDF text with PyMuPDF (`fitz`).
  - If PDF parse is better than initial HTML parse, replace supplier/buyer/business/site/date/amount/item values and rename the saved PDF to the corrected filename.
  - Date extraction now prefers the `작성일자 공급가액 세액` table row, avoiding the notice text date `2013.4.1`.
- Verified with attached PDF parser output:
  - supplier `대신아이씨티(주)`, buyer `(주)대승`, buyer biz `1258105619`, site `D1공장`, issue date `20260430`, supply `250000`, tax `25000`, total `275000`, item `4월분 통합 보수료`.
- `py_compile` passed and `portal_smartbill.py` was synced to server build handoff folder.

## 2026-04-30 SmartBill/WEHAGO hardening after repeat failure
- User reported the same two failures still appearing in runtime: WEHAGO still leaving `새 폴더*`, SmartBill still showing `공급자미상`.
- WEHAGO:
  - Added cleanup/recovery for newly created `새 폴더*` under target downloads, Downloads, Documents, and Desktop.
  - If a PDF lands inside that folder, newest recent PDF is moved back to the intended final path.
  - Recent empty/safe `새 폴더*` folders are removed even on early Save As failures (`filename_set_failed`, `save_button_not_clicked`).
  - Debug goes to `_debug_wehago_saveas.txt`.
- SmartBill:
  - Added PDF text extraction fallback using `fitz` then `pdfplumber`, plus `pdf_text_head`/error debug in `_debug_smartbill_parse.txt`.
  - `crawler_main.py` now logs the exact loaded handler module path.
  - Server v3.2 now runs `_repair_smartbill_result_from_pdf()` before inserting crawler invoices. Even if crawler result still says `공급자미상`, the server reads the saved PDF, rewrites `subject`, `vendor_name`, `site_name`, business number, amounts, date, items, and renames the PDF.
- Deployment sync:
  - Copied latest `crawler_main.py`, `portal_smartbill.py`, `portal_wehago.py`, and server v3.2 into both `전표 자동화 프로그램_서버빌드_v3.2` and `전표자동화_전달용_20260430_091404\서버용_v3.2`.
  - Added `portal_smartbill`/`portal_xml` hiddenimports to the old delivery spec.
- Verified:
  - Attached bad SmartBill PDF parses to supplier `대신아이씨티(주)`, buyer `(주)대승`, site `D1공장`, date `20260430`, total `275000`, item `4월분 통합 보수료`.
  - Server repair test on a `C:\Tmp` copy renamed it to `세금계산서 - 대신아이씨티(주)(4월분 통합 보수료)_(주)대승(D1공장)_2026년 04월.pdf` and returned corrected manager-display JSON.
  - `py_compile` passed for main crawler/server files and both copied deployment folders.

## 2026-05-06 Manager v6.2 regular ERP account/vendor management fix
- User reported two manager-side regular accounting issues:
  - `동양정보통신` was being classified as `통신비` because the vendor name contains `통신`; it must be `지급수수료`.
  - For `대승정밀` regular `지급수수료`, ERP management item `거래처` must be filled; for `동양정보통신`, select the vendor row whose business number is `402-81-23213` rather than the personal-business row `402-12-65712`.
- Changed `전표 자동화 프로그램(담당자용)_v6.2.py`:
  - `_guess_regular_account()` now returns `지급수수료` for `동양정보통신` and `대신아이씨티` before generic `통신` keyword checks.
  - ERP management `_corp_group()` distinguishes `대승정밀` / P factories from generic `대승`.
  - Management plans now set `("지급수수료", "대승정밀") -> ["vendor"]`.
  - Generalized vendor picker target business-number selection; `동양정보통신` uses search name `동양정보통신` and selects business number `402-81-23213`.
- Verified `py_compile` passed and rebuilt `dist\전표 자동화 프로그램(담당자용)_v6.2.exe`.
- Synced rebuilt exe and updated py to `전표자동화_전달용_20260430_091404\담당자용_v6.2`; synced updated py to `전표 자동화 프로그램_서버빌드_v3.2`.

## 2026-05-06 Manager v6.2 tax invoice preview button
- User requested a `세금계산서 미리보기` button in the manager app.
- Added shared `preview_tax_invoice()` method that opens the current `tax_path` with the Windows default PDF viewer via `os.startfile()`.
- Added preview buttons:
  - Purchase tab tax action panel: `🔍 세금계산서 미리보기`
  - Regular tab bottom action row: `세금계산서 미리보기`
- Button state now follows tax PDF availability in `_refresh_tax_action_buttons()` and `_refresh_regular_action_buttons()`.
- Verified `py_compile` passed.
- Rebuilt `dist\전표 자동화 프로그램(담당자용)_v6.2.exe`; first build failed because old local exe processes locked the output, then rebuild succeeded after those processes exited.
- Synced rebuilt exe and updated py to `전표자동화_전달용_20260430_091404\담당자용_v6.2`; synced updated py to `전표 자동화 프로그램_서버빌드_v3.2`.

## 2026-05-06 Manager v6.2 multi-select receive-list actions
- User requested multi-select manual completion and deletion for both manager receive-list tabs.
- Changed purchase tab (`self.tv`) and regular tab (`self.regular_tv`) to `selectmode="extended"` so Ctrl/Shift multi-select works.
- Updated `complete_invoice_manually()`, `delete_purchase_invoice()`, `complete_regular_invoice_manually()`, and `delete_regular_invoice()`:
  - They now operate on all selected rows.
  - Manual completion skips rows already marked completed.
  - Each action shows one count-based confirmation dialog, processes rows one by one via the existing server APIs, refreshes both dashboards once, and reports partial failures if any server call fails.
- Verified `py_compile` passed.
- Rebuilt `dist\?꾪몴 ?먮룞???꾨줈洹몃옩(?대떦?먯슜)_v6.2.exe`.
- Synced rebuilt exe and updated py to the manager handoff folder; synced updated py to the server-build folder.

## 2026-05-13 WEB v1.0 expense report template path fix85
- User pointed out the original CS Excel cash expense template exists in document-centralized storage:
  `Y:\관리총괄\경영지원본부\전산팀\2파트\2파트 개인 자료\김기창\현금출금결의서 양식\양식_현금출금정산서.xlsx`.
- Confirmed the current Codex/server execution session cannot see that `Y:` path (`Test-Path` returned false), which explains why server-side WEB generation did not use the CS template while the old 담당자 PC CS program could.
- Updated `web_v1/backend/output_set.py` so expense report template candidates now include environment overrides, the original CS `Y:` path, server-stable `C:\ERP_DB\templates\expense_template.xlsx`, and existing Korean template names under `C:\ERP_DB\templates` / `support`.
- Improved the non-Excel fallback PDF to mimic the CS 현금출금결의서(정산서) layout instead of the temporary plain WEB layout.
- Verified `py_compile` passed and fallback PDF generation created `C:\Tmp\expense_fallback_fix85_test.pdf`.

## 2026-05-13 WEB v1.0 expense Excel template asset/helper fix86
- User provided local `C:\Users\user\Downloads\양식_현금출금정산서.xlsx` and clarified WEB should not draw an arbitrary PDF when the Excel form exists.
- Inspected workbook:
  - sheet `출력용`, print area `A1:R42`, top slot cells match old CS code: `D5/D6/G6/D7/D8/D9/C11/B19`.
  - the local copy has normal Archive attribute, but document-centralized `Y:` may appear to exist while direct read raises `PermissionError`.
- Copied the supplied workbook into `support/expense_template.xlsx` so update ZIPs can carry the known-good Excel form.
- Added `_is_readable_template()` so inaccessible `Y:` paths are skipped instead of blocking template selection.
- Split Excel PDF export into `web_v1/backend/expense_excel_export.py`, run by `output_set.py` as a bounded subprocess (`EXPENSE_REPORT_EXCEL_TIMEOUT`, default 30s). This prevents a hung Excel COM call from freezing the WEB request and kills new orphan Excel processes on timeout.
- Changed behavior: when a readable Excel template exists but Excel PDF conversion fails, the API now returns a clear failure instead of silently producing a WEB-drawn fallback PDF.
- Verified syntax for `output_set.py` and `expense_excel_export.py`; short-timeout runtime test returned the expected timeout error and left no Excel process.
## 2026-05-13 WEB v1.0 expense AppData template/workspace fix88
- Expense report generation now assumes Excel can safely write only under `%APPDATA%`. The Agent `1.0.82` preflight copies `support\expense_template.xlsx` to `%APPDATA%\AccountingWeb\templates\expense_template.xlsx` only when the Roaming copy is missing.
- `output_set.py` now exports the working XLSX and temporary PDF under `%APPDATA%\AccountingWeb\expense_reports\{invoice_id}` and moves the finished PDF back to `C:\ERP_DB\expense_reports\{invoice_id}`. This is intended to work with document-security policies that allow Excel read/write for `<APPDATA>`.
- Setup status includes an `expense_template` check so operators can see whether the Roaming Excel template is ready.

## 2026-05-13 WEB v1.0 manual purchase upload fix91
- Added a true manual purchase intake path: `POST /api/invoices/manual-purchase` creates a new purchase invoice from uploaded tax-invoice PDF and optional quote PDF, without mail collection or crawler involvement.
- The manual create flow parses tax order number/date/amounts, saves the quote under the purchase quote folder, attempts normal purchase analysis when both PDFs are present, and returns the newly selected invoice.
- Frontend `자료 수동업로드` now opens even with no selected row. The modal has a top "신규 구매자료 등록" area and keeps existing selected-row attachment buttons below it.
