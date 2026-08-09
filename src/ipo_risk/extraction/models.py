"""Internal contracts for deterministic financial value extraction."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ExtractionStatus(StrEnum):
    """Outcome of extracting one financial metric."""

    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"
    NOT_FOUND = "not_found"


class FinancialMetricValue(BaseModel):
    """One normalized financial value with complete source traceability."""

    metric_name: str
    raw_label: str = ""
    raw_value: str = ""
    normalized_value: Decimal | None = None
    currency: str | None = None
    unit: str | None = None
    period_end: date | None = None
    period_months: int | None = Field(default=None, ge=1, le=12)
    evidence_id: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    status: ExtractionStatus = ExtractionStatus.NOT_FOUND
    issues: list[str] = Field(default_factory=list)
    context_chunk_ids: list[str] = Field(default_factory=list)
    context_pages: list[int] = Field(default_factory=list)
    extraction_method: str = "not_applicable"
    metadata: dict[str, Any] = Field(default_factory=dict)


class FinancialExtractionResult(BaseModel):
    """A3 output for the two metrics required by the real vertical slice."""

    cash_and_cash_equivalents: FinancialMetricValue
    operating_cash_flow: FinancialMetricValue


class FinancialPeriodFact(BaseModel):
    """One extracted net-result or revenue observation for a reporting period."""

    metric_name: Literal["net_result", "revenue"]
    period_end: date | None = None
    period_months: int | None = Field(default=None, ge=1, le=12)
    normalized_value: Decimal | None = None
    currency: str | None = None
    unit: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    document_id: str | None = None
    chunk_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    raw_label: str = ""
    raw_value: str = ""
    status: ExtractionStatus = ExtractionStatus.NOT_FOUND
    issues: list[str] = Field(default_factory=list)
    context_chunk_ids: list[str] = Field(default_factory=list)
    context_pages: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FinancialPeriodSeriesResult(BaseModel):
    """Typed extraction result for a sequence of comparable financial periods."""

    metric_name: Literal["net_result", "revenue"]
    observations: list[FinancialPeriodFact] = Field(default_factory=list)
    status: ExtractionStatus = ExtractionStatus.NOT_FOUND
    issues: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConcentrationFact(BaseModel):
    """One customer or supplier concentration observation with traceability."""

    concentration_type: Literal["customer", "supplier"]
    period_end: date | None = None
    period_months: int | None = Field(default=None, ge=1, le=12)
    largest_counterparty_pct: Decimal | None = None
    top_five_pct: Decimal | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    document_id: str | None = None
    chunk_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    status: ExtractionStatus = ExtractionStatus.NOT_FOUND
    issues: list[str] = Field(default_factory=list)
    context_chunk_ids: list[str] = Field(default_factory=list)
    context_pages: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class V03FinancialExtractionResult(BaseModel):
    """Internal v0.3 extraction output consumed by the later Financial Agent."""

    net_results: FinancialPeriodSeriesResult
    revenues: FinancialPeriodSeriesResult
    customer_concentration: ConcentrationFact
    supplier_concentration: ConcentrationFact
