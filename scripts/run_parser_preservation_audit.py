"""Run the parser-only preservation audit for one Expert Annotation case."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.evaluation.parser_preservation import build_audit, write_audit_outputs
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.schemas import DocumentParseRequest


def _catalog_row(catalog: Path, case_id: str) -> dict[str, str]:
    with catalog.open(encoding="utf-8-sig", newline="") as handle:
        row = next((item for item in csv.DictReader(handle) if item["case_id"] == case_id), None)
    if row is None:
        raise ValueError(f"case_id is absent from prospectus manifest: {case_id}")
    return row


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_pdf(row: dict[str, str], roots: list[Path]) -> Path:
    """Resolve a manifest-declared PDF from authorized roots and verify its hash."""
    relative = Path(row["relative_path"])
    filename = row["source_filename"]
    candidates: list[Path] = []
    for root in roots:
        for candidate in (root / relative, root / filename):
            if candidate.is_file():
                candidates.append(candidate)
        candidates.extend(path for path in root.rglob(filename) if path.is_file())
    unique = sorted(set(path.resolve() for path in candidates), key=lambda path: str(path).lower())
    matching = [path for path in unique if _sha256(path) == row["sha256"]]
    if not matching:
        raise FileNotFoundError("SOURCE_PDF_NOT_FOUND")
    return matching[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--annotation", type=Path, required=True)
    parser.add_argument("--pdf-root", type=Path, action="append", required=True)
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--output-root", type=Path, default=Path("reports/parser_preservation"))
    args = parser.parse_args()

    try:
        row = _catalog_row(args.catalog, args.case_id)
        pdf_path = resolve_pdf(row, args.pdf_root)
        annotation_text = args.annotation.read_text(encoding="utf-8")
        bundle = ExpertAnnotationBundle.model_validate_json(annotation_text)
        if bundle.case_id != args.case_id or bundle.annotation_version != "gpt_expert_v1.1":
            raise ValueError("annotation identity/version mismatch")
        if bundle.stock_code != row["stock_code_wind"] or bundle.company_name != row["company_short_name"]:
            raise ValueError("annotation identity does not match catalog")

        document_parser = PyMuPDFDocumentParser()
        chunks = document_parser.parse(DocumentParseRequest(
            document_id=args.case_id,
            prospectus_path=str(pdf_path),
        ))
        audit = build_audit(
            bundle=bundle,
            chunks=chunks,
            pdf_sha256=row["sha256"],
            pdf_page_count=int(row["pdf_page_count"]),
            annotation_sha256=hashlib.sha256(annotation_text.encode("utf-8")).hexdigest(),
            parser_errors=document_parser.last_errors,
        )
        outputs = write_audit_outputs(audit, args.output_root / args.case_id)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(json.dumps({"completed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({
        "completed": True,
        "case_id": audit.case_id,
        "summary": audit.summary.model_dump(mode="json"),
        "parser_decision": audit.parser_decision,
        "recommend_retriever_audit": audit.recommend_retriever_audit,
        "outputs": [str(path) for path in outputs],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
