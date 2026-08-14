from __future__ import annotations

from pathlib import Path

from ipo_risk.retrieval.domain_aware_v21 import (
    RRF_K,
    DomainAwareRetrieverV21,
    QuerySpec,
    Specificity,
    _Candidate,
    _Hit,
    policy_hashes,
    query_specs,
)
from ipo_risk.schemas import DocumentChunk


def chunk(page: int, text: str = "financial evidence") -> DocumentChunk:
    return DocumentChunk(document_id="case", chunk_id=f"case:page:{page}", page=page, text=text)


def hit(query_id: str, family: str, rank: int, *, round_number: int = 1, specificity=Specificity.HIGH) -> _Hit:
    return _Hit(QuerySpec(query_id, query_id, family, specificity, round_number), rank, 1.0, ())


def test_family_capped_rrf_counts_each_family_once() -> None:
    candidate = _Candidate(chunk(1), hits=[hit("a", "F1", 1), hit("b", "F1", 2), hit("c", "F2", 3)])
    assert candidate.family_rrf == 1 / (RRF_K + 1) + 1 / (RRF_K + 3)


def test_family_multiplicity_cannot_outvote_two_distinct_families() -> None:
    repeated = _Candidate(chunk(1), hits=[hit(str(i), "ONE", i) for i in range(1, 8)])
    diverse = _Candidate(chunk(2), hits=[hit("a", "A", 5), hit("b", "B", 5)])
    assert diverse.family_rrf > repeated.family_rrf


def test_stable_tie_break_uses_page_then_chunk_id() -> None:
    first = _Candidate(chunk(3), hits=[hit("a", "A", 1)])
    second = _Candidate(chunk(2), hits=[hit("a", "A", 1)])
    ranked = DomainAwareRetrieverV21()._rank({"x": first, "y": second}, "cash_runway", "v21")
    assert [item.chunk.page for item in ranked] == [2, 3]


def test_neighbor_and_round2_tail_guards() -> None:
    neighbor = _Candidate(chunk(1), neighbor_seed_pages={2})
    round2 = _Candidate(chunk(2), hits=[hit("r2", "F", 1, round_number=2, specificity=Specificity.MEDIUM)])
    direct = _Candidate(chunk(3), hits=[hit("r1", "F", 2)])
    ranked = DomainAwareRetrieverV21()._rank({"n": neighbor, "r": round2, "d": direct}, "cash_runway", "v21")
    assert ranked[0] is direct
    assert neighbor not in ranked[:1]
    assert round2 not in ranked[:1]


def test_legal_boilerplate_is_demoted_unless_transaction_context_exists() -> None:
    retriever = DomainAwareRetrieverV21()
    assert retriever._legal_boilerplate("Articles of association and Cayman Companies Law")
    assert not retriever._legal_boilerplate("Articles of association; investor agreement termination and waiver")


def test_query_specs_do_not_expand_v2_query_text() -> None:
    from ipo_risk.retrieval.domain_aware_v2 import V2_QUERY_PLANS

    for risk_code, plan in V2_QUERY_PLANS.items():
        first, second = query_specs(risk_code)
        assert tuple(item.text for item in first) == plan.first_round
        assert tuple(item.text for item in second) == plan.second_round


def test_policy_hashes_are_stable_and_complete() -> None:
    assert set(policy_hashes()) == {
        "query_plan_sha256", "query_family_mapping_sha256",
        "specificity_policy_sha256", "ranking_policy_sha256",
    }
    assert policy_hashes() == policy_hashes()


def test_production_module_has_no_case_specific_identifiers() -> None:
    source = Path("src/ipo_risk/retrieval/domain_aware_v21.py").read_text(encoding="utf-8").lower()
    for forbidden in ("00368", "01167", "01408", "01961", "01942", "02057", "02135", "02263", "02599", "00013"):
        assert forbidden not in source

