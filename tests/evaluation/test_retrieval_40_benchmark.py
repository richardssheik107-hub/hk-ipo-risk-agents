"""Contracts for the low-disk 40-case benchmark helpers."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from ipo_risk.evaluation.retrieval_40_annotations import load_annotation, required_gold_pages
from ipo_risk.evaluation.retrieval_40_benchmark import (
    _CaseQueryCache, classify_miss, recall, required_completion,
)
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentChunk


def test_annotation_parser_tolerates_missing_optional_fields(tmp_path: Path) -> None:
    path = tmp_path / "case" / "pass1" / "expert_annotation_v1.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"case_id": "ipo_x", "risks": [{"risk_code": "risk_a"}],
                                "evidence": [{"risk_code": "risk_a", "page": 7, "exact_text": "gold"}]}), encoding="utf-8")
    case = load_annotation(path, repository_root=tmp_path)
    assert case.evidence[0].requirement == "required"
    assert case.evidence[0].source_authority == "unknown"
    assert required_gold_pages(case, "risk_a") == {7}


def test_recall_calculation() -> None:
    assert recall([1, 5, 6, None], 5) == 0.5


def test_miss_type_classification() -> None:
    assert classify_miss(None, parser_or_input_miss=False) == "candidate_miss"
    assert classify_miss(14, parser_or_input_miss=False) == "ranking_miss"
    assert classify_miss(4, parser_or_input_miss=False) == "hit"
    assert classify_miss(4, parser_or_input_miss=True) == "parser_or_input_miss"


def test_multiple_required_evidence_completion() -> None:
    assert required_completion([1, 5])
    assert not required_completion([1, 6])
    assert not required_completion([1, None])


def test_temporary_directory_is_cleaned() -> None:
    parent = Path(tempfile.gettempdir())
    with tempfile.TemporaryDirectory(prefix="retrieval40_test_", dir=parent) as name:
        path = Path(name)
        (path / "annual.zip").write_bytes(b"temporary")
        assert path.exists()
    assert not path.exists()


def test_case_memory_cache_preserves_keyword_ranking() -> None:
    chunks = [DocumentChunk(document_id="d", chunk_id=f"p{page}", page=page,
                            text=text) for page, text in ((1, "收益 10"), (2, "收益 20"), (3, "其他"))]
    expected = KeywordDocumentRetriever().retrieve(chunks, "收益", limit=2)
    actual = _CaseQueryCache().retrieve(chunks, "收益", limit=2)
    assert [(item.page, item.relevance_score) for item in actual] == [
        (item.page, item.relevance_score) for item in expected
    ]
