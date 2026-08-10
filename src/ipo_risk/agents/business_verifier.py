"""Deterministic, standalone verification for v0.3 Business risks.

Member-5 professional rules for the ``precommercial_product`` candidate:

* The candidate must stay provisional ``medium / 60`` under the frozen
  severity policy; the Verifier never upgrades or downgrades the level.
* Embedded Evidence must factually support both rule inputs: the core
  product is not yet commercialized AND no direct product sales revenue
  was generated. Evidence that instead shows commercialization or direct
  product sales revenue contradicts the candidate and rejects it.
* Licensing, milestone, R&D-service, or collaboration revenue must not be
  treated as product sales revenue; ambiguous attribution degrades to
  ``needs_review`` instead of ``verified``.
* The core product identity and development stage must be known; unknown
  values degrade to ``needs_review``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from ipo_risk.agents.business_extraction import (
    _COMMERCIALIZED,
    _DIRECT_PRODUCT_REVENUE,
    _NO_PRODUCT_REVENUE,
    _NOT_COMMERCIALIZED,
    normalize_business_text,
)
from ipo_risk.agents.business_policy import RULE_VERSION, SEVERITY_POLICY
from ipo_risk.domain.risk_codes import V03_RISK_OWNERS
from ipo_risk.schemas import (
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationResult,
    VerificationStatus,
)


_BUSINESS_CODES = tuple(
    risk_code for risk_code, owner in V03_RISK_OWNERS.items() if owner == "business"
)
_KNOWN_REVENUE_SOURCES = frozenset(
    {"licensing", "milestone", "rd_service", "collaboration", "other_service"}
)
_BANNED_CLAIMS = (
    "必然破产",
    "必然失败",
    "必然下跌",
    "will go bankrupt",
    "will certainly fail",
    "guaranteed failure",
)


@dataclass(frozen=True, slots=True)
class _ReviewDecision:
    """Private classification for one input risk."""

    bucket: str
    risk: RiskItem


class V03BusinessVerifier:
    """Classify v0.3 pre-commercial Business RiskItems deterministically."""

    name = "business_verifier"

    def verify(
        self,
        risks: list[RiskItem],
        evidence_by_code: dict[str, list[Evidence]] | None = None,
    ) -> VerificationResult:
        """Return one stable classification for every input risk."""

        external = evidence_by_code or {}
        verified: list[RiskItem] = []
        pending: list[RiskItem] = []
        rejected: list[RiskItem] = []
        for risk in risks:
            decision = self._verify_one(risk, external.get(risk.risk_code, []))
            {"verified": verified, "pending": pending, "rejected": rejected}[
                decision.bucket
            ].append(decision.risk)
        return VerificationResult(
            verified_risks=verified,
            pending_risks=pending,
            rejected_risks=rejected,
        )

    def _verify_one(
        self, risk: RiskItem, external_evidence: Sequence[Evidence]
    ) -> _ReviewDecision:
        if risk.risk_code not in _BUSINESS_CODES:
            return self._pending(
                risk,
                VerificationStatus.PENDING,
                "Risk is outside the v0.3 Business Verifier scope.",
            )
        identity_error = self._identity_error(risk)
        if identity_error:
            return self._reject(risk, identity_error)
        if risk.verification_status == VerificationStatus.NEEDS_REVIEW:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Input candidate already requires review.",
            )
        if risk.verification_status != VerificationStatus.PENDING:
            return self._reject(risk, "input_verification_status_invalid")

        severity_error = self._severity_error(risk)
        if severity_error:
            return self._reject(risk, severity_error)

        evidence_decision = self._evidence_decision(risk, external_evidence)
        if evidence_decision is not None:
            return evidence_decision

        fact_decision = self._fact_decision(risk)
        if fact_decision is not None:
            return fact_decision

        support_decision = self._evidence_support_decision(risk)
        if support_decision is not None:
            return support_decision

        conclusion_decision = self._conclusion_decision(risk)
        if conclusion_decision is not None:
            return conclusion_decision

        verified = risk.model_copy(
            update={
                "verification_status": VerificationStatus.VERIFIED,
                "verification_notes": (
                    "Evidence identity passed; both pre-commercial rule inputs are "
                    "factually supported by prospectus Evidence; licensing or "
                    "collaboration revenue was not treated as product sales revenue; "
                    "level and rule score matched the frozen severity policy "
                    f"{SEVERITY_POLICY}. The score is rule-based, not a probability."
                ),
            }
        )
        return _ReviewDecision("verified", verified)

    @staticmethod
    def _identity_error(risk: RiskItem) -> str | None:
        if V03_RISK_OWNERS.get(risk.risk_code) != "business":
            return "risk_owner_invalid"
        if risk.category != RiskCategory.BUSINESS:
            return "risk_category_invalid"
        if risk.agent_name != "business":
            return "agent_name_invalid"
        if risk.metadata.get("score_is_rule_based") is not True:
            return "score_is_rule_based_invalid"
        if risk.metadata.get("score_is_probability") is not False:
            return "score_is_probability_invalid"
        if risk.metadata.get("rule_version") != RULE_VERSION:
            return "rule_version_invalid"
        if risk.metadata.get("severity_policy") != SEVERITY_POLICY:
            return "severity_policy_invalid"
        return None

    @staticmethod
    def _severity_error(risk: RiskItem) -> str | None:
        """v0.3 Business severity is provisional medium/60; never escalated."""

        if risk.level != RiskLevel.MEDIUM:
            return "risk_level_outside_frozen_policy"
        if float(risk.score) != 60.0:
            return "risk_score_outside_frozen_policy"
        return None

    def _evidence_decision(
        self, risk: RiskItem, external_evidence: Sequence[Evidence]
    ) -> _ReviewDecision | None:
        if not risk.evidence:
            return self._pending(
                risk, VerificationStatus.PENDING, "Embedded Evidence is not available."
            )
        ids = [item.evidence_id for item in risk.evidence]
        if any(not item for item in ids) or len(ids) != len(set(ids)):
            return self._reject(risk, "embedded_evidence_id_invalid")
        for item in risk.evidence:
            if not item.document_id or not item.chunk_id or item.page is None:
                return self._pending(
                    risk,
                    VerificationStatus.NEEDS_REVIEW,
                    "Embedded Evidence identity is incomplete.",
                )
            if item.source_type != EvidenceSourceType.PROSPECTUS:
                return self._reject(risk, "evidence_source_type_invalid")
            if not item.text.strip():
                return self._pending(
                    risk,
                    VerificationStatus.NEEDS_REVIEW,
                    "Embedded Evidence text is empty.",
                )
        documents = {item.document_id for item in risk.evidence}
        if len(documents) != 1:
            return self._reject(risk, "cross_document_evidence")

        if not external_evidence:
            return None
        external_by_id = {item.evidence_id: item for item in external_evidence}
        if not set(ids) <= set(external_by_id):
            return self._pending(
                risk,
                VerificationStatus.PENDING,
                "Referenced external Evidence is temporarily unavailable.",
            )
        embedded_by_id = {item.evidence_id: item for item in risk.evidence}
        if any(
            not self._same_evidence(embedded_by_id[evidence_id], external_by_id[evidence_id])
            for evidence_id in ids
        ):
            return self._reject(risk, "external_evidence_identity_or_text_mismatch")
        return None

    @staticmethod
    def _same_evidence(left: Evidence, right: Evidence) -> bool:
        return all(
            getattr(left, field) == getattr(right, field)
            for field in ("evidence_id", "document_id", "chunk_id", "page", "source_type")
        ) and " ".join(left.text.split()) == " ".join(right.text.split())

    def _fact_decision(self, risk: RiskItem) -> _ReviewDecision | None:
        """Business facts must stay consistent with the frozen rule inputs."""

        has_product_revenue = risk.metadata.get("has_product_revenue")
        if has_product_revenue is True:
            return self._reject(risk, "metadata_product_revenue_contradicts_risk")
        if has_product_revenue is not False:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Product sales revenue attribution is not deterministically false.",
            )
        product_name = str(risk.metadata.get("product_name") or "")
        stage = str(risk.metadata.get("development_stage") or "")
        if product_name.casefold() in {"", "unknown"}:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Core product identity is unclear.",
            )
        if stage.casefold() in {"", "unknown"}:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Core product development stage is unclear.",
            )
        sources = risk.metadata.get("revenue_source_types")
        if not isinstance(sources, list) or not all(
            isinstance(item, str) for item in sources
        ):
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Revenue source types metadata is not a string list.",
            )
        if not set(sources) <= _KNOWN_REVENUE_SOURCES:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Revenue source types contain an unsupported value.",
            )
        return None

    def _evidence_support_decision(self, risk: RiskItem) -> _ReviewDecision | None:
        """Both rule inputs must be literally supported by the Evidence text."""

        combined = normalize_business_text(" \n ".join(item.text for item in risk.evidence))
        not_commercialized = self._matches(combined, _NOT_COMMERCIALIZED)
        commercialized = self._matches(combined, _COMMERCIALIZED)
        no_product_revenue = self._matches(combined, _NO_PRODUCT_REVENUE)
        positive_text = combined
        for pattern in _NO_PRODUCT_REVENUE:
            positive_text = re.sub(pattern, " ", positive_text, flags=re.IGNORECASE)
        direct_product_revenue = self._matches(positive_text, _DIRECT_PRODUCT_REVENUE)

        if commercialized and not not_commercialized:
            return self._reject(risk, "evidence_shows_commercialization")
        if direct_product_revenue and not no_product_revenue:
            return self._reject(risk, "evidence_shows_direct_product_sales_revenue")
        if not not_commercialized or not no_product_revenue:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Evidence does not literally support both pre-commercial rule inputs.",
            )
        if not_commercialized and commercialized or no_product_revenue and direct_product_revenue:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Evidence contains conflicting commercialization or revenue statements.",
            )
        product_name = str(risk.metadata.get("product_name") or "")
        if product_name and product_name.casefold() not in combined:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Core product name does not appear in the Evidence text.",
            )
        return None

    def _conclusion_decision(self, risk: RiskItem) -> _ReviewDecision | None:
        lowered = risk.conclusion.casefold()
        if any(claim.casefold() in lowered for claim in _BANNED_CLAIMS):
            return self._reject(risk, "conclusion_contains_certainty_claim")
        product_name = str(risk.metadata.get("product_name") or "")
        if product_name and product_name.casefold() not in lowered:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Risk conclusion does not restate the core product identity.",
            )
        return None

    @staticmethod
    def _matches(text: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _pending(
        risk: RiskItem, status: VerificationStatus, note: str
    ) -> _ReviewDecision:
        return _ReviewDecision(
            "pending",
            risk.model_copy(
                update={"verification_status": status, "verification_notes": note}
            ),
        )

    @staticmethod
    def _reject(risk: RiskItem, issue: str) -> _ReviewDecision:
        return _ReviewDecision(
            "rejected",
            risk.model_copy(
                update={
                    "verification_status": VerificationStatus.REJECTED,
                    "verification_notes": f"Business verification rejected: {issue}",
                }
            ),
        )
