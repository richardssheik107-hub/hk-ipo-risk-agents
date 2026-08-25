"""Deterministic cross-agent conflict detection for the Final Supervisor lane.

A conflict is a *disagreement between two named producers*, never a restatement
of a single agent's own uncertainty.  Detection is deterministic and policy
versioned so the same run identity always yields the same conflict identities:
nothing here samples, scores or asks a model.

The detector reads only governed objects that other lanes already produced.  It
mints no risk, no evidence and no market fact; every id it emits is copied from
its input.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from ipo_risk.schemas import (
    ComponentDiagnostic,
    DiagnosticCode,
    PredictionResult,
    RiskItem,
    RiskLevel,
    SupervisionResult,
    VerificationStatus,
)
from ipo_risk.schemas.competition_runtime import CompetitionConflict
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView, ModelPredictionView


CONFLICT_POLICY_VERSION = "v04_e_conflict_policy_v1"

DOCUMENT_SUPERVISOR = "document_supervisor"
RULE_PREDICTOR = "rule_predictor"
MODEL_CHANNEL = "frozen_model_channel"
MARKET_INTELLIGENCE = "market_intelligence"
VERIFIER = "verifier"

RULE_AGENT_VERIFIER = "agent_verifier_disagreement"
RULE_DOCUMENT_RULE_SEVERITY = "document_rule_severity_divergence"
RULE_DOCUMENT_MARKET = "document_market_divergence"
RULE_DOCUMENT_MODEL = "document_model_divergence"
RULE_INTRA_DOCUMENT = "document_internal_conflict"
RULE_UNRESOLVED_CLAIM = "unresolved_agent_claim"

# Conflicts are ordered by rule, then by the ids they carry, so a re-run of the
# same case produces the same conflict list in the same order.
_RULE_ORDER = (
    RULE_AGENT_VERIFIER,
    RULE_UNRESOLVED_CLAIM,
    RULE_INTRA_DOCUMENT,
    RULE_DOCUMENT_RULE_SEVERITY,
    RULE_DOCUMENT_MARKET,
    RULE_DOCUMENT_MODEL,
)

_SEVERE_LEVELS = frozenset({RiskLevel.HIGH, RiskLevel.CRITICAL})
_UNSETTLED_STATUSES = frozenset({VerificationStatus.PENDING, VerificationStatus.NEEDS_REVIEW})
# Diagnostic codes where the agent held bounded Evidence but the document
# channel still asserts nothing about that risk code.
_UNRESOLVED_CODES = frozenset({DiagnosticCode.EXTRACTION_FAILED, DiagnosticCode.NEEDS_REVIEW,
                               DiagnosticCode.CONFLICTING_VALUES, DiagnosticCode.COMPONENT_FAILURE})


def _evidence_ids(risks: Iterable[RiskItem]) -> list[str]:
    return list(dict.fromkeys(item.evidence_id for risk in risks for item in risk.evidence))


def conflict_rule(conflict: CompetitionConflict) -> str:
    """Read back the detection rule a conflict was produced by."""

    for claim in conflict.claim_ids:
        if claim.startswith("rule:"):
            return claim.split(":", 1)[1]
    return ""


def _conflict_id(run_id: str, rule: str, discriminator: str) -> str:
    """Deterministic identity; a re-run of the same run_id reproduces it exactly."""

    return f"conflict:{run_id}:{rule}:{discriminator}"


class ConflictDetector:
    """Turn governed channel outputs into named, reproducible disagreements."""

    name = "conflict_detector"
    policy_version = CONFLICT_POLICY_VERSION

    def detect(
        self,
        *,
        case_id: str,
        run_id: str,
        document_supervision: SupervisionResult | None = None,
        unsettled_risks: Sequence[RiskItem] = (),
        agent_diagnostics: Sequence[tuple[str, ComponentDiagnostic]] = (),
        market_context: MarketContextView | None = None,
        model_prediction: ModelPredictionView | None = None,
        rule_prediction: PredictionResult | None = None,
    ) -> tuple[CompetitionConflict, ...]:
        conflicts: list[CompetitionConflict] = []
        verified = list(document_supervision.verified_risks) if document_supervision else []
        asserted_codes = {risk.risk_code for risk in verified} | {
            risk.risk_code for risk in unsettled_risks
        }

        conflicts.extend(self._agent_verifier(case_id, run_id, unsettled_risks))
        conflicts.extend(self._unresolved_claim(case_id, run_id, agent_diagnostics, asserted_codes))
        conflicts.extend(self._intra_document(case_id, run_id, document_supervision, verified))
        conflicts.extend(self._document_rule(case_id, run_id, verified, rule_prediction))
        conflicts.extend(self._document_market(case_id, run_id, verified, market_context))
        conflicts.extend(self._document_model(case_id, run_id, verified, model_prediction))

        order = {rule: index for index, rule in enumerate(_RULE_ORDER)}
        conflicts.sort(key=lambda item: (order[conflict_rule(item)], item.conflict_id))
        return tuple(conflicts)

    def _claims(self, rule: str, *extra: str) -> list[str]:
        return [f"policy:{self.policy_version}", f"rule:{rule}", *extra]

    def _agent_verifier(
        self, case_id: str, run_id: str, unsettled_risks: Sequence[RiskItem]
    ) -> list[CompetitionConflict]:
        """A producing agent asserted a risk the Verifier declined to verify."""

        grouped: dict[tuple[str, str], list[RiskItem]] = {}
        for risk in unsettled_risks:
            if risk.verification_status not in _UNSETTLED_STATUSES:
                continue
            if risk.agent_name == VERIFIER:
                continue
            grouped.setdefault((risk.agent_name, risk.risk_code), []).append(risk)

        conflicts = []
        for (agent_name, risk_code), risks in sorted(grouped.items()):
            risk_ids = sorted(risk.risk_id for risk in risks)
            statuses = sorted({risk.verification_status.value for risk in risks})
            conflicts.append(
                CompetitionConflict(
                    conflict_id=_conflict_id(run_id, RULE_AGENT_VERIFIER, f"{agent_name}:{risk_code}"),
                    case_id=case_id,
                    run_id=run_id,
                    involved_agents=[agent_name, VERIFIER],
                    risk_ids=risk_ids,
                    claim_ids=self._claims(RULE_AGENT_VERIFIER, f"risk_code:{risk_code}"),
                    summary=(
                        f"{agent_name} produced {len(risks)} {risk_code} risk item(s) that the Verifier left "
                        f"as {'/'.join(statuses)}; the assertion and its verification disagree."
                    ),
                    evidence_ids=_evidence_ids(risks),
                )
            )
        return conflicts

    def _unresolved_claim(
        self,
        case_id: str,
        run_id: str,
        agent_diagnostics: Sequence[tuple[str, ComponentDiagnostic]],
        asserted_codes: set[str],
    ) -> list[CompetitionConflict]:
        """The agent retrieved Evidence for a risk code the document channel never asserts.

        This is the coverage disagreement the competition chain has to surface:
        bounded Evidence exists, but extraction or the deterministic decision could
        not settle it, so nothing about that risk code reaches the final report.
        Naming it makes the gap reviewable instead of invisible.
        """

        conflicts = []
        seen: set[tuple[str, str]] = set()
        for agent_name, diagnostic in agent_diagnostics:
            if diagnostic.code not in _UNRESOLVED_CODES:
                continue
            if not diagnostic.evidence_ids:
                continue
            if diagnostic.risk_code in asserted_codes:
                continue
            key = (agent_name, diagnostic.risk_code)
            if key in seen:
                continue
            seen.add(key)
            conflicts.append(
                CompetitionConflict(
                    conflict_id=_conflict_id(run_id, RULE_UNRESOLVED_CLAIM, f"{agent_name}:{diagnostic.risk_code}"),
                    case_id=case_id,
                    run_id=run_id,
                    involved_agents=sorted({agent_name, DOCUMENT_SUPERVISOR}),
                    risk_ids=[],
                    claim_ids=self._claims(
                        RULE_UNRESOLVED_CLAIM,
                        f"risk_code:{diagnostic.risk_code}",
                        f"diagnostic_code:{diagnostic.code.value}",
                    ),
                    summary=(
                        f"{agent_name} held {len(diagnostic.evidence_ids)} bounded Evidence item(s) for "
                        f"{diagnostic.risk_code} and reported {diagnostic.code.value}, while the document "
                        f"channel asserts nothing about {diagnostic.risk_code}: {diagnostic.message}"
                    ),
                    evidence_ids=list(dict.fromkeys(diagnostic.evidence_ids)),
                )
            )
        return conflicts

    def _intra_document(
        self,
        case_id: str,
        run_id: str,
        document_supervision: SupervisionResult | None,
        verified: Sequence[RiskItem],
    ) -> list[CompetitionConflict]:
        """Lift a Document Supervisor conflict to the cross-lane contract verbatim."""

        if document_supervision is None:
            return []
        by_id = {risk.risk_id: risk for risk in verified}
        conflicts = []
        for index, conflict in enumerate(document_supervision.conflicts):
            agents = sorted({by_id[risk_id].agent_name for risk_id in conflict.risk_ids if risk_id in by_id})
            # A conflict contract needs two named producers; a single-producer
            # inconsistency is reported against the Supervisor that observed it.
            if len(agents) < 2:
                agents = sorted({*agents, DOCUMENT_SUPERVISOR})
            if len(agents) < 2:
                continue
            conflicts.append(
                CompetitionConflict(
                    conflict_id=_conflict_id(run_id, RULE_INTRA_DOCUMENT, f"{conflict.risk_code}:{index}"),
                    case_id=case_id,
                    run_id=run_id,
                    involved_agents=agents,
                    risk_ids=list(conflict.risk_ids),
                    claim_ids=self._claims(RULE_INTRA_DOCUMENT, f"risk_code:{conflict.risk_code}"),
                    summary=f"Document Supervisor recorded a {conflict.risk_code} conflict: {conflict.description}",
                    evidence_ids=list(conflict.evidence_ids),
                )
            )
        return conflicts

    def _document_rule(
        self,
        case_id: str,
        run_id: str,
        verified: Sequence[RiskItem],
        rule_prediction: PredictionResult | None,
    ) -> list[CompetitionConflict]:
        if rule_prediction is None:
            return []
        severe = sorted(risk.risk_id for risk in verified if risk.level in _SEVERE_LEVELS)
        if not severe or rule_prediction.risk_level not in {RiskLevel.LOW}:
            return []
        return [
            CompetitionConflict(
                conflict_id=_conflict_id(run_id, RULE_DOCUMENT_RULE_SEVERITY, "severity"),
                case_id=case_id,
                run_id=run_id,
                involved_agents=[DOCUMENT_SUPERVISOR, RULE_PREDICTOR],
                risk_ids=severe,
                claim_ids=self._claims(
                    RULE_DOCUMENT_RULE_SEVERITY, f"rule_risk_level:{rule_prediction.risk_level.value}"
                ),
                summary=(
                    f"{len(severe)} verified document risk(s) are high or critical while the deterministic "
                    f"rule score reports {rule_prediction.risk_level.value}."
                ),
                evidence_ids=_evidence_ids(risk for risk in verified if risk.risk_id in set(severe)),
            )
        ]

    def _document_market(
        self,
        case_id: str,
        run_id: str,
        verified: Sequence[RiskItem],
        market_context: MarketContextView | None,
    ) -> list[CompetitionConflict]:
        """Market-side risk and document-side risk point in opposite directions."""

        if market_context is None or market_context.status is not ChannelStatus.AVAILABLE:
            return []
        intelligence: dict[str, Any] = market_context.provenance.get("market_intelligence") or {}
        market_risk = str(intelligence.get("risk_level") or "")
        if market_risk not in {"high", "low"}:
            return []
        severe = sorted(risk.risk_id for risk in verified if risk.level in _SEVERE_LEVELS)
        if market_risk == "high" and severe:
            return []
        if market_risk == "low" and not severe:
            return []
        document_side = "no high or critical verified document risk" if market_risk == "high" else (
            f"{len(severe)} high or critical verified document risk(s)"
        )
        return [
            CompetitionConflict(
                conflict_id=_conflict_id(run_id, RULE_DOCUMENT_MARKET, market_risk),
                case_id=case_id,
                run_id=run_id,
                involved_agents=[DOCUMENT_SUPERVISOR, MARKET_INTELLIGENCE],
                risk_ids=severe,
                claim_ids=self._claims(RULE_DOCUMENT_MARKET, f"market_risk_level:{market_risk}"),
                summary=(
                    f"Governed market-side risk is {market_risk} while the document channel reports "
                    f"{document_side}; the two channels disagree on direction."
                ),
                evidence_ids=[
                    f"market_feature:{item.name}"
                    for item in market_context.observations
                    if item.availability == "available"
                ],
            )
        ]

    def _document_model(
        self,
        case_id: str,
        run_id: str,
        verified: Sequence[RiskItem],
        model_prediction: ModelPredictionView | None,
    ) -> list[CompetitionConflict]:
        """Signed frozen SHAP drivers point against the document severity.

        The frozen score is uncalibrated, so only the *direction* of its top
        driver is compared.  No threshold on the score itself is invented here.
        """

        if model_prediction is None or model_prediction.status is not ChannelStatus.AVAILABLE:
            return []
        if not model_prediction.drivers:
            return []
        severe = sorted(risk.risk_id for risk in verified if risk.level in _SEVERE_LEVELS)
        top = max(model_prediction.drivers, key=lambda driver: (abs(driver.shap_value), driver.feature))
        if bool(severe) == (top.direction == "increases"):
            return []
        document_side = (
            f"{len(severe)} high or critical verified document risk(s)" if severe
            else "no high or critical verified document risk"
        )
        return [
            CompetitionConflict(
                conflict_id=_conflict_id(run_id, RULE_DOCUMENT_MODEL, top.feature),
                case_id=case_id,
                run_id=run_id,
                involved_agents=[DOCUMENT_SUPERVISOR, MODEL_CHANNEL],
                risk_ids=severe,
                claim_ids=self._claims(
                    RULE_DOCUMENT_MODEL,
                    f"model_feature:{top.feature}",
                    f"model_driver_direction:{top.direction}",
                ),
                summary=(
                    f"The frozen model's strongest driver {top.feature} {top.direction} risk while the document "
                    f"channel reports {document_side}; the uncalibrated score direction disagrees with the document."
                ),
                evidence_ids=[],
            )
        ]
