"""Build or verify the additive PR-D frozen bulk-input binding manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.modeling.pr_d_input_binding import (
    build_pr_d_input_binding,
    verify_pr_d_input_binding,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-a-dir", type=Path, required=True)
    parser.add_argument("--pr-b-dir", type=Path, required=True)
    parser.add_argument("--pr-c-dir", type=Path, required=True)
    parser.add_argument("--pr-a-freeze-manifest", type=Path, required=True)
    parser.add_argument("--pr-b-freeze-manifest", type=Path, required=True)
    parser.add_argument("--pr-c-freeze-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    kwargs = {
        "production_dir": args.pr_a_dir / "production_features",
        "market_core_dir": args.pr_b_dir / "core_features",
        "target_dir": args.pr_c_dir / "targets",
        "oracle_dir": args.pr_a_dir / "oracle_features",
        "pr_a_manifest_path": args.pr_a_freeze_manifest,
        "pr_b_manifest_path": args.pr_b_freeze_manifest,
        "pr_c_manifest_path": args.pr_c_freeze_manifest,
    }
    if args.verify:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        result = verify_pr_d_input_binding(payload, **kwargs)
    else:
        result = build_pr_d_input_binding(**kwargs)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
