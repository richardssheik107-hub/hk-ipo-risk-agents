"""Build the batch risk report over a Role-E matrix run's artifacts.

This reads what a matrix run already wrote -- ``summary.json`` and each case
directory -- and produces one portfolio-level view: ``batch_report.json`` and
``batch_report.md`` next to the summary.  It re-analyses nothing, and it adds
nothing to any case: a case with no screenshot manifest, no human review or no
executed run is reported as exactly that.

The report is ordered for triage, and the ordering rule is printed inside it so
it cannot be read as a model score. No outcome label of any year is opened here.
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

from ipo_risk.runtime.batch_report import (  # noqa: E402
    build_batch_report,
    render_batch_report,
)

DEFAULT_INPUT = Path("reports/v045_role_e")
REPORT_JSON = "batch_report.json"
REPORT_MARKDOWN = "batch_report.md"


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def collect_case_payloads(
    input_dir: Path, summary: dict
) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    """Per-case analysis results, screenshot manifests and review exports.

    Every one of the three is optional except the analysis result: a case whose
    result cannot be read is left out of the executed set entirely, so the batch
    lists it as unexecuted rather than showing an empty row.
    """

    results: dict[str, dict] = {}
    screenshots: dict[str, dict] = {}
    reviews: dict[str, dict] = {}
    for case in summary.get("cases", []) or []:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id") or "")
        case_dir = input_dir / case_id
        result = _load_json(case_dir / "analysis_result.json")
        if result is None:
            continue
        results[case_id] = result
        manifest = _load_json(case_dir / "screenshot_manifest.json")
        if manifest is not None:
            screenshots[case_id] = manifest
        review = _load_json(case_dir / "human_review_export.json")
        if review is not None:
            reviews[case_id] = review
    return results, screenshots, reviews


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="where to write the report; defaults to --input-dir",
    )
    arguments = parser.parse_args()

    summary = _load_json(arguments.input_dir / "summary.json")
    if summary is None:
        print(
            json.dumps(
                {
                    "status": "unavailable_matrix_summary",
                    "input_dir": str(arguments.input_dir),
                    "reason": "no summary.json to read; run the case matrix first",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    results, screenshots, reviews = collect_case_payloads(arguments.input_dir, summary)
    report = build_batch_report(
        summary=summary, results=results, screenshots=screenshots, human_reviews=reviews
    )
    output_dir = arguments.output_dir or arguments.input_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / REPORT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / REPORT_MARKDOWN).write_text(render_batch_report(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "built",
                "input_dir": str(arguments.input_dir),
                "case_count": report["aggregate"]["case_count"],
                "unexecuted_case_count": len(report["unexecuted_cases"]),
                "triage_order": [case["case_id"] for case in report["cases"]],
                "aggregate": report["aggregate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
