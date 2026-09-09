# Debug

Updated: 2026-08-25

## I-001 — backend static frontend dependency was missing — resolved

- Symptom: tracked `web_v1/frontend/*` files were deleted in the worktree while `app.py` served that directory.
- Resolution: restored HEAD-identical static files, verified later `index.html` from fix210, and verified later `app.js` from fix214.
- Check: JavaScript syntax and DOM-reference audit passed; all required frontend files exist.

## I-002 — required setup EXE was missing — resolved

- Symptom: `AccountingWebRequiredSetup.cs/.exe` were deleted, causing the installer endpoint to return 404.
- Resolution: restored Git HEAD content; all audited preserved copies were byte-identical.
- Check: restored hashes match Git HEAD.

## I-003 — Zoom module was untracked — resolved

- Symptom: `mail_collector.py` imported `web_v1/backend/zoom_billing.py`, but the module was not tracked.
- Resolution: retained the current 10,279-byte file; SHA-256 `96945EDBEEA011150B7D9CAD32F75979B345E4D5BE55AC561F78C67E6D5A3397` matches recent preserved candidates.
- Check: Python compilation passed with the importing mail/backend modules.

## I-004 — Graphify corpus was polluted — resolved

- Symptom: the prior report analyzed 2,418 files, including historical `_codex_*` and release/stage/check copies.
- Resolution: added `.graphifyignore`, preserved the old graph under an ignored local backup directory, and regenerated the tracked outputs.
- Check: 64 files, 1,458 nodes, 4,187 edges, 32 communities, and zero historical source-path hits.

## I-005 — patch tool limitation — contained

- Symptom: the patch tool repeatedly hung while adding or updating Markdown in this Windows workspace.
- Workaround: after confirming repeated failure, state/documentation files were written with explicit UTF-8 paths through PowerShell. Runtime source code was not edited through this workaround.

## I-006 — deployment E2E boundary — partially resolved

- Live verified: FastAPI restart and `/health`, Agent bundle update, Agent claims, Excel report generation/upload, output-set creation, Pyeongtaek printing, and Windows spooler submission.
- Still not rerun: installer download and ERP GUI entry. ERP was intentionally excluded to avoid duplicating completed accounting work.
- Next safe check: installer response plus a controlled non-production ERP case.

## I-007 — origin/main advanced concurrently — isolated safely

- Symptom: push to main was rejected because the remote advanced from the local base to `c20a96c`.
- Remote scope: new `excel_voucher_web`, extensive manager-side fixes, and overlapping AGENTS/Graphify outputs.
- Containment: no force push, no automatic dirty-worktree rebase, and no user changes stashed or overwritten. The focused commit is published on `codex/reconcile-state-20260812`.
- Next check: compare product ownership and graph scope before cherry-picking or merging into main.

## I-008 — WEHAGO saved the surrounding web page — resolved

- Symptom: the operating server produced a 156,339-byte Chrome/Skia PDF containing WEHAGO status controls instead of the tax invoice alone.
- Expected reference: a 169,651-byte, one-page Developer Express PDF containing only the invoice.
- Resolution: browser-PDF fallback is rejected; only the Duzon native print path can become canonical.

## I-009 — WEHAGO native print/save timing and UI handling — resolved

- The print runtime was killed before its delayed preview appeared; retries now keep it alive and wait longer.
- Preview detection recursively scanned unrelated Chrome UI and missed the already-open title; detection is now title-only.
- The PDF button opens Save As directly on the installed runtime; the obsolete second print click is skipped when that dialog exists.
- Save As now receives the final path with synchronous `WM_SETTEXT` and confirms Save with synchronous `BM_CLICK`.
- Verification: 12 WEHAGO unit tests pass. Production retry job `0f382cd4-db29-4225-980f-0f0930c22aa0` finished with zero failures. The server-created PDF is 169,685 bytes, Developer Express v15.1.7, one page, and is visually equivalent to the manual normal PDF.

## I-010 — cash-disbursement author used Agent login fragment — resolved

- Symptom: `#206` and `#207` displayed `작성자 reum` instead of `작성자 구름`.
- Root cause: one-click frontend payload hard-coded `processor: "WEB v1.0"`; server fallback derived `reum` from Agent ID `reum-reum`, which does not match auth user ID `reum0009`.
- Operational repair: set both invoice processors/authors to `구름`, preserve prior PDFs as `pre_regen` backups, regenerate through the connected user-PC Agent, save individual PDFs, and print only the two corrected cash-disbursement documents.
- Verification: both PDFs are one-page A4, extracted text contains `작성자 구름` and no `reum`, visual renders are clean, and print job `3ef76859-c824-421d-96fa-4ecb493e6d3f` reports `2/2` Windows spooler submissions.
- Permanent resolution: authenticated WEB user identity is resolved to a canonical display name on the server; unique legacy prefixes remain supported, while Agent/machine IDs cannot become authors. The fix is deployed on 121 and the focused regression tests pass.

## I-011 — duplicate 12:00 regular-due status messages — guard deployed, observation pending

- Symptom: a correct `[정상]` message arrived around 12:00:10, followed by a stale `[누락]` message around 12:00:25 with old counts and a loopback history URL.
- Evidence: the valid sender reported the current `https://172.17.39.121:8080/regular-due-history` state from PID 11160 on `WIN-2H29RFPBUMN`; the stale copy used `http://127.0.0.1:8080/regular-due-history` and obsolete waiting/completion data.
- Fix deployed: regular-due alert sending requires explicit enablement and canonical hostname `WIN-2H29RFPBUMN`; wrong-host/default-disabled/enabled-host regression tests pass.
- Boundary: observe the next real 12:00 run and confirm exactly one message.

## I-012 — first corrected-source deployment reported a false test failure — resolved and deployed

- Symptom: 121 returned `ok=false` with `test_login_binds_user_to_agent (...) ... ok` as the error text.
- Root cause: Python `unittest -v` writes normal progress to stderr, and PowerShell with `ErrorActionPreference=Stop` converted that stream into a terminating native-command error.
- Resolution: compile/tests now run through `cmd.exe /d /c ... 2>&1`; `$LASTEXITCODE` is the only success criterion. The first attempt restored all five backed-up source files before touching the backend process.
- Final state: the corrected deploy completed at `2026-08-21T09:54:20`; six focused tests, import, database initialization, restart, and health all passed.

## I-013 — historical author variants on four rows — resolved

- Corrected: `#176=구름`, `#179=구름`, `#180=김기창`, and `#205=현시훈`; old reports were copied to `C:\ERP_DB\backups\document_actor_repair_20260821_095421`.
- `#205` retained its existing ERP error and ERP was not rerun. The repair print queue verified four submissions.
- Already-correct `#206` and `#207` remained `구름` and were excluded from duplicate repair printing.

## I-014 — cash-disbursement PDF was undersized; required direction clarified — resolved

- Symptom: the form was small because the Excel print area included unused rows 21–42. An interim correction changed the document to landscape, but the user clarified that the required physical direction is portrait.
- Root cause: `PrintArea = "$A$1:$R$42"` included 22 blank rows although the form ends at row 20. Landscape was an incorrect requirement assumption, not the desired final output.
- Resolution: restore portrait A4 (`1`), keep corrected print area `$A$1:$R$20`, deploy to 121, and let both generation Agents update.
- Verification: final `#176`, `#179`, and `#180` PDFs are each one `595.20 x 841.68` portrait page and preserve authors `구름`, `구름`, and `김기창` without Agent-ID text.
- The interim landscape output job `ab3d3fc6-8351-4586-9e91-2a0c9e206452` was superseded. Final portrait regeneration completed with `print_skipped=true`; no additional paper was submitted.

## I-015 — backend deployment process/health detection was too broad — resolved in deployment tooling

- A stale listener PID and loopback HTTPS health request caused false deployment failures even while Uvicorn was starting correctly.
- Deployment now targets only Python processes whose command line matches `-m web_v1.backend`, checks `https://172.17.39.121:8080/health`, and accepts the Uvicorn startup log only as a bounded fallback.
- The final portrait deployment restarted the backend to PID `7360` and returned healthy version `1.0.228`.

## I-016 - same-server orphan workers caused duplicate noon mail - resolved, observation pending

- Symptom: the stale 12:00 message continued after the canonical-host guard was deployed.
- Evidence: the message source identified sender PID `3836` on `WIN-2H29RFPBUMN` and a loopback history URL. The server had both `127.0.0.1:8080` and `0.0.0.0:8080` listeners.
- Root cause: old multiprocessing workers survived their parent backends and retained inherited listener handles. PID `3836` referenced dead parent `1696`; PID `3748` referenced dead parent `10128`. An obsolete Common Startup link targeted the system-profile project copy.
- Resolution: stop both orphan workers, move the obsolete link into a recoverable backup, create one canonical startup link, and require a cross-process file lock before the regular-due scheduler starts.
- Verification: final exact-source deployment `2026-08-24T08:47:59` passed six focused tests and import/health checks. Backend PID `9940` is the sole port-8080 listener, owns `C:\ERP_DB\regular_due_sender.lock`, and reports `scheduler_started=true` plus `process_lock_acquired=true`.
- Boundary: no test email was sent; the next real 12:00 delivery must contain exactly one message.

## I-017 - Zoom #212 repeatedly failed during Excel PDF export - resolved and live-verified

- Symptom: Zoom `#212` remained waiting while a new expense-report job failed about every minute; Etech `#213` had already completed independently.
- Root cause: the target PC's active Excel printer driver rejected `PageSetup.PaperSize = 9` with COM error `-2146827284`. The exception aborted export before the missing cash-disbursement PDF could be uploaded.
- Resolution: isolate page setup, tolerate the paper-size setter failure, preserve portrait/print-area/fit settings, normalize non-A4 output to exact portrait A4 with PyMuPDF, and throttle automatic retries to 600 seconds.
- Deployment: the first attempt safely rolled back because PowerShell treated normal `unittest -v` stderr as a terminating error. The corrected deployment passed all 11 tests, restarted the sole backend from PID `9940` to `7484`, retained the regular-due process lock, and updated Agent `DESKTOP-55LQ6BN-TEST` to bundle hash `5c25d508c1471269ad3230704e860a979ec2c89c897b2c94cca228ce26ffa536`.
- Verification: generation job `5064f4ad-67e8-48c3-82d3-9918e03c5f62` completed; the PDF is one exact `595.28 x 841.89` portrait-A4 page with clean rendering. Output job `2477e07e-9807-4464-b091-330910d4302c` submitted the billing PDF and report once each to the Pyeongtaek printer and returned `2/2` success with two spooler confirmations. Invoice `#212` is complete.

## I-018 - Gemini SDK failed TLS on the first production deployment - resolved

- Symptom: the first Gemini 3.7 deployment reached its SDK model check but failed with `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` on the operating server.
- Containment: the deployment script restored all changed source/environment files and restarted the prior healthy backend as PID `7740`; backup `C:\ERP_DB\backups\gemini37_20260824_114141` remains available.
- Root cause: the production network's certificate chain is trusted by Windows but was not available through the SDK's default Python CA path.
- Resolution: create a `truststore.SSLContext` and pass it as the `google-genai` client's HTTP verification context. Certificate verification remains enabled.
- Final verification: deployment backup `C:\ERP_DB\backups\gemini37_20260824_115520`; 13 tests passed; SDK lookup returned `models/gemini-3.7-flash`; live JSON generation succeeded; backend PID/listener `8568` passed HTTPS health and owns the regular-due process lock.
- Graph boundary: `graphify update .` was run after code changes, but Graphify refused the unexpectedly smaller regeneration. Do not force it; rebuild from a clean, reconciled source tree before replacing tracked graph outputs.

## I-019 - Korean PDF filenames blocked the new Gemini file upload - resolved and deployed

- Symptom: read-only comparison of invoices `#159`, `#207`, and `#208` failed before generation with `UnicodeEncodeError: 'ascii' codec can't encode characters` in the SDK/httpx multipart header builder.
- Root cause: `_ai_parse` passes the original Korean Windows path directly to `client.files.upload`; the maintained SDK uses that filename in an ASCII-constrained HTTP header.
- Fix: copy the unchanged PDF bytes to temporary `tax_invoice.pdf` and `quote.pdf` paths, upload those copies, and retain remote-file deletion plus client cleanup in `finally`.
- Regression coverage: success and forced-generation-failure tests verify ASCII upload names, exact copied bytes, local temporary-file cleanup, remote Gemini-file deletion, and client closure.
- Retry containment: SDK defaults could retry five times per call, and the first live verifier wrapped that with three more attempts. The production client now limits each request to 60 seconds and two total SDK attempts; the verifier uses the production function once.
- Comparison boundary: the new key received 404 for `gemini-2.5-flash` because it is unavailable to new users. Historical stored results are the only 2.5-era baseline; `#207` has subsequent manual edits.
- Deployment: backup `C:\ERP_DB\backups\gemini_filename_fix_20260824_135253`; 14 tests passed; Korean-named `#208` completed one read-only `_ai_parse` call through `gemini-3.7-flash`; temp cleanup passed; invoice state remained unchanged for status, processor, analysis source/model, and items; backend PID `6568` is healthy and owns the sole listener/scheduler lock.
- Final availability check: `https://172.17.39.121:8080/health` returned `ok=true` and the production UI rendered in Chrome. The same port intentionally closes plaintext HTTP requests because TLS is enabled.

## I-020 - PowerPoint COM could render but could not save a new presentation - contained

- Symptom: both the full draft and a one-slide blank test failed at `Presentation.SaveAs` and `SaveCopyAs` with the same generic PowerPoint save error, including when the destination was an ASCII path under `%TEMP%`.
- Isolation: the failure reproduced without screenshots, notes, Korean filenames, or project content, so it was not a deck-layout or source-data defect.
- Containment: generate the `.pptx` with installed `python-pptx 1.0.2`, reopen it programmatically, and use PowerPoint COM only to open the existing file and export every slide to PNG.
- Verification: final deck opens as 14 slides, all 14 speaker-note source blocks are present, PowerPoint exported 14 PNGs at 1600x900, and each slide was visually inspected. The skill-provided overflow test was unavailable because `numpy` is not installed; PowerPoint rendering and full-size inspection were used as the layout acceptance check.

## I-021 - executive PPT v0.1 reused browser chrome and overemphasized errors - resolved in v0.2

- Symptom: slide titles wrapped, reused screenshots exposed Chrome tabs/bookmarks, and error/retry material displaced the executive value story.
- Resolution: capture clean content-only mail/history/quote views, remove operational error slides, add actual ERP/output documents, and rebuild around business impact and simplified work.
- Layout acceptance: all 12 title boxes contain no newline and render on one line in PowerPoint at 1600x900. Every slide was checked full size and in `output/system_overview_ppt_v02/renders/montage.png`.
- Artifact acceptance: `python-pptx` reopened 12 slides, all notes contain `[Sources]`, the package is a valid PPTX ZIP, and PowerPoint reopened it with 12 slides.

## I-022 - v0.2 counted unattended automation time as operator labor - resolved in v0.3

- Symptom: post-adoption time used five minutes for regular and eight minutes for purchase, overstating operator occupancy and understating time saved.
- Correction: use one minute per case for click/result confirmation and exclude automation waiting time. Annual volume is regular 240 plus purchase 250.
- Result: 225.8 hours before, 8.2 hours after, 217.7 hours saved; 96.4% reduction. At the 2026 minimum wage of KRW 10,320/hour, direct labor is KRW 2,246,320/year.
- ROI correction: external rebuild and outsourced-maintenance ranges are no longer presented as actual system costs; they remain appendix references only.
- Verification: 13-slide PPTX reopened programmatically and in PowerPoint, all source notes are present, all title boxes contain no newline, and all 13 slides rendered at 1600x900 for visual QA.

## I-023 - v0.3 duplicated impact metrics and used sentence-length titles - resolved in v0.4

- Symptom: slide 3 repeated annual time and wage figures already explained later, while multiple slide titles read like full conclusions rather than section/function names.
- Resolution: merge the summary and system-flow slides into a metric-free `원클릭 회계처리` slide, shorten all titles, and reduce the deck from 13 to 12 slides.
- Verification: the final PPTX is a valid ZIP, contains 12 slides and 12 source-note blocks, every title has no newline, PowerPoint reopened all 12 slides, and the full deck rendered cleanly at 1600x900.

## I-024 - invoice #209 reports error after blind vendor selection and failed PDF output - diagnosed

- Scope: production was read only; no ERP retry, state mutation, or source-code change was performed.
- Data: invoice `#209` is a P3 Compuzone purchase for KRW 2,649,360. XML supplier business number is `106-81-83458`; the four-row ERP payload ends with `가지급금(업체)`.
- Management evidence: both runs used `106-81-83458`, but rows 3 and 4 logged `vendor popup already opened`, deliberately skipped reopening/refocusing the row relation field, and then ran a fixed `Tab 4 / Down 5 / Up 1 / Tab 3 / Enter 2` sequence. The function returns `True` and logs completion without reading the selected vendor back from ERP. This explains how the intended query can be correct while the visible management value is wrong.
- Misleading log: `3행 사업자번호` received `대승정밀(주)-김제P3`; this is the buyer-site query used by the VAT row, not the fourth-row Compuzone vendor value. The label makes the sequence easy to misread.
- Terminal failure: jobs `d9cc4929-8e37-420c-9f35-09991cd3e310` and `f5f0b54e-441f-48d7-91c2-2718ed102f4c` both sent Ctrl+S, timed out waiting for `rdviewer_u.exe`, timed out waiting for the print dialog, and then failed because the expected ERP PDF did not exist.
- Error propagation defect: the save/print helper treats viewer/dialog timeouts as non-fatal and logs coordinate-form completion; only the backend missing-file check later raises `ERP 전표 PDF 자동 저장 실패`.
- Duplicate risk: Ctrl+S was sent in both failed attempts, so one or two ERP vouchers may already exist even though the web job is marked error. Check K-System before any retry.
- Performance evidence: purchase tasks do not receive the regular-auto management timing profile, and full menu/header verification remains enabled. The flow spends time verifying menu/company/unit/date while the critical selected-vendor and print-output states are not verified at their source.

## I-025 - local Agent self-update reverted the in-progress #209 fix - contained

- Symptom: while the purchase ERP fix was being edited, the source files reverted exactly to their pre-change hashes and `web_v1/test_purchase_gemini_sdk.py` disappeared.
- Root cause: local PID `20356` was the live `pythonw.exe ... web_v1\agent\erp_agent.py --server https://172.17.39.121:8080 --insecure`; its self-updater downloaded the still-old production bundle over the shared worktree.
- Containment: verify the exact command line, stop only PID `20356`, reapply the patches, and restore the deleted Gemini test mechanically from `tmp/gemini_filename_fix_worktree`. Its restored SHA-256 is `8AD0F6A02CE08F2D1B382A8978A67DE85DC75C1EB88A6374D9145854D49EDFEE`.
- Boundary: do not restart this Agent against the old production bundle. Deploy `1.0.229` first, then restart it and verify the downloaded bundle hash.

## I-026 - #209 vendor and output defects corrected and deployed

- Vendor repair: stale popup reuse and the fixed `Tab 4 / Down 5 / Up 1 / Tab 3 / Enter 2` sequence were removed. Each row now opens its own popup and accepts only an exact 10-digit business-number result.
- Output repair: viewer, print-dialog, and PDF-save timeouts now fail immediately. Any failure after Ctrl+S carries `[ERP_SAVE_CONFIRM_REQUIRED]`, and the API returns HTTP 409 on direct retry until an explicit error-to-waiting transition clears the guard.
- Performance repair: purchase tasks receive a dedicated ordinary-PC fast profile; `regular_auto` and its 243-PC timing remain unchanged.
- Verification: all changed Python modules compile; `python -m unittest discover -s web_v1 -p 'test*.py' -v` passes 11 tests; Graphify rebuilt successfully to 1,405 nodes, 3,875 edges, and 48 communities.
- Deployment: operating-server backup `C:\ERP_DB\backups\erp_purchase_fix_20260826_110738`; backend PID/listener `3948`; version `1.0.229`; scheduler and process lock active. Local Agent PID `21168` reports ready and matches server bundle hash `df297cc0601d8b314205d8367bb7446d7f706eef19b7cd6a7975b690fd9084d7`.
- Remaining risk: static tests cannot prove how the live K-System popup exposes result cells through UI Automation. First safe new purchase use must be observed, and invoice #209 must not be retried until the earlier save attempts are checked inside K-System.

## I-027 - WinRM credential was stale during 1.0.229 deployment - RDP transport succeeded

- Symptom: port 5985 was reachable, but the password currently served by `http://172.17.39.121/pass.txt` was rejected by WinRM. External port 8080 also appeared unavailable before deployment.
- Recovery path: connect through the saved administrator RDP endpoint on port 6389, run a short typed PowerShell bootstrap, download hash-pinned payload files from the temporary development-PC transport, and execute the backup/rollback deployment script on the server.
- Verification: seven production targets matched their expected old hashes before replacement; 11 server tests passed; the backend moved from PID `6568` to `3948`; external HTTPS health/version, single listener, regular-due lock, Agent heartbeat, setup readiness, and exact server/local bundle-hash equality all passed.
- Cleanup: the temporary HTTP transport and RDP client were stopped after verification. No ERP job or invoice state was changed during deployment.

## I-028 - 1.0.229 purchase fast profile invalidated the K-System header/UIA flow - diagnosed

- Symptom: invoice `#209` job `0be1a41e-5d97-4950-8454-e69fc8947972` failed three seconds after the `회계일` coordinate click with COM/UIA error `-2147220991` (`이벤트에서 가입자를 불러낼 수 없습니다`). The operator reported that K-System itself closed during the date entry.
- Retry evidence: job `f7e66896-2ec1-4746-b7fc-c427b659637f` opened a new K-System PID and passed header/grid entry, but every later `main_win.rectangle()`/popup scan saw the same disconnected UIA state. Cached coordinates allowed the flow to continue until exact-vendor popup selection failed; Ctrl+S was not reached in either post-deployment job.
- Regression source: 1.0.229 adds the purchase-only `ERP_FAST_INPUT=1` and `ERP_FAST_FIELD_VERIFY=1` defaults. They set global PyAutoGUI pause to `0.01`, shorten paste waits, and skip verification for critical coordinate-entered fields including 회계일.
- Baseline: the pre-deployment `#208` job verified 전표관리단위 and 회계일 successfully with the conservative path. Earlier `#209` attempts also verified 회계일 before reaching management and Ctrl+S.
- Boundary: the development-PC Agent at `172.17.30.13` had no claimed ERP task; both failing jobs ran on `송명학-송명학` at `172.17.30.15`. Local Windows event logs therefore cannot identify the remote K-System crash process.
- Containment: do not retry #209. The older 08:39 attempt already issued Ctrl+S, so K-System must be checked for an existing voucher before any future run.

## I-029 - purchase header/UIA regression corrected and deployed in 1.0.230

- Root cause: the 1.0.229 purchase profile combined `ERP_FAST_INPUT=1` and `ERP_FAST_FIELD_VERIFY=1`, reducing global key pacing and removing read-back at the exact header transitions where K-System can recreate or disconnect its UIA provider.
- Repair: interactive purchase tasks now force stable input and mandatory critical-field verification. The automation reconnects to the active K-System process/window after header transitions; failure to reconnect or read back a required value stops before management-grid work and before Ctrl+S.
- Regression coverage: 10 purchase runtime-safety tests plus the three Gemini upload tests pass; changed Python files compile and `git diff --check` is clean.
- Deployment: production backup `C:\ERP_DB\backups\erp_header_stability_20260826_120208`; version `1.0.230`; backend/listener PID `8268`; scheduler and process lock active; exact bundle hash `5eae04b11a38dcdcdd5741d11c29f7d5df5f878508761d05fef657d9141fd1e2`.
- Live setup verification: local Agent PID `26008` is connected from `172.17.30.13`, reports current/latest `1.0.230`, and matches the production bundle hash. No ERP task was run as a deployment test.
- Remaining acceptance risk: #209 still requires a manual K-System saved-voucher check because an earlier pre-fix attempt sent Ctrl+S. The next genuinely safe new purchase case should be observed for live header read-back and exact vendor result exposure.

## I-030 - local Agent self-update overwrote the in-progress 1.0.230 worktree - contained

- Symptom: while 1.0.230 was being prepared, the local Agent noticed that production still served 1.0.229 and restored the shared Agent bundle, including deleting an unbundled test file.
- Containment: identify the exact `pythonw.exe ... web_v1\agent\erp_agent.py` command line, stop only that Agent, restore the test mechanically from the verified worktree backup, reapply the source patch, and rerun all checks.
- Prevention: keep the editable-worktree Agent stopped whenever local and production bundle hashes intentionally differ. Restart it only after deployment and confirm version/hash equality through `/api/setup/status`.

## I-031 - exact UIA vendor selection introduced in 1.0.229 cannot see K-System results - resolved in 1.0.231

- Symptom: #209 repeatedly opened the vendor popup but logged `정확히 일치하는 사업자번호 검색결과 없음`; the operator saw the management popup close without a usable value.
- Root cause: 1.0.229 replaced the established default-focus keyboard contract with `popup.set_focus()`, an inferred search-Edit click, and an exact UIA result scan. Live inspection showed the popup exposes search Edit `textBox1` and button `btnServerSearch`, but exposes no result grid rows/cells at all. Moving focus also prevents the business number from reaching the already-focused search box.
- Direct proof: manually entering `106-81-83458` displayed the single Compuzone row; copying the visible business-number cell returned the exact value, and double-clicking it populated `컴퓨존`. The failed code path still could not discover that visible row through UIA.
- Repair: remove all search-Edit click/filter/result-cell functions and restore the existing sequence `Ctrl+A`, business-number paste, `Tab 4`, `Down 5`, `Up 1`, `Tab 3`, `Enter 2`. Keep stale-popup closing, stable header read-back, UIA reconnection, and post-save retry guard. Remove purchase fast-management timings only; retain fast navigation.
- Safe direct verification: invoice #209 ran through the real ERP input function with `_save_and_open_print_dialog()` replaced in memory by a hard `[DIRECT_STOP_BEFORE_SAVE]` exception. Rows 1, 3, and 4 completed; row 4 visibly showed `컴퓨존`. No Ctrl+S was sent, and PID `27684` was closed unsaved.
- Deployment: first 1.0.231 attempt auto-rolled back because the cold regular-due status endpoint exceeded a 15-second verification timeout. A direct call completed normally in 11 seconds; the deployment check was raised to 60 seconds and the second attempt succeeded. Production backup `C:\ERP_DB\backups\erp_vendor_restore_20260826_133229`, backend/listener PID `6160`, server tests `13`, scheduler/lock healthy.
- Agent acceptance: local Agent PID `9688` reports current/server version 1.0.231, `ready=true`, and matching hash `1ce3dbf32a0e363016cf0be9a8a10ace243ef36594db215815568449ea4697e9`. The temporary direct-test UI dump was moved out of the hashed source tree and preserved under `tmp/`.

## I-032 - intermittent purchase vendor failures persisted after keys were restored - resolved in 1.0.232

- Evidence: the latest #209 job failed before save at the VAT-row popup-open step. The latest #211 job sent vendor sequences successfully but later reached Ctrl+S and failed output, so it remains a manual-confirmation case and was not replayed.
- Primary defect: `_input_vendor_by_business_no_keyboard` returned success after key transmission without checking the selected management value. The outer row retry covered `plan == ["vendor"]` only, so a VAT-row popup failure was immediately terminal.
- Timing/state defects: management double-clicks used a fixed 0.05 seconds, popup keys used 0.08 seconds, the form trusted the ambient clipboard after ERP startup, and a surviving unsaved ERP instance could be reused by a subsequent run.
- Repair: use configurable slower click/key intervals, retry vendor selection inside the shared function, wait for popup closure, and read the visible management Edit value through UIA without clicking it. Rebuild the grid clipboard from task rows, force a fresh purchase ERP session, and allow three seconds for the purchase entry screen.
- Live proof: two consecutive fresh-session #209 runs reported four clipboard rows and verified `컴퓨존` for rows 1, 3, and 4. The in-memory harness replaced the save call with `[DIRECT_STOP_BEFORE_SAVE]`; neither run sent Ctrl+S.
- Deployment: 13 server tests passed; production backup `C:\ERP_DB\backups\erp_vendor_state_20260826_141624`; backend/listener PID `3976`; version `1.0.232`; scheduler and lock healthy; server and local Agent hash `22cab9b29207b627bcd751e435e37fa1237ec52a64fe11e28a81918239685d4e`; local Agent PID `25036` is ready.
- Remaining safety boundary: inspect K-System before resetting #209 or #211 because older runs may have saved vouchers. Use the next new purchase case for full save/output acceptance.

## I-033 - 송명학 PC fixed coordinates differ despite equal resolution - resolved in 1.0.233

- Evidence: 송명학 Agent reports primary `DISPLAY1` at 1920x1080/125% and ERP `DISPLAY2` at 1920x1080/100% with virtual bounds `(-1920,-106)-(0,974)`. Previous #209 logs used maximized ERP bounds `(-1920,-106)-(0,926)` and absolute management clicks derived directly from that outer rectangle.
- Root cause: fixed points were anchored to the mutable outer window rectangle. Mixed-DPI extended desktops, taskbars, RDP reconnects, and DWM frame bounds can keep resolution constant while changing the physical screen origin by several pixels.
- Repair: re-enumerate the target monitor for each maximize phase, use its `rcWork` as the canonical canvas, record outer/client/work diagnostics, and calibrate form points from the live `cboAccUnit` center with a bounded 40-pixel correction.
- Verification/deployment: three geometry/wiring tests passed locally and on the server. Version 1.0.233 backup `C:\ERP_DB\backups\erp_coord_fix_20260826_153351`; exact bundle hash `50beb2aa9f3693a547556f7ea8c1fa480373a5119e186dbf62f84a29540b85a2`.

## I-034 - progress HTTP timeout blocked and failed ERP input - resolved in 1.0.234

- Evidence: prior #209 ended with `HTTPSConnectionPool(... Read timed out, read timeout=10)` propagated as `FORM-XY` failure. The 1.0.233 acceptance run stopped updating immediately after `PID 3180` and did not heartbeat again while the job remained ERP-running.
- Root cause: every logger message executed `_post(.../event)` synchronously on the same thread that drives K-System. A slow telemetry request therefore added up to ten seconds per log and its exception could escape into the ERP form logic.
- Repair: `_ProgressEventDispatcher` sends progress through a bounded daemon queue with a two-second network timeout. Submit is non-blocking, overflow keeps the newest event, network exceptions stay local, and queued progress is discarded before the authoritative completion/error POST.
- Regression coverage: slow HTTP, failed HTTP, late-progress rejection, two coordinate geometry cases, and runtime wiring all pass (6 tests). Production backup `C:\ERP_DB\backups\erp_coord_fix_20260826_154936`; version 1.0.234; backend PID `7508`; exact bundle hash `3fb9dfba25ec68add2c58ae5cbb39e5e398d1dc3739646ca5d715e51530bc71f`.
- Live containment: #209 remains `ERP대기` with no ERP voucher PDF. Its old 1.0.233 Agent task is still claimed and the remote PC exposes no management/RDP port. Do not enqueue another task until the old Agent/K-System process is ended and K-System is checked for an existing voucher.

## I-035 - 1.0.236 applied an account-unit displacement to every form click - rolled back

- Symptom: Song's #209 retry passed account-unit selection but clicked outside the accounting-date input and failed with `expected=2026-08-18, actual=회계일`.
- Root cause: calibration accepted an anonymous 166x28 ComboBox at X offset `-76` and assigned that value to `form_coord_offset_x`; `_form_point()` then added `-76` to every later coordinate. The date point moved from relative X `375` to `299`, which selected the static date label. Slip-unit success did not make the global-offset assumption valid because its input area was wider.
- Safety result: job `a45c2217-c7aa-4c78-91e9-57e915bc65e6` failed before grid entry and before Ctrl+S. No new ERP voucher PDF or output set was produced.
- Rollback: production and Song Agent are back on 1.0.235/hash `1900baa462be33af637905dec64e5c3d4ef64afa361f1d26532996b5f15e4674`; server tests `8/8`, health, single 8080 listener, and Agent readiness passed. Production backend PID is `7064`.
- Prevention boundary: do not reintroduce anonymous-anchor global calibration. The next repair must isolate live positioning to the account-unit selector, preserve all other coordinates, reject labels during value verification, and use moderate action/read-back pacing.

## I-036 - SmartBill PDFs looked like screen captures because portrait `print_page()` kept the preview whitespace - resolved

- Symptom: the saved PDF contained the correct invoice and extractable text, but the invoice occupied only roughly `y=55..350` on a portrait `612x792` page, leaving more than half the page blank.
- Root cause: SmartBill's official invoice is wide, while Selenium `driver.print_page()` emits portrait A4 by default. The crawler reached the correct `prt_prev.aspx` print view but did not normalize that layout.
- Repair: `_normalize_smartbill_pdf_layout()` unions visible text, drawing, and image bounds, adds six points of source padding, and places the clipped vector page into a landscape A4 target with a 24-point margin. Failure keeps the untouched source PDF.
- Verification: two unit tests passed; `#216/#217/#218` each became `842x595` with 132-134 extractable words. Visual QA showed only the electronic tax invoice, seals, table, and legal note—no browser chrome, ads, menus, or blank lower half.
- Deployment: source/download/output-set backups under `C:\ERP_DB\deploy_backups\20260831_smartbill_pdf_layout`; source hash `C556B4ADF9DE3408BA2E491755AD96B60677F1F002A0D490E76F3275FFD36207`; backend listener PID `5872`; HTTPS `200`.
- Graph maintenance: `graphify update .` refused a non-force overwrite at 1,430 new nodes versus 1,440 existing nodes. Preserve the current graph until missing chunks are recovered or an explicit force rebuild is approved.

## I-037 - SmartBill print-button check allowed unapproved invoices - resolved

- Symptom: invoices `#216/#217/#218` had valid-looking PDFs and completed ERP records, but the SmartBill document page still showed `수신 미승인`.
- Root cause: `_handle_approval()` returned success whenever an `인쇄` button was visible. SmartBill renders that button even with hidden `hdndtistatus=I`; its print JavaScript merely prompts for approval. The crawler's generic text/alert handling could dismiss that prompt and proceed to the print preview without committing receipt approval.
- DOM proof: the real controls are images `btnApprove02` and `btnApprove01`, both calling `fnApprove2_click('APPROVE')`. That opens `/xDti/common/popup/n_mem_Approve_layer.aspx`; the real confirmation button calls `fnConfirmClick('APPROVE')`, which invokes the synchronous status-change request and updates the parent status to `C`.
- Repair: select only those exact controls, process only the exact approval iframe action, require and re-check the canonical `I -> C` transition, close the success modal without its OK-button side effects, and independently block the PDF form POST for missing/`I` state.
- Production proof: live runs logged `수신 상태값: I` then `수신승인 완료 상태값: C` for all three invoice IDs. Their ERP rows stayed `처리완료`; no ERP retry occurred. Refreshed PDF sizes are `89,885`, `90,007`, and `90,859` bytes, with identical download/output-set hashes and clean landscape-A4 renders.
- Deployment: backup `C:\ERP_DB\deploy_backups\20260831_smartbill_receipt_approval`; source hash `71400F60D9605B98AD3A9FA9C71EE05234D04FEF797504CD59EC84464645B703`; five tests and compilation pass; Graphify rebuilt to 1,452 nodes/3,931 edges/75 communities; backend PID `5736`, HTTPS `200`.

## I-038 - SmartBill PDFs were incorrectly cropped and enlarged to landscape - resolved

- Symptom: production PDFs contained only the occupied invoice bounds enlarged across landscape A4. They did not match Chrome's original portrait print with full page whitespace and print header/footer.
- Root cause: `_normalize_smartbill_pdf_layout()` was added under the incorrect assumption that the blank lower area was unwanted. It unioned visible content bounds and replaced the original page with a clipped landscape page.
- Repair: the normalization hook is now a strict no-op. Final save uses CDP `Page.printToPDF` at `8.27 x 11.69` inches, portrait, with background graphics plus date/title and URL/page-number templates.
- Deployment-path containment: the server Desktop contains two similar project copies. Runtime evidence showed the one-off runner imports `C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version`; the first attempted copy targeted the non-operating directory and was stopped after the first validation exposed the old log marker. The non-operating copy was restored and the operating path was then deployed explicitly.
- Production proof: `#216/#217/#218` are one-page `595.92 x 841.92` portrait PDFs with title, SmartBill URL, and `1/1`; sizes are `152,890`, `153,339`, and `153,857` bytes. Each DB download hash equals its `02_*.pdf` output-set hash, and each DB row remains `처리완료`.
- Verification/deployment: five tests and compilation pass; backup `C:\ERP_DB\deploy_backups\20260831_smartbill_portrait_restore`; source hash `A0422B70BBF573A969CCAE17B720565EBDA9CA8D2AEF7B5AD13F39C04E7E6A13`; Graphify `1,455/3,936/76`; backend PID `10568`, HTTPS `200`.

## I-039 - SmartBill physical print dispatch verification (2026-08-31)

- Target resolution: Windows registered `평택 프린터 (172.16.10.172)` as `Normal` on port `172.16.10.172`; `김제 프린터` remained the default but was not selected.
- Dispatch proof: PDF24 Reader `/printTo` returned `0` for `#216`, `#217`, and `#218`; final target queue count was zero.

## I-040 - One deferred SmartBill mail filled the recent failure list - resolved

- Symptom: the dashboard failure group shows many `done 100%` purchase-mail collection rows with `실패 메일 1건 자동 재시도 대기`.
- Evidence: every listed one-minute job has `failed_count=0` and `deferred_count=1`. State contains only one failure key: Gmail UID `1087`, message ID `<6a8f9de5.5e3d45fe.65b1b.cc86SMTPIN_ADDED_MISSING@mx.google.com>`, dated `2026-08-27 11:15 KST`.
- Actual failure: 11th attempt ended `2026-08-31 06:38 KST` with `'charmap' codec can't encode characters in position 16-17`; 12-hour backoff schedules the next real attempt for `18:38 KST`. The collector merely records cooldown checks once per minute until then.
- Scope check: invoice `#219` completed ERP and two-file Pyeongtaek output; `#216/#217/#218` are separate processed message IDs. No evidence indicates multiple current invoice failures.
- Repair: `BaseTaxInvoiceHandler.process()` makes legacy stdout/stderr Unicode-safe with `backslashreplace`. Deferred event and completion text no longer contains `실패`, so the existing frontend classifier does not group successful cooldown checks as failures.
- Safety: production source, state, and SQLite DB were backed up at `C:\ERP_DB\deploy_backups\20260831_mail_retry_fix`. UID `1087` was fetched read-only first and checked for both exact-path and semantic duplicates before insertion. State clearing and IMAP read marking occurred only after invoice lookup succeeded.
- Live result: a transient SmartBill print-window closure was retried by the existing bounded retry path; the second fresh browser session succeeded. The invoice was inserted once as `#220`, with no semantic duplicate found.
- End-to-end proof: `#220` completed ERP input at 14:42, verified vendor management value `대신아이씨티(DS163)`, stored the ERP voucher PDF, and completed Pyeongtaek output job `2754a858-49b5-4311-bc65-14e6c3ea8641` with `2/2` Windows spooler submissions. Parent job `b4991887-08aa-4cc6-bf93-ad23728bd908` finished and sent the result email.
- Post-restart proof: consecutive automatic collector jobs report zero unread/new/failed/deferred items and finish with `구매 메일 수집 완료: 신규 대상 없음`; HTTPS health is `200`, version `1.0.237`.

## I-041 - 8080 disappeared while the backend task remained Running - resolved in 1.0.238

- Symptom: SSH and the server host were reachable, `AccountingWeb-Backend` reported `Running`, and Python PID `9720` remained alive, but no process listened on TCP 8080.
- Root cause evidence: at `2026-09-07 17:03:33`, asyncio's Windows `IocpProactor.accept()` raised `OSError [WinError 64]` and logged `Accept failed on a socket`. Mail collection continued every minute, preventing the `Start-Process -Wait` wrapper from returning and hiding the dead web listener from Task Scheduler.
- Recovery: wait for the current automatic collector to finish, end the wrapper, terminate only backend PIDs `9720` and `9304`, and rerun `AccountingWeb-Backend` from the verified active production root.
- Verification: `https://172.17.39.121:8080/health` returned HTTP `200` with `ok=true`, version `1.0.237`, production environment, and agent ERP mode.
- Prevention deployed: `AccountingWeb-Backend-Watchdog` runs as SYSTEM every minute, requires two consecutive HTTPS health failures, stops only the named task and exact `-m web_v1.backend` Python processes, restarts, and verifies HTTP 200. The external runner now pins the verified production root.
- Production proof: manual healthy-path execution returned `0`; the scheduled task reports `Ready` and last result `0`; `/health` returns v1.0.238 and the active listener PID command line matches `-m web_v1.backend`.

## I-042 - Song management-row retries could click the row below - resolved in 1.0.238

- Symptom: on Song's PC the relation popup intermittently opened for `가지급금(업체)` while the automation was processing the VAT row. The later wrong management value prevented voucher completion.
- Root cause: equal monitor model, resolution, and scale did not remove per-session ERP work-area and control timing differences. More importantly, management-summary recovery deliberately retried Y offsets `0, +4, +8, -4, -8`; on the slower Song session a late retry could cross the row boundary. Earlier form calibration could also propagate a detected account-unit vertical displacement to unrelated fields.
- Repair: `_erp_form_applied_offsets()` accepts only a trusted bounded X offset and always returns Y `0`. `_erp_management_summary_click_candidates()` preserves the exact management-row Y and changes only X. Existing default-focus vendor entry and the slower field-specific verification path remain intact.
- Verification: 6 focused tests, compilation, and production source invariants pass. Song heartbeat at `172.17.30.15` reports v1.0.238, exact production hash, and preflight success. No ERP replay was performed.

## I-043 - Local Agent updater reverted source edits - contained with isolated runtime

- Symptom: code patches in the editable worktree reverted within seconds while the local v1.0.237 Agent compared that dirty tree with the newer production bundle.
- Root cause: the operator Agent was launched directly from the development repository, so normal self-update copied the production payload over source and unrelated local work.
- Containment: stop only that Agent, finish and deploy from preserved source, then launch the exact v1.0.238 production payload from `%LOCALAPPDATA%\AccountingWebAgent\1.0.238`. Update the current-user startup and `accountingweb://start` commands to that isolated runtime.
- Proof: local `172.17.30.13` heartbeat now reports v1.0.238, exact hash `306e8b91adae798a83d7e12b963cf817d0e6cdcfc38e486987f6645632993469`, successful preflight, and the editable worktree remains unchanged.
