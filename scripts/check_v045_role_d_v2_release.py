"""Strict checker for the committed Role-D V2 promotion candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.modeling.role_d_v2_release import (
    V2_FROZEN_MANIFEST_NAME,
    validate_release,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-manifest", type=Path, default=Path("reports/frozen") / V2_FROZEN_MANIFEST_NAME)
    parser.add_argument("--receipt", type=Path, default=Path("reports/frozen/v045_role_d_v2_promotion_receipt.json"))
    parser.add_argument("--role-d-dir", type=Path, default=Path("reports/v045_role_d_v2"))
    parser.add_argument("--handoff-dir", type=Path, default=Path("reports/v045_role_d_v2_product_handoff_final3"))
    args = parser.parse_args()
    result = validate_release(
        freeze_manifest_path=args.freeze_manifest,
        receipt_path=args.receipt,
        role_d_dir=args.role_d_dir,
        handoff_dir=args.handoff_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
