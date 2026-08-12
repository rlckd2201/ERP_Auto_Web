# Debug

Updated: 2026-08-12

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
