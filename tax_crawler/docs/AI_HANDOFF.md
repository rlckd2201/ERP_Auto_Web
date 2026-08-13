> **Historical record — not the current source of truth.**
>
> This file preserves earlier requirements, decisions, or verification. For current work, read `SESSION.md`, `TODO.md`, `DECISIONS.md`, and `DEBUG.md` first; read `web_v1/VERSION` for the active branch version (integration baseline: `1.0.164`).
> Current U+ state (2026-08-12): the exclusion statements below are historical. Current `tax_crawler/crawler_main.py` registers `UplusHandler` and eligible `edocu.uplus.co.kr` routing.

# AI Handoff

Updated: 2026-04-28

This project is a Python tax-invoice crawler module used by an accounting automation workflow. Start with `crawler_main.py` for the public API and `base_handler.py` for shared Selenium/download behavior.

Recent setup work:
- Graphify is installed and output lives in `graphify-out/`.
- Project Memory Lite is now applied through `AGENTS.md`, `PROJECT_STATE.md`, `DEVLOG.md`, and this `docs/` memory set.

Useful next checks:
- AutoEver and KT are now included in active `crawler_main.py` routing.
- U+ is intentionally excluded from active mail detection and automation.
- Important: `W00127***` KT mails must be ignored by automation and handled manually by the user.
- KT handler now decrypts local PDFs without launching Chrome.
- Next likely focus: HomeTax sample HTML authentication/parsing precision, then CSBill sample URL parsing/file naming.
- Re-run `graphify update .` after meaningful code changes.
