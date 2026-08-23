from __future__ import annotations

import json
from pathlib import Path

import pytest

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES
from ipo_risk.modeling.features import DOCUMENT_FEATURE_MANIFEST_V1
from ipo_risk.schemas import (
    Calculation,
    Evidence,
    IPOAnalysisResult,
    RiskCategory,
    RiskItem,
    RiskLevel,
    TaskStatus,
    VerificationStatus,
)
from ipo_risk.schemas.canonical_modeling import canonical_hash
from scripts.audit_v04_pr_d_document_contract import (
    audit_production_artifacts,
    build_explanation_records,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _artifact(case_id: str = "ipo_2023_00001") -> dict:
    names = [item.name for item in DOCUMENT_FEATURE_MANIFEST_V1.features]
    values = []
    for name in names:
        if "__state_" in name:
            values.append(int(name.endswith("state_not_emitted")))
        elif name.endswith("__missing"):
            values.append(1)
        elif name.endswith("__evidence_count"):
            values.append(0)
        elif name in {
            "verified_risk_count",
            "pending_risk_count",
            "needs_review_risk_count",
            "rejected_risk_count",
            "unavailable_risk_count",
            "high_risk_count",
            "critical_risk_count",
        }:
            values.append(0)
        elif name in {"not_emitted_risk_count", "missing_risk_feature_count"}:
            values.append(8)
        else:
            values.append(None)
    body = {
        "case_id": case_id,
        "document_id": f"doc-{case_id}",
        "stock_code": "00001.HK",
        "cohort_year": 2023,
        "listing_date": "2023-01-03",
        "dataset_split": "development",
        "snapshot_hash": "a" * 64,
        "feature_schema_version": DOCUMENT_FEATURE_MANIFEST_V1.version,
        "feature_manifest_hash": DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
        "feature_names": names,
        "feature_values": values,
    }
    return body | {"content_hash": canonical_hash(body)}


def _rehash(payload: dict) -> dict:
    body = {key: value for key, value in payload.items() if key != "content_hash"}
    return body | {"content_hash": canonical_hash(body)}


def test_bulk_audit_accepts_valid_document_x_and_is_deterministic(tmp_path: Path) -> None:
    artifact = _artifact()
    _write(tmp_path / f"{artifact['case_id']}.json", artifact)
    first = audit_production_artifacts(tmp_path, official_case_ids=[artifact["case_id"]])
    second = audit_production_artifacts(tmp_path, official_case_ids=[artifact["case_id"]])
    assert first == second
    assert first["status"] == "pass"
    assert first["artifact_count"] == first["unique_case_count"] == 1


@pytest.mark.parametrize("mutation,expected", [
    ("nonfinite", "invalid feature values"),
    ("silent_zero", "silent_fill"),
    ("gold", "Gold/Oracle-derived"),
    ("provenance", "missing provenance fields"),
])
def test_bulk_audit_fails_closed_on_invalid_document_x(
    tmp_path: Path, mutation: str, expected: str
) -> None:
    artifact = _artifact()
    if mutation == "nonfinite":
        artifact["feature_values"][-1] = float("nan")
    elif mutation == "silent_zero":
        index = artifact["feature_names"].index("cash_runway__score")
        artifact["feature_values"][index] = 0
    elif mutation == "gold":
        artifact["expert_annotation"] = {"gold_page": 12}
    else:
        artifact.pop("snapshot_hash")
    artifact = _rehash(artifact)
    _write(tmp_path / f"{artifact['case_id']}.json", artifact)
    result = audit_production_artifacts(tmp_path, official_case_ids=[artifact["case_id"]])
    assert result["status"] == "fail"
    assert expected in result["failures"][0]["reason"]


def test_bulk_audit_detects_missing_orphan_and_filename_identity(tmp_path: Path) -> None:
    orphan = _artifact("ipo_2023_99999")
    _write(tmp_path / "wrong_filename.json", orphan)
    result = audit_production_artifacts(
        tmp_path, official_case_ids=["ipo_2023_00001"]
    )
    assert result["status"] == "fail"
    assert result["missing_case_ids"] == ["ipo_2023_00001"]
    assert result["orphan_case_ids"] == ["ipo_2023_99999"]
    assert "filename/case_id mismatch" in result["failures"][0]["reason"]


def test_explanation_projection_preserves_page_calculation_verifier_and_provenance() -> None:
    evidence = Evidence(
        evidence_id="e-1",
        document_id="doc-1",
        chunk_id="doc-1:page:7",
        page=7,
        text="Auditable Production evidence text.",
    )
    risk = RiskItem(
        risk_id="r-1",
        risk_code="cash_runway",
        category=RiskCategory.FINANCIAL,
        risk_type="Cash runway",
        level=RiskLevel.HIGH,
        score=80,
        conclusion="Cash runway is constrained.",
        evidence=[evidence],
        calculation=Calculation(
            skill_name="cash_runway",
            formula="cash / burn",
            result=6,
            unit="months",
            evidence_ids=["e-1"],
        ),
        agent_name="financial",
        verification_status=VerificationStatus.VERIFIED,
    )
    result = IPOAnalysisResult(
        analysis_id="a-1",
        request_id="req-1",
        company_name="Fixture",
        stock_code="00001.HK",
        workflow_version="enhanced_v2",
        verified_risks=[risk],
        status=TaskStatus.COMPLETED,
    )
    records = build_explanation_records(result, case_id="ipo_2023_00001")
    by_code = {record.risk_code: record for record in records}
    cash = by_code["cash_runway"]
    assert cash.evidence_pages == (7,)
    assert cash.evidence_previews == ("Auditable Production evidence text.",)
    assert cash.verifier_status == "verified"
    assert cash.provenance["source_risk_id"] == "r-1"
    assert cash.provenance["calculation_evidence_ids"] == ["e-1"]
    assert "cash / burn" in cash.calculation_summary
    assert by_code["continuous_loss"].missingness == "not_emitted"
    assert len(records) == len(V03_ENABLED_RISK_CODES)


def test_explanation_projection_rejects_duplicate_final_risk() -> None:
    risk = RiskItem(
        risk_code="cash_runway",
        category=RiskCategory.FINANCIAL,
        risk_type="Cash runway",
        level=RiskLevel.HIGH,
        score=80,
        conclusion="Duplicate.",
        agent_name="financial",
    )
    result = IPOAnalysisResult(
        request_id="req-1",
        company_name="Fixture",
        workflow_version="enhanced_v2",
        pending_risks=[risk, risk.model_copy(update={"risk_id": "r-2"})],
        status=TaskStatus.COMPLETED,
    )
    with pytest.raises(ValueError, match="duplicate final risk"):
        build_explanation_records(result, case_id="ipo_2023_00001")
