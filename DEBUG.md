# Debug

Updated: 2026-08-21

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

## I-006 — deployment E2E boundary — partially resolved

- Live verified: FastAPI restart and `/health`, Agent bundle update, Agent claims, Excel report generation/upload, output-set creation, Pyeongtaek printing, and Windows spooler submission.
- Still not rerun: installer download and ERP GUI entry. ERP was intentionally excluded to avoid duplicating completed accounting work.
- Next safe check: installer response plus a controlled non-production ERP case.

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

## I-010 — cash-disbursement author used Agent login fragment — resolved

- Symptom: `#206` and `#207` displayed `작성자 reum` instead of `작성자 구름`.
- Root cause: one-click frontend payload hard-coded `processor: "WEB v1.0"`; server fallback derived `reum` from Agent ID `reum-reum`, which does not match auth user ID `reum0009`.
- Operational repair: set both invoice processors/authors to `구름`, preserve prior PDFs as `pre_regen` backups, regenerate through the connected user-PC Agent, save individual PDFs, and print only the two corrected cash-disbursement documents.
- Verification: both PDFs are one-page A4, extracted text contains `작성자 구름` and no `reum`, visual renders are clean, and print job `3ef76859-c824-421d-96fa-4ecb493e6d3f` reports `2/2` Windows spooler submissions.
- Permanent resolution: authenticated WEB user identity is resolved to a canonical display name on the server; unique legacy prefixes remain supported, while Agent/machine IDs cannot become authors. The fix is deployed on 121 and the focused regression tests pass.

## I-011 — duplicate 12:00 regular-due status messages — guard deployed, observation pending

- Symptom: a correct `[정상]` message arrived around 12:00:10, followed by a stale `[누락]` message around 12:00:25 with old counts and a loopback history URL.
- Evidence: the valid sender reported the current `https://172.17.39.121:8080/regular-due-history` state from PID 11160 on `WIN-2H29RFPBUMN`; the stale copy used `http://127.0.0.1:8080/regular-due-history` and obsolete waiting/completion data.
- Fix deployed: regular-due alert sending requires explicit enablement and canonical hostname `WIN-2H29RFPBUMN`; wrong-host/default-disabled/enabled-host regression tests pass.
- Boundary: observe the next real 12:00 run and confirm exactly one message.

## I-012 — first corrected-source deployment reported a false test failure — resolved and deployed

- Symptom: 121 returned `ok=false` with `test_login_binds_user_to_agent (...) ... ok` as the error text.
- Root cause: Python `unittest -v` writes normal progress to stderr, and PowerShell with `ErrorActionPreference=Stop` converted that stream into a terminating native-command error.
- Resolution: compile/tests now run through `cmd.exe /d /c ... 2>&1`; `$LASTEXITCODE` is the only success criterion. The first attempt restored all five backed-up source files before touching the backend process.
- Final state: the corrected deploy completed at `2026-08-21T09:54:20`; six focused tests, import, database initialization, restart, and health all passed.

## I-013 — historical author variants on four rows — resolved

- Corrected: `#176=구름`, `#179=구름`, `#180=김기창`, and `#205=현시훈`; old reports were copied to `C:\ERP_DB\backups\document_actor_repair_20260821_095421`.
- `#205` retained its existing ERP error and ERP was not rerun. The repair print queue verified four submissions.
- Already-correct `#206` and `#207` remained `구름` and were excluded from duplicate repair printing.

## I-014 — cash-disbursement PDF was undersized; required direction clarified — resolved

- Symptom: the form was small because the Excel print area included unused rows 21–42. An interim correction changed the document to landscape, but the user clarified that the required physical direction is portrait.
- Root cause: `PrintArea = "$A$1:$R$42"` included 22 blank rows although the form ends at row 20. Landscape was an incorrect requirement assumption, not the desired final output.
- Resolution: restore portrait A4 (`1`), keep corrected print area `$A$1:$R$20`, deploy to 121, and let both generation Agents update.
- Verification: final `#176`, `#179`, and `#180` PDFs are each one `595.20 x 841.68` portrait page and preserve authors `구름`, `구름`, and `김기창` without Agent-ID text.
- The interim landscape output job `ab3d3fc6-8351-4586-9e91-2a0c9e206452` was superseded. Final portrait regeneration completed with `print_skipped=true`; no additional paper was submitted.

## I-015 — backend deployment process/health detection was too broad — resolved in deployment tooling

- A stale listener PID and loopback HTTPS health request caused false deployment failures even while Uvicorn was starting correctly.
- Deployment now targets only Python processes whose command line matches `-m web_v1.backend`, checks `https://172.17.39.121:8080/health`, and accepts the Uvicorn startup log only as a bounded fallback.
- The final portrait deployment restarted the backend to PID `7360` and returned healthy version `1.0.228`.
