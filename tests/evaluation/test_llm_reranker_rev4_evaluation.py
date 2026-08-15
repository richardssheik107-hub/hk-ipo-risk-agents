from ipo_risk.evaluation.llm_reranker_rev4 import (
    GoldEvidenceRecord,
    evaluate_ranks,
    promotion_matrix,
    reliability_analysis,
    runtime_case_aliases,
)


def _record(index: int, *, page: int, requirement: str = "required") -> GoldEvidenceRecord:
    return GoldEvidenceRecord(
        case_id="ipo_2021_00013",
        runtime_case_id="ipo_2020_00013",
        stock_code="0013.HK",
        risk_code="cash_runway",
        evidence_index=index,
        page=page,
        requirement=requirement,
        evidence_role="primary",
        source_authority="audited_financial_statement",
    )


def test_runtime_alias_preserves_canonical_case_identity() -> None:
    aliases = runtime_case_aliases(
        ["ipo_2020_00368", "ipo_2021_00013"],
        ["ipo_2020_00368", "ipo_2020_00013"],
    )
    assert aliases == {
        "ipo_2020_00368": "ipo_2020_00368",
        "ipo_2020_00013": "ipo_2021_00013",
    }


def test_historical_completion_and_mrr_definitions_are_preserved() -> None:
    rows = [_record(0, page=10), _record(1, page=11)]
    ranks = {rows[0].key: 2, rows[1].key: None}
    metrics = evaluate_ranks(rows, ranks)
    assert metrics["required_recall_at"][3] == 0.5
    assert metrics["required_completion_at"][20] == 0.0
    assert metrics["mrr"] == 0.25


def test_promotion_matrix_distinguishes_coverage_and_head_changes() -> None:
    rows = [_record(0, page=10), _record(1, page=11), _record(2, page=12)]
    variants = {
        "v1": {row.key: None for row in rows},
        "v2": {row.key: None for row in rows},
        "v21": {row.key: None for row in rows},
        "stage1_union": {rows[0].key: None, rows[1].key: 8, rows[2].key: 2},
        "llm_rev4": {rows[0].key: None, rows[1].key: 3, rows[2].key: 7},
    }
    statuses = {rows[0].task: "completed"}
    result = promotion_matrix(rows, variants, statuses)
    assert [row["classification"] for row in result] == [
        "NOT_IN_STAGE1",
        "RECOVERED_TO_TOP3",
        "DEMOTED_FROM_TOP3",
    ]


def test_reliability_breakdown_keeps_fallback_as_official_cost() -> None:
    statuses = {
        ("case_a", "cash_runway"): "completed",
        ("case_a", "redemption_rights"): "failed",
        ("case_a", "precommercial_product"): "failed",
    }
    result = reliability_analysis(statuses)
    assert result["overall"] == {
        "task_count": 3,
        "completed": 1,
        "fallback": 2,
        "fallback_rate": 2 / 3,
    }
    assert result["by_domain"]["legal"]["fallback"] == 1
