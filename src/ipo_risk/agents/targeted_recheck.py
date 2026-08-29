"""One controlled, targeted re-check per conflict -- never an autonomous loop.

The runner re-retrieves evidence for exactly the risk codes named by a conflict
and asks the existing Verifier to rule again on the enlarged evidence set. It
adds no risk, rewrites no verdict by hand, and stops after a single attempt:
``RecheckRequest.max_attempts`` is pinned to 1 by the public contract, and this
runner never issues a second request for the same conflict.

A conflict that no document re-retrieval can settle -- a market, model or rule
divergence -- is reported ``unresolved`` with the reason. Such cross-channel
conflicts are still recorded as outcomes, but they do not consume the bounded
document re-check budget reserved for conflicts that can actually benefit from
re-retrieval.
"""

from __future__ import annotations

from time import perf_counter
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.agents.conflict_detection import (
    RULE_AGENT_VERIFIER,
    RULE_INTRA_DOCUMENT,
    RULE_UNRESOLVED_CLAIM,
    conflict_rule,
)
from ipo_risk.schemas import DocumentChunk, Evidence, RiskItem
from ipo_risk.schemas.competition_runtime import (
    CompetitionConflict,
    ConflictStatus,
    RecheckRequest,
    RecheckStatus,
    TraceEvent,
    TraceEventType,
)


RECHECK_POLICY_VERSION = "v04_e_recheck_policy_v2"
RECHECK_AGENT = "targeted_recheck"

_DOCUMENT_RULES = frozenset({RULE_AGENT_VERIFIER, RULE_INTRA_DOCUMENT, RULE_UNRESOLVED_CLAIM})


class RecheckOutcome(BaseModel):
    """What one controlled re-check actually changed, stated in full."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request: RecheckRequest
    conflict_id: str
    status: ConflictStatus
    resolution_note: str = Field(min_length=1)
    new_evidence_ids: tuple[str, ...] = ()
    revised_risk_ids: tuple[str, ...] = ()
    trace_events: tuple[TraceEvent, ...] = ()


class TargetedRecheckRunner:
    """Re-retrieve, re-verify once, and report the result honestly."""

    name = RECHECK_AGENT
    policy_version = RECHECK_POLICY_VERSION

    def __init__(self, retriever=None, verifier=None, *, evidence_limit: int = 5, max_conflicts: int = 12) -> None:
        self.retriever = retriever
        self.verifier = verifier
        self.evidence_limit = evidence_limit
        # Submission-sprint default: allow a normal current case to re-check all
        # actionable document conflicts while remaining bounded. Cross-channel
        # conflicts that document retrieval cannot settle do not consume this budget.
        self.max_conflicts = max_conflicts

    def run(
        self,
        conflicts: Sequence[CompetitionConflict],
        *,
        case_id: str,
        run_id: str,
        chunks: Sequence[DocumentChunk] = (),
        risks: Sequence[RiskItem] = (),
    ) -> tuple[tuple[CompetitionConflict, ...], tuple[RecheckOutcome, ...]]:
        """Return conflicts with updated status plus one outcome per processed conflict."""

        risks_by_id = {risk.risk_id: risk for risk in risks}
        updated: list[CompetitionConflict] = []
        outcomes: list[RecheckOutcome] = []
        attempted_actionable = 0
        for conflict in conflicts:
            rule = conflict_rule(conflict)

            # Market/model/rule disagreements cannot be settled by document
            # re-retrieval. Record the honest not-actionable outcome without
            # spending a document-recheck slot that a Financial/Legal/Business
            # coverage conflict can use.
            if rule not in _DOCUMENT_RULES:
                outcome = self._recheck(
                    conflict,
                    case_id=case_id,
                    run_id=run_id,
                    chunks=chunks,
                    risks_by_id=risks_by_id,
                )
                outcomes.append(outcome)
                updated.append(
                    conflict.model_copy(
                        update={"status": outcome.status, "resolution_note": outcome.resolution_note}
                    )
                )
                continue

            if attempted_actionable >= self.max_conflicts:
                updated.append(
                    conflict.model_copy(
                        update={
                            "status": ConflictStatus.UNRESOLVED,
                            "resolution_note": (
                                "not attempted: the controlled document re-check budget of "
                                f"{self.max_conflicts} actionable conflict(s) for this run was already used"
                            ),
                        }
                    )
                )
                continue

            attempted_actionable += 1
            outcome = self._recheck(
                conflict,
                case_id=case_id,
                run_id=run_id,
                chunks=chunks,
                risks_by_id=risks_by_id,
            )
            outcomes.append(outcome)
            updated.append(
                conflict.model_copy(
                    update={"status": outcome.status, "resolution_note": outcome.resolution_note}
                )
            )
        return tuple(updated), tuple(outcomes)

    def _recheck(
        self,
        conflict: CompetitionConflict,
        *,
        case_id: str,
        run_id: str,
        chunks: Sequence[DocumentChunk],
        risks_by_id: dict[str, RiskItem],
    ) -> RecheckOutcome:
        targets = self._targets(conflict, risks_by_id)
        request = RecheckRequest(
            recheck_id=f"recheck:{conflict.conflict_id}",
            conflict_id=conflict.conflict_id,
            case_id=case_id,
            run_id=run_id,
            requested_by="final_supervisor",
            targets=targets,
            reason=conflict.summary,
            evidence_ids=list(conflict.evidence_ids),
            max_attempts=1,
        )
        rule = conflict_rule(conflict)
        if rule not in _DOCUMENT_RULES:
            return self._not_actionable(request, conflict, case_id, run_id, rule)
        if self.retriever is None or not chunks:
            return self._not_actionable(
                request, conflict, case_id, run_id, rule,
                note="no retriever or parsed document is available for a targeted re-check",
            )
        if rule == RULE_UNRESOLVED_CLAIM:
            return self._coverage_recheck(request, conflict, case_id, run_id, chunks)
        risks = [risks_by_id[risk_id] for risk_id in conflict.risk_ids if risk_id in risks_by_id]
        if not risks:
            return self._not_actionable(
                request, conflict, case_id, run_id, rule,
                note="the conflicting risk items are not present in this run's risk set",
            )
        if self.retriever is None or self.verifier is None or not chunks:
            return self._not_actionable(
                request, conflict, case_id, run_id, rule,
                note="no retriever, verifier or parsed document is available for a targeted re-check",
            )
        return self._document_recheck(request, conflict, case_id, run_id, chunks, risks)

    def _document_recheck(
        self,
        request: RecheckRequest,
        conflict: CompetitionConflict,
        case_id: str,
        run_id: str,
        chunks: Sequence[DocumentChunk],
        risks: list[RiskItem],
    ) -> RecheckOutcome:
        trace: list[TraceEvent] = []
        started = perf_counter()
        known = {item.evidence_id for risk in risks for item in risk.evidence}
        retrieved: dict[str, list[Evidence]] = {}
        errors: list[str] = []
        for risk_code in sorted({risk.risk_code for risk in risks}):
            try:
                found = self._retrieve(chunks, risk_code)
            except Exception as exc:  # a degraded retriever must not erase the conflict
                errors.append(f"{risk_code}: {type(exc).__name__}")
                found = []
            retrieved[risk_code] = found
        new_evidence = tuple(
            dict.fromkeys(
                item.evidence_id
                for found in retrieved.values()
                for item in found
                if item.evidence_id not in known
            )
        )
        trace.append(
            TraceEvent(
                event_id=f"trace:{request.recheck_id}:retrieve",
                case_id=case_id, run_id=run_id, event_type=TraceEventType.RETRIEVER,
                status="completed" if not errors else "partial",
                agent_name=self.name, action="targeted_re_retrieval",
                tool_or_skill=getattr(self.retriever, "name", type(self.retriever).__name__),
                evidence_ids=list(new_evidence), conflict_id=conflict.conflict_id,
                recheck_id=request.recheck_id,
                latency_ms=max(0, int((perf_counter() - started) * 1000)),
                details={
                    "risk_codes": sorted(retrieved),
                    "retrieved_counts": {code: len(found) for code, found in sorted(retrieved.items())},
                    "new_evidence_count": len(new_evidence),
                    "retriever_errors": errors,
                    "policy_version": self.policy_version,
                },
            )
        )

        evidence_by_code: dict[str, list[Evidence]] = {}
        for risk in risks:
            merged = {item.evidence_id: item for item in risk.evidence}
            for item in retrieved.get(risk.risk_code, []):
                merged.setdefault(item.evidence_id, item)
            evidence_by_code.setdefault(risk.risk_code, [])
            for item in merged.values():
                if all(existing.evidence_id != item.evidence_id for existing in evidence_by_code[risk.risk_code]):
                    evidence_by_code[risk.risk_code].append(item)

        challenged = [
            risk.model_copy(update={"evidence": evidence_by_code.get(risk.risk_code, list(risk.evidence))})
            for risk in risks
        ]
        verifier_started = perf_counter()
        try:
            result = self.verifier.verify(challenged, evidence_by_code)
            verifier_status = "completed"
            verified_ids = {risk.risk_id for risk in result.verified_risks}
            rejected_ids = {risk.risk_id for risk in result.rejected_risks}
            verifier_error = ""
        except Exception as exc:
            verifier_status = "failed"
            verified_ids, rejected_ids = set(), set()
            verifier_error = f"{type(exc).__name__}: {exc}"

        settled = sorted(verified_ids | rejected_ids)
        trace.append(
            TraceEvent(
                event_id=f"trace:{request.recheck_id}:verify",
                case_id=case_id, run_id=run_id, event_type=TraceEventType.VERIFIER,
                status=verifier_status, agent_name=self.name, action="verifier_challenge",
                tool_or_skill=getattr(self.verifier, "name", type(self.verifier).__name__),
                evidence_ids=sorted({item.evidence_id for items in evidence_by_code.values() for item in items}),
                conflict_id=conflict.conflict_id, recheck_id=request.recheck_id,
                latency_ms=max(0, int((perf_counter() - verifier_started) * 1000)),
                details={
                    "challenged_risk_ids": sorted(risk.risk_id for risk in challenged),
                    "settled_risk_ids": settled,
                    "verified_risk_ids": sorted(verified_ids),
                    "rejected_risk_ids": sorted(rejected_ids),
                    "error": verifier_error,
                    "policy_version": self.policy_version,
                },
            )
        )

        if verifier_status == "failed":
            status = ConflictStatus.UNRESOLVED
            note = f"the targeted re-check could not complete: the Verifier failed ({verifier_error})"
        elif settled and len(settled) == len(risks):
            status = ConflictStatus.RESOLVED
            note = (
                f"targeted re-retrieval added {len(new_evidence)} new evidence item(s) and the Verifier "
                f"settled all {len(risks)} challenged risk item(s)"
            )
        elif settled or new_evidence:
            status = ConflictStatus.PARTIALLY_RESOLVED
            note = (
                f"targeted re-retrieval added {len(new_evidence)} new evidence item(s); the Verifier settled "
                f"{len(settled)} of {len(risks)} challenged risk item(s) and the rest remain unsettled"
            )
        else:
            status = ConflictStatus.UNRESOLVED
            note = (
                "targeted re-retrieval found no evidence beyond what the agent already used and the Verifier "
                "did not change its ruling"
            )
        return RecheckOutcome(
            request=request.model_copy(update={"status": RecheckStatus.COMPLETED}),
            conflict_id=conflict.conflict_id,
            status=status,
            resolution_note=note,
            new_evidence_ids=new_evidence,
            revised_risk_ids=tuple(settled),
            trace_events=tuple(trace),
        )

    def _coverage_recheck(
        self,
        request: RecheckRequest,
        conflict: CompetitionConflict,
        case_id: str,
        run_id: str,
        chunks: Sequence[DocumentChunk],
    ) -> RecheckOutcome:
        """Separate a retrieval gap from an extraction gap, and say which it is.

        There is no risk item to re-verify here: the agent produced none. What a
        controlled re-check can establish is whether additional in-scope Evidence
        exists that the agent did not use. If it does, the gap is at least partly
        retrieval and the new Evidence is handed to the reviewer; if it does not,
        the gap is in extraction, and saying so is more useful than a silent
        unresolved.
        """

        started = perf_counter()
        known = set(conflict.evidence_ids)
        risk_codes = sorted(request.targets)
        retrieved: dict[str, list[Evidence]] = {}
        errors: list[str] = []
        for risk_code in risk_codes:
            try:
                retrieved[risk_code] = self._retrieve(chunks, risk_code)
            except Exception as exc:
                errors.append(f"{risk_code}: {type(exc).__name__}")
                retrieved[risk_code] = []
        new_evidence = tuple(
            dict.fromkeys(
                item.evidence_id
                for found in retrieved.values()
                for item in found
                if item.evidence_id not in known
            )
        )
        if errors:
            status = ConflictStatus.UNRESOLVED
            note = f"the targeted re-retrieval degraded and could not complete: {'; '.join(errors)}"
        elif new_evidence:
            status = ConflictStatus.PARTIALLY_RESOLVED
            note = (
                f"targeted re-retrieval surfaced {len(new_evidence)} in-scope Evidence item(s) the agent did "
                "not use, so the gap is at least partly retrieval; the machine still asserts no risk for this "
                "code and the new Evidence is routed to human review"
            )
        else:
            status = ConflictStatus.UNRESOLVED
            note = (
                "targeted re-retrieval found no in-scope Evidence beyond what the agent already held, so the "
                "gap is in extraction rather than retrieval; the machine asserts no risk for this code"
            )
        return RecheckOutcome(
            request=request.model_copy(update={"status": RecheckStatus.COMPLETED}),
            conflict_id=conflict.conflict_id,
            status=status,
            resolution_note=note,
            new_evidence_ids=new_evidence,
            trace_events=(
                TraceEvent(
                    event_id=f"trace:{request.recheck_id}:coverage",
                    case_id=case_id, run_id=run_id, event_type=TraceEventType.RETRIEVER,
                    status="completed" if not errors else "partial",
                    agent_name=self.name, action="targeted_coverage_re_retrieval",
                    tool_or_skill=getattr(self.retriever, "name", type(self.retriever).__name__),
                    evidence_ids=list(new_evidence), conflict_id=conflict.conflict_id,
                    recheck_id=request.recheck_id,
                    latency_ms=max(0, int((perf_counter() - started) * 1000)),
                    details={
                        "risk_codes": risk_codes,
                        "retrieved_counts": {code: len(found) for code, found in sorted(retrieved.items())},
                        "agent_evidence_count": len(known),
                        "new_evidence_count": len(new_evidence),
                        "gap_classification": (
                            "retrieval_gap" if new_evidence else "extraction_gap"
                        ) if not errors else "undetermined",
                        "retriever_errors": errors,
                        "policy_version": self.policy_version,
                        "no_evidence_reason": (
                            "" if new_evidence else
                            "the re-retrieval returned nothing beyond the Evidence the agent already held"
                        ),
                    },
                ),
            ),
        )

    def _retrieve(self, chunks: Sequence[DocumentChunk], risk_code: str) -> list[Evidence]:
        """Prefer the risk-aware entry point when the configured retriever has one."""

        retrieve_for_risk = getattr(self.retriever, "retrieve_for_risk", None)
        if callable(retrieve_for_risk):
            return list(retrieve_for_risk(list(chunks), risk_code, limit=self.evidence_limit))
        return list(self.retriever.retrieve(list(chunks), risk_code, self.evidence_limit))

    def _not_actionable(
        self,
        request: RecheckRequest,
        conflict: CompetitionConflict,
        case_id: str,
        run_id: str,
        rule: str,
        note: str = "",
    ) -> RecheckOutcome:
        reason = note or (
            f"conflict rule {rule or 'unknown'} spans channels outside the document, so no document "
            "re-retrieval can settle it; it is carried to the Final Supervisor unresolved"
        )
        return RecheckOutcome(
            request=request.model_copy(update={"status": RecheckStatus.COMPLETED}),
            conflict_id=conflict.conflict_id,
            status=ConflictStatus.UNRESOLVED,
            resolution_note=reason,
            trace_events=(
                TraceEvent(
                    event_id=f"trace:{request.recheck_id}:skipped",
                    case_id=case_id, run_id=run_id, event_type=TraceEventType.RECHECK,
                    status="not_actionable", agent_name=self.name, action="targeted_recheck",
                    tool_or_skill="none", conflict_id=conflict.conflict_id, recheck_id=request.recheck_id,
                    latency_ms=0,
                    details={
                        "reason": reason,
                        "rule": rule,
                        "policy_version": self.policy_version,
                        "no_evidence_reason": (
                            "this conflict is not document-actionable, so this re-check does not "
                            "retrieve or cite document Evidence"
                        ),
                    },
                ),
            ),
        )

    @staticmethod
    def _targets(conflict: CompetitionConflict, risks_by_id: dict[str, RiskItem]) -> list[str]:
        codes = sorted({risks_by_id[risk_id].risk_code for risk_id in conflict.risk_ids if risk_id in risks_by_id})
        if codes:
            return codes
        claimed = sorted(
            claim.split(":", 1)[1]
            for claim in conflict.claim_ids
            if claim.startswith("risk_code:")
        )
        return claimed or sorted(conflict.involved_agents)
