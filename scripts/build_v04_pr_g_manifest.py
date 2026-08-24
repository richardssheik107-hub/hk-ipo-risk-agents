"""Draft the PR-G freeze manifest from a real closed-loop run.

E owns PR-G and produces this draft; **A performs the freeze**.  The script
deliberately refuses to write into ``reports/frozen/`` so the gate-review action
stays with the Tech Lead.

The listing date is an explicit required input.  A freeze run must never use a
placeholder date because the PR-H governed Market-X path is point-in-time and
case identity/listing date are part of its provenance boundary.
"""
from __future__ import annotations

import argparse, hashlib, json
from dataclasses import replace
from datetime import date
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.core.config import load_settings
from ipo_risk.modeling.frozen_model_evidence import FROZEN_MANIFEST_NAME, load_frozen_cohort_evidence
from ipo_risk.schemas import IPOAnalysisRequest
from ipo_risk.services.analysis_service import IPOAnalysisService

PR_G_VERSION = "v04_pr_g_final_supervision_v1"
FROZEN_DIR_NAME = "frozen"


def _sha(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build(
    config: str,
    prospectus: Path,
    company: str,
    stock_code: str,
    listing_date: date,
    data_dir: Path,
) -> dict:
    settings = replace(load_settings(config), data_dir=str(data_dir))
    prospectus_sha256 = hashlib.sha256(prospectus.read_bytes()).hexdigest()
    # Parser chunk/Evidence identities derive from request_id. Bind it to the
    # governed case and actual bytes so repeated PR-H runs are deterministic.
    request_id = str(uuid5(
        NAMESPACE_URL,
        f"v04-real-e2e:{stock_code}:{listing_date.isoformat()}:{prospectus_sha256}",
    ))
    result = IPOAnalysisService(settings=settings).analyze(IPOAnalysisRequest(
        request_id=request_id,
        company_name=company,
        stock_code=stock_code,
        listing_date=listing_date,
        prospectus_path=str(prospectus),
        use_mock=False,
    ))
    final = result.metadata.get("final_supervision") or {}
    market = result.metadata.get("market_context") or {}
    evidence = load_frozen_cohort_evidence(Path(settings.report_dir) / FROZEN_DIR_NAME)
    synthesis = next((s for s in result.report_sections if s.order == 9), None)
    index = next((s for s in result.report_sections if s.title == "Evidence Index"), None)
    referenced = set(synthesis.metadata.get("referenced_evidence_ids", [])) if synthesis else set()
    indexed = {entry["evidence_id"] for entry in index.metadata.get("entries", [])} if index else set()
    return {
        "manifest_version": "v04_pr_g_freeze_manifest_v1",
        "pr_g_version": PR_G_VERSION,
        "status": "implementation_complete_awaiting_gate_review",
        "formal_gate_passed": False,  # only A may set this
        "config": config,
        "case_identity": {
            "company_name": company,
            "stock_code": stock_code,
            "listing_date": listing_date.isoformat(),
        },
        "channels": {
            "market_context": settings.market_context,
            "final_supervisor": settings.final_supervisor,
            "report_generator": settings.report_generator,
        },
        "closed_loop": {
            "prospectus_sha256": prospectus_sha256,
            "deterministic_request_id": request_id,
            "analysis_status": result.status.value,
            "report_section_count": len(result.report_sections),
            "verified_risk_count": len(result.verified_risks),
        },
        "channel_states": final.get("channel_states", []),
        "market_channel": {"status": market.get("status"), "reason": market.get("reason"),
                           "feature_manifest_hash": market.get("feature_manifest_hash")},
        "model_channel": {
            "per_case_score_available": final.get("model_prediction") is not None,
            "score_semantics": "uncalibrated_model_score",
            "frozen_pr_f_manifest": FROZEN_MANIFEST_NAME,
            "frozen_pr_f_manifest_hash": evidence.freeze_manifest_hash,
            "production_gain_interval": [evidence.production_gain.interval_low,
                                         evidence.production_gain.interval_high],
            "oracle_gain_interval": [evidence.oracle_gain.interval_low,
                                     evidence.oracle_gain.interval_high],
        },
        "traceability": {
            "referenced_evidence_count": len(referenced),
            "indexed_evidence_count": len(indexed),
            "all_references_resolve": referenced <= indexed,
        },
        "uncertainty_statement": final.get("uncertainty_statement", ""),
        "creates_no_new_risk": final.get("metadata", {}).get("creates_no_new_risk"),
        "probability_claimed": final.get("metadata", {}).get("probability_claimed"),
        "blind_2025_y_accessed": False,
        "final_supervision_content_hash": _sha(final),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/v04_offline.yaml")
    parser.add_argument("--prospectus", type=Path, required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--stock-code", required=True)
    parser.add_argument(
        "--listing-date",
        type=date.fromisoformat,
        required=True,
        metavar="YYYY-MM-DD",
        help="authoritative listing date for this exact IPO case",
    )
    parser.add_argument("--data-dir", type=Path, default=Path("reports/v04_pr_g/repo"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v04_pr_g"))
    args = parser.parse_args()
    if args.output_dir.resolve().name == FROZEN_DIR_NAME:
        parser.error("E drafts this manifest; freezing it into reports/frozen/ is A's gate-review action")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build(
        args.config,
        args.prospectus,
        args.company,
        args.stock_code,
        args.listing_date,
        args.data_dir,
    )
    target = args.output_dir / "v04_pr_g_manifest_draft.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"status={manifest['closed_loop']['analysis_status']} "
          f"sections={manifest['closed_loop']['report_section_count']} "
          f"traceable={manifest['traceability']['all_references_resolve']} draft={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
