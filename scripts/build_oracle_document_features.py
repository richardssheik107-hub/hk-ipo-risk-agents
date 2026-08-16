"""Build evaluation-only Oracle document features from audited expert results."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from ipo_risk.modeling.oracle_document import build_oracle_document_features

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--all-eligible", action="store_true")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/oracle_document_features"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not args.case_id and not args.all_eligible:
        parser.error("provide --case-id or --all-eligible")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    failures = []
    case_ids = set(args.case_id or [])
    if args.all_eligible:
        case_ids.update(path.parents[1].name for path in (args.root / "expert_results").glob("*/pass1/expert_annotation_v1.json"))
    for case_id in sorted(case_ids):
        target = args.output_dir / f"{case_id}.json"
        try:
            artifact = build_oracle_document_features(args.root, case_id)
            encoded = json.dumps(artifact, ensure_ascii=False, indent=2) + "\n"
            if target.exists() and args.resume:
                existing = json.loads(target.read_text(encoding="utf-8"))
                if existing.get("content_hash") == artifact["content_hash"]:
                    continue
                raise ValueError("existing artifact provenance differs; use a new output directory")
            if target.exists() and not args.resume:
                raise ValueError("existing artifact; use --resume or a new output directory")
            target.write_text(encoded, encoding="utf-8")
        except Exception as exc:
            failures.append({"case_id": case_id, "error": f"{type(exc).__name__}: {exc}"})
    (args.output_dir / "failure_report.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if failures else 0
if __name__ == "__main__":
    raise SystemExit(main())
