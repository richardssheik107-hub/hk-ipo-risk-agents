import pytest

from ipo_risk.retrieval.llm_reranker import rerank
from ipo_risk.retrieval.llm_reranker_schemas import CandidateEvidenceView, LLMCandidateJudgment, LLMCandidateJudgmentBundle


def _candidate(cid: str, page: int):
    return CandidateEvidenceView(candidate_id=cid, document_id="d", page=page, chunk_id=cid, section="unknown", v1_rank=page, origin=["v1"], excerpt="text", excerpt_start=0, excerpt_end=4, truncated=False)


def _j(cid: str, relevance: str, boilerplate=False):
    return LLMCandidateJudgment(candidate_id=cid, risk_relevance=relevance, evidence_specificity="high", source_authority="primary", evidence_role="boilerplate" if boilerplate else "primary", boilerplate=boilerplate, current_status_relevance="direct", supports_risk_assessment=True, confidence=.5, completeness_facets=["revenue"], reason="ok")


def test_semantic_tier_precedes_stage1_rank():
    pool = [_candidate("broad", 1), _candidate("direct", 2)]
    bundle = LLMCandidateJudgmentBundle(judgments=[_j("broad", "high", True), _j("direct", "high")])
    assert [x.candidate_id for x in rerank(pool, bundle, "revenue_growth")] == ["direct", "broad"]


def test_missing_candidate_fails_closed():
    with pytest.raises(ValueError, match="coverage"):
        rerank([_candidate("a", 1)], LLMCandidateJudgmentBundle(judgments=[]), "revenue_growth")
