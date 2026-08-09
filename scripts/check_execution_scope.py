"""Check every working-tree change against an Execution Plan's file scope."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

try:
    from .execution_plan import PlanParseError, normalize_repo_path, parse_plan, path_matches, validate_plan
except ImportError:  # Direct script execution.
    from execution_plan import PlanParseError, normalize_repo_path, parse_plan, path_matches, validate_plan


def changed_paths(repository_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repository_root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace").strip())
    tokens = result.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(tokens):
        entry = tokens[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4:
            raise RuntimeError(f"unexpected git status entry: {entry!r}")
        status, path = entry[:2], entry[3:]
        paths.add(path.replace("\\", "/"))
        if "R" in status or "C" in status:
            if index >= len(tokens) or not tokens[index]:
                raise RuntimeError("git rename/copy entry is missing its source path")
            paths.add(tokens[index].replace("\\", "/"))
            index += 1
    return sorted(paths)


def check_scope(plan_path: str | Path) -> list[tuple[str, str]]:
    plan = parse_plan(plan_path)
    structural_issues = validate_plan(plan)
    if structural_issues:
        return [("<plan>", f"invalid_plan:{issue.error}:{issue.detail}") for issue in structural_issues]
    allowed = [normalize_repo_path(value) for value in plan.list_items("Allowed Files")]
    forbidden = [normalize_repo_path(value) for value in plan.list_items("Forbidden Files")]
    allowed_rules = [value for value in allowed if value]
    forbidden_rules = [value for value in forbidden if value]
    violations: list[tuple[str, str]] = []
    for path in changed_paths(plan.repository_root):
        if any(path_matches(path, rule) for rule in forbidden_rules):
            violations.append((path, "forbidden"))
        elif not any(path_matches(path, rule) for rule in allowed_rules):
            violations.append((path, "not_allowed"))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_path")
    args = parser.parse_args()
    try:
        violations = check_scope(args.plan_path)
    except (OSError, UnicodeError, PlanParseError, RuntimeError) as exc:
        print("execution_scope=invalid")
        print("reason=scope_check_error")
        print(f"detail={exc}")
        return 1
    if violations:
        print("execution_scope=invalid")
        for path, reason in violations:
            print(f"file={path}")
            print(f"reason={reason}")
        return 1
    print("execution_scope=valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
