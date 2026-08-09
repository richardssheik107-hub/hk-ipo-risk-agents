# Execution Report Contract

Use this front matter:

```text
---
plan_id: TASK-001
plan_revision: 1
execution_status: COMPLETED
base_commit: <plan base>
start_head: <recorded start HEAD>
end_head: <current HEAD>
branch: <plan branch>
executor: codex
---
```

Use these sections in this order:

1. `Summary`
2. `Plan Compliance`: exactly `COMPLIANT` or `DEVIATION_FOUND`, followed by an explanation when needed.
3. `Files Created`: list paths or `None.`
4. `Files Modified`: list paths or `None.`
5. `Files Deleted`: list paths or `None.`
6. `Tasks Completed`: copy every plan task and mark its real state.
7. `Validation Results`: for each command, record `Command`, `Result` (`PASS`, `FAIL`, or `NOT_RUN`), and a concrete output summary under `Details`.
8. `Acceptance Criteria`: copy each criterion and mark `PASS`, `FAIL`, or `NOT_TESTED`.
9. `Manual Validation`: record completed checks and remaining human checks.
10. `Deviations`: describe deviations or write `None.`
11. `Known Limitations`
12. `Suggested Follow-ups`: suggestions only; do not implement them.
13. `Plan Change Requests`: when relevant, include current task, blocking assumption, required out-of-scope file, required interface change, why the plan cannot continue, and the Planner decision required.
14. `Git Diff Summary`: include the real `git diff --stat` output.
15. `Final Git Status`: include the real `git status --short` output.
16. `Next Action`: exactly one of `READY_FOR_REVIEW`, `PLAN_CHANGE_REQUIRED`, or `BLOCKED`.

Do not claim `MERGED` or `RELEASED` unless the user separately authorized and completed that action outside this skill.
