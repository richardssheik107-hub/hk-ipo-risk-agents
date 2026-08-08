"""Batch v0.3 analysis runner over catalog-selected IPO cases (member #2, V3-10).

Selects cases from the frozen catalog (by id, dataset split, or a golden
manifest), resolves each to an :class:`IPOProfile` via
:class:`CatalogIPODataProvider`, and runs :class:`IPOAnalysisService` once per
case. Failures are isolated (one bad case never aborts the batch), runs are
resumable, and every run records the code revision, resolved configuration and
timing so results are reproducible.

The 2025 blind-test split is protected: it is skipped by default and can only be
included with an explicit acknowledgement token, so nobody tunes rules on it by
accident.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

from ipo_risk.core.config import Settings, load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.providers.catalog import CatalogIPODataProvider
from ipo_risk.repositories.json_repository import JsonAnalysisRepository
from ipo_risk.schemas import IPOAnalysisRequest, IPOAnalysisResult, TaskStatus
from ipo_risk.services.analysis_service import IPOAnalysisService

BLIND_TEST_SPLIT = "blind_test"
BLIND_TEST_TOKEN = "I_ACCEPT_FINAL_BLIND_TEST"
REAL_PARSERS = {"pymupdf"}


class CasePreflightError(Exception):
    """A case could not be prepared to run (missing PDF, unknown id, ...)."""


@dataclass
class CaseOutcome:
    case_id: str
    stock_code: str
    company_name: str
    dataset_split: str
    status: str  # completed | partial | failed | skipped | protected
    analysis_id: str | None = None
    verified_risks: int = 0
    pending_risks: int = 0
    rejected_risks: int = 0
    error_count: int = 0
    agent_status: dict[str, str] = field(default_factory=dict)
    duration_ms: int | None = None
    message: str = ""


@dataclass
class BatchReport:
    outcomes: list[CaseOutcome]
    run_manifest: dict
    output_dir: Path

    def counts(self) -> dict[str, int]:
        tally: dict[str, int] = {}
        for outcome in self.outcomes:
            tally[outcome.status] = tally.get(outcome.status, 0) + 1
        return tally


def code_revision() -> str:
    """Best-effort git commit SHA so results trace back to source."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def select_case_ids(
    provider: CatalogIPODataProvider,
    *,
    case_ids: list[str] | None = None,
    split: str | None = None,
    golden_manifest: Path | None = None,
    limit: int | None = None,
) -> list[str]:
    """Resolve a case selection, preserving order and dropping duplicates."""
    selected: list[str]
    if case_ids:
        selected = list(case_ids)
    elif golden_manifest is not None:
        selected = _distinct_case_ids_from_manifest(golden_manifest)
    elif split is not None:
        selected = [
            row["case_id"]
            for row in provider._rows  # noqa: SLF001 - trusted internal view
            if row.get("dataset_split") == split
        ]
    else:
        selected = provider.case_ids()

    deduped: list[str] = []
    seen: set[str] = set()
    for case_id in selected:
        if case_id not in seen:
            seen.add(case_id)
            deduped.append(case_id)
    return deduped[:limit] if limit is not None else deduped


def _distinct_case_ids_from_manifest(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ordered: list[str] = []
    seen: set[str] = set()
    for row in rows:
        case_id = (row.get("case_id") or "").strip()
        if case_id and case_id not in seen:
            seen.add(case_id)
            ordered.append(case_id)
    return ordered


def _agent_status(result: IPOAnalysisResult) -> dict[str, str]:
    """Last analyze-status per agent, e.g. {'financial_agent': 'success'}."""
    status: dict[str, str] = {}
    for log in result.agent_logs:
        if log.action == "analyze":
            status[log.agent_name] = log.status.value
    return status


def _build_service(
    settings: Settings,
    provider: CatalogIPODataProvider,
    results_dir: Path,
) -> IPOAnalysisService:
    """Wire the catalog provider in at runtime (no container.py edit needed)."""
    registry = default_registry()
    registry.register("ipo_data_provider", "catalog", lambda: provider)
    container = DependencyContainer(settings, registry)
    repository = JsonAnalysisRepository(str(results_dir))
    return IPOAnalysisService(settings, container, repository)


def _build_request(profile, settings: Settings, data_root: Path, case_id: str) -> IPOAnalysisRequest:
    if settings.parser in REAL_PARSERS:
        relative = profile.metadata.get("prospectus_relative_path", "")
        if not relative:
            raise CasePreflightError("no prospectus path in catalog for real-parser run")
        pdf_path = data_root / relative
        if not pdf_path.is_file():
            raise CasePreflightError(f"prospectus PDF missing: {relative}")
        prospectus_path = str(pdf_path)
    else:
        prospectus_path = "mock://prospectus"
    return IPOAnalysisRequest(
        company_name=profile.company_name,
        stock_code=profile.stock_code,
        listing_date=profile.listing_date,
        prospectus_path=prospectus_path,
        workflow_version=settings.workflow_version,
        parser_name=settings.parser,
        predictor_name=settings.predictor,
        use_mock=settings.use_mock,
        options={"case_id": case_id},
    )


def run_batch(
    *,
    catalog_dir: str | Path = "data/catalog",
    data_root: str | Path = "data/inputs",
    output_dir: str | Path = "reports/v03_batch",
    config_path: str | Path | None = None,
    case_ids: list[str] | None = None,
    split: str | None = None,
    golden_manifest: Path | None = None,
    limit: int | None = None,
    overwrite: bool = False,
    include_blind_test: bool = False,
    blind_test_token: str | None = None,
) -> BatchReport:
    """Run the selected cases and write the batch artifacts. Fail-closed on 2025."""
    if include_blind_test and blind_test_token != BLIND_TEST_TOKEN:
        raise PermissionError(
            "2025 blind test requires include_blind_test with the exact acknowledgement token; "
            "refusing to run to prevent leakage."
        )

    data_root = Path(data_root)
    output_dir = Path(output_dir)
    cases_dir = output_dir / "cases"
    results_dir = output_dir / "results_json"
    cases_dir.mkdir(parents=True, exist_ok=True)

    # The batch always resolves identity from the catalog, so make the workflow
    # use the catalog provider too (full profile + special-securities metadata).
    settings = load_settings(str(config_path)) if config_path else load_settings()
    settings = replace(settings, ipo_data_provider="catalog")
    provider = CatalogIPODataProvider(catalog_dir)
    service = _build_service(settings, provider, results_dir)

    selection = select_case_ids(
        provider, case_ids=case_ids, split=split, golden_manifest=golden_manifest, limit=limit
    )

    started_at = datetime.now(timezone.utc)
    outcomes: list[CaseOutcome] = []
    for case_id in selection:
        outcomes.append(
            _run_one_case(
                case_id, provider, service, settings, data_root, cases_dir, overwrite, include_blind_test
            )
        )
    finished_at = datetime.now(timezone.utc)

    run_manifest = {
        "code_revision": code_revision(),
        "config_path": str(config_path) if config_path else "configs/mock.yaml",
        "settings": settings.__dict__,
        "python_version": sys.version.split()[0],
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": (finished_at - started_at).total_seconds(),
        "selected_case_count": len(selection),
        "blind_test_included": include_blind_test,
        "counts": _tally(outcomes),
    }
    report = BatchReport(outcomes=outcomes, run_manifest=run_manifest, output_dir=output_dir)
    _write_artifacts(report, cases_dir)
    return report


def _run_one_case(
    case_id, provider, service, settings, data_root, cases_dir, overwrite, include_blind_test
) -> CaseOutcome:
    try:
        profile = provider.get_by_case_id(case_id)
    except KeyError:
        return CaseOutcome(case_id, "", "", "", "failed", message="case_id not found in catalog")

    split = str(profile.metadata.get("dataset_split", ""))
    base = CaseOutcome(
        case_id=case_id,
        stock_code=profile.stock_code,
        company_name=profile.company_name,
        dataset_split=split,
        status="pending",
    )

    if split == BLIND_TEST_SPLIT and not include_blind_test:
        base.status = "protected"
        base.message = "2025 blind test protected; rerun with explicit acknowledgement to include"
        return base

    case_file = cases_dir / f"{case_id}.json"
    if case_file.exists() and not overwrite:
        base.status = "skipped"
        base.message = "existing result kept (use overwrite to rerun)"
        return base

    try:
        request = _build_request(profile, settings, data_root, case_id)
        result = service.analyze(request)
    except Exception as exc:  # isolate: one bad case never aborts the batch
        base.status = "failed"
        base.message = f"{type(exc).__name__}: {exc}"
        return base

    # Stamp the case identity so downstream evaluation maps results deterministically.
    result = result.model_copy(
        update={"metadata": {**result.metadata, "case_id": case_id, "dataset_split": split}}
    )
    case_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    duration_ms = None
    if result.finished_at is not None:
        duration_ms = int((result.finished_at - result.started_at).total_seconds() * 1000)
    base.status = result.status.value
    base.analysis_id = result.analysis_id
    base.verified_risks = len(result.verified_risks)
    base.pending_risks = len(result.pending_risks)
    base.rejected_risks = len(result.rejected_risks)
    base.error_count = len(result.errors)
    base.agent_status = _agent_status(result)
    base.duration_ms = duration_ms
    return base


def _tally(outcomes: list[CaseOutcome]) -> dict[str, int]:
    tally: dict[str, int] = {}
    for outcome in outcomes:
        tally[outcome.status] = tally.get(outcome.status, 0) + 1
    return tally


def _write_artifacts(report: BatchReport, cases_dir: Path) -> None:
    output_dir = report.output_dir
    (output_dir / "run_manifest.json").write_text(
        json.dumps(report.run_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # analysis_results.jsonl rebuilt from every persisted case (resume-safe).
    with (output_dir / "analysis_results.jsonl").open("w", encoding="utf-8") as handle:
        for outcome in report.outcomes:
            case_file = cases_dir / f"{outcome.case_id}.json"
            if case_file.is_file():
                payload = json.loads(case_file.read_text(encoding="utf-8"))
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    with (output_dir / "case_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "case_id", "stock_code", "company_name", "dataset_split", "status",
            "verified_risks", "pending_risks", "rejected_risks", "error_count",
            "agent_status", "duration_ms", "message",
        ])
        for outcome in report.outcomes:
            writer.writerow([
                outcome.case_id, outcome.stock_code, outcome.company_name,
                outcome.dataset_split, outcome.status, outcome.verified_risks,
                outcome.pending_risks, outcome.rejected_risks, outcome.error_count,
                json.dumps(outcome.agent_status, ensure_ascii=False),
                outcome.duration_ms if outcome.duration_ms is not None else "",
                outcome.message,
            ])

    with (output_dir / "failure_report.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "status", "message"])
        for outcome in report.outcomes:
            if outcome.status in {"failed", "protected"}:
                writer.writerow([outcome.case_id, outcome.status, outcome.message])
