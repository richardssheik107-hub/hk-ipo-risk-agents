"""Parse and validate portable Markdown Execution Plans using the standard library."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ALLOWED_STATUSES = {
    "DRAFT",
    "APPROVED",
    "EXECUTING",
    "BLOCKED",
    "COMPLETED",
    "SUPERSEDED",
}
REQUIRED_FIELDS = (
    "plan_id",
    "title",
    "status",
    "revision",
    "base_commit",
    "branch",
    "owner",
    "planner",
    "executor",
    "report_path",
)
REQUIRED_SECTIONS = (
    "Goal",
    "Background",
    "Project Rules",
    "Inputs",
    "Allowed Files",
    "Forbidden Files",
    "Tasks",
    "Acceptance Criteria",
    "Required Validation",
    "Manual Validation",
    "Stop Conditions",
    "Expected Deliverables",
)
PLACEHOLDER_VALUES = {
    "replace_with_commit_sha",
    "replace-with-commit-sha",
    "your-secret-here",
    "changeme",
    "example",
    "placeholder",
}


@dataclass(frozen=True)
class ExecutionPlan:
    path: Path
    repository_root: Path
    metadata: dict[str, str]
    sections: dict[str, str]
    text: str

    def list_items(self, section: str) -> list[str]:
        items: list[str] = []
        for line in self.sections.get(section, "").splitlines():
            match = re.match(r"^\s*[-*]\s+(.+?)\s*$", line)
            if not match:
                continue
            value = match.group(1).strip()
            if value.startswith("[") and re.match(r"^\[[ xX]\]\s*", value):
                value = re.sub(r"^\[[ xX]\]\s*", "", value)
            items.append(value.strip("`").strip())
        return items


@dataclass(frozen=True)
class PlanIssue:
    error: str
    detail: str = ""


class PlanParseError(ValueError):
    """Raised when a Plan cannot be parsed into its structural parts."""


def find_repository_root(start: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
    )
    if result.returncode != 0:
        raise PlanParseError("not inside a Git repository")
    return Path(result.stdout.strip()).resolve()


def parse_plan(path: str | Path) -> ExecutionPlan:
    plan_path = Path(path).resolve()
    if not plan_path.is_file():
        raise PlanParseError(f"plan file does not exist: {plan_path}")
    text = plan_path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise PlanParseError("missing front matter opening delimiter")
    try:
        closing = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise PlanParseError("missing front matter closing delimiter") from exc

    metadata: dict[str, str] = {}
    for line_number, raw in enumerate(lines[1:closing], 2):
        if not raw.strip():
            continue
        if ":" not in raw:
            raise PlanParseError(f"invalid front matter line {line_number}")
        key, value = raw.split(":", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise PlanParseError(f"invalid front matter key on line {line_number}")
        if key in metadata:
            raise PlanParseError(f"duplicate front matter key: {key}")
        if value.startswith(("[", "{", "|", ">")):
            raise PlanParseError(f"front matter values must be scalar: {key}")
        metadata[key] = value

    sections: dict[str, str] = {}
    section_name: str | None = None
    section_lines: list[str] = []
    for raw in lines[closing + 1 :]:
        match = re.match(r"^##\s+(.+?)\s*$", raw)
        if match:
            if section_name is not None:
                sections[section_name] = "\n".join(section_lines).strip()
            section_name = match.group(1).strip()
            section_lines = []
        elif section_name is not None:
            section_lines.append(raw)
    if section_name is not None:
        sections[section_name] = "\n".join(section_lines).strip()

    repository_root = find_repository_root(plan_path.parent)
    return ExecutionPlan(plan_path, repository_root, metadata, sections, text)


def normalize_repo_path(value: str) -> str | None:
    cleaned = value.strip().strip("`").replace("\\", "/")
    if not cleaned or cleaned.lower() in {"none", "none."}:
        return None
    if re.match(r"^[A-Za-z]:/", cleaned) or cleaned.startswith("/"):
        return None
    path = PurePosixPath(cleaned)
    if any(part in {"", ".", ".."} for part in path.parts):
        return None
    normalized = path.as_posix()
    if cleaned.endswith("/"):
        normalized += "/"
    return normalized


def _section_has_content(value: str) -> bool:
    meaningful = [line.strip() for line in value.splitlines() if line.strip() not in {"```", "```text"}]
    return bool(meaningful)


def _looks_like_real_secret(text: str) -> bool:
    if "-----BEGIN " in text and "PRIVATE KEY-----" in text:
        return True
    token_patterns = (
        r"\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{12,}\b",
        r"\bAKIA[A-Z0-9]{16}\b",
    )
    if any(re.search(pattern, text) for pattern in token_patterns):
        return True
    assignment = re.compile(
        r"(?im)\b(?:api[_ -]?key|access[_ -]?token|password|client[_ -]?secret)\b\s*[:=]\s*[\"']?([^\s\"']+)"
    )
    for match in assignment.finditer(text):
        value = match.group(1).strip().lower()
        if value in PLACEHOLDER_VALUES or value.startswith(("$", "${", "<", "replace_", "your_")):
            continue
        if re.fullmatch(r"[A-Z][A-Z0-9_]+", match.group(1)):
            continue
        if len(value) >= 8 and any(character.isdigit() for character in value):
            return True
    return False


def validate_plan(plan: ExecutionPlan, require_approved: bool = False) -> list[PlanIssue]:
    issues: list[PlanIssue] = []
    for field in REQUIRED_FIELDS:
        if not plan.metadata.get(field, "").strip():
            issues.append(PlanIssue("missing_field", field))

    status = plan.metadata.get("status", "")
    if status and status not in ALLOWED_STATUSES:
        issues.append(PlanIssue("invalid_status", status))
    if require_approved and status != "APPROVED":
        issues.append(PlanIssue("plan_not_approved", status or "missing"))

    revision = plan.metadata.get("revision", "")
    if revision and (not revision.isdigit() or int(revision) < 1):
        issues.append(PlanIssue("invalid_revision", revision))

    branch = plan.metadata.get("branch", "").strip().lower()
    if branch in {"main", "master"}:
        issues.append(PlanIssue("protected_branch", branch))

    base_commit = plan.metadata.get("base_commit", "")
    if require_approved and not re.fullmatch(r"[0-9a-fA-F]{7,40}", base_commit):
        issues.append(PlanIssue("invalid_approved_base_commit", base_commit))

    for section in REQUIRED_SECTIONS:
        if section not in plan.sections:
            issues.append(PlanIssue("missing_section", section))
        elif not _section_has_content(plan.sections[section]):
            issues.append(PlanIssue("empty_section", section))

    for section in ("Allowed Files", "Forbidden Files"):
        if section in plan.sections and not plan.list_items(section):
            issues.append(PlanIssue("empty_path_list", section))
        for value in plan.list_items(section):
            if normalize_repo_path(value) is None:
                issues.append(PlanIssue("invalid_scope_path", f"{section}: {value}"))

    task_text = plan.sections.get("Tasks", "")
    if task_text and not re.search(r"(?m)^\s*[-*]\s+\[[ xX]\]\s+\S", task_text):
        issues.append(PlanIssue("missing_task_checkbox", "Tasks"))

    report_path = plan.metadata.get("report_path", "")
    normalized_report = normalize_repo_path(report_path) if report_path else None
    if report_path and normalized_report is None:
        issues.append(PlanIssue("invalid_report_path", report_path))
    elif normalized_report and normalized_report.endswith("/"):
        issues.append(PlanIssue("invalid_report_path", report_path))

    for rule in plan.list_items("Project Rules"):
        normalized_rule = normalize_repo_path(rule)
        if normalized_rule is None or normalized_rule.endswith("/"):
            issues.append(PlanIssue("invalid_project_rule", rule))
            continue
        if not (plan.repository_root / PurePosixPath(normalized_rule)).is_file():
            issues.append(PlanIssue("missing_project_rule", normalized_rule))

    allowed = [normalize_repo_path(value) for value in plan.list_items("Allowed Files")]
    forbidden = [normalize_repo_path(value) for value in plan.list_items("Forbidden Files")]
    if normalized_report and not any(path_matches(normalized_report, rule) for rule in allowed if rule):
        issues.append(PlanIssue("report_path_not_allowed", normalized_report))
    if normalized_report and any(path_matches(normalized_report, rule) for rule in forbidden if rule):
        issues.append(PlanIssue("report_path_forbidden", normalized_report))

    if _looks_like_real_secret(plan.text):
        issues.append(PlanIssue("suspected_secret", "plan content"))
    return issues


def path_matches(path: str, rule: str) -> bool:
    normalized_path = path.replace("\\", "/")
    if normalized_path.startswith("./"):
        normalized_path = normalized_path[2:]
    if rule.endswith("/"):
        return normalized_path.startswith(rule)
    return normalized_path == rule
