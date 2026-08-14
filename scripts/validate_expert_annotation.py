"""Validate an external GPT expert annotation without changing it."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from ipo_risk.evaluation.expert_annotation import validate_expert_annotation_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("annotation", type=Path)
    parser.add_argument("--page-count", type=int, required=True)
    args = parser.parse_args()
    payload = json.loads(args.annotation.read_text(encoding="utf-8"))
    _, issues = validate_expert_annotation_payload(payload, page_count=args.page_count)
    print(json.dumps({"valid": not issues, "issues": [asdict(issue) for issue in issues]}, ensure_ascii=False, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
