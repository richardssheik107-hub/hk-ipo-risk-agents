from __future__ import annotations

from pathlib import Path

import pytest

from ipo_risk.evaluation.existing_gold_metrics import (
    METRIC_PROTOCOL_VERSION,
    _manifest_hash,
    build_existing_gold_coverage,
    evaluate_existing_gold,
)


def _mini_manifest() -> dict:
    exact = "The investor has a redemption right if the listing does not occur."
    manifest = {
        "manifest_version": "v045_existing_gold_evaluable_manifest_v1",
        "metric_protocol_version": METRIC_PROTOCOL_VERSION,
        "evaluator_version": "v045_existing_gold_evaluator_v1",
        "existing_gold_source": "test frozen gold",
        "source_governance": {"source_inventory_matches_frozen": True},
        "official_existing_gold_case_count": 1,
        "evaluable_development_case_count": 1,
        "evaluable_validation_case_count": 0,
        "primary_risk_support": {},
        "risk_unit_count": 1,
        "positive_risk_unit_count": 1,
        "primary_positive_risk_unit_count": 1,
        "evidence_unit_count": 1,
        "primary_evidence_unit_count": 1,
        "risk_units": [
            {
                "risk_unit_id": "risk-unit-1",
                "case_id": "ipo_2023_00001",
                "stock_code": "0001.HK",
                "cohort_year": 2023,
                "split": "development",
                "source_manifest_key": "source-key",
                "source_annotation_hash": "source-hash",
                "source_audit_hash": None,
                "source_audit_status": "none",
                "source_risk_code": "redemption_rights",
                "competition_risk_family": "redemption_rights",
                "primary_scope": True,
                "explicit_gold_judgment": True,
                "applicable": True,
                "expected_status": "verified",
                "expected_level": "high",
                "calculation_requirement": None,
                "gold_evidence_unit_count": 1,
                "evaluable_positive": True,
            }
        ],
        "evidence_units": [
            {
                "evidence_unit_id": "evidence-unit-1",
                "case_id": "ipo_2023_00001",
                "stock_code": "0001.HK",
                "cohort_year": 2023,
                "split": "development",
                "source_manifest_key": "source-key",
                "source_annotation_hash": "source-hash",
                "source_audit_hash": None,
                "source_audit_status": "none",
                "source_risk_code": "redemption_rights",
                "competition_risk_family": "redemption_rights",
                "gold_risk_applicable": True,
                "primary_scope": True,
                "page": 12,
                "exact_text_hash": "text-hash",
                "exact_text": exact,
                "evidence_role": "primary",
                "requirement": "required",
                "source_authority": "legal_disclosure",
            }
        ],
        "new_manual_annotations_added": False,
        "existing_gold_modified": False,
        "blind_2025_outcome_accessed": False,
    }
    manifest["manifest_hash"] = _manifest_hash(manifest)
    return manifest


def _matching_result(*, text: str | None = None) -> dict:
    return {
        "stock_code": "0001.HK",
        "verified_risks": [
            {
                "risk_code": "redemption_rights",
                "level": "high",
                "verification_status": "verified",
                "evidence": [
                    {
                        "page": 12,
                        "text": text
                        or "Context: The investor has a redemption right if the listing does not occur.",
                        "relevance_score": 0.99,
                    }
                ],
            }
        ],
        "pending_risks": [],
        "rejected_risks": [],
        "metadata": {
            "case_id": "ipo_2023_00001",
            "configuration": {"use_mock": False},
            "component_modes": {
                "llm_provider": "openai_compatible",
                "llm_status": "available",
            },
        },
    }


def test_existing_gold_coverage_matches_frozen_source_inventory() -> None:
    manifest = build_existing_gold_coverage(Path("."))

    assert manifest["metric_protocol_version"] == METRIC_PROTOCOL_VERSION
    assert manifest["source_governance"]["source_inventory_matches_frozen"] is True
    assert manifest["official_existing_gold_case_count"] == 98
    assert (
        manifest["evaluable_development_case_count"]
        + manifest["evaluable_validation_case_count"]
        == 98
    )
    assert manifest["new_manual_annotations_added"] is False
    assert manifest["existing_gold_modified"] is False
    assert manifest["blind_2025_outcome_accessed"] is False
    assert (
        manifest["primary_risk_support"]["related_party_transaction"]["status"]
        == "NOT_EVALUABLE_FROM_EXISTING_GOLD"
    )


def test_existing_gold_evaluator_scores_exact_supported_prediction() -> None:
    summary, risk_rows, evidence_rows = evaluate_existing_gold(
        _mini_manifest(),
        [_matching_result()],
    )

    assert summary["risk_extraction"]["official_aligned_accuracy"] == 1.0
    assert summary["evidence_coverage"]["coverage_recall"] == 1.0
    assert summary["retrieval_diagnostics"]["recall_at_1"] == 1.0
    assert summary["measurement_gate"]["competition_pass_claim_eligible"] is True
    assert risk_rows[0]["correct"] is True
    assert evidence_rows[0]["covered"] is True


def test_evidence_same_page_wrong_text_does_not_cover_gold_anchor() -> None:
    summary, risk_rows, evidence_rows = evaluate_existing_gold(
        _mini_manifest(),
        [_matching_result(text="A completely different statement on the same page.")],
    )

    assert summary["evidence_coverage"]["coverage_recall"] == 0.0
    assert risk_rows[0]["evidence_hit"] is False
    assert risk_rows[0]["correct"] is False
    assert evidence_rows[0]["covered"] is False


def test_unmapped_prediction_does_not_turn_unjudged_into_negative() -> None:
    result = _matching_result()
    result["verified_risks"].append(
        {
            "risk_code": "precommercial_product",
            "level": "high",
            "verification_status": "verified",
            "evidence": [{"page": 3, "text": "product text", "relevance_score": 0.8}],
        }
    )
    summary, _, _ = evaluate_existing_gold(_mini_manifest(), [result])

    assert summary["risk_extraction"]["official_aligned_accuracy"] == 1.0
    assert summary["risk_extraction"]["existence_precision"] == 1.0


def test_validation_requires_explicit_open() -> None:
    manifest = _mini_manifest()
    manifest["risk_units"][0]["split"] = "validation"
    manifest["evidence_units"][0]["split"] = "validation"
    manifest["evaluable_development_case_count"] = 0
    manifest["evaluable_validation_case_count"] = 1
    manifest["manifest_hash"] = _manifest_hash(manifest)

    with pytest.raises(ValueError, match="explicit open_validation"):
        evaluate_existing_gold(manifest, [_matching_result()], split="validation")


def test_debug_subset_cannot_be_claimed_as_competition_pass() -> None:
    summary, _, _ = evaluate_existing_gold(
        _mini_manifest(),
        [_matching_result()],
        case_ids={"ipo_2023_00001"},
    )

    assert summary["evaluation_scope"] == "debug_subset"
    assert summary["measurement_gate"]["competition_pass_claim_eligible"] is False
