# TODO

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
