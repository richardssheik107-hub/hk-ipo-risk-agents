from pathlib import Path
import csv
import tempfile

import pytest

from ipo_risk.retrieval.bm25_v3 import (
    BM25Config, PageBM25Index, bounded_rrf_union, deterministic_group_folds,
    risk_query_phrases, risk_query_tokens, tokenize,
)
from ipo_risk.schemas import DocumentChunk
from scripts.run_retriever_v3_phase_b_bm25 import _load_qrels, _old_complete_misses


def chunk(page: int, text: str) -> DocumentChunk:
    return DocumentChunk(document_id="case", chunk_id=f"p{page}", page=page, text=text)


def test_english_chinese_mixed_number_and_percent_tokenization():
    assert "revenue" in tokenize("Revenue growth 12.5%", "cjk_bigram")
    assert "12.5%" in tokenize("Revenue growth 12.5%", "cjk_bigram")
    assert tokenize("最大客户", "cjk_bigram") == ["最大", "大客", "客户"]
    mixed = tokenize("五大客户 top five 42%", "cjk_bigram_trigram")
    assert {"五大", "客户", "五大客", "top", "42%"} <= set(mixed)


def test_empty_and_short_text_do_not_crash():
    assert tokenize(None, "cjk_unigram") == []
    assert tokenize("", "cjk_bigram") == []
    assert tokenize("客", "cjk_bigram") == ["客"]
    index = PageBM25Index([chunk(1, "x")], BM25Config("x", "cjk_bigram", 1.5, .75))
    assert isinstance(index.search("customer_concentration"), list)


def test_bm25_score_and_page_tie_break_are_deterministic():
    config = BM25Config("x", "cjk_bigram", 1.5, .75)
    chunks = [chunk(2, "最大客户"), chunk(1, "最大客户"), chunk(3, "无关文本")]
    first = PageBM25Index(chunks, config).search("customer_concentration")
    second = PageBM25Index(list(reversed(chunks)), config).search("customer_concentration")
    assert first == second
    assert [item.page for item in first[:2]] == [1, 2]


def test_risk_query_uses_only_frozen_global_sources():
    phrases = risk_query_phrases("customer_concentration")
    assert "top five customers" in phrases
    assert "customer concentration" in phrases
    joined = " ".join(phrases)
    assert "ipo_" not in joined and "case_id" not in joined and "page" not in joined
    assert risk_query_tokens("customer_concentration", "cjk_bigram")


def test_top_k_and_union_dedup_presence_and_cap():
    config = BM25Config("x", "cjk_unigram", 1.2, .75)
    candidates = PageBM25Index([chunk(i, "客户收入") for i in range(1, 121)], config).search("customer_concentration")
    assert len(candidates) == 100
    union = bounded_rrf_union({"v1": [(1, None), (2, None), (2, None)],
                               "bm25": [(2, 4.0), (3, 3.0)]}, limit=100)
    assert len({item.page for item in union}) == len(union) == 3
    page2 = next(item for item in union if item.page == 2)
    assert page2.lane_presence == {"bm25": True, "v1": True}
    assert page2.multi_retriever_hit_count == 2 and page2.bm25_score == 4.0
    with pytest.raises(ValueError):
        bounded_rrf_union({"v1": []}, limit=101)


def test_group_cv_is_deterministic_balanced_and_case_level():
    cases = [f"ipo_{index:02d}" for index in range(50)]
    folds = deterministic_group_folds(cases)
    assert folds == deterministic_group_folds(reversed(cases))
    assert {fold: list(folds.values()).count(fold) for fold in range(1, 6)} == {fold: 10 for fold in range(1, 6)}


def test_temporary_index_has_no_persistent_artifact(tmp_path: Path):
    with tempfile.TemporaryDirectory(prefix=".tmp_bm25_", dir=tmp_path) as name:
        PageBM25Index([chunk(1, "revenue")], BM25Config("x", "cjk_bigram", 1.5, .75))
        root = Path(name)
    assert not root.exists()


def test_locked_qrels_are_rejected(tmp_path: Path):
    path = tmp_path / "gold.csv"
    fields = ("case_id", "risk_code", "page", "evidence_id", "requirement", "gold_label")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        writer.writerow({"case_id": "locked", "risk_code": "cash_runway", "page": 1,
                         "evidence_id": "e", "requirement": "required", "gold_label": 3})
    with pytest.raises(ValueError, match="LOCKED_QRELS_LEAKAGE"):
        _load_qrels(path, {"development"}, {"locked"})


def test_old_complete_miss_recovery_basis_uses_native_presence():
    qrels = [{"case_id": "c", "risk_code": "r", "page": 7, "evidence_id": "e", "key": ("c", "r", "e")},
             {"case_id": "c", "risk_code": "r", "page": 8, "evidence_id": "f", "key": ("c", "r", "f")}]
    old = {"c": {"r": {"v1": [(8, None)], "v2": [], "v21": []}}}
    assert [row["page"] for row in _old_complete_misses(qrels, old)] == [7]
