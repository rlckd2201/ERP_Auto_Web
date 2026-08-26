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
