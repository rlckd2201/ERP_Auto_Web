# TODO

## 2026-10-28 all-user243 rollout

- [x] Enable all named/login users including future accounts for shared purchase execution; preserve author/printer and no-fallback behavior.
- [x] Backup/deploy module and production wildcard config. Verify Song/Hyeon/Kim/reum routes to243 with fresh ready Agents.
- [x] Recover the exact pinned accounting runtime with missing listener; fix watchdog health endpoint without changing portal authentication/bridge.
- [x] Run59 Python and8 PowerShell regression checks; update Graphify.
- [ ] Observe a real user-triggered purchase after rollout; do not replay yesterday's completed277/278.
- [ ] Continue investigating Windows accept socket failure only if it recurs; guarded recovery handles the observed orphan state, but the underlying network event was not reproduced.

## 2026-10-27 purchase output correction (supersedes blockers below)

- [x] Make purchase approval attachment optional for output while preserving the three required accounting PDFs and missing-document visibility.
- [x] Verify automatic selected-printer queuing and one-click reuse without duplicate ERP; deploy backed-up105 module.
- [x] Confirm #2773/3 and #2784/4 print-queue acknowledgements; #278 department blocker is no longer current after its later successful user processing.
- [x] Confirm243/Hyeon updated and ready after deployment. Do not resubmit completed jobs.
- [ ] Physical paper receipt is not remotely verified. If still missing, inspect the Samsung device/queue first.
- [ ] Observe the next user-initiated missing-approval purchase under the deployed policy; fixture and production read-only selection checks passed, but no new print was generated for testing.

## 2026-10-27 v2 execution after actual TLS failure

- [x] Find/analyze16:32 repair report on Desktop; all23 Python imports pass, first repair stopped at verified HTTPS missingSKI error before Agent launch.
- [x] Reproduce strict TLS failure and verify Python3.11 HTTPS200; prepare/test/copy v2 ZIP without changing shared servers.
- [ ] Hyeon executes Desktop-delivered 현시훈_PC복구_v2.zip and returns the new repair_version2 JSON.
- [ ] Verify fresh105 Agent record and correct ownership/readiness. Original Agent-start failure and common portal502 are not fully explained or resolved by the repair-gate finding.

## 2026-10-27 execute targeted Hyeon repair

- [x] Prepare/test standalone repair and copy 현시훈_PC복구.zip to the current user's Desktop for forwarding.
- [ ] Hyeon executes AccountingWebRepair.exe on his PC and returns his Desktop AccountingWeb_Repair_*.json.
- [ ] Verify real import/HTTPS result and fresh105 Agent ownership/version/readiness; diagnose any remaining stage from recorded errors.
- [ ] Confirm portal recheck and printer/ERP prerequisites after enrollment. Do not mark recovered merely because the EXE was delivered or the process starts.

## 2026-10-27 actual Hyeon diagnostic follow-up

- [x] Receive/analyze Hyeon's16:18:41 report:254 files/registrations present, direct105 HTTPS reachable, Agent not running.
- [x] Check105: no fresh Hyeon registration; lastOct26 10:49:58/v250.
- [ ] Capture the actual selected Python, real imports/user-site and pip/startup failure metadata. Adjacent package-file absence alone is insufficient to establish the root cause.
- [ ] Repair the demonstrated local startup failure; require fresh254 heartbeat and readiness before declaring recovery.
- [ ] Keep common authenticated-portal502 investigation open separately.

## 2026-10-27 Hyeon recheck502 follow-up

- [x] Confirm common portal502 also occurs on Kim's connected PC and preserve current blank-screen fix.
- [x] Add and deploy bounded retries only for read-only setup status502/503/504;18 tests and normal live recheck pass.
- [ ] Obtain the diagnostic JSON generated on HYEON's Desktop, not this PC. User has been told the location and execution steps.
- [ ] Restore Hyeon's actual new Agent connection from that evidence; current .18 record is stillOct26/v250.
- [ ] Resolve the common gateway502 root cause. The frontend retry is resilience only;105 setup200 logs cannot locate the35 failure by themselves.


## 2026-10-27 14:56 portal blank-screen recovery

- [x] Identify actual script-load503, isolate the incompatible11:28 app.js change, and restore the purchase view.
- [x] Deploy response validation separately while retaining the portal-adapted app.js source;14 tests and live purchase/setup/printer/status checks pass.
- [x] Supersede the13:17 Storage Proxy handoff. That candidate is not the fix for this incident; no35 change is needed for the current recovery.
- [ ] Await Hyeon's actual replacement-PC diagnostic and verify its fresh Agent enrollment separately. Do not label that issue resolved from Kim's working PC.
- [ ] Investigate recurrent portal API503 separately if it continues: one setup-status warning occurred14:58:37 after the blank-screen repair. Do not reopen the fixed script-adaptation issue on this evidence alone.
- Next: monitor fresh portal status if the user reports recurrence; preserve request-helper source compatibility when planning subsequent releases.


## 2026-10-27 11:16 portal incident reopened

- [x] Reproduce/raw-HTML response parser defect; deploy static response validation with backup/hash guards and12 passingNode tests.
- [x] Provide tested read-only diagnosticEXE/ZIP for Hyeon's replacement laptop172.16.10.18. User will request execution; await its DesktopJSON result.
- [ ] Diagnose and restore Hyeon's Agent registration/connection from the actual result. Current record is old250/Oct26, and remote management ports are unavailable. Do not infer successful installation from download/execution alone.
- [ ] Obtain35 owner IIS502 substatus/Win32 error/time-taken around11:16-11:31; portal still intermittently502 while105/api/version responds200. No35 configuration change performed.
- [ ] Complete browser acceptance of the new cache-busted frontend once the portal loads, including stable status checks; then verify Hyeon setup readiness. Earlier10:52 UI recovery did not complete these checks.

## 2026-10-27 portal Agent repair and remaining portal-owner task

- [x] User authorized immediate fixes; implement verified-session Agent ownership while preserving separate accounting login.
- [x] Back up/deploy254; verify91 Python tests plus5 frontend checks, four254/exact/ready Agents, direct purchase screen, original243 routing/output ownership, unchanged financial states and healthy DB.
- [x] Prevent broken JavaScript from submitting login credentials into URL: form POST, submit disabled until handler registration, cache-busted frontend. Existing user password was not changed; user-controlled rotation is advisable after its observed URL exposure.
- [ ] Team lead managing172.16.19.35 must correct common portal runtime validation for applicationId it2-accounting-automation with registered basePath /accounting-automation. Preserve all other checks; inspect current source, back up and test. No35 management access or authority to message that person was supplied.
- [ ] After portal runtime repair, verify accounting password login actually reaches105, session header survives the portal envelope, setup resolves the user's private Agent, and the purchase screen/selected printer are correct. No actual business transaction is needed for this acceptance.
- [ ] Register/identify Hyeon's replacement laptop, verify its output readiness; only then close the remaining old121 redirect as previously authorized.

## 2026-10-27 public3010 completion and old-address cleanup

- [x] Confirm user-fixed205 accepts243 ->105:3010; redirect old121 address to3010 and recover243 automatically.
- [x] Back up/deploy253 canonical installer/default endpoint;68 tests pass locally/clean stage/server, full payload hash coverage verified, Graphify refreshed.
- [x] Verify four currently active Agents253/exact/ready on3010; shared purchase/regular executor243 and original output identity retained.163 financial states unchanged, SQLite/mail collection healthy, original UI byte-identical.
- [x] Close105:8081 externally by loopback-only backend binding and disabling its owned inbound allow rule.3010 remains healthy; its internal8081 dependency and unrelated8080 app preserved.
- [ ] Hyeon.18 Agent is offline on250/old121 endpoint. Observe its restart/update to253/3010 and output readiness. Old121 business tasks stay disabled;307 compatibility remains solely for remaining client transition.
- [ ] After that transition, stop/disable121 AccountingWeb-Migration-Bridge and verify8080 closed. User has already authorized this cleanup; preserve backups/data/SSH management.
- [ ] Observe next real user purchase/regular job through ERP/document/selected output device; no test voucher, historical replay or duplicate printing.

## 2026-10-27 confirmed243 firewall cause and public3010

- [x] Verify HTTPS3010 original-CA/healthy252, existing native-bridge frontend and underlying8081 backend; no service changes.
- [x] Query both FortiGates: Gimje243 matches enabled deny11 for3010/8081; normal .13 matches allow155;155 excludes243. HQ side accepts via117, return route exists. SSH management still22.
- [x] Inspect user-identified205: correctly enabled/accept/source243/TCP3010/before11, but destination object resolves172.16.10.105 instead of172.16.19.105. Paired lookups match205 only for10.105;19.105 still hits11.
- [ ] Correct205 destination reference to verified172.16.19.105/32 after authorization; preserve shared10.105 object and existing policies. Then test243 itself and align Agent endpoint to3010; require fresh252/exact hash/ready. No firewall change was made during diagnosis.
- [ ] Finish shared purchase/regular migration acceptance after243 reconnects; no historical invoice or print replay.

## 2026-10-26 actual105 backend acceptance

- [x] Obtain external SMTP RCPT250 on105; IMAP read-only login passes. Freeze121 at idle, seal final163-row snapshot, transfer/hash-check complete data, and activate105 public8081 with business workers alone.
- [x] Preserve original UI,121 recovery source/env/tasks/Startup links, existing account/output/printer ownership, and unrelated target8080 application. Old121 address now307 forwards directly to105; disable both old business tasks and former105 frontdoor.
- [x] Fix missing deploy Python in Agent update payload, deploy252 after backup, verify real package hash coverage and66 focused tests locally/on target; refresh Graphify.
- [x] Verify163 financial states/integrity/due-send dedup unchanged and natural new-server mail collection successful; three active personal Agents ready on exact252 bundle. Stop temporary capture/remove filter/restore firewall logging.
- [ ] Resolve243 ->105 TCP8081 timeout.19:15 NIC capture sees other three clients and no243 traffic; remote Chrome independently times out. Pending user firewall allow/deny policy match. Require fresh243252/exact bundle/ready before declaring shared purchase/regular processing accepted.
- [ ] Observe Hyeon's next normal Agent startup (pre-existing offline since10:49); preserve original output ownership and pre-existing printer mappings. Do not replay completed #267/#272/#275/#276 to test migration.
- [ ] After243 reconnects, finish read-only routing verification and observe the next genuine user purchase/regular work. Target backend retains Interactive Administrator/AtLogon startup; server login session remains an operational dependency.

## 2026-10-26 correct migration UI and retain working production

- [x] Remove unrequested custom preview and restore original application source/UI.
- [x] Serve105:8081 through a TLS forwarding-only service to existing121; preserve live data, request/client identity, source Agent URL and original printer/author ownership.
- [x] Confirm original root and all frontend assets exact; real login and20 purchase records render; current management PC setup ready.65 tests pass; Graphify refreshed after removing preview code.
- [x] Preserve121 source/config/backend/watchdog and target8080 unrelated app. Disable the copied target business backend and retain its163-row snapshot privately at future8082; no duplicate processing.
- [ ] Complete actual backend migration after external SMTP authorization and fresh private8082 acceptance. Adapt old phase scripts for current architecture/65 tests before executing any freeze/swap.
- [ ] Final-sync at idle, hand public8081 from frontdoor to the new backend, retain old source recovery files, then verify actual Agent/owner/printer/due/mail operation. Forwarding alone is not completed backend migration.

## 2026-10-22 shared purchase execution acceptance

- [x] Back up current operating source/config/DB/queue before implementation; validate backup integrity.
- [x] Enable only account tuy1120 on shared Agent 243; retain other users' routes and the original author/output destination.
- [x] Add shared-PC purchase timing, preserve task environment restoration/session cleanup, and block unreviewed post-save retries.
- [x] Pass 55 focused tests in working, focused-commit, and production staging; compile; deploy v250 with rollback copies and restored watchdog.
- [x] Confirmed updated 243/Song Agent bundle and ready state; real production routing and two unaffected users passed read-only checks.
- [ ] Observe the next genuinely new purchase through ERP save, voucher upload, report generation, and original-destination output. Do not use a previously saved/completed invoice as a test.
- [ ] Commit and push only this feature's source/docs/config delta; preserve existing unrelated dirty/deleted files.

## 2026-10-21 purchase expense report #272

- [x] Identify the current #272 report requests and correlate Agent done/upload events with later false timeout logs.
- [x] Reproduce the existing handler's 120-second HTTP 408 with a completed Agent job and nested report path, without production side effects.
- [x] Inspect the existing PDF in full and reproduce valid 2026-10-20 becoming 2026.01.00 in the expense date formatter.
- [x] After explicit user approval, fix current-request completion/path detection and calendar-valid date display while preserving unrelated output_set.py changes.
- [x] Pass 28 focused tests in the working tree and clean focused stage; pass 13 new tests on server, compile, and update Graphify.
- [x] Recover SSH using the existing management rule scoped to old/current work PCs; close the user's RDP connection; back up and deploy v1.0.249, restoring the watchdog.
- [x] Verify the target Agent's exact final bundle and regenerate #272 once through the real endpoint: HTTP 200 in 37.61 seconds, done job eddcbb1e-442e-4e03-b819-2815d0f94801.
- [x] Inspect the corrected native PDF in full and synchronize only its output-set copy: valid 2026.10.20 date, author 현시훈, 193,100 amount. No ERP replay/additional print was performed.
- [ ] Observe the next natural user-initiated expense generation; track the separate #272 ERP failure independently of this completed document fix.

## 2026-10-12 Daou date repair

- [x] Identify #259, reproduce the date parser failure from the real PDF, and correlate ERP failure with the false noon missing alert.
- [x] Confirm the original date visually and verify no grid/save phase was reached in the failed automatic job.
- [x] Check recent regular invoices and demonstrate correct received status on an in-memory repaired copy.
- [x] Obtain approval for the proposed implementation/deployment/recovery scope and the original 243 PC target.
- [x] Correct date token boundaries and require valid calendar dates; pass 12 focused tests locally/on server.
- [x] Back up production/SQLite/#259, deploy v1.0.248, restore the source-grounded date, and verify Daou due status is received.
- [x] Fix self-update installation-root handling, pass three focused tests plus PowerShell parsing, and isolate the current-PC Agent from the editable repository.
- [x] Submit one #259 retry `d91c7b9c-958f-4c17-8ff5-33e6fa4aeff1` to the chosen 243 Agent with Pyeongtaek output.
- [ ] Verify 243 reconnects on the final v1.0.248 bundle, then confirm that existing job completes ERP save, voucher PDF, and two-file output. Do not submit another retry.
- [ ] Confirm the next real vendor alert uses valid date evidence and does not repeat the false Daou request.

Updated: 2026-08-25

## P0 - Zoom expense-report generation failure

- [x] Identify Zoom `#212` as an Excel `PageSetup.PaperSize` COM failure rather than a queue dependency on Etech.
- [x] Continue export when the active printer driver rejects the A4 setter and normalize the resulting PDF to exact portrait A4.
- [x] Limit failed automatic Zoom retries to one attempt per 600 seconds while leaving manual requests immediate.
- [x] Pass 11 focused tests locally and on the operating server, then deploy to backend PID `7484` and update target Agent `DESKTOP-55LQ6BN-TEST`.
- [x] Complete live generation job `5064f4ad-67e8-48c3-82d3-9918e03c5f62` and visually verify the one-page A4 report.
- [x] Complete one Pyeongtaek output job `2477e07e-9807-4464-b091-330910d4302c` with the two required files and `2/2` spooler success.

## P0 - Gemini purchase-document analysis

- [x] Rotate the production Gemini API key without adding it to source or Git.
- [x] Migrate purchase analysis from `google-generativeai` to the maintained `google-genai` SDK.
- [x] Make the model configurable and set production to `gemini-3.7-flash`.
- [x] Use the Windows certificate store for Google API TLS validation on the operating server.
- [x] Pass 13 focused tests, SDK model lookup, live JSON generation, backend health, sole-listener, and scheduler-lock verification.
- [x] Compare three existing tax/quote pairs against the historical 2.5-era results; 3.7 matched all totals and corrected the `#159` package/order quantity ambiguity.
- [x] Copy Korean-named PDFs to ASCII temporary upload names inside `_ai_parse`, guarantee local/remote cleanup, and add success/failure regression tests.
- [x] Deploy the filename fix and run Korean-named `#208` through the exact production function without writing analysis back to the invoice DB.
- [ ] Add a deterministic non-zero discount-line case and define whether the discount is allocated across goods or retained as an explicit adjustment.
- [ ] Observe the next genuinely AI-required purchase document and confirm its persisted analysis model is `gemini-3.7-flash`.

## P0 - expense-report author identity

- [x] Correct `#206` and `#207` from `reum` to `구름`.
- [x] Regenerate and individually save both cash-disbursement PDFs.
- [x] Verify `작성자 구름`, one-page A4 rendering, and absence of `reum`.
- [x] Print both corrected reports to the mapped Pyeongtaek printer and verify `2/2` spooler submissions.
- [x] Implement backend authenticated-user ownership and regression tests so login IDs/display names resolve canonically and Agent IDs do not overwrite document authors.
- [x] Deploy the corrected source on 121 and verify server health/source hashes after restart.
- [x] Regenerate `#176`, `#179`, `#180`, and `#205`, verify canonical authors, preserve `#205`'s existing ERP error, and confirm four Pyeongtaek spooler submissions.

## P0 - cash-disbursement PDF layout

- [x] Identify the oversized `$A$1:$R$42` print area that included 22 empty rows and shrank the form.
- [x] Confirm the required output direction is portrait and deploy portrait A4 plus actual `$A$1:$R$20` print area to 121 and both generation Agents.
- [x] Regenerate `#176`, `#179`, and `#180`; verify one-page `595.20 x 841.68` portrait output and canonical authors.
- [x] Stop additional printing after the direction correction; final regeneration completed with `print_skipped=true`.

## P0 - duplicate noon regular-due email

- [x] Identify the second `[누락]` message as a stale copied backend sender; the canonical 121 message uses the correct server URL/current state.
- [x] Add an explicit-enable plus canonical-hostname guard and focused tests.
- [x] Deploy the guard to 121/Agent-distributed sources.
- [x] Trace same-host orphan workers (`3836`, `3748`), remove their inherited loopback listeners, and replace the obsolete startup link.
- [x] Deploy the cross-process sender lock and verify backend PID `9940` is the only 8080 listener and lock owner.
- [ ] Verify only one message arrives at the next 12:00 run.

## P0 — WEHAGO native PDF incident

- [x] Restore the target WEHAGO mail to retryable unread state and force live collection.
- [x] Keep the Duzon print runtime alive and wait for its delayed preview.
- [x] Detect the preview without scanning the Chrome UI tree.
- [x] Drive PDF and Save As through server-session Win32 controls.
- [x] Block Chrome/Skia web-page PDF fallback.
- [x] Deploy to operating server 1.0.228 and complete a live retry with zero failures.
- [x] Retrieve and compare the server PDF against the manual normal reference.
- [ ] Observe the next genuinely new WEHAGO mail to confirm the new-row path; the repaired duplicate/replacement path is already verified.

## P0 — repository consistency

- [x] Restore `web_v1/frontend` from verified current sources without reverting later UI behavior.
- [x] Restore `AccountingWebRequiredSetup.cs/.exe` from Git HEAD.
- [x] Include the verified current `web_v1/backend/zoom_billing.py`.
- [x] Confirm static import/serve dependencies and required installer artifacts.

## P1 — documentation and graph

- [x] Make current version and architecture authoritative in the root documentation.
- [x] Mark the ERP RFP as target-state procurement scope, not current implementation.
- [x] Record that U+ is active in current routing while older exclusion notes are historical.
- [x] Keep mojibake-heavy historical logs out of the current handoff path.
- [x] Configure supported Graphify exclusions and regenerate the active graph.

## P2 — verification and handoff

- [x] Run Python syntax checks for the affected backend/Agent/crawler entry modules.
- [x] Run frontend JavaScript syntax and DOM-reference checks.
- [x] Verify required frontend, installer, Zoom, version, and Graphify artifacts.
- [x] Review diffs and update all compact session documents.
- [x] Run live FastAPI restart/health, Agent update/queue, Excel generation/upload, output-set, printer, and spooler verification.
- [ ] Verify installer download and a controlled non-duplicating ERP GUI cycle when a safe test case is available.

## Remaining item acceptance condition

Remaining acceptance: confirm one regular-due message at the next real noon run, installer download, and one safe ERP GUI cycle. `/health`, regular-due lock ownership, Agent claims, Excel generation/upload, output-set completion, and Pyeongtaek spooler submission are live-verified.

## Repository integration

- [ ] Reconcile `codex/reconcile-state-20260812` with latest `origin/main` after confirming how the local WEB/Agent 1.0.228 line relates to the independently added `excel_voucher_web` line.
- [ ] Regenerate Graphify after that integration; do not carry either side's graph outputs across the merge without rebuilding.

## Executive PPT draft (2026-08-25)

- [x] Create a concise 14-slide PPTX covering the requested executive and operator topics.
- [x] Use actual mail, dashboard, history, quote-discount, DB, and error-log screenshots.
- [x] Calculate conservative time savings from a read-only 100-invoice operating snapshot and label assumptions clearly.
- [x] Estimate realistic external build and annual maintenance ranges using official 2026 applied-SW wage data.
- [x] Open the PPTX in PowerPoint, export all 14 slides at 1600x900, and visually inspect every slide.
- [ ] Replace the assumed per-case times with measured operator data after a short time study.
- [ ] Apply approved logo/brand colors and executive feedback in v0.2.

## Executive PPT revision v0.2 (2026-08-25)

- [x] Rebuild as a concise 12-slide executive narrative with one-line titles.
- [x] Capture clean mail, history, and quote screens without browser chrome.
- [x] Remove error-log/retry slides and emphasize ERP plus complete document-set output.
- [x] Add actual ERP voucher and cash-disbursement report evidence.
- [x] Add annual direct-labor saving and realistic external replacement-value ranges.
- [x] Reopen in PowerPoint, export all slides, and complete full-size visual QA.
- [ ] Replace planning-time assumptions after a measured operator time study.

## Executive PPT revision v0.3 (2026-08-25)

- [x] Exclude system waiting time and use one minute of operator hands-on time per case.
- [x] Apply 240 regular and 250 purchase cases per year.
- [x] Recalculate annual time saving to 217.7 hours and 96.4%.
- [x] Use the official 2026 minimum wage of KRW 10,320/hour.
- [x] Move external rebuild/maintenance estimates to a clearly separated appendix.
- [x] Render, visually inspect, and reopen all 13 slides in PowerPoint.
- [ ] Confirm the actual annual current-system operating cash cost for a final break-even judgment.

## Executive PPT revision v0.4 (2026-08-25)

- [x] Remove the duplicated slide-3 cost/time summary.
- [x] Merge the executive summary and system-flow concepts into `원클릭 회계처리`.
- [x] Shorten all slide titles to concise function or section names.
- [x] Reduce the deck to 12 slides without removing required feature, manual, time, cost, or external-build content.
- [x] Reopen and render all 12 slides in PowerPoint and verify every title remains on one line.

## Invoice #209 Compuzone diagnosis (2026-08-26)

- [x] Inspect invoice `#209` and both failed production job timelines without mutating production state.
- [x] Trace the `가지급금(업체)` vendor value from purchase payload through the management-item popup automation.
- [x] Separate the unverified vendor-selection defect from the terminal ERP PDF-output failure.
- [ ] Before retrying, check K-System for vouchers saved by either failed job to prevent duplicate posting.
- [x] On explicit fix approval, require row-scoped popup activation plus exact business-number result verification and propagate RD Viewer/print-dialog timeouts as immediate failures.
- [x] Review purchase-task verification and timing separately; preserve company/unit/date correctness checks while removing redundant scanning and synchronous progress noise.

## Invoice #209 purchase ERP safety/performance fix (2026-08-26)

- [x] Back up all directly modified source/version files with SHA-256 verification.
- [x] Add a purchase-only fast profile for ordinary operator PCs while preserving the 243-PC `regular_auto` profile.
- [x] Replace blind vendor-popup keyboard navigation with an exact business-number result match.
- [x] Make RD Viewer, print-dialog, and PDF-save failures fatal at their source.
- [x] Block direct retries after a post-save output failure until K-System is checked and the operator explicitly resets the invoice to waiting.
- [x] Add regression tests, compile changed Python files, run the full discovered `web_v1` test set, and update Graphify.
- [x] Deploy version `1.0.229`, restart the backend and local ERP Agent, then verify the production Agent bundle hash.
- [ ] Check K-System for already-saved #209 voucher(s) before any retry; do not use #209 as an unattended acceptance test.
- [ ] Observe one safe new purchase job and confirm the live vendor result grid is exposed by UI Automation as an exact business-number cell.

## Purchase fast-profile regression (2026-08-26)

- [x] Correlate the two post-deployment #209 jobs with Agent, client IP, K-System PID, and exact failure phase.
- [x] Confirm the first failure occurred immediately after the 회계일 click and the retry continued with a disconnected UIA wrapper.
- [x] Remove global fast input and critical-field verification skipping from interactive purchase tasks.
- [x] Add bounded K-System window/UIA reconnection after critical header transitions and fail before Ctrl+S if read-back cannot be restored.
- [x] Add regression tests for COM/UIA invalidation at 회계일 and management-popup entry.
- [x] Back up, verify, deploy 1.0.230, and confirm bundle hashes without replaying #209.
- [ ] Check K-System for any voucher created by the earlier pre-1.0.229 Ctrl+S attempt before resetting or retrying #209.
- [ ] Observe one safe new purchase case on an ordinary operator PC; confirm header read-back, exact vendor selection, and one-time document-set output.

## Invoice #209 vendor-popup restoration (2026-08-26)

- [x] Back up the 1.0.230 source/version files before modification.
- [x] Inspect the live K-System vendor popup and prove that result rows/cells are not available through UI Automation.
- [x] Remove the failed search-Edit click and exact-result UIA scan paths.
- [x] Restore the proven default-focus keyboard sequence while retaining stale-popup closing and header/save guards.
- [x] Disable purchase-only fast management timings while retaining fast menu navigation and leaving `regular_auto` unchanged.
- [x] Run invoice #209 directly to a hard pre-save stop; confirm rows 1/3/4 complete and row-4 `가지급금(업체)` visibly contains `컴퓨존` without sending Ctrl+S.
- [x] Deploy 1.0.231 with production backup/rollback, server tests, health, scheduler lock, listener, Agent version, and exact bundle-hash verification.
- [ ] Check K-System for vouchers from the older pre-1.0.229 Ctrl+S attempts before any #209 reset or retry.
- [ ] Observe the next safe new purchase case through one-time document-set output.

## Invoice #209 intermittent vendor hardening (2026-08-26)

- [x] Inspect the latest #209 and #211 production logs without replaying either invoice.
- [x] Apply the same bounded vendor selection retries to VAT and advance-payment rows.
- [x] Require popup closure plus actual visible management-value read-back before success.
- [x] Slow only the purchase row/popup/key transitions that were skipping focus; leave the 243-PC regular profile unchanged.
- [x] Rebuild ERP grid text from authoritative task rows and force a fresh purchase ERP session.
- [x] Extend purchase menu/new-form readiness waits for slow consecutive K-System launches.
- [x] Pass compilation, 13 tests, focused diff checks, Graphify update, and two consecutive direct #209 pre-save runs.
- [x] Deploy 1.0.232 with hash-pinned backup/rollback and verify server health, scheduler lock, listener, Agent readiness, version, and exact bundle hash.
- [ ] Check K-System for prior #209/#211 vouchers before any reset or retry.
- [ ] Observe one new safe purchase case through one-time document-set output.

## 송명학 PC 좌표/지연 보정 (2026-08-26)

- [x] 송명학 PC의 실제 다중 모니터 좌표와 DPI 구성을 운영 Agent heartbeat에서 확인한다.
- [x] ERP 고정좌표를 매 실행 갱신한 대상 모니터 작업영역 기준으로 계산한다.
- [x] 신규 전표 폼의 실제 회계단위 컨트롤을 기준으로 작은 자리별 편차를 보정한다.
- [x] 진행 로그 HTTP 전송을 ERP 키 입력/클릭 스레드에서 분리하고 느린/실패 HTTP 회귀 테스트를 추가한다.
- [x] 운영 1.0.234를 백업·해시검증·6개 테스트·헬스체크와 함께 배포한다.
- [ ] 송명학 PC에서 멈춘 1.0.233 Agent/K-System을 종료하고 Agent 1.0.234 재접속을 확인한다.
- [ ] K-System에서 #209 기존 저장 전표 유무를 확인한 뒤 claimed 큐와 invoice 상태를 안전하게 정리한다.
- [ ] 중복 위험이 없는 1건으로 실제 좌표 캔버스/앵커/거래처 입력/전표 PDF까지 최종 확인한다.

## Invoice #209 coordinate rollback and next repair (2026-08-27)

- [x] Stop the failed 1.0.236 #209 job before ERP save and leave the invoice in error.
- [x] Roll production and the Song operator Agent back to 1.0.235; verify version, bundle hash, health, and eight regression tests.
- [x] Restore the editable worktree to the exact 1.0.235 source hashes and rebuild Graphify.
- [ ] Implement 1.0.237 with account-unit-only live positioning and no form-wide coordinate offset.
- [ ] Use moderate field-specific pacing; require ERP read-back after account unit, slip unit, date, and each vendor management value.
- [ ] Add tests proving Song's account-unit X difference cannot move date, grid, or management coordinates and that a `Text` label cannot satisfy field verification.
- [ ] Perform no-click coordinate diagnostics before any live retry; run #209 only during an explicitly approved operator test window.

## SmartBill clean PDF output (2026-08-31)

- [x] Inspect the signed-in SmartBill invoice and confirm the official print-preview endpoint.
- [x] Preserve vector text/lines/seals while cropping the occupied invoice region and fitting it to landscape A4.
- [x] Add focused layout tests and compile the changed crawler module.
- [x] Visually inspect the transformed `#216`, `#217`, and `#218` PDFs.
- [x] Back up and deploy the crawler change to the 121 server.
- [x] Back up and normalize the three production download PDFs and their output-set copies without rerunning ERP.
- [x] Verify backend task/listener and HTTPS `200` after deployment.
- [ ] Observe one new SmartBill mail end to end and confirm the future-crawl path produces landscape A4 without manual normalization.

## SmartBill receipt approval (2026-08-31)

- [x] Prove that the print button is present while canonical `hdndtistatus` is still `I`.
- [x] Identify the actual approval controls: `btnApprove01/02`, approval iframe, and `fnConfirmClick('APPROVE')`.
- [x] Require an `I -> C` status transition before parsing, PDF saving, or later processing.
- [x] Block the official print form POST when status is missing or still `I`.
- [x] Back up production source and the three existing download/output PDFs.
- [x] Approve `#216/#217/#218` on SmartBill without rerunning ERP and refresh only their PDFs.
- [x] Verify 5 tests, compilation, landscape-A4 visual QA, matching download/output hashes, backend task/listener, HTTPS `200`, and Graphify update.
- [ ] Observe one new SmartBill mail end to end and confirm the log records status `C` before the first PDF print request.

## SmartBill portrait print correction (2026-08-31)

- [x] Confirm the user-authoritative target is Chrome's full portrait A4 print, including blank lower page and native-style header/footer.
- [x] Disable occupied-region cropping and landscape enlargement.
- [x] Generate PDFs through Chrome CDP with A4 portrait dimensions and date/title/URL/page-number header/footer fields.
- [x] Reprint `#216/#217/#218` without rerunning ERP and copy the exact files to the user's local Desktop.
- [x] Verify all three are one-page portrait `595.92 x 841.92`, contain title/source/page fields, and match their output-set copies by SHA-256.
- [x] Verify five tests, compilation, backend PID/listener, HTTPS `200`, and Graphify update.
- [ ] Observe one new SmartBill mail end to end and confirm the stored/output PDF remains the full portrait print artifact.
- [x] Send the verified `#216/#217/#218` portrait PDFs, one copy each, to `평택 프린터 (172.16.10.172)` and confirm the queue drains.
- [x] Repair UID `1087` with encoding-safe console output, exact/semantic duplicate checks, and failure-state clearing only after successful DB registration.
- [x] Prevent cooldown-only completed mail jobs from repeating under the failure-log group by removing the failure keyword from deferred event/notification text.
- [x] Complete invoice `#220` through ERP entry, voucher PDF storage, two-file Pyeongtaek output, spooler verification, and result email.
- [x] Verify post-restart mail jobs complete with zero failures and no deferred-failure wording.

## 2026-09-09 backend/socket and Song-PC follow-up

- [x] Identify why task state was `Running` while 8080 was unavailable (`WinError 64` killed the accept socket; background mail thread kept PID `9720` alive).
- [x] Recover 8080 with a clean backend-only restart and verify HTTPS `/health` returns `200` on production `1.0.237`.
- [x] Add listener-aware supervision; process/task presence alone must not count as backend health.
- [x] Make ERP form calibration X-only and force management summary retries to keep the exact same Y coordinate.
- [x] Add regression tests and deploy WEB/Agent v1.0.238 after a production backup.
- [x] Rotate the user-supplied Voucher Automation API key only in the production secret environment; never commit or document its value.
- [x] Confirm Song, 243 regular, and local operator Agents report v1.0.238, the exact production bundle hash, and successful preflight.
- [ ] Observe one genuinely new Song purchase voucher end to end; do not replay an existing voucher for acceptance.

## 2026-09-09 Compuzone September 7 mail check

- [x] Locate both Compuzone messages in Gmail, including All Mail, without changing read state.
- [x] Confirm both are payment confirmations for orders `28692792` and `28682826`, not tax-invoice messages.
- [x] Confirm there is no tax-invoice attachment, portal link, or separate Compuzone tax-invoice mail through September 9.
- [ ] On receipt of the official tax-invoice mail/PDF, verify it creates two distinct purchase rows and attaches the matching order context.

## 2026-09-09 purchase-page loading latency

- [x] Separate browser/network latency from production loopback API latency.
- [x] Confirm invoice list construction is about 40 ms and is not the primary delay.
- [x] Identify the synchronous `3,615`-file ERP queue scan inside the async Agent claim endpoint as the repeating 1.75-1.99 second event-loop blocker.
- [x] Replace full historical queue scans with actionable-task indexing/filtering and offload unavoidable filesystem work from the event loop.
- [ ] Load health, jobs, mail status, and invoice data concurrently after the application shell is visible.
- [x] Verify sub-second health/list responses with all four currently active Agents polling, back up production, and deploy v1.0.239.
- [x] Preserve all completed/error/stale JSON audit records and the claimed-output 120-second recovery path.
- [x] Verify exact deployed hashes, HTTPS v1.0.239 health, zero mail failures, and exact bundle-hash/preflight status from all four active Agents.

## 2026-09-14 243PC 정기처리 오류 복구

- [x] 운영 정기 목록의 실패 건을 전수 확인하고 ERP 저장 전 실패만 선별했다: #231, #232.
- [x] 243의 실제 실패 화면과 UI 요소 위치를 서버에 보존해 증빙→통화 오입력과 거래처 표 밖 클릭 원인을 확인했다.
- [x] 검증된 243 이동형 폼의 증빙·관리항목 입력 좌표를 수정하고, 거래처 값 검증 실패 시 저장을 막았다.
- [x] 소스·환경 백업 후 v1.0.247 배포, 243 Agent 해시 일치, 정적 회귀 12건과 Graphify 업데이트 확인.
- [x] #231 및 #232의 ERP 저장과 평택 문서 2/2개 출력 완료 확인. 정기 목록 90/90 처리완료, 오류 0건.
- [ ] 다음 신규 정기 D1건을 자연 실행으로 관찰하고 다른 공장/폼 배치는 별도 진단 후 확장한다.
