# Project Status

Updated: 2026-05-14

## How To Use This File

- Read this file before starting work.
- Update this file before ending a meaningful work session.
- This file must be enough to recover goals, decisions, changed files, remaining work, tests, deployment ZIP, and cautions after context compaction.
- When commands are requested, provide copy-pasteable command blocks without `1.`/`2.` prefixes inside the commands.

## Current Goal

WEB v1.0 accounting automation is replacing the old CS desktop accounting flow.
The active focus is purchase one-click processing, automatic mail collection, and simplified manager UI:

- Multiple selected purchase invoices should run through one simple `one-click processing` flow.
- One-click should cover ERP input, ERP voucher PDF save/upload, cash withdrawal report creation, output-set refresh, and selected output target.
- The manager default UI should stay simple; debug logs and individual analysis/output buttons should live in detail/admin mode.
- Mail collection should run automatically every minute while the operating server is running.

## Active Architecture Decisions

- ERP GUI automation must run on the manager PC Agent, not on the operating server.
- The operating server has no Excel installed. Excel COM/PDF export work must run on the manager PC Agent.
- Cash withdrawal/expense reports must use the prepared Excel template. Do not silently create arbitrary WEB-drawn fallback PDFs.
- Manager PC cash report template target is `%APPDATA%\양식_현금출금정산서.xlsx`; if it exists, leave it untouched.
- ERP voucher PDF saving should be automatic and uploaded back to the server by the Agent.
- After ERP input completes successfully for a purchase invoice, the server should queue an `expense_report` Agent task automatically.
- Output target options are fixed to `통합본 PDF 저장`, `평택 프린터`, `김제 프린터`.

## Latest Implemented State

- Current WEB/Agent version in files: `1.0.89`.
- Previous deployable ZIP before current one-click UI cleanup: `C:\Tmp\accounting_web_v1_autorefresh_autoexpense_fix96_20260514_094000.zip`.
- Latest local deployment ZIP after source restore/rebuild: `C:\Tmp\accounting_web_v1_one_click_full_rebuild_fix101_20260514_121500.zip`.
- `fix98` still had backend/version mismatch symptoms in the active workspace. Rebuilt `fix101` after restoring the missing backend one-click API, mail status API, scheduler wiring, Agent default printer reporting, and WEB/Agent `1.0.89` version files.
- Backend has new `POST /api/jobs/purchase-one-click`.
- Backend has new `GET /api/mail-collect/status`.
- Backend startup starts a 1-minute mail collection scheduler with duplicate-run prevention.
- Mail collector now records `saved_invoice_ids`; worker auto-analyzes newly saved purchase invoices.
- Agent preflight now reports Windows default printer as `default_printer`.
- Setup status exposes `capabilities.default_printer`.
- Frontend has one-click output target combo and localStorage preference.
- Frontend routes purchase ERP button to `/api/jobs/purchase-one-click`.
- Frontend has mail auto-collection summary text.
- Frontend hides mail collect/log/debug panels in simple mode via `admin-only`.
- Frontend hides purchase `분석` and `분석 저장` buttons in simple mode via `admin-only`.
- Graphify was updated after restoring the one-click source.
- Graphify was updated again after the `fix101` backend/Agent/version repair.

## Recently Changed Files

- `web_v1/backend/app.py`
- `web_v1/backend/job_store.py`
- `web_v1/backend/mail_collector.py`
- `web_v1/backend/models.py`
- `web_v1/backend/setup_state.py`
- `web_v1/backend/worker.py`
- `web_v1/agent/erp_agent.py`
- `web_v1/deploy/install_operating_server.ps1`
- `web_v1/frontend/app.js`
- `web_v1/frontend/index.html`
- `web_v1/frontend/styles.css`
- `web_v1/VERSION`
- `PROJECT_STATUS.md`

## Verification Results

- `py_compile` passed for all `.py` files directly under:
  - `web_v1/backend`
  - `web_v1/agent`
- `node --check web_v1/frontend/app.js` passed.
- `web_v1/frontend/index.html` now has `admin-only` on both purchase analysis buttons.
- `fix101` ZIP content verification passed for `web_v1/VERSION`, `purchase-one-click`, `mail-collect/status`, `_start_mail_collect_scheduler`, `purchase_one_click`, `auto_analyzed_count`, `default_printer`, `oneClickOutputTarget`, and `원클릭 처리`.

## Open Work

- End-to-end verify on operating server and at least one manager PC:
  - multiple selected invoices run sequentially,
  - ERP failure stops remaining invoices,
  - expense report job runs after ERP,
  - output set refreshes after each event,
  - selected output target produces merged PDF or printer output.
- Verify automatic mail collection scheduler with real unread mail and Compuzone quote auto-attach.
- After deploying this ZIP, manager PCs may require Agent update because the Agent bundle hash changes with backend/agent/version files.

## Operational Cautions

- Operating server path:
  - `C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version`
- Local development path:
  - `C:\Users\user\Desktop\개발파일\회계업무 자동화_WEB_Version`
- Because backend files are included in the Agent bundle hash, manager PCs may show latest-version-required after this update. Run the required setup/installer on manager PCs after deploying the server ZIP.
- User expects clean command blocks without `1.`/`2.` prefixes inside the commands.
- Large feature updates or high-volume work should be committed and pushed to `origin` (`https://github.com/rlckd2201/ERP_Auto_Web`) after verification, using a focused commit that excludes pycache, temporary ZIPs, and unrelated backup folders.
- Keep Graphify current: inspect `graphify-out/GRAPH_REPORT.md` before architecture/codebase questions and run `graphify update .` after meaningful code changes.
