# Devlog

## 2026-05-14 WEB v1.0 fix95 cash expense Excel PDF export no-save

- User showed Excel opening a `다른 이름으로 저장` dialog with `.xlsx` selected while generating the cash withdrawal/expense report.
- Root cause: `web_v1/backend/expense_excel_export.py` called `workbook.Save()` before `ExportAsFixedFormat`. Under the 담당자 PC document/security environment this can trigger an Excel workbook Save As dialog and block the helper until timeout.
- Changed the helper to fill the template in memory, skip workbook save, activate the output sheet, export directly with `ExportAsFixedFormat(...pdf)`, and mark the workbook as saved before closing without changes.
- Bumped WEB/Agent version to `1.0.87` because the 담당자 PC Agent must receive the helper change.
- Verified:
  - `py_compile` passed for `web_v1/backend/expense_excel_export.py` and `web_v1/agent/erp_agent.py`.

## 2026-05-14 WEB v1.0 cash expense Agent generation fix

- User clarified the operating server has no Excel installed. The cash withdrawal/expense report path must therefore not run Excel COM on the server.
- Changed `POST /api/invoices/{id}/expense-report` so it queues an `expense_report` task for the 담당자 PC Agent instead of calling server-side Excel conversion.
- Added Agent handling for `expense_report`: the Agent uses the 담당자 PC `%APPDATA%` Excel template and local Excel install, exports the PDF, uploads it back to `/api/agent/jobs/{job_id}/expense-report`, and then marks only the document-set state complete.
- Agent completion for this job type no longer changes the invoice processing status back to done/error; it only refreshes output docs and logs.
- Bumped the Agent bundle to `1.0.86` and verified `py_compile` for the changed server/Agent modules.

## 2026-05-14 WEB v1.0 cash expense active Excel payload aggregation fix

- User confirmed the regenerated cash withdrawal PDF still listed repeated non-consumable rows such as `CAD PC 1EA` twice and `모니터 1EA` four times.
- Root cause: the active Excel payload builder still iterated each non-consumable item row directly. The earlier aggregation note had not actually changed that active branch.
- Changed `web_v1/backend/output_set.py` so non-consumable expense report lines are grouped by normalized item name before writing the Excel payload.
  - Example: repeated `CAD PC` rows now become `CAD PC 2EA`.
  - Example: repeated `모니터` rows now become `모니터 4EA`.
  - Consumables keep the agreed representative behavior: highest item plus `외 N건`.
- Removed the remaining silent WEB fallback return paths from both expense report generation branches; Excel template/export failure now reports the real Excel failure instead of creating an arbitrary fallback PDF.
- Verified:
  - `py_compile` passed for `web_v1/backend/output_set.py`.
  - Runtime payload sample produced `CAD PC 2EA`, `모니터 4EA`, `Windows 11 Pro 2EA`, and the header total `￦5,118,560`.

## 2026-05-14 WEB v1.0 cash expense Excel-only generation fix

- User clarified that WEB must not silently generate an arbitrary fallback PDF for cash withdrawal/expense reports when the Excel template has already been prepared under `%APPDATA%`.
- Changed `web_v1/backend/output_set.py` so cash expense report generation requires the Excel template and Excel export path. If the template or Excel export fails, it now reports the real failure instead of creating a WEB-drawn fallback PDF.
- Fixed the Excel payload body so duplicate non-consumable items are aggregated by account/name before writing the report body.
  - Example: `CAD PC 1EA` + `CAD PC 1EA` now becomes `CAD PC 2EA`.
  - Consumables still collapse to the most expensive consumable item plus `외 N건`.
- Verified:
  - `py_compile` passed for `web_v1/backend/output_set.py`.
  - Runtime sample produced the expected aggregated body text.

## 2026-05-13 WEB v1.0 fix90 expense report Excel failure fallback

- User reported that `현금결의서 생성` still shows a failure popup even though the document-set card can show an expense report path.
- Root cause: when an Excel template exists, the active generator only accepted Excel COM PDF export as success. If Excel COM failed with `-2147221005`, the API raised an error instead of using the existing WEB PDF fallback.
- Changed both expense report generator paths so Excel export failure falls back to the WEB PDF generator and returns success when a valid PDF is created.
- Verified:
  - `py_compile` passed for `web_v1/backend/output_set.py` and `web_v1/backend/app.py`.
  - Forced Excel-export failure test generated `C:\ERP_DB\expense_reports\999001\04_현금출금결의서.pdf`; the temporary test folder was removed.

## 2026-05-13 WEB v1.0 fix89 expense template roaming gate

- User clarified that the cash withdrawal/expense Excel template must live directly under the Windows Roaming profile, e.g. `%APPDATA%\양식_현금출금정산서.xlsx`.
- Changed 담당자 PC Agent preflight so login/setup installs the template to the Roaming root when it is missing and leaves the existing file untouched when present.
- Added fallback detection for Roaming, LocalAppData, and LocalLow locations, but the primary path shown by setup is now the Roaming root file.
- Adjusted output-set expense generation to prefer the same Roaming-root template before falling back to bundled/server templates.
- Fixed bundle hashing scope: only WEB/Agent/backend/deploy code files are hashed; support Excel templates are not hashed, so changing the Excel template does not trigger an Agent version mismatch.
- Bumped WEB/Agent version to `1.0.84`.

## 2026-05-13 WEB v1.0 fix87 manual upload menu

- User reported that the purchase detail screen is getting cluttered because `전표 첨부`, `품의 첨부/교체`, and `견적서 첨부` appear as separate buttons.
- Replaced the visible attachment buttons with one `자료 수동업로드` button.
- Added an in-page upload chooser with five document types:
  - `세금계산서`
  - `견적서`
  - `전표`
  - `전자결재 품의`
  - `현금출금결의서`
- Kept the existing upload flows for quote, voucher, and approval, but moved them behind the chooser.
- Added manual upload endpoints for:
  - `POST /api/invoices/{id}/tax-invoice`
  - `POST /api/invoices/{id}/expense-report-file`
- Added `update_invoice_pdf_path()` so a manually replaced tax invoice updates both the DB column and JSON payload.
- Verified:
  - `node --check web_v1\frontend\app.js` passed.
  - `py_compile` passed for `web_v1/backend/app.py` and `web_v1/backend/invoice_db.py`.
- Deployment note: server/frontend hotfix. Current WEB/Agent version remains `1.0.81`.

## 2026-05-13 WEB v1.0 fix84 output-set cleanup and expense fallback

- User reported:
  - cash withdrawal/expense report generation fails with Excel COM error `-2147221005`;
  - approval replacement/attachment sends completed rows back to waiting;
  - the purchase screen is too noisy for 담당자 users because logs and admin buttons are always visible.
- Fixed approval manual upload:
  - removed the `reset_invoice()` call from `POST /api/invoices/{id}/approval`;
  - removed the approval upload side effect that rewrote `erp_ready`;
  - approval replacement now updates document paths/status without changing the invoice processing status.
- Fixed cash withdrawal/expense report generation:
  - Excel-template export is still tried first;
  - if Excel COM is missing/broken, WEB now generates a fallback PDF directly with PyMuPDF using the same CS-style payload;
  - if the Excel template file is missing, the same fallback PDF is generated instead of failing.
- Cleaned the purchase screen:
  - default mode is now 담당자 mode;
  - logs, server diagnostics, delete/demo/admin output controls, and recent-job tables are hidden by default;
  - `상세모드` toggles the full admin/diagnostic view on and `담당자모드` returns to the clean screen;
  - job progress and stage strip remain visible in 담당자 mode.
- Verified:
  - `node --check web_v1\frontend\app.js` passed.
  - `py_compile` passed for `web_v1/backend/app.py`, `web_v1/backend/output_set.py`, and `web_v1/backend/worker.py`.
  - Direct fallback PDF generation test succeeded with a small PDF.
- Deployment ZIP: `C:\Tmp\accounting_web_v1_clean_output_expense_fix84_20260513_142000.zip`.
- Deployment note: server/frontend hotfix. Current WEB/Agent version remains `1.0.81`.

## 2026-05-13 WEB v1.0 fix83 manual approval replacement and expense report restore

- User requested two output-set fixes:
  - allow manually replacing a wrong/missing approval document;
  - restore cash withdrawal/expense report generation from the older CS workflow.
- Restored the missing active `web_v1/frontend` directory from the latest fix81 deployment bundle, then reapplied the new UI changes on top.
- Added a purchase detail `품의 첨부/교체` file button.
  - `POST /api/invoices/{id}/approval` now accepts `replace=true`.
  - When replacing, existing approval PDFs for the invoice are removed, DB approval paths are reset, and the output-set status is refreshed immediately.
- Added `POST /api/invoices/{id}/expense-report`.
  - It regenerates the cash withdrawal/expense report PDF with `force=True`.
  - Failure is stored in the invoice log and reflected in the output-set document status.
- Restored the CS-style cash withdrawal report payload in `web_v1/backend/output_set.py`.
  - Non-consumable accounts are listed item by item.
  - Consumables collapse to the most expensive consumable plus `외 N건`, with the group total.
  - The Excel template is exported to PDF and saved under `C:\ERP_DB\expense_reports\{invoice_id}`.
- Added a document-set button to trigger cash withdrawal/expense report generation from the web detail screen.
- Verified:
  - `node --check web_v1\frontend\app.js` passed.
  - `py_compile` passed for `web_v1/backend/app.py`, `web_v1/backend/output_set.py`, and `web_v1/backend/worker.py`.
- Deployment ZIP: `C:\Tmp\accounting_web_v1_manual_approval_expense_fix83_20260513_133809.zip`.
- Deployment note: server/frontend hotfix. Current WEB/Agent version remains `1.0.81`.

## 2026-05-13 WEB v1.0 server hotfix purchase slip summary label

- User reported that purchase ERP rows correctly group multiple consumables as `대표품목 외 N건`, but VAT/payable rows still concatenate every item name with commas.
- Fixed `web_v1/backend/erp_runner.py` purchase summary generation.
  - Non-consumable purchase items such as `집기비품` and `컴퓨터소프트웨어` remain visible by item name in VAT/payable summaries.
  - Only `소모품비` items are collapsed to the most expensive consumable item plus `외 N건`.
  - Example verified:
    - Only consumables: `싱글 광점퍼코드 10M 외 3건`
    - Mixed assets/consumables: `CAD PC, 모니터, 마우스 외 1건`
- Verified:
  - `py_compile` passed for `web_v1/backend/erp_runner.py`.
  - Runtime sample confirmed the final `부가세대급금` and `가지급금(업체)` rows now use the corrected summary label.
- Built deployment ZIP: `C:\Tmp\accounting_web_v1_purchase_summary_fix82_latest.zip`.
- Deployment note: server-side hotfix only. 담당자 PC Agent refresh is not required.

## 2026-05-13 WEB v1.0 fix81 ERP management-item speed

- User reported ERP management-item entry is still slower than manual input.
- Optimized the 담당자 PC ERP manager automation path for the bottom management fields only.
  - Set `pyautogui.PAUSE` to a low explicit value during fast ERP input so every click/key command no longer carries PyAutoGUI's default delay.
  - Added `ERP_FAST_MANAGEMENT` defaults with shorter but non-zero waits for management-field focus, clipboard, click, and commit timing.
  - Kept small post-paste/commit waits to reduce the previous missing-value risk for vendor/date/business fields.
  - Avoided repeated clipboard writes when consecutive management values are identical.
  - Made modifier-key release skip extra sleeps in the management path while retaining the existing safer behavior elsewhere.
- Bumped WEB/Agent bundle version to `1.0.81`, because the 담당자 PC manager automation file changed again.
- Verified:
  - `py_compile` passed for manager v6.2, `web_v1/backend/app.py`, `web_v1/backend/erp_runner.py`, and `web_v1/agent/erp_agent.py`.
  - User-PC payload ZIP check confirmed it contains `payload/manager_server/전표 자동화 프로그램(담당자용)_v6.2.py` and `VERSION=1.0.81`.
- Built deployment ZIP: `C:\Tmp\accounting_web_v1_mgmt_speed_fix81_latest.zip`.

## 2026-05-13 WEB v1.0 fix80 ERP voucher PDF Save As hotkeys

- User reported the ERP voucher PDF Save As dialog still did not respond after fix79.
- Added a keyboard-first save routine for the Windows common PDF Save As dialog.
  - Sequence: `Alt+D` -> paste target folder -> `Enter` -> `Alt+N` -> paste filename -> `Alt+S`.
  - This runs before UIA/Edit-control manipulation, so file-dialog controls that ignore pywinauto clicks can still be handled.
  - If the hotkey route does not create the PDF, the older Edit-control fallback still runs.
- Bumped WEB/Agent bundle version to `1.0.80`, because the 담당자 PC manager automation file changed again.
- Verified:
  - `py_compile` passed for manager v6.2, `web_v1/backend/app.py`, `web_v1/backend/erp_runner.py`, and `web_v1/agent/erp_agent.py`.
  - User-PC payload ZIP check confirmed it contains `payload/manager_server/전표 자동화 프로그램(담당자용)_v6.2.py` and `VERSION=1.0.80`.
- Built deployment ZIP: `C:\Tmp\accounting_web_v1_pdf_save_hotkeys_fix80_latest.zip`.

## 2026-05-13 WEB v1.0 fix79 ERP voucher PDF Save As dialog

- Fixed ERP voucher PDF saving when Windows opens the Save As dialog titled `다음 이름으로 프린터 출력 저장`.
  - The legacy v6.2 print helper now detects broader PDF save dialog titles: English `Save Print Output As`, Korean print-output save titles, and generic dialogs containing file-name/save/PDF controls.
  - The save path is pasted through the clipboard into the filename field instead of being typed key-by-key, which is more reliable for Windows common file dialogs and document-centralized locations.
  - The helper now clicks `저장`/`Save` or falls back to Enter, then records `last_erp_print_output` only after the expected PDF file exists.
- Fixed the 담당자 PC installer payload to include the actual resolved legacy manager file.
  - Previously the payload builder could point at a mojibake v6.2 filename and omit the patched manager file from 담당자 PC updates.
  - The payload now uses `settings.legacy_manager_path`, which already falls back to the real Korean filename.
- Bumped WEB/Agent bundle version to `1.0.79` so setup gate forces 담당자 PC Agent refresh for this manager-side automation fix.
- Verified:
  - `py_compile` passed for manager v6.2, `web_v1/backend/app.py`, `web_v1/backend/erp_runner.py`, and `web_v1/agent/erp_agent.py`.
  - User-PC payload ZIP check confirmed it contains `payload/manager_server/전표 자동화 프로그램(담당자용)_v6.2.py` and `VERSION=1.0.79`.
- Built deployment ZIP: `C:\Tmp\accounting_web_v1_pdf_save_dialog_fix79_latest.zip`.

## 2026-05-13 WEB v1.0 fix78 CAD PC account and approval legacy path

- Fixed purchase item classification for the proper-name item `CAD PC`.
  - `CAD PC` now wins over the generic `CAD` software keyword.
  - Analyzer, display normalization, manual analysis save, and dictionary learning all force `CAD PC` to `집기비품`.
  - This prevents edited/saved purchase analysis from learning `CAD PC` as `컴퓨터소프트웨어`.
- Hardened the approval-document background fetch legacy path.
  - If `LEGACY_MANAGER_PATH` points to a missing or mojibake filename, WEB now falls back to the real Korean v6.2 manager file under `manager_server`.
  - Runtime check resolved: `manager_server\전표 자동화 프로그램(담당자용)_v6.2.py`.
- Verified:
  - `py_compile` passed for `web_v1/backend/purchase_analysis.py`, `web_v1/backend/config.py`, `web_v1/backend/app.py`, `web_v1/backend/invoice_db.py`.
  - Runtime check confirmed `CAD PC -> 집기비품`.
  - Runtime check confirmed `settings.legacy_manager_path.exists() == True`.
- Built deployment ZIP: `C:\Tmp\accounting_web_v1_cadpc_approval_path_fix78_latest.zip`.
- Deployment note: this is a server-side hotfix; 담당자 PC Agent code/version was not changed.

## 2026-05-13 WEB v1.0 fix77 ERP voucher server upload

- User clarified that ERP voucher saving must be automatic after ERP input, not a manual later attachment step.
- Fixed the WEB ERP flow so the user-PC Agent uploads the generated ERP voucher PDF to the operating server immediately after K-System voucher PDF save succeeds.
- Added server endpoint `POST /api/agent/jobs/{job_id}/voucher`.
  - Stores uploaded voucher PDFs at `C:\ERP_DB\erp_vouchers\{invoice_id}\01_전표.pdf`.
  - Updates invoice JSON fields: `erp_pdf_path`, `erp_voucher_pdf_path`, `voucher_pdf_path`, `erp_pdf_local_path`, upload agent/job/time metadata.
  - Rebuilds/persists `output_docs`, so `GET /api/invoices/{id}/output-set` can detect the voucher without manual upload.
- Updated Agent `web_v1/agent/erp_agent.py`.
  - Agent bundle version is now `1.0.77`.
  - After `run_invoice_erp_input()` returns a local `erp_pdf_path`, Agent uploads the file to the server and changes the result path to the server path.
  - If upload fails, the job logs the local path and upload error instead of silently marking the server-side voucher as present.
- Hardened `web_v1/backend/erp_runner.py`.
  - The ERP print target path is still generated automatically under `C:\ERP_DB\erp_outputs`.
  - The runner now fails visibly if the expected PDF file does not exist after printing, instead of returning a ghost path.
- Hardened legacy manager v6.2 PDF Save As helper.
  - Rejects empty save paths.
  - Deletes an old same-name PDF before printing so the automation must create a fresh file.
- Version/cache updated to `1.0.77` / `fix77_agent_voucher_upload`.
- Verified with `py_compile` for `web_v1/backend/app.py`, `web_v1/backend/erp_runner.py`, `web_v1/agent/erp_agent.py`, and `manager_server/전표 자동화 프로그램(담당자용)_v6.2.py`.
- Built deployment ZIP: `C:\Tmp\accounting_web_v1_agent_voucher_upload_fix77_latest.zip`.
- Important deployment note: this fix requires both operating-server update and 담당자 PC Agent update, because the upload logic lives in the Agent.

## 2026-05-08

- Advanced the WEB v1.0 purchase workflow from mail collection into an operator-facing queue.
- Added invoice DB status/log support: `last_error`, `erp_job_id`, and `invoice_logs` are initialized/migrated automatically.
- Added purchase invoice APIs: detail lookup, per-invoice logs, retry/reset, delete, and `POST /api/jobs/purchase-erp-input`.
- Added `web_v1/backend/erp_queue.py`; selected purchase invoices now create `C:\ERP_DB\erp_queue\purchase_erp_<job_id>.json` and move to the ERP queued state.
- Rebuilt the purchase screen with selectable rows, ERP queue registration, retry, delete, invoice log viewing, job log viewing, and static asset cache busting.
- Verified backend syntax with `py_compile`, frontend syntax with `node --check`, FastAPI route registration, and a temp-DB smoke test for invoice insert/list/log/reset/ERP queue-file creation.
- Fix2 after operating-server feedback: purchase mail collection now forces crawler results to `invoice_type=purchase`, duplicate existing PDFs are reclassified to purchase, the frontend invoice list no longer hides existing regular-classified rows, and recent job log viewing scrolls the current-job log panel into view.
- Fix3: added purchase-list status filters and stronger status coloring for waiting/processing/ERP queued/done/error rows. ERP queue completion logs now explicitly say that the queue file is created but the real ERP input engine is still the next connection step.
- Fix4: added a purchase-list page-size selector so operators can show 20/50/100/200 rows at a time. Selection and select-all now operate only on the currently visible filtered rows.
- Fix5: made the server status summary and current-job log collapsible and hidden by default. Manual toggles can open/close them, and loading a recent job log automatically opens the current-job log panel.
- Fix6: connected WEB v1.0 ERP execution to the legacy v6.2 K-System automation path. Selected rows still write an ERP queue JSON, then the worker builds ERP clipboard rows, loads the legacy `ERPLoginBot`, runs K-System input, saves voucher output through the configured print target, and updates invoice statuses to `처리완료` or `오류`.
- Fix7: ERP execution import now stubs the legacy module's top-level `fitz` import when PyMuPDF DLL loading fails, because WEB ERP input does not use that PDF path. This avoids `_extra` DLL failures before K-System automation starts.
- Fix8: ERP execution now resolves the legacy K-System `config.ini` from `manager_server` first and falls back to `support/config.ini`. It validates `INSTALL_* exe_path` and `CORP_*` credentials before launching, so missing config now reports the exact file/section/key instead of a blank `실행 파일이 없습니다` message.
- Fix9: corrected the WEB purchase/regular split and ERP safety checks. Mail collection no longer forces every crawler result into the purchase screen, known regular vendors are repaired out of purchase, the purchase table fetches only `mode=purchase`, purchase ERP execution skips non-purchase invoices, purchase ERP rows follow the manager v6.2 purchase `copy_erp()` shape with `가지급금(업체)`, and K-System navigation verifies the `분개전표입력` form actually opened before form input.
- Fix10: blocked unsafe WEB purchase ERP execution when only the tax invoice exists. Purchase ERP now requires quote/approval or analysis-ready metadata, a concrete mapped site such as `D1공장`/`P1공장`/`일강1공장`, and a positive supply amount before any queue/run step can launch K-System. This prevents Compuzone tax-only rows from being entered as incomplete vouchers with corporation names in the accounting-unit fields.
- Fix11: added the first WEB purchase-detail workflow. Operators can select one purchase invoice, upload a quote PDF, run tax-invoice/quote analysis, edit site/vendor/date/amount/item/account/dept values, and save the analysis back into the invoice JSON. Purchase ERP execution is now stricter: a quote alone is not enough, analysis items must exist, and the ERP button stays disabled until approval-document readiness is recorded.
- Fix12: aligned WEB purchase analysis with the existing manager/server purchase logic. Quote parsing now filters shipping/delivery/discount rows, runs the learned item dictionary matcher, forces monitor-arm rows back to `소모품비`, strips vendor corporation suffixes for ERP summaries, fixes non-asset dept to `소모품`, and lets operators attach approval PDFs so ERP readiness is explicit before K-System input.
- Fix13: stopped unconditional Gemini calls in WEB purchase analysis. The analyzer now uses learned dictionary/fast parsing first and calls AI only when unknown quote items remain. Saving edited purchase analysis writes item mappings back to the `dictionary` table so later Compuzone-style quotes reuse prior learning instead of spending another AI request.
- Fix14: moved WEB purchase analysis into the job queue/SSE progress path so the top current-work panel shows analysis, learned/AI decision, DB save, and approval-document fetch progress. The analysis job now reuses the 담당자용 approval helper to fetch 품의결재본 automatically from the quote order number; the manual approval upload button was removed from the normal UI.
- Fix15: fixed purchase accounting-date extraction so tax-invoice filenames and explicit invoice-date labels are preferred over unrelated certificate/legal dates inside the PDF body. Added a greenlet/Playwright runtime preflight for approval fetches and updated the operating-server install script to force-reinstall `greenlet`/`playwright` before installing Chromium.
- Fix16: fixed WEB purchase readiness calculation. The invoice list and detail view now merge top-level JSON, nested `data`, and list-row fields before deciding whether a quote, analysis, or approval document is missing, so a purchase row with an attached/analyzed quote no longer reports `견적서 필요` from stale nested fields.
- Fix17: corrected the purchase ERP gate to match the CS 담당자용 flow. ERP input is enabled after quote attachment and item analysis; 품의결재본 is no longer a blocking condition and is fetched in a separate background thread after analysis so approval retrieval and ERP input can proceed concurrently.
- Fix18: fixed stale purchase-detail rendering after background analysis jobs. The frontend now forces a fresh `/api/invoices/{id}` reload after job completion so corrected fields such as accounting date replace old form values, and the backend guards purchase-analysis saves from re-saving invalid old dates like `2002-02-06` when the tax-invoice filename contains the real issue date.
- Fix19: disabled PyAutoGUI fail-safe just before WEB ERP automation calls the legacy v6.2 `ERPLoginBot`. Operating-server/RDP sessions can park the mouse on a screen corner and abort every coordinate input, so WEB v1.0 now forces the shared `pyautogui.FAILSAFE` flag off for K-System input.
- Fix20: hardened the legacy v6.2 K-System form automation for WEB ERP execution. 회계단위 now opens the real UIA ComboBox/ListItem dropdown, verifies the selected site, verifies 전표관리단위 and 회계일 before grid paste, and stops the WEB job as `error` with UI dump/screenshot diagnostics instead of logging a false ERP completion.
- Fix21: corrected the K-System form coordinates after operating-server visual feedback. 전표관리단위, 회계일, and the first 계정과목 grid cell now click the actual input cells instead of their labels/header area before typing or pasting.
- Fix22: started ERP form stabilization away from hardcoded coordinates. 전표관리단위 and 회계일 are now found by label-to-right-input anchoring, 행추가 prefers the real button, and grid paste clicks the first data cell under the `계정과목` header before falling back to coordinates.
- Fix23: fixed a false-negative ERP form verification bug. K-System UIA can report the same date value through multiple getters, so form value reads are now de-duplicated and date verification accepts the expected date inside the normalized actual text instead of requiring exact string equality.
- Fix24: hardened and sped up WEB purchase ERP form input. 상단 전표관리단위/회계일 now use the fast verified coordinate path instead of repeated full UIA label scans, the always-on pre-form UI dump is disabled unless `ERP_FORM_DEBUG_DUMP=1`, waits were shortened, and the first grid paste clicks the verified `계정과목` header + `001` row intersection so it cannot drift into the right-side `부가세행추가` button.
- Fix25: started the user-PC ERP Agent architecture. `ERP_EXECUTION_MODE=agent` is now the default, purchase ERP jobs create a server-side Agent queue instead of launching K-System on the WEB server, and new Agent APIs let a 담당자 PC claim ERP work, stream logs back to the WEB progress panel, and complete/fail the job. Added `web_v1/agent/erp_agent.py` with package/config.ini/K-System install checks plus monitor resolution/DPI checks before it runs the existing v6.2 ERP automation locally.
- Fix26: repackaged the user-PC ERP Agent patch for server deployment and made the Agent stop with a clear "server is not updated" message when `/api/agent/erp/next` returns 404, instead of polling forever against a 구버전 WEB server.

- Fix27: fixed FastAPI startup on the Agent polling route by disabling response-model generation for `/api/agent/erp/next`. The route may return either `204 No Content` or a task JSON, which must not be interpreted as a Pydantic response model.
- Fix28: fixed user-PC Agent ERP form drift after real 1920x1080 feedback. Agent mode now fresh-starts K-System by closing stale ERP processes before launch, 전표관리단위/회계일 use label-anchored controls before coordinate fallback, stale ERP queue files are skipped when invoices are no longer `ERP대기`, and HTTPS warning spam is suppressed in the Agent log.
- Fix29: corrected K-System row-add detection so `부가세행추가` is never accepted as the normal `행추가` button. Both the WEB coordinate form path and the legacy fallback now require an exact `행추가` match or the real add-row automation id, and stale UIA generator warnings were removed by materializing visible controls before selection.
- Fix30: tightened Agent queue claiming so old or duplicate queue files do not run just because the 담당자 PC Agent was started. New ERP queue files now include `created_at`; legacy queue files without it are marked stale, and an invoice is claimable only when its current `erp_job_id` matches the queue file's `job_id`.
- Fix31: corrected the user-PC Agent 1920x1080 100% ERP coordinates after live P3 feedback. The top form fields now use coordinate-first entry for speed, 전표관리단위 uses `(692,124)`, 회계일 uses `(375,149)`, and the grid paste starts at the real first `계정과목` cell `(398,231)` instead of the old 125%/safe fallback coordinates.
- Fix32: added the missing management-item rule for `집기비품` on `대승정밀` sites such as `P3공장`, so the purchase ERP Agent now enters the `거래처` management value before saving and printing.
- Fix33: sped up user-PC Agent ERP entry by throttling high-volume progress posts, suppressing default key-safe/management-clear chatter, skipping already-stable coordinate field verification in fast mode, and using the known `행추가` coordinate before UIA button scans.

## 2026-05-07

- WEB v1.0 SmartBill crawler verified on the operating server with `SMARTBILL_FORM_POST_PRINT_V4`.
- Root cause: SmartBill print is not a plain URL open. The real page has `ibtnPrint` calling `fnPrint()`, which sets `document.forms[0].hdnCheckedIds` to `dtiid;dtiWday;status;dtiType;arap;dtiDocType;BrkDtiYn;`, opens the `DTIPrint` popup target, and posts the current form to `/xDTI/arap_repo/common/prt_prev.aspx`.
- Updated `tax_crawler/portal_smartbill.py` so `_save_pdf` preserves that form POST behavior. It first tries the real `ibtnPrint` click and falls back to an exact JavaScript form POST that reproduces `fnPrint()`.
- Important: do not replace this with direct `dti_prev.aspx` navigation or a plain GET to `prt_prev.aspx`; those were the failing paths.
- Created hotfix `C:\Tmp\smartbill_form_post_v4_hotfix.zip`.
- Created working backup `C:\Tmp\accounting_web_v1_working_smartbill_v4_20260507_171727.zip`.
- Next WEB v1.0 focus: finish purchase collection result persistence/list refresh, then connect selected purchase invoices to the ERP input job queue.

## 2026-05-06

- Fixed SmartBill WEB v1.0 crawler print-preview handling. When the first print action does not produce a Selenium-visible new window, the handler opens `/xDti/n_mem/dti_prev.aspx?Caller=N_MEM_02` in the same authenticated session, scrolls to the bottom of that real SmartBill preview page, clicks the actual `인쇄` button while excluding `스마트인쇄`/XML/list buttons, and then saves the print preview PDF.
- Reset `tax_crawler/portal_smartbill.py` from the known working reference at `C:\Tmp\portal_smartbill.py`, then added only the SmartBill preview fallback/print-button flow on top of that reference so the existing approval, parsing, and PDF repair logic remains unchanged.
- Updated SmartBill again to skip the original invoice-page `인쇄` button entirely because it can raise the certificate toolkit installation alert. The handler now goes directly to `dti_prev.aspx?Caller=N_MEM_02`, then clicks that preview page's bottom `인쇄` button.
- Added the first real WEB v1.0 purchase-mail job path. The dashboard now has a `구매 메일 수집` button that queues `purchase_mail_collect`, checks Gmail once on the operating server, runs the existing tax crawler targets, saves new invoices to `C:\ERP_DB\learned_data.db`, and refreshes the purchase invoice table.
- Added `web_v1/backend/mail_collector.py` and `web_v1/backend/invoice_db.py` so the WEB backend can reuse the existing `tax_crawler` modules without starting the old CS Flask server.
- Added `POST /api/jobs/purchase-mail-collect` and `GET /api/invoices?mode=purchase`.
- Verified frontend JavaScript with `node --check`, backend syntax with `py_compile`, and FastAPI route registration for `/api/jobs/purchase-mail-collect` and `/api/invoices`.
- Added the first WEB v1.0 FastAPI backend skeleton under `web_v1/backend`.
- Implemented in-memory job registration, a single background worker, progress events, job status APIs, and an SSE progress stream.
- Added backend requirements and a PowerShell run script.
- Verified backend syntax, app import, `/health`, `/api/jobs/demo`, and the demo job progressing to `done`.
- Added operating-server copy/paste deployment scripts under `web_v1/deploy`.
- Clarified operating-server deploy docs to unzip the project into `C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version` and run deploy scripts by absolute path.
- Updated the operating-server installer to write the known mail account and Gemini API key into `.env` without prompting; printer names are auto-detected when possible and only requested if detection fails.
- Added the first WEB v1.0 frontend screen served directly by FastAPI at `/`, with a progress bar, stage strip, log panel, recent jobs table, and Browser Notification permission flow.
- Improved the frontend notification state so remote HTTP access shows `HTTPS 필요` instead of a misleading blocked state when Browser Notification permission cannot be requested.
- Added an immediate test notification after the user grants browser notification permission.
- Added `enable_http_notification_policy.ps1` to allow the internal HTTP origin `http://172.17.39.121:8080` to be treated as secure by Chrome/Edge for notification testing.
- Switched WEB v1.0 operating-server default access to HTTPS at `https://172.17.39.121:8080`, added certificate generation/trust scripts, and wired Uvicorn SSL certificate settings through `.env`.
- Changed browser notifications to prefer Service Worker `showNotification()` and strengthened the certificate trust script to try both CurrentUser and LocalMachine Root stores.
- Quieted expected browser disconnects from the SSE progress stream and switched the Windows backend runner to `WindowsSelectorEventLoopPolicy` to avoid noisy `WinError 10054` Proactor callback tracebacks.
- Reset active product naming to `회계업무 자동화 WEB v1.0`.
- Added `web_v1` as the new active WEB development root with backend/frontend/docs placeholders and v1.0 environment template.
- Clarified that existing `manager_server` 담당자용 v6.2 / 서버용 v3.2 files are CS reference sources, not the WEB product version.
- Removed the hardcoded Gemini API key from `manager_server/전표 자동화 프로그램(서버용)_v3.2.py`.
- Server v3.2 now reads `GEMINI_API_KEY` from the process environment and returns HTTP 503 from `/api/analyze_ai` when the key is not configured.
- Verified the updated server file with `py_compile`.

## 2026-04-30

- Diagnosed the copied server `C:\ERP_DB` state. CSBill was updating the existing `CSBill_202640254004.xml` filename, but the handler only detected newly named XML files; fallback clicks then navigated to the CSBill invalid-info page before PDF rendering.
- Updated `portal_csbill.py` to detect changed existing XML files by mtime/size, execute CSBill XML save scripts in the default page and invoice frames, and render the actual `fraView` invoice URL directly to PDF instead of depending on a fragile print form on the parent page.
- Fixed KT parsed payload quality in `portal_kt.py`: KT items now prefer actual service lines such as `biz Managed 보안` instead of subject tokens or invoice numbers, and KT crawler items now return `통신비`.
- Hardened manager v6.2 purchase approval lookup so Compuzone quote PDFs only accept the 8 digits immediately after the `견적번호` label inside the PDF; filename `(########)` remains only as a last-resort fallback.
- Fixed manager v6.2 purchase dashboard display numbers to show row order instead of DB ids while keeping the real invoice id in the tree item id for lock/complete API calls.
- Updated manager v6.2 ERP management fields for Ilgang VAT rows to enter 거래처, 공급가액, 거래일, 사업자번호 in the requested order, and to select the 3rd duplicate KT vendor row for Ilgang KT vendor lookups.
- Corrected manager v6.2 Compuzone purchase ERP summaries: monitor-arm items are forced to `소모품비`, while VAT and `가지급금(업체)` summaries now aggregate all purchase item names such as `터치모니터, 모니터암` instead of reusing the last consumable item.
- Updated manager v6.2 KT vendor management selection: VAT/payable vendor fields now search with `케이티` and select the result row whose business number is `102-81-42945`, shared across corporations.
- Fixed KT PDF handling direction: `portal_kt.py` now tries PyMuPDF decrypted PDF save first so the original text layer is preserved; image-rendered PDF is only a fallback. KT parsing also explicitly prefers `명세서 작성일자`.
- Verified the provided encrypted KT original `2026년 4월 KT email 명세서... (3).pdf`: password `51622` opens it, decrypted PDF text length is nonzero, parsed issue/accounting date is `2026-04-06`, and item is `biz Managed 보안`.
- Updated manager v6.2 ERP setup so `미지급금(원화)` no longer turns off `출납처리여부`; the ERP default checked state is left intact. If no invoice date can be recovered, today's-date fallback is blocked instead of silently entering the current date.
- Verified syntax with `py_compile` for `portal_csbill.py`, `portal_kt.py`, and manager `전표 자동화 프로그램(담당자용)_v6.2.py`.

## 2026-04-29

- Updated 담당자용 v6.2 regular-accounting payload resolution so the buyer business number is preferred over guessed company/site strings. If crawler data lacks `buyer_biz_no`, the client parses the attached tax-invoice PDF text, matches the first known buyer business number through `FACTORY_MAP`, and uses that site for ERP 회계단위/전표관리단위. Verified `125-81-05619` maps to `D1공장` and rebuilt the 담당자용 v6.2 exe.
- Fixed regular-accounting slip dates in 담당자용 v6.2. The client now prefers the tax-invoice issue/write date from crawler data, nested XML parse data, or the downloaded PDF text (`작성일자`/approval-number date) instead of falling back to today's date. Verified a HomeTax PDF with `작성일자 2026/04/25` resolves to `2026-04-25`.
- Updated 담당자용 v6.2 ERP voucher printing cleanup: after RD Viewer printing/PDF saving finishes, the automation now closes `Report Designer Viewer` windows and terminates leftover `rdviewer_u.exe` processes if needed. Rebuilt the 담당자용 v6.2 exe successfully.
- Corrected the WEHAGO/Duzon print-preview PDF-button fallback in `portal_wehago.py`. UIA is still attempted first, but when the custom-drawn PDF button is not exposed as a control, the fallback now clicks the actual dialog-relative PDF button area seen in the server preview instead of the old upper-left coordinates.
- Fixed the WEHAGO Microsoft Print to PDF Save As flow. The Korean dialog can treat `Alt+N` as the New Folder command in some server sessions, so `_save_pdf_dialog()` now focuses the lower filename edit and pastes the full target path at once before pressing Enter.
- Reworked the WEHAGO Save As flow to use the requested keyboard sequence: `Alt+D` for the folder path, Enter, then `Alt+N` for the file name, Enter. Also fixed `_paste_text()` so it only pastes text; its misplaced dialog-close/Alt+F4 fallback was moved into `_close_print_dialog()`, which now closes the Duzon/WEHAGO print preview after a successful PDF save.
- Changed WEHAGO Save As handling again to avoid file-dialog clicks and `Alt+N` entirely because the server dialog can interpret `Alt+N` as the New Folder command. The handler now sets the lower filename `Edit` control directly to the full target path, then presses Enter, with misplaced-file recovery still active.
- Fixed WEHAGO/Duzon print-preview cleanup so `_export_pdf_from_print_dialog()` always closes the preview in a `finally` block, even when PDF saving fails. It also sweeps remaining `인쇄 기본 설정 / 미리보기`, `Duzon Print`, `WehagoPrint`, and `TX2A.drf` windows after the primary close attempt.
- Tightened WEHAGO mail-link extraction in `crawler_main.py`: only `https://www.wehago.com/invoice/` URLs are accepted for WEHAGO, so CDN/static image URLs such as `static.wehago.com/imgs/...png&quot` are ignored.
- Added the missing `email.message` import needed for direct `crawler_main.py` import with evaluated type annotations.
- Verified `extract_links_from_mail()` keeps the WEHAGO invoice URL and CSBill URL while dropping the WEHAGO static image URL.
- Re-ran `graphify update .` after the code change.
- Diagnosed the HomeTax debug dump `260428_20260429_081014`: authentication and PDF rendering succeeded, but `CriDownFile(0)` Blob download did not create an XML file in the server Chrome download directory.
- Updated `portal_hometax.py` to call HomeTax's in-page `CriGetFileName(0)`/`CriGetFileData(0)` directly and write the decrypted base64 XML from Python before falling back to Blob download attempts.
- Verified the failing WEHAGO URL decodes to `TX2026047916179&1258105619`; updated `portal_wehago.py` to require `https://www.wehago.com/invoice/` support and accept authentication success when the invoice action buttons become visible, not only when the text-input count shrinks.
- Updated `base_handler.py` to use a persistent crawler Chrome profile at `C:\ERP_DB\chrome_profile` (configurable as `PATH.chrome_profile_dir`) so server-only WEHAGO external-app permission choices can persist instead of re-prompting every run.
- Improved WEHAGO permission fallback in `portal_wehago.py` to click the actual Chrome permission bubble allow button area after the print action, while keeping UI Automation button search as the first attempt.
- Fixed WEHAGO print export flow: after selecting the `PDF` output button in the Duzon/WEHAGO print preview app, the handler now clicks `인쇄하기` before waiting for the Save As dialog. The prior flow selected PDF but never started printing, causing `WEHAGO PDF 다운로드 실패`.

## 2026-04-28

- Installed and applied Graphify to the project.
- Generated `graphify-out/graph.json`, `graphify-out/graph.html`, and `graphify-out/GRAPH_REPORT.md`.
- Added Project Memory Lite files and cross-tool entry files (`CLAUDE.md`, `GEMINI.md`).
- Updated `AGENTS.md` so future agents read compact project memory first and update it only for durable changes.
- Captured user-provided project scope, sample URLs, KT password rules, and current unfinished refinement targets.
- Static syntax check passed for all Python modules with `py_compile`.
- Verified the four KT sample PDFs can be opened with the expected password candidates: Daeseung corporate `0003577`, Daeseung Precision P1 `32697`, Ilgang `51622`, and Daeseung Precision P4 `07029`.
- Excluded U+ from active automation: removed U+ from `crawler_main.py` auto-detection/handler routing and removed the U+ test menu entry while keeping `portal_uplus.py` as a legacy file.
- Backed up touched files to `세금계산서_크롤러_백업_20260428_130539_routing_kt` before code edits.
- Added AutoEver and KT to `crawler_main.py` active handler routing.
- Tightened HomeTax `supports()` so it only claims NTS/HomeTax HTML files and no longer catches arbitrary `file://` paths such as KT PDFs.
- Refactored KT to override `process()` and decrypt local PDFs without launching Chrome.
- Updated KT to skip `W00127***` as manual and to parse total payment/site names from sample PDFs more accurately.
- Verified routing: Unipost, WEHAGO, CSBill, AutoEver, KT PDF, and HomeTax HTML resolve to the expected handlers; U+ resolves to none.
- Verified all four KT sample PDFs process successfully in a temporary output directory; W00127 returns the manual-handling error.
- Changed common PDF filename generation to `세금계산서 - 업체명(시스템명)_법인명(사업자명)_현재월.pdf`.
- Added business/site-name resolution from `FACTORY_MAP` for XML-based buyer business numbers and explicit KT password-rule site names.
- Improved KT system-name parsing so sample files use representative product names like `new kt biz GiGAoffice Compact`, `biz Managed 보안`, and `인터넷 에센스` instead of `요금구성표`.
- Added filename period rules: Groupware/DaouOffice and NAC use issue-month, DLP maps issue date to 1st~4th quarter-like rounds, and KT/customer VPN/Watching-On/Acronis use the previous month. The item/product name is the primary classifier.
- Improved HomeTax parsing: after secure-mail authentication, the handler downloads the XML attachment, parses supplier/buyer/business number/issue date/item/supply/tax/total through `xml_parser.py`, then names the rendered PDF with the parsed buyer site.
- Verified the HomeTax sample saves a PDF as `주식회사 시큐어포인트(...NAC...)_(주)대승(D1공장)_2026년 04월.pdf` and returns total `1,039,390`, tax `94,490`, item `대승 Genian NAC 1Year 기술지원 4월분 [2/12]`.
- Improved CSBill parsing: after business-number authentication, the handler downloads the XML through CSBill's `/download.do` path and parses supplier/buyer/business number/issue date/item/supply/tax/total with `xml_parser.py` before rendering the print page PDF.
- Verified the CSBill sample URL saves `세금계산서 - (주)다우기술(그룹웨어 서비스 이용료)_(주)대승(D1공장)_2026년 04월.pdf` and returns total `3,542,000`, tax `322,000`, item `그룹웨어 서비스 이용료`.
- Improved WEHAGO parsing: XML-derived issue date, tax amount, buyer business number, and VAT-inclusive item amounts are now used in the final filename/result data.
- Adjusted WEHAGO Save As dialog input to paste Unicode path/file names through the clipboard instead of typing them key-by-key, so Korean paths and filenames are safer.
- Verified the WEHAGO sample URL authenticates and downloads XML. Parsed values are supplier `(주)에티버스`, buyer `(주)대승`, item `Watching-On 모니터링 서비스`, issue date `2026/04/10`, total `163,350`, and tax `14,850`.
- Improved AutoEver popup parsing by reading the rendered invoice table cells directly. Buyer business number is now passed to common filename generation so site names like `D1공장` are included.
- Verified the AutoEver sample URL with password `2026042098s6hv0m399p` saves `세금계산서 - 현대오토에버(주)((주)대승_평택_SDWAN)_(주)대승(D1공장)_2026년 03월.pdf` and returns total `148,830`, tax `13,530`, item `(주)대승_평택_SDWAN`.
- Improved KT parsing: tax-invoice summary rows inside the decrypted PDF are now parsed for issue date, supplier business number, buyer business number, supply amount, VAT, and approval number. Buyer business number now drives the factory/site label in filename, subject, and result data.
- Verified all four KT sample PDFs: P1 `603,220`/VAT `54,838`, Ilgang1 `1,878,800`/VAT `170,800`, P4 `2,511,300`/VAT `228,300`, and Daeseung D1 `2,427,940`/VAT `220,722`. `W00127***` remains manual-only.
- Updated the accounting manager app v6.2 electronic-approval/groupware helper to use the new dedicated approval account. Confirmed server v3.2 has no groupware access path. Rebuilt the manager v6.2 executable after the credential change.
- Tightened CSBill mail-link detection to accept only `https://www.csbill.co.kr/` URLs, ignore `mailer.csbill.co.kr` tracking links, and keep only the best URL per `mana_Bill_Numb` so duplicate CSBill links are not crawled one by one. Also narrowed the CSBill handler support check to the same `www.csbill.co.kr` prefix.
- Corrected the CSBill filter to keep all valid `https://www.csbill.co.kr/` invoice links instead of deduping a bill down to a single `loginSave.do` URL, because CSBill mail flows can require the preceding `mailReceive.do` visit. Added an invalid-page guard for the `정보가 올바르지 않습니다` response. Made KT load PyMuPDF lazily so a broken `fitz` DLL no longer disables the entire KT handler at import time.
- Updated CSBill mail-link extraction to canonicalize `loginSave.do`/`mailReceive.do` links into the actual invoice view URL: `https://www.csbill.co.kr/noRegIssueView.do?mode=view&mana_Bill_Numb=...&mail=...&listYn=N&supp_Mail=N`. The mail address keeps `@` unescaped to match the real opened URL. Updated KT to use `pypdfium2` as the primary path for encrypted PDF opening/text extraction and render the decrypted output as a normal image-backed PDF, avoiding PyMuPDF DLL failures on the server.

## 2026-05-13 WEB v1.0 현금출금결의서 양식 경로 보강
- `web_v1/backend/output_set.py` 현금출금결의서 Excel 양식 후보에 기존 CS 문서중앙화 경로 `Y:\관리총괄\경영지원본부\전산팀\2파트\2파트 개인 자료\김기창\현금출금결의서 양식\양식_현금출금정산서.xlsx`를 추가했다.
- 운영서버 안정 경로로 `C:\ERP_DB\templates\expense_template.xlsx`를 추가해, 담당자 PC에서 보이는 `Y:` 양식을 서버 로컬에 복사해 두면 WEB이 항상 같은 양식을 사용할 수 있게 했다.
- `Y:`가 서버 세션에 매핑되지 않거나 Excel COM 변환이 실패할 때 쓰는 WEB fallback PDF를 기존 임시 양식에서 CS 현금출금결의서(정산서) 형태에 가깝게 개선했다.
- `py_compile` 및 fallback PDF 생성(`C:\Tmp\expense_fallback_fix85_test.pdf`)을 확인했다.

## 2026-05-13 WEB v1.0 현금출금결의서 Excel 양식 내장/헬퍼 분리
- 사용자가 제공한 `양식_현금출금정산서.xlsx`를 분석했다. 시트는 `출력용`, 인쇄영역은 `A1:R42`, 기존 CS와 같은 셀 매핑(`D5/D6/G6/D7/D8/D9/C11/B19`)으로 값만 주입하면 되는 구조임을 확인했다.
- 제공받은 양식을 `support\expense_template.xlsx`로 포함해 서버 업데이트 ZIP만 적용해도 WEB이 동일 양식을 찾을 수 있게 했다.
- 문서중앙화 `Y:` 경로가 존재해도 읽기 권한이 막혀 `PermissionError`가 날 수 있어 `_is_readable_template()` 검사를 추가했다. 이제 읽을 수 없는 `Y:`는 건너뛰고 로컬/지원 폴더 템플릿으로 넘어간다.
- Excel COM PDF 변환을 `web_v1/backend/expense_excel_export.py` 별도 프로세스로 분리했다. 변환 제한시간은 기본 30초이며, 멈춘 Excel이 웹 요청을 붙잡지 않게 새 Excel 프로세스를 정리한다.
- 읽기 가능한 Excel 템플릿이 있는데 변환에 실패하면 더 이상 임시 WEB PDF를 몰래 생성하지 않고 명확한 실패로 표시한다.
- `output_set.py`, `expense_excel_export.py` 문법 검사를 통과했고, 짧은 timeout 검증에서 웹이 멈추지 않고 예상 실패를 반환하는 것을 확인했다.
 
## 2026-05-13 WEB v1.0 expense AppData template/workspace fix88
- 담당자 PC Agent 버전을 `1.0.82`로 올리고, preflight/heartbeat 때 `%APPDATA%\AccountingWeb\templates\expense_template.xlsx`가 없으면 `support\expense_template.xlsx`를 자동 배치하도록 추가했다. 이미 있으면 덮어쓰지 않는다.
- 필수환경 점검에 `현금출금결의서 Excel 양식` 항목을 추가해 Roaming 양식 경로 준비 상태를 웹에서 확인할 수 있게 했다.
- 현금출금결의서 Excel/PDF 변환은 Excel이 직접 쓰는 작업 파일을 `%APPDATA%\AccountingWeb\expense_reports\{invoice_id}` 아래에서 만들고, 생성된 PDF만 최종 `C:\ERP_DB\expense_reports\{invoice_id}`로 이동하도록 변경했다. Excel 보안정책은 `<APPDATA>`만 허용해도 된다.

## 2026-05-13 WEB v1.0 manual purchase upload fix91
- `POST /api/invoices/manual-purchase`를 추가해 메일 수집/크롤러를 타지 않고도 세금계산서 PDF와 견적서 PDF로 신규 구매 건을 만들 수 있게 했다.
- 수동 등록 시 세금계산서 PDF에서 작성일, 공급가액, 부가세, 합계, TaxNo 주문번호를 먼저 파싱하고, 견적서가 같이 올라오면 주문번호를 보강한 뒤 구매 분석을 자동 시도한다.
- 기존 `자료 수동업로드` 버튼은 선택 건이 없어도 열리며, 모달 상단에서 신규 구매자료 등록을 할 수 있고 하단은 선택된 기존 건의 자료 첨부/교체로 유지했다.
- 이번 작업 중 로컬 `web_v1/frontend`가 누락되어 fix88 ZIP에서 프론트 폴더를 복구한 뒤 변경했다.
