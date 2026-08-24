"""v0.4 report: the ten frozen v0.3 sections plus the three PR-G channels.

``V03ReportGenerator`` is left untouched.  Its ten-section shape is pinned by
tests and consumed by the presenter, and its methodology text is accurate *for
v0.3*.  This subclass renumbers around it and adds what PR-G introduced.

Section ids are deterministic here, unlike the uuid4 default, so a v0.4 report is
content-addressable.
"""

from __future__ import annotations

from typing import Any

from ipo_risk.reporting.v03 import V03ReportGenerator
from ipo_risk.schemas import ReportContext, ReportSection

# Where the inherited v0.3 sections land in the v0.4 ordering.
_INHERITED_ORDER = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 10, 8: 11, 9: 12, 10: 13}
_RENAMED = {6: "Document Supervisor Summary"}
_METHODOLOGY = (
    "This version provides deterministic, document-based risk analysis combined with "
    "governed market context and a frozen model signal. Rule scores and model scores "
    "are not probabilities and the output is not investment, legal, listing, or "
    "stock-return advice. The frozen model score is an uncalibrated_model_score; "
    "calibrated probability remains outside v0.4. Financial and Business formal "
    "independent second-review Golden certification remains deferred under the owner "
    "waiver. OCR and PDF report export are outside v0.4."
)


class V04ReportGenerator(V03ReportGenerator):
    """Thirteen sections; answers risk, evidence, market, model and uncertainty."""

    name = "v04"

    def generate(self, context: ReportContext) -> list[ReportSection]:
        sections = [self._renumber(section) for section in super().generate(context)]
        sections.extend((
            self._channel_section(7, "Market Context", *self._market(context)),
            self._channel_section(8, "Model Signal and Uncertainty", *self._model(context)),
            self._channel_section(9, "Final Supervisor Synthesis", *self._synthesis(context)),
        ))
        sections.sort(key=lambda section: section.order)
        return [section.model_copy(update={"section_id": f"v04-section-{section.order:02d}"})
                for section in sections]

    def _renumber(self, section: ReportSection) -> ReportSection:
        order = _INHERITED_ORDER[section.order]
        update: dict[str, Any] = {"order": order}
        if section.order in _RENAMED:
            update["title"] = _RENAMED[section.order]
        if section.order == 10:
            update["summary"] = _METHODOLOGY
        return section.model_copy(update=update)

    @staticmethod
    def _channel_section(order: int, title: str, summary: str, metadata: dict[str, Any]) -> ReportSection:
        """A channel section carries no risks of its own; it points at them."""
        return ReportSection(title=title, summary=summary, risks=[], evidence_ids=[],
                             order=order, metadata=metadata)

    @staticmethod
    def _market(context: ReportContext) -> tuple[str, dict[str, Any]]:
        view = context.options.get("market_context")
        if view is None:
            return ("The market context channel did not run for this analysis.", {})
        payload = view.model_dump(mode="json")
        available = [item for item in payload["observations"] if item["availability"] == "available"]
        if payload["status"] != "available":
            summary = f"Market context {payload['status']}: {payload['reason']}. No market observation is reported."
        else:
            provenance = payload.get("provenance") or {}
            source = provenance.get("source") or provenance.get("feature_pipeline")
            if source == "governed_pr_b_core":
                source_label = "governed PR-B Market-X Core"
            elif source:
                source_label = str(source)
            else:
                source_label = "governed market context"
            summary = (f"{len(available)} of {len(payload['observations'])} pre-listing market "
                       f"observations available from {source_label}.")
        return (summary, payload)

    @staticmethod
    def _model(context: ReportContext) -> tuple[str, dict[str, Any]]:
        final = context.options.get("final_supervision")
        if final is None:
            return ("The model signal channel did not run for this analysis.", {})
        payload = final.model_dump(mode="json")
        prediction = payload.get("model_prediction")
        if prediction is None:
            summary = ("No per-case model score is available for this IPO. The frozen cohort "
                       "evidence below states what the model was and was not able to establish.")
        else:
            summary = (f"Frozen {prediction['model_name']} {prediction['model_version']} score "
                       f"{prediction['score']}, reported as {prediction['score_semantics']}; "
                       f"calibration status {prediction['calibration_status']}.")
        return (summary, {"model_prediction": prediction,
                          "uncertainty_statement": payload["uncertainty_statement"]})

    @staticmethod
    def _synthesis(context: ReportContext) -> tuple[str, dict[str, Any]]:
        final = context.options.get("final_supervision")
        if final is None:
            return ("The Final Supervisor did not run for this analysis.", {})
        payload = final.model_dump(mode="json")
        states = ", ".join(f"{item['channel']}={item['status']}" for item in payload["channel_states"])
        summary = f"{payload['summary']} Channels: {states}."
        return (summary, {
            "channel_states": payload["channel_states"],
            "referenced_risk_ids": payload["referenced_risk_ids"],
            "referenced_evidence_ids": payload["referenced_evidence_ids"],
            # Conflicts are preserved, never resolved; arbitration is CH-4.
            "conflicts": payload["conflicts"],
            "composite_findings": payload["composite_findings"],
            "uncertainty_statement": payload["uncertainty_statement"],
            "metadata": payload["metadata"],
        })
