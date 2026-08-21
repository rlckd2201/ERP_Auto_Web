# Session

Updated: 2026-08-21

## Current objective

Keep the 1.0.228 operating server reliable: native WEHAGO PDFs, one canonical noon alert, canonical document authors, and correctly scaled cash-disbursement PDFs.

## Status

The WEHAGO incident, global document-author defect, duplicate-noon-sender defect, and cash-disbursement PDF layout defect are deployed on `172.17.39.121`. Server health is good on version `1.0.228`; the final corrected reports for `#176`, `#179`, and `#180` were visually verified and submitted `3/3` to the Pyeongtaek printer.

## 2026-08-21 deployment and repair

- Global authenticated-user document-author resolution is live in `app.py`, `setup_state.py`, `worker.py`, and `models.py`. Full login IDs, exact display names, and unique legacy prefixes resolve canonically; Agent/machine IDs no longer become authors.
- The noon alert is live only when explicitly enabled on canonical host `WIN-2H29RFPBUMN`. The next real 12:00 run still needs observation to confirm that only one message arrives.
- Main deployment completed at `09:54:20`; backup `C:\ERP_DB\backups\document_actor_fix_20260821_095410`, backend PID `7608`, import/database checks passed, and six focused tests passed.
- Historical repair completed for `#176=구름`, `#179=구름`, `#180=김기창`, and `#205=현시훈`. Old reports were backed up; `#205` retained status `오류` and ERP was not rerun. Initial repair printing verified `4/4` spooler submissions.
- PDF visual QA found two independent layout defects in `expense_excel_export.py`: `Orientation=1` forced portrait and print area `$A$1:$R$42` included 22 empty rows, shrinking the form.
- Final global layout is `A4 landscape`, print area `$A$1:$R$20`, one page, width `841.68`, height `595.20`. Deployed helper SHA-256: `204F9052C2181F7E9814753184221B566C13DD1D22711B02CF32420E308BC1FB`; final backend PID `1984`.
- Both generation agents (`reum-reum`, `김기창-김기창`) reported current bundle hash `0e098d8e0aae449d15667d2b161d67eba49bd8d70e4cfd7c795b5d0a718db608` before regeneration.
- Final reports were regenerated without ERP, downloaded, rendered, and visually checked. Authors are `구름`, `구름`, and `김기창`; no machine/Agent ID text appears.
- Final print job `ab3d3fc6-8351-4586-9e91-2a0c9e206452` completed at `10:21:39`: three one-page A4 files, `gdi_a4_fit`, Windows spooler verified `3/3`, no failures, printer `평택 프린터 (172.16.10.172)`.
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
- Graphify regenerated to 1,353 nodes, 3,767 edges, and 42 communities after the layout source change.
- `git diff --check` passed for the task-owned changes.

## Known verification boundary

Live FastAPI restart/health, Agent self-update, Excel report generation, report upload, output-set construction, Pyeongtaek printer submission, and Windows spooler verification were performed. Installer download and an actual ERP GUI-entry cycle were not rerun because this correction must not duplicate ERP work.

## Next start point

Observe the next 12:00 regular-due run and confirm that exactly one status email arrives. Also monitor the next genuinely new WEHAGO invoice and confirm that it creates a new DB row rather than taking the already-verified duplicate path.

## Release handoff

- Focused reconciliation changes are published on `codex/reconcile-state-20260812`.
- `origin/main` advanced independently to `c20a96c` during this work and includes a new `excel_voucher_web` subsystem plus manager-side changes.
- Main was not force-pushed, and the dirty 1.0.228 worktree was not auto-stashed/rebased. Before integrating the branch into main, compare the two active product lines and regenerate Graphify from the chosen combined tree.
