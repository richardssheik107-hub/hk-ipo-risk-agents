"""Frozen v0.3 internal candidate models for the Legal Agent."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ShareholderRightCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    right_type: str
    holder: str = ""
    trigger_or_termination: str = ""
    survives_listing: bool | None = None
    is_effective: bool | None = None
    termination_event: str = ""
    termination_timing: str = ""
    restoration_clause: bool | None = None
    restoration_condition: str = ""
    impact_on_public_shareholders: str = ""
    uncertainty_reason: str = ""
    evidence_ids: list[str] = Field(min_length=1)


class LitigationComplianceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matter_type: str
    subject: str = ""
    counterparty_or_authority: str = ""
    current_status: str
    event_date: date | None = None
    amount: Decimal | None = None
    currency: str = ""
    amount_unit: str = ""
    is_pending: bool | None = None
    is_resolved: bool | None = None
    is_remediated: bool | None = None
    management_materiality: str = ""
    potential_impact: str = ""
    license_impact: str = ""
    materiality_stated: bool | None = None
    uncertainty_reason: str = ""
    evidence_ids: list[str] = Field(min_length=1)
