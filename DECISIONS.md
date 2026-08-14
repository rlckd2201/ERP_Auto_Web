# Decisions

Updated: 2026-08-14

## D-001 — actual code is the source of truth

When old Markdown, Graphify output, and current code disagree, verify the active root and follow current code. Update documentation; do not change runtime behavior merely to match stale documents.

## D-002 — preserve the operating-server/Agent split

Current implementation keeps orchestration, mail, database, and document-set work on the operating server while manager-PC Agent handles ERP GUI, Excel COM, and local printing. The external ERP RFP is a future official-integration target and does not redefine the current architecture.

## D-003 — no destructive cleanup

Historical `_codex_*`, `_release_*`, `_hotfix_*`, ZIP, and backup artifacts are not deleted in this task. `.gitignore` and `.graphifyignore` exclude local investigation/stage copies without altering their contents.

## D-004 — canonical session memory

Use `SESSION.md`, `TODO.md`, `DECISIONS.md`, and `DEBUG.md` as the compact current handoff. Older status, devlog, and AI-memory files remain historical references.

## D-005 — behavior-preserving asset sources

- Restore setup `.cs/.exe` from Git HEAD; audited copies are byte-identical.
- Keep the current 10,279-byte `zoom_billing.py`; it matches the newest preserved candidates.
- Restore frontend static files from HEAD, `index.html` from fix210, and `app.js` from fix214 so later UI behavior is not reverted.

## D-006 — Graphify scope follows active source roots

Use `.graphifyignore` to exclude generated outputs, local investigations, release/check/stage copies, recursive support copies, and standalone audit utilities. The regenerated graph covers 64 active code files with zero historical source-path hits; preserve `graphify-out/GRAPH_REPORT.md`, `graph.json`, and `graph.html` as the tracked navigation outputs.

## D-007 — distinguish static verification from operational E2E

Syntax, imports referenced in source, DOM mappings, artifact presence, hashes, and graph scope are safe local checks. Starting schedulers or exercising ERP GUI, credentials, printers, and production-like queues requires a controlled deployment environment and remains explicitly unverified here.

## D-008 — preserve concurrent remote work

When `origin/main` advanced to `c20a96c`, do not force-push or rebase through the dirty WEB/Agent 1.0.228 worktree. Publish the focused reconciliation commit on `codex/reconcile-state-20260812`; integrate only after comparing the independently added `excel_voucher_web`, manager changes, current-state documents, and Graphify scope.

## D-009 — WEHAGO accepts native PDFs only

A WEHAGO result is valid only when its producer is Developer Express/DXperience and invoice identifiers are present. Chrome/Skia captures of the surrounding web page remain blocked even if they contain readable invoice text.

## D-010 — server-session native controls are authoritative

Do not depend on foreground RDP mouse control. Detect the Duzon preview by window title and use Win32 messages for the PDF, filename, and Save controls. Avoid recursive UI-tree enumeration of Chrome and the Duzon report viewer.

## D-011 — a successful duplicate is not a collection failure

When a retried mail produces and validates its native PDF but its invoice identity already exists, report it as a duplicate with zero failures. Do not create a second DB row solely to prove retry success.
