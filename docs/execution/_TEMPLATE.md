---
plan_id: TASK-001
title: Replace with a concise task title
status: DRAFT
revision: 1
base_commit: REPLACE_WITH_COMMIT_SHA
branch: feat/replace-with-task-branch
owner: project-owner
planner: web-chatgpt
executor: codex
report_path: docs/execution/reports/TASK-001_EXECUTION_REPORT.md
---

# Replace with task title

## Goal

State the one outcome this execution must achieve.

## Background

Explain the current state and why this task is needed.

## Project Rules

- docs/execution/README.md

## Inputs

- List required files, interfaces, data, and prerequisites.

## Allowed Files

- path/to/allowed-file.ext
- path/to/allowed-directory/
- docs/execution/reports/TASK-001_EXECUTION_REPORT.md

## Forbidden Files

- path/to/protected-file.ext
- path/to/protected-directory/

## Tasks

- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

## Acceptance Criteria

- A specific behavior can be judged PASS or FAIL.
- Existing public interfaces remain unchanged.

## Required Validation

```text
replace-with-real-test-command
git diff --check
```

## Manual Validation

None.

## Stop Conditions

- A forbidden file must change.
- A public interface or dependency change is needed but not authorized.
- A prerequisite is missing or a key plan assumption is false.
- Passing validation requires wider scope or weaker tests.
- A secret, unsafe artifact, or destructive operation is encountered.

## Expected Deliverables

- List expected files, behavior, tests, and documentation.

## Notes

Optional planner notes.
