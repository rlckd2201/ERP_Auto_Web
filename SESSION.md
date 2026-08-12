# Session

Updated: 2026-08-12

## Current objective

Resolve important documentation, packaging, tracking, and Graphify inconsistencies without changing established runtime behavior.

## Status

Reconciliation is complete. Required served/imported artifacts are present, current-state documents match the active code baseline, and Graphify now excludes historical work copies.

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

If operational validation is required, start the server in a controlled deployment-compatible environment, verify `/health` and `/api/setup/user-pc-installer.exe`, then exercise one non-production Agent queue/output-set job before any new feature work.

## Release handoff

- Focused reconciliation changes are published on `codex/reconcile-state-20260812`.
- `origin/main` advanced independently to `c20a96c` during this work and includes a new `excel_voucher_web` subsystem plus manager-side changes.
- Main was not force-pushed, and the dirty 1.0.228 worktree was not auto-stashed/rebased. Before integrating the branch into main, compare the two active product lines and regenerate Graphify from the chosen combined tree.
