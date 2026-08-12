## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## Git / release hygiene

- For large feature updates or high-volume work, create a focused git commit and push it to `origin` (`https://github.com/rlckd2201/ERP_Auto_Web`) after verification.
- Before committing, check `git status` carefully and stage only relevant source/docs/config changes. Avoid committing generated caches, pycache files, temporary ZIPs, and unrelated backup/stage folders unless explicitly requested.
- Keep Graphify current during these larger updates: inspect the graph before architecture/codebase questions and run `graphify update .` after meaningful code changes.

## Session workflow

- Restore context in this order: `SESSION.md`, `TODO.md`, `DECISIONS.md`, `DEBUG.md`, Graphify, then only the directly relevant source files.
- Treat active source as authoritative when documents or generated graphs disagree with code.
- Keep chat concise. Store reusable state, decisions, and debugging evidence in the four session documents without duplicating the same information.
- The primary agent owns requirements, architecture, compatibility decisions, integration, and final review. Delegate only bounded implementation, research, and verification work.
- Parallelize only independent work and assign non-overlapping file ownership. Preserve unrelated worktree changes.
- Before implementation, present the approach, agent/model roles, and expected change scope, then wait for approval.
- Do not delete existing behavior or make destructive/compatibility-breaking changes without explicit approval.
- Before ending a meaningful session, update all four session documents, record verification and remaining risks, and confirm the next exact starting point.
