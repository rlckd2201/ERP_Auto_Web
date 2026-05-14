# Decisions

## 2026-04-28 - Use Project-Local Memory

Decision: Apply Project Memory Lite inside this project rather than relying only on chat history.

Rationale: The crawler has multiple portal-specific handlers and local operational conventions. A compact handoff and state file should reduce repeated rediscovery in future sessions.

## 2026-04-28 - Use Graphify For Structure, Not Product Memory

Decision: Keep Graphify as a code-structure map and keep feature rationale, decisions, and user feedback in Markdown memory files.

Rationale: Graphify is useful for module relationships and central files, while project intent and durable notes are easier to maintain in short human-readable docs.

## 2026-04-28 - KT W00127 Manual Handling

Decision: Do not automate KT `(W00127***)` mails.

Rationale: User explicitly said this token should be ignored and entered manually.

## 2026-04-28 - Exclude U+

Decision: Exclude U+ eDocu from active mail detection, routing, and test menus.

Rationale: User explicitly said to remove U+ from the project scope. The existing `portal_uplus.py` file is retained as legacy/reference code unless the user asks to delete it.

## 2026-04-28 - Backup Before Code Edits

Decision: Always create a timestamped backup of files that will be changed before editing code.

Rationale: User explicitly required backups before code work.
