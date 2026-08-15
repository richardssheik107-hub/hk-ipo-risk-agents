from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES, V03_RISK_OWNERS
from ipo_risk.modeling.exceptions import (
    DocumentSnapshotValidationError,
    DuplicateAuthoritativeRiskError,
)
from ipo_risk.modeling.features import (
    CANONICAL_V03_RISK_ORDER,
    DOCUMENT_FEATURE_MANIFEST_V1,
    vectorize_document_snapshot,
)
from ipo_risk.modeling.snapshot import DocumentRiskSnapshotBuilder
from ipo_risk.schemas import (
    AnalysisError,
    Calculation,
    Evidence,
    IPOAnalysisResult,
    PredictionResult,
    RiskCategory,
    RiskItem,
    RiskLevel,
    TaskStatus,
    VerificationStatus,
)
from ipo_risk.schemas.market import MarketDatasetSplit, expected_market_split
from ipo_risk.schemas.modeling import (
    DocumentRiskFeatureState,
    DocumentRiskSnapshotBuildContext,
)


def context(
    year: int = 2023,
    *,
    commit: str = "a" * 40,
    case_id: str | None = None,
    stock_code: str = "0001.HK",
) -> DocumentRiskSnapshotBuildContext:
    return DocumentRiskSnapshotBuildContext(
        case_id=case_id or f"ipo_{year}_00001",
        document_id=f"document-{year}-0001",
        stock_code=stock_code,
        cohort_year=year,
        listing_date=date(year, 1, 2),
        dataset_split=expected_market_split(year),
        document_pipeline_version="v03_enhanced_v2",
        document_pipeline_commit=commit,
    )


def risk(
    risk_code: str,
    state: VerificationStatus,
    *,
    risk_id: str | None = None,
    with_calculation: bool = False,
) -> RiskItem:
    owner = V03_RISK_OWNERS.get(risk_code, "market")
    calculation = (
        Calculation(
            skill_name="fixture",
            formula="1 + 1",
            result=2,
            success=True,
        )
        if with_calculation
        else None
    )
    return RiskItem(
        risk_id=risk_id or f"risk-{risk_code}-{state.value}",
        risk_code=risk_code,
        category=RiskCategory(owner),
        risk_type=risk_code,
        level=RiskLevel.HIGH,
        score=72,
        conclusion="fixture conclusion",
        evidence=[Evidence(evidence_id=f"evidence-{risk_code}", text="fixture")],
        calculation=calculation,
        agent_name=f"{owner}_agent",
        confidence=0.8,
        verification_status=state,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def analysis(
    *,
    year: int = 2023,
    verified: list[RiskItem] | None = None,
    pending: list[RiskItem] | None = None,
    rejected: list[RiskItem] | None = None,
    status: TaskStatus = TaskStatus.COMPLETED,
    errors: list[AnalysisError] | None = None,
    metadata: dict | None = None,
) -> IPOAnalysisResult:
    base_metadata = {
        "case_id": f"ipo_{year}_00001",
        "dataset_split": expected_market_split(year).value,
        "ipo_profile": {
            "stock_code": "0001.HK",
            "listing_date": date(year, 1, 2).isoformat(),
        },
        "document": {"document_id": f"document-{year}-0001"},
        "supervision": {"conflicts": []},
    }
    return IPOAnalysisResult(
        analysis_id=f"analysis-{year}-0001",
        request_id=f"request-{year}-0001",
        company_name="Fixture IPO",
        stock_code="0001.HK",
        workflow_version="enhanced_v2",
        schema_version="1.0",
        verified_risks=verified or [],
        pending_risks=pending or [],
        rejected_risks=rejected or [],
        prediction=PredictionResult(
            model_name="RuleBasedPredictor",
            model_version="rule_v2",
            risk_score=72,
            risk_level=RiskLevel.HIGH,
        ),
        status=status,
        errors=errors or [],
        metadata={**base_metadata, **(metadata or {})},
    )


def feature_by_code(snapshot, risk_code: str):
    return next(item for item in snapshot.risk_features if item.risk_code == risk_code)


def vector_values(snapshot) -> dict[str, int | float | None]:
    vector = vectorize_document_snapshot(snapshot)
    return dict(zip(vector.feature_names, vector.feature_values))


def test_exact_authoritative_eight_risks_and_stable_order() -> None:
    snapshot = DocumentRiskSnapshotBuilder().build(analysis(), context())
    assert set(CANONICAL_V03_RISK_ORDER) == set(V03_ENABLED_RISK_CODES)
    assert len(CANONICAL_V03_RISK_ORDER) == 8
    assert tuple(item.risk_code for item in snapshot.risk_features) == tuple(
        sorted(V03_ENABLED_RISK_CODES)
    )


def test_verified_pending_review_rejected_and_not_emitted_states() -> None:
    result = analysis(
        verified=[risk("cash_runway", VerificationStatus.VERIFIED, with_calculation=True)],
        pending=[
            risk("continuous_loss", VerificationStatus.PENDING),
            risk("revenue_growth", VerificationStatus.NEEDS_REVIEW),
        ],
        rejected=[risk("redemption_rights", VerificationStatus.REJECTED)],
    )
    snapshot = DocumentRiskSnapshotBuilder().build(result, context())
    assert feature_by_code(snapshot, "cash_runway").state is DocumentRiskFeatureState.VERIFIED
    assert feature_by_code(snapshot, "continuous_loss").state is DocumentRiskFeatureState.PENDING
    assert feature_by_code(snapshot, "revenue_growth").state is DocumentRiskFeatureState.NEEDS_REVIEW
    assert feature_by_code(snapshot, "redemption_rights").state is DocumentRiskFeatureState.REJECTED
    assert feature_by_code(snapshot, "supplier_concentration").state is DocumentRiskFeatureState.NOT_EMITTED
    assert feature_by_code(snapshot, "cash_runway").calculation_success is True


def test_component_failure_produces_unavailable_not_safe_zero() -> None:
    result = analysis(
        status=TaskStatus.PARTIAL,
        errors=[
            AnalysisError(
                stage="financial",
                component="financial_agent",
                code="component_failure",
                message="fixture failure",
            )
        ],
    )
    snapshot = DocumentRiskSnapshotBuilder().build(result, context())
    item = feature_by_code(snapshot, "cash_runway")
    values = vector_values(snapshot)
    assert item.state is DocumentRiskFeatureState.UNAVAILABLE
    assert item.score is None
    assert values["cash_runway__score"] is None
    assert values["cash_runway__state_unavailable"] == 1
    assert values["cash_runway__missing"] == 1


def test_not_emitted_is_not_silently_encoded_as_safe_zero() -> None:
    snapshot = DocumentRiskSnapshotBuilder().build(analysis(), context())
    values = vector_values(snapshot)
    assert values["cash_runway__state_not_emitted"] == 1
    assert values["cash_runway__score"] is None
    assert values["cash_runway__missing"] == 1
    assert values["max_verified_score"] is None
    assert values["mean_verified_score"] is None


def test_duplicate_authoritative_risk_fails_closed() -> None:
    result = analysis(
        verified=[risk("cash_runway", VerificationStatus.VERIFIED, risk_id="verified")],
        pending=[risk("cash_runway", VerificationStatus.PENDING, risk_id="pending")],
    )
    with pytest.raises(DuplicateAuthoritativeRiskError, match="cash_runway"):
        DocumentRiskSnapshotBuilder().build(result, context())


def test_unknown_risk_is_diagnostic_only_and_does_not_change_manifest() -> None:
    result = analysis(pending=[risk("future_unknown_risk", VerificationStatus.PENDING)])
    snapshot = DocumentRiskSnapshotBuilder().build(result, context())
    vector = vectorize_document_snapshot(snapshot)
    assert snapshot.unknown_risk_codes == ("future_unknown_risk",)
    assert vector.feature_names == tuple(
        item.name for item in DOCUMENT_FEATURE_MANIFEST_V1.features
    )
    assert not any("future_unknown_risk" in name for name in vector.feature_names)


def test_snapshot_and_vector_generation_are_deterministic() -> None:
    result = analysis(verified=[risk("cash_runway", VerificationStatus.VERIFIED)])
    builder = DocumentRiskSnapshotBuilder()
    first = builder.build(result, context())
    second = builder.build(result, context())
    assert first.canonical_json() == second.canonical_json()
    assert first.content_hash() == second.content_hash()
    assert vectorize_document_snapshot(first) == vectorize_document_snapshot(second)


def test_pipeline_commits_distinguish_provenance_even_when_features_match() -> None:
    result = analysis(verified=[risk("cash_runway", VerificationStatus.VERIFIED)])
    builder = DocumentRiskSnapshotBuilder()
    first = builder.build(result, context(commit="a" * 40))
    second = builder.build(result, context(commit="b" * 40))
    assert first.document_pipeline_commit != second.document_pipeline_commit
    assert first.content_hash() != second.content_hash()
    assert vectorize_document_snapshot(first).feature_values == vectorize_document_snapshot(
        second
    ).feature_values


def test_workflow_schema_pipeline_and_analysis_provenance_are_preserved() -> None:
    snapshot = DocumentRiskSnapshotBuilder().build(analysis(), context())
    assert snapshot.workflow_version == "enhanced_v2"
    assert snapshot.schema_version == "1.0"
    assert snapshot.feature_schema_version == "v04_document_features_v1"
    assert snapshot.document_pipeline_version == "v03_enhanced_v2"
    assert snapshot.document_pipeline_commit == "a" * 40
    assert snapshot.source_analysis_id == "analysis-2023-0001"
    assert snapshot.source_analysis_status == "completed"
    assert snapshot.rule_predictor_version == "rule_v2"
    assert not any("rule" in item.name for item in DOCUMENT_FEATURE_MANIFEST_V1.features)


@pytest.mark.parametrize(
    "mutation,error",
    [
        ({"case_id": "different-case"}, "case_id"),
        ({"dataset_split": "validation"}, "dataset split"),
        ({"document": {"document_id": "different-document"}}, "document_id"),
        (
            {"ipo_profile": {"stock_code": "0001.HK", "listing_date": "2023-02-01"}},
            "listing_date",
        ),
    ],
)
def test_source_identity_mismatches_are_rejected(mutation: dict, error: str) -> None:
    with pytest.raises(DocumentSnapshotValidationError, match=error):
        DocumentRiskSnapshotBuilder().build(
            analysis(metadata=mutation),
            context(),
        )


def test_stock_code_mismatch_is_rejected() -> None:
    result = analysis().model_copy(update={"stock_code": "9999.HK"})
    with pytest.raises(DocumentSnapshotValidationError, match="stock_code"):
        DocumentRiskSnapshotBuilder().build(result, context())


def test_nonfinal_analysis_and_bucket_state_mismatch_are_rejected() -> None:
    with pytest.raises(DocumentSnapshotValidationError, match="final status"):
        DocumentRiskSnapshotBuilder().build(
            analysis(status=TaskStatus.RUNNING), context()
        )
    invalid = analysis(
        verified=[risk("cash_runway", VerificationStatus.PENDING)]
    )
    with pytest.raises(DocumentSnapshotValidationError, match="bucket"):
        DocumentRiskSnapshotBuilder().build(invalid, context())


def test_context_rejects_listing_year_or_split_mismatch() -> None:
    with pytest.raises(ValidationError, match="listing date"):
        context().model_validate(
            {**context().model_dump(), "listing_date": date(2024, 1, 2)}
        )
    with pytest.raises(ValidationError, match="split"):
        context().model_validate(
            {**context().model_dump(), "dataset_split": MarketDatasetSplit.VALIDATION}
        )
