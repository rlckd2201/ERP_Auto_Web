# TODO

Updated: 2026-08-13

## P0 — repository integration

- [x] Compare `codex/reconcile-state-20260812` with remote `main` from their common base.
- [x] Confirm product ownership: `web_v1` and `excel_voucher_web` remain separate services.
- [x] Apply reconciliation commit `0fd4f46` on top of remote `main` in an isolated branch.
- [x] Preserve the verified Manager/Excel-voucher line and the user's dirty WEB/Agent 1.0.228 worktree.
- [x] Resolve generated Graphify conflicts without choosing either stale graph as final.
- [x] Record that the integrated branch's committed `web_v1` version is `1.0.164`, not 1.0.228.
- [x] Record that `zoom_billing.py` is not wired into this branch's mail collector.

## P1 — documentation and graph

- [x] Update the four canonical session documents for the combined repository.
- [x] Update current architecture/version documentation for both products.
- [x] Regenerate Graphify from the combined active tree.
- [x] Confirm the graph contains `web_v1`, `excel_voucher_web`, `manager_server`, and `tax_crawler` while excluding historical work copies.

## P2 — static and regression verification

- [x] Compile active Python entry modules for both products.
- [x] Check JavaScript syntax for both frontends.
- [x] Verify `web_v1` static DOM references and required setup assets.
- [x] Run the `excel_voucher_web` regression suite (186 passed).
- [x] Run `git diff --check` and review staged paths.
- [x] Commit and push `codex/integrate-reconcile-20260813` (`f190302`).

## P3 — operational verification

- [ ] Run a controlled `web_v1` health, installer-download, Agent queue, ERP/printer, and output-set E2E.
- [ ] Run a controlled `excel_voucher_web` upload through the 172.17.30.243 Agent, including ERP save, voucher-number recovery, PDF storage, and print.
- [ ] Test actual SMTP delivery for Excel-voucher notifications.
- [ ] Confirm bank/account rules for Daeseung Precision, Ilgang, and JM.

## Acceptance conditions

Repository integration is complete when the combined graph and local regression checks pass and the focused branch is published. Operational items require deployment-compatible Windows hosts, credentials, GUI sessions, printer mappings, and `C:\ERP_DB`; they are not inferred from static checks.

The dirty WEB/Agent 1.0.228 line is a separate future integration unit. Before merging it, inventory its backend, Agent, crawler, deployment, and Zoom mail-collector changes and give it its own versioned regression/release review.
