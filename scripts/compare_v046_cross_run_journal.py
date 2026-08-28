from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.role_b_cross_run import compare_cross_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two Role-B journals offline")
    parser.add_argument("--run-a-journal", type=Path, required=True)
    parser.add_argument("--run-b-journal", type=Path, required=True)
    parser.add_argument("--run-a-lifecycle", type=Path, required=True)
    parser.add_argument("--run-b-lifecycle", type=Path, required=True)
    parser.add_argument("--run-a-evidence-units", type=Path)
    parser.add_argument("--run-b-evidence-units", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare_cross_run(
        run_a_journal=args.run_a_journal,
        run_b_journal=args.run_b_journal,
        run_a_lifecycle=args.run_a_lifecycle,
        run_b_lifecycle=args.run_b_lifecycle,
        run_a_evidence_units=args.run_a_evidence_units,
        run_b_evidence_units=args.run_b_evidence_units,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: result[key] for key in (
        "classification", "case_count", "identity_mismatch_count",
        "structured_payload_variance_case_count", "network_calls",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
