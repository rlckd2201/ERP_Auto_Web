# Decisions

Updated: 2026-08-13

## D-001 — active source is authoritative

When Markdown, Graphify, preserved work copies, and current code disagree, follow the active branch's source. Version claims must match `web_v1/VERSION` in that branch.

## D-002 — preserve the operating-server/Agent split

`web_v1` keeps orchestration, mail, database, and document-set work on the operating server while a manager-PC Agent handles ERP GUI, Excel COM, and local printing. The ERP API/DB RFP is a future target and does not redefine current runtime behavior.

## D-003 — keep the two web products separate

`web_v1` is the general accounting automation product. `excel_voucher_web` is the independently deployed workbook-to-voucher service on port 8081. They may share the Manager ERP implementation but do not share queues, storage, ports, or release versions.

## D-004 — preserve the verified Manager baseline

Remote `main` contains the 2026-07-27 Excel-voucher baseline that completed 210 ERP rows through save and print. Keep tag `stable-2026-07-27-full-success` as the operational rollback point and do not replace the Manager source with the older reconciliation parent.

## D-005 — isolate integration from the dirty worktree

Build the integration from remote `main` plus reconciliation commit `0fd4f46` in a separate branch. Do not stash, rebase, reset, or overwrite the user's dirty WEB/Agent 1.0.228 worktree.

## D-006 — distinguish committed 1.0.164 from dirty 1.0.228

The integrated branch contains `web_v1/VERSION` 1.0.164. The 1.0.228 value and its related backend, Agent, crawler, and deployment edits exist only in the separate dirty worktree and are not claimed as part of this branch.

## D-007 — do not activate an orphan Zoom module by assumption

`web_v1/backend/zoom_billing.py` is retained from the reconciliation commit, but the integrated 1.0.164 `mail_collector.py` does not call it. The dirty 1.0.228 collector combines Zoom routing with broader mail retry/state changes. Integrate that behavior later as a reviewed unit with tests rather than copying an entangled hunk blindly.

## D-008 — regenerate generated graphs after integration

Graphify output conflicts are resolved using the remote output only as a temporary cherry-pick choice. The final `GRAPH_REPORT.md`, `graph.json`, and `graph.html` must be regenerated from the combined tree; neither parent's generated graph is authoritative.

## D-009 — canonical session memory

Use root `SESSION.md`, `TODO.md`, `DECISIONS.md`, and `DEBUG.md` for repository-wide handoff. Keep detailed Excel-voucher history under `excel_voucher_web/`; older root and crawler logs remain historical references.

## D-010 — separate static verification from operational E2E

Syntax, unit tests, assets, DOM mappings, hashes, and graph scope are local checks. Live schedulers, mailbox access, ERP GUI, credentials, printers, and production queues require controlled deployment environments and explicit operational validation.
