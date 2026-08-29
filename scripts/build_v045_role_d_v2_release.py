"""Build the frozen Role-D V2 promotion candidate and final-three handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ipo_risk.modeling.role_d_v2_release import (
    V2_FROZEN_MANIFEST_NAME,
    materialize_v2_release,
    write_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market-core-dir", type=Path, default=Path("reports/v04_pr_b/core_features"))
    parser.add_argument("--target-dir", type=Path, required=True)
    parser.add_argument("--prior-role-d-dir", type=Path, default=Path("reports/v045_role_d"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v045_role_d_v2"))
    parser.add_argument("--handoff-dir", type=Path, default=Path("reports/v045_role_d_v2_product_handoff_final3"))
    parser.add_argument("--case-list", type=Path, default=Path("configs/v045_demo_cases.json"))
    parser.add_argument("--freeze-manifest", type=Path, default=Path("reports/frozen") / V2_FROZEN_MANIFEST_NAME)
    parser.add_argument("--receipt", type=Path, default=Path("reports/frozen/v045_role_d_v2_promotion_receipt.json"))
    parser.add_argument("--base-main-commit", required=True)
    args = parser.parse_args()

    implementation = REPO_ROOT / "src/ipo_risk/modeling/role_d_v2_release.py"
    implementation_sha256 = hashlib.sha256(implementation.read_bytes()).hexdigest()
    case_ids = [
        row["case_id"]
        for row in json.loads(args.case_list.read_text(encoding="utf-8"))["cases"]
    ]
    result = materialize_v2_release(
        market_core_dir=args.market_core_dir,
        target_dir=args.target_dir,
        prior_role_d_dir=args.prior_role_d_dir,
        output_dir=args.output_dir,
        handoff_dir=args.handoff_dir,
        case_ids=case_ids,
        base_main_commit=args.base_main_commit,
        implementation_sha256=implementation_sha256,
    )
    args.freeze_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.freeze_manifest.write_text(
        json.dumps(result["freeze_manifest"], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt = write_receipt(
        args.receipt,
        freeze_manifest_path=args.freeze_manifest,
        build_result=result,
    )
    print(json.dumps({
        "status": receipt["status"],
        "output_dir": str(args.output_dir),
        "handoff_dir": str(args.handoff_dir),
        "freeze_manifest": str(args.freeze_manifest),
        "receipt": str(args.receipt),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
