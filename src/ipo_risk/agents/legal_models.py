"""Frozen v0.3 internal candidate models for the Legal Agent."""

from pydantic import BaseModel, Field


class ShareholderRightCandidate(BaseModel):
    right_type: str
    holder: str = ""
    trigger_or_termination: str = ""
    survives_listing: bool | None = None
    evidence_ids: list[str] = Field(min_length=1)

class LitigationComplianceCandidate(BaseModel):
    matter_type: str
    counterparty_or_authority: str = ""
    current_status: str
    potential_impact: str = ""
    materiality_stated: bool | None = None
    evidence_ids: list[str] = Field(min_length=1)
