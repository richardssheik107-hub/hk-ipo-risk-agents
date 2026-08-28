from __future__ import annotations

from scripts.audit_v046_financial_conversion import build_audit


def test_conversion_audit_records_earliest_proven_stage_without_raw_gold() -> None:
    lifecycle = [
        {
            "case_id": "case-1",
            "risk_unit_id": "risk-1",
            "risk_code": "cash_runway",
            "gold_status": "verified",
            "gold_level": "critical",
            "gold_evidence_count": "2",
            "parser_anchor_available": "True",
            "first_gold_rank": "3",
            "agent_consumed": "True",
            "candidate_evidence_count": "20",
            "extraction_status": "needs_review",
            "builder_status": "UNAVAILABLE",
            "builder_risk_present": "False",
            "final_present": "False",
            "m1_correct": "False",
            "secondary_observations": '["period_end_mismatch"]',
        }
    ]
    retrieval = [
        {
            "case_id": "case-1",
            "risk_code": "cash_runway",
            "candidate_count": "20",
            "gold_page_in_top20": "True",
            "gold_anchor_in_top20": "True",
            "agent_consumed_gold_anchor": "True",
        }
    ]

    grouped, summary, trace = build_audit(lifecycle, retrieval)

    assert grouped["cash_runway"][0]["earliest_failure_stage"] == "extraction"
    assert summary["gold_used_at_runtime"] is False
    assert summary["blind_2025_accessed"] is False
    assert trace[0]["earliest_failure_stage"] == "extraction"


def test_conversion_audit_distinguishes_consumption_miss() -> None:
    lifecycle = [
        {
            "case_id": "case-2",
            "risk_unit_id": "risk-2",
            "risk_code": "customer_concentration",
            "gold_status": "verified",
            "gold_level": "high",
            "gold_evidence_count": "1",
            "parser_anchor_available": "True",
            "first_gold_rank": "12",
            "agent_consumed": "False",
            "candidate_evidence_count": "20",
        }
    ]
    retrieval = [
        {
            "case_id": "case-2",
            "risk_code": "customer_concentration",
            "candidate_count": "20",
            "gold_page_in_top20": "True",
            "gold_anchor_in_top20": "True",
            "agent_consumed_gold_anchor": "False",
        }
    ]

    grouped, summary, _ = build_audit(lifecycle, retrieval)

    assert grouped["customer_concentration"][0]["earliest_failure_stage"] == (
        "agent_consumption_miss"
    )
    assert summary["earliest_failure_counts"]["agent_consumption_miss"] == 1
