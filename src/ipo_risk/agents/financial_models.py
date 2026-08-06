"""Frozen v0.3 internal candidate models for the Financial Agent."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class LossObservation(BaseModel):
    period_end: date
    period_months: int | None = Field(default=None, ge=1, le=12)
    net_result: Decimal
    currency: str
    unit: str
    evidence_ids: list[str] = Field(min_length=1)

class RevenueObservation(BaseModel):
    period_end: date
    period_months: int | None = Field(default=None, ge=1, le=12)
    revenue: Decimal
    currency: str
    unit: str
    evidence_ids: list[str] = Field(min_length=1)


class ConcentrationObservation(BaseModel):
    concentration_type: str
    period_end: date
    largest_counterparty_pct: Decimal | None = Field(default=None, ge=0, le=100)
    top_five_pct: Decimal | None = Field(default=None, ge=0, le=100)
    evidence_ids: list[str] = Field(min_length=1)
