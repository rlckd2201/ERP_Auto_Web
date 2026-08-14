# Debug

Updated: 2026-08-14

## I-001 — backend static frontend dependency was missing — resolved

- Symptom: tracked `web_v1/frontend/*` files were deleted in the worktree while `app.py` served that directory.
- Resolution: restored HEAD-identical static files, verified later `index.html` from fix210, and verified later `app.js` from fix214.
- Check: JavaScript syntax and DOM-reference audit passed; all required frontend files exist.

## I-002 — required setup EXE was missing — resolved

- Symptom: `AccountingWebRequiredSetup.cs/.exe` were deleted, causing the installer endpoint to return 404.
- Resolution: restored Git HEAD content; all audited preserved copies were byte-identical.
- Check: restored hashes match Git HEAD.

## I-003 — Zoom module was untracked — resolved

- Symptom: `mail_collector.py` imported `web_v1/backend/zoom_billing.py`, but the module was not tracked.
- Resolution: retained the current 10,279-byte file; SHA-256 `96945EDBEEA011150B7D9CAD32F75979B345E4D5BE55AC561F78C67E6D5A3397` matches recent preserved candidates.
- Check: Python compilation passed with the importing mail/backend modules.

## I-004 — Graphify corpus was polluted — resolved

- Symptom: the prior report analyzed 2,418 files, including historical `_codex_*` and release/stage/check copies.
- Resolution: added `.graphifyignore`, preserved the old graph under an ignored local backup directory, and regenerated the tracked outputs.
- Check: 64 files, 1,458 nodes, 4,187 edges, 32 communities, and zero historical source-path hits.

## I-005 — patch tool limitation — contained

- Symptom: the patch tool repeatedly hung while adding or updating Markdown in this Windows workspace.
- Workaround: after confirming repeated failure, state/documentation files were written with explicit UTF-8 paths through PowerShell. Runtime source code was not edited through this workaround.

## I-006 — deployment E2E not executed — open verification boundary

- Not run: live FastAPI startup, installer HTTP response, manager-PC Agent claim/complete, ERP GUI, local printer, and real output-set completion.
- Reason: these paths can start schedulers or require deployment credentials, GUI state, printer mappings, and `C:\ERP_DB`.
- Risk: environment-specific startup or integration failures remain possible despite successful static/syntax checks.
- Next check: follow the exact sequence in `SESSION.md` on a controlled deployment-compatible host.

## I-007 — origin/main advanced concurrently — isolated safely

- Symptom: push to main was rejected because the remote advanced from the local base to `c20a96c`.
- Remote scope: new `excel_voucher_web`, extensive manager-side fixes, and overlapping AGENTS/Graphify outputs.
- Containment: no force push, no automatic dirty-worktree rebase, and no user changes stashed or overwritten. The focused commit is published on `codex/reconcile-state-20260812`.
- Next check: compare product ownership and graph scope before cherry-picking or merging into main.

## I-008 — WEHAGO saved the surrounding web page — resolved

- Symptom: the operating server produced a 156,339-byte Chrome/Skia PDF containing WEHAGO status controls instead of the tax invoice alone.
- Expected reference: a 169,651-byte, one-page Developer Express PDF containing only the invoice.
- Resolution: browser-PDF fallback is rejected; only the Duzon native print path can become canonical.

## I-009 — WEHAGO native print/save timing and UI handling — resolved

- The print runtime was killed before its delayed preview appeared; retries now keep it alive and wait longer.
- Preview detection recursively scanned unrelated Chrome UI and missed the already-open title; detection is now title-only.
- The PDF button opens Save As directly on the installed runtime; the obsolete second print click is skipped when that dialog exists.
- Save As now receives the final path with synchronous `WM_SETTEXT` and confirms Save with synchronous `BM_CLICK`.
- Verification: 12 WEHAGO unit tests pass. Production retry job `0f382cd4-db29-4225-980f-0f0930c22aa0` finished with zero failures. The server-created PDF is 169,685 bytes, Developer Express v15.1.7, one page, and is visually equivalent to the manual normal PDF.
