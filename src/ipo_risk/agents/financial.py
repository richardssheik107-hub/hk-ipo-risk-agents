"""Deterministic financial agent for the v0.2 cash-runway vertical slice."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from ipo_risk.domain.cash_runway import CashRunwayBuildStatus, CashRunwayRiskBuilder
from ipo_risk.extraction import ExtractionStatus, FinancialEvidenceExtractor
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentChunk, IPOProfile, MarketSnapshot, RiskItem


class CashRunwayAgentStatus(StrEnum):
    BUILT = "built"
    RETRIEVER_NO_RESULT = "retriever_no_result"
    EXTRACTION_NEEDS_REVIEW = "extraction_needs_review"
    BUILDER_NEEDS_REVIEW = "builder_needs_review"
    NOT_APPLICABLE = "not_applicable"
    COMPONENT_FAILURE = "component_failure"


class CashRunwayAgentDiagnostics(BaseModel):
    status: CashRunwayAgentStatus
    cash_evidence_count: int = 0
    operating_cash_flow_evidence_count: int = 0
    extraction_status: dict[str, str] = Field(default_factory=dict)
    builder_status: str | None = None
    issues: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    pages: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CashRunwayFinancialAgent:
    """Retrieve, extract, and build one pending cash-runway risk."""

    name = "financial"

    def __init__(
        self,
        retriever=None,
        extractor: FinancialEvidenceExtractor | None = None,
        risk_builder: CashRunwayRiskBuilder | None = None,
    ) -> None:
        self.retriever = retriever or KeywordDocumentRetriever()
        self.extractor = extractor or FinancialEvidenceExtractor()
        self.risk_builder = risk_builder or CashRunwayRiskBuilder()
        self.last_diagnostics = CashRunwayAgentDiagnostics(
            status=CashRunwayAgentStatus.RETRIEVER_NO_RESULT
        )

    def analyze(
        self,
        profile: IPOProfile,
        chunks: list[DocumentChunk],
        market: MarketSnapshot | None = None,
    ) -> list[RiskItem]:
        """Return a pending cash-runway risk only when the full chain succeeds."""

        try:
            cash_evidence = self.retriever.retrieve(
                chunks, "现金流量表期末现金及现金等价物", limit=5
            )
            cash_flow_evidence = self.retriever.retrieve(
                chunks, "经营活动现金流", limit=5
            )
        except Exception as exc:
            self.last_diagnostics = CashRunwayAgentDiagnostics(
                status=CashRunwayAgentStatus.COMPONENT_FAILURE,
                issues=["retriever_failure"],
                metadata={"component": "retriever", "error_type": type(exc).__name__},
            )
            raise

        counts = {
            "cash_evidence_count": len(cash_evidence),
            "operating_cash_flow_evidence_count": len(cash_flow_evidence),
        }
        if not cash_evidence or not cash_flow_evidence:
            self.last_diagnostics = CashRunwayAgentDiagnostics(
                status=CashRunwayAgentStatus.RETRIEVER_NO_RESULT,
                issues=[
                    name
                    for name, values in (
                        ("cash_evidence_not_found", cash_evidence),
                        ("operating_cash_flow_evidence_not_found", cash_flow_evidence),
                    )
                    if not values
                ],
                **counts,
            )
            return []

        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        try:
            extraction = self.extractor.extract(
                cash_evidence, cash_flow_evidence, chunks_by_id
            )
        except Exception as exc:
            self.last_diagnostics = CashRunwayAgentDiagnostics(
                status=CashRunwayAgentStatus.COMPONENT_FAILURE,
                issues=["extractor_failure"],
                metadata={"component": "extractor", "error_type": type(exc).__name__},
                **counts,
            )
            raise
        extraction_status = {
            "cash_and_cash_equivalents": extraction.cash_and_cash_equivalents.status.value,
            "operating_cash_flow": extraction.operating_cash_flow.status.value,
        }
        extraction_issues = list(
            dict.fromkeys(
                [
                    *extraction.cash_and_cash_equivalents.issues,
                    *extraction.operating_cash_flow.issues,
                ]
            )
        )
        if any(
            metric.status != ExtractionStatus.EXTRACTED
            for metric in (
                extraction.cash_and_cash_equivalents,
                extraction.operating_cash_flow,
            )
        ):
            self.last_diagnostics = CashRunwayAgentDiagnostics(
                status=CashRunwayAgentStatus.EXTRACTION_NEEDS_REVIEW,
                extraction_status=extraction_status,
                issues=extraction_issues,
                **counts,
            )
            return []

        available_evidence = {
            item.evidence_id: item for item in [*cash_evidence, *cash_flow_evidence]
        }
        selected = [
            extraction.cash_and_cash_equivalents,
            extraction.operating_cash_flow,
        ]
        evidence_ids = [item.evidence_id for item in selected if item.evidence_id]
        pages = [item.page for item in selected if item.page is not None]
        try:
            built = self.risk_builder.build(extraction, available_evidence)
        except Exception as exc:
            self.last_diagnostics = CashRunwayAgentDiagnostics(
                status=CashRunwayAgentStatus.COMPONENT_FAILURE,
                extraction_status=extraction_status,
                issues=["risk_builder_failure"],
                evidence_ids=evidence_ids,
                pages=pages,
                metadata={
                    "component": "risk_builder",
                    "error_type": type(exc).__name__,
                },
                **counts,
            )
            raise
        if built.status == CashRunwayBuildStatus.NOT_APPLICABLE:
            self.last_diagnostics = CashRunwayAgentDiagnostics(
                status=CashRunwayAgentStatus.NOT_APPLICABLE,
                extraction_status=extraction_status,
                builder_status=built.status.value,
                issues=built.issues,
                evidence_ids=evidence_ids,
                pages=pages,
                **counts,
            )
            return []
        if built.status != CashRunwayBuildStatus.BUILT or built.risk_item is None:
            self.last_diagnostics = CashRunwayAgentDiagnostics(
                status=CashRunwayAgentStatus.BUILDER_NEEDS_REVIEW,
                extraction_status=extraction_status,
                builder_status=built.status.value,
                issues=built.issues,
                evidence_ids=evidence_ids,
                pages=pages,
                **counts,
            )
            return []

        self.last_diagnostics = CashRunwayAgentDiagnostics(
            status=CashRunwayAgentStatus.BUILT,
            extraction_status=extraction_status,
            builder_status=built.status.value,
            evidence_ids=evidence_ids,
            pages=pages,
            **counts,
        )
        return [built.risk_item]
