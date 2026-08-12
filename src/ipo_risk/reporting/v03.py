"""Structured, deterministic v0.3 report generation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ipo_risk.schemas import ReportContext, ReportSection, RiskItem


class V03ReportGenerator:
    """Generate the frozen ten-section report without new risk decisions."""

    name = "v03"

    def generate(self, context: ReportContext) -> list[ReportSection]:
        all_risks = [
            *context.verified_risks,
            *context.pending_risks,
            *context.rejected_risks,
        ]
        by_domain: dict[str, list[RiskItem]] = defaultdict(list)
        for risk in all_risks:
            by_domain[risk.category.value].append(risk)

        supervision = context.options.get("supervision", {})
        diagnostics = context.options.get("component_diagnostics", {})
        runtime = context.options.get("runtime", {})
        return [
            self._section(
                1,
                "IPO Profile",
                self._profile_summary(context),
                [],
                metadata=context.profile.model_dump(mode="json"),
            ),
            self._section(
                2,
                "System Runtime and Executive Risk Summary",
                (
                    f"{len(context.verified_risks)} verified, "
                    f"{len(context.pending_risks)} pending/needs-review, and "
                    f"{len(context.rejected_risks)} rejected risk(s). "
                    + (
                        "Overall rule score is unavailable."
                        if context.prediction is None
                        else (
                            f"Overall deterministic rule score "
                            f"{context.prediction.risk_score:g}/100 "
                            f"({context.prediction.risk_level.value})."
                        )
                    )
                ),
                all_risks,
                metadata={
                    "runtime": runtime,
                    "component_diagnostics": diagnostics,
                    "prediction": (
                        context.prediction.model_dump(mode="json")
                        if context.prediction is not None
                        else None
                    ),
                },
            ),
            self._section(3, "Financial Risks", self._domain_summary(by_domain["financial"]), by_domain["financial"]),
            self._section(4, "Legal Risks", self._domain_summary(by_domain["legal"]), by_domain["legal"]),
            self._section(5, "Business Risks", self._domain_summary(by_domain["business"]), by_domain["business"]),
            self._section(
                6,
                "Multi-Agent Supervisor Summary",
                supervision.get("summary", "No cross-domain supervisor summary was produced."),
                context.verified_risks + context.pending_risks,
                metadata=supervision,
            ),
            self._section(
                7,
                "Evidence Index",
                f"{sum(len(item.evidence) for item in all_risks)} Evidence reference(s).",
                all_risks,
                metadata={"entries": self._evidence_index(all_risks)},
            ),
            self._section(
                8,
                "Calculation Index",
                f"{sum(item.calculation is not None for item in all_risks)} deterministic Calculation object(s).",
                [risk for risk in all_risks if risk.calculation is not None],
                metadata={"entries": self._calculation_index(all_risks)},
            ),
            self._section(
                9,
                "Needs Human Review",
                f"{len(context.pending_risks)} item(s) remain pending or need review.",
                context.pending_risks,
                metadata={"component_diagnostics": diagnostics},
            ),
            self._section(
                10,
                "Methodology, Limitations and Governance",
                (
                    "This version provides deterministic, document-based risk analysis. "
                    "Rule scores are not probabilities and the output is not investment, "
                    "legal, listing, or stock-return advice. Financial and Business formal "
                    "independent second-review Golden certification remains deferred under "
                    "the owner waiver. Market prediction, calibrated probability, OCR and "
                    "PDF report export are outside v0.3."
                ),
                [],
                metadata={
                    "workflow_version": context.options.get("workflow_version", "enhanced_v2"),
                    "owner_waiver": context.options.get("owner_waiver", {}),
                },
            ),
        ]

    @staticmethod
    def _profile_summary(context: ReportContext) -> str:
        profile = context.profile
        return (
            f"{profile.company_name} ({profile.stock_code or 'Unavailable'}); "
            f"listing date {profile.listing_date or 'Unavailable'}; "
            f"industry {profile.industry or 'Unavailable'}."
        )

    @staticmethod
    def _domain_summary(risks: list[RiskItem]) -> str:
        if not risks:
            return "No risk item was produced for this domain."
        counts: dict[str, int] = defaultdict(int)
        for risk in risks:
            counts[risk.verification_status.value] += 1
        status = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        codes = ", ".join(dict.fromkeys(item.risk_code for item in risks))
        return f"{len(risks)} item(s): {codes}. Status: {status}."

    @staticmethod
    def _evidence_index(risks: list[RiskItem]) -> list[dict[str, Any]]:
        return [
            {
                "evidence_id": evidence.evidence_id,
                "page": evidence.page,
                "section": evidence.section,
                "risk_code": risk.risk_code,
                "text": evidence.text,
                "source_type": evidence.source_type.value,
            }
            for risk in risks
            for evidence in risk.evidence
        ]

    @staticmethod
    def _calculation_index(risks: list[RiskItem]) -> list[dict[str, Any]]:
        return [
            {
                "risk_code": risk.risk_code,
                "skill_name": risk.calculation.skill_name,
                "formula": risk.calculation.formula,
                "inputs": risk.calculation.inputs,
                "result": risk.calculation.result,
                "unit": risk.calculation.unit,
                "evidence_ids": risk.calculation.evidence_ids,
            }
            for risk in risks
            if risk.calculation is not None
        ]

    @staticmethod
    def _section(
        order: int,
        title: str,
        summary: str,
        risks: list[RiskItem],
        *,
        metadata: dict[str, Any] | None = None,
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
