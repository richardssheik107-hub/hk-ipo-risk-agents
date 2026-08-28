from pathlib import Path

from scripts.evaluate_hybrid_bm25_adapter import evaluate


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_frozen_development_ab_keeps_only_non_regressive_adapter() -> None:
    result = evaluate(
        REPO_ROOT / "reports/retriever_v3/candidate_ltr_features.csv.gz",
        REPO_ROOT / "reports/retriever_v3/split_manifest.json",
    )

    assert result["locked_cases_read"] is False
    assert result["gold_rows"] == 625
    assert result["after"]["recall_at_5"] > result["before"]["recall_at_5"]
    assert result["after"]["recall_at_20"] > result["before"]["recall_at_20"]
    assert result["after"]["mrr"] > result["before"]["mrr"]
    assert result["per_risk"]["cash_runway"]["after"] == result["per_risk"][
        "cash_runway"
    ]["before"]
    assert result["per_risk"]["material_litigation_compliance"]["after"] == result[
        "per_risk"
    ]["material_litigation_compliance"]["before"]
