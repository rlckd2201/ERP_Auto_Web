# TODO

Updated: 2026-08-24

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
