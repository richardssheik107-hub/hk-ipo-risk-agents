from __future__ import annotations

from ipo_risk.evaluation.role_b_forensics import (
    _risk_root_cause,
    anchor_matches,
    build_evidence_lifecycle,
    build_m1_decomposition,
    build_m2_decomposition,
    build_retrieval_stage,
)


def _parser(unit_id: str, *, found: bool = True) -> dict[str, object]:
    return {
        "evidence_unit_id": unit_id,
        "anchor_found_expected_page": found,
        "anchor_found_any_page": found,
    }


def _trace(
    unit_id: str,
    *,
    page_rank: int | None,
    anchor_rank: int | None,
    consumed: bool,
) -> dict[str, object]:
    return {
        "trace_kind": "retrieval",
        "evidence_unit_id": unit_id,
        "candidate_count": 20,
        "first_gold_page_rank": page_rank,
        "first_gold_rank": anchor_rank,
        "agent_consumed": consumed,
        "retrieval_query_family": ["fixture"],
    }


def test_short_anchor_requires_exact_match() -> None:
    assert anchor_matches("short", "short")
    assert not anchor_matches("short", "a short phrase")
    assert anchor_matches("a sufficiently long anchor", "prefix a sufficiently long anchor suffix")


def test_retrieval_separates_page_only_candidate_and_ranking_misses() -> None:
    evaluated = [
        {"case_id": "ipo_2020_a", "evidence_unit_id": "page", "source_risk_code": "cash_runway"},
        {"case_id": "ipo_2020_a", "evidence_unit_id": "rank", "source_risk_code": "cash_runway"},
        {"case_id": "ipo_2020_a", "evidence_unit_id": "miss", "source_risk_code": "cash_runway"},
    ]
    traces = [
        _trace("page", page_rank=2, anchor_rank=None, consumed=False),
        _trace("rank", page_rank=2, anchor_rank=11, consumed=False),
        _trace("miss", page_rank=None, anchor_rank=None, consumed=False),
    ]
    rows, _ = build_retrieval_stage(evaluated, traces, [_parser(key) for key in ("page", "rank", "miss")])
    assert [row["retrieval_status"] for row in rows] == [
        "retrieved_page_anchor_truncated",
        "retrieval_ranking_or_topk_miss",
        "retrieval_candidate_miss",
    ]


def test_evidence_root_cause_uses_earliest_proven_stage() -> None:
    evaluated = [{"case_id": "ipo_2020_a", "evidence_unit_id": "e1", "source_risk_code": "cash_runway", "covered": False}]
    coverage = {"evidence_units": [{"case_id": "ipo_2020_a", "evidence_unit_id": "e1", "source_risk_code": "cash_runway", "page": 3, "exact_text": "a sufficiently long anchor"}]}
    retrieval = [{"evidence_unit_id": "e1", "first_gold_page_rank": None, "first_exact_anchor_rank": None, "agent_consumed_gold_anchor": False}]
    risk = [{"case_id": "ipo_2020_a", "risk_code": "cash_runway", "final_present": False, "final_bucket": "", "builder_risk_present": False}]
    rows = build_evidence_lifecycle(evaluated, coverage, [_parser("e1")], retrieval, risk, {"ipo_2020_a": {}})
    assert rows[0]["primary_root_cause"] == "retrieval_candidate_miss"
    assert rows[0]["proof_level"] == "PROVEN"


def test_evidence_missing_trace_is_unavailable_not_guessed() -> None:
    evaluated = [{"case_id": "ipo_2020_a", "evidence_unit_id": "e1", "source_risk_code": "cash_runway", "covered": False}]
    coverage = {"evidence_units": [{"case_id": "ipo_2020_a", "evidence_unit_id": "e1", "source_risk_code": "cash_runway", "page": 3, "exact_text": "a sufficiently long anchor"}]}
    retrieval = [{"evidence_unit_id": "e1", "first_gold_page_rank": 1, "first_exact_anchor_rank": 1, "agent_consumed_gold_anchor": True}]
    risk = [{"case_id": "ipo_2020_a", "risk_code": "cash_runway", "final_present": True, "final_bucket": "verified", "builder_risk_present": True}]
    result = {"ipo_2020_a": {"verified_risks": [{"risk_code": "cash_runway", "evidence": [{"page": 3, "text": "a sufficiently long anchor"}]}]}}
    rows = build_evidence_lifecycle(evaluated, coverage, [_parser("e1")], retrieval, risk, result)
    # Evaluator disagreement despite a retained, page/anchor-matching Evidence is not guessed.
    assert rows[0]["primary_root_cause"] == "unavailable_trace"
    assert rows[0]["proof_level"] == "UNAVAILABLE"


def test_waterfalls_are_cumulative_and_monotonic() -> None:
    risk_rows = [
        {"final_present": True, "final_bucket": "verified", "status_match": True, "level_match": False, "calculation_match": True, "evidence_hit": True, "m1_correct": False, "risk_code": "x", "primary_root_cause": "level_mismatch"},
        {"final_present": True, "final_bucket": "verified", "status_match": True, "level_match": True, "calculation_match": True, "evidence_hit": True, "m1_correct": True, "risk_code": "x", "primary_root_cause": "correct"},
    ]
    counts = [row["count"] for row in build_m1_decomposition(risk_rows)["waterfall"]]
    assert counts == sorted(counts, reverse=True)

    evidence_rows = [
        {"parser_expected_page": True, "first_gold_anchor_rank": 1, "agent_consumed": True, "candidate_risk_created": False, "final_positive_risk": True, "evidence_retained": True, "page_match": True, "anchor_match": True, "m2_covered": False},
        {"parser_expected_page": True, "first_gold_anchor_rank": 1, "agent_consumed": True, "candidate_risk_created": True, "final_positive_risk": True, "evidence_retained": True, "page_match": True, "anchor_match": True, "m2_covered": True},
    ]
    counts = [row["count"] for row in build_m2_decomposition(evidence_rows)["waterfall"]]
    assert counts == sorted(counts, reverse=True)


def test_llm_not_invoked_is_distinct_from_transport_failure() -> None:
    base = {
        "source_risk_code": "redemption_rights",
        "predicted_present": False,
    }
    parser = [{"anchor_found_any_page": True}]
    retrieval = [{"agent_consumed_gold_anchor": True}]
    root, proof, _ = _risk_root_cause(base, parser, retrieval, None, None)
    assert (root, proof) == ("llm_not_invoked_unexpectedly", "PROVEN")
    root, proof, _ = _risk_root_cause(
        base, parser, retrieval, None, {"failure_kind": "transport"}
    )
    assert (root, proof) == ("llm_transport_failure", "PROVEN")


def test_correct_unit_is_not_assigned_a_failure_root_cause() -> None:
    row = {"source_risk_code": "redemption_rights", "correct": True}
    root, proof, _ = _risk_root_cause(
        row,
        [{"anchor_found_any_page": True}],
        [{"agent_consumed_gold_anchor": True}],
        {"diagnostic_code": "needs_review", "issue_codes": ["bounded_uncertainty"]},
        {"failure_kind": None},
    )
    assert (root, proof) == ("correct", "PROVEN")


def test_builder_not_applicable_is_distinct_from_semantic_abstention() -> None:
    base = {
        "source_risk_code": "redemption_rights",
        "predicted_present": False,
    }
    parser = [{"anchor_found_any_page": True}]
    retrieval = [{"agent_consumed_gold_anchor": True}]
    successful = {"failure_kind": None}
    root, _, _ = _risk_root_cause(
        base,
        parser,
        retrieval,
        {"diagnostic_code": "not_applicable", "issue_codes": ["historical_right_only"]},
        successful,
    )
    assert root == "builder_not_applicable_misclassification"
    root, _, _ = _risk_root_cause(
        base,
        parser,
        retrieval,
        {"diagnostic_code": "needs_review", "issue_codes": ["rights_ambiguous"]},
        successful,
    )
    assert root == "llm_abstention_with_sufficient_evidence"


def test_verifier_and_final_binding_failures_remain_distinct() -> None:
    parser = [{"anchor_found_any_page": True}]
    retrieval = [{"agent_consumed_gold_anchor": True}]
    rejected = {
        "source_risk_code": "cash_runway",
        "predicted_present": True,
        "predicted_positive": False,
        "predicted_bucket": "rejected",
    }
    assert _risk_root_cause(rejected, parser, retrieval, None, None)[0] == "verifier_rejection"
    missing_evidence = {
        **rejected,
        "predicted_positive": True,
        "predicted_bucket": "verified",
        "status_match": True,
        "level_match": True,
        "calculation_match": True,
        "evidence_hit": False,
    }
    assert _risk_root_cause(missing_evidence, parser, retrieval, None, None)[0] == "final_evidence_not_retained"


def test_evidence_page_and_anchor_mismatches_remain_distinct() -> None:
    evaluated = [{"case_id": "ipo_2020_a", "evidence_unit_id": "e1", "source_risk_code": "cash_runway", "covered": False}]
    coverage = {"evidence_units": [{"case_id": "ipo_2020_a", "evidence_unit_id": "e1", "source_risk_code": "cash_runway", "page": 3, "exact_text": "a sufficiently long anchor"}]}
    retrieval = [{"evidence_unit_id": "e1", "first_gold_page_rank": 1, "first_exact_anchor_rank": 1, "agent_consumed_gold_anchor": True}]
    risk = [{"case_id": "ipo_2020_a", "risk_code": "cash_runway", "final_present": True, "final_bucket": "verified", "builder_risk_present": True}]
    wrong_page = {"ipo_2020_a": {"verified_risks": [{"risk_code": "cash_runway", "evidence": [{"page": 4, "text": "a sufficiently long anchor"}]}]}}
    rows = build_evidence_lifecycle(evaluated, coverage, [_parser("e1")], retrieval, risk, wrong_page)
    assert rows[0]["primary_root_cause"] == "final_evidence_page_mismatch"

    wrong_anchor = {"ipo_2020_a": {"verified_risks": [{"risk_code": "cash_runway", "evidence": [{"page": 3, "text": "different sufficiently long wording"}]}]}}
    rows = build_evidence_lifecycle(evaluated, coverage, [_parser("e1")], retrieval, risk, wrong_anchor)
    assert rows[0]["primary_root_cause"] == "final_evidence_anchor_mismatch"
