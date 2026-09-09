# Session

Updated: 2026-08-31

## Current objective

Keep the 1.0.237 operating server reliable, including end-to-end mail collection, ERP entry, and document output.

## Status

The purchase-mail retry/log repair is deployed on `172.17.39.121`; HTTPS health reports version `1.0.237`. The only real deferred failure, SmartBill UID `1087`, was recovered as invoice `#220`, completed ERP, generated its voucher PDF, submitted both output files to the Pyeongtaek printer, and sent the result email. New one-minute mail checks complete without being misclassified as failures.

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
- Critical deployment finding: `google-genai` file upload raises `UnicodeEncodeError` when a Korean source filename is placed in the multipart header. The comparison succeeded only after copying each source to an ASCII-named temporary PDF; the production repair and verification are recorded below.

## Gemini Korean-filename fix deployment (2026-08-24)

- Final deployment completed at `2026-08-24T13:53:53`; backup `C:\ERP_DB\backups\gemini_filename_fix_20260824_135253`, backend PID/listener `6568`.
- Fourteen focused tests passed on the operating server. Read-only production `_ai_parse` verification used Korean-named invoice `#208`, returned three items through `gemini-3.7-flash`, and matched supply `228,527`, tax `22,853`, and total `251,380`.
- Verification confirmed one production-function call, complete temporary-directory cleanup, no invoice DB write, external HTTPS health, sole 8080 listener, and regular-due scheduler/process-lock ownership.
- A final browser check opened `https://172.17.39.121:8080/` and rendered the production UI. Port 8080 is HTTPS-only, so a plain HTTP probe returning an empty response is expected and is not a backend outage.
- SDK calls are bounded to a 60-second request timeout and two total attempts. The verifier does not wrap `_ai_parse` in another retry loop.
- Source and operational records are published on `origin/codex/gemini-filename-fix-20260824` through commit `959d548`.

## Next exact starting point after deployment

Observe the next genuinely unknown purchase item and confirm its saved row records `analysis_ai_model=gemini-3.7-flash`. Separately add a deterministic test case for a non-zero discount line such as `-6,730원`; the three historical comparison quotes only contained net-zero delivery adjustments.

## Executive system PPT draft (2026-08-25)

- Created a 14-slide executive-facing draft at `output/회계업무_자동화_WEB_시스템_소개_초안_v0.1.pptx`.
- The deck covers the agenda, system overview, four concise feature slides using real operating screenshots, daily and exception operator manuals, a conservative time-saving calculation, annualized impact, and a realistic external-development estimate.
- Read-only operating snapshot used in the draft: 100 invoices over 2026-05-12 through 2026-08-24; 73 regular, 27 purchase; 97 complete, 2 waiting, 1 error; 30,676 invoice-log rows.
- Time model is explicitly labeled as a pre-interview assumption: regular 20 to 5 minutes, purchase 35 to 8 minutes. It yields 30.4 hours saved per 100 cases and about 105.7 hours, or 13.2 eight-hour workdays, annualized at the observed volume.
- External-build planning range is `KRW 55-80 million` plus VAT/server/licenses, with annual maintenance `KRW 6-12 million`; the deck notes that this is a planning range based on 2026 KOSA applied-SW wage data, not a vendor quote.
- Verification: `python-pptx` reopened all 14 slides, every slide contains a `[Sources]` speaker-note block, PowerPoint opened the deck and exported 14 PNGs at 1600x900, and all rendered slides were visually inspected at full size. The skill-provided `slides_test.py` could not run because its optional `numpy` dependency is absent.
- Build and QA sources are retained in `output/system_overview_ppt_draft/`; no production code, database row, ERP job, email, or deployment state was changed.
- Added generated `output/` to `.graphifyignore` and rebuilt Graphify after the expected removal of the draft-builder nodes: 1,383 nodes, 3,850 edges, and 42 communities.

## Next exact starting point after PPT draft

Collect executive/operator feedback on terminology, measured per-case handling time, preferred company branding, and whether the cost slide should remain in the main deck or move to an appendix. Apply those choices to v0.2 without changing the evidence snapshot unless a new measurement is supplied.

## Executive system PPT revision v0.2 (2026-08-25)

- Rebuilt the executive deck as 12 slides at `output/회계업무_자동화_WEB_시스템_소개_v0.2.pptx`; v0.1 remains preserved.
- Replaced every reused/user-provided browser image with new clean captures that exclude Chrome tabs, address bar, and bookmarks: accounting mail, regular receipt history, and the live Compuzone quote.
- Removed error-log/retry content and reframed the main story around usefulness, automatic document interpretation, ERP/document-set output, time reduction, direct labor savings, and external replacement value.
- Added actual generated ERP voucher `#180` and cash-disbursement report `#180` as output evidence.
- All slide titles render on one line. PowerPoint reopened the file and exported 12 slides at 1600x900; all slides were inspected individually and in a montage.
- Final validation passed: valid PPTX ZIP, 12 slides, `[Sources]` notes on every slide, no title newline, and PowerPoint COM reopen count 12.

## Next exact starting point after PPT v0.2

Use measured operator handling times to replace the disclosed planning assumptions when available. Otherwise the deck is ready for executive review without any production-code or deployment change.

## Executive system PPT revision v0.3 (2026-08-25)

- Corrected the labor model so automation elapsed time is not counted as operator work; post-adoption hands-on time is one minute per case for click and result confirmation.
- Regular volume uses completed June/July production months at 20 cases/month, or 240/year. Purchase volume uses the user-supplied operating average of 250/year, for 490/year total.
- Revised annual impact: 225.8 hours before, 8.2 hands-on hours after, 217.7 hours or 96.4% saved.
- Direct labor is now a floor based on the official 2026 minimum wage of KRW 10,320/hour: KRW 2,246,320/year.
- External rebuild and outsourced-maintenance ranges were removed from main ROI and placed in an appendix as replacement-market references, not current operating costs.
- Final deck: `output/회계업무_자동화_WEB_시스템_소개_v0.3.pptx`; 13 slides, all titles one line, all notes sourced, PowerPoint reopen/render verification passed.

## Next exact starting point after PPT v0.3

Obtain the actual annual cash operating/maintenance cost. Compare it with the KRW 2.246 million direct-labor floor; quantify deadline/error/continuity value only if management requires a fuller ROI.

## Executive system PPT revision v0.4 (2026-08-25)

- Removed the duplicated metric summary and merged system introduction/process into one `원클릭 회계처리` slide.
- Reduced the deck from 13 to 12 slides. Slide 3 contains no time or cost metrics; those appear only on `연간 업무시간 절감` and `연간 인건비 절감`.
- Replaced sentence-style titles with concise functional titles across the deck.
- Simplified the cover metrics into four automation-scope labels: automatic receipt, AI analysis, ERP input, and document output.
- Final deck: `output/회계업무_자동화_WEB_시스템_소개_v0.4.pptx`; valid 12-slide PPTX, all titles one line, all source notes present, PowerPoint reopen and 1600x900 render QA passed.

## Next exact starting point after PPT v0.4

Use v0.4 for executive review. Only revise operating-cost economics after the actual current annual cash operating cost is supplied.

## Invoice #209 Compuzone diagnosis (2026-08-26)

- Read-only production inspection covered invoice `#209` and both failed purchase jobs `d9cc4929-8e37-420c-9f35-09991cd3e310` and `f5f0b54e-441f-48d7-91c2-2718ed102f4c`.
- The purchase payload correctly builds four rows: fixtures, supplies, input VAT, and `가지급금(업체)`. Compuzone's intended vendor lookup value is the correct supplier business number `106-81-83458`.
- The management-item defect is state/focus validation: rows 3 and 4 reuse an already-open vendor popup, assume its default search-box focus, run a fixed keyboard sequence, and report completion without reading back the selected vendor.
- The terminal job failure is separate: both runs sent Ctrl+S, then RD Viewer and the Windows print dialog timed out, so no ERP voucher PDF was created. The print helper swallowed the timeout and only the backend's missing-file check marked the job failed.

## Next exact starting point after #209 diagnosis

Before any retry, confirm in K-System whether either Ctrl+S created a saved voucher. If implementation is approved, make vendor selection row-scoped and read-back verified, make print/viewer failure fatal at its source, and apply an appropriate fast profile to purchase tasks without removing critical field checks.

## Invoice #209 purchase ERP safety/performance fix (2026-08-26)

- Preserved the pre-change files under `tmp/erp_purchase_fix_backup_20260826_091706`; SHA-256 verification matched every copied source.
- Purchase tasks now use a dedicated interactive fast profile on ordinary operator PCs. The 243-PC `regular_auto` profile is unchanged.
- Vendor management values are selected from a newly opened row-scoped popup by exact 10-digit business-number match. The prior blind `Tab/Down/Up/Enter` sequence was removed.
- A failure after Ctrl+S now raises `[ERP_SAVE_CONFIRM_REQUIRED]`; the web API blocks a direct retry until an operator checks K-System and explicitly returns the invoice to waiting.
- RD Viewer, print-dialog, and PDF-save failures are no longer reported as success. Progress-event chatter and redundant purchase-only UI scans were reduced.
- Verification passed: Python compile, all 11 discovered `web_v1/test*.py` tests, and `graphify update .` (`1,405` nodes, `3,875` edges, `48` communities).
- Version `1.0.229` was deployed at `2026-08-26T11:07:54`. Production backup: `C:\ERP_DB\backups\erp_purchase_fix_20260826_110738`; backend PID/listener: `3948`.
- External HTTPS health, version, the regular-due scheduler/process lock, and the single 8080 listener all passed. The local ERP Agent restarted as PID `21168`; setup status reports ready, current/latest version `1.0.229`, and matching bundle hash `df297cc0601d8b314205d8367bb7446d7f706eef19b7cd6a7975b690fd9084d7`.

## Next exact starting point after #209 fix

Before retrying invoice `#209`, confirm in K-System that neither prior Ctrl+S attempt already created a voucher. Observe the first safe new purchase job to confirm the live K-System result grid exposes the exact business-number cell as expected; do not use #209 for this acceptance check.

## Purchase fast-profile regression diagnosis (2026-08-26)

- Production jobs `0be1a41e-5d97-4950-8454-e69fc8947972` and `f7e66896-2ec1-4746-b7fc-c427b659637f` retried invoice `#209` from Agent `송명학-송명학` at `172.17.30.15` after the 1.0.229 deployment.
- The first run lost the K-System UI Automation connection immediately after the `회계일` click at `11:18:45`; the server received COM/UIA error `-2147220991` at `11:18:48`.
- The second run passed header/grid entry but repeatedly reused the disconnected UIA wrapper, so the exact-vendor popup could not be found and the job failed before Ctrl+S.
- The regression is the purchase profile's use of `ERP_FAST_INPUT=1` plus `ERP_FAST_FIELD_VERIFY=1`: it reduces global PyAutoGUI pacing and skips read-back of critical header fields, leaving no recovery boundary when K-System recreates or invalidates its UIA provider.
- No further ERP run was started during diagnosis. The current development-PC Agent had no claimed task; the failing jobs ran on the separate operator PC.

## Next exact starting point after fast-profile diagnosis

After implementation approval, preserve fast menu/progress behavior but restore stable pacing and mandatory read-back for 회계단위, 전표관리단위, and 회계일. Reconnect the active K-System window after critical transitions; if reconnect/read-back fails, stop before grid management or Ctrl+S. Back up, test the COM/UIA invalidation path, deploy as 1.0.230, and do not use #209 for acceptance until its earlier saved-voucher risk is checked.

## Purchase header/UIA recovery deployment (2026-08-26)

- Preserved the 1.0.229 pre-change sources under `tmp/erp_header_stability_backup_20260826_114355`; production created `C:\ERP_DB\backups\erp_header_stability_20260826_120208` before replacement.
- Version 1.0.230 removes purchase-task global fast input and verification skipping for 회계단위, 전표관리단위, and 회계일 while retaining the safe menu, progress, management, and output optimizations.
- Critical header transitions now reconnect to the current K-System process/window and require value read-back. A disconnected UIA provider or unverifiable value raises a terminal error before management-grid work and before Ctrl+S.
- The local self-updating Agent was stopped while source and production bundles differed, preventing another overwrite of the editable worktree. It was restarted only after the server published the exact 1.0.230 bundle.
- Verification passed Python compilation, 13 discovered regression tests, `git diff --check`, and `graphify update .` (`1,414` nodes, `3,886` edges, `50` communities).
- Production deployed at `2026-08-26T12:02:34`; backend/listener PID `8268`, scheduler and process lock active, version `1.0.230`, and Agent bundle hash `5eae04b11a38dcdcdd5741d11c29f7d5df5f878508761d05fef657d9141fd1e2` matched exactly.
- Local Agent PID `26008` reports setup ready, version current/latest `1.0.230`, matching bundle hash, all required packages, ERP installations, templates, display, and printers ready.
- No ERP job or invoice state was changed during deployment. Invoice #209 was not replayed; only scheduled purchase-mail collection jobs appeared after restart.

## Next exact starting point after 1.0.230 deployment

Check K-System for a voucher potentially created by #209's earlier pre-fix Ctrl+S attempt before any reset or retry. Use the next safe new purchase case for live acceptance of header read-back, exact vendor selection, and one-time document-set output.

## Invoice #209 vendor-popup restoration and deployment (2026-08-26)

- Backed up 1.0.230 sources under `tmp/erp_vendor_restore_backup_20260826_132020` before modification.
- Direct UIA inspection proved that the K-System vendor result grid exposes no rows or cells to UI Automation. The 1.0.229/1.0.230 exact-result scanner therefore could never find Compuzone even when the visible search result was correct.
- Restored the proven popup-default-focus sequence: `Ctrl+A`, paste business number, `Tab 4`, `Down 5`, `Up 1`, `Tab 3`, `Enter 2`. Removed the active and dead search-Edit click/result-cell UIA paths. Previous-row popup closing and 1.0.230 header/UIA/save guards remain.
- Purchase management items no longer use the over-fast management timing profile; fast menu navigation remains. The 243-PC `regular_auto` profile is unchanged.
- Ran invoice `#209` directly through the product ERP function, bypassing the event queue. Rows 1, 3, and 4 completed their management inputs; the final visible row-4 `가지급금(업체)` value was `컴퓨존`. A harness replaced the save call and stopped at `[DIRECT_STOP_BEFORE_SAVE]`; Ctrl+S was never sent and the K-System test process was closed unsaved.
- Verification passed Python compilation, 10 purchase-safety tests, 3 Gemini tests on the operating server, `git diff --check`, and `graphify update .` (`1,419` nodes, `3,886` edges, `55` communities).
- The first deployment attempt timed out only on the cold `/api/regular-due/status` check and automatically rolled back to healthy 1.0.230. The second attempt allowed 60 seconds for that read-only status calculation and deployed 1.0.231 successfully.
- Production backup: `C:\ERP_DB\backups\erp_vendor_restore_20260826_133229`; backend/listener PID `6160`; scheduler and process lock active. Local Agent PID `9688` is ready/current at 1.0.231 and exactly matches bundle hash `1ce3dbf32a0e363016cf0be9a8a10ace243ef36594db215815568449ea4697e9`.
- A direct-test-only `manager_server/erp_ui_dump.txt` changed the local bundle hash; it was preserved as `tmp/direct_209_erp_ui_dump_20260826.txt`, after which local/server hashes matched. No production invoice or queue state was changed during deployment.

## Next exact starting point after 1.0.231 deployment

Before resetting or retrying invoice `#209`, check K-System for vouchers potentially saved by the older pre-1.0.229 Ctrl+S attempts. The 1.0.231 direct run itself did not save. Observe the next safe purchase case through document-set output; do not re-run #209 unattended.

## Invoice #209 intermittent vendor hardening and 1.0.232 deployment (2026-08-26)

- Production evidence showed the remaining asymmetry: invoice `#209` failed before save when the VAT-row vendor popup did not open, while invoice `#211` passed vendor key entry but reached Ctrl+S before an output failure and therefore remains protected by `[ERP_SAVE_CONFIRM_REQUIRED]`.
- Root causes were treating a sent keyboard sequence as success, retrying only vendor-only rows but not VAT rows, overly short click/key timing, and trusting the ambient Windows clipboard after K-System startup.
- Purchase vendor selection now retries both VAT and advance-payment vendor cells, preserves popup default focus, waits for popup closure, and reads the visible management Edit value back. The expected normalized vendor name must match before the row can continue.
- Purchase tasks force safe double-click/key intervals, a fresh ERP session, and longer menu/new-form readiness waits. The task's `erp_clipboard_rows` are rebuilt at form-entry time, so K-System clipboard changes cannot collapse a four-row voucher to one row. The 243-PC `regular_auto` profile is unchanged.
- Local pre-change backup: `tmp/erp_vendor_state_backup_20260826_140100`. Two consecutive direct #209 runs with fresh ERP sessions preserved all four rows and verified `컴퓨존` in rows 1, 3, and 4; both stopped at `[DIRECT_STOP_BEFORE_SAVE]` and never sent Ctrl+S.
- Verification passed Python compilation, 13 unit tests, focused `git diff --check`, and `graphify update .` (`1,424` nodes, `3,886` edges, `60` communities).
- Production 1.0.232 deployed at `2026-08-26T14:16:44`; backup `C:\ERP_DB\backups\erp_vendor_state_20260826_141624`; backend/listener PID `3976`; scheduler and process lock active; bundle hash `22cab9b29207b627bcd751e435e37fa1237ec52a64fe11e28a81918239685d4e`.
- Local Agent PID `25036` reports `ready=true`, version 1.0.232, and the exact server bundle hash. No production invoice or queue state was changed for acceptance.

## Next exact starting point after 1.0.232 deployment

Do not reset or retry #209 or #211 until K-System is checked for vouchers saved by their older Ctrl+S attempts. Observe the next genuinely new purchase job through ERP save and one-time document-set output; use its logs to confirm the live read-back messages for every vendor row.

## 송명학 PC ERP 좌표/진행로그 보정 배포 (2026-08-26)

- 로컬 변경 전 파일을 `tmp/erp_client_coord_backup_20260826_145136`에 보존했다.
- 송명학 PC의 실제 구성은 주 모니터 1920x1080 125%, ERP용 보조 모니터 1920x1080 100%, 가상 원점 `(-1920,-106)`이다. 해상도는 같아도 Windows 작업영역/좌표 원점이 다른 것이 자리별 클릭 편차의 원인이다.
- ERP 고정좌표 기준을 창 외곽선이 아니라 매 실행 새로 읽은 대상 모니터 `rcWork`로 통일하고, 신규 전표 폼의 실제 `cboAccUnit` 중심점으로 작은 잔여 편차를 보정한다. 거래처 팝업 키 순서와 검증된 입력 로직은 변경하지 않았다.
- 1.0.233을 운영 배포했고 송명학 Agent가 동일 번들 해시를 수신한 것을 확인했다. 이어 #209 재실행에서 진행 로그 HTTP 지연이 ERP 입력 스레드에 전파되어 멈추는 별도 결함을 재현했다.
- 1.0.234는 ERP 화면 입력과 진행 로그 전송을 제한된 비동기 큐로 분리했다. 로그 서버 지연/타임아웃은 화면 자동입력을 중단시키지 않고 완료/오류 보고만 동기 확정한다.
- 운영 1.0.234 배포 시 좌표 3건과 비동기 로그 3건, 총 6건의 서버 테스트가 통과했다. 운영 백업은 `C:\ERP_DB\backups\erp_coord_fix_20260826_154936`, 백엔드 PID는 `7508`, 번들 해시는 `3fb9dfba25ec68add2c58ae5cbb39e5e398d1dc3739646ca5d715e51530bc71f`다.
- 송명학 PC에서 1.0.233으로 시작된 #209 작업은 `PID 3180 확정` 이후 응답이 없고, 서버 재시작으로 메모리 Job도 사라졌다. 송명학 PC 원격관리 포트(135/445/3389/5985)는 운영서버와 개발PC 모두에서 닫혀 있어 원격 강제종료는 불가능하다. Invoice #209는 현재 `ERP대기`, ERP 전표 PDF는 없으며 큐 파일은 claimed 상태다.
- Graphify는 `graphify update .`에서 기존보다 노드가 줄어드는 보호 경고(1,422 vs 1,424)로 갱신을 거부했다. 강제 갱신하지 않는다.

## Next exact starting point after 1.0.234 deployment

송명학 PC에서 멈춘 1.0.233 `pythonw.exe` Agent와 해당 K-System 세션을 종료한다. Agent를 다시 시작해 1.0.234/번들 해시 일치를 확인한 뒤, #209의 기존 전표 저장 여부를 K-System에서 먼저 확인하고 큐/상태를 정리한다. 중복 위험이 없을 때만 새 Job으로 한 번 재실행하고 `ERP coordinate canvas` 및 폼 앵커 보정 로그와 거래처 행 1/3/4 결과를 확인한다.

## Invoice #209 coordinate rollback (2026-08-27)

- Version 1.0.236 incorrectly treated the anonymous account-unit ComboBox's `-76px` X difference as a form-wide offset. The same offset moved the accounting-date click from relative X `375` to `299`, where validation read the `회계일` label instead of the date value.
- Job `a45c2217-c7aa-4c78-91e9-57e915bc65e6` stopped before grid entry and Ctrl+S with `expected=2026-08-18, actual=회계일`; invoice #209 remains error and no new voucher/output PDF was created by this run.
- Production, the Song operator Agent, and the editable worktree were rolled back to version 1.0.235 and bundle hash `1900baa462be33af637905dec64e5c3d4ef64afa361f1d26532996b5f15e4674`.
- Production restore source: `C:\ERP_DB\backups\erp_form_anchor_236_20260827_093703`. Pre-rollback 1.0.236 safety snapshot: `C:\ERP_DB\backups\before_rollback_236_20260827_102111`.
- Rollback verification passed eight tests, external health/version, background backend task PID `7064`, and Song Agent setup/display readiness. No ERP retry was started after rollback.

## Next exact starting point after 1.0.235 rollback

Design 1.0.237 without a form-wide offset: use the live ComboBox only for account-unit selection, keep the proven coordinates for slip unit/date/grid/management, reject label controls during value verification, and apply moderate field-specific pacing with read-back before advancing. Do not run #209 again until the implementation and no-click coordinate checks pass and the operator explicitly provides a test window.

## SmartBill clean tax-invoice PDF deployment (2026-08-31)

- Confirmed in the user's signed-in Daou Office/SmartBill page that the official `인쇄` action posts the invoice form to `/xDTI/arap_repo/common/prt_prev.aspx`. The crawler already reached that preview, but Selenium `print_page()` forced portrait A4 and left the wide invoice in the top half, which looked like a screen capture.
- Added vector-preserving PDF layout normalization: detect the occupied invoice bounds (text, rules, seals), clip only that region, and fit it to landscape A4 with a 24-point margin. No raster screenshot or advertisement/browser UI is included.
- Two focused unit tests and Python compilation passed. Real PDFs for invoices `#216`, `#217`, and `#218` rendered at `842x595` points with 132-134 extractable words and passed visual inspection.
- Production source backup: `C:\ERP_DB\deploy_backups\20260831_smartbill_pdf_layout\portal_smartbill.py`. Original download PDFs and output-set copies are backed up under the same directory.
- Deployed source hash `C556B4ADF9DE3408BA2E491755AD96B60677F1F002A0D490E76F3275FFD36207`. Backend scheduled task is running with listener PID `5872`; HTTPS root returns `200`.
- Existing download PDFs and `output_sets\regular\216..218\02_세금계산서.pdf` were normalized in place after backup. ERP vouchers were not rerun and invoice states were not changed.
- `graphify update .` was attempted but refused the safety overwrite because the new graph had 1,430 nodes versus the existing 1,440. No force update was used.

## Next exact starting point after SmartBill PDF deployment

Observe the next genuinely new SmartBill invoice collection and verify that its download PDF and output-set tax invoice are landscape A4 before ERP output. If production still shows portrait A4, inspect whether that portal bypassed the final `_smartbill_form_post_print_save_pdf` override; do not fall back to printing the detail webpage.

## SmartBill receipt-approval gate and production repair (2026-08-31)

- Root cause: `_handle_approval()` treated the presence of SmartBill's always-visible print button as proof of receipt approval. The official page still had canonical `hdndtistatus=I`, and the print routine's confirmation was dismissed, so PDFs and ERP work could continue while the portal remained `수신 미승인`.
- Approval now reads `hdndtistatus` and fails closed when the value is missing or `I`. For an unapproved invoice it clicks only the real `btnApprove01/btnApprove02` element, then only the approval iframe action `fnConfirmClick('APPROVE')`. It requires the canonical status to transition away from `I` and revalidates it before PDF print.
- The generic text matcher is no longer used for approval. The success modal is closed directly without invoking its unrelated OK-button side effects, and PDF form submission independently rejects missing/`I` status.
- Production invoices `#216`, `#217`, and `#218` were repaired in place: all three live SmartBill pages transitioned from `I` to `C`; ERP vouchers were not rerun; only their download PDFs and `output_sets\regular\216..218\02_세금계산서.pdf` copies were refreshed.
- Visual QA confirmed all three refreshed documents are single-page landscape A4 (`842x595`) with aligned tables, no crop/skew/browser chrome, and `275,000` total. Each download/output-set pair has an identical SHA-256 hash; DB rows remain `처리완료`.
- Production backup: `C:\ERP_DB\deploy_backups\20260831_smartbill_receipt_approval`. Deployed source SHA-256 is `71400F60D9605B98AD3A9FA9C71EE05234D04FEF797504CD59EC84464645B703`.
- Five focused tests, Python compilation, focused diff checks, and `graphify update .` passed. Graphify now reports `1,452` nodes, `3,931` edges, and `75` communities. Backend task/listener PID `5736` is running and HTTPS root returns `200`.

## Next exact starting point after SmartBill approval repair

Observe the next genuinely new SmartBill mail from collection through ERP/output. Require log evidence of canonical status `C` before print and verify the new download/output PDF is landscape A4. Do not infer approval from an available print button or retry an existing completed ERP voucher.

## SmartBill original portrait print restoration (2026-08-31)

- User acceptance corrected the PDF requirement: SmartBill output must match Chrome's original print artifact, not a cropped or enlarged invoice. The authoritative format is full portrait A4 with the blank lower page retained, date/title header, and source URL/page-number footer.
- Replaced the final PDF creation with Chrome CDP `Page.printToPDF` fixed to A4 portrait (`8.27 x 11.69`), background graphics, and explicit native-style header/footer templates. `_normalize_smartbill_pdf_layout()` is now a compatibility no-op and cannot crop, rotate, resize, or rewrite the file.
- Reprinted production invoices `#216`, `#217`, and `#218` without rerunning ERP. All three remain `처리완료`; each download PDF exactly matches its `output_sets\regular\<id>\02_*.pdf` copy by SHA-256.
- Visual and structural QA passed for all three: one page, `595.92 x 841.92` points, portrait orientation, invoice at the top, full blank lower area, `:: Business is ON! ::`, SmartBill source URL, and `1/1` present.
- Local deliverables: `C:\Users\user\Desktop\스마트빌_승인완료_PDF\216_대승_D1공장_세금계산서.pdf`, `217_일강1공장_세금계산서.pdf`, and `218_대승정밀_P1공장_세금계산서.pdf`.
- Production safety backup: `C:\ERP_DB\deploy_backups\20260831_smartbill_portrait_restore`. Operating source hash `A0422B70BBF573A969CCAE17B720565EBDA9CA8D2AEF7B5AD13F39C04E7E6A13`; backend PID `10568`; HTTPS `200`.
- Five focused tests and compilation pass. `graphify update .` completed at 1,455 nodes, 3,936 edges, and 76 communities.

## Next exact starting point after portrait restoration

Observe one genuinely new SmartBill mail end to end. Require canonical receipt status `C`, full portrait A4 with header/footer, matching download/output hashes, and no duplicate ERP execution. Do not restore the superseded landscape normalization.

## SmartBill local print dispatch (2026-08-31)

- Sent the three verified portrait PDFs for invoices `#216`, `#217`, and `#218`, one copy each, to the explicitly selected local device `평택 프린터 (172.16.10.172)`.
- PDF24 Reader returned exit code `0` for every file. The target queue drained to zero; the default `김제 프린터` was not used.

## Purchase-mail repeated failure-log diagnosis (2026-08-31)

- The many visible failure rows are not many failed invoices. The one-minute automatic collector creates a completed job each minute, and every completed job reports the same single deferred mail in its message.
- The sole failure-state record is unread Gmail UID `1087`, dated `2026-08-27 11:15 KST`, subject `[전자세금계산서 정발행] 대신아이씨티㈜ ▶ ㈜대승`, with 11 historical attempts. Last actual failure was `2026-08-31 06:38 KST`; next retry is `18:38 KST`.
- Stored root error: Python Windows encoding exception `'charmap' codec can't encode characters in position 16-17`. The per-minute jobs since then have `failed_count=0`, `deferred_count=1`, and status `done`; they do not execute the crawler during the cooldown.
- Current invoice `#219` (피플러스) is unrelated and completed ERP/output successfully. The three new SmartBill mails `#216/#217/#218` also have distinct message IDs and remain processed.

## Purchase-mail retry/log repair completed (2026-08-31)

- Root cause was one UID `1087` crawler run aborting while Windows `cp1252` stdout tried to print Korean text. The many dashboard rows were successful cooldown checks whose notification still contained the word `실패`.
- Crawler stdout/stderr now use `backslashreplace` when a legacy console cannot encode a message. Cooldown-only job/event text now says `재시도 대기` without the failure keyword.
- Production source, collector state, and SQLite DB were backed up under `C:\ERP_DB\deploy_backups\20260831_mail_retry_fix`; deployed files match the staged SHA-256 hashes and the backup DB passes `PRAGMA integrity_check`.
- UID `1087` was fetched without marking it read, crawled with the normal transient-window retry, checked by exact PDF path and vendor/date/amount/context identity, then inserted once as invoice `#220`. Its failure record was cleared only after DB verification and the mail was then marked read.
- Invoice `#220` (`대신아이씨티(주)`, D1공장, 935,000원, 2026-08-27) completed the normal regular-auto flow: ERP 3 rows, vendor management value `대신아이씨티(DS163)` verified, voucher PDF stored, two output files submitted to `평택 프린터 (172.16.10.172)` with `2/2` spooler verification, and result email sent.
- Post-restart mail jobs show `failed_count=0`, `deferred_count=0`, status `done`, and message `구매 메일 수집 완료: 신규 대상 없음`. HTTPS `/health` returns `200` on version `1.0.237`.

## Next exact starting point after purchase-mail repair

Observe the next genuinely failed mail, if any, as a single underlying failure rather than repeated cooldown jobs. Do not replay invoice `#220`; its ERP and Pyeongtaek output are complete.

## 8080 listener recovery (2026-09-09)

- `AccountingWeb-Backend` still reported `Running`, but `172.17.39.121:8080` had no listener. The surviving Python PID `9720` continued one-minute mail collection after the web socket had failed.
- The first fatal listener evidence is at `2026-09-07 17:03:33`: asyncio `IocpProactor.accept()` raised `OSError [WinError 64]`, followed by `Accept failed on a socket`. The non-web background thread kept the process alive, so the task wrapper never exited and no restart occurred.
- Recovery ended the scheduled-task wrapper, terminated only the confirmed orphan/current backend PIDs (`9720`, `9304`), and started `AccountingWeb-Backend` cleanly after the current automatic mail collection completed.
- Final proof: HTTPS `/health` returned `200`, version `1.0.237`, production/agent mode. The active production root is `C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version`.

## Next exact starting point after 8080 recovery

Implement a listener-aware watchdog so a live Python process without a healthy 8080 listener is restarted. Then continue the approved Song-PC coordinate repair: never propagate account-unit Y displacement to the form and never retry management rows at a different Y coordinate. Do not replay an ERP voucher during code verification.

## v1.0.238 Song-PC coordinate and backend supervision release (2026-09-09)

- Deployed v1.0.238 to the verified production root with a pre-change backup at `C:\ERP_DB\deploy_backups\20260909_v1.0.238_song_y_watchdog`.
- ERP form calibration is now X-only. A detected account-unit Y displacement is never propagated to the slip unit, accounting date, grid, or management rows.
- Management-summary retries keep the exact row Y and vary only the bounded X candidates. The old `0, +4, +8, -4, -8` vertical retries that could open the next relation row on a slow PC are gone.
- Preserved the established default-focus vendor search sequence; no search textbox-click path was added and the 243-PC regular automation timing profile was not changed.
- Installed `AccountingWeb-Backend-Watchdog` as SYSTEM every minute. It requires two consecutive HTTPS health failures, then ends only `AccountingWeb-Backend` and Python processes whose command line is `-m web_v1.backend`, restarts the task, and requires HTTP 200.
- Replaced the external server runner with an explicit production-root runner so it can no longer select a similarly named Desktop folder.
- Rotated the production Voucher Automation/Gemini key in `web_v1/backend/.env` without placing the value in source, Git, logs, or session documents. `APP_VERSION` is `1.0.238`.
- Production verification: all seven selected deployed files match their staged SHA-256 values; the external runner matches; all coordinate invariants are true; `/health` is HTTP 200; the active listener PID command line is `-m web_v1.backend`; recent one-minute mail jobs finish `done` with zero failures.
- Agent acceptance: Song `172.17.30.15`, regular PC `172.17.30.243`, and the local operator PC `172.17.30.13` all report v1.0.238, exact bundle hash `306e8b91adae798a83d7e12b963cf817d0e6cdcfc38e486987f6645632993469`, and successful preflight. The local operator Agent now runs from isolated `%LOCALAPPDATA%\AccountingWebAgent\1.0.238` so its updater does not overwrite the editable repository.
- Verification passed: Python compilation, 6 focused tests, three PowerShell parser checks, Graphify update (`1,484` nodes / `3,956` edges / `91` communities), healthy watchdog execution, and production hash checks.
- No existing ERP voucher was replayed and no live ERP click/save was issued during this release.

## Next exact starting point after v1.0.238

Observe the first genuinely new Song purchase voucher through account unit, accounting date, VAT/vendor management rows, save, and document-set output. Require the log to show `form-x-only` calibration and same-Y management retries. Do not reuse or reset an older voucher merely to test coordinates.

## Compuzone September 7 mail diagnosis (2026-09-09)

- The two expected messages exist in Gmail and in `purchase_mail_collect_state.json`: 2026-09-07 15:02:06/07 KST, message IDs ending `CDF842400707` and `876B82400706`.
- They are payment-confirmation messages, not electronic tax invoices. Orders `28692792` and `28682826` show amounts `1,220,000` and `282,000`, but contain no tax-invoice wording, no attachment, and no supported e-tax portal link; only generic Compuzone/My Orders links are present.
- The collector examined both before the later 8080 listener failure and recorded `no supported tax invoice target`. This is why no purchase invoice row was inserted.
- Read-only IMAP inspection of Gmail All Mail from September 7 through September 9 found no other Compuzone message and therefore no later official tax-invoice mail to recover.

## Next exact starting point after Compuzone mail diagnosis

Wait for the official electronic tax-invoice mail or obtain its PDF. When it arrives, collect it by its distinct message ID and merge/attach the existing order number as quote context; do not post an ERP voucher from payment-confirmation email alone.
