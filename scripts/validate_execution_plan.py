"""Command-line validator for Markdown Execution Plans."""

from __future__ import annotations

import argparse

try:
    from .execution_plan import PlanParseError, parse_plan, validate_plan
except ImportError:  # Direct script execution.
    from execution_plan import PlanParseError, parse_plan, validate_plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_path")
    parser.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        plan = parse_plan(args.plan_path)
    except (OSError, UnicodeError, PlanParseError) as exc:
        print("plan_validation=invalid")
        print("error=parse_error")
        print(f"detail={exc}")
        return 1
    issues = validate_plan(plan, require_approved=args.approved)
    if issues:
        print("plan_validation=invalid")
        for issue in issues:
            print(f"error={issue.error}")
            if issue.detail:
                print(f"detail={issue.detail}")
        return 1
    print("plan_validation=valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
