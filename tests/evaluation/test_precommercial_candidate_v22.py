"""Contracts for the research-only precommercial V2.2 candidate experiment."""

from __future__ import annotations

from ipo_risk.retrieval.precommercial_v22 import (
    PRECOMMERCIAL_V22_QUERY_FAMILIES,
    PrecommercialCandidateRetrieverV22,
    frozen_query_phrases,
)
from ipo_risk.schemas import DocumentChunk, Evidence
from scripts.run_precommercial_candidate_v22 import case_split


def _evidence(page: int, text: str = "baseline") -> Evidence:
    return Evidence(document_id="d", chunk_id=f"p{page}", page=page, text=text)


class _Baseline:
    def __init__(self, pages: tuple[int, ...]) -> None:
        self.pages = pages

    def retrieve_for_risk(self, chunks, risk_code, *, limit=20):
        return [_evidence(page) for page in self.pages[:limit]]

    def retrieve(self, chunks, query, limit=3):
        return [_evidence(page) for page in self.pages[:limit]]


class _LexicalBase:
    def retrieve(self, chunks, query, limit=3):
        pages = [chunk.page for chunk in chunks if query in chunk.text]
        return [_evidence(page, query) for page in pages[:limit]]


def _chunks() -> list[DocumentChunk]:
    return [
        DocumentChunk(document_id="d", chunk_id=f"p{page}", page=page, text=text)
        for page, text in ((1, "old"), (2, "old"), (9, "context"),
                           (10, "收益主要來自產品及服務"), (11, "context"))
    ]


def test_v22_preserves_v21_head_and_appends_direct_page_and_neighbours() -> None:
    retriever = PrecommercialCandidateRetrieverV22(
        base=_LexicalBase(), baseline=_Baseline((1, 2)), neighbour_radius=1,
    )
    result = retriever.retrieve_for_risk(_chunks(), "precommercial_product", limit=8)
    assert [item.page for item in result] == [1, 2, 10, 9, 11]
    assert result[2].metadata["candidate_generation_only"] is True
    assert result[2].metadata["baseline_order_preserved"] is True


def test_v22_delegates_other_risks_without_any_change() -> None:
    baseline = _Baseline((2, 1))
    retriever = PrecommercialCandidateRetrieverV22(base=_LexicalBase(), baseline=baseline)
    expected = baseline.retrieve_for_risk(_chunks(), "cash_runway", limit=5)
    actual = retriever.retrieve_for_risk(_chunks(), "cash_runway", limit=5)
    assert [item.page for item in actual] == [item.page for item in expected]


def test_v22_respects_hard_candidate_cap() -> None:
    retriever = PrecommercialCandidateRetrieverV22(
        base=_LexicalBase(), baseline=_Baseline((1, 2)), neighbour_radius=1,
    )
    result = retriever.retrieve_for_risk(_chunks(), "precommercial_product", limit=3)
    assert [item.page for item in result] == [1, 2, 10]


def test_frozen_policy_is_small_and_contains_no_case_specific_tokens() -> None:
    phrases = frozen_query_phrases()
    assert len(PRECOMMERCIAL_V22_QUERY_FAMILIES) == 3
    assert len(phrases) == 10
    assert all("ipo_" not in phrase and not any(char.isdigit() for char in phrase) for phrase in phrases)
    assert len(set(phrases)) == len(phrases)


def test_case_split_reuses_published_case_level_partition() -> None:
    cases = [
        "ipo_2020_00368", "ipo_2020_06618", "ipo_2020_03347",
        "ipo_2020_06063", "ipo_2020_06688", "ipo_2020_09633",
    ]
    split = case_split(cases)
    assert split["ipo_2020_00368"] == "historical_development"
    assert set(split) == set(cases)
    assert all(value in {"historical_development", "development", "locked_validation"} for value in split.values())
