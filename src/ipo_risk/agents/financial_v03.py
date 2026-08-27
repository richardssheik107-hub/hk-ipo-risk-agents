"""Independent v0.3 Financial Agent with deterministic failure isolation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from ipo_risk.agents.financial import (
    CashRunwayAgentDiagnostics,
    CashRunwayAgentStatus,
    CashRunwayFinancialAgent,
)
from ipo_risk.agents.financial_builders import V03FinancialRiskBuilder, _RiskDecision
from ipo_risk.agents.financial_policy import V03FinancialPolicy, load_v03_financial_policy
from ipo_risk.extraction import (
    ConcentrationFact,
    ExtractionStatus,
    FinancialPeriodSeriesResult,
    V03FinancialFactExtractor,
)
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import (
    ComponentDiagnostic,
    DiagnosticCode,
    DocumentChunk,
    Evidence,
    IPOProfile,
    MarketSnapshot,
    RiskItem,
    VerificationStatus,
)


FINANCIAL_EVIDENCE_QUERIES: Mapping[str, tuple[str, ...]] = {
    "continuous_loss": (
        "年內虧損",
        "年内亏损",
        "期內虧損",
        "net loss",
        "loss for the year",
        "年內溢利",
        "年╱期內溢利",
        "net profit",
        "profit for the year",
    ),
    "revenue_growth": ("收入", "收益", "營業收入", "营业收入", "revenue", "turnover"),
    "customer_concentration": (
        "最大客戶",
        "最大客户",
        "五大客戶",
        "五大客户",
        "largest customer",
        "top five customers",
    ),
    "supplier_concentration": (
        "最大供應商",
        "最大供应商",
        "五大供應商",
        "五大供应商",
        "largest supplier",
        "top five suppliers",
    ),
}

_V03_RISK_ORDER = (
    "cash_runway",
    "continuous_loss",
    "revenue_growth",
    "customer_concentration",
    "supplier_concentration",
)


@dataclass(frozen=True, slots=True)
class _RetrievalResult:
    evidence: list[Evidence]
    error_types: list[str]


class V03FinancialAgent:
    """Analyze five owned financial risks without Workflow registration."""

    name = "financial"

    def __init__(
        self,
        *,
        retriever: Any | None = None,
        extractor: V03FinancialFactExtractor | None = None,
        cash_runway_agent: Any | None = None,
        policy: V03FinancialPolicy | None = None,
        risk_builder: V03FinancialRiskBuilder | None = None,
    ) -> None:
        self.retriever = retriever or KeywordDocumentRetriever()
        self.extractor = extractor or V03FinancialFactExtractor()
        self.policy = policy or load_v03_financial_policy()
        # Share this agent's extractor with the cash sub-agent so the structured
        # table path (when configured) also covers the cash-flow statement. With
        # the default regex extractor this is behaviourally identical to the base
        # FinancialEvidenceExtractor (no overrides), and the frozen 2410.HK slice
        # uses the standalone cash_runway agent, not this one.
        self.cash_runway_agent = cash_runway_agent or CashRunwayFinancialAgent(
            retriever=self.retriever, extractor=self.extractor
        )
        self.risk_builder = risk_builder or V03FinancialRiskBuilder(self.policy)
        self.last_diagnostics: list[ComponentDiagnostic] = []

    def analyze(
        self,
        profile: IPOProfile,
        chunks: list[DocumentChunk],
        market: MarketSnapshot | None = None,
    ) -> list[RiskItem]:
        """Return stable pending risks while isolating each financial component."""

        self.last_diagnostics = []
        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        risks: list[RiskItem] = []

        cash_risk, cash_diagnostic = self._analyze_cash_runway(profile, chunks, market)
        if cash_risk is not None:
            risks.append(cash_risk)
        self.last_diagnostics.append(cash_diagnostic)

        for risk_code in _V03_RISK_ORDER[1:]:
            risk, diagnostic = self._analyze_v03_risk(
                risk_code, chunks, chunks_by_id
            )
            if risk is not None:
                risks.append(risk)
            self.last_diagnostics.append(diagnostic)

        order = {risk_code: index for index, risk_code in enumerate(_V03_RISK_ORDER)}
        risks.sort(key=lambda item: (order[item.risk_code], item.risk_id))
        self.last_diagnostics.sort(key=lambda item: order[item.risk_code])
        return risks

    def _analyze_cash_runway(
        self,
        profile: IPOProfile,
        chunks: list[DocumentChunk],
        market: MarketSnapshot | None,
    ) -> tuple[RiskItem | None, ComponentDiagnostic]:
        try:
            risks = self.cash_runway_agent.analyze(profile, chunks, market)
        except Exception as exc:
            return None, self._component_failure(
                "cash_runway", "cash_runway_agent", exc
            )
        diagnostics = getattr(self.cash_runway_agent, "last_diagnostics", None)
        if risks:
            risk = next((item for item in risks if item.risk_code == "cash_runway"), None)
            if risk is None or risk.calculation is None or not risk.evidence:
                return None, self._diagnostic(
                    "cash_runway",
                    DiagnosticCode.NEEDS_REVIEW,
                    "Cash-runway agent returned an incomplete risk candidate.",
                    metadata={"issue": "cash_runway_candidate_incomplete"},
                )
            try:
                exact_runway = Decimal(str(risk.metadata.get("runway_months_exact")))
            except (InvalidOperation, ValueError):
                exact_runway = None
            expected_level = (
                self.policy.cash_runway_level(exact_runway)
                if exact_runway is not None and exact_runway.is_finite()
                else None
            )
            risk_evidence_ids = [item.evidence_id for item in risk.evidence]
            evidence_id_set = set(risk_evidence_ids)
            if (
                expected_level is None
                or risk.level != expected_level
                or not risk.calculation.success
                or not set(risk.calculation.evidence_ids) <= evidence_id_set
            ):
                return None, self._diagnostic(
                    "cash_runway",
                    DiagnosticCode.NEEDS_REVIEW,
                    "Cash-runway candidate does not match the frozen v0.3 rule contract.",
                    evidence_ids=risk_evidence_ids,
                    metadata={"issue": "cash_runway_policy_or_traceability_mismatch"},
                )
            risk = risk.model_copy(
                update={
                    "verification_status": VerificationStatus.PENDING,
                    "metadata": {
                        **risk.metadata,
                        "rule_version": self.policy.version,
                    },
                }
            )
            return risk, self._diagnostic(
                "cash_runway",
                DiagnosticCode.RISK_GENERATED,
                "A pending cash-runway risk was generated for Verifier review.",
                evidence_ids=[item.evidence_id for item in risk.evidence],
                metadata={
                    "rule_version": self.policy.version,
                    "legacy_policy_version": risk.metadata.get("policy_version"),
                },
            )
        return None, self._cash_diagnostic(diagnostics)

    def _cash_diagnostic(
        self, diagnostics: CashRunwayAgentDiagnostics | Any
    ) -> ComponentDiagnostic:
        if not isinstance(diagnostics, CashRunwayAgentDiagnostics):
            return self._diagnostic(
                "cash_runway",
                DiagnosticCode.NEEDS_REVIEW,
                "Cash-runway agent returned no risk and no typed diagnostic.",
                metadata={"issue": "cash_runway_diagnostic_missing"},
            )
        mapping = {
            CashRunwayAgentStatus.RETRIEVER_NO_RESULT: DiagnosticCode.EVIDENCE_NOT_FOUND,
            CashRunwayAgentStatus.EXTRACTION_NEEDS_REVIEW: self._issue_code(diagnostics.issues),
            CashRunwayAgentStatus.BUILDER_NEEDS_REVIEW: DiagnosticCode.NEEDS_REVIEW,
            CashRunwayAgentStatus.NOT_APPLICABLE: DiagnosticCode.NOT_APPLICABLE,
            CashRunwayAgentStatus.COMPONENT_FAILURE: DiagnosticCode.COMPONENT_FAILURE,
            CashRunwayAgentStatus.BUILT: DiagnosticCode.NEEDS_REVIEW,
        }
        return self._diagnostic(
            "cash_runway",
            mapping[diagnostics.status],
            "Cash-runway analysis did not generate a pending risk.",
            evidence_ids=diagnostics.evidence_ids,
            metadata={
                "rule_version": self.policy.version,
                "legacy_status": diagnostics.status.value,
                "issues": diagnostics.issues,
                "pages": diagnostics.pages,
                **diagnostics.metadata,
            },
        )

    def _analyze_v03_risk(
        self,
        risk_code: str,
        chunks: list[DocumentChunk],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> tuple[RiskItem | None, ComponentDiagnostic]:
        retrieval = self._retrieve_family(risk_code, chunks)
        query_metadata = {
            "query_count": len(FINANCIAL_EVIDENCE_QUERIES[risk_code]),
            "retrieved_evidence_count": len(retrieval.evidence),
            "retriever_error_types": retrieval.error_types,
        }
        if not retrieval.evidence:
            code = (
                DiagnosticCode.COMPONENT_FAILURE
                if retrieval.error_types
                else DiagnosticCode.EVIDENCE_NOT_FOUND
            )
            message = (
                "All usable retrieval attempts failed for this financial risk."
                if retrieval.error_types
                else "No supporting Evidence was retrieved for this financial risk."
            )
            return None, self._diagnostic(
                risk_code, code, message, metadata=query_metadata
            )

        try:
            extraction = self._extract_family(
                risk_code, retrieval.evidence, chunks_by_id
            )
            status, issues, evidence_ids, extraction_metadata = self._extraction_summary(
                extraction
            )
        except Exception as exc:
            return None, self._component_failure(
                risk_code,
                "v03_financial_extractor",
                exc,
                evidence_ids=[item.evidence_id for item in retrieval.evidence],
                metadata=query_metadata,
            )

        if status != ExtractionStatus.EXTRACTED or issues:
            return None, self._diagnostic(
                risk_code,
                self._issue_code(issues, status=status),
                "Retrieved financial Evidence could not be mapped to clean facts.",
                evidence_ids=evidence_ids,
                metadata={
                    **query_metadata,
                    **extraction_metadata,
                    "extraction_status": status.value,
                    "issues": issues,
                },
            )

        evidence_by_id = {item.evidence_id: item for item in retrieval.evidence}
        try:
            decision = self._build_decision(
                risk_code, extraction, evidence_by_id, chunks_by_id
            )
        except Exception as exc:
            return None, self._component_failure(
                risk_code,
                "v03_financial_risk_builder",
                exc,
                evidence_ids=evidence_ids,
                metadata=query_metadata,
            )
        diagnostic = decision.diagnostic.model_copy(
            update={
                "metadata": {**decision.diagnostic.metadata, **query_metadata}
            }
        )
        return decision.risk, diagnostic

    def _retrieve_family(
        self, risk_code: str, chunks: list[DocumentChunk]
    ) -> _RetrievalResult:
        retained: list[Evidence] = []
        source_keys: set[tuple[object, ...]] = set()
        error_types: list[str] = []
        for query in FINANCIAL_EVIDENCE_QUERIES[risk_code]:
            try:
                candidates = self.retriever.retrieve(chunks, query, limit=5)
                for evidence in candidates:
                    if not isinstance(evidence, Evidence):
                        raise TypeError("retriever_item_type_invalid")
                    key = (
                        evidence.document_id,
                        evidence.chunk_id,
                        evidence.page,
                    )
                    if key in source_keys:
                        continue
                    source_keys.add(key)
                    retained.append(evidence)
                    if len(retained) == 5:
                        return _RetrievalResult(retained, error_types)
            except Exception as exc:
                error_type = type(exc).__name__
                if error_type not in error_types:
                    error_types.append(error_type)
                continue
        return _RetrievalResult(retained, error_types)

    def _extract_family(
        self,
        risk_code: str,
        evidence: Sequence[Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> FinancialPeriodSeriesResult | ConcentrationFact:
        kwargs = {
            "net_result_candidates": evidence if risk_code == "continuous_loss" else [],
            "revenue_candidates": evidence if risk_code == "revenue_growth" else [],
            "customer_concentration_candidates": (
                evidence if risk_code == "customer_concentration" else []
            ),
            "supplier_concentration_candidates": (
                evidence if risk_code == "supplier_concentration" else []
            ),
            "chunks_by_id": chunks_by_id,
        }
        result = self.extractor.extract_v03(**kwargs)
        return {
            "continuous_loss": result.net_results,
            "revenue_growth": result.revenues,
            "customer_concentration": result.customer_concentration,
            "supplier_concentration": result.supplier_concentration,
        }[risk_code]

    def _build_decision(
        self,
        risk_code: str,
        extraction: FinancialPeriodSeriesResult | ConcentrationFact,
        evidence_by_id: Mapping[str, Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> _RiskDecision:
        if risk_code == "continuous_loss":
            assert isinstance(extraction, FinancialPeriodSeriesResult)
            return self.risk_builder.build_continuous_loss(
                extraction, evidence_by_id, chunks_by_id
            )
        if risk_code == "revenue_growth":
            assert isinstance(extraction, FinancialPeriodSeriesResult)
            return self.risk_builder.build_revenue_growth(
                extraction, evidence_by_id, chunks_by_id
            )
        assert isinstance(extraction, ConcentrationFact)
        return self.risk_builder.build_concentration(
            extraction, evidence_by_id, chunks_by_id
        )

    @staticmethod
    def _extraction_summary(
        extraction: FinancialPeriodSeriesResult | ConcentrationFact,
    ) -> tuple[ExtractionStatus, list[str], list[str], dict[str, object]]:
        metadata: dict[str, object] = {}
        if isinstance(extraction, ConcentrationFact):
            metadata = {
                "period_end": (
                    extraction.period_end.isoformat() if extraction.period_end else None
                ),
                "period_months": extraction.period_months,
                "reconciliation_version": extraction.metadata.get(
                    "reconciliation_version"
                ),
                "candidate_count": extraction.metadata.get("candidate_count"),
                "selected_candidate_count": extraction.metadata.get(
                    "selected_candidate_count"
                ),
                "governing_candidate_count": extraction.metadata.get(
                    "governing_candidate_count"
                ),
                "value_candidate_count": extraction.metadata.get(
                    "value_candidate_count"
                ),
                "merge_value_basis": extraction.metadata.get("merge_value_basis"),
                "candidate_diagnostics": extraction.metadata.get(
                    "candidate_diagnostics", []
                ),
            }
        return (
            extraction.status,
            list(extraction.issues),
            list(extraction.evidence_ids),
            metadata,
        )

    @staticmethod
    def _issue_code(
        issues: Sequence[str],
        *,
        status: ExtractionStatus | None = None,
    ) -> DiagnosticCode:
        joined = " ".join(issues)
        if "conflict" in joined:
            return DiagnosticCode.CONFLICTING_VALUES
        if "unsupported_layout" in issues:
            return DiagnosticCode.UNSUPPORTED_LAYOUT
        if status == ExtractionStatus.NOT_FOUND:
            return DiagnosticCode.EXTRACTION_FAILED
        return DiagnosticCode.NEEDS_REVIEW

    def _component_failure(
        self,
        risk_code: str,
        component: str,
        exc: Exception,
        *,
        evidence_ids: Sequence[str] = (),
        metadata: Mapping[str, object] | None = None,
    ) -> ComponentDiagnostic:
        return self._diagnostic(
            risk_code,
            DiagnosticCode.COMPONENT_FAILURE,
            "A financial component failed; independent risk analysis continued.",
            evidence_ids=evidence_ids,
            metadata={
                "component": component,
                "error_type": type(exc).__name__,
                **dict(metadata or {}),
            },
        )

    def _diagnostic(
        self,
        risk_code: str,
        code: DiagnosticCode,
        message: str,
        *,
        evidence_ids: Sequence[str] = (),
        metadata: Mapping[str, object] | None = None,
    ) -> ComponentDiagnostic:
        return ComponentDiagnostic(
            risk_code=risk_code,
            code=code,
            message=message,
            recoverable=True,
            evidence_ids=list(dict.fromkeys(evidence_ids)),
            metadata={"rule_version": self.policy.version, **dict(metadata or {})},
        )
