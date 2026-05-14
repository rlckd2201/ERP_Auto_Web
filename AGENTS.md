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
