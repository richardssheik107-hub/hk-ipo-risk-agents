"""Failure-isolated routing across the frozen v0.3 professional verifiers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ipo_risk.domain.risk_codes import V03_RISK_OWNERS
from ipo_risk.schemas import Evidence, RiskItem, VerificationResult, VerificationStatus


class SpecializedVerifierRouter:
    """Route each candidate to its owning verifier without cross-domain failure."""

    name = "specialized_v03"

    def __init__(
        self,
        *,
        financial_verifier: Any,
        legal_rights_verifier: Any,
        litigation_verifier: Any,
        business_verifier: Any,
    ) -> None:
        self.financial_verifier = financial_verifier
        self.legal_rights_verifier = legal_rights_verifier
        self.litigation_verifier = litigation_verifier
        self.business_verifier = business_verifier
        self.last_diagnostics: dict[str, Any] = {}

    def verify(
        self,
        risks: list[RiskItem],
        evidence_by_code: dict[str, list[Evidence]],
    ) -> VerificationResult:
        """Return exactly one safe classification for each input candidate."""

        grouped: dict[str, list[RiskItem]] = defaultdict(list)
        for risk in risks:
            grouped[V03_RISK_OWNERS.get(risk.risk_code, "unsupported")].append(risk)

        verified: list[RiskItem] = []
        pending: list[RiskItem] = []
        rejected: list[RiskItem] = []
        diagnostics: dict[str, Any] = {}

        self._verify_batch(
            "financial",
            grouped.get("financial", []),
            self.financial_verifier,
            evidence_by_code,
            verified,
            pending,
            rejected,
            diagnostics,
        )
        self._verify_batch(
            "business",
            grouped.get("business", []),
            self.business_verifier,
            evidence_by_code,
            verified,
            pending,
            rejected,
            diagnostics,
        )

        legal_items = grouped.get("legal", [])
        legal_counts = {"verified": 0, "pending": 0, "rejected": 0, "failed": 0}
        for risk in legal_items:
            verifier = {
                "redemption_rights": self.legal_rights_verifier,
                "material_litigation_compliance": self.litigation_verifier,
            }.get(risk.risk_code)
            if verifier is None:
                pending.append(self._pending(risk, "No specialized Legal verifier is registered."))
                legal_counts["pending"] += 1
                continue
            available = {item.evidence_id: item for item in risk.evidence}
            for item in evidence_by_code.get(risk.risk_code, []):
                available[item.evidence_id] = item
            try:
                result = verifier.verify(risk, available)
                reviewed = result.reviewed_risk
                if result.status == VerificationStatus.VERIFIED:
                    verified.append(result.verified_risk or reviewed)
                    legal_counts["verified"] += 1
                elif result.status == VerificationStatus.REJECTED:
                    rejected.append(reviewed)
                    legal_counts["rejected"] += 1
                else:
                    pending.append(reviewed)
                    legal_counts["pending"] += 1
            except Exception as exc:  # component boundary; never hides the failure
                pending.append(
                    self._pending(
                        risk,
                        f"Legal verifier failed safely: {type(exc).__name__}.",
                    )
                )
                legal_counts["failed"] += 1
        diagnostics["legal"] = legal_counts

        unsupported = grouped.get("unsupported", [])
        pending.extend(
            self._pending(risk, "Risk code has no frozen v0.3 verifier owner.")
            for risk in unsupported
        )
        diagnostics["unsupported"] = {"pending": len(unsupported)}
        diagnostics["input_count"] = len(risks)
        diagnostics["output_count"] = len(verified) + len(pending) + len(rejected)
        self.last_diagnostics = diagnostics
        return VerificationResult(
            verified_risks=verified,
            pending_risks=pending,
            rejected_risks=rejected,
        )

    def _verify_batch(
        self,
        domain: str,
        risks: list[RiskItem],
        verifier: Any,
        evidence_by_code: dict[str, list[Evidence]],
        verified: list[RiskItem],
        pending: list[RiskItem],
        rejected: list[RiskItem],
        diagnostics: dict[str, Any],
    ) -> None:
        if not risks:
            diagnostics[domain] = {"input": 0, "failed": False}
            return
        try:
            result = verifier.verify(risks, evidence_by_code)
            verified.extend(result.verified_risks)
            pending.extend(result.pending_risks)
            rejected.extend(result.rejected_risks)
            diagnostics[domain] = {
                "input": len(risks),
                "verified": len(result.verified_risks),
                "pending": len(result.pending_risks),
                "rejected": len(result.rejected_risks),
                "failed": False,
            }
        except Exception as exc:  # component boundary; candidates remain reviewable
            pending.extend(
                self._pending(
                    risk,
                    f"{domain.title()} verifier failed safely: {type(exc).__name__}.",
                )
                for risk in risks
            )
            diagnostics[domain] = {
                "input": len(risks),
                "failed": True,
                "error_type": type(exc).__name__,
            }

    @staticmethod
    def _pending(risk: RiskItem, note: str) -> RiskItem:
        return risk.model_copy(
            update={
                "verification_status": VerificationStatus.NEEDS_REVIEW,
                "verification_notes": note,
            }
        )
