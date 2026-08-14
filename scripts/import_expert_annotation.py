"""Preserve and validate one blind expert output in a versioned Case folder."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from ipo_risk.evaluation.expert_annotation import validate_expert_annotation_payload


STAGE_FILENAMES = {
    "pass1": "expert_annotation_v1.json",
    "pass2": "expert_annotation_v2.json",
    "final": "expert_annotation_final.json",
}


def import_annotation(
    annotation: Path,
    *,
    inventory_path: Path,
    output_dir: Path,
    stage: str,
) -> tuple[Path, Path, bool]:
    """Preserve raw JSON and write a separate validation result without overwrites."""
    raw_text = annotation.read_text(encoding="utf-8")
    payload = json.loads(raw_text)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    source = next((item for item in inventory["cases"] if item["case_id"] == payload.get("case_id")), None)
    if source is None:
        raise ValueError("source case is absent from the blind source inventory")
    identity_fields = ("case_id", "stock_code", "company_name", "document_id")
    mismatches = [field for field in identity_fields if payload.get(field) != source.get(field)]
    if mismatches:
        raise ValueError(f"annotation identity does not match source inventory: {mismatches}")

    stage_dir = output_dir / str(source["case_id"]) / stage
    destination = stage_dir / STAGE_FILENAMES[stage]
    validation_path = stage_dir / "validation_result.json"
    collisions = [path for path in (destination, validation_path) if path.exists()]
    if collisions:
        raise FileExistsError(
            "refusing to overwrite existing review artifacts: "
            + ", ".join(str(path) for path in collisions)
        )

    bundle, issues = validate_expert_annotation_payload(payload, page_count=int(source["page_count"]))
    result = {
        "case_id": source["case_id"],
        "stage": stage,
        "source_annotation": destination.name,
        "valid": not issues and bundle is not None,
        "issues": [asdict(issue) for issue in issues],
    }
    stage_dir.mkdir(parents=True, exist_ok=True)
    destination.write_text(raw_text, encoding="utf-8")
    validation_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination, validation_path, bool(result["valid"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("annotation", type=Path)
    parser.add_argument("--inventory", type=Path, default=Path("reports/gpt_expert_annotation_pilot/source_inventory.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/gpt_expert_annotation_pilot/expert_results"))
    parser.add_argument("--stage", choices=tuple(STAGE_FILENAMES), default="pass1")
    args = parser.parse_args()
    try:
        destination, validation_path, valid = import_annotation(
            args.annotation,
            inventory_path=args.inventory,
            output_dir=args.output_dir,
            stage=args.stage,
        )
    except (FileExistsError, ValueError) as exc:
        print(json.dumps({"imported": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(
        {
            "preserved": True,
            "valid": valid,
            "annotation_path": str(destination),
            "validation_path": str(validation_path),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
