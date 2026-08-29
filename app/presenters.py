"""Pure presentation helpers for Streamlit and UI tests."""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import date
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Iterator

from ipo_risk.schemas import IPOAnalysisRequest, IPOAnalysisResult, RiskItem


MAX_PDF_UPLOAD_BYTES = 200 * 1024 * 1024
DOMAINS = ("financial", "legal", "business")


def validate_pdf_upload(filename: str, content: bytes) -> None:
    """Reject empty, oversized, mislabelled, or non-PDF uploads."""

    if Path(filename).suffix.lower() != ".pdf":
        raise ValueError("Only .pdf files are accepted.")
    if not content:
        raise ValueError("The uploaded PDF is empty.")
    if len(content) > MAX_PDF_UPLOAD_BYTES:
        raise ValueError("The uploaded PDF exceeds the 200 MB size limit.")
    if not content.startswith(b"%PDF-"):
        raise ValueError("The uploaded file does not have a valid PDF header.")


@contextmanager
def temporary_pdf(content: bytes) -> Iterator[str]:
    """Write bytes to a random temporary PDF and always remove it afterward."""

    path: Path | None = None
    try:
        with NamedTemporaryFile(prefix="ipo-risk-", suffix=".pdf", delete=False) as handle:
            handle.write(content)
            path = Path(handle.name)
        yield str(path)
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def build_analysis_request(
    *,
    company_name: str,
    stock_code: str,
    listing_date: date | None,
    prospectus_path: str,
    use_mock: bool,
    workflow_version: str = "mvp_v1",
) -> IPOAnalysisRequest:
    """Build the only request object the UI sends to the service boundary."""

    return IPOAnalysisRequest(
        company_name=company_name,
        stock_code=stock_code,
        listing_date=listing_date,
        prospectus_path=prospectus_path,
        use_mock=use_mock,
        workflow_version=workflow_version,
    )


def all_risks(result: IPOAnalysisResult) -> list[RiskItem]:
    """Return every service-owned risk bucket without changing its status."""

    return [*result.verified_risks, *result.pending_risks, *result.rejected_risks]


def profile_payload(result: IPOAnalysisResult) -> dict[str, object]:
    """Normalize the Service profile metadata for stable UI display."""

    profile = dict(result.metadata.get("ipo_profile", {}))
    profile.setdefault("company_name", result.company_name)
    profile.setdefault("stock_code", result.stock_code)
    for key in ("listing_date", "industry", "issue_price", "issue_size"):
        if profile.get(key) in (None, ""):
            profile[key] = "Unavailable"
    profile_metadata = profile.get("metadata") or {}
    if isinstance(profile_metadata, dict):
        special = profile_metadata.get("special_security") or {}
        profile["security_category"] = (
            special.get("security_category", "Unavailable")
            if isinstance(special, dict)
            else "Unavailable"
        )
        profile["source"] = profile_metadata.get("source", "Unavailable")
        profile["match_status"] = profile_metadata.get(
            "official_match_status",
            profile_metadata.get("match_status", "Unavailable"),
        )
    return profile


def risk_status_counts(result: IPOAnalysisResult) -> dict[str, int]:
    """Count existing risk statuses without deriving or changing decisions."""

    counts = Counter(risk.verification_status.value for risk in all_risks(result))
    return {
        status: counts.get(status, 0)
        for status in ("verified", "needs_review", "pending", "rejected")
    }


def _llm_diagnostic_signals(value: object) -> tuple[bool, bool]:
    """Return whether existing diagnostics prove remote LLM success/failure."""

    if isinstance(value, dict):
        provider = str(value.get("llm_provider") or value.get("provider_name") or "")
        failure_kind = value.get("llm_failure_kind")
        internal_codes = value.get("internal_issue_codes") or []
        failed = bool(failure_kind) or any(
            str(code).startswith("llm_") for code in internal_codes
        )
        succeeded = provider not in {"", "mock", "unavailable"} and not failed
        for item in value.values():
            child_success, child_failure = _llm_diagnostic_signals(item)
            succeeded = succeeded or child_success
            failed = failed or child_failure
        return succeeded, failed
    if isinstance(value, (list, tuple)):
        succeeded = failed = False
        for item in value:
            child_success, child_failure = _llm_diagnostic_signals(item)
            succeeded = succeeded or child_success
            failed = failed or child_failure
        return succeeded, failed
    return False, False


def runtime_completion_status(result: IPOAnalysisResult) -> str:
    """Distinguish real-LLM completion from honest deterministic degradation."""

    configuration = result.metadata.get("configuration", {})
    modes = result.metadata.get("component_modes", {})
    provider = str(modes.get("llm_provider") or "")
    if configuration.get("runtime_mode") != "ai_enhanced" or provider in {
        "",
        "mock",
        "unavailable",
    }:
        return result.status.value

    diagnostics = result.metadata.get("component_diagnostics", {})
    synthesis = diagnostics.get("final_supervision_llm") or {}
    succeeded, failed = _llm_diagnostic_signals(diagnostics)
    synthesis_available = synthesis.get("status") == "available" and isinstance(
        synthesis.get("judgement"), dict
    )
    synthesis_failed = synthesis.get("status") == "unavailable"
    succeeded = succeeded or synthesis_available
    failed = failed or synthesis_failed
    if synthesis_available and not failed:
        return "completed_with_real_llm"
    if succeeded:
        return "completed_with_partial_llm"
    return "completed_with_deterministic_fallback"


def domain_payload(result: IPOAnalysisResult, domain: str) -> dict[str, object]:
    """Build a domain-specific, audit-friendly display payload."""

    if domain not in DOMAINS:
        raise ValueError(f"Unsupported risk domain: {domain}")
    risks = [risk for risk in all_risks(result) if risk.category.value == domain]
    counts = Counter(risk.verification_status.value for risk in risks)
    diagnostics = result.metadata.get("component_diagnostics", {}).get(domain, {})
    failed = any(error.component == domain for error in result.errors)
    return {
        "domain": domain,
        "status": "failed" if failed else ("completed" if risks else "no_risk_emitted"),
        "risk_count": len(risks),
        "status_counts": dict(counts),
        "diagnostics": diagnostics,
        "risks": [risk.model_dump(mode="json") for risk in risks],
    }


def component_statuses(result: IPOAnalysisResult) -> list[dict[str, object]]:
    """Expose configured modes and workflow outcomes as presentation-only rows."""

    modes = result.metadata.get("component_modes", {})
    diagnostics = result.metadata.get("component_diagnostics", {})
    components = (
        "parser",
        "retriever",
        "financial",
        "legal",
        "business",
        "verifier",
        "supervisor",
        "predictor",
        "report_generator",
        "llm_provider",
    )
    failed_components = {error.component for error in result.errors}
    rows: list[dict[str, object]] = []
    mode_aliases = {
        "financial": "financial_agent",
        "legal": "legal_agent",
        "business": "business_agent",
    }
    llm_status = runtime_completion_status(result)
    for component in components:
        mode = modes.get(mode_aliases.get(component, component), "Unavailable")
        component_diagnostic = diagnostics.get(component, {})
        failed = component in failed_components or (
            isinstance(component_diagnostic, dict)
            and component_diagnostic.get("failed") is True
        )
        if failed:
            status = "failed"
        elif component == "llm_provider" and llm_status == "completed_with_partial_llm":
            status = "partial"
        elif component == "llm_provider" and llm_status == "completed_with_deterministic_fallback":
            status = "degraded"
        elif mode == "unavailable":
            status = "unavailable"
        else:
            status = "completed"
        rows.append({"component": component, "mode": mode, "status": status})
    return rows


def safe_download_stem(stock_code: str) -> str:
    """Return a filesystem-safe report stem without exposing local paths."""

    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", stock_code.strip())
    return normalized.strip(".-") or "ipo"


def result_payload(result: IPOAnalysisResult) -> dict[str, object]:
    """Serialize service output without deriving financial values or risk states."""

    return {
        "status": result.status.value,
        "runtime_completion_status": runtime_completion_status(result),
        "profile": profile_payload(result),
        "component_modes": result.metadata.get("component_modes", {}),
        "component_statuses": component_statuses(result),
        "document": result.metadata.get("document", {}),
        "real_slice": result.metadata.get("real_slice", {}),
        "workflow_version": result.workflow_version,
        "configuration": result.metadata.get("configuration", {}),
        "supervision": result.metadata.get("supervision", {}),
        "market_context": result.metadata.get("market_context", {}),
        "market_intelligence": result.metadata.get("market_intelligence", {}),
        "model_prediction": result.metadata.get("model_prediction", {}),
        "final_supervision": result.metadata.get("final_supervision", {}),
        "governance": result.metadata.get("governance", {}),
        "component_diagnostics": result.metadata.get("component_diagnostics", {}),
        "risk_status_counts": risk_status_counts(result),
        "domains": {domain: domain_payload(result, domain) for domain in DOMAINS},
        "verified_risks": [item.model_dump(mode="json") for item in result.verified_risks],
        "pending_risks": [item.model_dump(mode="json") for item in result.pending_risks],
        "rejected_risks": [item.model_dump(mode="json") for item in result.rejected_risks],
        "prediction": result.prediction.model_dump(mode="json") if result.prediction else None,
        "report_sections": [item.model_dump(mode="json") for item in result.report_sections],
        "errors": [item.model_dump(mode="json") for item in result.errors],
        "agent_logs": [item.model_dump(mode="json") for item in result.agent_logs],
    }


def markdown_report(result: IPOAnalysisResult) -> str:
    """Render a complete audit report from existing structured service output."""

    profile = profile_payload(result)
    counts = risk_status_counts(result)
    prediction = result.prediction
    lines = [
        f"# {result.company_name} IPO Risk Analysis",
        "",
        "> Deterministic rule scores are not probabilities or investment advice.",
        "",
        "## Analysis identity",
        "",
        f"- Stock code: `{result.stock_code or 'Unavailable'}`",
        f"- Status: `{result.status.value}`",
        f"- Workflow: `{result.workflow_version}`",
        f"- Listing date: `{profile.get('listing_date', 'Unavailable')}`",
        f"- Industry: `{profile.get('industry', 'Unavailable')}`",
        f"- Rule score: `{prediction.risk_score if prediction else 'Unavailable'}`",
        f"- Rule level: `{prediction.risk_level.value if prediction else 'Unavailable'}`",
        f"- Verified / needs review / pending / rejected: "
        f"`{counts['verified']} / {counts['needs_review']} / {counts['pending']} / {counts['rejected']}`",
        "",
    ]
    for section in sorted(result.report_sections, key=lambda item: item.order):
        lines.extend([f"## {section.order}. {section.title}", "", section.summary, ""])
        render_risks = (
            section.risks
            if len(result.report_sections) < 10 or section.order in {3, 4, 5}
            else []
        )
        for risk in render_risks:
            lines.extend(
                [
                    f"### `{risk.risk_code}` — {risk.level.value} / {risk.score:g}",
                    "",
                    f"- Domain: `{risk.category.value}`",
                    f"- Verification: `{risk.verification_status.value}`",
                    f"- Verifier notes: {risk.verification_notes or 'Unavailable'}",
                    f"- Conclusion: {risk.conclusion}",
                ]
            )
            if risk.calculation is not None:
                calculation = risk.calculation
                lines.extend(
                    [
                        f"- Calculation formula: `{calculation.formula}`",
                        f"- Calculation inputs: `{json.dumps(calculation.inputs, ensure_ascii=False, default=str)}`",
                        f"- Calculation result: `{calculation.result} {calculation.unit}`",
                        f"- Calculation Evidence: `{', '.join(calculation.evidence_ids) or 'Unavailable'}`",
                    ]
                )
            for evidence in risk.evidence:
                lines.extend(
                    [
                        f"- Evidence `{evidence.evidence_id}` — PDF page {evidence.page or 'Unavailable'}",
                        f"  - {evidence.text}",
                    ]
                )
            lines.append("")
        if section.metadata:
            lines.extend(
                [
                    "<details><summary>Structured section metadata</summary>",
                    "",
                    "```json",
                    json.dumps(section.metadata, ensure_ascii=False, indent=2, default=str),
                    "```",
                    "</details>",
                    "",
                ]
            )
    lines.extend(
        [
            "## Runtime errors and limitations",
            "",
            *(f"- `{error.component}/{error.code}`: {error.message}" for error in result.errors),
        ]
    )
    if not result.errors:
        lines.append("- No structured runtime error was recorded.")
    return "\n".join(lines)