"""Failure-isolated v0.3 Legal Agent for both frozen legal risk codes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError

from ipo_risk.domain.material_litigation_compliance import (
    MaterialLitigationComplianceBuildStatus,
    MaterialLitigationComplianceRiskBuilder,
)
from ipo_risk.domain.redemption_rights import (
    RedemptionRightsBuildStatus,
    RedemptionRightsRiskBuilder,
)
from ipo_risk.extraction import (
    ExtractionStatus,
    LitigationComplianceExtractor,
    ShareholderRightsExtractor,
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
)


class LLMProviderUnavailableError(RuntimeError):
    """Internal honest-degradation signal when no structured LLM is configured."""


class _UnavailableStructuredLLMProvider:
    name = "unavailable"
    last_call_metadata = None

    def complete(self, prompt: str) -> str:
        raise LLMProviderUnavailableError("Structured LLM provider is unavailable.")

    def generate_structured(self, **kwargs):
        raise LLMProviderUnavailableError("Structured LLM provider is unavailable.")


class LegalAgent:
    """Retrieve, extract and build both legal risks without cross-component failure."""

    name = "legal"
    rights_risk_code = "redemption_rights"
    litigation_risk_code = "material_litigation_compliance"
    max_evidence = 10

    rights_queries = (
        "redemption right",
        "赎回权",
        "贖回權",
        "special rights",
        "特殊权利",
        "特殊權利",
        "liquidation preference",
        "anti-dilution right",
        "termination",
        "restoration",
    )
    litigation_queries = (
        "material litigation",
        "重大诉讼",
        "重大訴訟",
        "arbitration",
        "administrative penalty",
        "行政处罚",
        "行政處罰",
        "regulatory investigation",
        "non-compliance",
        "licence",
        "牌照",
        "remediation",
    )

    def __init__(
        self,
        retriever=None,
        llm_provider=None,
        rights_extractor: ShareholderRightsExtractor | None = None,
        litigation_extractor: LitigationComplianceExtractor | None = None,
        rights_builder: RedemptionRightsRiskBuilder | None = None,
        litigation_builder: MaterialLitigationComplianceRiskBuilder | None = None,
    ) -> None:
        provider = llm_provider or _UnavailableStructuredLLMProvider()
        self.retriever = retriever or KeywordDocumentRetriever()
        self.rights_extractor = rights_extractor or ShareholderRightsExtractor(provider)
        self.litigation_extractor = litigation_extractor or LitigationComplianceExtractor(
            provider
        )
        self.rights_builder = rights_builder or RedemptionRightsRiskBuilder()
        self.litigation_builder = (
            litigation_builder or MaterialLitigationComplianceRiskBuilder()
        )
        self.last_diagnostics: list[ComponentDiagnostic] = []

    def analyze(
        self,
        profile: IPOProfile,
        chunks: list[DocumentChunk],
        market: MarketSnapshot | None = None,
    ) -> list[RiskItem]:
        """Run both frozen legal risk chains and isolate every component failure."""

        risks: list[RiskItem] = []
        diagnostics: list[ComponentDiagnostic] = []

        rights_risks, rights_diagnostic = self._run_rights(chunks)
        risks.extend(rights_risks)
        diagnostics.append(rights_diagnostic)

        litigation_risks, litigation_diagnostic = self._run_litigation(chunks)
        risks.extend(litigation_risks)
        diagnostics.append(litigation_diagnostic)

        self.last_diagnostics = diagnostics
        return risks

    def _run_rights(
        self, chunks: list[DocumentChunk]
    ) -> tuple[list[RiskItem], ComponentDiagnostic]:
        risk_code = self.rights_risk_code
        evidence, retrieval_failure = self._retrieve_component(
            chunks, self.rights_queries, risk_code
        )
        if retrieval_failure is not None:
            return [], retrieval_failure
        if not evidence:
            return [], self._diagnostic(
                risk_code,
                DiagnosticCode.EVIDENCE_NOT_FOUND,
                "No shareholder-rights Evidence was retrieved.",
                ["evidence_not_found"],
                stage="retrieval",
            )

        try:
            fact = self.rights_extractor.extract(evidence)
        except Exception as exc:
            return [], self._extraction_failure(risk_code, exc, evidence)

        try:
            built = self.rights_builder.build(
                fact, {item.evidence_id: item for item in evidence}
            )
        except Exception as exc:
            return [], self._component_failure(
                risk_code, "risk_builder", exc, evidence
            )

        internal_issues = self._rights_internal_issues(fact, built.issues)
        metadata = {
            "stage": "risk_builder",
            "extraction_status": fact.status.value,
            "builder_status": built.status.value,
            "failure_isolated": True,
        }
        if built.status == RedemptionRightsBuildStatus.NOT_APPLICABLE:
            return [], self._diagnostic(
                risk_code,
                DiagnosticCode.NOT_APPLICABLE,
                "Special shareholder rights are not a current applicable risk.",
                internal_issues,
                evidence,
                metadata=metadata,
            )
        if built.risk_item is not None:
            code = (
                DiagnosticCode.RISK_GENERATED
                if built.status == RedemptionRightsBuildStatus.BUILT
                else self._issue_diagnostic_code(built.issues)
            )
            return [built.risk_item], self._diagnostic(
                risk_code,
                code,
                "Shareholder-rights candidate was generated for verification."
                if code == DiagnosticCode.RISK_GENERATED
                else "Shareholder-rights facts require legal review.",
                internal_issues,
                evidence,
                metadata=metadata,
            )
        return [], self._diagnostic(
            risk_code,
            self._issue_diagnostic_code(built.issues),
            "Shareholder-rights processing did not emit a risk candidate.",
            internal_issues,
            evidence,
            metadata=metadata,
        )

    def _run_litigation(
        self, chunks: list[DocumentChunk]
    ) -> tuple[list[RiskItem], ComponentDiagnostic]:
        risk_code = self.litigation_risk_code
        evidence, retrieval_failure = self._retrieve_component(
            chunks, self.litigation_queries, risk_code
        )
        if retrieval_failure is not None:
            return [], retrieval_failure
        if not evidence:
            return [], self._diagnostic(
                risk_code,
                DiagnosticCode.EVIDENCE_NOT_FOUND,
                "No litigation or compliance Evidence was retrieved.",
                ["evidence_not_found"],
                stage="retrieval",
            )

        try:
            observation = self.litigation_extractor.extract(evidence)
        except Exception as exc:
            return [], self._extraction_failure(risk_code, exc, evidence)

        try:
            built = self.litigation_builder.build(
                observation, {item.evidence_id: item for item in evidence}
            )
        except Exception as exc:
            return [], self._component_failure(
                risk_code, "risk_builder", exc, evidence
            )

        internal_issues = self._litigation_internal_issues(
            observation, built.issues
        )
        metadata = {
            "stage": "risk_builder",
            "extraction_status": observation.status.value,
            "builder_status": built.status.value,
            "failure_isolated": True,
        }
        if built.status == MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE:
            return [], self._diagnostic(
                risk_code,
                DiagnosticCode.NOT_APPLICABLE,
                "Evidence does not establish a current material litigation or compliance risk.",
                internal_issues,
                evidence,
                metadata=metadata,
            )
        if built.risk_item is not None:
            code = (
                DiagnosticCode.RISK_GENERATED
                if built.status == MaterialLitigationComplianceBuildStatus.BUILT
                else self._issue_diagnostic_code(built.issues)
            )
            return [built.risk_item], self._diagnostic(
                risk_code,
                code,
                "Litigation/compliance candidate was generated for verification."
                if code == DiagnosticCode.RISK_GENERATED
                else "Litigation/compliance facts require legal review.",
                internal_issues,
                evidence,
                metadata=metadata,
            )
        return [], self._diagnostic(
            risk_code,
            self._issue_diagnostic_code(built.issues),
            "Litigation/compliance processing did not emit a risk candidate.",
            internal_issues,
            evidence,
            metadata=metadata,
        )

    def _retrieve_component(
        self,
        chunks: list[DocumentChunk],
        queries: Sequence[str],
        risk_code: str,
    ) -> tuple[list[Evidence], ComponentDiagnostic | None]:
        collected: list[Evidence] = []
        for query in queries:
            try:
                collected.extend(self.retriever.retrieve(chunks, query, limit=5))
            except Exception as exc:
                return [], self._component_failure(
                    risk_code,
                    "retriever",
                    exc,
                    collected,
                    extra_metadata={"failed_query": query},
                )
        unique: dict[tuple[Any, ...], Evidence] = {}
        for item in collected:
            key = (
                item.document_id,
                item.chunk_id,
                item.page,
                " ".join(item.text.split()),
            )
            existing = unique.get(key)
            if existing is None or item.relevance_score > existing.relevance_score:
                unique[key] = item
        evidence = sorted(
            unique.values(),
            key=lambda item: (
                -item.relevance_score,
                item.page or 0,
                item.chunk_id or "",
                item.evidence_id,
            ),
        )[: self.max_evidence]
        return evidence, None

    def _extraction_failure(
        self,
        risk_code: str,
        exc: Exception,
        evidence: Sequence[Evidence],
    ) -> ComponentDiagnostic:
        issues = ["extraction_failed"]
        if isinstance(exc, ValidationError):
            issues.append("llm_structured_output_invalid")
        if isinstance(exc, LLMProviderUnavailableError):
            issues.append("llm_provider_unavailable")
        return self._diagnostic(
            risk_code,
            DiagnosticCode.EXTRACTION_FAILED,
            "Structured legal fact extraction failed; the other legal component continued.",
            issues,
            evidence,
            metadata={
                "stage": "extraction",
                "component": "structured_extractor",
                "error_type": type(exc).__name__,
                "failure_isolated": True,
            },
        )

    def _component_failure(
        self,
        risk_code: str,
        component: str,
        exc: Exception,
        evidence: Sequence[Evidence],
        extra_metadata: dict[str, Any] | None = None,
    ) -> ComponentDiagnostic:
        return self._diagnostic(
            risk_code,
            DiagnosticCode.COMPONENT_FAILURE,
            f"Legal {component} failed; the other legal component continued.",
            [f"{component}_failure"],
            evidence,
            metadata={
                "stage": component,
                "component": component,
                "error_type": type(exc).__name__,
                "failure_isolated": True,
                **(extra_metadata or {}),
            },
        )

    @staticmethod
    def _issue_diagnostic_code(issues: Sequence[str]) -> DiagnosticCode:
        if any("conflict" in issue for issue in issues):
            return DiagnosticCode.CONFLICTING_VALUES
        if any("unsupported_layout" in issue for issue in issues):
            return DiagnosticCode.UNSUPPORTED_LAYOUT
        if any("evidence_not_found" in issue for issue in issues):
            return DiagnosticCode.EVIDENCE_NOT_FOUND
        return DiagnosticCode.NEEDS_REVIEW

    @staticmethod
    def _rights_internal_issues(fact, builder_issues: Sequence[str]) -> list[str]:
        issues = list(dict.fromkeys([*fact.issues, *builder_issues]))
        if "termination_condition_not_established" in issues:
            issues.append("termination_clause_not_found")
        if any(
            issue in issues
            for issue in (
                "restoration_status_not_established",
                "restoration_condition_missing",
            )
        ):
            issues.append("restoration_clause_ambiguous")
        if (
            fact.status == ExtractionStatus.EXTRACTED
            and fact.is_effective is False
            and fact.survives_listing is False
        ):
            issues.append("historical_right_only")
        return list(dict.fromkeys(issues))

    @staticmethod
    def _litigation_internal_issues(
        observation, builder_issues: Sequence[str]
    ) -> list[str]:
        issues = list(dict.fromkeys([*observation.issues, *builder_issues]))
        classifications = observation.metadata.get("evidence_classifications", [])
        kinds = {
            item.get("kind") for item in classifications if isinstance(item, dict)
        }
        if "explicit_negative" in kinds:
            issues.append("negation_detected")
        if kinds and kinds.issubset(
            {"explicit_negative", "generic_future_risk", "template_statement"}
        ):
            issues.append("no_actual_matter_detected")
        if observation.current_status in {"resolved", "remediated"}:
            issues.append("matter_resolved")
        if "management_materiality_not_established" in issues:
            issues.append("materiality_unclear")
        if observation.current_status in {"resolved", "remediated"} and not observation.is_pending:
            issues.append("historical_matter_only")
        return list(dict.fromkeys(issues))

    @staticmethod
    def _diagnostic(
        risk_code: str,
        code: DiagnosticCode,
        message: str,
        internal_issues: Sequence[str],
        evidence: Sequence[Evidence] = (),
        *,
        stage: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ComponentDiagnostic:
        details = dict(metadata or {})
        if stage is not None:
            details["stage"] = stage
        details["internal_issue_codes"] = list(dict.fromkeys(internal_issues))
        details["evidence_count"] = len(evidence)
        details["pages"] = list(
            dict.fromkeys(item.page for item in evidence if item.page is not None)
        )
        return ComponentDiagnostic(
            risk_code=risk_code,
            code=code,
            message=message,
            evidence_ids=[item.evidence_id for item in evidence],
            metadata=details,
        )
