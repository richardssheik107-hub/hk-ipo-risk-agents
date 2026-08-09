from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_execution_scope import check_scope
from scripts.execution_plan import PlanParseError, parse_plan, validate_plan

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=True,
    )
    return result.stdout.strip()


def plan_text(base_commit: str, status: str = "APPROVED") -> str:
    return f"""---
plan_id: TEST-001
title: Portable contract test
status: {status}
revision: 1
base_commit: {base_commit}
branch: feat/portable-test
owner: test-owner
planner: human
executor: codex
report_path: docs/reports/TEST-001.md
---

# Portable contract test

## Goal

Exercise the generic plan contract.

## Background

The temporary repository contains no business code.

## Project Rules

- AGENTS.md

## Inputs

- README.md

## Allowed Files

- allowed.txt
- docs/
- renamed.txt

## Forbidden Files

- docs/protected/
- protected.txt

## Tasks

- [ ] Make an allowed change.

## Acceptance Criteria

- The allowed change is present.

## Required Validation

```text
git diff --check
```

## Manual Validation

None.

## Stop Conditions

- A forbidden file must change.

## Expected Deliverables

- allowed.txt
"""


class RepositoryFixture:
    def __init__(self, *, unicode_path: bool = False) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        if unicode_path:
            self.root = self.root / "中文测试仓库"
            self.root.mkdir()
        run_git(self.root, "init", "-b", "feat/portable-test")
        run_git(self.root, "config", "user.email", "test@example.invalid")
        run_git(self.root, "config", "user.name", "Contract Test")
        (self.root / "README.md").write_text("# Fixture\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("# Test rules\n", encoding="utf-8")
        run_git(self.root, "add", "README.md", "AGENTS.md")
        run_git(self.root, "commit", "-m", "initial")
        self.base = run_git(self.root, "rev-parse", "HEAD")
        self.plan_path = self.root / "docs" / "plans" / "TEST-001.md"
        self.plan_path.parent.mkdir(parents=True)
        self.plan_path.write_text(plan_text(self.base), encoding="utf-8")

    def commit_plan(self) -> None:
        run_git(self.root, "add", "docs/plans/TEST-001.md")
        run_git(self.root, "commit", "-m", "add plan")

    def close(self) -> None:
        self.temp.cleanup()


class PlanValidatorContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = RepositoryFixture()
        self.addCleanup(self.fixture.close)

    def issues(self, *, approved: bool = False):
        return validate_plan(parse_plan(self.fixture.plan_path), require_approved=approved)

    def replace(self, old: str, new: str, count: int = -1) -> None:
        text = self.fixture.plan_path.read_text(encoding="utf-8")
        self.fixture.plan_path.write_text(text.replace(old, new, count), encoding="utf-8")

    def assert_issue(self, name: str, *, approved: bool = False) -> None:
        self.assertIn(name, {issue.error for issue in self.issues(approved=approved)})

    def test_valid_approved_plan(self):
        self.assertEqual(self.issues(approved=True), [])

    def test_valid_draft_under_normal_validation(self):
        self.replace("status: APPROVED", "status: DRAFT")
        self.assertEqual(self.issues(), [])

    def test_draft_fails_approved_validation(self):
        self.replace("status: APPROVED", "status: DRAFT")
        self.assert_issue("plan_not_approved", approved=True)

    def test_missing_front_matter(self):
        self.fixture.plan_path.write_text("# No metadata\n", encoding="utf-8")
        with self.assertRaises(PlanParseError):
            parse_plan(self.fixture.plan_path)

    def test_missing_required_field(self):
        self.replace("owner: test-owner\n", "")
        self.assert_issue("missing_field")

    def test_invalid_revision(self):
        self.replace("revision: 1", "revision: 0")
        self.assert_issue("invalid_revision")

    def test_main_branch_is_rejected(self):
        self.replace("branch: feat/portable-test", "branch: main")
        self.assert_issue("protected_branch")

    def test_master_branch_is_rejected(self):
        self.replace("branch: feat/portable-test", "branch: master")
        self.assert_issue("protected_branch")

    def test_missing_goal(self):
        self.replace("## Goal", "## Unrecognized Goal")
        self.assert_issue("missing_section")

    def test_empty_allowed_files(self):
        self.replace("- allowed.txt\n- docs/\n- renamed.txt", "")
        self.assert_issue("empty_section")

    def test_empty_forbidden_files(self):
        self.replace("- docs/protected/\n- protected.txt", "")
        self.assert_issue("empty_section")

    def test_tasks_require_checkbox(self):
        self.replace("- [ ] Make an allowed change.", "Make an allowed change.")
        self.assert_issue("missing_task_checkbox")

    def test_empty_acceptance_criteria(self):
        self.replace("- The allowed change is present.", "")
        self.assert_issue("empty_section")

    def test_empty_required_validation(self):
        self.replace("```text\ngit diff --check\n```", "")
        self.assert_issue("empty_section")

    def test_empty_stop_conditions(self):
        self.replace("- A forbidden file must change.", "")
        self.assert_issue("empty_section")

    def test_invalid_report_path(self):
        self.replace("report_path: docs/reports/TEST-001.md", "report_path: ../outside.md")
        self.assert_issue("invalid_report_path")

    def test_suspicious_real_secret_is_rejected(self):
        self.replace("None.", "password = realpass12345", 1)
        self.assert_issue("suspected_secret")

    def test_placeholder_environment_key_name_is_allowed(self):
        self.replace("None.", "Set API_KEY through the environment.", 1)
        self.assertNotIn("suspected_secret", {issue.error for issue in self.issues()})

    def test_validator_cli_reports_valid(self):
        result = subprocess.run(
            [sys.executable, str(REPOSITORY_ROOT / "scripts/validate_execution_plan.py"), str(self.fixture.plan_path), "--approved"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "plan_validation=valid")

    def test_validator_cli_reports_not_approved(self):
        self.replace("status: APPROVED", "status: DRAFT")
        result = subprocess.run(
            [sys.executable, str(REPOSITORY_ROOT / "scripts/validate_execution_plan.py"), str(self.fixture.plan_path), "--approved"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error=plan_not_approved", result.stdout)

    def test_unicode_repository_path_is_supported(self):
        fixture = RepositoryFixture(unicode_path=True)
        self.addCleanup(fixture.close)
        self.assertEqual(validate_plan(parse_plan(fixture.plan_path), require_approved=True), [])


class ScopeGuardContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = RepositoryFixture()
        self.fixture.commit_plan()
        self.addCleanup(self.fixture.close)

    def violations(self):
        return check_scope(self.fixture.plan_path)

    def test_exact_allowed_file_passes(self):
        (self.fixture.root / "allowed.txt").write_text("allowed\n", encoding="utf-8")
        self.assertEqual(self.violations(), [])

    def test_allowed_directory_passes(self):
        path = self.fixture.root / "docs" / "new.md"
        path.write_text("allowed\n", encoding="utf-8")
        self.assertEqual(self.violations(), [])

    def test_outside_allowed_directory_fails(self):
        (self.fixture.root / "outside.txt").write_text("outside\n", encoding="utf-8")
        self.assertIn(("outside.txt", "not_allowed"), self.violations())

    def test_exact_forbidden_file_fails(self):
        (self.fixture.root / "protected.txt").write_text("no\n", encoding="utf-8")
        self.assertIn(("protected.txt", "forbidden"), self.violations())

    def test_forbidden_directory_fails(self):
        path = self.fixture.root / "docs" / "protected" / "no.md"
        path.parent.mkdir(parents=True)
        path.write_text("no\n", encoding="utf-8")
        self.assertIn(("docs/protected/no.md", "forbidden"), self.violations())

    def test_forbidden_overrides_allowed(self):
        path = self.fixture.root / "docs" / "protected" / "nested.md"
        path.parent.mkdir(parents=True)
        path.write_text("no\n", encoding="utf-8")
        self.assertEqual(self.violations(), [("docs/protected/nested.md", "forbidden")])

    def test_new_untracked_file_is_detected(self):
        (self.fixture.root / "untracked.txt").write_text("new\n", encoding="utf-8")
        self.assertIn(("untracked.txt", "not_allowed"), self.violations())

    def test_deleted_file_is_detected(self):
        path = self.fixture.root / "outside.txt"
        path.write_text("tracked\n", encoding="utf-8")
        run_git(self.fixture.root, "add", "outside.txt")
        run_git(self.fixture.root, "commit", "-m", "add outside")
        path.unlink()
        self.assertIn(("outside.txt", "not_allowed"), self.violations())

    def test_renamed_file_checks_source_and_destination(self):
        old = self.fixture.root / "old.txt"
        old.write_text("tracked\n", encoding="utf-8")
        run_git(self.fixture.root, "add", "old.txt")
        run_git(self.fixture.root, "commit", "-m", "add old")
        run_git(self.fixture.root, "mv", "old.txt", "renamed.txt")
        self.assertIn(("old.txt", "not_allowed"), self.violations())

    def test_scope_guard_cli_reports_forbidden_file(self):
        (self.fixture.root / "protected.txt").write_text("no\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(REPOSITORY_ROOT / "scripts/check_execution_scope.py"), str(self.fixture.plan_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("execution_scope=invalid", result.stdout)
        self.assertIn("file=protected.txt", result.stdout)
        self.assertIn("reason=forbidden", result.stdout)


if __name__ == "__main__":
    unittest.main()
