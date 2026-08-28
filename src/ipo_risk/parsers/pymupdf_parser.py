"""Physical-page PDF parsing backed by PyMuPDF."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import re

import fitz

from ipo_risk.schemas import AnalysisError, DocumentChunk, DocumentParseRequest


class DocumentParseError(RuntimeError):
    """A whole-document parsing error that retains the internal error contract."""

    def __init__(self, error: AnalysisError) -> None:
        self.error = error
        super().__init__(error.message)


class PyMuPDFDocumentParser:
    """Convert a local PDF into one stable text chunk per physical page."""

    name = "pymupdf"

    def __init__(self) -> None:
        self.last_errors: list[AnalysisError] = []

    def parse(self, request: DocumentParseRequest) -> list[DocumentChunk]:
        """Parse non-blank physical pages without crossing page boundaries."""
        self.last_errors = []
        path = Path(request.prospectus_path)
        self._validate_path(path)

        try:
            document = fitz.open(path)
        except Exception as exc:
            raise self._failure("pdf_open_failure", "Unable to open PDF.", path, exc) from exc

        with document:
            if document.needs_pass:
                raise self._failure("encrypted_pdf", "Encrypted PDFs are not supported.", path)
            if document.page_count == 0:
                raise self._failure("empty_pdf", "PDF contains no pages.", path)

            chunks: list[DocumentChunk] = []
            for page_index in range(document.page_count):
                try:
                    chunk = self._parse_page(document, request.document_id, page_index)
                except Exception as exc:
                    self.last_errors.append(
                        AnalysisError(
                            stage="document_parser",
                            component=self.name,
                            code="page_parse_failure",
                            message="Unable to parse PDF page.",
                            context={
                                "path": str(path),
                                "page": page_index + 1,
                                "exception": str(exc),
                            },
                        )
                    )
                    continue
                if chunk is not None:
                    chunks.append(chunk)

        if not chunks and not self.last_errors:
            raise self._failure("empty_pdf", "PDF contains no non-blank text.", path)
        return chunks

    def _validate_path(self, path: Path) -> None:
        if not path.exists():
            raise self._failure("file_not_found", "PDF file does not exist.", path)
        if not path.is_file():
            raise self._failure("not_a_file", "PDF path must point to a file.", path)
        if path.suffix.lower() != ".pdf":
            raise self._failure("non_pdf_file", "Parser only accepts .pdf files.", path)

    def _parse_page(
        self, document: fitz.Document, document_id: str, page_index: int
    ) -> DocumentChunk | None:
        page = document.load_page(page_index)
        text = page.get_text("text").strip()
        if not text:
            return None
        physical_page = page_index + 1
        return DocumentChunk(
            document_id=document_id,
            chunk_id=f"{document_id}:page:{physical_page}",
            page=physical_page,
            section="unknown",
            text=text,
            block_type="page_text",
            metadata={
                "parser": self.name,
                "page_index": page_index,
                "physical_page": physical_page,
            },
        )

    def _failure(
        self,
        code: str,
        message: str,
        path: Path,
        exception: Exception | None = None,
    ) -> DocumentParseError:
        context = {"path": str(path)}
        if exception is not None:
            context["exception"] = str(exception)
        return DocumentParseError(
            AnalysisError(
                stage="document_parser",
                component=self.name,
                code=code,
                message=message,
                context=context,
            )
        )


class PyMuPDFTableDocumentParser(PyMuPDFDocumentParser):
    """PyMuPDF parser that additionally reconstructs borderless financial tables.

    The emitted ``.text`` and every chunk-identity field (``chunk_id``, ``page``,
    ``section``, ``block_type``) are **byte-identical** to
    :class:`PyMuPDFDocumentParser`, so retrieval, chunk-identity checks, and every
    frozen text-only expectation are unaffected. Structured tables are attached
    under ``metadata["tables"]`` only when a page actually yields a
    fiscal-year-anchored numeric grid, keeping the metadata small.
    """

    name = "pymupdf_table"

    def _parse_page(
        self, document: fitz.Document, document_id: str, page_index: int
    ) -> DocumentChunk | None:
        chunk = super()._parse_page(document, document_id, page_index)
        if chunk is None:
            return None
        try:
            from ipo_risk.parsers.table_reconstruction import reconstruct_page_tables

            page = document.load_page(page_index)
            tables = reconstruct_page_tables(page.get_text("words"))
        except Exception:
            # Table reconstruction is strictly additive; never fail a page over it.
            tables = []
        if not tables:
            return chunk
        metadata = {
            **chunk.metadata,
            "tables": tables,
            "has_structured_tables": True,
        }
        return chunk.model_copy(update={"metadata": metadata})


_ROLE_B_SEARCH_TEXT_LIMIT = 50_000


def _canonical_view(text: str) -> str:
    """Canonical identity for de-duplicating parser search views."""

    return re.sub(r"\s+", "", text or "").casefold()


def _unique_search_text_variants(
    primary: str,
    candidates: Sequence[tuple[str, str]],
) -> dict[str, str]:
    """Return bounded, non-empty parser views not equivalent to ``primary``.

    The variants are retrieval-only metadata. They do not replace the physical
    page text or alter the public ``DocumentChunk`` identity.
    """

    seen = {_canonical_view(primary)}
    output: dict[str, str] = {}
    for name, raw in candidates:
        text = (raw or "").strip()
        if not text:
            continue
        text = text[:_ROLE_B_SEARCH_TEXT_LIMIT]
        identity = _canonical_view(text)
        if not identity or identity in seen:
            continue
        seen.add(identity)
        output[name] = text
    return output


def _table_search_text(tables: Sequence[Mapping[str, object]]) -> str:
    """Serialize reconstructed tables into a deterministic retrieval-only view."""

    lines: list[str] = []
    for table in tables:
        period_columns = table.get("period_columns")
        if isinstance(period_columns, list):
            header: list[str] = []
            for column in period_columns:
                if not isinstance(column, Mapping):
                    continue
                for field in ("period_group", "year_label"):
                    value = str(column.get(field) or "").strip()
                    if value and value not in header:
                        header.append(value)
            if header:
                lines.append(" ".join(header))
        rows = table.get("rows")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            label = str(row.get("label") or "").strip()
            cells = row.get("cells")
            values = (
                [str(value).strip() for value in cells if str(value).strip()]
                if isinstance(cells, list)
                else []
            )
            text = " ".join([value for value in (label, *values) if value])
            if text:
                lines.append(text)
    return "\n".join(lines)


class PyMuPDFRoleBRecallParser(PyMuPDFDocumentParser):
    """Opt-in multi-view parser for the v0.4.6 Role-B Development lane.

    PyMuPDF's default text view can omit or reorder a disclosure even when its
    word coordinates are available. This parser keeps the released one-page
    chunk identity and primary text, while attaching alternative sorted, block,
    word-stream, and reconstructed-table views under retrieval-only metadata.
    A page that is blank only in the default view is retained from the first
    non-empty alternate view. No OCR, Gold text, issuer rule, or page rule is
    involved.
    """

    name = "pymupdf_role_b_recall"
    version = "pymupdf_role_b_recall_v1"

    def _parse_page(
        self, document: fitz.Document, document_id: str, page_index: int
    ) -> DocumentChunk | None:
        page = document.load_page(page_index)
        default_text = page.get_text("text").strip()
        sorted_text = page.get_text("text", sort=True).strip()
        blocks = page.get_text("blocks", sort=True)
        block_text = "\n".join(
            str(block[4]).strip()
            for block in blocks
            if len(block) > 4 and str(block[4]).strip()
        )
        words = page.get_text("words", sort=True)
        word_text = " ".join(
            str(word[4]).strip()
            for word in words
            if len(word) > 4 and str(word[4]).strip()
        )

        try:
            from ipo_risk.parsers.table_reconstruction import reconstruct_page_tables

            tables = reconstruct_page_tables(words)
        except Exception:
            # The recall parser is fail-soft at page level: alternate text still
            # remains useful when table reconstruction cannot classify a page.
            tables = []
        table_text = _table_search_text(tables)

        primary = default_text or sorted_text or block_text or word_text or table_text
        if not primary:
            return None

        physical_page = page_index + 1
        variants = _unique_search_text_variants(
            primary,
            (
                ("sorted_text", sorted_text),
                ("block_text", block_text),
                ("word_stream", word_text),
                ("structured_table", table_text),
            ),
        )
        metadata: dict[str, object] = {
            "parser": self.name,
            "parser_version": self.version,
            "page_index": page_index,
            "physical_page": physical_page,
            "primary_text_view": (
                "default_text"
                if default_text
                else "sorted_text"
                if sorted_text
                else "block_text"
                if block_text
                else "word_stream"
                if word_text
                else "structured_table"
            ),
            "search_text_variants": variants,
            "search_text_variant_count": len(variants),
        }
        if tables:
            metadata.update(
                {
                    "tables": tables,
                    "has_structured_tables": True,
                }
            )
        return DocumentChunk(
            document_id=document_id,
            chunk_id=f"{document_id}:page:{physical_page}",
            page=physical_page,
            section="unknown",
            text=primary,
            block_type="page_text",
            metadata=metadata,
        )
