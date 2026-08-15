"""Research-only structured contracts for the Phase 0.6C reranker."""

from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskRelevance(StrEnum):
    HIGH = "high"; MEDIUM = "medium"; LOW = "low"; IRRELEVANT = "irrelevant"


class EvidenceSpecificity(StrEnum):
    HIGH = "high"; MEDIUM = "medium"; BROAD = "broad"


class SourceAuthority(StrEnum):
    PRIMARY = "primary"; STRONG_SUPPORTING = "strong_supporting"; SUPPORTING = "supporting"; WEAK = "weak"; UNKNOWN = "unknown"


class EvidenceRole(StrEnum):
    PRIMARY = "primary"; SUPPORTING = "supporting"; CONTEXT = "context"; BOILERPLATE = "boilerplate"; IRRELEVANT = "irrelevant"


class CurrentStatusRelevance(StrEnum):
    DIRECT = "direct"; INDIRECT = "indirect"; NONE = "none"; NOT_APPLICABLE = "not_applicable"


class CandidateEvidenceView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    document_id: str
    page: int = Field(ge=1)
    chunk_id: str
    section: str
    v1_rank: int | None = Field(default=None, ge=1)
    v2_rank: int | None = Field(default=None, ge=1)
    v1_score: float | None = None
    v2_score: float | None = None
    origin: list[str]
    matched_query_terms: list[str] = Field(default_factory=list)
    matched_query_families: list[str] = Field(default_factory=list)
    excerpt: str = Field(min_length=1, max_length=2400)
    excerpt_start: int = Field(ge=0)
    excerpt_end: int = Field(ge=1)
    truncated: bool


class LLMCandidateJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    risk_relevance: RiskRelevance
    evidence_specificity: EvidenceSpecificity
    source_authority: SourceAuthority
    evidence_role: EvidenceRole
    boilerplate: bool
    current_status_relevance: CurrentStatusRelevance
    supports_risk_assessment: bool
    confidence: float = Field(ge=0, le=1)
    completeness_facets: list[str] = Field(default_factory=list)
    reason: str = Field(max_length=240)


class LLMCandidateJudgmentBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    judgments: list[LLMCandidateJudgment]

    @model_validator(mode="after")
    def unique_candidate_ids(self) -> "LLMCandidateJudgmentBundle":
        ids = [item.candidate_id for item in self.judgments]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate candidate_id in LLM judgment bundle")
        return self
