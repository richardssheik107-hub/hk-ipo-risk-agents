from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from ipo_risk.modeling.exceptions import (
    DocumentMaterializationConflictError,
    DocumentMaterializationError,
)
from ipo_risk.modeling.materialization import (
    DocumentMaterializationInput,
    V04DocumentSnapshotMaterializer,
)
from ipo_risk.schemas import IPOAnalysisResult, TaskStatus
from ipo_risk.schemas.market import expected_market_split
from ipo_risk.schemas.modeling import DocumentRiskSnapshotBuildContext


def _context(year: int = 2023, *, commit: str = "a" * 40):
    return DocumentRiskSnapshotBuildContext(
        case_id=f"ipo_{year}_00368",
        document_id=f"prospectus-sha-{year}",
        stock_code="0368.HK",
        cohort_year=year,
        listing_date=date(year, 1, 3),
        dataset_split=expected_market_split(year),
        official_ipo_universe_member=True,
        modeling_eligibility="eligible",
        eligibility_reason="official_ipo_universe_member",
        document_pipeline_version="v03_enhanced_v2",
        document_pipeline_commit=commit,
    )


def _result(*, workflow: str = "enhanced_v2", use_mock: bool = False):
    modes = {
        "workflow": "enhanced_v2",
        "parser": "real",
        "retriever": "real",
        "financial_agent": "real",
        "legal_agent": "real",
        "business_agent": "real",
    }
    return IPOAnalysisResult(
        analysis_id="analysis-2023-00368",
        request_id="request-2023-00368",
        company_name="Fixture IPO",
        stock_code="0368.HK",
        workflow_version=workflow,
        schema_version="1.0",
        status=TaskStatus.COMPLETED,
        metadata={
            "case_id": "ipo_2023_00368",
            # This is the source-corpus split, not the official listing-year split.
            "dataset_split": "validation",
            "ipo_profile": {
                "stock_code": "0368.HK",
                "listing_date": "2023-01-03",
            },
            "configuration": {
                "workflow_version": workflow,
                "use_mock": use_mock,
            },
            "component_modes": modes,
            "supervision": {"conflicts": []},
        },
    )


def test_authoritative_enhanced_v2_result_materializes_and_reuses(tmp_path: Path) -> None:
    materializer = V04DocumentSnapshotMaterializer(tmp_path)
    created = materializer.materialize(_result(), _context())
    reused = materializer.materialize(_result(), _context())

    assert created.status == "created"
    assert reused.status == "reused"
    assert created.snapshot_hash == reused.snapshot_hash
    artifact = tmp_path / "snapshots" / "ipo_2023_00368.json"
    payload = artifact.read_text(encoding="utf-8")
    assert '"document_pipeline_version": "v03_enhanced_v2"' in payload
    assert f'"document_pipeline_commit": "{"a" * 40}"' in payload


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (_result(workflow="mvp_v1"), "enhanced_v2"),
        (_result(use_mock=True), "mock"),
    ],
)
def test_mock_and_mvp_results_are_rejected(result, message: str, tmp_path: Path) -> None:
    with pytest.raises(DocumentMaterializationError, match=message):
        V04DocumentSnapshotMaterializer(tmp_path).materialize(result, _context())


def test_nonreal_component_mode_is_rejected(tmp_path: Path) -> None:
    result = _result()
    metadata = dict(result.metadata)
    metadata["component_modes"] = {
        **metadata["component_modes"],
        "retriever": "mock",
    }
    result = result.model_copy(update={"metadata": metadata})
    with pytest.raises(DocumentMaterializationError, match="retriever"):
        V04DocumentSnapshotMaterializer(tmp_path).materialize(result, _context())


def test_different_pipeline_provenance_never_overwrites(tmp_path: Path) -> None:
    materializer = V04DocumentSnapshotMaterializer(tmp_path)
    materializer.materialize(_result(), _context(commit="a" * 40))
    before = (tmp_path / "snapshots" / "ipo_2023_00368.json").read_bytes()
    with pytest.raises(DocumentMaterializationConflictError, match="different"):
        materializer.materialize(_result(), _context(commit="b" * 40))
    assert (tmp_path / "snapshots" / "ipo_2023_00368.json").read_bytes() == before


def test_batch_report_is_ordered_and_records_failures(tmp_path: Path) -> None:
    good = DocumentMaterializationInput(_result(), _context())
    bad_result = _result(use_mock=True).model_copy(
        update={"metadata": {**_result(use_mock=True).metadata, "case_id": "ipo_2022_00368"}}
    )
    bad_context = _context(2022).model_copy(
        update={"case_id": "ipo_2022_00368", "listing_date": date(2022, 1, 3)}
    )
    report = V04DocumentSnapshotMaterializer(tmp_path).materialize_batch(
        [good, DocumentMaterializationInput(bad_result, bad_context)],
        pipeline_version="v03_enhanced_v2",
        pipeline_commit="a" * 40,
    )
    assert tuple(item.case_id for item in report.outcomes) == (
        "ipo_2022_00368",
        "ipo_2023_00368",
    )
    assert report.counts == {"created": 1, "reused": 0, "failed": 1}
    with (tmp_path / "failure_report.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["case_id"] == "ipo_2022_00368"


def test_2025_is_rejected_before_any_outcome_access(tmp_path: Path) -> None:
    result = _result().model_copy(
        update={
            "stock_code": "0368.HK",
            "metadata": {
                **_result().metadata,
                "case_id": "ipo_2025_00368",
                "ipo_profile": {
                    "stock_code": "0368.HK",
                    "listing_date": "2025-01-03",
                },
            },
        }
    )
    with pytest.raises(DocumentMaterializationError, match="2025 blind"):
        V04DocumentSnapshotMaterializer(tmp_path).materialize(result, _context(2025))
