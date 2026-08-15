"""Run the isolated raw Retriever audit for one Expert Annotation case."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from ipo_risk.core.config import load_settings
from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.evaluation.raw_retrieval_audit import (
    build_raw_retrieval_audit,
    write_raw_retrieval_outputs,
)
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentParseRequest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _catalog_row(catalog: Path, case_id: str) -> dict[str, str]:
    with catalog.open(encoding="utf-8-sig", newline="") as handle:
        row = next((item for item in csv.DictReader(handle) if item["case_id"] == case_id), None)
    if row is None:
        raise ValueError(f"case_id is absent from prospectus manifest: {case_id}")
    return row


def _resolve_pdf(row: dict[str, str], roots: list[Path]) -> Path:
    candidates: list[Path] = []
    relative = Path(row["relative_path"])
    for root in roots:
        for candidate in (root / relative, root / row["source_filename"]):
            if candidate.is_file():
                candidates.append(candidate)
        candidates.extend(path for path in root.rglob(row["source_filename"]) if path.is_file())
    unique = sorted(set(path.resolve() for path in candidates), key=lambda path: str(path).lower())
    matching = [path for path in unique if _sha256(path) == row["sha256"]]
    if not matching:
        raise FileNotFoundError("SOURCE_PDF_NOT_FOUND")
    return matching[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--annotation", type=Path, required=True)
    parser.add_argument("--pdf-root", type=Path, action="append", required=True)
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--config", default="configs/v03_offline.yaml")
    parser.add_argument("--output-root", type=Path, default=Path("reports/raw_retrieval"))
    args = parser.parse_args()

    try:
        settings = load_settings(args.config)
        if settings.parser != "pymupdf" or settings.retriever != "keyword":
            raise ValueError("audit requires configured pymupdf/keyword production components")
        row = _catalog_row(args.catalog, args.case_id)
        pdf_path = _resolve_pdf(row, args.pdf_root)
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
        audit = build_raw_retrieval_audit(
            bundle=bundle,
            chunks=chunks,
            retriever=KeywordDocumentRetriever(),
            annotation_sha256=hashlib.sha256(annotation_text.encode("utf-8")).hexdigest(),
            pdf_sha256=row["sha256"],
            pdf_page_count=int(row["pdf_page_count"]),
            configured_retriever_name=settings.retriever,
            parser_error_count=len(document_parser.last_errors),
        )
        outputs = write_raw_retrieval_outputs(audit, args.output_root / args.case_id)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(json.dumps({"completed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({
        "completed": True,
        "case_id": audit.case_id,
        "annotation_version": audit.annotation_version,
        "parser": audit.parser_name,
        "retriever": audit.retriever_name,
        "parser_chunks": audit.parser_chunk_count,
        "parser_errors": audit.parser_error_count,
        "parser_regression": audit.parser_regression,
        "metrics": audit.metrics.model_dump(mode="json"),
        "risks": [item.model_dump(mode="json") for item in audit.risks],
        "outputs": [str(path) for path in outputs],
        "llm_used": audit.llm_used,
        "agent_used": audit.agent_used,
        "blind_2025_accessed": audit.blind_2025_accessed,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
