# Session

Updated: 2026-08-14

## Current objective

Keep the 1.0.228 operating server reliable, with WEHAGO invoices saved only as native tax-invoice PDFs.

## Status

The WEHAGO incident is resolved and verified on `172.17.39.121`. The retry mail completes with zero failures, and the resulting PDF matches the manually saved native invoice.

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
- Graphify regenerated to 1,458 nodes, 4,187 edges, and 32 communities; historical source-path hits are zero.
- `git diff --check` passed for the task-owned changes.

## Known verification boundary

A live FastAPI startup, installer HTTP download, manager-PC Agent queue, ERP GUI, printer, and real output-set end-to-end run was not performed because it can start schedulers or depend on deployment hosts, credentials, Windows GUI, printers, and `C:\ERP_DB`. Static dependencies and syntax are verified; operational E2E remains the next environment-level check.

## Next start point

For WEHAGO, monitor the next genuinely new invoice and confirm it creates a new DB row rather than the expected duplicate path. The remaining broader Agent/ERP/output-set E2E boundary below is unrelated to this resolved incident.

## Release handoff

- Focused reconciliation changes are published on `codex/reconcile-state-20260812`.
- `origin/main` advanced independently to `c20a96c` during this work and includes a new `excel_voucher_web` subsystem plus manager-side changes.
- Main was not force-pushed, and the dirty 1.0.228 worktree was not auto-stashed/rebased. Before integrating the branch into main, compare the two active product lines and regenerate Graphify from the chosen combined tree.
