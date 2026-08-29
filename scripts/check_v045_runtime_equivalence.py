"""Prove whether a recorded final-three run needs to be repeated.

The proof is intentionally Git-derived. It never edits the recorded artifact
and it fails closed when any source, configuration, application, data-catalog,
or other material file differs from the recorded run commit.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = "v045_runtime_equivalence_v1"
DEFAULT_RECORDED_SHA = "3d81e5d0d71aeb5ffc76e3f123e8eecb5c75af8d"
ALLOWED_NON_RUNTIME_FILES = frozenset({".github/workflows/role-d-runtime.yml"})


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def parse_name_status(output: str) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status = fields[0]
        path = fields[-1].replace("\\", "/")
        changes.append({"status": status, "path": path})
    return changes


def build_report(
    *,
    recorded_sha: str,
    release_sha: str,
    changes: Iterable[dict[str, str]],
) -> dict[str, object]:
    normalized = list(changes)
    changed_files = [item["path"] for item in normalized]
    runtime_files = [
        path for path in changed_files if path not in ALLOWED_NON_RUNTIME_FILES
    ]
    equivalent = not runtime_files
    return {
        "schema_version": SCHEMA_VERSION,
        "recorded_run_sha": recorded_sha,
        "release_head_sha": release_sha,
        "runtime_equivalent": equivalent,
        "changed_files": changed_files,
        "changed_file_statuses": normalized,
        "allowed_non_runtime_files": sorted(ALLOWED_NON_RUNTIME_FILES),
        "runtime_files_changed": runtime_files,
        "runtime_behavior_changed": not equivalent,
        "rerun_required": not equivalent,
        "statement": (
            "The recorded final-three run predates a rebase whose only material "
            "file addition is a CI workflow. Runtime source/configuration is unchanged."
            if equivalent
            else "Tracked files outside the approved non-runtime CI change differ; "
            "the final-three runtime must be rerun before release."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--recorded-sha", default=DEFAULT_RECORDED_SHA)
    parser.add_argument("--release-sha", default="HEAD")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    recorded_sha = _git(root, "rev-parse", args.recorded_sha)
    release_sha = _git(root, "rev-parse", args.release_sha)
    changes = parse_name_status(
        _git(root, "diff", "--name-status", recorded_sha, release_sha)
    )
    report = build_report(
        recorded_sha=recorded_sha,
        release_sha=release_sha,
        changes=changes,
    )
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        "RUNTIME_EQUIVALENCE = "
        + ("PASS" if report["runtime_equivalent"] else "FAIL")
    )
    return 0 if report["runtime_equivalent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
