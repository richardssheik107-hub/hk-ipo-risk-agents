"""Materialize the 438-case governed CSMAR HSI readiness audit.

This command reads only the normalized, ignored HSI cache.  It never reads an
outcome or any 2025 Blind row and preserves the frozen Extended feature engine.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from ipo_risk.market.csmar_hsi import (
    CSMAR_HSI_DATASET_NAME,
    CSMAR_HSI_REFERENCE_ID,
    CSMARHSIProvider,
)
from ipo_risk.market.features import PreListingMarketFeatureEngine
from ipo_risk.schemas.market import (
    MarketDataProvenance,
    expected_market_split,
)
from ipo_risk.schemas.market_features import (
    MarketFeatureAvailability,
    MarketReferenceBar,
    PreListingMarketFeatureContext,
)


EXPECTED_OFFICIAL_CASES = 438
HSI_FEATURE_NAMES = (
    "hsi_return_5d",
    "hsi_return_20d",
    "market_volatility_20d",
)
READINESS_FIELDS = (
    "case_id",
    "listing_date",
    "observation_date",
    "hsi_return_5d",
    "hsi_return_5d__missing",
    "hsi_return_20d",
    "hsi_return_20d__missing",
    "market_volatility_20d",
    "market_volatility_20d__missing",
    "missing_reason",
    "source_version",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _content_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _load_official_cases(
    catalog_path: Path,
    *,
    expected_cases: int = EXPECTED_OFFICIAL_CASES,
) -> tuple[dict[str, Any], ...]:
    with catalog_path.open("r", encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    cases: list[dict[str, Any]] = []
    for source in source_rows:
        if (source.get("official_match_status") or "").strip() != "matched":
            continue
        raw_listing_date = (source.get("official_listed_date") or "").strip()
        if not raw_listing_date:
            continue
        listing_date = date.fromisoformat(raw_listing_date)
        if not 2020 <= listing_date.year <= 2024:
            continue
        # The catalog retains one historical source-year exception.  All v0.4
        # market contracts instead derive the frozen split from the authoritative
        # official listing year, so the legacy catalog label is not consumed.
        split = expected_market_split(listing_date.year)
        cases.append(
            {
                "case_id": (source.get("case_id") or "").strip(),
                "stock_code": (source.get("stock_code_wind") or "").strip(),
                "listing_date": listing_date,
                "cohort_year": listing_date.year,
                "dataset_split": split,
            }
        )
    cases.sort(key=lambda item: item["case_id"])
    case_ids = [item["case_id"] for item in cases]
    if len(cases) != expected_cases:
        raise ValueError(
            f"official cohort drift: expected {expected_cases}, found {len(cases)}"
        )
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("official cohort contains duplicate case_id values")
    if any(not item["stock_code"] for item in cases):
        raise ValueError("official cohort contains a missing stock code")
    return tuple(cases)


def _context(case: dict[str, Any], provider: CSMARHSIProvider) -> PreListingMarketFeatureContext:
    manifest = provider.manifest
    return PreListingMarketFeatureContext(
        case_id=case["case_id"],
        stock_code=case["stock_code"],
        cohort_year=case["cohort_year"],
        listing_date=case["listing_date"],
        dataset_split=case["dataset_split"],
        benchmark_reference_id=CSMAR_HSI_REFERENCE_ID,
        industry_reference_id=None,
        source="CSMAR HSI governed normalized layer",
        provenance=MarketDataProvenance(
            source="CSMAR",
            dataset_version=manifest.source_version(),
            metadata={
                "dataset_name": CSMAR_HSI_DATASET_NAME,
                "source_archive_sha256": manifest.source_archive_sha256,
                "source_file_sha256": manifest.source_file_sha256,
            },
        ),
    )


def _feature_payload(snapshot: Any) -> dict[str, Any]:
    by_name = {item.name: item for item in snapshot.features}
    result: dict[str, Any] = {}
    missing_reasons: list[str] = []
    for name in HSI_FEATURE_NAMES:
        feature = by_name[name]
        available = feature.availability is MarketFeatureAvailability.AVAILABLE
        result[name] = str(feature.value) if available else ""
        result[f"{name}__missing"] = not available
        if feature.missing_reason is not None:
            missing_reasons.append(f"{name}:{feature.missing_reason.value}")
    result["missing_reason"] = "|".join(missing_reasons)
    return result


def materialize_readiness(
    cases: tuple[dict[str, Any], ...],
    provider: CSMARHSIProvider,
    *,
    poison_future_rows: bool,
) -> list[dict[str, Any]]:
    """Build one readiness row per official case without reading any outcome."""

    engine = PreListingMarketFeatureEngine()
    output: list[dict[str, Any]] = []
    for case in cases:
        context = _context(case, provider)
        benchmark_bars = provider.get_benchmark_bars(
            CSMAR_HSI_REFERENCE_ID,
            end_date_exclusive=case["listing_date"],
        )
        snapshot = engine.build(
            context,
            benchmark_bars=benchmark_bars,
            industry_bars=None,
            activity_observations=None,
            prior_ipos=(),
            prior_outcomes=(),
        )
        payload = _feature_payload(snapshot)
        if poison_future_rows:
            poison = MarketReferenceBar(
                reference_id="WRONG-FUTURE-ID",
                trading_date=case["listing_date"] + timedelta(days=1),
                close=Decimal("999999999"),
                provenance=MarketDataProvenance(
                    source="future-row-poisoning-test",
                    dataset_version="test-only",
                    source_record_id=f"poison:{case['case_id']}",
                ),
            )
            poisoned = engine.build(
                context,
                benchmark_bars=(*benchmark_bars, poison),
                industry_bars=None,
                activity_observations=None,
                prior_ipos=(),
                prior_outcomes=(),
            )
            if _feature_payload(poisoned) != payload:
                raise AssertionError(
                    f"future-row poisoning changed historical HSI features for {case['case_id']}"
                )
        output.append(
            {
                "case_id": case["case_id"],
                "listing_date": case["listing_date"].isoformat(),
                "observation_date": (
                    snapshot.observation_date.isoformat()
                    if snapshot.observation_date is not None
                    else ""
                ),
                **payload,
                "source_version": provider.manifest.source_version(),
            }
        )
    return output


def _write_conflict_safe(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise ValueError(f"refusing to overwrite conflicting artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")


def _csv_text(rows: list[dict[str, Any]]) -> str:
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=READINESS_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def run(args: argparse.Namespace) -> dict[str, Any]:
    provider = CSMARHSIProvider(args.normalized_csv, args.source_manifest)
    cases = _load_official_cases(
        args.catalog,
        expected_cases=args.expected_cases,
    )
    first = materialize_readiness(cases, provider, poison_future_rows=True)
    second = materialize_readiness(cases, provider, poison_future_rows=False)
    first_hash = _content_hash(first)
    second_hash = _content_hash(second)
    if first != second or first_hash != second_hash:
        raise AssertionError("HSI readiness materialization is not deterministic")

    availability = {
        name: sum(not bool(row[f"{name}__missing"]) for row in first)
        for name in HSI_FEATURE_NAMES
    }
    summary = {
        "audit_version": "v04_c_hsi_readiness_v1",
        "dataset_name": CSMAR_HSI_DATASET_NAME,
        "reference_id": CSMAR_HSI_REFERENCE_ID,
        "official_cases": len(first),
        "hsi_5d_available": availability["hsi_return_5d"],
        "hsi_20d_available": availability["hsi_return_20d"],
        "hsi_volatility_available": availability["market_volatility_20d"],
        "future_row_poisoning": "PASS",
        "determinism": "PASS",
        "artifact_hash": first_hash,
        "source_version": provider.manifest.source_version(),
        "source_archive_sha256": provider.manifest.source_archive_sha256,
        "source_file_sha256": provider.manifest.source_file_sha256,
        "coverage_start": provider.manifest.coverage_start.isoformat(),
        "coverage_end": provider.manifest.coverage_end.isoformat(),
        "blind_2025_y_accessed": False,
        "silent_drops": 0,
    }
    output_dir: Path = args.output_dir
    _write_conflict_safe(output_dir / "hsi_readiness_438.csv", _csv_text(first))
    summary_text = json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    _write_conflict_safe(output_dir / "hsi_readiness_summary.json", summary_text)
    if "国际指数日行情文件" not in (
        output_dir / "hsi_readiness_summary.json"
    ).read_text(encoding="utf-8"):
        raise AssertionError("UTF-8 Chinese content verification failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normalized-csv", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/catalog/ipo_official_master_bridge.csv"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-cases", type=int, default=EXPECTED_OFFICIAL_CASES)
    return parser.parse_args()


def main() -> int:
    summary = run(parse_args())
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
