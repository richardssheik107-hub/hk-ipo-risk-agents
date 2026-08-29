"""Audit the frozen model as a runtime, not as three replayed rows.

Four questions, one command:

``model load``
    the committed package loads, and its hashes still chain to the V2 promotion
    manifest that A merged.

``published parity``
    every case the promotion already published is re-scored through the loaded
    booster and the live market handoff, and must reproduce the published score,
    alert and native SHAP drivers.  Only the label-free columns are read; the
    outcome columns of ``test_predictions.csv`` are never opened.

``historical universe``
    every officially identified governed case is pushed through market context
    -> handoff -> frozen inference -> native SHAP, and classified.  This is what
    separates a generalizing runtime from a per-case handoff.

``fresh``
    new-IPO probes, including listings outside the frozen universe, which must
    either infer for real or say exactly why they cannot.

``--strict`` fails the run on any inference error, any parity mismatch, any
missing-feature integrity violation, or any degenerate SHAP output.
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
from ipo_risk.core.config import load_settings
from ipo_risk.market.dynamic_extended import DynamicExtendedMarketSource
from ipo_risk.market.handoff import (
    MarketFeatureHandoffError,
    MarketHandoffBindingError,
    build_market_feature_handoff,
)
from ipo_risk.market.prior_ipo_history import load_official_prior_ipo_history
from ipo_risk.modeling.dynamic_model_runtime import (
    DYNAMIC_MODEL_RUNTIME_VERSION,
    DynamicModelRuntimeError,
    infer_batch,
    load_frozen_model_bundle,
)
from ipo_risk.modeling.role_d_v2_model_artifact import (
    DEFAULT_MODEL_DIR,
    SINGLE_CASE_ALERT_POLICY_VERSION,
)
from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_PREDICTIONS = Path("reports/v045_role_d_v2/test_predictions.csv")
FINAL_THREE = ("ipo_2024_02410", "ipo_2024_02460", "ipo_2024_01318")
SCORE_TOLERANCE = 1e-12
SHAP_TOLERANCE = 1e-12


def _rooted(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _build_market_provider(settings) -> tuple[GovernedPRBMarketContextProvider, Path]:
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
                    hsi_normalized_csv=_rooted(settings.market_dynamic_extended_hsi_csv),
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
    return provider, bridge_path


def _handoff_or_reason(view: MarketContextView) -> tuple[dict[str, Any] | None, str]:
    if view.status is not ChannelStatus.AVAILABLE:
        return None, f"market_channel_{view.status.value}"
    try:
        return build_market_feature_handoff(view), ""
    except MarketFeatureHandoffError as exc:
        return None, f"market_handoff_not_projectable: {exc}"


def _bridge_profiles(bridge_path: Path) -> list[IPOProfile]:
    with bridge_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    profiles: list[IPOProfile] = []
    for row in rows:
        listing = (row.get("official_listed_date") or "").strip()
        code = (row.get("stock_code_wind") or "").strip()
        if (row.get("official_match_status") or "matched").strip() != "matched":
            continue
        if not listing or not code:
            continue
        profiles.append(
            IPOProfile(
                company_name=(row.get("selected_name") or "").strip(),
                stock_code=code,
                listing_date=date.fromisoformat(listing),
                industry=(row.get("official_industry_name") or "").strip(),
                metadata={"case_id": row["case_id"]},
            )
        )
    profiles.sort(key=lambda profile: profile.metadata["case_id"])
    return profiles


def _infer_profiles(
    profiles: list[IPOProfile],
    *,
    provider,
    bundle,
    frozen_dir: Path,
    use_batch_alert_policy: bool,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Resolve market context for each profile, then score every bound case once."""

    rows: list[dict[str, Any]] = []
    handoffs: list[dict[str, Any]] = []
    for profile in profiles:
        case_id = profile.metadata.get("case_id", "")
        view = provider.context(profile)
        handoff, reason = _handoff_or_reason(view)
        row = {
            "case_id": case_id,
            "listing_year": profile.listing_date.isoformat()[:4] if profile.listing_date else "",
            "market_status": view.status.value,
            "market_runtime_path": view.provenance.get("runtime_path", ""),
            "model_status": "unavailable" if handoff is None else "pending",
            "failure_code": reason,
        }
        if handoff is not None:
            handoffs.append(handoff)
        rows.append(row)

    signals_by_case: dict[str, dict[str, Any]] = {}
    if handoffs:
        try:
            signals = infer_batch(
                handoffs,
                bundle=bundle,
                frozen_dir=frozen_dir,
                use_batch_alert_policy=use_batch_alert_policy,
            )
        except DynamicModelRuntimeError as exc:
            for row in rows:
                if row["model_status"] == "pending":
                    row.update({"model_status": "error", "failure_code": f"inference_error: {exc}"})
            return rows, signals_by_case
        signals_by_case = {str(signal["case_id"]): signal for signal in signals}

    for row in rows:
        signal = signals_by_case.get(row["case_id"])
        if signal is None:
            if row["model_status"] == "pending":
                row.update({"model_status": "error", "failure_code": "case_lost_during_inference"})
            continue
        available = signal["status"] == ChannelStatus.AVAILABLE.value
        row.update(
            {
                "model_status": "available" if available else "unavailable",
                "failure_code": "" if available else str(signal.get("reason") or ""),
                "score": signal.get("score"),
                "alert": signal.get("alert"),
                "alert_policy": signal.get("alert_policy"),
                "driver_count": len(signal.get("drivers") or ()),
                "available_model_feature_count": signal.get("available_model_feature_count"),
                "missing_model_features": ";".join(signal.get("missing_model_features") or ()),
                "input_feature_hash": signal.get("input_feature_hash"),
                "inference_run_id": signal.get("inference_run_id"),
            }
        )
    return rows, signals_by_case


def _published_rows(path: Path) -> list[dict[str, Any]]:
    """Read only the label-free columns of the published predictions."""

    with path.open(encoding="utf-8", newline="") as handle:
        return [
            {
                "case_id": row["case_id"],
                "score": float(row["poor_performer_score"]),
                "alert": row["predicted_significant_drop_5d"].lower() == "true",
                "alert_policy": row["alert_policy_version"],
                "drivers": json.loads(row["top_shap_drivers_json"]),
            }
            for row in csv.DictReader(handle)
        ]


def _parity(
    published: list[dict[str, Any]],
    signals: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    max_score_delta = 0.0
    max_shap_delta = 0.0
    compared = 0
    for row in published:
        signal = signals.get(row["case_id"])
        if signal is None or signal["status"] != ChannelStatus.AVAILABLE.value:
            mismatches.append({"case_id": row["case_id"], "problem": "not_inferable_at_runtime"})
            continue
        compared += 1
        score_delta = abs(float(signal["score"]) - row["score"])
        max_score_delta = max(max_score_delta, score_delta)
        if score_delta > SCORE_TOLERANCE:
            mismatches.append(
                {"case_id": row["case_id"], "problem": "score", "delta": score_delta}
            )
        if bool(signal["alert"]) != row["alert"]:
            mismatches.append({"case_id": row["case_id"], "problem": "alert"})
        if signal["alert_policy"] != row["alert_policy"]:
            mismatches.append({"case_id": row["case_id"], "problem": "alert_policy"})
        published_drivers = {item["feature"]: item for item in row["drivers"]}
        runtime_drivers = {item["feature"]: item for item in signal["drivers"]}
        if set(published_drivers) != set(runtime_drivers):
            mismatches.append({"case_id": row["case_id"], "problem": "driver_feature_set"})
            continue
        if [item["feature"] for item in row["drivers"]] != [
            item["feature"] for item in signal["drivers"]
        ]:
            mismatches.append({"case_id": row["case_id"], "problem": "driver_ranking"})
        for feature, item in published_drivers.items():
            delta = abs(float(runtime_drivers[feature]["shap_value"]) - float(item["shap_value"]))
            max_shap_delta = max(max_shap_delta, delta)
            if delta > SHAP_TOLERANCE:
                mismatches.append(
                    {"case_id": row["case_id"], "problem": f"shap:{feature}", "delta": delta}
                )
    return {
        "source": str(PUBLISHED_PREDICTIONS),
        "published_case_count": len(published),
        "compared_case_count": compared,
        "outcome_columns_read": False,
        "max_score_delta": max_score_delta,
        "max_shap_delta": max_shap_delta,
        "score_tolerance": SCORE_TOLERANCE,
        "shap_tolerance": SHAP_TOLERANCE,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:20],
        "passed": not mismatches and compared == len(published),
    }


def _fresh_probes(bridge_path: Path) -> list[tuple[str, str, IPOProfile]]:
    history = load_official_prior_ipo_history(bridge_path)
    covered = history.history_end_date - timedelta(days=30)
    beyond = history.history_end_date + timedelta(days=180)
    return [
        (
            "new_issuer_inside_coverage",
            "an issuer absent from the frozen universe, listing inside coverage",
            IPOProfile(
                company_name="Fresh Issuer Ltd",
                stock_code="9999.HK",
                listing_date=covered,
                industry="软件服务",
            ),
        ),
        (
            "new_issuer_without_industry",
            "the same case with no industry, so the industry families go missing",
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
            "a prospectus with no listing date, so there is no point-in-time cutoff",
            IPOProfile(company_name="Undated Issuer Ltd", stock_code="9997.HK"),
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/v045_competition_offline.yaml")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument(
        "--output-dir", type=Path, default=REPO_ROOT / "reports" / "v046_dynamic_model_runtime"
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="run the audit without rewriting the committed evidence artifacts",
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    settings = load_settings(str(_rooted(args.config)))
    frozen_dir = _rooted(settings.report_dir) / "frozen"
    provider, bridge_path = _build_market_provider(settings)

    try:
        bundle = load_frozen_model_bundle(
            model_dir=_rooted(args.model_dir), frozen_dir=frozen_dir
        )
    except DynamicModelRuntimeError as exc:
        payload = {
            "status": "fail",
            "runtime_version": DYNAMIC_MODEL_RUNTIME_VERSION,
            "model_load": {"loaded": False, "error": str(exc)},
            "runtime_inference": False,
            "native_shap": False,
            "uses_frozen_model": False,
            "per_case_handoff_only": True,
            "blind_2025_y_accessed": False,
        }
        if not args.no_write:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            (args.output_dir / "dynamic_model_runtime_audit.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 2

    profiles = _bridge_profiles(bridge_path)
    historical_rows, historical_signals = _infer_profiles(
        profiles,
        provider=provider,
        bundle=bundle,
        frozen_dir=frozen_dir,
        use_batch_alert_policy=False,
    )

    published = _published_rows(_rooted(PUBLISHED_PREDICTIONS))
    published_ids = {row["case_id"] for row in published}
    cohort_profiles = [
        profile for profile in profiles if profile.metadata.get("case_id") in published_ids
    ]
    _, cohort_signals = _infer_profiles(
        cohort_profiles,
        provider=provider,
        bundle=bundle,
        frozen_dir=frozen_dir,
        use_batch_alert_policy=True,
    )
    parity = _parity(published, cohort_signals)

    fresh_rows: list[dict[str, Any]] = []
    for probe_id, description, profile in _fresh_probes(bridge_path):
        view = provider.context(profile)
        handoff, reason = _handoff_or_reason(view)
        entry: dict[str, Any] = {
            "probe_id": probe_id,
            "description": description,
            "market_status": view.status.value,
            "market_runtime_path": view.provenance.get("runtime_path", ""),
        }
        if handoff is None:
            entry.update({"model_status": "unavailable", "failure_code": reason})
        else:
            try:
                signal = infer_batch(
                    [handoff], bundle=bundle, frozen_dir=frozen_dir
                )[0]
            except (DynamicModelRuntimeError, MarketHandoffBindingError) as exc:
                entry.update({"model_status": "error", "failure_code": str(exc)})
            else:
                available = signal["status"] == ChannelStatus.AVAILABLE.value
                entry.update(
                    {
                        "model_status": "available" if available else "unavailable",
                        "failure_code": "" if available else str(signal.get("reason") or ""),
                        "score": signal.get("score"),
                        "alert": signal.get("alert"),
                        "alert_policy": signal.get("alert_policy"),
                        "driver_count": len(signal.get("drivers") or ()),
                        "missing_model_features": list(signal.get("missing_model_features") or ()),
                    }
                )
        fresh_rows.append(entry)

    statuses = Counter(row["model_status"] for row in historical_rows)
    available_rows = [row for row in historical_rows if row["model_status"] == "available"]
    outside_handoff = [row for row in available_rows if row["case_id"] not in FINAL_THREE]
    degenerate_shap = [
        row["case_id"]
        for row in available_rows
        if row.get("driver_count") != len(bundle.model_feature_names)
    ]
    partial_inputs = [
        row for row in available_rows if row.get("missing_model_features")
    ]
    failure_codes = Counter(
        row["failure_code"].split(":")[0]
        for row in historical_rows
        if row["model_status"] != "available" and row["failure_code"]
    )

    fresh_available = [row for row in fresh_rows if row["model_status"] == "available"]
    native_shap = bool(available_rows) and not degenerate_shap and parity["passed"]
    runtime_inference = bool(outside_handoff) and bool(fresh_available)
    failed = (
        bool(statuses["error"])
        or not parity["passed"]
        or not native_shap
        or not runtime_inference
        or any(row["model_status"] == "error" for row in fresh_rows)
    )

    payload = {
        "status": "fail" if failed else "pass",
        "runtime_version": DYNAMIC_MODEL_RUNTIME_VERSION,
        "config": args.config,
        "runtime_inference": runtime_inference,
        "native_shap": native_shap,
        "uses_frozen_model": True,
        "per_case_handoff_only": False,
        "blind_2025_y_accessed": False,
        "model_load": {
            "loaded": True,
            "model_dir": str(args.model_dir),
            "identity": bundle.identity,
            "single_case_alert_policy": SINGLE_CASE_ALERT_POLICY_VERSION,
            "single_case_cutoff": bundle.alert_policy["single_case_policy"]["cutoff"],
            "batch_alert_policy": bundle.alert_policy["batch_policy"]["version"],
            "retrained_at_runtime": False,
        },
        "published_parity": parity,
        "historical_summary": {
            "governed_case_count": len(historical_rows),
            "inference_available": statuses["available"],
            "inference_unavailable": statuses["unavailable"],
            "inference_error": statuses["error"],
            "available_outside_the_per_case_handoff": len(outside_handoff),
            "available_with_partial_model_input": len(partial_inputs),
            "degenerate_shap_case_ids": degenerate_shap,
            "by_failure_code": dict(sorted(failure_codes.items())),
            "by_listing_year": {
                year: dict(
                    sorted(
                        Counter(
                            row["model_status"]
                            for row in historical_rows
                            if row["listing_year"] == year
                        ).items()
                    )
                )
                for year in sorted({row["listing_year"] for row in historical_rows})
            },
            "alert_count": sum(bool(row.get("alert")) for row in available_rows),
        },
        "fresh_case_probes": fresh_rows,
        "historical_cases": historical_rows,
    }

    if not args.no_write:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "dynamic_model_runtime_audit.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        fieldnames = sorted({key for row in historical_rows for key in row})
        with (args.output_dir / "dynamic_model_runtime_audit.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(historical_rows)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "output_dir": str(args.output_dir),
                "published_parity": {
                    "compared_case_count": parity["compared_case_count"],
                    "mismatch_count": parity["mismatch_count"],
                    "max_score_delta": parity["max_score_delta"],
                    "max_shap_delta": parity["max_shap_delta"],
                },
                "historical_summary": {
                    key: value
                    for key, value in payload["historical_summary"].items()
                    if key not in ("by_listing_year",)
                },
                "fresh_case_model_status": {
                    row["probe_id"]: row["model_status"] for row in fresh_rows
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 2 if (args.strict and failed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
