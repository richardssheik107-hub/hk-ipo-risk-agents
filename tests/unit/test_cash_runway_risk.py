from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ipo_risk.domain.cash_runway import (
    CashRunwayBuildStatus,
    CashRunwayRiskBuilder,
)
from ipo_risk.extraction import ExtractionStatus, FinancialExtractionResult, FinancialMetricValue
from ipo_risk.schemas import (
    Evidence,
    EvidenceSourceType,
    RiskLevel,
    SkillResult,
    VerificationStatus,
)


def metric(
    name: str,
    value: str,
    evidence_id: str,
    page: int,
    *,
    status: ExtractionStatus = ExtractionStatus.EXTRACTED,
    currency: str | None = "CNY",
    unit: str | None = "thousand",
    period_end: date | None = date(2024, 3, 31),
    period_months: int | None = None,
    issues: list[str] | None = None,
) -> FinancialMetricValue:
    return FinancialMetricValue(
        metric_name=name,
        normalized_value=Decimal(value),
        currency=currency,
        unit=unit,
        period_end=period_end,
        period_months=period_months,
        evidence_id=evidence_id,
        document_id="doc",
        chunk_id=f"doc:page:{page}",
        page=page,
        status=status,
        issues=issues or [],
        extraction_method="page_text_rule",
    )


def inputs(
    *,
    cash: str = "77208",
    cash_flow: str = "-83918",
    period_months: int | None = 3,
) -> tuple[FinancialExtractionResult, dict[str, Evidence]]:
    cash_metric = metric("cash_and_cash_equivalents", cash, "cash-e", 71)
    cash_flow_metric = metric(
        "operating_cash_flow", cash_flow, "ocf-e", 72, period_months=period_months
    )
    extraction = FinancialExtractionResult(
        cash_and_cash_equivalents=cash_metric,
        operating_cash_flow=cash_flow_metric,
    )
    evidence = {
        "cash-e": Evidence(
            evidence_id="cash-e",
            document_id="doc",
            chunk_id="doc:page:71",
            page=71,
            text="cash source",
        ),
        "ocf-e": Evidence(
            evidence_id="ocf-e",
            document_id="doc",
            chunk_id="doc:page:72",
            page=72,
            text="cash flow source",
        ),
    }
    return extraction, evidence


def test_builds_pending_cash_runway_risk_with_complete_traceability() -> None:
    extraction, evidence = inputs()
    result = CashRunwayRiskBuilder().build(extraction, evidence)

    assert result.status == CashRunwayBuildStatus.BUILT
    assert result.calculation is not None
    assert result.risk_item is not None
    assert result.calculation.result == str(Decimal("77208") * Decimal("3") / Decimal("83918"))
    assert result.risk_item.metadata["runway_months_rounded"] == "2.76"
    assert result.calculation.evidence_ids == ["cash-e", "ocf-e"]
    assert [item.evidence_id for item in result.risk_item.evidence] == ["cash-e", "ocf-e"]
    assert result.risk_item.risk_code == "cash_runway"
    assert result.risk_item.metadata["canonical_code"] == "FIN_CASH_RUNWAY"
    assert result.risk_item.verification_status == VerificationStatus.PENDING
    assert result.risk_item.level == RiskLevel.CRITICAL
    assert result.risk_item.score == 90
    assert result.risk_item.metadata["score_is_probability"] is False


def test_one_page_can_support_both_cash_and_operating_cash_flow() -> None:
    extraction, evidence = inputs()
    combined = evidence["cash-e"].model_copy(
        update={
            "evidence_id": "combined-e",
            "text": "cash 77208; operating cash flow (83918)",
        }
    )
    cash = extraction.cash_and_cash_equivalents.model_copy(
        update={
            "evidence_id": "combined-e",
            "chunk_id": combined.chunk_id,
            "page": combined.page,
        }
    )
    cash_flow = extraction.operating_cash_flow.model_copy(
        update={
            "evidence_id": "combined-e",
            "chunk_id": combined.chunk_id,
            "page": combined.page,
        }
    )

    result = CashRunwayRiskBuilder().build(
        extraction.model_copy(
            update={
                "cash_and_cash_equivalents": cash,
                "operating_cash_flow": cash_flow,
            }
        ),
        {"combined-e": combined},
    )

    assert result.status == CashRunwayBuildStatus.BUILT
    assert result.risk_item is not None
    assert [item.evidence_id for item in result.risk_item.evidence] == ["combined-e"]
    assert result.calculation is not None
    assert result.calculation.evidence_ids == ["combined-e"]


def test_equivalent_financial_sources_are_retained_as_supporting_evidence() -> None:
    extraction, evidence = inputs()
    cash_support = evidence["cash-e"].model_copy(
        update={
            "evidence_id": "cash-support",
            "chunk_id": "doc:page:171",
            "page": 171,
            "text": "same cash fact in a second prospectus section",
        }
    )
    flow_support = evidence["ocf-e"].model_copy(
        update={
            "evidence_id": "ocf-support",
            "chunk_id": "doc:page:172",
            "page": 172,
            "text": "same cash-flow fact in a second prospectus section",
        }
    )
    cash = extraction.cash_and_cash_equivalents.model_copy(
        update={"metadata": {"equivalent_evidence_ids": ["cash-e", "cash-support"]}}
    )
    cash_flow = extraction.operating_cash_flow.model_copy(
        update={"metadata": {"equivalent_evidence_ids": ["ocf-e", "ocf-support"]}}
    )

    result = CashRunwayRiskBuilder().build(
        extraction.model_copy(
            update={
                "cash_and_cash_equivalents": cash,
                "operating_cash_flow": cash_flow,
            }
        ),
        {**evidence, "cash-support": cash_support, "ocf-support": flow_support},
    )

    assert result.status == CashRunwayBuildStatus.BUILT
    assert result.risk_item is not None
    assert [item.evidence_id for item in result.risk_item.evidence] == [
        "cash-e",
        "ocf-e",
        "cash-support",
        "ocf-support",
    ]
    assert result.calculation is not None
    assert result.calculation.evidence_ids == ["cash-e", "ocf-e"]


@pytest.mark.parametrize("field", ["cash_and_cash_equivalents", "operating_cash_flow"])
@pytest.mark.parametrize("status", [ExtractionStatus.NEEDS_REVIEW, ExtractionStatus.NOT_FOUND])
def test_non_extracted_metric_never_builds(field: str, status: ExtractionStatus) -> None:
    extraction, evidence = inputs()
    updated = getattr(extraction, field).model_copy(update={"status": status})
    extraction = extraction.model_copy(update={field: updated})
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    assert result.status == CashRunwayBuildStatus.NEEDS_REVIEW
    assert result.calculation is None
    assert result.risk_item is None


@pytest.mark.parametrize(
    ("field", "value", "issue"),
    [
        ("currency", "HKD", "currency_mismatch"),
        ("unit", "million", "unit_mismatch"),
        ("period_end", date(2024, 6, 30), "period_end_mismatch"),
        ("period_months", None, "operating_cash_flow_period_months_invalid"),
        ("period_months", 13, "operating_cash_flow_period_months_invalid"),
    ],
)
def test_incompatible_financial_facts_never_build(
    field: str, value: object, issue: str
) -> None:
    extraction, evidence = inputs()
    cash_flow = extraction.operating_cash_flow.model_copy(update={field: value})
    result = CashRunwayRiskBuilder().build(
        extraction.model_copy(update={"operating_cash_flow": cash_flow}), evidence
    )
    assert result.status == CashRunwayBuildStatus.NEEDS_REVIEW
    assert issue in result.issues
    assert result.calculation is None


def test_four_month_interim_cash_flow_builds_without_rescaling() -> None:
    extraction, evidence = inputs(cash="3864", cash_flow="-31645", period_months=4)

    result = CashRunwayRiskBuilder().build(extraction, evidence)

    assert result.status == CashRunwayBuildStatus.BUILT
    assert result.calculation is not None
    assert result.calculation.result == str(Decimal("3864") * Decimal("4") / Decimal("31645"))


def test_extraction_issues_prevent_calculation() -> None:
    extraction, evidence = inputs()
    cash = extraction.cash_and_cash_equivalents.model_copy(update={"issues": ["ambiguous"]})
    result = CashRunwayRiskBuilder().build(
        extraction.model_copy(update={"cash_and_cash_equivalents": cash}), evidence
    )
    assert result.status == CashRunwayBuildStatus.NEEDS_REVIEW
    assert "cash_extraction_has_issues" in result.issues


def test_missing_evidence_prevents_calculation() -> None:
    extraction, evidence = inputs()
    evidence.pop("cash-e")
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    assert result.status == CashRunwayBuildStatus.NEEDS_REVIEW
    assert "cash_evidence_not_found" in result.issues


@pytest.mark.parametrize("field", ["evidence_id", "document_id", "chunk_id", "page"])
def test_evidence_identity_mismatch_prevents_calculation(field: str) -> None:
    extraction, evidence = inputs()
    replacement: object = "different"
    if field == "page":
        replacement = 99
    evidence["cash-e"] = evidence["cash-e"].model_copy(update={field: replacement})
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    assert result.status == CashRunwayBuildStatus.NEEDS_REVIEW
    assert f"cash_evidence_{field}_mismatch" in result.issues
    assert result.risk_item is None


@pytest.mark.parametrize("cash_flow", ["0", "1"])
def test_non_negative_operating_cash_flow_is_not_applicable(cash_flow: str) -> None:
    extraction, evidence = inputs(cash_flow=cash_flow)
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    assert result.status == CashRunwayBuildStatus.NOT_APPLICABLE
    assert result.calculation is None
    assert result.risk_item is None


def test_negative_cash_needs_review() -> None:
    extraction, evidence = inputs(cash="-1")
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    assert result.status == CashRunwayBuildStatus.NEEDS_REVIEW
    assert "cash_value_negative" in result.issues


@pytest.mark.parametrize(
    ("cash_flow", "level", "score"),
    [
        ("-100", RiskLevel.HIGH, 80),
        ("-50", RiskLevel.MEDIUM, 60),
    ],
)
def test_policy_boundaries_are_explicit(
    cash_flow: str, level: RiskLevel, score: int
) -> None:
    extraction, evidence = inputs(cash="100", cash_flow=cash_flow, period_months=3)
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    assert result.risk_item is not None
    assert result.risk_item.level == level
    assert result.risk_item.score == score


def test_twelve_month_or_longer_runway_is_not_a_risk_item() -> None:
    extraction, evidence = inputs(cash="100", cash_flow="-25", period_months=3)

    result = CashRunwayRiskBuilder().build(extraction, evidence)

    assert result.status == CashRunwayBuildStatus.NOT_APPLICABLE
    assert result.risk_item is None
    assert result.calculation is None
    assert result.metadata["runway_months_exact"] == "12"
    assert result.metadata["threshold_months"] == "12"


def test_builder_consumes_skill_output_instead_of_reimplementing_formula(monkeypatch) -> None:
    extraction, evidence = inputs()

    def fake_skill(*args, **kwargs) -> SkillResult:
        return SkillResult(
            skill_name="cash_runway",
            skill_version="test",
            success=True,
            value=Decimal("7.5"),
            evidence_ids=["cash-e", "ocf-e"],
            metadata={"monthly_burn": Decimal("2"), "rounded_months": Decimal("7.50")},
        )

    monkeypatch.setattr("ipo_risk.domain.cash_runway.cash_runway_from_operating_cash_flow", fake_skill)
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    assert result.calculation is not None
    assert result.calculation.result == "7.5"
    assert result.risk_item is not None
    assert result.risk_item.level == RiskLevel.MEDIUM
    assert result.risk_item.metadata["monthly_burn"] == "2"


def test_builder_does_not_mutate_inputs_and_core_output_is_deterministic() -> None:
    extraction, evidence = inputs()
    extraction_before = extraction.model_dump()
    evidence_before = {key: value.model_dump() for key, value in evidence.items()}
    builder = CashRunwayRiskBuilder()
    first = builder.build(extraction, evidence)
    second = builder.build(extraction, evidence)
    assert extraction.model_dump() == extraction_before
    assert {key: value.model_dump() for key, value in evidence.items()} == evidence_before
    assert first.calculation == second.calculation
    assert first.risk_item is not None and second.risk_item is not None
    assert first.risk_item.risk_id == second.risk_item.risk_id
    assert first.risk_item.model_dump(exclude={"created_at"}) == second.risk_item.model_dump(
        exclude={"created_at"}
    )


def test_builder_has_no_company_page_or_fixture_dependency() -> None:
    extraction, evidence = inputs()
    cash = extraction.cash_and_cash_equivalents.model_copy(
        update={"document_id": "another-doc", "chunk_id": "arbitrary-cash", "page": 8}
    )
    cash_flow = extraction.operating_cash_flow.model_copy(
        update={"document_id": "another-doc", "chunk_id": "arbitrary-ocf", "page": 9}
    )
    evidence = {
        "cash-e": evidence["cash-e"].model_copy(
            update={"document_id": "another-doc", "chunk_id": "arbitrary-cash", "page": 8}
        ),
        "ocf-e": evidence["ocf-e"].model_copy(
            update={"document_id": "another-doc", "chunk_id": "arbitrary-ocf", "page": 9}
        ),
    }
    result = CashRunwayRiskBuilder().build(
        extraction.model_copy(
            update={"cash_and_cash_equivalents": cash, "operating_cash_flow": cash_flow}
        ),
        evidence,
    )
    assert result.status == CashRunwayBuildStatus.BUILT


def test_rejects_swapped_metric_names() -> None:
    extraction, evidence = inputs()
    swapped = extraction.model_copy(
        update={
            "cash_and_cash_equivalents": extraction.cash_and_cash_equivalents.model_copy(
                update={"metric_name": "operating_cash_flow"}
            ),
            "operating_cash_flow": extraction.operating_cash_flow.model_copy(
                update={"metric_name": "cash_and_cash_equivalents"}
            ),
        }
    )
    result = CashRunwayRiskBuilder().build(swapped, evidence)
    assert result.status == CashRunwayBuildStatus.NEEDS_REVIEW
    assert {"cash_metric_name_invalid", "operating_cash_flow_metric_name_invalid"}.issubset(
        result.issues
    )


def test_rejects_cross_document_metrics() -> None:
    extraction, evidence = inputs()
    cash_flow = extraction.operating_cash_flow.model_copy(update={"document_id": "other-doc"})
    result = CashRunwayRiskBuilder().build(
        extraction.model_copy(update={"operating_cash_flow": cash_flow}), evidence
    )
    assert "source_document_mismatch" in result.issues


def test_rejects_cash_with_duration() -> None:
    extraction, evidence = inputs()
    cash = extraction.cash_and_cash_equivalents.model_copy(update={"period_months": 3})
    result = CashRunwayRiskBuilder().build(
        extraction.model_copy(update={"cash_and_cash_equivalents": cash}), evidence
    )
    assert "cash_period_months_should_be_none" in result.issues


def test_rejects_non_prospectus_evidence() -> None:
    extraction, evidence = inputs()
    evidence["cash-e"] = evidence["cash-e"].model_copy(
        update={"source_type": EvidenceSourceType.MARKET_DATA}
    )
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    assert "evidence_source_type_invalid" in result.issues


def test_rejects_cross_document_evidence() -> None:
    extraction, evidence = inputs()
    cash_flow = extraction.operating_cash_flow.model_copy(update={"document_id": "other-doc"})
    evidence["ocf-e"] = evidence["ocf-e"].model_copy(update={"document_id": "other-doc"})
    result = CashRunwayRiskBuilder().build(
        extraction.model_copy(update={"operating_cash_flow": cash_flow}), evidence
    )
    assert "source_document_mismatch" in result.issues
    assert "evidence_document_mismatch" in result.issues
