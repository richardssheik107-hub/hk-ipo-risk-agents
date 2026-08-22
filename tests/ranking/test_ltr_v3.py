from __future__ import annotations

from pathlib import Path
import tempfile

import numpy as np
import pytest

try:
    import lightgbm as lgb
except (ImportError, OSError):  # optional/unloadable retrieval-research dependency
    lgb = None

from ipo_risk.ranking.ltr_v3 import (
    CandidateRow, FEATURE_VARIANTS, MISSING_RANK, audit_feature_names, build_feature_rows,
    completion_at, evidence_recall, minmax_scores, mrr_ndcg, rank_scores, sample_training_rows,
)


def _rows() -> list[CandidateRow]:
    rankings = {
        "v1": [(1, None, None), (2, None, None)], "v2": [(2, None, None)], "v21": [],
        "bm25": [(3, 8.0, None), (1, 2.0, None)],
        "table": [(4, 4.0, {"table_block_hit_count": 2, "heuristic_table_signal": 5.0})],
    }
    return build_feature_rows(case_id="ipo_dev", risk_code="cash_runway", fold=1, lane_rankings=rankings,
                              page_structures={3: {"page_text_length": 100, "numeric_density": .3}}, judgements={1: 3})


def test_feature_generation_dedup_missing_and_risk_encoding() -> None:
    rows = _rows()
    assert len(rows) == 4 and len({row.page for row in rows}) == 4
    first = next(row for row in rows if row.page == 1)
    assert first.features["v21_rank"] == MISSING_RANK
    assert first.features["v21_present"] == 0
    assert first.features["risk_cash_runway"] == 1
    assert sum(first.features[f"risk_{risk}"] for risk in ("cash_runway", "continuous_loss")) == 1


def test_score_normalization_is_within_query() -> None:
    assert minmax_scores({1: 2.0, 2: 4.0, 3: None}) == {1: 0.0, 2: 1.0, 3: 0.0}


def test_feature_schema_has_no_gold_leakage() -> None:
    for names in FEATURE_VARIANTS.values():
        audit_feature_names(names)
    try:
        audit_feature_names(["gold_label"])
    except ValueError as exc:
        assert "FEATURE_LEAKAGE" in str(exc)
    else:
        raise AssertionError("leakage audit did not fail")


def test_weak_negative_neighbor_exclusion_and_determinism() -> None:
    base = _rows()[0]
    rows = [base] + [CandidateRow(base.case_id, base.risk_code, page, 1, -1, "UNJUDGED",
                                  base.features, page) for page in range(2, 80)]
    one = sample_training_rows(rows, weak_limit=20)
    two = sample_training_rows(rows, weak_limit=20)
    assert [(r.page, y, s) for r, y, s in one] == [(r.page, y, s) for r, y, s in two]
    weak_pages = {row.page for row, _, source in one if source == "WEAK_UNJUDGED_ZERO"}
    assert 2 not in weak_pages and len(weak_pages) == 20


def test_rank_cap_determinism_and_metrics() -> None:
    rows = _rows()
    scores = np.array([1.0, 1.0, .5, .2])
    first = rank_scores(rows, scores, cap=3)
    assert first == rank_scores(rows, scores, cap=3) and len(first) == 3
    mapped = {(rows[0].case_id, rows[0].risk_code, page): rank for page, rank in first.items()}
    evidence = [{"case_id": "ipo_dev", "risk_code": "cash_runway", "page": 1}]
    assert evidence_recall(evidence, mapped, 5) == 1
    assert completion_at(evidence, mapped, 5) == 1
    mrr, ndcg = mrr_ndcg({("ipo_dev", "cash_runway"): rows}, mapped)
    assert 0 < mrr <= 1 and all(0 <= value <= 1 for value in ndcg.values())


def test_temporary_cleanup() -> None:
    with tempfile.TemporaryDirectory(prefix=".tmp_ltr_unit_", dir=Path.cwd()) as name:
        path = Path(name); assert path.exists()
    assert not path.exists()


@pytest.mark.skipif(lgb is None, reason="lightgbm optional retrieval-research dependency is unavailable")
def test_lightgbm_prediction_is_deterministic() -> None:
    assert lgb is not None
    x = np.asarray([[1.0], [2.0], [3.0], [4.0]], dtype=np.float32)
    y = np.asarray([3, 0, 2, 0], dtype=np.int32)
    params = dict(objective="lambdarank", n_estimators=5, num_leaves=3, min_child_samples=1,
                  random_state=7, n_jobs=1, verbosity=-1, force_col_wise=True)
    one = lgb.LGBMRanker(**params).fit(x, y, group=[2, 2]).predict(x)
    two = lgb.LGBMRanker(**params).fit(x, y, group=[2, 2]).predict(x)
    assert np.array_equal(one, two)


def test_reused_group_cv_has_no_case_or_locked_leakage() -> None:
    split = __import__("json").loads(Path("reports/retriever_v3/split_manifest.json").read_text(encoding="utf-8"))
    cv = __import__("json").loads(Path("reports/retriever_v3/bm25_cv_manifest.json").read_text(encoding="utf-8"))
    folded = [case for cases in cv["folds"].values() for case in cases]
    development = split["historical_development"] + split["new_development"]
    assert sorted(folded) == sorted(development)
    assert len(folded) == len(set(folded)) == 50
    assert not (set(folded) & set(split["locked_validation"]))
