"""Build or verify the deterministic G5 product and G6 capability artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from ipo_risk.runtime.product_capability_acceptance import (
    TARGETED_TEST_FILES,
    build_capability_manifest,
    build_product_acceptance,
    verify_persisted,
    write_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    test_result = None
    if not args.skip_tests:
        completed = subprocess.run(
            (sys.executable, "-m", "pytest", "-q", *TARGETED_TEST_FILES),
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        test_result = {
            "passed": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout_tail": (completed.stdout or "")[-2000:],
            "stderr_tail": (completed.stderr or "")[-2000:],
        }
        if completed.returncode:
            print(json.dumps({"status": "fail", "tests": test_result}, indent=2))
            return 2

    if args.write:
        product_path, capability_path = write_artifacts(root)
    else:
        product_path = root / "reports/final_status/product_acceptance.json"
        capability_path = root / "reports/final_status/capability_manifest.json"
        verify_persisted(build_product_acceptance(root), product_path)
        verify_persisted(build_capability_manifest(root), capability_path)
    result = {
        "status": "pass",
        "mode": "write" if args.write else "check",
        "product_acceptance": product_path.relative_to(root).as_posix(),
        "capability_manifest": capability_path.relative_to(root).as_posix(),
        "tests": test_result,
        "validation_opened": False,
        "blind_2025_y_accessed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

