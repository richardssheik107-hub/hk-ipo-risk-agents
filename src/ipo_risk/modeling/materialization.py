"""Governed orchestration from authoritative v0.3 results to V04 snapshots."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.modeling.exceptions import (
    DocumentMaterializationConflictError,
    DocumentMaterializationError,
)
from ipo_risk.modeling.snapshot import DocumentRiskSnapshotBuilder
from ipo_risk.schemas import IPOAnalysisResult, TaskStatus
from ipo_risk.schemas.market import MarketDatasetSplit
from ipo_risk.schemas.modeling import (
    DocumentRiskSnapshotBuildContext,
    V03DocumentRiskSnapshot,
)


AUTHORITATIVE_DOCUMENT_WORKFLOW = "enhanced_v2"
AUTHORITATIVE_COMPONENT_MODES = {
    "workflow": "enhanced_v2",
    "parser": "real",
    "retriever": "real",
    "financial_agent": "real",
    "legal_agent": "real",
    "business_agent": "real",
}


class DocumentMaterializationOutcome(BaseModel):
    """One case-level result suitable for deterministic batch reports."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(created|reused|failed)$")
    snapshot_hash: str | None = Field(default=None, min_length=64, max_length=64)
    artifact: str | None = None
    message: str = ""


class DocumentMaterializationReport(BaseModel):
    """Summary of a governed document snapshot materialization run."""

    model_config = ConfigDict(frozen=True)

    pipeline_version: str = Field(min_length=1)
    pipeline_commit: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    outcomes: tuple[DocumentMaterializationOutcome, ...]

    @property
    def counts(self) -> dict[str, int]:
        counts = {"created": 0, "reused": 0, "failed": 0}
        for outcome in self.outcomes:
            counts[outcome.status] += 1
        return counts


@dataclass(frozen=True)
class DocumentMaterializationInput:
    """Explicit pairing of one source result and its authoritative identity."""

    result: IPOAnalysisResult
    context: DocumentRiskSnapshotBuildContext


class V04DocumentSnapshotMaterializer:
    """Build and persist versioned snapshots without cross-version overwrite.

    This boundary deliberately accepts final structured results only. It never
    calls a Retriever, Agent, LLM, network service, or market outcome provider.
    """

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.snapshots_dir = self.output_dir / "snapshots"
        self.builder = DocumentRiskSnapshotBuilder()

    @staticmethod
    def load_result(path: str | Path) -> IPOAnalysisResult:
        return IPOAnalysisResult.model_validate_json(
            Path(path).read_text(encoding="utf-8")
        )

    @staticmethod
    def _validate_authoritative_result(
        result: IPOAnalysisResult,
        context: DocumentRiskSnapshotBuildContext,
    ) -> None:
        if context.dataset_split is MarketDatasetSplit.BLIND or context.cohort_year >= 2025:
            raise DocumentMaterializationError(
                "2025 blind cohort is outside this 2020-2024 materialization phase"
            )
        if result.workflow_version != AUTHORITATIVE_DOCUMENT_WORKFLOW:
            raise DocumentMaterializationError(
                "document result must use enhanced_v2 workflow"
            )
        if result.status not in {TaskStatus.COMPLETED, TaskStatus.PARTIAL}:
            raise DocumentMaterializationError(
                "document result must have a completed or partial final status"
            )

        configuration = result.metadata.get("configuration")
        if not isinstance(configuration, dict):
            raise DocumentMaterializationError(
                "document result is missing authoritative configuration metadata"
            )
        if configuration.get("workflow_version") != AUTHORITATIVE_DOCUMENT_WORKFLOW:
            raise DocumentMaterializationError(
                "configuration workflow is not enhanced_v2"
            )
        if configuration.get("use_mock") is not False:
            raise DocumentMaterializationError(
                "mock or unproven document results are not authoritative"
            )

        component_modes = result.metadata.get("component_modes")
        if not isinstance(component_modes, dict):
            raise DocumentMaterializationError(
                "document result is missing component mode provenance"
            )
        mismatches = {
            name: (component_modes.get(name), expected)
            for name, expected in AUTHORITATIVE_COMPONENT_MODES.items()
            if component_modes.get(name) != expected
        }
        if mismatches:
            rendered = ", ".join(
                f"{name}={actual!r} (expected {expected!r})"
                for name, (actual, expected) in sorted(mismatches.items())
            )
            raise DocumentMaterializationError(
                f"non-authoritative component modes: {rendered}"
            )

    @staticmethod
    def _prepare_for_snapshot(
        result: IPOAnalysisResult,
    ) -> IPOAnalysisResult:
        """Separate source-corpus split from the official V04 cohort split."""

        metadata = dict(result.metadata)
        source_split = metadata.pop("dataset_split", None)
        if source_split is not None:
            metadata["source_dataset_split"] = source_split
        return result.model_copy(update={"metadata": metadata})

    def materialize(
        self,
        result: IPOAnalysisResult,
        context: DocumentRiskSnapshotBuildContext,
    ) -> DocumentMaterializationOutcome:
        self._validate_authoritative_result(result, context)
        snapshot = self.builder.build(self._prepare_for_snapshot(result), context)
        artifact = self.snapshots_dir / f"{context.case_id}.json"
        relative_artifact = artifact.relative_to(self.output_dir).as_posix()

        if artifact.exists():
            existing = V03DocumentRiskSnapshot.model_validate_json(
                artifact.read_text(encoding="utf-8")
            )
            if existing.canonical_json() != snapshot.canonical_json():
                raise DocumentMaterializationConflictError(
                    f"{context.case_id} already exists with different content or provenance"
                )
            return DocumentMaterializationOutcome(
                case_id=context.case_id,
                status="reused",
                snapshot_hash=snapshot.content_hash(),
                artifact=relative_artifact,
            )

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        artifact.write_text(
            snapshot.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return DocumentMaterializationOutcome(
            case_id=context.case_id,
            status="created",
            snapshot_hash=snapshot.content_hash(),
            artifact=relative_artifact,
        )

    def materialize_batch(
        self,
        items: Iterable[DocumentMaterializationInput],
        *,
        pipeline_version: str,
        pipeline_commit: str,
    ) -> DocumentMaterializationReport:
        normalized_commit = pipeline_commit.strip().lower()
        ordered = sorted(items, key=lambda item: item.context.case_id)
        outcomes: list[DocumentMaterializationOutcome] = []
        for item in ordered:
            if item.context.document_pipeline_version != pipeline_version:
                outcomes.append(
                    DocumentMaterializationOutcome(
                        case_id=item.context.case_id,
                        status="failed",
                        message="context pipeline version differs from batch version",
                    )
                )
                continue
            if item.context.document_pipeline_commit.lower() != normalized_commit:
                outcomes.append(
                    DocumentMaterializationOutcome(
                        case_id=item.context.case_id,
                        status="failed",
                        message="context pipeline commit differs from batch commit",
                    )
                )
                continue
            try:
                outcomes.append(self.materialize(item.result, item.context))
            except Exception as exc:
                outcomes.append(
                    DocumentMaterializationOutcome(
                        case_id=item.context.case_id,
                        status="failed",
                        message=f"{type(exc).__name__}: {exc}",
                    )
                )

        report = DocumentMaterializationReport(
            pipeline_version=pipeline_version,
            pipeline_commit=normalized_commit,
            outcomes=tuple(outcomes),
        )
        self._write_reports(report)
        return report

    def _write_reports(self, report: DocumentMaterializationReport) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "materialization_report.json").write_text(
            json.dumps(
                {
                    **report.model_dump(mode="json"),
                    "counts": report.counts,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        with (self.output_dir / "failure_report.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow(["case_id", "status", "message"])
            for outcome in report.outcomes:
                if outcome.status == "failed":
                    writer.writerow([outcome.case_id, outcome.status, outcome.message])
