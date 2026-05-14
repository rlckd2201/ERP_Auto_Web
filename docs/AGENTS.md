## Project Memory Lite

This project uses lightweight project-local memory files. Use them to preserve durable context without rereading the entire codebase every session.

Default workflow:
- Read `PROJECT_STATUS.md` first before starting project work, and update it before ending a meaningful work session.
- Before code changes, quietly read `docs/AI_HANDOFF.md` and `PROJECT_STATE.md` if present.
- Before editing code, create a timestamped backup copy of the files that will be changed.
- Read `DEVLOG.md`, `docs/FEATURE_LEDGER.md`, `docs/DECISIONS.md`, `docs/USER_FEEDBACK.md`, and `graphify-out/GRAPH_REPORT.md` only when the task needs that deeper context.
- After meaningful code, behavior, architecture, or durable decision changes, update the relevant memory files briefly.
- Skip memory updates for casual chat, one-off explanations, temporary checks, tiny typo-only edits, and unrelated non-project tasks.
- Keep memory entries concise. Do not paste full conversations or large command output.

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
