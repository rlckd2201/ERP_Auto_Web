# Decisions

Updated: 2026-08-25

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

## D-015 — cash-disbursement PDFs use portrait A4 and the form's real bounds

The Excel export helper must explicitly use portrait A4 and print area `$A$1:$R$20`, the actual cash-disbursement form. Do not include the template's unused rows 21–42 because they shrink the form. Landscape output is not the required physical print direction. A regenerated server file must be one portrait page and retain the canonical author.

## D-016 — final printing follows server-file visual verification

For layout corrections, first regenerate without printing and validate the exact server PDFs. Do not submit test pages unless the user explicitly requests another print. A successful generation job alone is insufficient; orientation, page size, and author must match the requirement while ERP status remains unchanged.

## D-017 - the noon sender is a process-wide singleton

Canonical hostname and explicit enablement remain necessary, but they are not sufficient when stale backends survive on the same server. The regular-due scheduler must acquire a non-blocking OS file lock in `C:\ERP_DB` before its thread starts. Only one canonical Common Startup link may launch the backend, and deployment must reject any additional 8080 listener. Sender host/PID headers and lock-owner status are retained as operational evidence.

## D-018 - Excel paper-size selection is opportunistic; the PDF contract is authoritative

Printer drivers can reject Excel's `PageSetup.PaperSize` setter even when the template can still export. Cash-disbursement generation must therefore keep portrait orientation, `$A$1:$R$20`, and one-page fit, tolerate only the paper-size setter failure, and enforce the final contract by vector-normalizing the exported file to one exact portrait-A4 page. Automatic Zoom retries use a 600-second cooldown so a persistent workstation/driver fault cannot create a failure job every minute; explicit user requests bypass that cooldown.

## D-019 - Gemini configuration stays external and uses the maintained SDK

Purchase analysis uses `google-genai`, reads both API key and model from environment-backed settings, and defaults the model to `gemini-3.7-flash`. Secrets must remain in the operating server's `.env` and must not enter source, tests, logs, or session documents. On the Windows operating server, Google API clients use a `truststore.SSLContext` so certificate validation follows the Windows trust store; certificate verification is never disabled.

## D-020 - do not silently substitute a model in comparisons

If the requested historical model is no longer callable, report that boundary and use clearly labeled historical outputs only when the source proves which model produced them. Do not replace `gemini-2.5-flash` with 3.6 or another model and present that as a 2.5 comparison. A fair live comparison keeps the same source PDFs, prompt, parser context, JSON mode, and temperature.

## D-021 - Gemini uploads use disposable ASCII filenames

Keep original Korean document paths and filenames unchanged in ERP storage, but copy the two upload inputs into a bounded temporary directory as `tax_invoice.pdf` and `quote.pdf`. Upload only those copies, remove the temporary directory on every exit path, and delete every successfully created remote Gemini file in `finally`.

## D-022 - Gemini request retries are bounded once

The SDK request timeout is 60 seconds and its total attempt count is 2, with a one-second initial delay and five-second maximum delay. Callers must not add another retry loop around `_ai_parse`; a failed bounded request falls back to the fast parser so a transient provider outage cannot hold the purchase workflow indefinitely.

Production acceptance for document-upload changes uses an existing invoice through `_ai_parse` directly, never the persistence API. The check must prove the result model and totals, temporary-file cleanup, and unchanged invoice state before and after the call.

## D-023 - management benefits use operating evidence plus disclosed assumptions

The executive deck uses the current read-only invoice mix and date window for volume, but it does not present unmeasured handling times as observed facts. Regular `20 -> 5 minutes` and purchase `35 -> 8 minutes` are conservative pre-interview assumptions, shown directly on the calculation slide and in speaker notes. Future revisions replace those values only with measured operator data; the value case emphasizes deadline stability, error reduction, traceability, and search-time reduction rather than headcount removal.

## D-024 - external-development cost is a planning range, not a quote

Use official 2026 Korea AI Software Industry Association applied-SW wage data as the labor baseline, then account for analysis, UI/data/log implementation, ERP/portal/AI integration, testing, deployment, documentation, warranty, and integration risk. Present `KRW 55-80 million` initial build and `KRW 6-12 million` annual maintenance as a realistic planning range with VAT, infrastructure, and paid licenses separate. Actual procurement requires scoped vendor quotations.

## D-025 - the executive deck shows business outcomes before operating detail

Use a 12-slide flow of impact, automation scope, actual function/output evidence, simplified operator work, time/cost reduction, and replacement value. Exclude error-log and retry mechanics from the main deck. Feature slides use newly captured application content without browser chrome, and output claims use actual generated voucher/report files. Every title stays on one line; measured operating data and planning assumptions remain visibly separated.

## D-026 - automation elapsed time is not labor time

Count only the operator's active click and result-confirmation time after adoption; exclude unattended system processing because the operator can continue other work. For the executive floor calculation use one hands-on minute per case, 240 regular cases/year from completed-month production volume, 250 purchase cases/year from the user-supplied operating average, and the official 2026 minimum wage of KRW 10,320/hour. Treat external rebuild and outsourced-maintenance estimates as appendix replacement references, never as the current system's operating cost or direct ROI denominator.

## D-027 - slide titles name the subject instead of stating the whole argument

Use concise functional titles such as `원클릭 회계처리`, `연간 업무시간 절감`, and `운영 경제성 판단`. Do not repeat time/cost metrics in the system-summary slide; reserve quantitative evidence for its dedicated impact slides. Merge redundant overview slides before adding more pages.

## D-028 - ERP retry requires proof that the prior save did not commit

A missing voucher PDF does not prove that the ERP voucher itself was not saved. The current flow sends Ctrl+S before opening RD Viewer, and a later print failure can therefore leave a committed ERP voucher behind. Do not automatically retry or re-enter such a purchase job until K-System is checked for an existing voucher. Management-item completion must mean that the selected ERP relation value was read back and matched, not merely that a paste/Enter sequence was sent.

## D-029 - purchase and regular ERP automation use separate runtime profiles

Keep the slow-PC safeguards for `regular_auto` on the 243 PC. Apply the faster navigation, field-verification, management-item, progress, and output timeouts only to interactive purchase tasks on ordinary operator PCs. A fast path may skip redundant scans only when the existing final form-readiness check and fallback remain in place.

## D-030 - vendor selection is exact and post-save output failure is a guarded state

Every vendor relation row must close any stale popup, open the popup from the current row, and select a result whose normalized business number exactly matches the requested 10 digits. Never infer success from keyboard input alone. After Ctrl+S, failure to open RD Viewer, open the print dialog, or create the PDF must raise `[ERP_SAVE_CONFIRM_REQUIRED]`; automatic/direct retry is blocked until the operator checks K-System and explicitly resets the invoice.

## D-031 - production deployment does not use a save-risk invoice as its acceptance test

Deploy and verify source hashes, tests, HTTPS health, version, listener ownership, scheduler lock, Agent heartbeat, and bundle hash without running ERP input. When an earlier attempt may already have committed through Ctrl+S, first inspect K-System for the existing voucher. Validate live exact-vendor selection on the next safe new purchase case, not by replaying the risky invoice.

## D-032 - critical ERP header fields never use the purchase global-fast path

Purchase tasks may optimize menu navigation, progress posting, grid management, and output polling, but 회계단위, 전표관리단위, and 회계일 must retain stable key pacing and mandatory value read-back. After a field or dropdown transition, reconnect the active K-System main window before continuing if the UIA provider is invalid. A disconnected or unverifiable header is terminal before grid management and before Ctrl+S; cached screen coordinates are not sufficient proof that the ERP form is still valid. This narrows D-029: purchase speed improvements cannot include skipping verification of critical header fields.

## D-033 - do not run a self-updating Agent against an editable mismatched worktree

When the local source tree is newer than the production Agent bundle, stop only the exact Agent process before editing or verification. Otherwise its normal self-update can replace in-progress source and test files with the older server bundle. Restart the Agent only after production publishes the matching version and verify both version and bundle hash through setup status.

## D-034 - K-System vendor selection uses the proven default-focus keyboard contract

Live inspection supersedes the exact-result portion of D-030: the vendor popup's visible result grid does not expose rows or cells through UI Automation, so an exact UIA result-cell scan cannot validate or select a vendor. Do not call `popup.set_focus()`, infer/click a search Edit, or scan UIA result cells. Close any stale popup, open the current row's popup, preserve its default search-box focus, and use the established business-number sequence `Ctrl+A / paste / Tab 4 / Down 5 / Up 1 / Tab 3 / Enter 2`. Purchase tasks retain conservative management timing; ordinary-PC speed optimization remains limited to safe navigation and does not alter the 243-PC regular profile.

Direct acceptance may use an existing payload only when the save function is replaced with a hard pre-save stop and Ctrl+S is impossible. A visible final management value plus the pre-save stop is required evidence. This does not clear the duplicate-save risk from older runs that already sent Ctrl+S.
