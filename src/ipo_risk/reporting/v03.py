"""Structured, deterministic v0.3 report generation."""

from __future__ import annotations

from collections import defaultdict

from ipo_risk.schemas import ReportContext, ReportSection, RiskItem


class V03ReportGenerator:
    """Render an auditable report without making additional risk decisions."""

    name = "v03"

    def generate(self, context: ReportContext) -> list[ReportSection]:
        all_risks = [
            *context.verified_risks,
            *context.pending_risks,
            *context.rejected_risks,
        ]
        by_domain: dict[str, list[RiskItem]] = defaultdict(list)
        for risk in all_risks:
            by_domain[str(risk.category).split(".")[-1].lower()].append(risk)

        supervision = context.options.get("supervision", {})
        diagnostics = context.options.get("component_diagnostics", {})
        sections = [
            self._section(
                1,
                "Executive Summary",
                (
                    f"{context.profile.company_name}: "
                    f"{len(context.verified_risks)} verified, "
                    f"{len(context.pending_risks)} pending/needs-review, and "
                    f"{len(context.rejected_risks)} rejected risk(s)."
                ),
                all_risks,
            ),
            self._section(2, "Financial Risks", self._domain_summary(by_domain["financial"]), by_domain["financial"]),
            self._section(3, "Legal Risks", self._domain_summary(by_domain["legal"]), by_domain["legal"]),
            self._section(4, "Business Risks", self._domain_summary(by_domain["business"]), by_domain["business"]),
            self._section(5, "Market Risks", self._domain_summary(by_domain["market"]), by_domain["market"]),
            self._section(
                6,
                "Supervisor Findings",
                supervision.get("summary", "No cross-domain supervisor summary was produced."),
                context.verified_risks,
                metadata=supervision,
            ),
            self._section(
                7,
                "Prediction",
                (
                    "Prediction unavailable."
                    if context.prediction is None
                    else (
                        f"Rule score {context.prediction.risk_score}; "
                        f"level {context.prediction.risk_level}."
                    )
                ),
                context.verified_risks + context.pending_risks,
            ),
            self._section(
                8,
                "Evidence and Calculations",
                (
                    f"{sum(len(item.evidence) for item in all_risks)} Evidence reference(s); "
                    f"{sum(item.calculation is not None for item in all_risks)} Calculation object(s)."
                ),
                all_risks,
            ),
            self._section(
                9,
                "Needs Human Review",
                f"{len(context.pending_risks)} item(s) remain pending or need review.",
                context.pending_risks,
            ),
            self._section(
                10,
                "Limitations and Governance",
                (
                    "This architecture-level output is evidence-driven but not investment, "
                    "legal, or listing advice. Rule scores are not probabilities. Financial "
                    "and Business second review remains deferred under the owner waiver and "
                    "must not be represented as completed Golden review."
                ),
                [],
                metadata={
                    "workflow_version": context.options.get("workflow_version", "enhanced_v2"),
                    "component_diagnostics": diagnostics,
                    "owner_waiver": context.options.get("owner_waiver", {}),
                },
            ),
        ]
        return sections

    @staticmethod
    def _domain_summary(risks: list[RiskItem]) -> str:
        if not risks:
            return "No candidate was produced for this domain."
        codes = ", ".join(dict.fromkeys(item.risk_code for item in risks))
        return f"{len(risks)} item(s): {codes}."

    @staticmethod
    def _section(
        order: int,
        title: str,
        summary: str,
        risks: list[RiskItem],
        *,
        metadata: dict | None = None,
    ) -> ReportSection:
        return ReportSection(
            title=title,
            summary=summary,
            risks=risks,
            evidence_ids=list(
                dict.fromkeys(
                    evidence.evidence_id for risk in risks for evidence in risk.evidence
                )
            ),
            order=order,
            metadata=metadata or {},
        )
