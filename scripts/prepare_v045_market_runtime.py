"""Build the full governed Market-X runtime directly from the EOD ZIP archive.

The 1.1 GB CSV is extracted under the operating-system temporary directory,
not into the Git checkout.  This avoids workspace/file-sync size limits while
keeping the licensed raw source outside version control.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from run_v04_pr_b import materialize_pr_b


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_NAME = "hkshareeodprices.csv"


def _frozen_expectations(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    governed = payload.get("governed_eod") or {}
    return {
        "raw_eod_sha256": governed.get("raw_eod_sha256"),
        "row_count": governed.get("row_count"),
        "distinct_target_securities": governed.get("distinct_target_securities"),
        "provider_ohlcv_matched": governed.get("provider_ohlcv_matched"),
        "provider_ohlcv_missing": governed.get("provider_ohlcv_missing"),
        "official_case_count": payload.get("official_case_count"),
    }


def _extract_verified(archive: Path, destination: Path, expected_hash: str) -> Path:
    try:
        with zipfile.ZipFile(archive) as bundle:
            matches = [item for item in bundle.infolist() if Path(item.filename).name == RAW_NAME]
            if len(matches) != 1 or matches[0].is_dir():
                raise ValueError(f"archive must contain exactly one {RAW_NAME}")
            target = destination / RAW_NAME
            digest = hashlib.sha256()
            with bundle.open(matches[0]) as source, target.open("wb") as output:
                while block := source.read(1024 * 1024):
                    digest.update(block)
                    output.write(block)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("EOD archive is unreadable") from exc
    actual = digest.hexdigest()
    if actual != expected_hash:
        raise ValueError(
            f"EOD archive hash mismatch: expected {expected_hash}, found {actual}"
        )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eod-archive", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path, default=REPO_ROOT / "reports/v04_pr_b"
    )
    parser.add_argument(
        "--frozen-manifest",
        type=Path,
        default=REPO_ROOT / "reports/frozen/v04_pr_b_market_x_core_manifest.json",
    )
    args = parser.parse_args()

    expected = _frozen_expectations(args.frozen_manifest)
    raw_hash = expected["raw_eod_sha256"]
    if not isinstance(raw_hash, str):
        parser.error("frozen PR-B manifest has no raw EOD checksum")

    with tempfile.TemporaryDirectory(prefix="hk-ipo-eod-") as temporary:
        data_root = Path(temporary)
        try:
            _extract_verified(args.eod_archive, data_root, raw_hash)
            result = materialize_pr_b(
                repo_root=REPO_ROOT,
                catalog_dir=REPO_ROOT / "data/catalog",
                data_root=data_root,
                output_dir=args.output_dir,
                resume=True,
                verify_determinism=True,
                require_clean=True,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            parser.error(str(exc))

    summary = result["summary"]
    actual = summary["governed_eod"]
    checks = {
        "raw_eod_sha256": actual.get("raw_eod_sha256") == expected["raw_eod_sha256"],
        "row_count": actual.get("row_count") == expected["row_count"],
        "distinct_target_securities": actual.get("distinct_target_securities")
        == expected["distinct_target_securities"],
        "provider_ohlcv_matched": actual.get("provider_ohlcv_matched")
        == expected["provider_ohlcv_matched"],
        "provider_ohlcv_missing": actual.get("provider_ohlcv_missing")
        == expected["provider_ohlcv_missing"],
        "case_count": summary.get("selected_case_count")
        == summary.get("core_market_x_materialized_count")
        == expected["official_case_count"],
        "failure_count": summary.get("failed_count") == 0,
        "blind_outcomes": summary.get("blind_outcomes_included") is False,
        "determinism": result["reproducibility"].get("passed") is True,
    }
    passed = all(checks.values())
    print(
        json.dumps(
            {
                "status": "pass" if passed else "fail",
                "checks": checks,
                "output_dir": str(args.output_dir),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
