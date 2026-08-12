"""v0.3 shared workflow using the standalone professional components."""

from __future__ import annotations

from typing import Any

from ipo_risk.schemas import AnalysisError, LogStatus, ReportContext
from ipo_risk.workflows.mvp_v1 import MVPWorkflow


class EnhancedV2Workflow(MVPWorkflow):
    """Reuse the stable node lifecycle while adding v0.3 routing and supervision."""

    name = "enhanced_v2"

    def verify(self, state):
        risks = state.get("candidates", [])
        # Professional Agents already embed the Evidence used to reach each candidate.
        # Re-querying here can change identity or fabricate an apparent replacement.
        evidence_by_code: dict[str, list] = {}
        for risk in risks:
            evidence_by_code.setdefault(risk.risk_code, []).extend(risk.evidence)
        try:
            result = self.verifier.verify(risks, evidence_by_code)
            diagnostics = self._diagnostics(self.verifier)
            domain_failures = [
                domain
                for domain, details in diagnostics.items()
                if isinstance(details, dict)
                and (details.get("failed") is True or details.get("failed", 0) not in {0, False})
            ]
            errors = [
                AnalysisError(
                    stage="verifier",
                    component=f"{domain}_verifier",
                    code="specialized_verifier_failure",
                    message=f"{domain.title()} verification degraded; candidates were preserved for review.",
                    context={"domain": domain},
                )
                for domain in domain_failures
            ]
            logs = [
                self._log(
                    state,
                    f"{domain}_verifier",
                    "verify",
                    LogStatus.FAILED,
                    "specialized verifier degraded safely",
                    error,
                    diagnostics.get(domain, {}),
                )
                for domain, error in zip(domain_failures, errors)
            ]
            return {
                "verified_risks": result.verified_risks,
                "pending_risks": result.pending_risks,
                "rejected_risks": result.rejected_risks,
                "component_diagnostics": {"verifier": diagnostics},
                "errors": errors,
                "agent_logs": [
                    *logs,
                    self._log(
                        state,
                        "verifier",
                        "verify",
                        text=(
                            f"specialized routing produced {len(result.verified_risks)} "
                            f"verified, {len(result.pending_risks)} pending, and "
                            f"{len(result.rejected_risks)} rejected risk(s)"
                        ),
                        metadata=diagnostics,
                    )
                ],
            }
        except Exception as exc:
            error = self._error("verifier", exc)
            return {
                "pending_risks": self._pending(risks),
                "verified_risks": [],
                "rejected_risks": [],
                "component_diagnostics": {
                    "verifier": {"failed": True, "error_type": type(exc).__name__}
                },
                "errors": [error],
                "agent_logs": [
                    self._log(
                        state,
                        "verifier",
                        "verify",
                        LogStatus.FAILED,
                        str(exc),
                        error,
                    )
                ],
            }

    def supervise(self, state):
        all_risks = [
            *state.get("verified_risks", []),
            *state.get("pending_risks", []),
            *state.get("rejected_risks", []),
        ]

        def operation() -> dict[str, Any]:
            result = self.supervisor.supervise(all_risks)
            serialized = result.model_dump(mode="json")
            return {
                "supervised_verified_risks": result.verified_risks,
                "component_diagnostics": {"supervisor": serialized},
                "_summary": result.summary,
                "_log_metadata": result.metadata,
            }

        return self._safe(
            state,
            "supervisor",
            "supervise",
            operation,
            {
                "supervised_verified_risks": state.get("verified_risks", []),
                "component_diagnostics": {
                    "supervisor": {
                        "failed": True,
                        "fallback": "preserved_verifier_output",
                    }
                },
            },
        )

    def predict(self, state):
        return self._safe(
            state,
            "predictor",
            "predict",
            lambda: {
                "prediction": self.predictor.predict(
                    state.get("supervised_verified_risks", state.get("verified_risks", []))
                    + state.get("pending_risks", []),
                    state.get("market"),
                )
            },
            {"prediction": None},
        )

    def report(self, state):
        context = ReportContext(
            analysis_id=state["request"].request_id,
            profile=state["profile"],
            verified_risks=state.get(
                "supervised_verified_risks", state.get("verified_risks", [])
            ),
            pending_risks=state.get("pending_risks", []),
            rejected_risks=state.get("rejected_risks", []),
            prediction=state.get("prediction"),
            log_summary=f"{len(state.get('agent_logs', []))} workflow events",
            options={
                "workflow_version": self.name,
                "supervision": state.get("component_diagnostics", {}).get(
                    "supervisor", {}
                ),
                "component_diagnostics": state.get("component_diagnostics", {}),
                "runtime": {
                    "status": "partial" if state.get("errors") else "completed",
                    "event_count": len(state.get("agent_logs", [])),
                    "error_count": len(state.get("errors", [])),
                },
                "owner_waiver": {
                    "financial_second_review_deferred": True,
                    "business_second_review_deferred": True,
                },
            },
        )
        return self._safe(
            state,
            "report_generator",
            "generate",
            lambda: {"report_sections": self.reporter.generate(context)},
            {"report_sections": []},
        )
