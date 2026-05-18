# Project Status

Updated: 2026-05-15

## How To Use This File

- Read this file before starting work.
- Update this file before ending a meaningful work session.
- This file must be enough to recover goals, decisions, changed files, remaining work, tests, deployment ZIP, and cautions after context compaction.
- When commands are requested, provide copy-pasteable command blocks without `1.`/`2.` prefixes inside the commands.

## Current Goal

WEB v1.0 accounting automation is replacing the old CS desktop accounting flow.
Purchase one-click processing, automatic mail collection, simplified manager UI, WEB regular-processing (`정기 처리`), and SMILE EDI regular invoice intake are implemented enough for source-level review and next operational E2E:

- SMILE EDI `DtiEmail.do` mail links are collected through the active crawler flow.
- SMILE EDI tries D1~D3 business numbers inferred from the mail buyer name, detects unapproved invoices, and approves only when explicitly requested during standalone manual testing.
- Approval cannot be reverted, so default crawler runs must be dry-run for approval.
- Multiple selected purchase invoices should run through one simple `one-click processing` flow.
- One-click should cover ERP input, ERP voucher PDF save/upload, cash withdrawal report creation, output-set refresh, and selected output target.
- Already completed purchase invoices with all required output documents must skip ERP/cash-report regeneration and print/save from stored documents.
- The manager default UI should stay simple; debug logs and individual analysis/output buttons should live in detail/admin mode.
- Mail collection should run automatically every minute while the operating server is running.
- E2E verify the new WEB regular-processing view and regular Agent ERP/output queue on a real manager PC.
- Continue referencing the legacy manager regular tab behavior from `manager_server/전표 자동화 프로그램(담당자용)_v6.2.py` for remaining parity gaps.

## Active Architecture Decisions

- ERP GUI automation must run on the manager PC Agent, not on the operating server.
- The operating server has no Excel installed. Excel COM/PDF export work must run on the manager PC Agent.
- Cash withdrawal/expense reports must use the prepared Excel template. Do not silently create arbitrary WEB-drawn fallback PDFs.
- Manager PC cash report template target is `%APPDATA%\양식_현금출금정산서.xlsx`; if it exists, leave it untouched.
- ERP voucher PDF saving should be automatic and uploaded back to the server by the Agent.
- After ERP input completes successfully for a purchase invoice, the server should queue an `expense_report` Agent task automatically.
- Output target options are fixed to `통합본 PDF 저장`, `평택 프린터`, `김제 프린터`.

## Latest Implemented State

- Current WEB/Agent version in files: `1.0.109`.
- Previous deployable ZIP before current one-click UI cleanup: `C:\Tmp\accounting_web_v1_autorefresh_autoexpense_fix96_20260514_094000.zip`.
- Previous local deployment ZIP after source restore/rebuild: `C:\Tmp\accounting_web_v1_one_click_full_rebuild_fix101_20260514_121500.zip`.
- Previous local deployment ZIP after existing-document output update: `C:\Tmp\accounting_web_v1_one_click_existing_output_fix102_20260514_125629.zip`.
- Previous local deployment ZIP after first WEB regular-processing pass: `C:\Tmp\accounting_web_v1_regular_processing_fix106_20260514_155214.zip`.
- Previous local deployment ZIP after regular PDF 작성일자 fallback fix: `C:\Tmp\accounting_web_v1_regular_pdf_date_fix107_20260514_165139.zip`.
- Latest local deployment ZIP after resident tray Agent / auto-update fix: C:\Tmp\accounting_web_v1_agent_tray_autoupdate_fix108_20260515_082707.zip.
- Latest local deployment ZIP after required setup EXE / tray menu fix109: C:\Tmp\accounting_web_v1_required_setup_exe_tray_fix109_20260515_110534.zip.
- Latest local deployment ZIP after tray right-click menu fix110: `C:\Tmp\accounting_web_v1_tray_right_click_fix110_20260515_112408.zip`.
- Latest local deployment ZIP after regular account-rule fix112: `C:\Tmp\accounting_web_v1_regular_account_rules_fix112_20260515_122034.zip`.
- Latest local deployment ZIP after SMILE EDI regular 지급수수료 integration fix113: `C:\Tmp\accounting_web_v1_smileedi_regular_fee_fix113_20260515_125918.zip`.
- Latest local deployment ZIP after tray menu / Daou vendor fix114: `C:\Tmp\accounting_web_v1_tray_menu_daou_vendor_fix114_20260515_140924.zip`.
- Latest local deployment ZIP after KT vendor business-number fix115: `C:\Tmp\accounting_web_v1_kt_vendor_bizno_fix115_20260515_144302.zip`.
- Previous local deployment ZIP after voucher duplicate-page output fix116: `C:\Tmp\accounting_web_v1_voucher_single_doc_fix116_20260515_153227.zip`.
- Previous local deployment ZIP after no-op auto-save status reset fix117: `C:\Tmp\accounting_web_v1_noop_save_status_fix117_20260515_161724.zip`.
- Previous local deployment ZIP after Compuzone AI/item-name fix118: `C:\Tmp\accounting_web_v1_compuzone_ai_item_names_fix118_20260518_081512.zip`.
- Latest local deployment ZIP after admin DB viewer fix119: `C:\Tmp\accounting_web_v1_admin_db_view_fix119_20260518_083745.zip`.
- Latest local deployment ZIP after password recovery fix120: `C:\Tmp\accounting_web_v1_password_recovery_fix120_20260518_094634.zip`.
- Latest local deployment ZIP after purchase `vendor_biz_no` payload hotfix fix121: `C:\Tmp\accounting_web_v1_purchase_vendor_biz_fix121_20260518_101330.zip`.
- Known hosts: operating server `172.17.39.121`; development PC / temporary ZIP HTTP server `172.17.30.13`.
- `fix98` still had backend/version mismatch symptoms in the active workspace. Rebuilt `fix101` after restoring the missing backend one-click API, mail status API, scheduler wiring, Agent default printer reporting, and WEB/Agent `1.0.89` version files.
- `fix102` adds the existing-document output path and bumps WEB/Agent files to `1.0.90`.
- Backend has new `POST /api/jobs/purchase-one-click`.
- Backend one-click now partitions selected purchase invoices: invoices with ready output document sets skip ERP/cash-report regeneration; all-ready selections go straight to output-set job.
- Backend output-set jobs support `existing_only`; in that mode they fail if a required saved document is missing instead of generating a new cash withdrawal report.
- Backend has new `GET /api/mail-collect/status`.
- Backend startup starts a 1-minute mail collection scheduler with duplicate-run prevention.
- Mail collector now records `saved_invoice_ids`; worker auto-analyzes newly saved purchase invoices.
- Agent preflight now reports Windows default printer as `default_printer`.
- Setup status exposes `capabilities.default_printer`.
- WEB/Agent files are now bumped to `1.0.91` for Agent-side document-set printing.
- Printer output no longer uses operating-server `ShellExecute`; `print_individual` prepares PDFs on the server, queues `output_print`, and the manager PC Agent downloads/prints the PDFs locally.
- Agent preflight advertises `output_print=true`; old Agents without that capability will not claim print tasks and should be updated from the server installer.
- `fix104` guards PDF merge/copy preparation when an existing output-set file is also detected as a source. `merge_pdfs()` now writes to a temporary PDF and atomically replaces the target, so it no longer deletes its own input file.
- `fix105` removes automatic selected-detail/log refresh during job follow-up refreshes, so editing purchase analysis fields is not interrupted.
- `fix105` auto-saves the currently open purchase analysis form before one-click ERP starts.
- `fix105` makes ERP payload construction merge raw JSON, nested data, and current invoice fields with the latest saved screen edits taking priority; explicit edited 사업장 also wins over inferred buyer business-number mapping.
- `fix106` enables the WEB `정기 처리` nav/view, regular list/detail editing, regular one-click ERP/output routing, and regular Agent queue claiming.
- `fix106` adds `PATCH /api/invoices/{invoice_id}/regular-data`, `POST /api/jobs/regular-one-click`, and `POST /api/jobs/regular-erp-input`.
- `fix106` writes regular ERP queue files as `regular_erp_{job_id}.json` with `job_type=regular_erp_input`, and the Agent queue accepts that job type.
- `fix106` ports more legacy regular ERP account/summary rules into `build_regular_erp_payload()` and corrects the regular payable row to `미지급금(원화)`.
- `fix107` makes regular ERP payload creation fall back to reading the tax-invoice PDF body for 작성일자 when saved data and filename do not contain a full date.
- `fix107` enriches newly collected regular invoices with the PDF-derived 작성일자 before DB insert, so monthly filenames like `2026년 05월.pdf` do not fail ERP validation.
- `fix107` changes the user-PC bootstrap payload download to prefer `curl.exe -k`, avoiding PowerShell `Invoke-WebRequest` TLS failures on manager PCs.
- `fix108` preserves the operating-server HTTPS certificate/key across redeploys unless `FORCE_RENEW_HTTPS_CERT=1`, so manager PCs do not need to re-trust a new certificate every deploy.
- `fix108` starts the manager PC Agent as a hidden background process with a Windows tray icon and a single-instance mutex.
- `fix108` makes the Agent compare its bundle hash with `/api/version` and download/run the latest payload in the background when the server bundle changes.
- `fix108` changes the setup install button from blocked EXE download to a copied PowerShell bootstrap command.
- `fix109` adds a real `AccountingWebRequiredSetup.exe` endpoint artifact and removes user-facing PowerShell copy/paste from the setup UI.
- `fix109` makes the manager PC Agent run as a resident tray process with right-click menu items: `내 상태 확인`, `수동 업데이트`, `버전확인`, `종료`.
- `fix109` checks server Agent bundle updates every 1 minute, shows update notes from `/api/version`, and starts the self-update script hidden in the background.
- `fix109` registers `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\AccountingWebAgent`, so reboot/login brings the Agent back automatically.
- `fix109` includes the cash withdrawal report Excel templates from `support/*.xlsx` in the user-PC payload; the Agent still installs the template to `%APPDATA%\양식_현금출금정산서.xlsx` without overwriting an existing file.
- `fix110` fixes the Agent tray right-click menu by handling Windows context-menu events, tolerating foreground-window failures, and executing the selected menu command directly from `TrackPopupMenu`.
- `tax_crawler/portal_smileedi.py` is now registered through `tax_crawler/crawler_main.py` for SMILE EDI `DtiEmail.do` mail links.
- SMILE EDI approval handling remains opt-in via the CLI `--approve`; WEB automatic mail collection does not approve unapproved invoices and only stores approved invoices with saved PDF/XML.
- SMILE EDI approved invoices are stored as regular invoices with `지급수수료` items, so regular ERP/output uses only `전표 + 세금계산서`.
- SMILE EDI is not part of the purchase cash-withdrawal flow. It must not require a quote, approval PDF, or `현금출금결의서`.
- `fix114` fixes the Agent tray right-click menu crash caused by passing `None` to the pywin32 separator menu item.
- `fix114` normalizes regular ERP `vendor_name` before Agent management-item input, so `(주)다우기술` is sent as `다우기술`.
- `fix115` changes regular Agent-side ERP management-item vendor input for KT/케이티. If the ERP 거래처 search popup returns duplicates, the Agent selects the row whose business number is `102-81-42945`; if that row is not visible, it closes the popup and passes instead of selecting the wrong first row. This applies across 대승, 대승정밀, and 일강 because the rule is vendor-based, not company-specific.
- `fix116` stops output-set generation from re-merging an existing `output_sets/.../01_전표.pdf` with the original ERP voucher. Single-source documents such as voucher, tax invoice, and cash report now pick one source; only approval documents still merge multiple PDFs.
- `fix117` stops the purchase/regular auto-save APIs from resetting invoice status to `대기중` when the submitted screen payload is identical to the current saved data. Printing already-complete output sets should no longer make the 수신 내역 look pending just because the frontend auto-saved before one-click.
- `fix118` reconnects the disabled Gemini purchase analysis call for unknown purchase items and adds deterministic Compuzone fallback item-name simplification, so first-time low-cost items do not stay as raw quote lines.
- `fix119` adds a browser-based read-only DB viewer at `/admin-db`, backed by `/api/admin/db/overview` and `/api/admin/db/table`, so the current `C:\ERP_DB\learned_data.db` contents can be inspected without the old CS `admin_viewer.py`.
- `fix120` resets existing WEB users to the initial password `eotmd12!@` once after deployment, marks them as initial-password users, forces a new-password change after login, and restores password recovery as a mail verification-code flow before setting a new password.
- `fix121` fixes purchase one-click ERP payload creation when supplier/vendor business number is absent. `build_purchase_erp_payload()` now defines `vendor_biz_no` before returning it to the Agent queue, so Compuzone-style purchase invoices no longer fail with `name 'vendor_biz_no' is not defined`.
- Frontend has one-click output target combo and localStorage preference.
- Frontend routes purchase ERP button to `/api/jobs/purchase-one-click`.
- Frontend detail mode now has `기존 문서 출력` with output target combo; it only enables when 전표/세금계산서/품의/현금결의서 are all already saved.
- Frontend has mail auto-collection summary text.
- Frontend hides mail collect/log/debug panels in simple mode via `admin-only`.
- Frontend hides purchase `분석` and `분석 저장` buttons in simple mode via `admin-only`.
- Graphify was updated after restoring the one-click source.
- Graphify was updated again after the `fix101` backend/Agent/version repair.
- Graphify was updated again after the `fix102` existing-document output update.
- Graphify was updated after tightening the standalone SMILE EDI crawler authentication detection and the first regular-processing WEB pass: 1265 nodes, 4051 edges, 34 communities.

## Recently Changed Files

- `web_v1/backend/app.py`
- `web_v1/backend/agent_queue.py`
- `web_v1/backend/erp_queue.py`
- `web_v1/backend/erp_runner.py`
- `web_v1/backend/invoice_db.py`
- `web_v1/backend/job_store.py`
- `web_v1/backend/mail_collector.py`
- `web_v1/backend/models.py`
- `web_v1/backend/setup_state.py`
- `web_v1/backend/worker.py`
- `web_v1/agent/erp_agent.py`
- `web_v1/deploy/install_operating_server.ps1`
- `web_v1/frontend/app.js`
- `web_v1/frontend/index.html`
- `web_v1/frontend/styles.css`
- `web_v1/VERSION`
- `tax_crawler/portal_smileedi.py`
- `PROJECT_STATUS.md`
- `web_v1/backend/UPDATE_NOTES.txt`
- `web_v1/backend/tools/AccountingWebRequiredSetup.cs`
- `web_v1/backend/tools/AccountingWebRequiredSetup.exe`
- `web_v1/deploy/start_user_erp_agent.ps1`

## Verification Results

- `py_compile` passed for all `.py` files directly under:
  - `web_v1/backend`
  - `web_v1/agent`
- `node --check web_v1/frontend/app.js` passed.
- Changed-file `py_compile` passed for `web_v1/backend/app.py`, `web_v1/backend/worker.py`, `web_v1/backend/output_set.py`, `web_v1/backend/models.py`, and `web_v1/agent/erp_agent.py`.
- `web_v1/frontend/index.html` now has `admin-only` on both purchase analysis buttons.
- `fix101` ZIP content verification passed for `web_v1/VERSION`, `purchase-one-click`, `mail-collect/status`, `_start_mail_collect_scheduler`, `purchase_one_click`, `auto_analyzed_count`, `default_printer`, `oneClickOutputTarget`, and `원클릭 처리`.
- `fix102` ZIP content verification passed for `web_v1/VERSION`, `purchase-one-click`, `existing_only`, `saved_output`, `기존 문서 출력`, and no `__pycache__`/`.pyc`.
- Changed-file `py_compile` passed for `web_v1/backend/app.py`, `web_v1/backend/worker.py`, `web_v1/backend/erp_queue.py`, `web_v1/backend/agent_queue.py`, and `web_v1/agent/erp_agent.py`.
- Changed-file `py_compile` passed for `web_v1/backend/output_set.py`, `web_v1/backend/app.py`, `web_v1/backend/worker.py`, `web_v1/backend/erp_queue.py`, `web_v1/backend/agent_queue.py`, and `web_v1/agent/erp_agent.py`.
- `node --check web_v1/frontend/app.js` passed after restoring unrelated frontend deletion.
- PDF merge regression passed: merging `[target PDF, second PDF]` back into the target keeps the target and produced a 2-page PDF.
- The unrelated local deletion of `web_v1/frontend/app.js`, `web_v1/frontend/index.html`, and `web_v1/frontend/styles.css` was restored before packaging.
- `fix105` frontend syntax check passed after removing automatic selected-log/detail refresh and bumping the `app.js` cache key.
- `fix105` ERP payload regression passed: edited 매입처, 사업장, 회계일, 금액, 품목 values override older raw/top-level values before ERP input.
- `fix106` `node --check web_v1/frontend/app.js` passed.
- `fix106` changed-file `py_compile` passed for `web_v1/backend/app.py`, `web_v1/backend/worker.py`, `web_v1/backend/erp_queue.py`, `web_v1/backend/agent_queue.py`, `web_v1/backend/erp_runner.py`, `web_v1/backend/invoice_db.py`, `web_v1/backend/models.py`, and `web_v1/agent/erp_agent.py`.
- `fix106` browser mock smoke test passed: regular mode loaded, one regular invoice rendered, row selection opened regular detail with account/item/output-set content, and `정기 원클릭 처리` became enabled.
- `py_compile` passed for `tax_crawler/portal_smileedi.py`.
- SMILE EDI URL detection unit check passed for `https://www.smileedi.com/DtiEmail.do?...`.
- `fix109` changed-file `py_compile` passed for `web_v1/backend/app.py`, `web_v1/backend/setup_state.py`, and `web_v1/agent/erp_agent.py`.
- `fix109` `node --check web_v1/frontend/app.js` passed.
- `fix109` built `web_v1/backend/tools/AccountingWebRequiredSetup.exe` with .NET `csc.exe` and verified the ZIP contains the EXE, `UPDATE_NOTES.txt`, frontend app, `web_v1/VERSION`, and cash-report Excel templates.
- `graphify update .` was attempted after `fix109`, but Graphify refused to overwrite because the new AST-only graph had fewer nodes than the existing graph (`1245` vs `1274`). Existing graph/report were left untouched.
- `fix110` changed-file `py_compile` passed for `web_v1/agent/erp_agent.py`.
- `fix110` ZIP content verification passed for `web_v1/VERSION=1.0.98`, tray context-menu markers, setup EXE, update notes, and cash-report Excel templates; no `__pycache__`/`.pyc` or backup/hotfix/release folders were included.
- `graphify update .` was attempted after `fix110`, but Graphify again refused to overwrite because the new AST-only graph had fewer nodes than the existing graph (`1247` vs `1274`). Existing graph/report were left untouched.

## Open Work

- End-to-end verify on operating server and at least one manager PC:
  - multiple selected invoices run sequentially,
  - ERP failure stops remaining invoices,
  - expense report job runs after ERP,
  - output set refreshes after each event,
  - selected output target produces merged PDF or printer output.
- Verify automatic mail collection scheduler with real unread mail and Compuzone quote auto-attach.
- Verify Agent-side `output_print` on real 평택/김제 printers after deploying current WEB/Agent.
- Verify one-click ERP with an edited purchase analysis field set: 회계일, 매입처, 품목, 계정, 부서.
- Verify regular one-click on operating server and a real manager PC Agent:
  - regular ERP voucher creation/upload,
  - edited regular fields/items/accounts reaching ERP,
  - existing regular `전표 + 세금계산서` output skip path,
  - merged PDF and Agent-side 평택/김제 print targets.
- For SMILE EDI, run operational E2E with one already-approved mail link and one unapproved mail link. Already-approved should save PDF/XML and appear in regular processing as `지급수수료`; unapproved should fail safely without clicking 승인.
- After deploying this ZIP, manager PCs may require Agent update because the Agent bundle hash changes with backend/agent/version files.

## Operational Cautions

- Operating server path:
  - `C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version`
- Local development path:
  - `C:\Users\user\Desktop\개발파일\회계업무 자동화_WEB_Version`
- Because backend files are included in the Agent bundle hash, manager PCs may show latest-version-required after this update. Run the required setup/installer on manager PCs after deploying the server ZIP. For `fix109` and later, the setup UI should download `AccountingWebRequiredSetup.exe`; do not give 담당자 PowerShell copy/paste instructions.
- User expects clean command blocks without `1.`/`2.` prefixes inside the commands.
- Large feature updates or high-volume work should be committed and pushed to `origin` (`https://github.com/rlckd2201/ERP_Auto_Web`) after verification, using a focused commit that excludes pycache, temporary ZIPs, and unrelated backup folders.
- Keep Graphify current: inspect `graphify-out/GRAPH_REPORT.md` before architecture/codebase questions and run `graphify update .` after meaningful code changes.
- Work rhythm standard after fix116:
  - Do not create separate handoff-only commits after every feature commit. Update docs once near the end and include them in the same feature commit when a commit is needed.
  - Do not run Graphify for simple investigation, command handoff, or documentation wording changes. Run it only after meaningful code changes.
  - Keep `.codex/hooks.json` without the repetitive PreToolUse graphify reminder; follow `AGENTS.md` manually instead.
  - Before staging, use `git diff --name-status HEAD --` to identify real changed files, because `git status` may show noisy modified paths in this workspace.
  - For each fix, make one verified ZIP after tests pass. If the ZIP must be rebuilt after more changes, bump to the next fix number instead of repeatedly repackaging the same handoff.
## Current Session Fix111

- Active WEB/Agent files are now `1.0.99`.
- Latest fix111 ZIP: 
C:\Tmp\accounting_web_v1_regular_account_rules_fix112_20260515_122034.zip
.
- fix111 aligns WEB regular ERP rows with the legacy CS manager/server regular-processing 기준: stale crawler/default item accounts are ignored unless the user manually changes the account in the WEB regular detail form.
- Daou Office/groupware regular invoices now default to `지급수수료`, then `부가세대급금`, then `미지급금(원화)`.
- Regular ERP payload now passes `vendor_biz_no` / `supplier_biz_no` to the Agent, and the Agent-side ERP management popup can select a generic regular vendor by supplier business number instead of leaving the 거래처 search popup open.
- fix110 tray right-click menu handling was preserved while bumping Agent/installer version to `1.0.99`.
- Verification passed: Python `py_compile` for `web_v1/backend/erp_runner.py`, `web_v1/backend/app.py`, `manager_server/전표 자동화 프로그램(담당자용)_v6.2.py`, `web_v1/agent/erp_agent.py`; `node --check web_v1/frontend/app.js`; Daou Technology regular ERP regression; ZIP content verification.
- `graphify update .` was attempted after fix111, but Graphify refused to overwrite because the new AST-only graph had fewer nodes than the existing graph (`1247` vs `1274`). Existing graph/report were left untouched.




## Current Session Fix112

- Active WEB/Agent files are now 1.0.100.
- Latest fix112 ZIP: C:\Tmp\accounting_web_v1_regular_account_rules_fix112_20260515_122034.zip.
- Rechecked the CS legacy _guess_regular_account() rule list. WEB now includes the full regular account keyword set, including the previously missing crobat 지급수수료 keyword.
- Verification passed for Python py_compile, frontend node syntax, and regular account regression covering Daou/groupware, Acrobat, KT/VPN, and manual override.


## Current Session Fix113

- Active WEB/Agent files are now 1.0.101.
- Latest fix113 ZIP: C:\Tmp\accounting_web_v1_smileedi_regular_fee_fix113_20260515_125918.zip.
- SMILE EDI `DtiEmail.do` links are now extracted from mail bodies and routed through `SmileEdiHandler`.
- WEB auto collection still does not approve SMILE EDI invoices. 미승인 계산서는 안전하게 실패 처리하고, 승인 완료된 계산서만 PDF/XML 저장 후 DB에 저장한다.
- 승인 완료된 SMILE EDI 계산서는 정기건으로 저장되며, 품목 계정은 `지급수수료`, `erp_ready=true`로 들어간다.
- 정기 ERP payload는 `지급수수료`, `부가세대급금`, `미지급금(원화)` 행을 만들고 정기 출력 세트는 `전표 + 세금계산서`만 요구한다.
- SMILE EDI는 구매 분석/견적서/품의/현금출금결의서 흐름에 연결하지 않는다.
- Verification passed: changed-file Python py_compile, `node --check web_v1/frontend/app.js`, and a SMILE EDI integration regression covering link extraction, handler detection, regular invoice classification, 지급수수료 ERP rows, and 미지급금 row.
- `graphify update .` was attempted after fix113, but Graphify refused to overwrite because the new AST-only graph had fewer nodes than the existing graph (`1255` vs `1318`). Existing graph/report were left untouched.


## Current Session Fix114

- Active WEB/Agent files are now 1.0.102.
- Latest fix114 ZIP: C:\Tmp\accounting_web_v1_tray_menu_daou_vendor_fix114_20260515_140924.zip.
- Fixed Agent tray right-click menu creation: `AppendMenu(..., MF_SEPARATOR, 0, "")` no longer raises `None is not a valid string in this context`.
- Fixed regular ERP payload vendor normalization: Daou regular invoices now pass `vendor_name=다우기술` to the Agent/ERP management-item input instead of `(주)다우기술`.
- Local Agent was temporarily stopped and the HKCU Run entry removed during the patch because server 1.0.101 self-update was overwriting the development workspace back to fix113. Deploy the 1.0.102 server ZIP before restarting the Agent.
- Verification passed: Python `py_compile` for `web_v1/agent/erp_agent.py` and `web_v1/backend/erp_runner.py`; tray separator pywin32 smoke check; Daou regular ERP payload regression.
- Graphify update completed after fix114: 1330 nodes, 4238 edges, 79 communities.

## Current Session Fix115

- Active WEB/Agent files are now 1.0.103.
- Latest fix115 ZIP: C:\Tmp\accounting_web_v1_kt_vendor_bizno_fix115_20260515_144302.zip.
- Regular ERP management-item vendor selection now gives KT/케이티 priority over any supplier business number present in the payload.
- When the ERP 거래처 popup has duplicate 케이티 rows, the Agent selects business number 102-81-42945.
- If the popup does not appear or the 102-81-42945 row is not found, the Agent passes without pressing Enter on the highlighted first row.
- User stopped the local Agent before final packaging; `pythonw.exe` was no longer running. Deploy the 1.0.103 operating-server ZIP before restarting/patching the manager PC Agent.
- Verification passed: Python py_compile for `manager_server/전표 자동화 프로그램(담당자용)_v6.2.py` and `web_v1/agent/erp_agent.py`; `node --check web_v1/frontend/app.js`.
- fix115 ZIP content verification passed for `web_v1/VERSION=1.0.103`, KT business-number/pass markers, setup EXE, frontend assets, and no `graphify-out`/backup/hotfix/release/pycache files.
- Graphify update completed after fix115: 1330 nodes, 4238 edges.

## Current Session Fix116

- Active WEB/Agent files are now 1.0.104.
- Latest fix116 ZIP: C:\Tmp\accounting_web_v1_voucher_single_doc_fix116_20260515_153227.zip.
- User-provided samples `C:\Users\user\Downloads\73\01_전표.pdf` and `C:\Users\user\Downloads\77\01_전표.pdf` were 4 pages each, with all pages identical. The matching source ERP voucher PDFs under `C:\ERP_DB\erp_outputs` were 1 page each.
- Root cause: output-set voucher candidates included existing `output_sets/.../01_전표.pdf`; repeated output generation could merge the already-built output-set voucher back with the original voucher.
- Fix: `_copy_or_merge_doc()` removes the target file from merge inputs, prefers non-output-set sources for single-document outputs, and only preserves multi-PDF merging for `approval_docs`.
- Verification passed: Python py_compile for `web_v1/backend/output_set.py`; regression test confirmed voucher stays 1 page while approval docs still merge to 2 pages.
- fix116 ZIP content verification passed for `web_v1/VERSION=1.0.104`, single-document voucher guard markers, setup EXE, frontend assets, and no `graphify-out`/backup/hotfix/release/pycache files.
- Graphify update completed after fix116: 1334 nodes, 4247 edges, 35 communities.

## Current Session Fix117

- Active WEB/Agent files are now 1.0.105.
- Latest fix117 ZIP: C:\Tmp\accounting_web_v1_noop_save_status_fix117_20260515_161724.zip.
- Root cause: `startErpQueue()` auto-saves the selected regular/purchase detail before one-click. The backend save APIs then called `reset_invoice()` unconditionally, so already-complete invoices could become `대기중` even when the user only printed existing document sets.
- Fix: `PATCH /api/invoices/{invoice_id}/purchase-analysis` and `PATCH /api/invoices/{invoice_id}/regular-data` now compare normalized editable snapshots. If the screen payload is unchanged, they refresh output docs and return without updating JSON or resetting status.
- Verification passed: Python py_compile for `web_v1/backend/app.py` and `web_v1/agent/erp_agent.py`; frontend `node --check web_v1/frontend/app.js`; regular snapshot regression for same-value/no-change versus changed vendor.
- fix117 ZIP content verification passed for `web_v1/VERSION=1.0.105`, no-op save snapshot guard markers, setup EXE, frontend assets, and no `graphify-out`/`__pycache__`/`.pyc` files.
- Graphify update completed after fix117: 1339 nodes, 4264 edges, 81 communities.

## Current Session Fix118

- Active WEB/Agent files are now 1.0.106.
- Latest fix118 ZIP: C:\Tmp\accounting_web_v1_compuzone_ai_item_names_fix118_20260518_081512.zip.
- Root cause: `_ai_parse()` existed but `analyze_purchase_documents()` forced `ai_data = None`, so Gemini was never called. First-time Compuzone items fell back to fast parsing and kept the quote raw line as the item name.
- Fix: unknown purchase items now call `_ai_parse()` when `GEMINI_API_KEY` is configured. If AI is unavailable or fails, Compuzone low-cost item names still get deterministic fallback simplification such as `USB 3구 멀티탭`, `블루투스 스피커`, `차량용 공기청정기`, `차량용 무선충전 거치대`, and `모니터 받침대`.
- Verification passed: Python py_compile for `web_v1/backend/purchase_analysis.py`, `web_v1/backend/app.py`, and `web_v1/agent/erp_agent.py`; frontend `node --check web_v1/frontend/app.js`; item-name simplification regression; empty-learning-DB processing regression.
- fix118 ZIP content verification passed for `web_v1/VERSION=1.0.106`, Gemini call marker, Compuzone item-name simplifier markers, setup EXE, frontend assets, and no `graphify-out`/`__pycache__`/`.pyc` files.
- Graphify update completed after fix118: 1347 nodes, 4277 edges, 81 communities.

## Current Session Fix119

- Active WEB/Agent files are now 1.0.107.
- Latest fix119 ZIP: C:\Tmp\accounting_web_v1_admin_db_view_fix119_20260518_083745.zip.
- Root cause: the old CS `admin_viewer.py` called removed endpoints such as `/api/dictionary`, `/api/update_dict`, and `/api/delete_dict`, and was not aligned with the current WEB v1 database/API surface.
- Fix: added a read-only WEB DB viewer at `/admin-db`, plus `/api/admin/db/overview` and `/api/admin/db/table` for safe table/count/row inspection of `C:\ERP_DB\learned_data.db`.
- The main WEB UI now injects a detail-mode `DB 보기` button that opens `/admin-db` in a new tab.
- Verification passed: Python py_compile for `web_v1/backend/app.py` and `web_v1/agent/erp_agent.py`; `node --check` for `web_v1/frontend/app.js` and `web_v1/frontend/admin_db.js`; FastAPI TestClient confirmed overview/table APIs return current DB tables and invoice rows.
- Graphify update completed after fix119: 1363 nodes, 4323 edges, 79 communities.

## Current Session Fix120

- Active WEB/Agent files are now 1.0.108.
- Existing WEB users are reset once to `eotmd12!@` through an `auth_meta` reset marker, then users must change to a new password on first login.
- Password recovery now sends a 6-digit verification code to `{user_id}@dae-seung.co.kr` by default and changes the password only after the code is confirmed.
- SMTP password is not hardcoded in source. The server uses `PASSWORD_RESET_SMTP_PW`, or falls back to existing `EMAIL_PW`. For operation, deploy with `PASSWORD_RESET_SMTP_USER/PW=admpdm` and `PASSWORD_RESET_FROM=admpdm@dae-seung.co.kr`.
- Verification passed: Python py_compile for `web_v1/backend/app.py`, `web_v1/backend/setup_state.py`, `web_v1/backend/config.py`, and `web_v1/agent/erp_agent.py`; `node --check web_v1/frontend/app.js`; FastAPI TestClient auth regression for initial-password login, forced change, code issue, and reset-with-code.
- `install_operating_server.ps1` writes `PASSWORD_RESET_*` values into the server `.env`; set `PASSWORD_RESET_SMTP_USER/PW` before install when a dedicated SMTP account should be used.
- Graphify update completed after fix120: 1377 nodes, 4363 edges, 80 communities.

## Current Session Fix121

- Active WEB/Agent files are now 1.0.109.
- Latest fix121 ZIP: C:\Tmp\accounting_web_v1_purchase_vendor_biz_fix121_20260518_101330.zip.
- Root cause: fix111 regular-processing vendor business-number payload fields were later mirrored into the purchase ERP payload return, but `build_purchase_erp_payload()` did not define `vendor_biz_no` before returning it.
- Fix: purchase ERP payload now extracts `vendor_biz_no` from current data/raw supplier fields and falls back to an empty string when absent.
- Important local note: the resident local `pythonw.exe` Agent was running against the development folder and reverted source while editing. It was stopped before the real file patch was applied and verified.
- Verification passed: Python py_compile for `web_v1/backend/erp_runner.py` and `web_v1/agent/erp_agent.py`; #78-like Compuzone purchase payload regression confirmed `vendor_biz_no=''` and ERP rows are generated.

- Graphify update was attempted after fix121, but Graphify refused to overwrite because the AST-only rebuild had fewer nodes than the existing graph (1291 vs 1377). Existing graph/report were left untouched.
