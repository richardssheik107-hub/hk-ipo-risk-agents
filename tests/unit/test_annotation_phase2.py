from __future__ import annotations

import json
from pathlib import Path

from ipo_risk.quality.annotation_phase2 import (
    CORRECTION_FILENAME,
    classify_insufficient,
    resolve_concentration_bound,
    run_phase2,
)


def test_strict_single_customer_bound_excludes_medium_with_explicit_top_five_cardinality():
    result = resolve_concentration_bound(
        {
            "bound_operator": "<",
            "single_customer_upper_bound_pct": 10,
            "maximum_customers_considered": 5,
        },
        "customer",
    )
    assert result["resolution_status"] == "resolved"
    assert result["resolved_level"] == "not_applicable"


def test_non_strict_supplier_bound_near_threshold_requires_review():
    result = resolve_concentration_bound(
        {
            "bound_operator": "<=",
            "largest_supplier_upper_bound_pct": 32.0,
            "top_five_supplier_pct": 32.0,
        },
        "supplier",
    )
    assert result["resolution_status"] == "review_required"
    assert result["requires_human_review"] is True


def test_top_five_bound_also_bounds_largest():
    result = resolve_concentration_bound(
        {
            "bound_operator": "<",
            "top_five_supplier_upper_bound_pct": 30.0,
        },
        "supplier",
    )
    assert result["resolution_status"] == "resolved"
    assert result["resolved_level"] == "not_applicable"


def test_insufficient_positive_record_gets_p0_existing_evidence_backfill():
    finding = {
        "risk_code": "revenue_growth",
        "finding_code": "REVENUE_RECOMPUTE_INPUTS_INSUFFICIENT",
        "current_applicable": True,
        "current_status": "verified",
        "details": {"previous_revenue": None, "current_revenue": None},
    }
    bundle = {
        "evidence": [
            {
                "risk_code": "revenue_growth",
                "evidence_role": "primary",
                "page": 10,
                "exact_text": "Revenue ...",
            }
        ]
    }
    result = classify_insufficient(finding, bundle)
    assert result["priority"] == "P0_POSITIVE_OR_NEEDS_REVIEW"
    assert result["evidence_state"] == "EXISTING_EVIDENCE_BACKFILL"
    assert result["backfill_type"] == "REVENUE_COMPARABLE_VALUE_BACKFILL"
    assert result["evidence_count"] == 1


def test_repository_phase2_counts_and_pass1_immutability(tmp_path: Path):
    summary = run_phase2(Path("."), tmp_path / "phase2", write_corrections=False)

    assert summary["cases_scanned"] == 60
    assert summary["hard_deterministic_corrections"] == 7
    assert summary["correction_case_count"] == 6
    assert summary["policy_ambiguities_total"] == 33
    # Conservative Phase 2 resolves only formal bounds that explicitly supply
    # enough aggregate structure; one single-customer-only bound remains review.
    assert summary["policy_deterministically_resolved"] == 23
    assert summary["policy_review_remaining"] == 10
    assert summary["insufficient_input_total"] == 142
    assert summary["insufficient_priority_counts"] == {
        "P0_POSITIVE_OR_NEEDS_REVIEW": 51,
        "P1_REJECTED_LABEL_BACKFILL": 91,
    }
    assert summary["insufficient_evidence_state_counts"] == {
        "EXISTING_EVIDENCE_BACKFILL": 142,
    }
    assert summary["pass1_unchanged"] is True


def test_committed_correction_artifacts_cover_exactly_seven_findings():
    paths = sorted(Path("expert_results").glob(f"ipo_*/audit/{CORRECTION_FILENAME}"))
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in paths]

    assert len(paths) == 6
    assert sum(payload["correction_count"] for payload in payloads) == 7
    assert all(payload["promoted_to_final"] is False for payload in payloads)
    assert all(payload["safety"]["pass1_overwritten"] is False for payload in payloads)

    changes = {
        (payload["case_id"], correction["risk_code"], correction["replacement"]["expected_level"])
        for payload in payloads
        for correction in payload["corrections"]
    }
    assert ("ipo_2022_02145", "cash_runway", "medium") in changes
    assert ("ipo_2022_06922", "customer_concentration", "not_applicable") in changes
    assert ("ipo_2022_09863", "supplier_concentration", "not_applicable") in changes
