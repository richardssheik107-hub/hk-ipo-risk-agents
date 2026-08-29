"""Package a recorded case matrix into a self-contained demo bundle.

The bundle is what gets carried to the demonstration machine: the analysis
results, sidecars, case reports, Evidence screenshots and batch report a matrix
run already wrote, copied under one directory with a SHA-256 for every file, plus
a walkthrough generated from those same artifacts.

It needs no network, no provider credentials and no prospectus PDF, because it
re-runs nothing. Opening it replays the recorded run; it cannot produce a result
that run did not produce.

``--verify`` re-hashes an existing bundle instead of building one, which is the
check to run on the demo machine before anyone puts it on a screen.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ipo_risk.runtime.demo_replay import (  # noqa: E402
    DEMO_SCRIPT_NAME,
    MANIFEST_NAME,
    STATUS_UNAVAILABLE_SOURCE,
    available_recorded_cases,
    build_demo_bundle,
    load_recorded_case,
    render_demo_script,
    verify_demo_bundle,
)

DEFAULT_SOURCE = Path("reports/v045_role_e")
DEFAULT_OUTPUT = Path("reports/v045_demo_bundle")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case-id", action="append", default=None, help="only these case ids")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="re-hash the bundle in --output-dir against its manifest instead of building",
    )
    arguments = parser.parse_args()

    if arguments.verify:
        report = verify_demo_bundle(arguments.output_dir)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["passed"] else 1

    manifest = build_demo_bundle(
        source_dir=arguments.source_dir,
        output_dir=arguments.output_dir,
        case_ids=arguments.case_id,
    )
    if manifest["status"] == STATUS_UNAVAILABLE_SOURCE:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    # The walkthrough is generated from the bundled copies, so it can only
    # describe what actually made it into the bundle.
    matrix = json.loads((arguments.output_dir / "summary.json").read_text(encoding="utf-8")) if (
        arguments.output_dir / "summary.json"
    ).is_file() else {}
    cases = [
        load_recorded_case(case_dir, matrix)
        for case_dir in available_recorded_cases(arguments.output_dir)
    ]
    (arguments.output_dir / DEMO_SCRIPT_NAME).write_text(
        render_demo_script(manifest, cases), encoding="utf-8"
    )
    (arguments.output_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "output_dir": str(arguments.output_dir),
                "replayable_case_count": manifest["replayable_case_count"],
                "case_count": manifest["case_count"],
                "file_count": manifest["file_count"],
                "total_byte_size": manifest["total_byte_size"],
                "cases": [
                    {
                        "case_id": case["case_id"],
                        "screenshot_count": case["screenshot_count"],
                        "missing_files": case["missing_files"],
                    }
                    for case in manifest["cases"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
