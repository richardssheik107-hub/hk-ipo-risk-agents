from collections import defaultdict

from ipo_risk.domain.cash_runway_verifier import (
    CashRunwayRiskVerifier,
    CashRunwayVerificationStatus,
)
from ipo_risk.domain.risk_codes import requirement_for
from ipo_risk.schemas import Evidence, RiskItem, SupervisionResult, VerificationResult, VerificationStatus

class RuleVerifier:
    name = "verifier"
    def __init__(self, cash_runway_verifier: CashRunwayRiskVerifier | None = None):
        self.cash_runway_verifier = cash_runway_verifier or CashRunwayRiskVerifier()

    def verify(self, risks: list[RiskItem], evidence_by_code: dict[str, list[Evidence]]) -> VerificationResult:
        verified, pending, rejected = [], [], []
        for risk in risks:
            external_evidence = evidence_by_code.get(risk.risk_code, [])
            if risk.risk_code == "cash_runway":
                available = {item.evidence_id: item for item in risk.evidence}
                for item in external_evidence:
                    available[item.evidence_id] = item
                outcome = self.cash_runway_verifier.verify(risk, available)
                if outcome.status == CashRunwayVerificationStatus.VERIFIED:
                    verified.append(outcome.verified_risk)
                else:
                    pending.append(outcome.reviewed_risk)
                continue

            selected_evidence = external_evidence or risk.evidence
            item = risk.model_copy(update={"evidence": selected_evidence})
            requirement = requirement_for(item.risk_code)
            evidence_ids = {evidence.evidence_id for evidence in item.evidence}
            calculation_ok = item.calculation and item.calculation.success and set(item.calculation.evidence_ids).issubset(evidence_ids)
            if requirement.requires_evidence and not item.evidence:
                pending.append(item.model_copy(update={"verification_status": VerificationStatus.PENDING, "verification_notes": "No supporting evidence."}))
            elif requirement.requires_calculation and not calculation_ok:
                pending.append(item.model_copy(update={"verification_status": VerificationStatus.NEEDS_REVIEW, "verification_notes": "Required calculation is missing, failed, or references unavailable evidence."}))
            elif item.score > 95:
                rejected.append(item.model_copy(update={"verification_status": VerificationStatus.REJECTED, "verification_notes": "Rule rejected implausible score."}))
            else:
                verified.append(item.model_copy(update={"verification_status": VerificationStatus.VERIFIED, "verification_notes": "Evidence and score passed deterministic checks."}))
        return VerificationResult(verified_risks=verified, pending_risks=pending, rejected_risks=rejected)

class RuleSupervisor:
    name = "supervisor"
    def supervise(self, risks: list[RiskItem]) -> SupervisionResult:
        groups: dict[tuple[str, str], list[RiskItem]] = defaultdict(list)
        for risk in risks: groups[(risk.risk_code, risk.category)].append(risk)
        merged = []
        for values in groups.values():
            best = max(values, key=lambda x: x.score)
            seen, evidence = set(), []
            for item in values:
                for item_evidence in item.evidence:
                    if item_evidence.evidence_id not in seen: seen.add(item_evidence.evidence_id); evidence.append(item_evidence)
            merged.append(best.model_copy(update={"evidence": evidence, "metadata": {**best.metadata, "merged_count": len(values)}}))
        return SupervisionResult(verified_risks=merged, summary=f"Merged {len(risks)} risks into {len(merged)} risks.")
