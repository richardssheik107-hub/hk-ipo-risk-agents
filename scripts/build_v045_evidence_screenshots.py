"""Export Evidence screenshots for case runs that already happened.

This reads the artifacts a Role-E case run wrote -- it never re-analyses and
never invents an Evidence item.  For each case directory it takes the cited
Evidence out of ``analysis_result.json``, re-opens the same prospectus the run
verified, locates the cited text on its physical page and writes one PNG per
Evidence item plus a manifest binding each image to the source PDF hash, the
page, the geometry drawn and the image's own SHA-256.

Prospectus resolution is the frozen indirect one: the case directory records the
source filename and SHA-256 but no path, the filename comes from
``ipo_prospectus_manifest.csv`` and the archive root is supplied at run time by
``--prospectus-root`` or ``IPO_RISK_PROSPECTUS_ROOT``.  A prospectus whose bytes
do not match the record the run verified is refused, not rendered.

A case whose PDF is not present locally is reported ``unavailable_source_pdf``
and produces no images.  That is a recorded state of this machine, not a
failure of the run, so the command still exits 0; the summary is what says how
much of the cited Evidence actually has a screenshot.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ipo_risk.runtime.evidence_screenshots import (  # noqa: E402
    DEFAULT_RENDER_DPI,
    MANIFEST_STATUS_UNAVAILABLE_PDF,
    build_evidence_screenshots,
    summarise_screenshot_manifests,
)

DEFAULT_INPUT = Path("reports/v045_role_e")
DEFAULT_CATALOG = Path("data/catalog/ipo_prospectus_manifest.csv")
DEFAULT_BRIDGE = Path("data/catalog/ipo_official_master_bridge.csv")
PROSPECTUS_ROOT_ENV = "IPO_RISK_PROSPECTUS_ROOT"
MANIFEST_NAME = "screenshot_manifest.json"
SUMMARY_NAME = "screenshot_summary.json"
SCREENSHOT_DIR_NAME = "screenshots"


def _read_catalog(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row[key]: row for row in csv.DictReader(handle)}


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def case_directories(input_dir: Path, case_ids: list[str] | None) -> list[Path]:
    """Case directories in stable order, restricted to ``case_ids`` if given."""

    wanted = set(case_ids or [])
    return [
        path
        for path in sorted(input_dir.iterdir())
        if path.is_dir()
        and (path / "analysis_result.json").exists()
        and (not wanted or path.name in wanted)
    ]


def resolve_prospectus_bytes(
    case_id: str,
    catalog: dict[str, dict[str, str]],
    root: Path | None,
) -> tuple[bytes | None, str | None, str | None]:
    """The frozen prospectus bytes for this case, or the reason we have none.

    Returns ``(bytes, expected_sha256, reason)``.  Integrity is the manifest's
    job downstream: this refuses only what it cannot read, and hands the
    expected hash through so a mismatch is recorded rather than rendered.
    """

    row = catalog.get(case_id)
    if row is None:
        return None, None, "case_id is not present in the frozen prospectus catalog"
    expected = row.get("sha256")
    if root is None:
        return None, expected, (
            f"no prospectus root supplied; pass --prospectus-root or set {PROSPECTUS_ROOT_ENV}"
        )
    path = root / row["relative_path"]
    if not path.exists():
        # The licensed path itself is never recorded, only the fact of absence.
        return None, expected, "the frozen prospectus is not present in the local archive"
    try:
        return path.read_bytes(), expected, None
    except OSError as exc:
        return None, expected, f"prospectus could not be read: {type(exc).__name__}"


def run_case(
    case_dir: Path,
    catalog: dict[str, dict[str, str]],
    bridge: dict[str, dict[str, str]],
    root: Path | None,
    dpi: int,
    write_images: bool,
) -> dict:
    case_id = case_dir.name
    result = _load_json(case_dir / "analysis_result.json") or {}
    verification = _load_json(case_dir / "prospectus_verification.json") or {}
    stock_code = str((bridge.get(case_id) or {}).get("stock_code_wind") or "")

    pdf_bytes, expected_sha, reason = resolve_prospectus_bytes(case_id, catalog, root)
    # The run recorded the hash it verified; prefer it over the catalog row so a
    # manifest is bound to what actually produced the Evidence.
    expected_sha = str(verification.get("sha256") or expected_sha or "") or None

    manifest = build_evidence_screenshots(
        case_id=case_id,
        stock_code=stock_code,
        result=result,
        pdf_bytes=pdf_bytes,
        expected_pdf_sha256=expected_sha,
        output_dir=(case_dir / SCREENSHOT_DIR_NAME) if write_images else None,
        dpi=dpi,
    )
    if pdf_bytes is None and manifest["status"] == MANIFEST_STATUS_UNAVAILABLE_PDF and reason:
        manifest["source_pdf"]["unavailable_reason"] = reason
    manifest["screenshot_dir"] = SCREENSHOT_DIR_NAME if write_images else None
    (case_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument(
        "--prospectus-root",
        type=Path,
        default=None,
        help=f"local archive root; defaults to ${PROSPECTUS_ROOT_ENV}. Never committed.",
    )
    parser.add_argument("--case-id", action="append", default=None, help="only these case ids")
    parser.add_argument("--dpi", type=int, default=DEFAULT_RENDER_DPI)
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="compute manifests without writing PNG files",
    )
    arguments = parser.parse_args()

    root = arguments.prospectus_root
    if root is None and os.getenv(PROSPECTUS_ROOT_ENV):
        root = Path(os.environ[PROSPECTUS_ROOT_ENV])

    if not arguments.input_dir.exists():
        print(
            json.dumps(
                {
                    "status": "unavailable_input_dir",
                    "input_dir": str(arguments.input_dir),
                    "reason": "no Role-E case artifacts to read; run the case matrix first",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    catalog = _read_catalog(arguments.catalog, "case_id")
    bridge = _read_catalog(arguments.bridge, "case_id")
    manifests = [
        run_case(
            case_dir,
            catalog,
            bridge,
            root,
            arguments.dpi,
            write_images=not arguments.manifest_only,
        )
        for case_dir in case_directories(arguments.input_dir, arguments.case_id)
    ]
    summary = {
        **summarise_screenshot_manifests(manifests),
        "input_dir": str(arguments.input_dir),
        "prospectus_root_supplied": root is not None,
        "images_written": not arguments.manifest_only,
        "manifest_sha256": {
            str(manifest.get("case_id")): hashlib.sha256(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            for manifest in manifests
        },
    }
    (arguments.input_dir / SUMMARY_NAME).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
