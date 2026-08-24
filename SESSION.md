# Session

Updated: 2026-08-24

## Current objective

Keep the 1.0.228 operating server reliable: native WEHAGO PDFs, one canonical noon alert, canonical document authors, and resilient portrait-A4 cash-disbursement PDFs.

## Status

The Zoom Excel-PDF repair is deployed on `172.17.39.121`. Server health is good on version `1.0.228`; backend PID `7484` is the only port-8080 listener and owns the cross-process regular-due sender lock. Zoom `#212` generated its missing report and completed one `2/2` Pyeongtaek output job. The next real 12:00 run remains the final operational observation.

## 2026-08-24 Zoom expense-report recovery

- Zoom `#212` was not blocked behind Etech. Its automatically queued expense-report jobs repeatedly failed because the active Excel printer driver rejected `PageSetup.PaperSize = xlPaperA4` with COM error `-2146827284`.
- Excel page setup now treats that driver-specific setter as optional, preserves portrait orientation, print area `$A$1:$R$20`, and one-page fit, then vector-normalizes any non-A4 result to exact portrait A4.
- Automatic Zoom generation retries are limited to one attempt per 600 seconds after a queue/failure timestamp; manual requests remain immediate.
- Local and operating-server verification passed 11 focused tests. Deployment completed at `2026-08-24T09:51:02`; backup `C:\ERP_DB\backups\zoom_expense_fix_20260824_095043`, backend PID `7484`, bundle hash `5c25d508c1471269ad3230704e860a979ec2c89c897b2c94cca228ce26ffa536`.
- Target Agent `DESKTOP-55LQ6BN-TEST` reported that exact bundle hash before the live retry.
- Generation job `5064f4ad-67e8-48c3-82d3-9918e03c5f62` completed at 09:55:22. The server report is 31,746 bytes, SHA-256 `E884180C886685DB3D420BB50445AFFA0BE7F741773B034F2D845368BA0B2ED2`, one exact `595.28 x 841.89` portrait-A4 page, and the rendered form has no clipping or overlap.
- Output job `2477e07e-9807-4464-b091-330910d4302c` completed at 09:56:25: the Zoom billing PDF and cash-disbursement PDF were each submitted once to `평택 프린터 (172.16.10.172)`, with `2/2` success and two verified Windows spooler submissions. Invoice `#212` is now complete.

## 2026-08-24 duplicate-noon-sender repair

- Mail source inspection tied the stale message to PID `3836` on `WIN-2H29RFPBUMN`, so the canonical-host check alone could not stop the duplicate.
- The server contained two generations of orphaned multiprocessing workers. PID `3836` inherited a listener from dead parent `1696`; PID `3748` inherited the remaining `127.0.0.1:8080` listener from dead parent `10128`.
- Both stale workers were stopped, the obsolete Common Startup link was moved recoverably to `C:\ERP_DB\backups\duplicate_due_fix_20260824_083859`, and one canonical startup link now targets the Administrator project.
- The scheduler now acquires `C:\ERP_DB\regular_due_sender.lock` before starting. Status exposes its lock owner, and outgoing mail records sender host/PID headers for future attribution.
- Final exact-source deployment completed at `2026-08-24T08:47:59`; backup `C:\ERP_DB\backups\duplicate_due_fix_20260824_084742`, backend PID `9940`, six focused tests passed, import passed, and the final listener set is only `0.0.0.0:8080 / PID 9940`.
- No test email was sent. Acceptance remains observation of exactly one message at the next real noon run.

## 2026-08-21 deployment and repair

- Global authenticated-user document-author resolution is live in `app.py`, `setup_state.py`, `worker.py`, and `models.py`. Full login IDs, exact display names, and unique legacy prefixes resolve canonically; Agent/machine IDs no longer become authors.
- The noon alert is live only when explicitly enabled on canonical host `WIN-2H29RFPBUMN`. The next real 12:00 run still needs observation to confirm that only one message arrives.
- Main deployment completed at `09:54:20`; backup `C:\ERP_DB\backups\document_actor_fix_20260821_095410`, backend PID `7608`, import/database checks passed, and six focused tests passed.
- Historical repair completed for `#176=구름`, `#179=구름`, `#180=김기창`, and `#205=현시훈`. Old reports were backed up; `#205` retained status `오류` and ERP was not rerun. Initial repair printing verified `4/4` spooler submissions.
- PDF QA found that print area `$A$1:$R$42` included 22 empty rows and shrank the form. The user confirmed the required physical output direction is portrait, not landscape.
- Final global layout is `A4 portrait`, print area `$A$1:$R$20`, one page, width `595.20`, height `841.68`. Deployed helper SHA-256: `1C1DE7EBD4DBA4EEE4221760DD7AAEF2388EECC88909A1255F7536008BF27C9F`; final backend PID `7360`.
- Both generation agents (`reum-reum`, `김기창-김기창`) reported current bundle hash `0e098d8e0aae449d15667d2b161d67eba49bd8d70e4cfd7c795b5d0a718db608` before regeneration.
- The interim landscape print job `ab3d3fc6-8351-4586-9e91-2a0c9e206452` completed `3/3` but was superseded after the user clarified that portrait output is required.
- Final portrait reports were regenerated without ERP or printing at `10:29:45`. Server validation passed for `#176`, `#179`, and `#180`: portrait one-page A4, authors `구름`, `구름`, and `김기창`, and `print_skipped=true`. No additional sheets were submitted after the direction correction.
- `#205` remains `오류 / 현시훈 / 기존 ERP 처리 오류 유지`; `#206` and `#207` remain `처리완료 / 구름` and were not duplicated in the final layout pass.

## Expense-report correction (2026-08-14)

- Root cause: the frontend sent the hard-coded processor `WEB v1.0`; backend fallback reduced Agent ID `reum-reum` to `reum`, so the document author was not resolved from login user `reum0009` to display name `구름`.
- Corrected rows: `#206`, `#207`; both now expose `processor=구름` and `expense_author=구름`.
- Regenerated uploads: `codex-expense-author-206-da729432-7f93-4a30-ad89-95c853af3cc3` and `codex-expense-author-207-a83ceb8d-1ee5-44e7-956a-4d96c79ae7bb`.
- Server files: `C:\ERP_DB\expense_reports\206\04_현금출금결의서.pdf` and `C:\ERP_DB\expense_reports\207\04_현금출금결의서.pdf`; prior copies remain as timestamped `pre_regen` backups.
- Individual PDF-save job `34e81b82-6e0a-460f-825b-f8af9a67ddc4` completed for both reports.
- Print job `3ef76859-c824-421d-96fa-4ecb493e6d3f` completed `2/2`; Windows spooler submission was verified for both one-page A4 reports.
- QA copies: `output/pdf/expense_report_206.pdf` SHA-256 `ca7c23c85ab44ef3b90a09e4f0e70c55dfd1603411ed04f45825b237009438e2`; `output/pdf/expense_report_207.pdf` SHA-256 `84733a46829340da42a20fc2bfa699e0dd07e59c07d3ba72605dfb02a919d6e9`. Both contain `작성자 구름` and no `reum` text.
- Permanent source fix is deployed: authenticated user identity is canonicalized server-side and machine/Agent IDs are rejected as authors.

## WEHAGO incident resolution (2026-08-14)

- Root cause: the crawler treated a late Duzon preview as absent, scanned the Chrome UI tree before checking the preview title, and mishandled the native Save As workflow.
- Fix: keep `WehagoPrint.exe` alive, detect the preview by title, click the native PDF control in the server session, skip the obsolete extra print click when Save As opens directly, and use synchronous Win32 messages for filename/save controls.
- Production deployment: 1.0.228 source commit `e0a8ebf`; verified deployment PID 11160 and SHA-256 `164fc90d2cbaa106cb5d01cff0d84f3762fd4a17f1121edeb23f73a786b8e5e6` for `portal_wehago.py`.
- Live retry job `0f382cd4-db29-4225-980f-0f0930c22aa0`: target 1, failures 0, duplicate 34. The target invoice was correctly recognized as existing invoice ID 198.
- Retrieved server PDF: 169,685 bytes, one page, Producer `Developer Express Inc. DXperience (tm) v15.1.7`, approval `20260810-41000096-48917566`, management ID `TX2026083821631`, SHA-256 `ea779d542a293ed4c7d263360e79924a662f5e657230292fd810d7e40f363afb`.
- Manual-normal comparison: same producer, page count, identifiers, and extracted text length; no WEHAGO web-status markers; 2x rendered pixel RMS below 0.102 per channel.
- Focused fixes and deployment updates are published through remote commit `9d9f9b6`.

## Current baseline

- Active product root: `web_v1`.
- Actual WEB/Agent version: `1.0.228`.
- Architecture: operating-server FastAPI coordinator plus manager-PC Agent for ERP GUI, Excel, and printer work.
- Active crawler package: `tax_crawler`; ERP execution dynamically reuses the manager v6.2 source under `manager_server`.
- U+ routing is active. The ERP API/DB RFP describes a future target state, not the current GUI-Agent implementation.
- The worktree still contains extensive unrelated user changes; they remain preserved and outside this task's release scope.

## Completed in this session

- Restored the complete static frontend, preserving the newest verified `index.html` and `app.js` behavior.
- Restored the required setup `.cs/.exe` artifacts from byte-identical Git content.
- Included the verified `web_v1/backend/zoom_billing.py` imported by `mail_collector.py`.
- Established `SESSION.md`, `TODO.md`, `DECISIONS.md`, and `DEBUG.md` as the compact current handoff; labeled older state documents as historical.
- Corrected current architecture, version, U+ status, deployment prerequisites, and ERP RFP scope in documentation.
- Added Graphify/local-artifact exclusions and regenerated the graph from 64 active code files.

## Verification

- Python compile passed for Zoom billing, mail collection, backend app/worker/output-set, Agent, and crawler entry modules.
- JavaScript syntax passed for `app.js` and `admin_db.js`.
- Frontend DOM mapping passed: all 84 static IDs referenced by `app.js` exist; four unmatched selectors are runtime-generated elements.
- Required frontend/setup/Zoom assets and version `1.0.228` were confirmed.
- Graphify regenerated to 1,384 nodes, 3,828 edges, and 42 communities after the Zoom resilience change.
- `git diff --check` passed for the task-owned changes.

## Known verification boundary

Live FastAPI restart/health, Agent self-update, Excel report generation, report upload, output-set construction, Pyeongtaek printer submission, and Windows spooler verification were performed. Installer download and an actual ERP GUI-entry cycle were not rerun because this correction must not duplicate ERP work.

## Next start point

Observe the next 12:00 regular-due run and confirm that exactly one status email arrives from the canonical sender. Also monitor the next genuinely new WEHAGO invoice and confirm that it creates a new DB row rather than taking the already-verified duplicate path.

## Release handoff

- The duplicate-noon-sender singleton repair is published on `origin/codex/regular-due-singleton-20260824`; it includes the focused runtime, startup protection, tests, and session records.
- The Zoom Excel-PDF resilience and retry-throttling repair is published on `origin/codex/zoom-expense-a4-20260824` with the focused source, tests, and session records.
- Cash-disbursement layout source plus current session records are published on `origin/codex/expense-layout-20260821`; the branch tip is the final portrait correction. The earlier landscape state is superseded. No force push or dirty-worktree rebase was attempted.
- Focused reconciliation changes are published on `codex/reconcile-state-20260812`.
- `origin/main` is currently `9d9f9b6` and includes the independently added `excel_voucher_web` subsystem plus manager-side changes.
- Main was not force-pushed, and the dirty 1.0.228 worktree was not auto-stashed/rebased. Before integrating the branch into main, compare the two active product lines and regenerate Graphify from the chosen combined tree.

## Gemini purchase-analysis upgrade (2026-08-24)

- Purchase-document AI analysis now uses the maintained `google-genai` SDK with configurable model `gemini-3.7-flash`; the legacy `google-generativeai` path was removed.
- The rotated API key exists only in the operating server's backend `.env`. It is not stored in source, tests, session documents, or Git history.
- The operating-server certificate chain required Windows trust-store integration. `truststore.SSLContext` is now supplied to the SDK so the production network can validate Google's endpoint.
- The first deployment attempt failed its SDK model probe with `CERTIFICATE_VERIFY_FAILED`, restored the source/environment backup automatically, and restarted the prior healthy backend.
- Final deployment completed at `2026-08-24T11:55:49`; backup `C:\ERP_DB\backups\gemini37_20260824_115520`, backend PID `8568`, and sole listener PID `8568`.
- Production verification passed: 13 focused tests, SDK model lookup `models/gemini-3.7-flash`, a live JSON generation request, external HTTPS `/health`, and regular-due scheduler/process-lock ownership.
- Focused source commits `019f2a8` and `c6ec23f` are published on `origin/codex/zoom-expense-a4-20260824`.
- `graphify update .` was attempted after the code change but declined to replace the existing graph because the regenerated node count shrank unexpectedly. Existing graph outputs were left for a later clean-tree rebuild.

## Next exact starting point

Observe the next purchase case that contains items the fast parser cannot classify and confirm its saved analysis records `analysis_ai_model=gemini-3.7-flash`. Also confirm the next real 12:00 regular-due run sends exactly one status email.

## Gemini 2.5/3.7 sample comparison (2026-08-24)

- Read-only comparison used purchase invoices `#159`, `#207`, and `#208` with identical tax/quote PDFs, prompt, fast-parse context, and JSON mode. No invoice row was updated.
- The rotated key cannot call `gemini-2.5-flash`: all three requests returned 404 because the model is unavailable to new users. Historical stored Gemini results were used as the 2.5-era baseline because the pre-upgrade source hard-coded that model; `#207` includes later manual account edits and is not a pristine raw baseline.
- `gemini-3.7-flash` succeeded for all three samples. Target supply, tax, grand total, and summed item supply matched exactly in every sample.
- Material improvement: `#159` historically treated the RJ-45 `[100개]` package notation as quantity 100, while the quote's actual order quantity is 2; 3.7 returned quantity 2. `#207` still expanded each quantity-2 product into two quantity-1 rows. `#208` matched the historical result.
- All three quotes contain delivery-fee and free-delivery rows that net to zero; 3.7 correctly omitted both adjustment rows from ERP items.
- Critical deployment finding: `google-genai` file upload raises `UnicodeEncodeError` when a Korean source filename is placed in the multipart header. The comparison succeeded only after copying each source to an ASCII-named temporary PDF.

## Next exact starting point after comparison

Deploy the ASCII temporary upload fix, then rerun one existing sample through the exact production function without saving its result to the invoice DB.
