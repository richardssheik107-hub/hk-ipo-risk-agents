"""Create the final v0.4.5 competition bundle after every active readiness Gate passes.

The packager is fail-closed: it refuses to run unless Role-A readiness says
``COMPETITION_READY``, includes only an explicit source/artifact allowlist, and
rejects licensed PDFs, secret-bearing files, token-like material, private keys,
and local absolute paths.

Human Review remains an optional product artifact and is not required for the
active release policy.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.runtime.release_policy import DEFAULT_ROLE_E_DIR, activate_active_release_policy
from ipo_risk.runtime.submission_readiness import package_submission_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--role-b-dir", type=Path, default=Path("reports/v045_role_b"))
    parser.add_argument("--role-d-dir", type=Path, default=Path("reports/v045_role_d"))
    parser.add_argument("--role-e-dir", type=Path, default=Path(DEFAULT_ROLE_E_DIR))
    parser.add_argument("--a-output-dir", type=Path, default=Path("reports/v045_submission"))
    parser.add_argument(
        "--output-zip",
        type=Path,
        default=Path("dist/hk_ipo_risk_agents_v045_submission.zip"),
    )
    args = parser.parse_args()

    # Keep package selection consistent with the readiness artifact index: the
    # legacy historical M4/Human Review files are not mandatory package inputs.
    activate_active_release_policy()

    manifest = package_submission_bundle(
        repo_root=args.repo_root.resolve(),
        role_b_dir=args.role_b_dir,
        role_d_dir=args.role_d_dir,
        role_e_dir=args.role_e_dir,
        a_output_dir=args.a_output_dir,
        output_zip=args.output_zip,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
