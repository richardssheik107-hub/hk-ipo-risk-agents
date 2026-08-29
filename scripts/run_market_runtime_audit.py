"""Audit the Market-X runtime over the whole governed universe and fresh cases.

Two questions, one command:

``historical``
    every officially identified case in the committed bridge is resolved and run
    through the same composed provider the product uses -- frozen PR-B first,
    dynamic point-in-time build for anything outside it -- and classified as
    available / partial / unavailable / error.  Three hand-picked companies
    prove nothing about generalization; this covers the universe.

``fresh``
    synthetic new-IPO probes that must degrade honestly: a listing beyond the
    universe's coverage end, a prospectus with no listing date, an issuer absent
    from the catalog, a case with no industry, and an identity that disagrees
    with the governed row.

``--strict`` fails the run when any governed case errors, when a missing feature
carries a value, or when any absent feature lacks a stated reason.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ipo_risk.agents.dynamic_market_context import DynamicPITMarketContextProvider
from ipo_risk.agents.market_context import GovernedPRBMarketContextProvider
from ipo_risk.agents.market_context import FAILURE_OTHER
from ipo_risk.market.dynamic_extended import DynamicExtendedMarketSource
from ipo_risk.market.handoff import (
    MarketFeatureHandoffError,
    MarketHandoffBindingError,
    build_market_feature_handoff,
    verify_market_handoff_binding,
)
from ipo_risk.core.config import load_settings
from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
)
from ipo_risk.market.prior_ipo_history import load_official_prior_ipo_history
from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_FEATURE_COUNT = len(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER)


def _rooted(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _classify(view: MarketContextView) -> str:
    if view.status is ChannelStatus.UNAVAILABLE_ERROR:
        return "error"
    if view.status is not ChannelStatus.AVAILABLE:
        return "unavailable"
    available = sum(item.availability == "available" for item in view.observations)
    core = sum(
        item.availability == "available"
        and item.name in set(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER)
        for item in view.observations
    )
    if core == CORE_FEATURE_COUNT:
        return "available"
    return "partial" if available else "unavailable"


def _integrity_violations(view: MarketContextView) -> list[str]:
    """A missing feature must stay null and must say why it is missing."""

    problems: list[str] = []
    for item in view.observations:
        if item.availability == "available":
            continue
        if item.value is not None:
            problems.append(f"{item.name}:missing_feature_carries_value")
        if not item.missing_reason:
            problems.append(f"{item.name}:missing_feature_has_no_reason")
    return problems


def _row(case: dict[str, str], view: MarketContextView) -> dict[str, Any]:
    provenance = view.provenance
    available = [
        item.name for item in view.observations if item.availability == "available"
    ]
    return {
        "case_id": case["case_id"],
        "stock_code": case["stock_code"],
        "listing_date": case["listing_date"],
        "listing_year": case["listing_date"][:4],
        "classification": _classify(view),
        "channel_status": view.status.value,
        "runtime_path": provenance.get("runtime_path", ""),
        "identity_source": provenance.get("identity_source", ""),
        "available_observation_count": len(available),
        "missing_observation_count": len(view.observations) - len(available),
        "feature_manifest_hash": view.feature_manifest_hash or "",
        "artifact_content_hash": provenance.get("artifact_content_hash", ""),
        "reason_code": provenance.get("reason_code", ""),
        "failure_code": provenance.get("failure_code", ""),
        "model_handoff": case.get("model_handoff", ""),
        "reason": view.reason,
        "integrity_violations": ";".join(_integrity_violations(view)),
    }


def _model_handoff_state(view: MarketContextView, frozen_dir: Path) -> str:
    """Can the model lane build a frozen model input from this view, or not?"""

    try:
        handoff = build_market_feature_handoff(view)
    except MarketFeatureHandoffError:
        return "not_projectable"
    try:
        verify_market_handoff_binding(handoff, frozen_dir=frozen_dir)
    except MarketHandoffBindingError:
        return "binding_failed"
    return "bound"


def _historical(
    provider, bridge_path: Path, frozen_dir: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with bridge_path.open(encoding="utf-8-sig", newline="") as handle:
        bridge_rows = list(csv.DictReader(handle))

    rows: list[dict[str, Any]] = []
    unresolvable: list[str] = []
    for row in bridge_rows:
        listing = (row.get("official_listed_date") or "").strip()
        code = (row.get("stock_code_wind") or "").strip()
        if (row.get("official_match_status") or "matched").strip() != "matched" or not listing or not code:
            unresolvable.append(row.get("case_id", ""))
            continue
        profile = IPOProfile(
            company_name=(row.get("selected_name") or "").strip(),
            stock_code=code,
            listing_date=date.fromisoformat(listing),
            industry=(row.get("official_industry_name") or "").strip(),
            metadata={"case_id": row["case_id"]},
        )
        view = provider.context(profile)
        rows.append(
            _row(
                {
                    "case_id": row["case_id"],
                    "stock_code": code,
                    "listing_date": listing,
                    "model_handoff": _model_handoff_state(view, frozen_dir),
                },
                view,
            )
        )

    rows.sort(key=lambda item: item["case_id"])
    classifications = Counter(item["classification"] for item in rows)
    summary = {
        "governed_case_count": len(rows),
        "identity_unresolvable_count": len(unresolvable),
        "identity_unresolvable_case_ids": sorted(filter(None, unresolvable)),
        "available": classifications["available"],
        "partial": classifications["partial"],
        "unavailable": classifications["unavailable"],
        "error": classifications["error"],
        "by_runtime_path": dict(sorted(Counter(item["runtime_path"] for item in rows).items())),
        "by_listing_year": {
            year: dict(
                sorted(
                    Counter(
                        item["classification"]
                        for item in rows
                        if item["listing_year"] == year
                    ).items()
                )
            )
            for year in sorted({item["listing_year"] for item in rows})
        },
        "integrity_violation_count": sum(bool(item["integrity_violations"]) for item in rows),
        # Role-C 4.3 asks for the failure kinds by name, not one "error" bucket.
        "by_failure_code": dict(
            sorted(
                Counter(
                    item["failure_code"] or FAILURE_OTHER
                    for item in rows
                    if item["classification"] == "error"
                ).items()
            )
        ),
        "by_model_handoff": dict(
            sorted(Counter(item["model_handoff"] for item in rows).items())
        ),
    }
    return rows, summary


def _fresh(provider, bridge_path: Path, frozen_dir: Path) -> list[dict[str, Any]]:
    history = load_official_prior_ipo_history(bridge_path)
    covered = history.history_end_date - timedelta(days=30)
    beyond = history.history_end_date + timedelta(days=180)
    with bridge_path.open(encoding="utf-8-sig", newline="") as handle:
        governed = next(
            row
            for row in csv.DictReader(handle)
            if (row.get("official_listed_date") or "").strip()
            and (row.get("official_match_status") or "matched").strip() == "matched"
        )

    probes = [
        (
            "new_issuer_inside_coverage",
            "an issuer absent from the catalog, listing inside the covered window",
            IPOProfile(
                company_name="Fresh Issuer Ltd",
                stock_code="9999.HK",
                listing_date=covered,
                industry="软件服务",
            ),
        ),
        (
            "new_issuer_without_industry",
            "the same case with no industry classification",
            IPOProfile(
                company_name="Fresh Issuer Ltd",
                stock_code="9999.HK",
                listing_date=covered,
            ),
        ),
        (
            "listing_beyond_coverage_end",
            "a listing after the governed universe's coverage end",
            IPOProfile(
                company_name="Future Issuer Ltd",
                stock_code="9998.HK",
                listing_date=beyond,
                industry="软件服务",
            ),
        ),
        (
            "missing_listing_date",
            "a prospectus with no listing date, so no point-in-time cutoff",
            IPOProfile(company_name="Undated Issuer Ltd", stock_code="9997.HK"),
        ),
        (
            "identity_mismatch",
            "a governed case_id paired with a contradicting stock code",
            IPOProfile(
                company_name="Mismatched Issuer",
                stock_code="9996.HK",
                listing_date=date.fromisoformat(governed["official_listed_date"]),
                metadata={"case_id": governed["case_id"]},
            ),
        ),
    ]

    results: list[dict[str, Any]] = []
    for probe_id, description, profile in probes:
        view = provider.context(profile)
        results.append(
            {
                "probe_id": probe_id,
                "description": description,
                "channel_status": view.status.value,
                "classification": _classify(view),
                "runtime_path": view.provenance.get("runtime_path", ""),
                "reason_code": view.provenance.get("reason_code", ""),
                "failure_code": view.provenance.get("failure_code", ""),
                "reason": view.reason,
                "available_features": [
                    item.name
                    for item in view.observations
                    if item.availability == "available"
                ],
                "missing_reasons": {
                    item.name: item.missing_reason
                    for item in view.observations
                    if item.availability != "available"
                },
                "model_handoff": _model_handoff_state(view, frozen_dir),
                "integrity_violations": _integrity_violations(view),
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/v045_competition_offline.yaml")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "reports" / "v046_market_runtime",
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    settings = load_settings(str(_rooted(args.config)))
    bridge_path = _rooted(settings.market_official_bridge)
    provider = GovernedPRBMarketContextProvider(
        feature_dir=_rooted(settings.market_feature_dir),
        official_bridge_path=bridge_path,
        extended_readiness_path=(
            _rooted(settings.market_extended_readiness)
            if settings.market_extended_readiness
            else None
        ),
        new_case_provider=DynamicPITMarketContextProvider(
            official_bridge_path=bridge_path,
            outcome_pack_path=(
                _rooted(settings.market_dynamic_outcome_pack)
                if settings.market_dynamic_outcome_pack
                else None
            ),
            extended_source=(
                DynamicExtendedMarketSource(
                    hsi_normalized_csv=_rooted(
                        settings.market_dynamic_extended_hsi_csv
                    ),
                    turnover_normalized_csv=_rooted(
                        settings.market_dynamic_extended_turnover_csv
                    ),
                    hsi_manifest=_rooted("data/catalog/csmar_hsi_source_manifest.json"),
                    external_manifest=_rooted(
                        "data/catalog/v04_c_external_market_source_manifest.json"
                    ),
                )
                if settings.market_dynamic_extended_hsi_csv
                and settings.market_dynamic_extended_turnover_csv
                else None
            ),
        ),
    )

    frozen_dir = _rooted(settings.report_dir) / "frozen"
    rows, summary = _historical(provider, bridge_path, frozen_dir)
    fresh = _fresh(provider, bridge_path, frozen_dir)
    history = load_official_prior_ipo_history(
        bridge_path,
        outcome_pack_path=(
            _rooted(settings.market_dynamic_outcome_pack)
            if settings.market_dynamic_outcome_pack
            else None
        ),
    )
    payload = {
        "config": args.config,
        "historical_summary": summary,
        "prior_ipo_history": {
            "history_start_date": history.history_start_date.isoformat(),
            "history_end_date": history.history_end_date.isoformat(),
            "record_count": len(history.records),
            "outcome_history_available": history.outcome_history_available,
            "outcome_cohort_years": list(history.outcome_cohort_years),
            "provenance": history.provenance,
        },
        "fresh_case_probes": fresh,
        "historical_cases": rows,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "historical_market_runtime_audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fieldnames = list(rows[0]) if rows else []
    with (args.output_dir / "historical_market_runtime_audit.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    violations = summary["integrity_violation_count"] + sum(
        bool(item["integrity_violations"]) for item in fresh
    )
    failed = bool(summary["error"]) or bool(violations)
    print(
        json.dumps(
            {
                "status": "fail" if (args.strict and failed) else "pass",
                "output_dir": str(args.output_dir),
                "historical_summary": summary,
                "fresh_case_classifications": {
                    item["probe_id"]: (
                        item["failure_code"] or item["classification"]
                    )
                    for item in fresh
                },
                "by_failure_code": summary["by_failure_code"],
                "by_model_handoff": summary["by_model_handoff"],
                "integrity_violation_count": violations,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 2 if (args.strict and failed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
