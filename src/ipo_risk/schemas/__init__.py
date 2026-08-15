"""Stable cross-module data contracts."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION,
    MarketBasePriceSource,
    MarketDailyBar,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketExchange,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketLabelMissingReason,
    MarketLabelPolicy,
    MarketOutcomeLabel,
    MarketSecurityEligibility,
    MarketSecurityEligibilityDecision,
    MarketSecurityEligibilityReason,
    MarketSecurityType,
    MarketValidationIssue,
    MarketValidationResult,
    MarketValidationSeverity,
)


def now() -> datetime:
    return datetime.now(timezone.utc)


class RiskCategory(StrEnum):
    FINANCIAL = "financial"; LEGAL = "legal"; BUSINESS = "business"; MARKET = "market"


class RiskLevel(StrEnum):
    LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"


class VerificationStatus(StrEnum):
    PENDING = "pending"; VERIFIED = "verified"; REJECTED = "rejected"; NEEDS_REVIEW = "needs_review"


class TaskStatus(StrEnum):
    PENDING = "pending"; RUNNING = "running"; COMPLETED = "completed"; PARTIAL = "partial"; FAILED = "failed"


class LogStatus(StrEnum):
    STARTED = "started"; SUCCESS = "success"; FAILED = "failed"; SKIPPED = "skipped"


class EvidenceSourceType(StrEnum):
    PROSPECTUS = "prospectus"; MARKET_DATA = "market_data"; IPO_DATA = "ipo_data"; CALCULATION = "calculation"


class DiagnosticCode(StrEnum):
    RISK_GENERATED = "risk_generated"
    NOT_APPLICABLE = "not_applicable"
    EVIDENCE_NOT_FOUND = "evidence_not_found"
    EXTRACTION_FAILED = "extraction_failed"
    CONFLICTING_VALUES = "conflicting_values"
    UNSUPPORTED_LAYOUT = "unsupported_layout"
    NEEDS_REVIEW = "needs_review"
    COMPONENT_FAILURE = "component_failure"


class DocumentChunk(BaseModel):
    document_id: str
    chunk_id: str
    page: int = Field(ge=1)
    section: str = ""
    text: str = Field(min_length=1)
    block_type: str = "text"
    bbox: tuple[float, float, float, float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str | None = None
    chunk_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    section: str = ""
    text: str = Field(min_length=1)
    bbox: tuple[float, float, float, float] | None = None
    source_type: EvidenceSourceType = EvidenceSourceType.PROSPECTUS
    relevance_score: float = Field(default=1.0, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Calculation(BaseModel):
    skill_name: str
    skill_version: str = "1.0"
    inputs: dict[str, Any] = Field(default_factory=dict)
    formula: str
    result: float | int | str | None = None
    unit: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    success: bool = True
    error: str | None = None


class RiskItem(BaseModel):
    risk_id: str = Field(default_factory=lambda: str(uuid4()))
    risk_code: str
    category: RiskCategory
    risk_type: str
    level: RiskLevel
    score: float = Field(ge=0, le=100)
    conclusion: str
    evidence: list[Evidence] = Field(default_factory=list)
    calculation: Calculation | None = None
    agent_name: str
    confidence: float = Field(default=0.5, ge=0, le=1)
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verification_notes: str = ""
    created_at: datetime = Field(default_factory=now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisError(BaseModel):
    stage: str
    component: str
    code: str
    message: str
    recoverable: bool = True
    context: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=now)


class ComponentDiagnostic(BaseModel):
    """Structured explanation for a component decision that emitted no risk."""

    risk_code: str
    code: DiagnosticCode
    message: str
    recoverable: bool = True
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMCallMetadata(BaseModel):
    provider_name: str
    model_name: str
    prompt_version: str
    latency_ms: int = Field(ge=0)
    token_usage: dict[str, int] = Field(default_factory=dict)
    request_id: str
    raw_response_hash: str


class AgentLog(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    step: int
    agent_name: str
    action: str
    tool_name: str = ""
    status: LogStatus = LogStatus.STARTED
    input_summary: str = ""
    output_summary: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    error: AnalysisError | None = None
    started_at: datetime = Field(default_factory=now)
    finished_at: datetime | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskFactor(BaseModel):
    feature_name: str
    feature_value: Any
    contribution: float
    direction: str
    explanation: str
    source: str


class PredictionResult(BaseModel):
    model_name: str
    model_version: str = "rule_v1"
    target: str = "five_day_significant_decline_risk"
    risk_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    probabilities: dict[str, float] = Field(default_factory=dict)
    top_factors: list[RiskFactor] = Field(default_factory=list)
    explanation: str = ""
    feature_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketSnapshot(BaseModel):
    observation_date: date | None = None
    hsi_return_5d: float | None = None
    hsi_return_20d: float | None = None
    industry_return_5d: float | None = None
    industry_return_20d: float | None = None
    recent_ipo_break_rate: float | None = None
    recent_ipo_return_5d: float | None = None
    market_turnover: float | None = None
    market_volatility: float | None = None
    sentiment_score: float | None = None
    source: str = "mock"
    metadata: dict[str, Any] = Field(default_factory=dict)


class IPOProfile(BaseModel):
    company_name: str
    stock_code: str = ""
    listing_date: date | None = None
    industry: str = ""
    issue_price: float | None = None
    issue_size: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentParseRequest(BaseModel):
    document_id: str
    prospectus_path: str
    options: dict[str, Any] = Field(default_factory=dict)


class IPOAnalysisRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    company_name: str
    stock_code: str = ""
    listing_date: date | None = None
    prospectus_path: str = "mock://prospectus"
    workflow_version: str = "mvp_v1"
    parser_name: str = "mock"
    predictor_name: str = "rule_based"
    market_snapshot: MarketSnapshot | None = None
    use_mock: bool = True
    options: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now)


class ReportSection(BaseModel):
    section_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    summary: str
    risks: list[RiskItem] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    order: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportContext(BaseModel):
    analysis_id: str
    profile: IPOProfile
    verified_risks: list[RiskItem] = Field(default_factory=list)
    pending_risks: list[RiskItem] = Field(default_factory=list)
    rejected_risks: list[RiskItem] = Field(default_factory=list)
    prediction: PredictionResult | None = None
    log_summary: str = ""
    options: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    verified_risks: list[RiskItem] = Field(default_factory=list)
    pending_risks: list[RiskItem] = Field(default_factory=list)
    rejected_risks: list[RiskItem] = Field(default_factory=list)


class DuplicateRiskGroup(BaseModel):
    risk_code: str
    source_risk_ids: list[str] = Field(default_factory=list)
    kept_risk_id: str | None = None
    reason: str = ""


class RiskConflict(BaseModel):
    risk_code: str
    risk_ids: list[str] = Field(default_factory=list)
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


class CompositeFinding(BaseModel):
    finding_code: str
    related_risk_ids: list[str] = Field(default_factory=list)
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SupervisionResult(BaseModel):
    verified_risks: list[RiskItem] = Field(default_factory=list)
    summary: str = ""
    duplicate_groups: list[DuplicateRiskGroup] = Field(default_factory=list)
    conflicts: list[RiskConflict] = Field(default_factory=list)
    composite_findings: list[CompositeFinding] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IPOAnalysisResult(BaseModel):
    analysis_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    company_name: str
    stock_code: str = ""
    workflow_version: str
    schema_version: str = "1.0"
    verified_risks: list[RiskItem] = Field(default_factory=list)
    pending_risks: list[RiskItem] = Field(default_factory=list)
    rejected_risks: list[RiskItem] = Field(default_factory=list)
    prediction: PredictionResult | None = None
    agent_logs: list[AgentLog] = Field(default_factory=list)
    report_sections: list[ReportSection] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    errors: list[AnalysisError] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=now)
    finished_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillResult(BaseModel):
    skill_name: str
    skill_version: str = "1.0"
    success: bool
    value: Any = None
    evidence_ids: list[str] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
