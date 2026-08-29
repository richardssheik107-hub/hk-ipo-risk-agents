"""Physical-page PDF parsing backed by PyMuPDF."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
import inspect
from pathlib import Path
import math
import re
import time

import fitz

from ipo_risk.parsers.ranked_numeric_table import recover_ranked_numeric_table
from ipo_risk.schemas import AnalysisError, DocumentChunk, DocumentParseRequest


_ROLE_B_RAW_PAGE_CONTRACT = "v046_role_b_raw_pages_v1"
_ROLE_B_TABLE_CONTRACT = "v046_role_b_tables_v1"
_ROLE_B_CHUNK_CONTRACT = "v046_role_b_chunks_v1"


def _source_fingerprint(*objects: object, extra: Sequence[str] = ()) -> str:
    digest = sha256()
    for item in objects:
        digest.update(inspect.getsource(item).encode("utf-8"))
    for item in extra:
        digest.update(str(item).encode("utf-8"))
    return digest.hexdigest()


class DocumentParseError(RuntimeError):
    """A whole-document parsing error that retains the internal error contract."""

    def __init__(self, error: AnalysisError) -> None:
        self.error = error
        super().__init__(error.message)


def _page_text_bbox(words: Sequence[Sequence[object]]) -> list[float] | None:
    """Return the real PDF-coordinate union of non-empty text words on a page.

    This is intentionally a page-text bounding box, not a fabricated sentence
    anchor. Downstream Evidence can highlight a genuine source region today;
    exact snippet-level boxes remain a separate refinement because one page
    chunk may support multiple Evidence snippets.
    """

    rectangles: list[tuple[float, float, float, float]] = []
    for word in words:
        if len(word) <= 4 or not str(word[4]).strip():
            continue
        try:
            rectangle = tuple(float(word[index]) for index in range(4))
        except (TypeError, ValueError):
            continue
        if len(rectangle) != 4 or not all(math.isfinite(value) for value in rectangle):
            continue
        x0, y0, x1, y1 = rectangle
        if x1 <= x0 or y1 <= y0:
            continue
        rectangles.append((x0, y0, x1, y1))
    if not rectangles:
        return None
    return [
        min(item[0] for item in rectangles),
        min(item[1] for item in rectangles),
        max(item[2] for item in rectangles),
        max(item[3] for item in rectangles),
    ]


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
        words = page.get_text("words")
        bbox = _page_text_bbox(words)
        physical_page = page_index + 1
        return DocumentChunk(
            document_id=document_id,
            chunk_id=f"{document_id}:page:{physical_page}",
            page=physical_page,
            section="unknown",
            text=text,
            bbox=bbox,
            block_type="page_text",
            metadata={
                "parser": self.name,
                "page_index": page_index,
                "physical_page": physical_page,
                "bbox_granularity": "page_text_union" if bbox is not None else "unavailable",
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
    version = "pymupdf_role_b_recall_v2"

    def __init__(
        self,
        *,
        cache_root: str | Path | None = None,
        expected_pdf_sha256: str | None = None,
        fingerprint_overrides: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.cache_root = Path(cache_root) if cache_root is not None else None
        self.expected_pdf_sha256 = expected_pdf_sha256
        self._fingerprint_overrides = dict(fingerprint_overrides or {})
        self.last_cache_metrics: dict[str, object] = {}

    def parse(self, request: DocumentParseRequest) -> list[DocumentChunk]:
        if self.cache_root is None:
            started = time.perf_counter()
            chunks = super().parse(request)
            self.last_cache_metrics = {
                "parser_cache_hits": 0,
                "parser_cache_misses": 0,
                "table_cache_hits": 0,
                "table_cache_misses": 0,
                "raw_page_cache_hits": 0,
                "raw_page_cache_misses": 0,
                "retrieval_cache_hits": 0,
                "retrieval_cache_misses": 0,
                "fact_cache_hits": 0,
                "fact_cache_misses": 0,
                "stage_wall_clock_ms": {
                    "total": round((time.perf_counter() - started) * 1000, 3)
                },
                "cache_enabled": False,
            }
            return chunks

        from ipo_risk.parsers.role_b_cache import (
            CacheRunMetrics,
            RoleBContentCache,
            canonical_json_hash,
            sha256_file,
        )
        from ipo_risk.parsers.table_reconstruction import reconstruct_page_tables
        self.last_errors = []
        metrics = CacheRunMetrics()
        cache = RoleBContentCache(self.cache_root)
        path = Path(request.prospectus_path)
        self._validate_path(path)
        total_started = time.perf_counter()

        hash_started = time.perf_counter()
        pdf_sha256 = self.expected_pdf_sha256 or sha256_file(path)
        metrics.timings_ms["pdf_hash"] = (time.perf_counter() - hash_started) * 1000
        if not re.fullmatch(r"[0-9a-f]{64}", pdf_sha256):
            raise ValueError("expected PDF SHA-256 must be lowercase hexadecimal")

        raw_fingerprint = self._fingerprint_overrides.get("raw_pages") or _source_fingerprint(
            self._extract_raw_pages,
            extra=(_ROLE_B_RAW_PAGE_CONTRACT, str(getattr(fitz, "VersionBind", ""))),
        )
        raw_started = time.perf_counter()
        raw_payload = cache.load_or_build(
            stage="raw_pages",
            input_hash=pdf_sha256,
            fingerprint=raw_fingerprint,
            builder=lambda: self._extract_raw_pages(path),
            metrics=metrics,
        )
        metrics.timings_ms["raw_pages"] = (time.perf_counter() - raw_started) * 1000
        raw_pages = list(raw_payload.get("pages") or [])
        for error in raw_payload.get("errors") or []:
            page_index = int(error.get("page_index") or 0)
            self.last_errors.append(
                AnalysisError(
                    stage="document_parser",
                    component=self.name,
                    code="page_parse_failure",
                    message="Unable to parse PDF page.",
                    context={"path": str(path), "page": page_index + 1},
                )
            )
        raw_content_hash = canonical_json_hash(raw_payload)

        table_fingerprint = self._fingerprint_overrides.get(
            "table_reconstruction"
        ) or _source_fingerprint(
            reconstruct_page_tables,
            extra=(_ROLE_B_TABLE_CONTRACT,),
        )
        table_started = time.perf_counter()
        tables_by_page = cache.load_or_build(
            stage="table_reconstruction",
            input_hash=raw_content_hash,
            fingerprint=table_fingerprint,
            builder=lambda: [
                self._reconstruct_tables(page.get("words") or []) for page in raw_pages
            ],
            metrics=metrics,
        )
        metrics.timings_ms["table_reconstruction"] = (
            time.perf_counter() - table_started
        ) * 1000
        table_content_hash = canonical_json_hash(tables_by_page)

        parser_fingerprint = self._fingerprint_overrides.get(
            "parser_chunks"
        ) or _source_fingerprint(
            self._chunk_payload,
            _canonical_view,
            _unique_search_text_variants,
            _table_search_text,
            recover_ranked_numeric_table,
            extra=(
                _ROLE_B_CHUNK_CONTRACT,
                self.version,
                raw_fingerprint,
                table_fingerprint,
                table_content_hash,
                canonical_json_hash(DocumentChunk.model_json_schema()),
            ),
        )
        parser_input_hash = canonical_json_hash(
            {"pdf_sha256": pdf_sha256, "raw_content_hash": raw_content_hash}
        )
        parser_started = time.perf_counter()
        payloads = cache.load_or_build(
            stage="parser_chunks",
            input_hash=parser_input_hash,
            fingerprint=parser_fingerprint,
            builder=lambda: [
                payload
                for page, tables in zip(raw_pages, tables_by_page, strict=True)
                if (payload := self._chunk_payload(page, tables)) is not None
            ],
            metrics=metrics,
        )
        metrics.timings_ms["parser_chunks"] = (
            time.perf_counter() - parser_started
        ) * 1000
        chunks = [self._rehydrate_chunk(payload, request.document_id) for payload in payloads]
        if not chunks and not self.last_errors:
            raise self._failure("empty_pdf", "PDF contains no non-blank text.", path)
        metrics.timings_ms["total"] = (time.perf_counter() - total_started) * 1000
        self.last_cache_metrics = {
            **metrics.as_dict(),
            "cache_enabled": True,
            "pdf_sha256": pdf_sha256,
            "raw_fingerprint": raw_fingerprint,
            "table_fingerprint": table_fingerprint,
            "parser_fingerprint": parser_fingerprint,
            "raw_content_hash": raw_content_hash,
            "table_content_hash": table_content_hash,
        }
        return chunks

    def _extract_raw_pages(self, path: Path) -> dict[str, object]:
        try:
            document = fitz.open(path)
        except Exception as exc:
            raise self._failure("pdf_open_failure", "Unable to open PDF.", path, exc) from exc
        with document:
            if document.needs_pass:
                raise self._failure("encrypted_pdf", "Encrypted PDFs are not supported.", path)
            if document.page_count == 0:
                raise self._failure("empty_pdf", "PDF contains no pages.", path)
            pages: list[dict[str, object]] = []
            errors: list[dict[str, int]] = []
            for page_index in range(document.page_count):
                try:
                    page = document.load_page(page_index)
                    pages.append(
                        {
                            "page_index": page_index,
                            "geometry": [float(page.rect.width), float(page.rect.height)],
                            "default_text": page.get_text("text").strip(),
                            "sorted_text": page.get_text("text", sort=True).strip(),
                            "blocks": [list(item) for item in page.get_text("blocks", sort=True)],
                            "words": [list(item) for item in page.get_text("words", sort=True)],
                        }
                    )
                except Exception:
                    # Persist only safe physical identity; path/exception text stays out.
                    errors.append({"page_index": page_index})
            return {"pages": pages, "errors": errors}

    def _chunk_payload(
        self,
        page: Mapping[str, object],
        tables: Sequence[Mapping[str, object]],
    ) -> dict[str, object] | None:
        page_index = int(page["page_index"])
        default_text = str(page.get("default_text") or "")
        sorted_text = str(page.get("sorted_text") or "")
        blocks = page.get("blocks") or []
        block_text = "\n".join(
            str(block[4]).strip()
            for block in blocks
            if isinstance(block, Sequence) and len(block) > 4 and str(block[4]).strip()
        )
        words = page.get("words") or []
        word_text = " ".join(
            str(word[4]).strip()
            for word in words
            if isinstance(word, Sequence) and len(word) > 4 and str(word[4]).strip()
        )
        table_text = _table_search_text(tables)
        ranked_table = recover_ranked_numeric_table(default_text)
        ranked_table_text = str(ranked_table.get("body_text") or "") if ranked_table else ""
        primary = default_text or sorted_text or block_text or word_text or table_text
        if not primary:
            return None
        physical_page = page_index + 1
        bbox = _page_text_bbox(words)
        variants = _unique_search_text_variants(
            primary,
            (
                ("sorted_text", sorted_text),
                ("block_text", block_text),
                ("word_stream", word_text),
                ("structured_table", table_text),
                ("ranked_table_body", ranked_table_text),
            ),
        )
        metadata: dict[str, object] = {
            "parser": self.name,
            "parser_version": self.version,
            "page_index": page_index,
            "physical_page": physical_page,
            "primary_text_view": (
                "default_text" if default_text else "sorted_text" if sorted_text
                else "block_text" if block_text else "word_stream" if word_text
                else "structured_table"
            ),
            "search_text_variants": variants,
            "search_text_variant_count": len(variants),
            "bbox_granularity": "page_text_union" if bbox is not None else "unavailable",
        }
        if tables:
            metadata.update({"tables": list(tables), "has_structured_tables": True})
        if ranked_table:
            metadata["ranked_numeric_table"] = ranked_table
            metadata["has_ranked_numeric_table"] = True
        return {
            "page": physical_page,
            "section": "unknown",
            "text": primary,
            "bbox": bbox,
            "block_type": "page_text",
            "metadata": metadata,
        }

    @staticmethod
    def _reconstruct_tables(words: Sequence[Sequence[object]]) -> list[dict]:
        try:
            from ipo_risk.parsers.table_reconstruction import reconstruct_page_tables

            return reconstruct_page_tables(words)
        except Exception:
            # Table reconstruction remains strictly additive and fail-soft.
            return []

    @staticmethod
    def _rehydrate_chunk(payload: Mapping[str, object], document_id: str) -> DocumentChunk:
        physical_page = int(payload["page"])
        return DocumentChunk(
            document_id=document_id,
            chunk_id=f"{document_id}:page:{physical_page}",
            page=physical_page,
            section=str(payload.get("section") or ""),
            text=str(payload["text"]),
            bbox=payload.get("bbox"),
            block_type=str(payload.get("block_type") or "page_text"),
            metadata=dict(payload.get("metadata") or {}),
        )

    def _parse_page(
        self, document: fitz.Document, document_id: str, page_index: int
    ) -> DocumentChunk | None:
        page = document.load_page(page_index)
        rectangle = getattr(page, "rect", None)
        raw = {
            "page_index": page_index,
            "geometry": (
                [float(rectangle.width), float(rectangle.height)]
                if rectangle is not None
                else []
            ),
            "default_text": page.get_text("text").strip(),
            "sorted_text": page.get_text("text", sort=True).strip(),
            "blocks": [list(item) for item in page.get_text("blocks", sort=True)],
            "words": [list(item) for item in page.get_text("words", sort=True)],
        }
        tables = self._reconstruct_tables(raw["words"])
        payload = self._chunk_payload(raw, tables)
        return self._rehydrate_chunk(payload, document_id) if payload is not None else None
