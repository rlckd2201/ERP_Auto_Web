> **Historical record — not the current source of truth.**
>
> This file preserves earlier requirements, decisions, or verification. For current work, read `SESSION.md`, `TODO.md`, `DECISIONS.md`, and `DEBUG.md` first; read `web_v1/VERSION` for the active branch version (integration baseline: `1.0.164`).
> Current U+ state (2026-08-12): the exclusion statements below are historical. Current `tax_crawler/crawler_main.py` registers `UplusHandler` and eligible `edocu.uplus.co.kr` routing.

# User Feedback

## 2026-04-28

- User wants this folder treated as the final-file-only working set for unfinished mail-received tax invoice PDF saving modules.
- User wants future work to focus on completing and refining portal parsing/PDF save behavior together, not replacing the existing module structure.
- User explicitly marked KT `(W00127***)` as manual/ignored for automation.
- User explicitly said to exclude U+ from the active scope.
- User requires backups before code work.
- User wants PDF filenames to include the business/site name, not just the legal entity name, because one legal entity can have multiple business registrations.
- User says most period classification can be determined from the tax invoice item/product name.
