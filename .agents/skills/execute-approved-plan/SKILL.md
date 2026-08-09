---
name: execute-approved-plan
description: Safely and strictly execute a persisted Markdown Execution Plan that a human or Planner has already approved. Use when the user explicitly supplies a repository plan path whose front matter status is APPROVED and asks Codex to implement it, validate it, enforce allowed and forbidden file scope, and write an execution report. Do not use to draft, revise, approve, broaden, merge, release, or infer a plan, or when no exact plan path is supplied.
---

# Execute Approved Plan

Execute one approved plan without changing its goal, scope, architecture, or approval state. Treat repository instructions and explicit project rules as higher priority than the plan. Stop when safe execution requires a planner decision.

## Required input

Require one exact repository-relative Markdown plan path. If it is absent or ambiguous, ask for it and make no repository changes. Never guess the newest plan.

## Discover rules

1. Locate the Git repository root.
2. Read Codex instructions and every applicable root or nested `AGENTS.md` from the repository root to each target path.
3. Read the supplied plan.
4. Read every path listed under `Project Rules`.
5. Apply precedence: platform rules, repository instructions, nested instructions, explicit project rules, then the approved plan.
6. Return `PLAN_CHANGE_REQUIRED` if a higher-priority rule makes the plan impossible.

## Validate before changing files

Run:

```text
python scripts/validate_execution_plan.py <PLAN_PATH> --approved
```

Stop with `PLAN_NOT_APPROVED` or the validator's failure details if validation fails. Do not modify the plan to make it pass. Never change `DRAFT` to `APPROVED`.

## Enforce Git safety

1. Record `git status --short`, `git branch --show-current`, and `git rev-parse HEAD` as the start state.
2. Stop with `BLOCKED / DIRTY_WORKTREE` if unrelated work is present. Do not reset, clean, checkout, stash, overwrite, or delete it.
3. Verify that `base_commit` is an ancestor of `HEAD` with `git merge-base --is-ancestor` rather than requiring equality. Stop with `PLAN_BASE_MISMATCH` when histories are incompatible.
4. Never implement on `main` or `master`.
5. Use the exact branch from the plan. If it does not exist, create it only when the worktree is clean and the base check passed. If it exists, switch only when safe.
6. Do not commit, push, open a pull request, merge, tag, or release as part of this skill.

## Perform preflight scope checks

1. Parse `Allowed Files` and `Forbidden Files`.
2. Treat a trailing `/` as recursive directory scope; otherwise treat a path as exact.
3. Give forbidden paths absolute precedence over allowed paths.
4. Confirm every expected task deliverable fits the allowed scope and does not hit forbidden scope.
5. Confirm the execution report path is allowed.
6. Stop with `PLAN_CHANGE_REQUIRED` if the plan contradicts its own scope.

## Execute tasks sequentially

1. Work through `Tasks` in listed order and focus on one task at a time.
2. Make only the smallest changes necessary for the current task.
3. Do not add features, perform opportunistic refactors, resolve unrelated TODOs, change architecture, or implement later plans.
4. Record useful out-of-scope ideas under `Suggested Follow-ups`; do not implement them.
5. After every material task, inspect `git status` and `git diff`, then run:

```text
python scripts/check_execution_scope.py <PLAN_PATH>
```

6. Stop immediately on a scope violation. Do not add more changes to repair an unauthorized change.

## Run validation

1. Execute every command listed under `Required Validation` exactly and record its real exit status and output summary.
2. Perform every feasible `Manual Validation`; mark the rest `NOT_TESTED` for human review.
3. Never delete tests, add skips or xfails, weaken assertions, swallow exceptions, or fabricate results to make validation pass.
4. Fix failures only inside approved scope. Return `PLAN_CHANGE_REQUIRED` when a valid fix needs wider scope.

## Perform final safety checks

1. Run `git diff --check`.
2. Run the scope guard again.
3. Inspect `git status --short` and record `git diff --stat`.
4. Check for secrets, credentials, binary artifacts, caches, build outputs, and local environment files.
5. Stop if any unsafe artifact is present.

## Write the execution report

Create the report at the plan's `report_path` without modifying the plan status. Follow [references/execution-report.md](references/execution-report.md) exactly. Report actual commands and outcomes rather than generic claims.

Use only these final states:

- `READY_FOR_REVIEW` after compliant completion.
- `PLAN_CHANGE_REQUIRED` when a planner decision or scope change is required.
- `BLOCKED` for environmental, safety, or unrelated-work blockers.

## Mandatory stop conditions

Stop rather than deciding for the Planner when:

- a forbidden file must change;
- a public interface, dependency, architecture, or goal change was not authorized;
- an input or prerequisite is missing;
- plan assumptions contradict the repository;
- a test can pass only by expanding scope or weakening standards;
- a secret or sensitive value is found;
- a destructive Git or filesystem operation is required;
- the work materially exceeds the stated goal.

When returning `PLAN_CHANGE_REQUIRED`, identify the current task, blocking assumption, required out-of-scope file or interface, why execution cannot continue, and the decision needed.

## Forbidden behavior

Never create, approve, or rewrite a product plan; infer approval from chat; silently deviate; hard-code project-specific rules; rely on chat context instead of repository artifacts; touch files outside scope; hide failures; or automatically publish the result.
