"""Canonical PR-A orchestration for v0.4 Document + Oracle materialization.

This module is intentionally a thin orchestration layer. It reuses the frozen
v0.3 batch runner, authoritative V04 document materializer, frozen document
feature manifest/vectorizer, and the evaluation-only Oracle feature builder.

The command never reads 2025 blind outcomes and never changes Retriever/Agent
business logic. The official Production cohort is resolved from the governed
2020-2024 listing-year universe exposed by CompetitionCSVMarketDataProvider.

Typical local pilot::

    python scripts/run_v04_pr_a.py \
      --config configs/v03_offline.yaml \
      --data-root /path/to/prospectuses \
      --output-dir reports/v04_pr_a_pilot \
      --limit 5

Full resumable run::

    python scripts/run_v04_pr_a.py \
      --config configs/v03_offline.yaml \
      --data-root /path/to/prospectuses \
      --output-dir reports/v04_pr_a \
      --resume
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import subprocess
from contextlib import contextmanager
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Iterable, Iterator

import yaml

from ipo_risk.evaluation.batch import code_revision, run_batch
from ipo_risk.modeling.features import (
    DOCUMENT_FEATURE_MANIFEST_V1,
    vectorize_document_snapshot,
)
from ipo_risk.modeling.materialization import V04DocumentSnapshotMaterializer
from ipo_risk.modeling.oracle_document import (
    ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
    build_oracle_document_features,
)
from ipo_risk.providers.competition_market import CompetitionCSVMarketDataProvider
from ipo_risk.schemas.market import IPOMarketMetadata, expected_market_split
from ipo_risk.schemas.modeling import (
    DocumentRiskSnapshotBuildContext,
    V03DocumentRiskSnapshot,
)

PR_A_VERSION = "v04_pr_a_v1"
DOCUMENT_PIPELINE_VERSION = "v03_enhanced_v2"
EXPECTED_FULL_COHORT_SIZE = 438
_HEX_REVISION = re.compile(r"^[0-9a-f]{7,64}$")
OFFLINE_PROVIDER_ENV_VARS = (
    "IPO_RISK_LLM_PROVIDER",
    "IPO_RISK_LLM_API_KEY",
    "IPO_RISK_LLM_BASE_URL",
    "IPO_RISK_LLM_MODEL",
    "IPO_RISK_LLM_TIMEOUT_SECONDS",
    "IPO_RISK_LLM_MAX_RETRIES",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "ARK_CODING_API_KEY",
)


def require_clean_worktree(repo_root: Path) -> None:
    """Fail before materialization when source provenance is not committed."""

    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("PR-A could not verify the git working tree")
    if result.stdout.strip():
        raise RuntimeError(
            "PR-A requires a clean git working tree for reproducible materialization"
        )


@contextmanager
def offline_provider_boundary(config_path: Path) -> Iterator[None]:
    """Make an explicit offline config authoritative over ambient credentials."""

    values = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if values.get("runtime_mode") != "offline":
        yield
        return
    if values.get("llm_provider") != "unavailable":
        raise RuntimeError(
            "PR-A offline config requires llm_provider: unavailable"
        )
    saved = {name: os.environ[name] for name in OFFLINE_PROVIDER_ENV_VARS if name in os.environ}
    for name in OFFLINE_PROVIDER_ENV_VARS:
        os.environ.pop(name, None)
    try:
        yield
    finally:
        for name in OFFLINE_PROVIDER_ENV_VARS:
            os.environ.pop(name, None)
        os.environ.update(saved)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _content_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_versions() -> dict[str, str]:
    packages = ("pydantic", "PyMuPDF")
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _portable_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"path must stay inside repository root: {path}") from exc


def _read_bridge_rows(catalog_dir: Path) -> dict[str, dict[str, str]]:
    bridge = catalog_dir / "ipo_official_master_bridge.csv"
    with bridge.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


def load_official_metadata(catalog_dir: Path) -> tuple[IPOMarketMetadata, ...]:
    """Load the frozen official 2020-2024 listing-year universe.

    CompetitionCSVMarketDataProvider does not read the EOD payload until bars are
    requested, so it is safe to reuse here purely for authoritative metadata.
    """

    provider = CompetitionCSVMarketDataProvider(Path("."), catalog_dir=catalog_dir)
    return provider.iter_listing_metadata()


def select_metadata(
    metadata: Iterable[IPOMarketMetadata],
    *,
    case_ids: list[str] | None = None,
    limit: int | None = None,
) -> tuple[IPOMarketMetadata, ...]:
    ordered = tuple(sorted(metadata, key=lambda item: item.case_id))
    if case_ids:
        wanted = list(dict.fromkeys(case_ids))
        by_case = {item.case_id: item for item in ordered}
        missing = [case_id for case_id in wanted if case_id not in by_case]
        if missing:
            raise ValueError(
                f"case ids outside official 2020-2024 cohort: {', '.join(missing)}"
            )
        ordered = tuple(by_case[case_id] for case_id in wanted)
    if limit is not None:
        if limit <= 0:
            raise ValueError("--limit must be positive")
        ordered = ordered[:limit]
    return ordered


def build_snapshot_context(
    metadata: IPOMarketMetadata,
    *,
    pipeline_commit: str,
) -> DocumentRiskSnapshotBuildContext:
    revision = pipeline_commit.strip().lower()
    if not _HEX_REVISION.fullmatch(revision):
        raise ValueError(
            "pipeline commit must be a 7-64 character hexadecimal git revision"
        )
    if metadata.cohort_year >= 2025:
        raise ValueError("2025 blind cohort is forbidden in PR-A")
    if not metadata.document_id:
        raise ValueError(f"missing prospectus document id for {metadata.case_id}")
    return DocumentRiskSnapshotBuildContext(
        case_id=metadata.case_id,
        document_id=metadata.document_id,
        stock_code=metadata.stock_code,
        cohort_year=metadata.cohort_year,
        listing_date=metadata.listing_date,
        dataset_split=expected_market_split(metadata.cohort_year),
        official_ipo_universe_member=metadata.official_ipo_universe_member,
        security_type=metadata.security_type,
        modeling_eligibility=metadata.modeling_eligibility,
        eligibility_reason=metadata.eligibility_reason,
        eligibility_policy_version=metadata.eligibility_policy_version,
        document_pipeline_version=DOCUMENT_PIPELINE_VERSION,
        document_pipeline_commit=revision,
    )


def _write_json_conflict_safe(
    path: Path,
    payload: dict[str, Any],
    *,
    resume: bool,
) -> str:
    """Write deterministic JSON and fail closed on incompatible reuse.

    ``resume`` documents caller intent; it never authorizes overwriting changed
    provenance. Exact content is reused, different content always fails closed.
    """

    del resume
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    normalized_payload = json.loads(encoded)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing == normalized_payload:
            return "reused"
        raise ValueError(
            f"existing artifact differs; use a new output directory: {path.name}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")
    return "created"


def freeze_execution_context(
    *,
    repo_root: Path,
    catalog_dir: Path,
    config_path: Path,
    output_dir: Path,
    selected: tuple[IPOMarketMetadata, ...],
    revision: str,
    resume: bool,
) -> dict[str, Any]:
    revision = revision.strip().lower()
    if not _HEX_REVISION.fullmatch(revision):
        raise ValueError(
            "git revision is unavailable; run PR-A from a git checkout so provenance is auditable"
        )
    bridge = catalog_dir / "ipo_official_master_bridge.csv"
    prospectus_manifest = catalog_dir / "ipo_prospectus_manifest.csv"
    source_manifest = catalog_dir / "v04_source_manifest.json"
    for required in (bridge, prospectus_manifest, config_path):
        if not required.is_file():
            raise FileNotFoundError(required)

    payload: dict[str, Any] = {
        "pr_a_version": PR_A_VERSION,
        "git_revision": revision,
        "document_pipeline_version": DOCUMENT_PIPELINE_VERSION,
        "document_feature_schema_version": DOCUMENT_FEATURE_MANIFEST_V1.version,
        "document_feature_manifest_hash": DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
        "oracle_feature_manifest_hash": ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
        "config": {
            "relative_path": _portable_relative(config_path, repo_root),
            "sha256": _sha256_file(config_path),
        },
        "official_bridge": {
            "relative_path": _portable_relative(bridge, repo_root),
            "sha256": _sha256_file(bridge),
        },
        "prospectus_manifest": {
            "relative_path": _portable_relative(prospectus_manifest, repo_root),
            "sha256": _sha256_file(prospectus_manifest),
        },
        "source_manifest": (
            {
                "relative_path": _portable_relative(source_manifest, repo_root),
                "sha256": _sha256_file(source_manifest),
            }
            if source_manifest.is_file()
            else None
        ),
        "python_version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "package_versions": _package_versions(),
        "selected_case_count": len(selected),
        "selected_case_ids_hash": _content_hash(
            [item.case_id for item in selected]
        ),
        "selected_case_ids": [item.case_id for item in selected],
        "blind_outcomes_included": False,
    }
    _write_json_conflict_safe(
        output_dir / "execution_context.json",
        payload,
        resume=resume,
    )
    return payload


def _feature_artifact(
    snapshot: V03DocumentRiskSnapshot,
    *,
    snapshot_hash: str,
) -> dict[str, Any]:
    vector = vectorize_document_snapshot(snapshot)
    body: dict[str, Any] = {
        "case_id": snapshot.case_id,
        "document_id": snapshot.document_id,
        "stock_code": snapshot.stock_code,
        "cohort_year": snapshot.cohort_year,
        "listing_date": snapshot.listing_date.isoformat()
        if snapshot.listing_date
        else None,
        "dataset_split": snapshot.dataset_split.value,
        "snapshot_hash": snapshot_hash,
        "feature_schema_version": vector.feature_schema_version,
        "feature_manifest_hash": vector.manifest_hash,
        "feature_names": list(vector.feature_names),
        "feature_values": list(vector.feature_values),
    }
    body["content_hash"] = _content_hash(body)
    return body


def run_production(
    *,
    selected: tuple[IPOMarketMetadata, ...],
    catalog_dir: Path,
    data_root: Path,
    config_path: Path,
    output_dir: Path,
    revision: str,
    resume: bool,
) -> dict[str, dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir = output_dir / "production_analysis"
    with offline_provider_boundary(config_path):
        report = run_batch(
            catalog_dir=catalog_dir,
            data_root=data_root,
            output_dir=analysis_dir,
            config_path=config_path,
            case_ids=[item.case_id for item in selected],
            overwrite=False,
            include_blind_test=False,
        )
    outcome_by_case = {item.case_id: item for item in report.outcomes}
    materializer = V04DocumentSnapshotMaterializer(
        output_dir / "production_document"
    )
    states: dict[str, dict[str, Any]] = {}

    for metadata in selected:
        outcome = outcome_by_case.get(metadata.case_id)
        state: dict[str, Any] = {
            "case_id": metadata.case_id,
            "analysis_status": outcome.status if outcome else "missing",
            "analysis_message": outcome.message
            if outcome
            else "batch outcome missing",
            "snapshot_status": "not_run",
            "feature_status": "not_run",
            "production_document_available": False,
            "failure_stage": "",
            "failure_reason": "",
            "snapshot_hash": "",
            "feature_hash": "",
            "feature_manifest_hash": DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
        }
        case_file = analysis_dir / "cases" / f"{metadata.case_id}.json"
        if not case_file.is_file():
            state["failure_stage"] = "analysis"
            state["failure_reason"] = (
                state["analysis_message"] or "analysis result missing"
            )
            states[metadata.case_id] = state
            continue

        try:
            result = materializer.load_result(case_file)
            context = build_snapshot_context(metadata, pipeline_commit=revision)
            materialized = materializer.materialize(result, context)
            state["snapshot_status"] = materialized.status
            state["snapshot_hash"] = materialized.snapshot_hash or ""
        except Exception as exc:
            state["snapshot_status"] = "failed"
            state["failure_stage"] = "snapshot"
            state["failure_reason"] = f"{type(exc).__name__}: {exc}"
            states[metadata.case_id] = state
            continue

        try:
            snapshot_path = (
                output_dir
                / "production_document"
                / "snapshots"
                / f"{metadata.case_id}.json"
            )
            snapshot = V03DocumentRiskSnapshot.model_validate_json(
                snapshot_path.read_text(encoding="utf-8")
            )
            artifact = _feature_artifact(
                snapshot,
                snapshot_hash=state["snapshot_hash"],
            )
            status = _write_json_conflict_safe(
                output_dir / "production_features" / f"{metadata.case_id}.json",
                artifact,
                resume=resume,
            )
            state["feature_status"] = status
            state["feature_hash"] = artifact["content_hash"]
            state["feature_manifest_hash"] = artifact["feature_manifest_hash"]
            state["production_document_available"] = True
        except Exception as exc:
            state["feature_status"] = "failed"
            state["failure_stage"] = "feature"
            state["failure_reason"] = f"{type(exc).__name__}: {exc}"
        states[metadata.case_id] = state

    status_payload = {
        "pr_a_version": PR_A_VERSION,
        "cases": [states[item.case_id] for item in selected],
    }
    (output_dir / "production_status.json").write_text(
        json.dumps(
            status_payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return states


def run_oracle(
    *,
    repo_root: Path,
    selected: tuple[IPOMarketMetadata, ...],
    output_dir: Path,
    resume: bool,
) -> dict[str, dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    states: dict[str, dict[str, Any]] = {}
    features_dir = output_dir / "oracle_features"
    for metadata in selected:
        annotation = (
            repo_root
            / "expert_results"
            / metadata.case_id
            / "pass1"
            / "expert_annotation_v1.json"
        )
        if not annotation.is_file():
            states[metadata.case_id] = {
                "case_id": metadata.case_id,
                "status": "unavailable",
                "oracle_document_available": False,
                "failure_reason": "no_reviewed_gold",
                "feature_hash": "",
                "feature_manifest_hash": ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
                "effective_annotation_hash": "",
            }
            continue
        try:
            artifact = build_oracle_document_features(
                repo_root,
                metadata.case_id,
            )
            target = features_dir / f"{metadata.case_id}.json"
            status = _write_json_conflict_safe(
                target,
                artifact,
                resume=resume,
            )
            states[metadata.case_id] = {
                "case_id": metadata.case_id,
                "status": status,
                "oracle_document_available": True,
                "failure_reason": "",
                "feature_hash": artifact["content_hash"],
                "feature_manifest_hash": artifact["oracle_manifest_hash"],
                "effective_annotation_hash": artifact[
                    "effective_annotation_hash"
                ],
            }
        except Exception as exc:
            states[metadata.case_id] = {
                "case_id": metadata.case_id,
                "status": "failed",
                "oracle_document_available": False,
                "failure_reason": f"{type(exc).__name__}: {exc}",
                "feature_hash": "",
                "feature_manifest_hash": ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
                "effective_annotation_hash": "",
            }

    payload = {
        "pr_a_version": PR_A_VERSION,
        "cases": [states[item.case_id] for item in selected],
    }
    (output_dir / "oracle_status.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return states


def _load_status(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["case_id"]: row for row in payload.get("cases", [])}


def _csv_string_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            key: "" if value is None else str(value)
            for key, value in row.items()
        }
        for row in rows
    ]


def build_coverage(
    *,
    selected: tuple[IPOMarketMetadata, ...],
    catalog_dir: Path,
    production: dict[str, dict[str, Any]],
    oracle: dict[str, dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    bridge = _read_bridge_rows(catalog_dir)
    rows: list[dict[str, Any]] = []
    for metadata in sorted(selected, key=lambda item: item.case_id):
        prod = production.get(metadata.case_id, {})
        ora = oracle.get(metadata.case_id, {})
        source_row = bridge.get(metadata.case_id, {})
        rows.append(
            {
                "case_id": metadata.case_id,
                "stock_code": metadata.stock_code,
                "source_year": source_row.get("source_year", ""),
                "official_listing_year": metadata.cohort_year,
                "dataset_split": expected_market_split(
                    metadata.cohort_year
                ).value,
                "production_analysis_status": prod.get(
                    "analysis_status",
                    "not_run",
                ),
                "production_snapshot_status": prod.get(
                    "snapshot_status",
                    "not_run",
                ),
                "production_document_available": str(
                    bool(prod.get("production_document_available", False))
                ).lower(),
                "production_failure_stage": prod.get("failure_stage", ""),
                "production_failure_reason": prod.get("failure_reason", ""),
                "production_snapshot_hash": prod.get("snapshot_hash", ""),
                "production_feature_hash": prod.get("feature_hash", ""),
                "production_feature_manifest_hash": prod.get(
                    "feature_manifest_hash",
                    DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
                ),
                "oracle_document_available": str(
                    bool(ora.get("oracle_document_available", False))
                ).lower(),
                "oracle_failure_reason": ora.get(
                    "failure_reason",
                    "not_run",
                ),
                "oracle_feature_hash": ora.get("feature_hash", ""),
                "oracle_feature_manifest_hash": ora.get(
                    "feature_manifest_hash",
                    ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
                ),
                "oracle_effective_annotation_hash": ora.get(
                    "effective_annotation_hash",
                    "",
                ),
            }
        )

    csv_rows = _csv_string_rows(rows)
    fieldnames = list(csv_rows[0]) if csv_rows else ["case_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "coverage.csv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    production_materialized = sum(
        row["production_document_available"] == "true" for row in csv_rows
    )
    oracle_materialized = sum(
        row["oracle_document_available"] == "true" for row in csv_rows
    )
    intersection = sum(
        row["production_document_available"] == "true"
        and row["oracle_document_available"] == "true"
        for row in csv_rows
    )
    failures_by_stage: dict[str, int] = {}
    for row in csv_rows:
        stage = row["production_failure_stage"]
        if stage:
            failures_by_stage[stage] = failures_by_stage.get(stage, 0) + 1

    summary = {
        "pr_a_version": PR_A_VERSION,
        "selected_case_count": len(csv_rows),
        "production_materialized_count": production_materialized,
        "production_failure_count": len(csv_rows) - production_materialized,
        "production_failure_count_by_stage": dict(
            sorted(failures_by_stage.items())
        ),
        "oracle_materialized_count": oracle_materialized,
        "production_oracle_intersection_count": intersection,
        "coverage_hash": _content_hash(csv_rows),
    }
    (output_dir / "coverage_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def verify_determinism(
    *,
    selected: tuple[IPOMarketMetadata, ...],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    mismatches: list[dict[str, str]] = []
    for metadata in selected:
        snapshot_path = (
            output_dir
            / "production_document"
            / "snapshots"
            / f"{metadata.case_id}.json"
        )
        feature_path = (
            output_dir / "production_features" / f"{metadata.case_id}.json"
        )
        if snapshot_path.is_file() and feature_path.is_file():
            snapshot = V03DocumentRiskSnapshot.model_validate_json(
                snapshot_path.read_text(encoding="utf-8")
            )
            feature = json.loads(feature_path.read_text(encoding="utf-8"))
            expected = _feature_artifact(
                snapshot,
                snapshot_hash=snapshot.content_hash(),
            )
            if feature != expected:
                mismatches.append(
                    {
                        "case_id": metadata.case_id,
                        "layer": "production_feature",
                    }
                )

        oracle_path = output_dir / "oracle_features" / f"{metadata.case_id}.json"
        if oracle_path.is_file():
            oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
            expected_hash = _content_hash(
                {
                    key: value
                    for key, value in oracle.items()
                    if key != "content_hash"
                }
            )
            if oracle.get("content_hash") != expected_hash:
                mismatches.append(
                    {
                        "case_id": metadata.case_id,
                        "layer": "oracle_feature",
                    }
                )

    coverage_path = output_dir / "coverage.csv"
    summary_path = output_dir / "coverage_summary.json"
    coverage_hash_ok = False
    if coverage_path.is_file() and summary_path.is_file():
        with coverage_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        coverage_hash_ok = summary.get("coverage_hash") == _content_hash(rows)
        if not coverage_hash_ok:
            mismatches.append({"case_id": "*", "layer": "coverage_hash"})

    report = {
        "pr_a_version": PR_A_VERSION,
        "checked_case_count": len(selected),
        "mismatch_count": len(mismatches),
        "coverage_hash_ok": coverage_hash_ok,
        "mismatches": mismatches,
        "passed": not mismatches,
    }
    (output_dir / "determinism_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _parse_case_ids(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return list(dict.fromkeys(values)) or None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument("--data-root", type=Path, default=Path("data/inputs"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/v04_pr_a"),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/v03_offline.yaml"),
    )
    parser.add_argument("--limit", type=int, help="deterministic pilot limit")
    parser.add_argument(
        "--case-ids",
        help="comma-separated diagnostic/pilot case ids",
    )
    parser.add_argument("--resume", action="store_true")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--production-only", action="store_true")
    modes.add_argument("--oracle-only", action="store_true")
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="recompute hashes from persisted artifacts and fail if they drift",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    require_clean_worktree(repo_root)
    catalog_dir = (
        (repo_root / args.catalog_dir).resolve()
        if not args.catalog_dir.is_absolute()
        else args.catalog_dir
    )
    config_path = (
        (repo_root / args.config).resolve()
        if not args.config.is_absolute()
        else args.config
    )
    output_dir = (
        (repo_root / args.output_dir).resolve()
        if not args.output_dir.is_absolute()
        else args.output_dir
    )
    data_root = (
        (repo_root / args.data_root).resolve()
        if not args.data_root.is_absolute()
        else args.data_root
    )

    if output_dir.exists() and any(output_dir.iterdir()) and not args.resume:
        parser.error(
            "output directory is not empty; use --resume or a new output directory"
        )

    official = load_official_metadata(catalog_dir)
    case_ids = _parse_case_ids(args.case_ids)
    selected = select_metadata(
        official,
        case_ids=case_ids,
        limit=args.limit,
    )
    if not selected:
        parser.error("no official 2020-2024 cases selected")
    if (
        case_ids is None
        and args.limit is None
        and len(official) != EXPECTED_FULL_COHORT_SIZE
    ):
        raise RuntimeError(
            "official cohort drift: "
            f"expected {EXPECTED_FULL_COHORT_SIZE}, found {len(official)}"
        )

    revision = code_revision().strip().lower()
    freeze_execution_context(
        repo_root=repo_root,
        catalog_dir=catalog_dir,
        config_path=config_path,
        output_dir=output_dir,
        selected=selected,
        revision=revision,
        resume=args.resume,
    )

    if args.oracle_only:
        production = _load_status(output_dir / "production_status.json")
    else:
        production = run_production(
            selected=selected,
            catalog_dir=catalog_dir,
            data_root=data_root,
            config_path=config_path,
            output_dir=output_dir,
            revision=revision,
            resume=args.resume,
        )

    if args.production_only:
        oracle = _load_status(output_dir / "oracle_status.json")
    else:
        oracle = run_oracle(
            repo_root=repo_root,
            selected=selected,
            output_dir=output_dir,
            resume=args.resume,
        )

    summary = build_coverage(
        selected=selected,
        catalog_dir=catalog_dir,
        production=production,
        oracle=oracle,
        output_dir=output_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if args.verify_determinism:
        report = verify_determinism(
            selected=selected,
            output_dir=output_dir,
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2 if not report["passed"] else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
