"""Standalone v0.3 Business Agent for pre-commercial product risk."""

from __future__ import annotations

from inspect import signature
import re
from typing import Any

from ipo_risk.agents.base import RiskAgent
from ipo_risk.agents.business_extraction import (
    BusinessExtractionResult,
    DeterministicBusinessExtractor,
)
from ipo_risk.agents.business_models import (
    CommercializationCandidate,
    CoreProductCandidate,
)
from ipo_risk.agents.business_policy import RULE_VERSION, build_precommercial_risk
from ipo_risk.providers.llm import LLMProviderError
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import (
    ComponentDiagnostic,
    DiagnosticCode,
    DocumentChunk,
    Evidence,
    EvidenceSourceType,
    IPOProfile,
    MarketSnapshot,
    RiskItem,
)


BUSINESS_EVIDENCE_QUERIES = ("commercialization_status", "core_product_pipeline")
PROMPT_VERSION = "business_precommercial_v1"


class V03BusinessAgent:
    """Return only pending pre-commercial candidates or typed diagnostics."""

    name = "business"

    def __init__(
        self,
        *,
        retriever: Any | None = None,
        extractor: DeterministicBusinessExtractor | None = None,
        llm_provider: Any | None = None,
    ) -> None:
        self.retriever = retriever or KeywordDocumentRetriever()
        self.extractor = extractor or DeterministicBusinessExtractor()
        self.llm_provider = llm_provider
        self.last_diagnostics: list[ComponentDiagnostic] = []

    def analyze(
        self,
        profile: IPOProfile,
        chunks: list[DocumentChunk],
        market: MarketSnapshot | None = None,
    ) -> list[RiskItem]:
        """Analyze one owned risk without shared Workflow registration."""

        self.last_diagnostics = []
        evidence, retrieval_errors = self._retrieve(chunks)
        if not evidence:
            code = (
                DiagnosticCode.COMPONENT_FAILURE
                if retrieval_errors == len(BUSINESS_EVIDENCE_QUERIES)
                else DiagnosticCode.EVIDENCE_NOT_FOUND
            )
            self._record(code, "Business evidence could not be safely selected.")
            return []

        if not self._valid_identity(evidence, chunks):
            self._record(
                DiagnosticCode.NEEDS_REVIEW,
                "Selected Evidence does not map to the supplied document chunks.",
                evidence_ids=[item.evidence_id for item in evidence],
                metadata={"issue": "invalid_evidence_identity"},
            )
            return []

        try:
            extraction = self.extractor.extract(evidence)
        except Exception:
            self._record(
                DiagnosticCode.COMPONENT_FAILURE,
                "Deterministic Business extraction failed.",
                evidence_ids=[item.evidence_id for item in evidence],
                metadata={"component": "business_extractor"},
            )
            return []

        extraction, llm_issue, llm_metadata = self._enhance_with_llm(
            extraction, evidence
        )
        if llm_issue in {"evidence_out_of_scope", "candidate_conflict"}:
            self._record(
                DiagnosticCode.NEEDS_REVIEW
                if llm_issue == "evidence_out_of_scope"
                else DiagnosticCode.CONFLICTING_VALUES,
                "LLM candidate could not be safely reconciled.",
                evidence_ids=[item.evidence_id for item in evidence],
                metadata={"issue": llm_issue, **llm_metadata},
            )
            return []

        return self._decide(extraction, evidence, llm_issue, llm_metadata)

    def _retrieve(self, chunks: list[DocumentChunk]) -> tuple[list[Evidence], int]:
        selected: dict[tuple[str | None, str | None, int | None], Evidence] = {}
        errors = 0
        for query in BUSINESS_EVIDENCE_QUERIES:
            try:
                items = self.retriever.retrieve(chunks, query, limit=5)
            except Exception:
                errors += 1
                continue
            for item in items[:5]:
                key = (item.document_id, item.chunk_id, item.page)
                current = selected.get(key)
                if current is None or item.relevance_score > current.relevance_score:
                    selected[key] = item
        return sorted(
            selected.values(),
            key=lambda item: (item.page or 0, item.chunk_id or "", item.evidence_id),
        ), errors

    @staticmethod
    def _valid_identity(evidence: list[Evidence], chunks: list[DocumentChunk]) -> bool:
        identities = {(item.document_id, item.chunk_id, item.page) for item in chunks}
        return all(
            item.source_type == EvidenceSourceType.PROSPECTUS
            and item.document_id is not None
            and item.chunk_id is not None
            and item.page is not None
            and (item.document_id, item.chunk_id, item.page) in identities
            for item in evidence
        )

    def _enhance_with_llm(
        self,
        deterministic: BusinessExtractionResult,
        evidence: list[Evidence],
    ) -> tuple[BusinessExtractionResult, str | None, dict[str, Any]]:
        if self.llm_provider is None:
            return deterministic, None, {"llm_mode": "not_configured"}
        allowed_ids = {item.evidence_id for item in evidence}
        metadata: dict[str, Any] = {
            "llm_provider": getattr(self.llm_provider, "name", "unknown"),
            "prompt_version": PROMPT_VERSION,
        }
        try:
            llm_commercial = self.llm_provider.generate_structured(
                task_name="business_precommercial_commercialization_extract",
                prompt_version=PROMPT_VERSION,
                evidence=evidence,
                response_model=CommercializationCandidate,
            )
            llm_core = self.llm_provider.generate_structured(
                task_name="business_precommercial_core_product_extract",
                prompt_version=PROMPT_VERSION,
                evidence=evidence,
                response_model=CoreProductCandidate,
            )
        except LLMProviderError as exc:
            metadata["llm_failure_kind"] = exc.kind.value
            return deterministic, "provider_failure", metadata
        except Exception:
            metadata["llm_failure_kind"] = "safe_provider_failure"
            return deterministic, "provider_failure", metadata

        if not set(llm_commercial.evidence_ids) <= allowed_ids or not set(
            llm_core.evidence_ids
        ) <= allowed_ids:
            return deterministic, "evidence_out_of_scope", metadata

        llm_commercial, llm_core = self._canonicalize_llm_candidates(
            llm_commercial, llm_core
        )
        metadata["llm_normalization"] = "business_candidate_canonical_v1"
        conflict_reasons = self._llm_conflict_reasons(
            deterministic, llm_commercial, llm_core
        )
        if conflict_reasons:
            metadata["llm_conflicts"] = conflict_reasons
            return deterministic, "candidate_conflict", metadata
        metadata["llm_cross_check"] = "consistent"
        return self._fill_from_llm(deterministic, llm_commercial, llm_core), None, metadata

    @classmethod
    def _canonicalize_llm_candidates(
        cls,
        commercial: CommercializationCandidate,
        core: CoreProductCandidate,
    ) -> tuple[CommercializationCandidate, CoreProductCandidate]:
        stage = cls._canonical_stage(commercial.development_stage)
        launch = cls._canonical_launch_status(core.launch_status)
        approval = cls._canonical_approval_status(core.approval_status)
        return (
            commercial.model_copy(
                update={
                    "development_stage": stage or commercial.development_stage.strip(),
                }
            ),
            core.model_copy(
                update={
                    "launch_status": launch or core.launch_status.strip(),
                    "approval_status": approval or core.approval_status.strip(),
                }
            ),
        )

    @classmethod
    def _llm_conflict_reasons(
        cls,
        deterministic: BusinessExtractionResult,
        commercial: CommercializationCandidate,
        core: CoreProductCandidate,
    ) -> list[str]:
        conflicts: list[str] = []
        det_commercial = deterministic.commercialization
        det_core = deterministic.core_product
        if (
            deterministic.has_product_revenue is not None
            and commercial.has_product_revenue is not None
            and deterministic.has_product_revenue != commercial.has_product_revenue
        ):
            conflicts.append("product_revenue")
        if det_core and cls._canonical_product_name(core.product_name) != cls._canonical_product_name(
            det_core.product_name
        ):
            conflicts.append("core_product_identity")
        if det_core and not core.is_core_product:
            conflicts.append("core_product_designation")
        if det_commercial and det_commercial.development_stage not in {"", "unknown"}:
            llm_stage = cls._canonical_stage(commercial.development_stage)
            det_stage = cls._canonical_stage(det_commercial.development_stage)
            if llm_stage not in {"", "unknown", det_stage}:
                conflicts.append("development_stage")
        det_launch = cls._canonical_launch_status(det_core.launch_status) if det_core else ""
        llm_launch = cls._canonical_launch_status(core.launch_status)
        if det_launch and llm_launch and det_launch != llm_launch:
            conflicts.append("launch_status")
        return conflicts

    @classmethod
    def _llm_conflicts(
        cls,
        deterministic: BusinessExtractionResult,
        commercial: CommercializationCandidate,
        core: CoreProductCandidate,
    ) -> bool:
        """Backward-compatible boolean view used by older tests/callers."""

        return bool(cls._llm_conflict_reasons(deterministic, commercial, core))

    @staticmethod
    def _canonical_product_name(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.casefold())

    @staticmethod
    def _canonical_stage(value: str) -> str:
        raw = value.strip().casefold()
        if not raw:
            return ""
        compact = re.sub(r"[\s_-]+", "", raw)
        if raw == "unknown" or compact in {"unknown", "未知"}:
            return "unknown"
        if compact in {"launched", "commerciallylaunched", "商业化", "商業化", "已上市"}:
            return "launched"
        if compact in {"approved", "marketingapproved", "获批", "獲批", "批准上市"}:
            return "approved"
        if compact in {"registration", "nda", "bla", "注册申请", "註冊申請"}:
            return "registration"
        if compact in {"phaseiii", "phase3", "clinicalphaseiii", "三期", "iii期", "临床iii期", "臨床iii期"}:
            return "phase_iii"
        if compact in {"phaseii", "phase2", "clinicalphaseii", "二期", "ii期", "临床ii期", "臨床ii期"}:
            return "phase_ii"
        if compact in {"phasei", "phase1", "clinicalphasei", "一期", "i期", "临床i期", "臨床i期"}:
            return "phase_i"
        if compact in {"preclinical", "临床前", "臨床前"}:
            return "preclinical"
        return raw.replace(" ", "_").replace("-", "_")

    @staticmethod
    def _canonical_launch_status(value: str) -> str:
        raw = value.strip().casefold()
        if not raw:
            return ""
        compact = re.sub(r"[\s_-]+", "", raw)
        if compact in {"launched", "commerciallylaunched", "commercialized", "commercialised", "已上市", "已商业化", "已商業化"}:
            return "launched"
        if compact in {
            "notlaunched",
            "notyetlaunched",
            "notcommercialized",
            "notcommercialised",
            "notyetcommercialized",
            "notyetcommercialised",
            "尚未上市",
            "未上市",
            "尚未商业化",
            "尚未商業化",
        }:
            return "not_launched"
        if compact in {"unknown", "未知"}:
            return ""
        return raw.replace(" ", "_").replace("-", "_")

    @staticmethod
    def _canonical_approval_status(value: str) -> str:
        raw = value.strip().casefold()
        if not raw:
            return ""
        compact = re.sub(r"[\s_-]+", "", raw)
        if compact in {"approved", "marketingapproved", "获批", "獲批", "已批准"}:
            return "approved"
        if compact in {"notapproved", "notyetapproved", "未获批", "未獲批", "尚未批准"}:
            return "not_approved"
        if compact in {"unknown", "未知"}:
            return ""
        return raw.replace(" ", "_").replace("-", "_")

    @staticmethod
    def _fill_from_llm(
        deterministic: BusinessExtractionResult,
        commercial: CommercializationCandidate,
        core: CoreProductCandidate,
    ) -> BusinessExtractionResult:
        det_commercial = deterministic.commercialization
        det_core = deterministic.core_product
        merged_commercial = commercial if det_commercial is None else det_commercial.model_copy(
            update={
                "product_name": det_commercial.product_name
                if det_commercial.product_name != "unknown"
                else commercial.product_name,
                "development_stage": det_commercial.development_stage
                if det_commercial.development_stage != "unknown"
                else commercial.development_stage,
                "has_product_revenue": deterministic.has_product_revenue
                if deterministic.has_product_revenue is not None
                else commercial.has_product_revenue,
            }
        )
        merged_core = det_core or core
        return deterministic.model_copy(
            update={
                "commercialization": merged_commercial,
                "core_product": merged_core,
                "has_product_revenue": merged_commercial.has_product_revenue,
                "is_not_commercialized": deterministic.is_not_commercialized
                if deterministic.is_not_commercialized is not None
                else (
                    True
                    if merged_core.launch_status == "not_launched"
                    else False
                    if merged_core.launch_status == "launched"
                    else None
                ),
            }
        )

    def _decide(
        self,
        extraction: BusinessExtractionResult,
        evidence: list[Evidence],
        llm_issue: str | None,
        llm_metadata: dict[str, Any],
    ) -> list[RiskItem]:
        evidence_ids = [item.evidence_id for item in evidence]
        common = {
            "rule_version": RULE_VERSION,
            "issues": extraction.issues,
            "revenue_source_types": extraction.revenue_source_types,
            **llm_metadata,
        }
        if extraction.conflicting_values:
            self._record(
                DiagnosticCode.CONFLICTING_VALUES,
                "Commercialization or revenue facts conflict.",
                evidence_ids=evidence_ids,
                metadata=common,
            )
            return []
        if extraction.is_not_commercialized is False or extraction.has_product_revenue is True:
            self._record(
                DiagnosticCode.NOT_APPLICABLE,
                "Evidence shows commercialization or direct product sales revenue.",
                evidence_ids=evidence_ids,
                metadata=common,
            )
            return []
        if (
            extraction.core_product is not None
            and extraction.core_product.is_core_product
            and extraction.is_not_commercialized is True
            and extraction.has_product_revenue is False
        ):
            risk = build_precommercial_risk(extraction, evidence)
            self._record(
                DiagnosticCode.RISK_GENERATED,
                "A pending pre-commercial product risk was generated for Verifier review.",
                evidence_ids=evidence_ids,
                metadata={**common, "risk_id": risk.risk_id},
            )
            return [risk]
        code = (
            DiagnosticCode.COMPONENT_FAILURE
            if llm_issue == "provider_failure" and not extraction.factual_evidence_ids
            else DiagnosticCode.NEEDS_REVIEW
            if extraction.generic_revenue_ambiguous or extraction.factual_evidence_ids
            else DiagnosticCode.EXTRACTION_FAILED
        )
        self._record(
            code,
            "Business facts are insufficient for a deterministic rule decision.",
            evidence_ids=evidence_ids,
            metadata=common,
        )
        return []

    def _record(
        self,
        code: DiagnosticCode,
        message: str,
        *,
        evidence_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.last_diagnostics = [
            ComponentDiagnostic(
                risk_code="precommercial_product",
                code=code,
                message=message,
                evidence_ids=evidence_ids or [],
                metadata=metadata or {},
            )
        ]


# The implementation keeps postponed annotations for internal readability,
# while exposing the exact frozen Protocol signature to runtime introspection.
setattr(V03BusinessAgent.analyze, "__signature__", signature(RiskAgent.analyze))
