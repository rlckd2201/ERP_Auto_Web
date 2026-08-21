# Decisions

Updated: 2026-08-21

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

## D-012 — document authors come from authenticated user identity

Cash-disbursement document authors must use the authenticated WEB user's display name (for example, `reum0009` resolves to `구름`). Machine/Agent identifiers such as `reum-reum` are routing identities and must not be shortened into document author names. Existing incorrectly generated reports require both metadata correction and PDF regeneration before printing.

## D-013 — one canonical host owns the noon alert

The regular-due noon status email is permitted only when alerting is explicitly enabled and the running hostname matches `WIN-2H29RFPBUMN`. Copied backend/Agent bundles must remain silent even when they retain mail settings. This prevents duplicate, stale-state `[누락]` messages without weakening the canonical server's check.

## D-014 — historical author repair is recoverable and does not rerun ERP

Before regenerating affected cash-disbursement PDFs, copy the prior reports to a timestamped backup. Correct only author metadata, regenerate through the already connected responsible Agent, preserve any pre-existing ERP error (notably `#205`), and print only the corrected cash-disbursement PDFs. Do not rerun ERP merely to fix a document author.

## D-015 — cash-disbursement PDFs use the form's real A4 landscape bounds

The Excel export helper must explicitly use A4 landscape and print area `$A$1:$R$20`, the actual cash-disbursement form. Do not inherit portrait orientation or include the template's unused rows 21–42, because either condition produces a small form with excessive blank paper. A historical PDF is not accepted for printing until the regenerated server file is one landscape page, has the canonical author, and passes rendered visual review.

## D-016 — final printing follows server-file visual verification

For layout corrections, first regenerate without printing, download the exact server PDFs, render and inspect them, then submit only the verified files. A successful generation job or landscape media box alone is insufficient; the printed form must visibly occupy the intended A4 area. Keep ERP status unchanged during this document-only cycle.
