# PR-E Documentation Rebase Note

> Temporary coordination note for open PR #98.

The documentation audit branch deliberately rewrites the shared active-status docs that PR #98 also touches (`ARCHITECTURE.md`, `DATA_SCHEMA.md`, `PROJECT_SPEC.md`, `research/V04_DATA_READINESS.md`).

If this documentation cleanup merges before PR #98, PR #98 should rebase onto the updated `main` and preserve the new documentation ownership boundaries:

- active status remains in `ROADMAP.md` / master plan / data readiness;
- PR-E-specific method/results belong in `docs/research/V04_BASELINE_ORACLE_DIAGNOSTIC.md` and the eventual PR-E completion/freeze record;
- PR-E must not restore stale statements that PR-D or Oracle v2 are unfinished;
- measured PR-E metrics must only be added after the governed local frozen runtime execution;
- 2025 Blind y remains inaccessible.

This note is coordination-only and should be removed in the PR-E integration change after the rebase is complete.
