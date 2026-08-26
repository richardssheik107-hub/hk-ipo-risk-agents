"""Submission-facing artifacts for one competition case: reasoning log, case
report and Gate E1 acceptance evidence.

These are renderings, never sources.  Every id, page, number and status here is
read back out of what the run actually produced -- the analysis result, the
trace sidecar, the conflict and re-check diagnostics -- so a thin run renders a
thin report rather than a flattering one.  Nothing is filled in on behalf of
another lane: a document channel that asserted no risk, a market channel that
was unavailable and a Final Supervisor that fell back to the deterministic
composition are all stated as such.

The Gate E1 evidence is deliberately the strict half of this module.  The Gate
asks for a *successful* bounded LLM arbitration by a *real* provider with its
call trace retained and no out-of-scope reference; a run that honestly degraded
satisfies none of that, and this module refuses to record it as if it did.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field


REASONING_LOG_SCHEMA_VERSION = "v045_role_e_reasoning_log_v1"
CASE_REPORT_SCHEMA_VERSION = "v045_role_e_case_report_v1"
GATE_E1_SCHEMA_VERSION = "v045_role_e_gate_e1_v1"

GATE_E1_REQUIREMENT = (
    "same final case matrix + real provider credentials + successful bounded LLM Final "
    "Supervisor synthesis + trace metadata retained + no out-of-scope Evidence/Risk/Conflict "
    "references"
)

# An allowlist, not a denylist: an unrecognised provider name is not accepted as
# a real remote provider.  A new transport has to be added here deliberately,
# which is the fail-closed direction for an acceptance Gate.
REAL_LLM_PROVIDERS = frozenset({"openai_compatible", "openai_responses"})

# The provider call fields Gate E1 requires a successful synthesis to retain.
REQUIRED_CALL_TRACE_FIELDS = (
    "provider_name",
    "model_name",
    "prompt_version",
    "request_id",
    "raw_response_hash",
    "latency_ms",
)


class CaseRunArtifacts(BaseModel):
    """The JSON payloads one case run produced, as written to disk.

    Plain dicts on purpose: these renderers must be exercisable from a recorded
    run without re-executing an analysis.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    company_name: str
    stock_code: str
    listing_date: str
    config: str
    result: dict[str, Any]
    sidecar: dict[str, Any] = Field(default_factory=dict)
    composition: dict[str, Any] = Field(default_factory=dict)
    supervision_llm: dict[str, Any] = Field(default_factory=dict)
    conflicts: dict[str, Any] = Field(default_factory=dict)
    rechecks: dict[str, Any] = Field(default_factory=dict)
    traceability: dict[str, Any] = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)

    @property
    def channel_states(self) -> dict[str, str]:
        return {
            item["channel"]: item["status"]
            for item in self.composition.get("channel_states", [])
            if isinstance(item, dict) and "channel" in item
        }

    @property
    def trace_events(self) -> list[dict[str, Any]]:
        return list(self.sidecar.get("trace_events", []))

    @property
    def conflict_records(self) -> list[dict[str, Any]]:
        return list(self.conflicts.get("conflicts", []))

    @property
    def recheck_outcomes(self) -> list[dict[str, Any]]:
        return list(self.rechecks.get("outcomes", []))

    def risks(self, group: str) -> list[dict[str, Any]]:
        return list(self.result.get(group, []))


def _short(identifier: str | None, width: int = 12) -> str:
    if not identifier:
        return "—"
    return identifier if len(identifier) <= width else f"{identifier[:width]}…"


def _bullet(lines: list[str], items: Iterable[str], empty: str) -> None:
    rendered = list(items)
    lines.extend(rendered if rendered else [f"- {empty}"])


# --------------------------------------------------------------------------
# Agent reasoning log
# --------------------------------------------------------------------------


def build_agent_reasoning_log(artifacts: CaseRunArtifacts) -> dict[str, Any]:
    """One machine-readable reasoning log per case, derived from the trace.

    A step with no Evidence is not hidden: it either carries the explicit
    ``no_evidence_reason`` the trace assembler recorded, or it is marked
    unaccounted, which is exactly what pulls measured traceability below 1.0.
    """

    identity = artifacts.sidecar.get("identity", {})
    recheck_by_conflict = {
        outcome.get("conflict_id"): outcome for outcome in artifacts.recheck_outcomes
    }

    steps: list[dict[str, Any]] = []
    for index, event in enumerate(artifacts.trace_events, start=1):
        details = event.get("details", {}) or {}
        evidence_ids = list(event.get("evidence_ids", []) or [])
        calculation_ids = list(event.get("calculation_ids", []) or [])
        no_evidence_reason = details.get("no_evidence_reason")
        steps.append(
            {
                # Position in the assembled trace, not the workflow's own log
                # counter: events the workflow never logged (the synthesis pass)
                # carry no log step, and mixing the two counters would renumber
                # the narrative out of order.
                "step": index,
                "workflow_log_step": details.get("step"),
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "status": event.get("status"),
                "agent": event.get("agent_name"),
                "action": event.get("action"),
                "tool_or_skill": event.get("tool_or_skill"),
                "provider_name": event.get("provider_name"),
                "model_name": event.get("model_name"),
                "prompt_version": event.get("prompt_version"),
                "request_id": event.get("request_id"),
                "raw_response_hash": event.get("raw_response_hash"),
                "latency_ms": event.get("latency_ms"),
                "conflict_id": event.get("conflict_id"),
                "recheck_id": event.get("recheck_id"),
                "evidence_ids": evidence_ids,
                "evidence_id_count": len(evidence_ids),
                "calculation_ids": calculation_ids,
                "output_summary": details.get("output_summary") or "",
                "no_evidence_reason": no_evidence_reason,
                # Mirrors the traceability measurement rather than restating it:
                # a step with neither Evidence nor a stated reason is a real gap.
                "evidence_accounted": bool(evidence_ids or calculation_ids or no_evidence_reason),
                "occurred_at": event.get("occurred_at"),
            }
        )

    conflicts: list[dict[str, Any]] = []
    for record in artifacts.conflict_records:
        outcome = recheck_by_conflict.get(record.get("conflict_id"))
        conflicts.append(
            {
                "conflict_id": record.get("conflict_id"),
                "involved_agents": list(record.get("involved_agents", [])),
                "summary": record.get("summary"),
                "status": record.get("status"),
                "resolution_note": record.get("resolution_note"),
                "risk_ids": list(record.get("risk_ids", [])),
                "evidence_id_count": len(record.get("evidence_ids", []) or []),
                "targeted_recheck": (
                    {
                        "recheck_id": outcome.get("recheck_id"),
                        "status": outcome.get("status"),
                        "targets": list(outcome.get("targets", [])),
                        "new_evidence_ids": list(outcome.get("new_evidence_ids", [])),
                        "revised_risk_ids": list(outcome.get("revised_risk_ids", [])),
                    }
                    if outcome
                    else None
                ),
                # Budget is bounded by policy, so an unrechecked conflict is a
                # declared state, never a silent drop.
                "recheck_attempted": outcome is not None,
            }
        )

    unaccounted = [step for step in steps if not step["evidence_accounted"]]
    return {
        "schema_version": REASONING_LOG_SCHEMA_VERSION,
        "case_id": artifacts.case_id,
        "company_name": artifacts.company_name,
        "stock_code": artifacts.stock_code,
        "listing_date": artifacts.listing_date,
        "config": artifacts.config,
        "run_id": identity.get("run_id"),
        "analysis_id": artifacts.result.get("analysis_id"),
        "provenance": identity.get("provenance", {}),
        "channel_states": artifacts.channel_states,
        "steps": steps,
        "conflicts": conflicts,
        "recheck_budget": {
            "policy_version": artifacts.rechecks.get("policy_version"),
            "attempted": artifacts.rechecks.get("attempted", 0),
            "conflicts_detected": len(conflicts),
            "conflicts_not_attempted": [
                conflict["conflict_id"] for conflict in conflicts if not conflict["recheck_attempted"]
            ],
        },
        "final_supervision": {
            "status": artifacts.supervision_llm.get("status"),
            "outcome": artifacts.supervision_llm.get("outcome"),
            "reason": artifacts.supervision_llm.get("reason"),
            "deterministic_severity_floor": artifacts.supervision_llm.get(
                "deterministic_severity_floor"
            ),
            "fail_closed": artifacts.supervision_llm.get("fail_closed"),
            "scope_check": artifacts.supervision_llm.get("scope_check", {}),
            "call": artifacts.supervision_llm.get("call", {}),
            "judgement_present": artifacts.supervision_llm.get("judgement") is not None,
        },
        "traceability": artifacts.traceability,
        "accounting": {
            "trace_event_count": len(steps),
            "steps_without_evidence_reference": sum(
                1 for step in steps if not step["evidence_ids"] and not step["calculation_ids"]
            ),
            "unaccounted_step_count": len(unaccounted),
            "unaccounted_step_ids": [step["event_id"] for step in unaccounted],
        },
        "not_demonstrated": not_demonstrated(artifacts),
    }


def not_demonstrated(artifacts: CaseRunArtifacts) -> list[str]:
    """What this run does *not* establish, stated in the artifact itself."""

    statements: list[str] = []
    if not artifacts.risks("verified_risks"):
        statements.append(
            "No formal RiskItem was verified in this run. The chain executed end to end and "
            "Evidence was retrieved, so this case demonstrates chain integrity and traceability, "
            "not document extraction quality (Role B coverage)."
        )
    channels = artifacts.channel_states
    market = channels.get("market")
    if market and market != "available":
        statements.append(
            f"Market channel is `{market}`: no governed market fact entered this run, so no "
            "market-side divergence could be detected. Nothing was substituted for it."
        )
    model = channels.get("model")
    if model and model != "available":
        statements.append(
            f"Model channel is `{model}`: no model score entered this run. No replacement score "
            "was generated (Role D / frozen PR-F handoff)."
        )
    outcome = artifacts.supervision_llm.get("outcome")
    if outcome != "accepted":
        statements.append(
            f"The LLM Final Supervisor did not arbitrate (`{outcome}`); the deterministic "
            "composition stands unchanged. This run is not evidence for Gate E1."
        )
    evidence = _evidence_items(artifacts)
    if evidence and not any(item.get("bbox") for item in evidence):
        statements.append(
            "Evidence carries physical page grounding but no bbox, because the parser does not "
            "produce one. The viewer draws no box rather than guessing coordinates."
        )
    return statements


def _evidence_items(artifacts: CaseRunArtifacts) -> list[dict[str, Any]]:
    return [
        evidence
        for group in ("verified_risks", "pending_risks", "rejected_risks")
        for risk in artifacts.risks(group)
        for evidence in risk.get("evidence", [])
    ]


def render_agent_reasoning_log(log: dict[str, Any]) -> str:
    """The same log as a submission-facing narrative, in trace order."""

    lines = [
        f"# {log['company_name']} ({log['stock_code']}) — Agent reasoning log",
        "",
        f"- case_id: `{log['case_id']}`",
        f"- run_id: `{log['run_id']}`",
        f"- config: `{log['config']}`",
        f"- workflow: `{log['provenance'].get('workflow')}` · "
        f"trace schema `{log['provenance'].get('trace_schema_version')}`",
        f"- conflict policy: `{log['provenance'].get('conflict_policy_version')}` · "
        f"re-check policy: `{log['provenance'].get('recheck_policy_version')}`",
        "",
        "Every step below is a recorded trace event. Steps that referenced no Evidence carry the "
        "reason they did not, which is what the measured traceability counts.",
        "",
        "## Step by step",
        "",
    ]
    for step in log["steps"]:
        head = (
            f"{step['step']:>3}. **{step['agent']}** · `{step['action']}` · "
            f"tool `{step['tool_or_skill']}` · {step['status']}"
        )
        lines.append(head)
        if step["output_summary"]:
            lines.append(f"     - result: {step['output_summary']}")
        if step["evidence_ids"]:
            lines.append(
                f"     - evidence: {step['evidence_id_count']} item(s) — "
                + ", ".join(f"`{_short(item)}`" for item in step["evidence_ids"][:5])
                + (" …" if step["evidence_id_count"] > 5 else "")
            )
        if step["calculation_ids"]:
            lines.append(
                "     - calculations: "
                + ", ".join(f"`{_short(item)}`" for item in step["calculation_ids"])
            )
        if step["no_evidence_reason"]:
            lines.append(f"     - no Evidence, stated reason: {step['no_evidence_reason']}")
        if not step["evidence_accounted"]:
            lines.append("     - **unaccounted**: no Evidence and no stated reason")
        if step["provider_name"]:
            lines.append(
                f"     - provider `{step['provider_name']}` · model `{step['model_name'] or '—'}` · "
                f"prompt `{step['prompt_version'] or '—'}` · request `{_short(step['request_id'])}` · "
                f"response hash `{_short(step['raw_response_hash'])}` · {step['latency_ms']} ms"
            )
        if step["conflict_id"]:
            lines.append(f"     - conflict: `{_short(step['conflict_id'], 40)}`")
    lines += ["", "## Cross-agent conflicts and bounded re-check", ""]
    conflict_lines = []
    for conflict in log["conflicts"]:
        conflict_lines.append(
            f"- `{conflict['status']}` · {' vs '.join(conflict['involved_agents'])} — "
            f"{conflict['summary']}"
        )
        recheck = conflict["targeted_recheck"]
        if recheck:
            conflict_lines.append(
                f"  - targeted re-check `{recheck['status']}` on "
                f"{', '.join(recheck['targets']) or '—'}; "
                f"{len(recheck['new_evidence_ids'])} new Evidence, "
                f"{len(recheck['revised_risk_ids'])} revised risk(s)"
            )
        else:
            conflict_lines.append(
                "  - no targeted re-check was attempted: the bounded budget was already spent"
            )
        if conflict["resolution_note"]:
            conflict_lines.append(f"  - note: {conflict['resolution_note']}")
    _bullet(lines, conflict_lines, "no cross-agent conflict was detected in this run")

    budget = log["recheck_budget"]
    supervision = log["final_supervision"]
    accounting = log["accounting"]
    traceability = log.get("traceability") or {}
    lines += [
        "",
        f"Re-check budget: {budget['attempted']} attempted over {budget['conflicts_detected']} "
        f"detected conflict(s); policy `{budget['policy_version']}`, at most one re-check per "
        "conflict.",
        "",
        "## Final Supervisor",
        "",
        f"- status: `{supervision['status']}` · outcome: `{supervision['outcome']}`",
        f"- reason: {supervision['reason']}",
        f"- deterministic severity floor: `{supervision['deterministic_severity_floor']}`",
        f"- scope check: `{supervision['scope_check'].get('status', 'not_recorded')}`",
    ]
    call = supervision.get("call") or {}
    if call:
        lines.append(
            f"- provider `{call.get('provider_name') or '—'}` · model `{call.get('model_name') or '—'}` "
            f"· prompt `{call.get('prompt_version') or '—'}` · request `{_short(call.get('request_id'))}` "
            f"· response hash `{_short(call.get('raw_response_hash'))}` · "
            f"{call.get('latency_ms', '—')} ms"
        )
    lines += [
        "",
        "## Trace accounting",
        "",
        f"- trace events: {accounting['trace_event_count']}",
        f"- steps that referenced no Evidence directly: "
        f"{accounting['steps_without_evidence_reference']} (each states why)",
        f"- unaccounted steps: {accounting['unaccounted_step_count']}",
        f"- measured overall traceability: {traceability.get('overall_traceability', '—')}",
        f"- referenced Evidence resolved: {traceability.get('resolved_evidence_count', '—')}"
        f" / {traceability.get('referenced_evidence_count', '—')}",
        "",
        "## What this run does not demonstrate",
        "",
    ]
    _bullet(
        lines,
        [f"- {item}" for item in log["not_demonstrated"]],
        "every channel in this run was available and arbitrated.",
    )
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Gate E1 acceptance evidence
# --------------------------------------------------------------------------


def build_gate_e1_evidence(artifacts: CaseRunArtifacts) -> dict[str, Any]:
    """Machine-checkable Gate E1 evidence for one case.

    ``satisfied`` is true only when a real provider produced a judgement that
    the scope guard accepted, with the whole call trace retained.  A missing
    provider, a transport failure, a refused response or a mock all leave it
    false, with the unmet conditions named.
    """

    supervision = artifacts.supervision_llm
    outcome = supervision.get("outcome")
    status = supervision.get("status")
    scope_check = dict(supervision.get("scope_check", {}) or {})
    call = dict(supervision.get("call", {}) or {})

    provider_name = call.get("provider_name") or (
        artifacts.sidecar.get("identity", {}).get("provider_name")
    )
    provider_is_real = provider_name in REAL_LLM_PROVIDERS
    missing_trace_fields = [
        field for field in REQUIRED_CALL_TRACE_FIELDS if call.get(field) in (None, "")
    ]
    accepted = outcome == "accepted" and supervision.get("judgement") is not None

    unmet: list[str] = []
    if not accepted:
        unmet.append(f"successful bounded LLM synthesis (outcome: {outcome or 'not_recorded'})")
    if not provider_is_real:
        unmet.append(f"real remote provider (provider: {provider_name or 'none'})")
    if accepted and missing_trace_fields:
        unmet.append(f"retained call trace (missing: {', '.join(missing_trace_fields)})")
    if accepted and scope_check.get("status") != "passed":
        unmet.append(f"in-scope reference check (scope check: {scope_check.get('status')})")

    return {
        "schema_version": GATE_E1_SCHEMA_VERSION,
        "gate": "E1",
        "requirement": GATE_E1_REQUIREMENT,
        "case_id": artifacts.case_id,
        "stock_code": artifacts.stock_code,
        "config": artifacts.config,
        "synthesis_status": status,
        "synthesis_outcome": outcome,
        "successful_llm_arbitration": bool(accepted and provider_is_real),
        "deterministic_fallback_used": not accepted,
        "provider_name": provider_name,
        "provider_is_real_remote": provider_is_real,
        "provider_trace": call,
        "provider_trace_complete": accepted and not missing_trace_fields,
        "missing_provider_trace_fields": missing_trace_fields,
        # A guard that never ran proves nothing; only a real response can.
        "out_of_scope_reference_check": {
            "status": scope_check.get("status", "not_recorded"),
            "fail_closed_fired": bool(supervision.get("fail_closed")),
            "out_of_scope_reference_count": scope_check.get("out_of_scope_reference_count"),
            "violation": scope_check.get("violation"),
            "cited_risk_ids": scope_check.get("cited_risk_ids", []),
            "cited_evidence_ids": scope_check.get("cited_evidence_ids", []),
            "cited_conflict_ids": scope_check.get("cited_conflict_ids", []),
        },
        "deterministic_severity_floor": supervision.get("deterministic_severity_floor"),
        "severity_floor_respected": scope_check.get("severity_floor_respected"),
        "satisfied": not unmet,
        "unmet_conditions": unmet,
    }


def summarise_gate_e1(
    case_evidence: Sequence[dict[str, Any]], declared_case_count: int
) -> dict[str, Any]:
    """Roll the per-case evidence into one Gate verdict for the matrix."""

    arbitrated = [item for item in case_evidence if item.get("successful_llm_arbitration")]
    satisfied_cases = [item for item in case_evidence if item.get("satisfied")]
    fell_back = [item for item in case_evidence if item.get("deterministic_fallback_used")]
    reasons = sorted(
        {reason for item in case_evidence for reason in item.get("unmet_conditions", [])}
    )
    satisfied = bool(case_evidence) and len(satisfied_cases) == declared_case_count
    return {
        "schema_version": GATE_E1_SCHEMA_VERSION,
        "gate": "E1",
        "requirement": GATE_E1_REQUIREMENT,
        "declared_case_count": declared_case_count,
        "cases_with_evidence": len(case_evidence),
        "cases_with_successful_llm_arbitration": len(arbitrated),
        "cases_satisfying_gate": len(satisfied_cases),
        "cases_on_deterministic_fallback": len(fell_back),
        "satisfied": satisfied,
        "unmet_conditions": reasons,
        "verdict": (
            "Gate E1 met on the declared matrix"
            if satisfied
            else "Gate E1 NOT met: a deterministic fallback is an honest degradation, "
            "not a successful LLM arbitration"
        ),
    }


# --------------------------------------------------------------------------
# Case report
# --------------------------------------------------------------------------


def render_case_report(
    artifacts: CaseRunArtifacts, reasoning_log: dict[str, Any], gate_evidence: dict[str, Any]
) -> str:
    """The submission-facing case report: what was found, on what Evidence."""

    result = artifacts.result
    verification = artifacts.verification
    lines = [
        f"# {artifacts.company_name} ({artifacts.stock_code}) — Competition case report",
        "",
        f"- case_id: `{artifacts.case_id}`",
        f"- listing_date: `{artifacts.listing_date}`",
        f"- config: `{artifacts.config}`",
        f"- analysis status: `{result.get('status')}` · analysis_id `{result.get('analysis_id')}`",
        f"- workflow: `{result.get('workflow_version')}` · schema `{result.get('schema_version')}`",
        f"- parsed chunks: {result.get('metadata', {}).get('document', {}).get('parsed_chunk_count', '—')}"
        f" · report sections: {len(result.get('report_sections', []))}"
        f" · structured errors: {len(result.get('errors', []))}",
        "",
        "## Source integrity",
        "",
        f"- source file: `{verification.get('source_filename', '—')}`",
        f"- SHA-256: `{verification.get('sha256', '—')}` "
        f"({'matches' if verification.get('sha256_matches_frozen_catalog') else 'does not match'} "
        "the frozen catalog)",
        f"- size: {verification.get('file_size_bytes', '—')} bytes · physical pages: "
        f"{verification.get('pdf_page_count', '—')}",
        f"- dataset split: `{verification.get('dataset_split', '—')}`",
        "",
        "The archive path is licensed local state and is deliberately not recorded. A prospectus "
        "whose bytes or page count differ from the frozen catalog is refused, never analysed.",
        "",
        "## Channel states",
        "",
    ]
    _bullet(
        lines,
        [f"- `{channel}`: `{state}`" for channel, state in sorted(artifacts.channel_states.items())],
        "no channel state was recorded",
    )

    lines += ["", "## Verified risks", ""]
    verified_lines: list[str] = []
    for risk in artifacts.risks("verified_risks"):
        verified_lines.append(
            f"- **{risk['risk_code']}** · {risk['level']} · {risk['verification_status']} · "
            f"agent `{risk['agent_name']}`"
        )
        verified_lines.append(f"  - conclusion: {risk['conclusion']}")
        calculation = risk.get("calculation")
        if calculation:
            verified_lines.append(
                f"  - calculation `{calculation.get('skill_name')}` "
                f"v{calculation.get('skill_version')}: `{calculation.get('formula')}` = "
                f"{calculation.get('result')} {calculation.get('unit')}"
            )
        for evidence in risk.get("evidence", []):
            verified_lines.append(
                f"  - evidence `{_short(evidence.get('evidence_id'))}` · page "
                f"{evidence.get('page', '—')} · section `{evidence.get('section', '—')}`"
                + ("" if evidence.get("bbox") else " · no bbox (parser does not produce one)")
            )
        if risk.get("verification_notes"):
            verified_lines.append(f"  - verifier: {risk['verification_notes']}")
    _bullet(
        lines,
        verified_lines,
        "none. The document channel asserted no formal risk in this run; nothing was written in "
        "to fill the gap.",
    )

    for group, title in (("pending_risks", "Pending risks"), ("rejected_risks", "Rejected risks")):
        risks = artifacts.risks(group)
        if not risks:
            continue
        lines += ["", f"## {title}", ""]
        for risk in risks:
            lines.append(
                f"- **{risk['risk_code']}** · {risk['level']} · {risk['verification_status']} · "
                f"{len(risk.get('evidence', []))} evidence — {risk.get('verification_notes') or risk['conclusion']}"
            )

    lines += ["", "## Cross-agent conflicts and targeted re-check", ""]
    conflict_lines: list[str] = []
    for conflict in reasoning_log["conflicts"]:
        conflict_lines.append(f"- `{conflict['status']}` — {conflict['summary']}")
        if conflict["resolution_note"]:
            conflict_lines.append(f"  - re-check: {conflict['resolution_note']}")
    _bullet(lines, conflict_lines, "no cross-agent conflict was detected in this run")

    supervision = reasoning_log["final_supervision"]
    traceability = artifacts.traceability or {}
    lines += [
        "",
        "## Final Supervisor",
        "",
        f"- LLM synthesis: `{supervision['status']}` / `{supervision['outcome']}` — "
        f"{supervision['reason']}",
        f"- deterministic severity floor: `{supervision['deterministic_severity_floor']}`",
        f"- Gate E1 for this case: "
        f"{'satisfied' if gate_evidence['satisfied'] else 'NOT satisfied'}"
        + (
            ""
            if gate_evidence["satisfied"]
            else f" — unmet: {'; '.join(gate_evidence['unmet_conditions'])}"
        ),
        "",
        "## Traceability",
        "",
        f"- trace events: {traceability.get('event_count', '—')}"
        " (step by step in `agent_reasoning_log.md`)",
        f"- agent / tool / evidence traceability: "
        f"{traceability.get('agent_traceability', '—')} / "
        f"{traceability.get('tool_traceability', '—')} / "
        f"{traceability.get('evidence_traceability', '—')}",
        f"- overall measured traceability: {traceability.get('overall_traceability', '—')}",
        "",
        "## What this report does not demonstrate",
        "",
    ]
    _bullet(
        lines,
        [f"- {item}" for item in reasoning_log["not_demonstrated"]],
        "every channel in this run was available and arbitrated.",
    )
    lines += [
        "",
        "The rule and model scores are not probabilities. This report is not investment, legal or",
        "listing advice.",
        "",
    ]
    return "\n".join(lines)


__all__ = [
    "CASE_REPORT_SCHEMA_VERSION",
    "CaseRunArtifacts",
    "GATE_E1_REQUIREMENT",
    "GATE_E1_SCHEMA_VERSION",
    "REASONING_LOG_SCHEMA_VERSION",
    "REAL_LLM_PROVIDERS",
    "REQUIRED_CALL_TRACE_FIELDS",
    "build_agent_reasoning_log",
    "build_gate_e1_evidence",
    "not_demonstrated",
    "render_agent_reasoning_log",
    "render_case_report",
    "summarise_gate_e1",
]
