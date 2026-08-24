"""Build a deterministic, label-free product handoff from frozen PR-F artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.modeling.pr_f_product_handoff import write_product_handoff

FROZEN_MANIFEST_NAME = "v04_pr_f_lightgbm_manifest.json"


def _case_ids(explicit: list[str], case_list: Path | None) -> list[str]:
    values = list(explicit)
    if case_list is not None:
        text = case_list.read_text(encoding="utf-8")
        if case_list.suffix.lower() == ".json":
            payload = json.loads(text)
            if not isinstance(payload, list):
                raise ValueError("JSON case list must be an array")
            values.extend(str(item) for item in payload)
        else:
            values.extend(line.strip() for line in text.splitlines() if line.strip())
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pr-f-dir", type=Path, required=True)
    parser.add_argument("--frozen-dir", type=Path, default=Path("reports/frozen"))
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--case-list", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    frozen_path = args.frozen_dir / FROZEN_MANIFEST_NAME
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if frozen.get("status") != "complete_frozen" or frozen.get("formal_gate_passed") is not True:
        parser.error("PR-F frozen manifest is not complete and gate-passed")
    if frozen.get("blind_2025_y_accessed") is not False:
        parser.error("PR-F frozen manifest reports blind 2025 access")
    cases = _case_ids(args.case_id, args.case_list)
    if not cases:
        parser.error("provide at least one --case-id or --case-list")

    manifest = write_product_handoff(
        args.source_pr_f_dir,
        args.output_dir,
        expected_source_model_result_hash=str(frozen["model_result_hash"]),
        case_ids=cases,
        source_pr_f={
            "pr_f_version": frozen.get("pr_f_version"),
            "model_policy_version": frozen.get("model_policy_version"),
            "execution_revision": frozen.get("execution_revision"),
            "freeze_manifest_hash": frozen.get("freeze_manifest_hash"),
        },
    )
    print(json.dumps({"status": "complete", "case_count": manifest["case_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
