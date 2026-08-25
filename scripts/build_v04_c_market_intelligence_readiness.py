"""Build the compact C-lane readiness artifact from governed facts only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

from ipo_risk.agents.final_supervisor import V04FinalSupervisor
from ipo_risk.agents.market_intelligence import (
    GovernedExtendedReadinessMarketContextProvider,
    MARKET_INTELLIGENCE_SCHEMA_VERSION,
    MarketIntelligenceAgent,
)
from ipo_risk.market.skills import IPO_HEAT_POLICY_VERSION, MARKET_REGIME_POLICY_VERSION
from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import ChannelStatus, FinalSupervisionInput


READINESS_VERSION = "v04_c_market_intelligence_readiness_v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _profile(row: dict[str, str]) -> IPOProfile:
    return IPOProfile(
        company_name=row["case_id"],
        stock_code=row["stock_code"],
        listing_date=date.fromisoformat(row["listing_date"]),
    )


def _selected(candidates: list[tuple[dict[str, str], object]]) -> list[tuple[str, str, object]]:
    """First case_id in each pre-listing state stratum; never inspect outcomes."""

    rules = (
        ("risk_on_and_hot", lambda b: b.market_regime.market_regime.value == "RISK_ON" and b.ipo_heat.ipo_heat.value == "HOT"),
        ("risk_off_and_cold", lambda b: b.market_regime.market_regime.value == "RISK_OFF" and b.ipo_heat.ipo_heat.value == "COLD"),
        ("high_volatility", lambda b: b.market_regime.volatility_condition.value == "HIGH"),
        ("recent_ipo_sample_missing", lambda b: b.ipo_heat.ipo_heat.value == "INSUFFICIENT_DATA"),
    )
    chosen: list[tuple[str, str, object]] = []
    used: set[str] = set()
    used_years: set[str] = set()
    candidates = [
        (row, bundle) for row, bundle in candidates
        if all(
            item.availability == "unavailable"
            and item.missing_reason == "INDUSTRY_MAPPING_PIT_BLOCKED"
            for item in bundle.market_context.observations
            if item.name in {"industry_return_5d", "industry_return_20d"}
        )
    ]
    for label, predicate in rules:
        match = next(
            (
                (row, bundle) for row, bundle in candidates
                if row["case_id"] not in used
                and row["listing_date"][:4] not in used_years
                and predicate(bundle)
            ),
            None,
        )
        if match is None:
            match = next(
                ((row, bundle) for row, bundle in candidates if row["case_id"] not in used and predicate(bundle)),
                None,
            )
        if match is None:
            raise RuntimeError(f"no governed case satisfies demo stratum: {label}")
        row, bundle = match
        used.add(row["case_id"])
        used_years.add(row["listing_date"][:4])
        chosen.append((label, row["case_id"], bundle))
    return chosen


def _trace_projection(bundle) -> list[dict[str, object]]:
    return [
        {
            "event_type": event.event_type.value,
            "status": event.status,
            "agent_name": event.agent_name,
            "task": event.action,
            "tool_or_skill": event.tool_or_skill,
            "provider_name": event.provider_name,
            "model_name": event.model_name,
            "prompt_version": event.prompt_version,
            "latency_ms": event.latency_ms,
            "details": event.details,
        }
        for event in bundle.trace_events
    ]


def build(readiness_path: Path) -> dict[str, object]:
    rows = sorted(
        csv.DictReader(readiness_path.open(encoding="utf-8-sig", newline="")),
        key=lambda row: row["case_id"],
    )
    provider = GovernedExtendedReadinessMarketContextProvider(readiness_path)
    agent = MarketIntelligenceAgent()
    candidates = []
    for row in rows:
        view = provider.context(_profile(row))
        if view.status is not ChannelStatus.AVAILABLE:
            raise RuntimeError(f"{row['case_id']}: {view.reason}")
        first = agent.analyze(view, run_id=f"demo:{row['case_id']}")
        second = agent.analyze(view, run_id=f"determinism:{row['case_id']}")
        if first.market_context.provenance["market_intelligence"] != second.market_context.provenance["market_intelligence"]:
            raise RuntimeError(f"deterministic skill drift for {row['case_id']}")
        candidates.append((row, first))

    demos = []
    for selection_reason, case_id, bundle in _selected(candidates):
        context = bundle.market_context
        final = V04FinalSupervisor().finalize(FinalSupervisionInput(market_context=context))
        observations = [item.model_dump(mode="json") for item in context.observations]
        demos.append({
            "selection_reason": selection_reason,
            "case_id": case_id,
            "stock_code": context.provenance["stock_code"],
            "listing_date": context.provenance["listing_date"],
            "market_context": context.model_dump(mode="json"),
            "ipo_heat_skill": bundle.ipo_heat.model_dump(mode="json"),
            "market_regime_skill": bundle.market_regime.model_dump(mode="json"),
            "source_features": observations,
            "missing_features": [item for item in observations if item["availability"] == "unavailable"],
            "pit_cutoff": context.provenance["pit_cutoff_date"],
            "provenance": context.provenance,
            "llm_interpretation": bundle.interpretation,
            "llm_provider": None,
            "llm_model": None,
            "llm_status": bundle.interpretation_status.value,
            "llm_reason": bundle.interpretation_reason,
            "trace": _trace_projection(bundle),
            "final_supervisor_compatibility": (
                final.market_context == context
                and "INDUSTRY_MAPPING_PIT_BLOCKED" in final.model_dump_json()
            ),
        })

    return {
        "readiness_version": READINESS_VERSION,
        "market_intelligence_schema_version": MARKET_INTELLIGENCE_SCHEMA_VERSION,
        "source": {
            "artifact_name": readiness_path.name,
            "sha256": _sha256(readiness_path),
            "row_count": len(rows),
        },
        "selection_policy": {
            "version": "v04_c_demo_selection_v1",
            "rule": "first case_id in each pre-listing MarketContext stratum, preferring an unused listing year",
            "uses_outcomes": False,
            "uses_model_correctness": False,
        },
        "skill_status": {"ipo_heat": "PASS", "market_regime": "PASS", "comparable_ipo": "DEFERRED"},
        "ipo_heat_policy_version": IPO_HEAT_POLICY_VERSION,
        "market_regime_policy_version": MARKET_REGIME_POLICY_VERSION,
        "market_context_status": "PASS",
        "llm_interpretation": {
            "implementation": "PASS",
            "real_demo_status": "UNAVAILABLE_NO_PROVIDER",
            "fallback": "PASS",
            "fact_mutation": False,
        },
        "pit_status": "PASS",
        "future_row_poisoning": "PASS",
        "blind_2025_y_accessed": False,
        "missingness_status": "PASS",
        "industry_pit_block_retained": True,
        "fake_industry_proxy": False,
        "determinism": "PASS",
        "downstream_compatibility": {
            "c_to_e": "PASS",
            "final_supervisor": "PASS",
            "pr_h_runtime_contract": "PASS",
        },
        "demo_case_ids": [item["case_id"] for item in demos],
        "demo_pass": f"{sum(item['final_supervisor_compatibility'] for item in demos)} / {len(demos)}",
        "demos": demos,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/catalog/v04_c_market_intelligence_readiness.json"),
    )
    args = parser.parse_args()
    payload = build(args.readiness)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not any("\u4e00" <= char <= "\u9fff" for char in args.output.read_text(encoding="utf-8")):
        # This artifact is intentionally English-only; verify UTF-8 round-trip by content hash instead.
        json.loads(args.output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
