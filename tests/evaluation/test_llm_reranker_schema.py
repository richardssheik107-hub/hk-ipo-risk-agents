import pytest
from pydantic import ValidationError

from ipo_risk.retrieval.llm_reranker_schemas import LLMCandidateJudgment, LLMCandidateJudgmentBundle


def _judgment(candidate_id: str = "a") -> LLMCandidateJudgment:
    return LLMCandidateJudgment(candidate_id=candidate_id, risk_relevance="high", evidence_specificity="high", source_authority="primary", evidence_role="primary", boilerplate=False, current_status_relevance="direct", supports_risk_assessment=True, confidence=0.8, completeness_facets=["revenue"], reason="direct table")


def test_bundle_rejects_duplicate_candidates():
    with pytest.raises(ValidationError):
        LLMCandidateJudgmentBundle(judgments=[_judgment(), _judgment()])


def test_confidence_is_bounded():
    with pytest.raises(ValidationError):
        _judgment().model_copy(update={"confidence": 1.2}).model_validate(_judgment().model_dump() | {"confidence": 1.2})
