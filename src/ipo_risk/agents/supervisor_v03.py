"""Cross-domain deduplication and conservative conflict handling for v0.3."""

from __future__ import annotations

from collections import defaultdict

from ipo_risk.schemas import (
    CompositeFinding,
    DuplicateRiskGroup,
    RiskConflict,
    RiskItem,
    SupervisionResult,
    VerificationStatus,
)


class V03Supervisor:
    """Merge duplicates and report cross-domain facts without inventing certainty."""

    name = "v03"

    def supervise(self, risks: list[RiskItem]) -> SupervisionResult:
        groups: dict[tuple[str, str], list[RiskItem]] = defaultdict(list)
        for risk in risks:
            groups[(risk.risk_code, str(risk.category))].append(risk)

        merged: list[RiskItem] = []
        duplicates: list[DuplicateRiskGroup] = []
        for (_, _), values in groups.items():
            best = max(values, key=lambda item: (float(item.score), item.risk_id))
            evidence = {item.evidence_id: item for risk in values for item in risk.evidence}
            kept = best.model_copy(
                update={
                    "evidence": list(evidence.values()),
                    "metadata": {
                        **best.metadata,
                        "supervisor_merged_count": len(values),
                        "supervisor_source_risk_ids": [item.risk_id for item in values],
                    },
                }
            )
            merged.append(kept)
            if len(values) > 1:
                duplicates.append(
                    DuplicateRiskGroup(
                        risk_code=best.risk_code,
                        source_risk_ids=[item.risk_id for item in values],
                        kept_risk_id=best.risk_id,
                        reason="Same risk code and category; kept the highest rule score and unioned Evidence.",
                    )
                )

        conflicts, findings = self._revenue_semantics(merged)
        findings.extend(self._cross_domain_observations(merged))
        verified = [
            risk for risk in merged if risk.verification_status == VerificationStatus.VERIFIED
        ]
        return SupervisionResult(
            verified_risks=verified,
            summary=(
                f"Supervised {len(risks)} risks into {len(merged)} unique risks; "
                f"{len(conflicts)} unresolved conflict(s) and "
                f"{len(findings)} supervisory finding(s)."
            ),
            duplicate_groups=duplicates,
            conflicts=conflicts,
            composite_findings=findings,
            metadata={
                "input_count": len(risks),
                "unique_count": len(merged),
                "verified_count": len(verified),
                "pending_count": sum(
                    risk.verification_status
                    in {VerificationStatus.PENDING, VerificationStatus.NEEDS_REVIEW}
                    for risk in merged
                ),
                "rejected_count": sum(
                    risk.verification_status == VerificationStatus.REJECTED
                    for risk in merged
                ),
                "rule_score_components": [
                    {
                        "risk_code": risk.risk_code,
                        "domain": risk.category.value,
                        "score": risk.score,
                        "level": risk.level.value,
                        "verification_status": risk.verification_status.value,
                    }
                    for risk in verified
                ],
                "excluded_non_verified_risk_ids": [
                    risk.risk_id
                    for risk in merged
                    if risk.verification_status != VerificationStatus.VERIFIED
                ],
            },
        )

    @staticmethod
    def _cross_domain_observations(risks: list[RiskItem]) -> list[CompositeFinding]:
        financial = [
            risk
            for risk in risks
            if risk.category.value == "financial"
            and risk.verification_status != VerificationStatus.REJECTED
        ]
        business = [
            risk
            for risk in risks
            if risk.risk_code == "precommercial_product"
            and risk.verification_status != VerificationStatus.REJECTED
        ]
        if not financial or not business:
            return []
        related = [risk.risk_id for risk in [*financial, *business]]
        return [
            CompositeFinding(
                finding_code="financial_business_execution_risk_coexistence",
                related_risk_ids=related,
                summary=(
                    "Financial pressure and commercialization uncertainty coexist and may "
                    "amplify execution risk. This is supervisory synthesis, not a new "
                    "verified risk or probability."
                ),
                evidence_ids=list(
                    dict.fromkeys(
                        evidence.evidence_id
                        for risk in [*financial, *business]
                        for evidence in risk.evidence
                    )
                ),
                metadata={"classification": "SUPERVISORY_SYNTHESIS"},
            )
        ]

    @staticmethod
    def _revenue_semantics(
        risks: list[RiskItem],
    ) -> tuple[list[RiskConflict], list[CompositeFinding]]:
        financial = [item for item in risks if item.risk_code == "revenue_growth"]
        business = [item for item in risks if item.risk_code == "precommercial_product"]
        if not financial or not business:
            return [], []
        related = [item.risk_id for item in [*financial, *business]]
        evidence_ids = list(
            dict.fromkeys(
                evidence.evidence_id
                for item in [*financial, *business]
                for evidence in item.evidence
            )
        )
        has_product_sales = any(
            item.metadata.get("has_product_revenue") is True for item in business
        )
        if has_product_sales:
            return [
                RiskConflict(
                    risk_code="revenue_semantics",
                    risk_ids=related,
                    description=(
                        "Business metadata reports product-sales revenue while a "
                        "pre-commercial candidate remains present; human review is required."
                    ),
                    evidence_ids=evidence_ids,
                )
            ], []
        return [], [
            CompositeFinding(
                finding_code="revenue_semantics_distinguished",
                related_risk_ids=related,
                summary=(
                    "Financial revenue and Business product-sales revenue are different "
                    "concepts; no conflict was inferred from generic or non-product revenue."
                ),
                evidence_ids=evidence_ids,
                metadata={"classification": "NO_CONFLICT_DIFFERENT_REVENUE_SEMANTICS"},
            )
        ]
