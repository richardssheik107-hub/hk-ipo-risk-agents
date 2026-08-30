from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ipo_risk.agents.rules import RuleVerifier
from ipo_risk.domain.cash_runway import CashRunwayRiskBuilder
from ipo_risk.domain.cash_runway_verifier import (
    CashRunwayRiskVerifier,
    CashRunwayVerificationStatus,
)
from ipo_risk.extraction import ExtractionStatus, FinancialExtractionResult, FinancialMetricValue
from ipo_risk.schemas import (
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationStatus,
)


def valid_case(period_months: int = 3) -> tuple[RiskItem, dict[str, Evidence]]:
    cash_evidence = Evidence(
        evidence_id="cash-e",
        document_id="doc",
        chunk_id="cash-chunk",
        page=10,
        text="Cash and cash equivalents at period end 77,208",
    )
    cash_flow_evidence = Evidence(
        evidence_id="ocf-e",
        document_id="doc",
        chunk_id="ocf-chunk",
        page=11,
        text="Net cash used in operating activities (83,918)",
    )
    extraction = FinancialExtractionResult(
        cash_and_cash_equivalents=FinancialMetricValue(
            metric_name="cash_and_cash_equivalents",
            normalized_value=Decimal("77208"),
            currency="CNY",
            unit="thousand",
            period_end=date(2024, 3, 31),
            evidence_id="cash-e",
            document_id="doc",
            chunk_id="cash-chunk",
            page=10,
            status=ExtractionStatus.EXTRACTED,
            extraction_method="page_text_rule",
        ),
        operating_cash_flow=FinancialMetricValue(
            metric_name="operating_cash_flow",
            normalized_value=Decimal("-83918"),
            currency="CNY",
            unit="thousand",
            period_end=date(2024, 3, 31),
            period_months=period_months,
            evidence_id="ocf-e",
            document_id="doc",
            chunk_id="ocf-chunk",
            page=11,
            status=ExtractionStatus.EXTRACTED,
            extraction_method="page_text_rule",
        ),
    )
    built = CashRunwayRiskBuilder().build(
        extraction,
        {"cash-e": cash_evidence, "ocf-e": cash_flow_evidence},
    )
    assert built.risk_item is not None
    return built.risk_item, {"cash-e": cash_evidence, "ocf-e": cash_flow_evidence}


def update_calculation(risk: RiskItem, **updates) -> RiskItem:
    assert risk.calculation is not None
    return risk.model_copy(update={"calculation": risk.calculation.model_copy(update=updates)})


def update_inputs(risk: RiskItem, **updates) -> RiskItem:
    assert risk.calculation is not None
    return update_calculation(risk, inputs={**risk.calculation.inputs, **updates})


def update_metadata(risk: RiskItem, **updates) -> RiskItem:
    return risk.model_copy(update={"metadata": {**risk.metadata, **updates}})


def assert_needs_review(risk: RiskItem, evidence: dict[str, Evidence]) -> None:
    result = CashRunwayRiskVerifier().verify(risk, evidence)
    assert result.status == CashRunwayVerificationStatus.NEEDS_REVIEW
    assert result.verified_risk is None
    assert result.reviewed_risk.verification_status == VerificationStatus.NEEDS_REVIEW


def test_valid_cash_runway_is_independently_verified() -> None:
    risk, evidence = valid_case()
    result = CashRunwayRiskVerifier().verify(risk, evidence)
    assert result.status == CashRunwayVerificationStatus.VERIFIED
    assert result.verified_risk is not None
    assert result.verified_risk.verification_status == VerificationStatus.VERIFIED
    assert "not a probability" in result.verified_risk.verification_notes
    assert result.issues == []
    assert all(result.checks.values())


def test_four_month_interim_cash_runway_is_independently_verified() -> None:
    risk, evidence = valid_case(period_months=4)

    result = CashRunwayRiskVerifier().verify(risk, evidence)

    assert result.status == CashRunwayVerificationStatus.VERIFIED
    assert result.verified_risk is not None


def test_one_evidence_item_can_support_both_cash_metrics() -> None:
    risk, evidence = valid_case()
    combined = evidence["cash-e"].model_copy(
        update={
            "evidence_id": "combined-e",
            "text": "Cash 77,208; net cash used in operating activities (83,918)",
        }
    )
    assert risk.calculation is not None
    risk = risk.model_copy(
        update={
            "evidence": [combined],
            "calculation": risk.calculation.model_copy(
                update={"evidence_ids": ["combined-e"]}
            ),
        }
    )

    result = CashRunwayRiskVerifier().verify(risk, {"combined-e": combined})

    assert result.status == CashRunwayVerificationStatus.VERIFIED


def test_calculation_missing_needs_review() -> None:
    risk, evidence = valid_case()
    assert_needs_review(risk.model_copy(update={"calculation": None}), evidence)


def test_failed_calculation_needs_review() -> None:
    risk, evidence = valid_case()
    assert_needs_review(update_calculation(risk, success=False, error="failed"), evidence)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("risk_code", "continuous_loss"),
        ("category", RiskCategory.LEGAL),
        ("agent_name", "legal"),
        ("conclusion", "Cash runway is 2.76 months but the company will go bankrupt."),
    ],
)
def test_tampered_risk_identity_or_conclusion_needs_review(
    field: str, value: object
) -> None:
    risk, evidence = valid_case()
    assert_needs_review(risk.model_copy(update={field: value}), evidence)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("skill_name", "other"),
        ("skill_version", "1.0"),
        ("formula", "cash / monthly_burn"),
        ("unit", "days"),
        ("error", "unexpected"),
    ],
)
def test_tampered_calculation_contract_needs_review(field: str, value: object) -> None:
    risk, evidence = valid_case()
    assert_needs_review(update_calculation(risk, **{field: value}), evidence)


def test_missing_available_evidence_stays_pending() -> None:
    risk, evidence = valid_case()
    evidence.pop("cash-e")
    result = CashRunwayRiskVerifier().verify(risk, evidence)
    assert result.status == CashRunwayVerificationStatus.PENDING
    assert result.reviewed_risk.verification_status == VerificationStatus.PENDING


def test_missing_embedded_evidence_stays_pending() -> None:
    risk, _ = valid_case()
    result = CashRunwayRiskVerifier().verify(risk.model_copy(update={"evidence": []}), {})
    assert result.status == CashRunwayVerificationStatus.PENDING


def test_calculation_evidence_id_conflict_needs_review() -> None:
    risk, evidence = valid_case()
    assert_needs_review(update_calculation(risk, evidence_ids=["cash-e", "wrong"]), evidence)


def test_reversed_evidence_order_needs_review() -> None:
    risk, evidence = valid_case()
    assert_needs_review(risk.model_copy(update={"evidence": list(reversed(risk.evidence))}), evidence)


def test_cross_document_evidence_needs_review() -> None:
    risk, evidence = valid_case()
    changed = risk.evidence[1].model_copy(update={"document_id": "other"})
    evidence["ocf-e"] = changed
    assert_needs_review(risk.model_copy(update={"evidence": [risk.evidence[0], changed]}), evidence)


def test_non_prospectus_evidence_needs_review() -> None:
    risk, evidence = valid_case()
    changed = risk.evidence[0].model_copy(update={"source_type": EvidenceSourceType.MARKET_DATA})
    evidence["cash-e"] = changed
    assert_needs_review(risk.model_copy(update={"evidence": [changed, risk.evidence[1]]}), evidence)


@pytest.mark.parametrize("index", [0, 1])
def test_evidence_without_supporting_number_needs_review(index: int) -> None:
    risk, evidence = valid_case()
    changed = risk.evidence[index].model_copy(update={"text": "unrelated financial prose"})
    evidence[changed.evidence_id] = changed
    items = list(risk.evidence)
    items[index] = changed
    assert_needs_review(risk.model_copy(update={"evidence": items}), evidence)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cash", "77209"),
        ("operating_cash_flow", "-83919"),
        ("period_months", 6),
        ("monthly_burn", "1"),
        ("currency", "HKD"),
        ("source_unit", "million"),
        ("operating_cash_flow_period_end", "2024-06-30"),
    ],
)
def test_tampered_calculation_input_needs_review(field: str, value: object) -> None:
    risk, evidence = valid_case()
    assert_needs_review(update_inputs(risk, **{field: value}), evidence)


def test_tampered_rounded_result_needs_review() -> None:
    risk, evidence = valid_case()
    assert_needs_review(update_calculation(risk, result="9.99"), evidence)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("runway_months_exact", "9"),
        ("runway_months_rounded", "9.00"),
        ("monthly_burn", "1"),
        ("currency", "HKD"),
        ("source_unit", "million"),
        ("period_months", 6),
        ("score_is_probability", True),
        ("canonical_code", "WRONG"),
        ("policy_version", "wrong"),
    ],
)
def test_tampered_risk_metadata_needs_review(field: str, value: object) -> None:
    risk, evidence = valid_case()
    assert_needs_review(update_metadata(risk, **{field: value}), evidence)


@pytest.mark.parametrize(
    "risk",
    [
        lambda item: item.model_copy(update={"level": RiskLevel.HIGH}),
        lambda item: item.model_copy(update={"score": 80}),
    ],
)
def test_tampered_policy_output_needs_review(risk) -> None:
    original, evidence = valid_case()
    assert_needs_review(risk(original), evidence)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", True, ""])
def test_non_finite_or_invalid_decimal_needs_review(value: object) -> None:
    risk, evidence = valid_case()
    assert_needs_review(update_inputs(risk, cash=value), evidence)


def test_duplicate_evidence_id_needs_review() -> None:
    risk, evidence = valid_case()
    duplicate = risk.evidence[0].model_copy()
    assert_needs_review(risk.model_copy(update={"evidence": [risk.evidence[0], duplicate]}), evidence)


@pytest.mark.parametrize("count", [0, 1])
def test_fewer_than_two_evidence_items_stay_pending(count: int) -> None:
    risk, evidence = valid_case()
    shortened = risk.model_copy(update={"evidence": risk.evidence[:count]})
    result = CashRunwayRiskVerifier().verify(shortened, evidence)
    assert result.status == CashRunwayVerificationStatus.PENDING
    assert "risk_evidence_count_invalid" in result.issues


def test_three_evidence_items_need_review() -> None:
    risk, evidence = valid_case()
    extra = risk.evidence[1].model_copy(
        update={"evidence_id": "extra-e", "chunk_id": "extra", "page": 12}
    )
    evidence[extra.evidence_id] = extra
    assert risk.calculation is not None
    changed = risk.model_copy(
        update={
            "evidence": [*risk.evidence, extra],
            "calculation": risk.calculation.model_copy(
                update={"evidence_ids": [*risk.calculation.evidence_ids, extra.evidence_id]}
            ),
        }
    )
    result = CashRunwayRiskVerifier().verify(changed, evidence)
    assert result.status == CashRunwayVerificationStatus.NEEDS_REVIEW
    assert "risk_evidence_count_invalid" in result.issues


def test_marked_equivalent_supporting_evidence_is_independently_verified() -> None:
    risk, evidence = valid_case()
    support = risk.evidence[0].model_copy(
        update={
            "evidence_id": "cash-support",
            "chunk_id": "cash-support-chunk",
            "page": 110,
            "metadata": {
                "equivalent_financial_fact_support": True,
                "supports_evidence_id": "cash-e",
            },
        }
    )
    evidence[support.evidence_id] = support
    changed = risk.model_copy(update={"evidence": [*risk.evidence, support]})

    result = CashRunwayRiskVerifier().verify(changed, evidence)

    assert result.status == CashRunwayVerificationStatus.VERIFIED
    assert result.issues == []


def test_calculation_with_extra_evidence_id_needs_review() -> None:
    risk, evidence = valid_case()
    assert risk.calculation is not None
    changed = update_calculation(
        risk, evidence_ids=[*risk.calculation.evidence_ids, "extra-e"]
    )
    assert_needs_review(changed, evidence)


def test_empty_evidence_text_needs_review() -> None:
    risk, evidence = valid_case()
    empty = risk.evidence[0].model_copy(update={"text": ""})
    evidence["cash-e"] = empty
    assert_needs_review(risk.model_copy(update={"evidence": [empty, risk.evidence[1]]}), evidence)


def test_rule_verifier_does_not_overwrite_embedded_evidence_with_empty_external_results() -> None:
    risk, _ = valid_case()
    result = RuleVerifier().verify([risk], {})
    assert len(result.verified_risks) == 1
    assert [item.evidence_id for item in result.verified_risks[0].evidence] == ["cash-e", "ocf-e"]


def test_rule_verifier_detects_conflicting_external_evidence() -> None:
    risk, evidence = valid_case()
    conflict = evidence["cash-e"].model_copy(update={"page": 99})
    result = RuleVerifier().verify([risk], {"cash_runway": [conflict]})
    assert not result.verified_risks
    assert result.pending_risks[0].verification_status == VerificationStatus.NEEDS_REVIEW


def test_rule_verifier_detects_conflicting_external_evidence_text() -> None:
    risk, evidence = valid_case()
    conflict = evidence["cash-e"].model_copy(
        update={"text": "Cash and cash equivalents at period end 1"}
    )
    result = RuleVerifier().verify(
        [risk], {"cash_runway": [conflict, evidence["ocf-e"]]}
    )
    assert not result.verified_risks
    assert result.pending_risks[0].verification_status == VerificationStatus.NEEDS_REVIEW
    assert "cash_evidence_text_mismatch" in result.pending_risks[0].verification_notes


def test_generic_rule_verifier_behavior_remains_compatible() -> None:
    evidence = Evidence(document_id="doc", page=1, text="legal clause")
    risk = RiskItem(
        risk_code="redemption_rights",
        category=RiskCategory.LEGAL,
        risk_type="Redemption rights",
        level=RiskLevel.HIGH,
        score=70,
        conclusion="Clause exists",
        evidence=[evidence],
        agent_name="legal",
    )
    result = RuleVerifier().verify([risk], {})
    assert result.verified_risks
    assert result.verified_risks[0].verification_status == VerificationStatus.VERIFIED


def test_verification_is_deterministic_and_does_not_mutate_input() -> None:
    risk, evidence = valid_case()
    risk_before = risk.model_dump()
    evidence_before = {key: value.model_dump() for key, value in evidence.items()}
    verifier = CashRunwayRiskVerifier()
    assert verifier.verify(risk, evidence) == verifier.verify(risk, evidence)
    assert risk.model_dump() == risk_before
    assert {key: value.model_dump() for key, value in evidence.items()} == evidence_before
