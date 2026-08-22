from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ipo_risk.quality.annotation_phase2c import run_phase2c


def main() -> int:
    summary = run_phase2c(
        ROOT,
        ROOT / "reports" / "annotation_audit" / "phase2c",
        write_artifacts=True,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if summary["remaining_unresolved"] != 0:
        return 2
    if summary["financial_issue_records_total"] != 188:
        raise RuntimeError(
            "Phase 2c expected the frozen 188-record financial issue set "
            f"(46 policy + 142 insufficient), got {summary['financial_issue_records_total']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
