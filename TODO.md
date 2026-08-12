# TODO

Updated: 2026-08-12

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
- [ ] Run deployment-environment live E2E for FastAPI startup, installer download, Agent queue, ERP GUI/printer, and output-set completion.

## Remaining item acceptance condition

Use a controlled deployment-compatible Windows host with the expected credentials, GUI, printer mappings, and `C:\ERP_DB`. Confirm `/health`, installer download, one non-production Agent claim/complete cycle, and one output-set result. Do not infer this from static checks.

## Repository integration

- [ ] Reconcile `codex/reconcile-state-20260812` with latest `origin/main` after confirming how the local WEB/Agent 1.0.228 line relates to the independently added `excel_voucher_web` line.
- [ ] Regenerate Graphify after that integration; do not carry either side's graph outputs across the merge without rebuilding.
