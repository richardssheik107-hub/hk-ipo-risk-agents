---
plan_id: EXAMPLE-001
title: Add a hello documentation example
status: DRAFT
revision: 1
base_commit: REPLACE_WITH_COMMIT_SHA
branch: docs/example-hello
owner: example-owner
planner: human
executor: codex
report_path: docs/execution/reports/EXAMPLE-001_EXECUTION_REPORT.md
---

# Add a hello documentation example

## Goal

Add one short example document without changing code.

## Background

This business-neutral plan demonstrates the persisted Planner → Executor format. It is deliberately not approved and must not be executed as-is.

## Project Rules

- docs/execution/README.md

## Inputs

- docs/execution/README.md

## Allowed Files

- docs/examples/hello.md
- docs/execution/reports/EXAMPLE-001_EXECUTION_REPORT.md

## Forbidden Files

- src/
- tests/

## Tasks

- [ ] Create `docs/examples/hello.md` with one heading and one sentence.
- [ ] Validate Markdown whitespace.

## Acceptance Criteria

- `docs/examples/hello.md` exists.
- The file contains one level-one heading.
- No source or test file changes.

## Required Validation

```text
git diff --check
```

## Manual Validation

- Confirm the rendered heading is readable.

## Stop Conditions

- Any source or test file must change.
- The requested output requires a dependency.
- Unrelated work exists in the worktree.

## Expected Deliverables

- `docs/examples/hello.md`
- `docs/execution/reports/EXAMPLE-001_EXECUTION_REPORT.md`

## Notes

Example only. A human must replace the base commit and explicitly approve a copied plan before execution.
