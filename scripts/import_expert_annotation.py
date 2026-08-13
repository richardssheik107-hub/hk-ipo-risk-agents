"""Import validated blind expert output into the ignored reports workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.expert_annotation import validate_expert_annotation_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("annotation", type=Path)
    parser.add_argument("--inventory", type=Path, default=Path("reports/gpt_expert_annotation_pilot/source_inventory.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/gpt_expert_annotation_pilot/expert_results"))
    args = parser.parse_args()
    payload = json.loads(args.annotation.read_text(encoding="utf-8"))
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    source = next((item for item in inventory["cases"] if item["case_id"] == payload.get("case_id")), None)
    if source is None:
        raise SystemExit("source case is absent from the blind source inventory")
    identity_fields = ("case_id", "stock_code", "company_name", "document_id")
    mismatches = [field for field in identity_fields if payload.get(field) != source.get(field)]
    if mismatches:
        raise SystemExit(f"annotation identity does not match source inventory: {mismatches}")
    bundle, issues = validate_expert_annotation_payload(payload, page_count=int(source["page_count"]))
    if issues or bundle is None:
        print(json.dumps({"imported": False, "issues": [issue.__dict__ for issue in issues]}, ensure_ascii=False, indent=2))
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / f"{bundle.stock_code.replace('.', '_')}_expert_annotation.json"
    destination.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    print(json.dumps({"imported": True, "path": str(destination)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
