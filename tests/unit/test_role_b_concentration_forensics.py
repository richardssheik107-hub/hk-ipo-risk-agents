from ipo_risk.evaluation.role_b_concentration_forensics import (
    ConcentrationFormationEvidence,
    classify_concentration_formation,
    summarize_concentration_matrix,
)


def _evidence(**overrides: object) -> ConcentrationFormationEvidence:
    values: dict[str, object] = {
        "status": "needs_review",
        "merged_issues": (),
        "candidate_count": 2,
        "clean_complete_candidate_count": 0,
        "complete_candidate_count": 1,
        "largest_only_candidate_count": 0,
        "top_five_only_candidate_count": 0,
        "candidate_issue_counts": {},
    }
    values.update(overrides)
    return ConcentrationFormationEvidence(**values)  # type: ignore[arg-type]


def test_clean_extracted_fact_is_not_mislabeled_as_formation_failure() -> None:
    observed = classify_concentration_formation(
        _evidence(status="extracted", clean_complete_candidate_count=1)
    )
    assert observed["primary_pattern"] == "fact_formed_downstream_miss"
    assert observed["source_sufficiency"] == "source_information_sufficient_fact_formed"
    assert observed["generic_runtime_fix_candidate"] is False


def test_complete_companion_series_is_a_bounded_pipeline_fix_candidate() -> None:
    observed = classify_concentration_formation(
        _evidence(
            merged_issues=("value_period_count_mismatch",),
            candidate_issue_counts={"value_period_count_mismatch": 2},
        )
    )
    assert observed["primary_pattern"] == "companion_series_binding"
    assert observed["source_sufficiency"] == "source_information_sufficient_pipeline_failed"
    assert observed["generic_runtime_fix_candidate"] is True


def test_true_conflict_with_clean_candidates_remains_fail_closed() -> None:
    observed = classify_concentration_formation(
        _evidence(
            clean_complete_candidate_count=2,
            merged_issues=("period_months_conflict",),
        )
    )
    assert observed["primary_pattern"] == "genuine_conflict"
    assert observed["source_sufficiency"] == "genuine_ambiguity_fail_closed"
    assert observed["generic_runtime_fix_candidate"] is False


def test_multiple_complete_but_noisy_conflicting_candidates_remain_fail_closed() -> None:
    observed = classify_concentration_formation(
        _evidence(
            complete_candidate_count=2,
            merged_issues=("conflicting_values_for_same_period",),
        )
    )
    assert observed["primary_pattern"] == "genuine_conflict"
    assert observed["source_sufficiency"] == "genuine_ambiguity_fail_closed"
    assert observed["generic_runtime_fix_candidate"] is False


def test_complementary_partial_candidates_require_aggregation() -> None:
    observed = classify_concentration_formation(
        _evidence(
            complete_candidate_count=0,
            largest_only_candidate_count=1,
            top_five_only_candidate_count=1,
        )
    )
    assert observed["primary_pattern"] == "aggregation_required"
    assert observed["generic_runtime_fix_candidate"] is True


def test_missing_label_is_candidate_evidence_insufficient() -> None:
    observed = classify_concentration_formation(
        _evidence(
            candidate_count=0,
            complete_candidate_count=0,
            merged_issues=("concentration_label_not_found",),
        )
    )
    assert observed["primary_pattern"] == "insufficient_evidence"
    assert observed["source_sufficiency"] == "candidate_evidence_insufficient"
    assert observed["generic_runtime_fix_candidate"] is False


def test_summary_counts_units_and_fix_candidates() -> None:
    summary = summarize_concentration_matrix(
        [
            {
                "primary_pattern": "companion_series_binding",
                "source_sufficiency": "source_information_sufficient_pipeline_failed",
                "generic_runtime_fix_candidate": True,
            },
            {
                "primary_pattern": "genuine_conflict",
                "source_sufficiency": "genuine_ambiguity_fail_closed",
                "generic_runtime_fix_candidate": False,
            },
        ]
    )
    assert summary["unit_count"] == 2
    assert summary["generic_runtime_fix_candidate_count"] == 1
