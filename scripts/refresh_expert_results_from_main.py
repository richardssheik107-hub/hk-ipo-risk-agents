"""Safely inventory and restore the 60 IPO annotations from a Git ref.

Deletion is intentionally not implemented here: the caller must validate and
remove the one explicit ``<repo>/expert_results`` path separately.  Restore
writes only exact ``ipo_*`` annotation blobs and never touches the Git index.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


REMOTE_PATTERN = re.compile(
    r"^expert_results/ipo_\d{4}_[^/]+/pass1/expert_annotation_v1\.json$"
)
AUDIT_NAMES = {"financial_resolution_v1.json", "deterministic_corrections_v1.json"}
EXPECTED_REMOTE_COUNT = 60


def _git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE,
    ).stdout


def enumerate_remote_annotations(repo: Path, ref: str = "origin/main") -> list[str]:
    output = _git(repo, "ls-tree", "-r", "--name-only", ref, "--", "expert_results")
    paths = output.decode("utf-8").splitlines()
    return sorted(path for path in paths if REMOTE_PATTERN.fullmatch(path))


def require_remote_count(paths: list[str], expected: int = EXPECTED_REMOTE_COUNT) -> None:
    if len(paths) != expected:
        raise ValueError(f"REMOTE_ANNOTATION_COUNT:{len(paths)} expected={expected}")
    if len(set(paths)) != len(paths):
        raise ValueError("DUPLICATE_REMOTE_ANNOTATION_PATH")


def safe_expert_results_path(repo: Path, target: Path) -> Path:
    resolved_repo = repo.resolve()
    resolved = target.resolve()
    expected = (resolved_repo / "expert_results").resolve()
    if resolved != expected or resolved in {resolved_repo, resolved_repo.parent}:
        raise ValueError(f"UNSAFE_EXPERT_RESULTS_PATH:{resolved}")
    return resolved


def _record(path: str, content: bytes) -> dict[str, str]:
    payload = json.loads(content.decode("utf-8-sig"))
    return {
        "path": path,
        "case_id": str(payload.get("case_id", "")),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def local_records(repo: Path) -> list[dict[str, str]]:
    root = safe_expert_results_path(repo, repo / "expert_results")
    if not root.exists():
        return []
    return [
        _record(path.relative_to(repo).as_posix(), path.read_bytes())
        for path in sorted(root.rglob("expert_annotation_v1.json")) if path.is_file()
    ]


def remote_records(repo: Path, paths: list[str], ref: str = "origin/main") -> list[dict[str, str]]:
    return [_record(path, _git(repo, "show", f"{ref}:{path}")) for path in paths]


def enumerate_remote_audits(repo: Path, case_ids: set[str], ref: str = "origin/main") -> list[str]:
    output = _git(repo, "ls-tree", "-r", "--name-only", ref, "--", "expert_results")
    paths = output.decode("utf-8").splitlines()
    selected = []
    for path in paths:
        parts = Path(path).parts
        if len(parts) == 4 and parts[0] == "expert_results" and parts[1] in case_ids and parts[2] == "audit" and parts[3] in AUDIT_NAMES:
            selected.append(path)
    return sorted(selected)


def prepare_manifest(repo: Path, output: Path, ref: str = "origin/main") -> dict:
    paths = enumerate_remote_annotations(repo, ref)
    require_remote_count(paths)
    local = local_records(repo)
    remote = remote_records(repo, paths, ref)
    manifest = {
        "manifest_version": "retriever_v3_source_refresh_v1",
        "remote_ref": ref,
        "remote_commit": _git(repo, "rev-parse", ref).decode().strip(),
        "remote_filter": REMOTE_PATTERN.pattern,
        "real_case_excluded": True,
        "local_annotation_count_before": len(local),
        "local_annotations": local,
        "remote_annotation_count": len(remote),
        "remote_annotations": remote,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def restore(repo: Path, manifest_path: Path) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest["remote_annotations"]
    require_remote_count([record["path"] for record in records])
    root = safe_expert_results_path(repo, repo / "expert_results")
    if root.exists() and any(root.iterdir()):
        raise ValueError("EXPERT_RESULTS_NOT_EMPTY_BEFORE_RESTORE")
    for record in records:
        relative = Path(record["path"])
        target = (repo / relative).resolve()
        if root not in target.parents:
            raise ValueError(f"RESTORE_PATH_ESCAPES_ROOT:{target}")
        content = _git(repo, "show", f"{manifest['remote_ref']}:{record['path']}")
        if hashlib.sha256(content).hexdigest() != record["sha256"]:
            raise ValueError(f"REMOTE_BLOB_HASH_CHANGED:{record['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return len(records)


def restore_audits(repo: Path, manifest_path: Path) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case_ids = {record["case_id"] for record in manifest["remote_annotations"]}
    paths = enumerate_remote_audits(repo, case_ids, manifest["remote_ref"])
    records = remote_records(repo, paths, manifest["remote_ref"])
    root = safe_expert_results_path(repo, repo / "expert_results")
    for record in records:
        target = (repo / record["path"]).resolve()
        if root not in target.parents:
            raise ValueError(f"AUDIT_PATH_ESCAPES_ROOT:{target}")
        content = _git(repo, "show", f"{manifest['remote_ref']}:{record['path']}")
        if hashlib.sha256(content).hexdigest() != record["sha256"]:
            raise ValueError(f"REMOTE_AUDIT_HASH_CHANGED:{record['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    manifest["remote_audit_overlay_count"] = len(records)
    manifest["remote_audit_overlays"] = records
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "restore", "restore-audits"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--manifest", type=Path, default=Path("reports/retriever_v3/source_refresh_manifest.json"))
    args = parser.parse_args()
    repo = args.repo.resolve(); manifest_path = (repo / args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest
    if args.action == "prepare":
        result = prepare_manifest(repo, manifest_path, args.ref)
        print(json.dumps({"prepared": True, "local": result["local_annotation_count_before"],
                          "remote": result["remote_annotation_count"]}, ensure_ascii=False))
    elif args.action == "restore":
        count = restore(repo, manifest_path)
        print(json.dumps({"restored": count}, ensure_ascii=False))
    else:
        count = restore_audits(repo, manifest_path)
        print(json.dumps({"restored_audit_overlays": count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
