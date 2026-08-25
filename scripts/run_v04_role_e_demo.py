"""Run the E-lane competition chain over the declared demo cases.

For each case with a locally available prospectus this executes the full
governed chain -- parse, agents, verifier, Document Supervisor, governed market
context, rule signal, conflict detection, one bounded targeted re-check per
conflict, LLM Final Supervisor synthesis and trace assembly -- and writes the
per-case artifacts the submission package needs.

A declared case whose PDF is not present locally is reported as
``unavailable_prospectus``.  Nothing is substituted, mocked or quietly dropped:
the summary states how many of the declared cases actually ran.

The request identity is derived from the governed case, its listing date and the
prospectus bytes, so two runs of the same case produce the same Evidence
identities and the same Final Supervisor content hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.core.config import load_settings
from ipo_risk.schemas import IPOAnalysisRequest, IPOAnalysisResult
from ipo_risk.services.analysis_service import IPOAnalysisService

DEMO_VERSION = "v045_role_e_demo_v1"
DEFAULT_CASES = Path("configs/v045_demo_cases.json")
DEFAULT_CONFIG = "configs/v045_competition_offline.yaml"
DEFAULT_OUTPUT = Path("reports/v045_role_e")


def _sha(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def deterministic_request_id(stock_code: str, listing_date: date, prospectus_sha256: str) -> str:
    """Same identity convention the PR-G/PR-H freeze runs use."""

    return str(
        uuid5(NAMESPACE_URL, f"v04-real-e2e:{stock_code}:{listing_date.isoformat()}:{prospectus_sha256}")
    )


def run_case(case: dict, config: str, output_dir: Path) -> dict:
    prospectus = Path(case["prospectus_path"])
    if not prospectus.exists():
        return {
            "case_id": case["case_id"],
            "stock_code": case["stock_code"],
            "status": "unavailable_prospectus",
            "reason": f"declared prospectus is not present locally: {prospectus}",
        }
    listing_date = date.fromisoformat(case["listing_date"])
    prospectus_sha256 = hashlib.sha256(prospectus.read_bytes()).hexdigest()
    request_id = deterministic_request_id(case["stock_code"], listing_date, prospectus_sha256)
    settings = load_settings(config)
    result = IPOAnalysisService(settings=settings).analyze(
        IPOAnalysisRequest(
            request_id=request_id,
            company_name=case["company_name"],
            stock_code=case["stock_code"],
            listing_date=listing_date,
            prospectus_path=str(prospectus),
            use_mock=False,
        )
    )
    return _write_artifacts(case, result, config, prospectus_sha256, request_id, output_dir)


def _write_artifacts(
    case: dict,
    result: IPOAnalysisResult,
    config: str,
    prospectus_sha256: str,
    request_id: str,
    output_dir: Path,
) -> dict:
    diagnostics = result.metadata.get("component_diagnostics", {})
    runtime = diagnostics.get("competition_runtime", {})
    final = result.metadata.get("final_supervision", {})
    supervision_llm = diagnostics.get("final_supervision_llm", {})
    conflicts = diagnostics.get("conflict_detection", {})
    rechecks = diagnostics.get("targeted_recheck", {})

    case_dir = output_dir / case["case_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "analysis_result.json": json.loads(result.model_dump_json()),
        "final_supervision.json": {"composition": final, "llm_synthesis": supervision_llm},
        "conflicts.json": conflicts,
        "rechecks.json": rechecks,
        "trace_sidecar.json": runtime.get("sidecar"),
        "traceability.json": runtime.get("traceability"),
    }
    for name, payload in artifacts.items():
        (case_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (case_dir / "case_report.md").write_text(_markdown(case, result), encoding="utf-8")

    conflict_statuses: dict[str, int] = {}
    for conflict in conflicts.get("conflicts", []):
        conflict_statuses[conflict["status"]] = conflict_statuses.get(conflict["status"], 0) + 1
    return {
        "case_id": case["case_id"],
        "stock_code": case["stock_code"],
        "listing_date": case["listing_date"],
        "status": result.status.value,
        "config": config,
        "prospectus_sha256": prospectus_sha256,
        "deterministic_request_id": request_id,
        "analysis_id": result.analysis_id,
        "verified_risk_count": len(result.verified_risks),
        "pending_risk_count": len(result.pending_risks),
        "report_section_count": len(result.report_sections),
        "channel_states": {
            item["channel"]: item["status"] for item in final.get("channel_states", [])
        },
        "conflict_count": conflicts.get("conflict_count", 0),
        "conflict_statuses": conflict_statuses,
        "recheck_attempted": rechecks.get("attempted", 0),
        "llm_synthesis_status": supervision_llm.get("status"),
        "llm_synthesis_reason": supervision_llm.get("reason"),
        "deterministic_severity_floor": supervision_llm.get("deterministic_severity_floor"),
        "traceability": runtime.get("traceability"),
        "final_supervision_content_hash": _sha(final),
        "probability_claimed": final.get("metadata", {}).get("probability_claimed"),
        "creates_no_new_risk": final.get("metadata", {}).get("creates_no_new_risk"),
        "artifact_dir": str(case_dir),
    }


def _markdown(case: dict, result: IPOAnalysisResult) -> str:
    diagnostics = result.metadata.get("component_diagnostics", {})
    conflicts = diagnostics.get("conflict_detection", {}).get("conflicts", [])
    supervision = diagnostics.get("final_supervision_llm", {})
    lines = [
        f"# {case['company_name']} ({case['stock_code']}) — Competition case report",
        "",
        f"- case_id: `{case['case_id']}`",
        f"- listing_date: `{case['listing_date']}`",
        f"- analysis status: `{result.status.value}`",
        f"- verified risks: {len(result.verified_risks)}; pending: {len(result.pending_risks)}",
        "",
        "## Verified risks",
        "",
    ]
    if result.verified_risks:
        for risk in result.verified_risks:
            lines.append(
                f"- **{risk.risk_code}** · {risk.level.value} · {risk.verification_status.value} · "
                f"{len(risk.evidence)} evidence — {risk.conclusion}"
            )
    else:
        lines.append("- none")
    lines += ["", "## Cross-agent conflicts and targeted re-check", ""]
    if conflicts:
        for conflict in conflicts:
            lines.append(f"- `{conflict['status']}` — {conflict['summary']}")
            if conflict.get("resolution_note"):
                lines.append(f"  - re-check: {conflict['resolution_note']}")
    else:
        lines.append("- no cross-agent conflict was detected in this run")
    lines += [
        "",
        "## Final Supervisor",
        "",
        f"- LLM synthesis: `{supervision.get('status')}` — {supervision.get('reason')}",
        f"- deterministic severity floor: `{supervision.get('deterministic_severity_floor')}`",
        "",
        "The rule and model scores are not probabilities. This report is not investment, legal or",
        "listing advice.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case-id", action="append", default=None, help="run only these case ids")
    arguments = parser.parse_args()

    manifest = json.loads(arguments.cases.read_text(encoding="utf-8"))
    cases = [
        case for case in manifest["cases"]
        if arguments.case_id is None or case["case_id"] in set(arguments.case_id)
    ]
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    results = [run_case(case, arguments.config, arguments.output_dir) for case in cases]
    executed = [item for item in results if item["status"] != "unavailable_prospectus"]
    summary = {
        "demo_version": DEMO_VERSION,
        "config": arguments.config,
        "cases_manifest": str(arguments.cases),
        "cases_manifest_version": manifest.get("manifest_version"),
        "declared_case_count": len(cases),
        "executed_case_count": len(executed),
        "unavailable_case_count": len(cases) - len(executed),
        "minimum_required_demo_cases": 3,
        "minimum_demo_cases_met": len(executed) >= 3,
        "blind_2025_y_accessed": False,
        "cases": results,
    }
    (arguments.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    # A missing local prospectus is a declared, reported state, not a script
    # failure; the summary is what records whether the demo bar was met.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
