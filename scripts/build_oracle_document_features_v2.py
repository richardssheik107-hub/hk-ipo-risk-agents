"""Materialize versioned evaluation-only Oracle v2 features."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.modeling.oracle_document_v2 import materialize_oracle_v2
from ipo_risk.modeling.pr_d_input_binding import verify_oracle_v2_upstream_binding


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--production-dir", type=Path, required=True)
    parser.add_argument("--target-dir", type=Path, required=True)
    parser.add_argument("--input-binding-manifest", type=Path, required=True)
    parser.add_argument("--pr-d-freeze-manifest", type=Path, required=True)
    parser.add_argument("--pr-a-freeze-manifest", type=Path, required=True)
    parser.add_argument("--pr-c-freeze-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/oracle_document_features_v2"))
    parser.add_argument("--all-eligible", action="store_true", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    upstream = verify_oracle_v2_upstream_binding(
        production_dir=args.production_dir,
        target_dir=args.target_dir,
        binding_manifest_path=args.input_binding_manifest,
        pr_d_freeze_manifest_path=args.pr_d_freeze_manifest,
        pr_a_manifest_path=args.pr_a_freeze_manifest,
        pr_c_manifest_path=args.pr_c_freeze_manifest,
    )
    result = materialize_oracle_v2(
        root=args.root,
        production_dir=args.production_dir,
        target_dir=args.target_dir,
        output_dir=args.output_dir,
        resume=args.resume,
        upstream_binding=upstream,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "statuses"}, ensure_ascii=False, sort_keys=True))
    return 0 if not any(item["status"] == "failed" for item in result["statuses"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
