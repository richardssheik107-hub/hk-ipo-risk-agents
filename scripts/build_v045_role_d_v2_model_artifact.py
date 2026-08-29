"""Materialize the frozen Role-D V2 runtime model package, or fail closed.

The booster is rebuilt from committed artifacts and written only if its model
text hashes to the ``classifier_model_sha256`` already frozen by the V2
promotion.  Nothing is retrained at runtime; this script exists so the product
has a loadable model file instead of three replayed handoff rows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.modeling.role_d_v2_model_artifact import (
    DEFAULT_FROZEN_DIR,
    DEFAULT_MARKET_CORE_DIR,
    DEFAULT_MODEL_DIR,
    DEFAULT_OUTCOME_PACK,
    RoleDV2ModelArtifactError,
    materialize_model_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--market-core-dir", type=Path, default=DEFAULT_MARKET_CORE_DIR)
    parser.add_argument("--outcome-pack", type=Path, default=DEFAULT_OUTCOME_PACK)
    parser.add_argument("--frozen-dir", type=Path, default=DEFAULT_FROZEN_DIR)
    args = parser.parse_args()
    try:
        result = materialize_model_artifact(
            model_dir=args.model_dir,
            market_core_dir=args.market_core_dir,
            outcome_pack_path=args.outcome_pack,
            frozen_dir=args.frozen_dir,
        )
    except RoleDV2ModelArtifactError as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
