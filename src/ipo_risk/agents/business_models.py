"""Frozen v0.3 internal candidate models for the Business Agent."""

from pydantic import BaseModel, Field


class CommercializationCandidate(BaseModel):
    product_name: str
    development_stage: str
    has_product_revenue: bool | None = None
    commercialization_dependency: str = ""
    evidence_ids: list[str] = Field(min_length=1)

class CoreProductCandidate(BaseModel):
    product_name: str
    is_core_product: bool
    approval_status: str = ""
    launch_status: str = ""
    evidence_ids: list[str] = Field(min_length=1)
