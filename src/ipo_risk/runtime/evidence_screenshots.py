"""Evidence screenshots: the cited region of the real prospectus page, exported.

The Evidence Viewer already shows a page beside the claim that cites it.  The
submission needs the same thing as a file: one PNG per cited Evidence item, and
a manifest that binds each image to the source PDF hash, the physical page, the
geometry it drew and the hash of the image itself, so a reviewer can recompute
every one of them without trusting this process.

Two things are deliberately kept apart here, because collapsing them would
overstate what we know:

``page_text_union``
    what the parser recorded on the chunk -- the union of a page's text, a real
    PDF-coordinate region but a page-level one;
``snippet_line_match`` / ``keyword_match``
    geometry PyMuPDF found for text that is actually in the retrieved snippet,
    located on this page at render time.

The second is the precise localisation the release gate asks for.  When it is
not available for an item we fall back to the recorded page-level box and label
it as such; we never present a page union as a snippet box, and we never invent
a rectangle.  An item with no geometry at all renders the page with no box drawn
and says so, because a drawn box is a claim about where something is.

Nothing is substituted when the source is wrong or absent: a PDF whose bytes do
not match the hash the run verified is refused outright, and every per-item
failure is a recorded status rather than a missing row.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence
import hashlib
import math

SCREENSHOT_MANIFEST_SCHEMA_VERSION = "v045_role_e_evidence_screenshot_manifest_v1"

DEFAULT_RENDER_DPI = 130
_HIGHLIGHT_RGB = (0.85, 0.16, 0.16)
_HIGHLIGHT_BORDER_WIDTH = 1.6

# Anchor selection.  A snippet is a window cut out of the page text, so its
# interior lines are verbatim page text and are what we search for.  Anchors are
# bounded in length because a search string spanning many lines matches nothing,
# and bounded in count because three located lines are enough to show a reviewer
# where the claim came from.
MIN_ANCHOR_CHARS = 8
MAX_ANCHOR_CHARS = 120
MAX_ANCHOR_CANDIDATES = 8
MAX_ANCHORS_USED = 3
MAX_KEYWORD_ANCHORS = 5
ANCHOR_PREVIEW_LIMIT = 40

# Matching is done against the page's own text lines rather than against raw
# search hits.  A hit that wraps comes back as one rectangle per visual line,
# which cannot be told apart from two separate occurrences by geometry alone;
# the page's line list can, because each line is one place on the page.

GRANULARITY_SNIPPET = "snippet_line_match"
GRANULARITY_KEYWORD = "keyword_match"
GRANULARITY_PAGE_UNION = "page_text_union"
GRANULARITY_UNAVAILABLE = "unavailable"

_PRECISE_GRANULARITIES = frozenset({GRANULARITY_SNIPPET, GRANULARITY_KEYWORD})

METHOD_SNIPPET_SEARCH = "pymupdf_search_snippet_line"
METHOD_KEYWORD_SEARCH = "pymupdf_search_matched_keyword"
METHOD_PARSER_BBOX = "parser_recorded_bbox"
METHOD_NONE = "none"

STATUS_RENDERED = "rendered"
STATUS_NO_PAGE = "no_page_reference"
STATUS_PAGE_OUT_OF_RANGE = "page_out_of_range"
STATUS_RENDER_FAILED = "render_failed"

MANIFEST_STATUS_RENDERED = "rendered"
MANIFEST_STATUS_NO_EVIDENCE = "no_cited_evidence"
MANIFEST_STATUS_UNAVAILABLE_PDF = "unavailable_source_pdf"
MANIFEST_STATUS_PDF_MISMATCH = "source_pdf_hash_mismatch"

_RISK_GROUPS = ("verified_risks", "pending_risks", "rejected_risks")


@dataclass(frozen=True)
class LocalisedRegion:
    """Where on the page this Evidence was located, and how precisely."""

    granularity: str
    method: str
    rects: tuple[tuple[float, float, float, float], ...] = ()
    anchors: tuple[dict[str, Any], ...] = ()

    @property
    def precise(self) -> bool:
        """True only when the geometry came from text inside the snippet."""

        return self.granularity in _PRECISE_GRANULARITIES and bool(self.rects)

    @property
    def union(self) -> tuple[float, float, float, float] | None:
        return _union(self.rects) if self.rects else None

    def as_payload(self) -> dict[str, Any]:
        return {
            "granularity": self.granularity,
            "method": self.method,
            "precise_snippet_localisation": self.precise,
            "rect_count": len(self.rects),
            "rects": [list(rect) for rect in self.rects],
            "bbox": list(self.union) if self.union is not None else None,
            "anchors": [dict(anchor) for anchor in self.anchors],
        }


@dataclass
class EvidenceCapture:
    """One cited Evidence item and the risks that cite it."""

    evidence_id: str
    page: int | None
    snippet: str
    matched_keywords: tuple[str, ...] = ()
    recorded_bbox: tuple[float, ...] | None = None
    recorded_bbox_granularity: str | None = None
    risk_ids: list[str] = field(default_factory=list)
    risk_codes: list[str] = field(default_factory=list)


def collect_cited_evidence(result: dict[str, Any]) -> list[EvidenceCapture]:
    """Every Evidence item some risk in this run actually cites, deduplicated.

    One Evidence item can support several risks; it is one page region and gets
    one screenshot, with all citing risk ids recorded against it.
    """

    captures: dict[str, EvidenceCapture] = {}
    order: list[str] = []
    for group in _RISK_GROUPS:
        for risk in result.get(group) or []:
            for evidence in risk.get("evidence") or []:
                evidence_id = str(evidence.get("evidence_id") or "")
                if not evidence_id:
                    continue
                metadata = evidence.get("metadata") or {}
                capture = captures.get(evidence_id)
                if capture is None:
                    capture = EvidenceCapture(
                        evidence_id=evidence_id,
                        page=evidence.get("page"),
                        snippet=str(evidence.get("text") or ""),
                        matched_keywords=tuple(
                            str(keyword)
                            for keyword in (metadata.get("matched_keywords") or [])
                            if str(keyword).strip()
                        ),
                        recorded_bbox=_clean_bbox(evidence.get("bbox")),
                        recorded_bbox_granularity=metadata.get("bbox_granularity"),
                    )
                    captures[evidence_id] = capture
                    order.append(evidence_id)
                risk_id = risk.get("risk_id")
                if risk_id and risk_id not in capture.risk_ids:
                    capture.risk_ids.append(str(risk_id))
                risk_code = risk.get("risk_code")
                if risk_code and risk_code not in capture.risk_codes:
                    capture.risk_codes.append(str(risk_code))
    return [captures[evidence_id] for evidence_id in order]


def _clean_bbox(value: Any) -> tuple[float, float, float, float] | None:
    """A bbox we can draw, or nothing.  A malformed box is not repaired."""

    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        rect = tuple(float(item) for item in value)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in rect):
        return None
    if rect[2] <= rect[0] or rect[3] <= rect[1]:
        return None
    return rect  # type: ignore[return-value]


def snippet_anchors(snippet: str) -> list[str]:
    """Searchable verbatim fragments of a retrieved snippet.

    The snippet is a character window cut out of the page text, so its first and
    last lines may be truncated mid-line.  Interior lines are preferred; the
    truncated ends are kept as lower-priority candidates rather than dropped,
    since a partial line is still verbatim page text.
    """

    lines = [line.strip() for line in (snippet or "").splitlines()]
    interior = [line for line in lines[1:-1] if len(line) >= MIN_ANCHOR_CHARS]
    edges = [line for line in (lines[:1] + lines[-1:]) if len(line) >= MIN_ANCHOR_CHARS]
    if len(lines) == 1:
        interior, edges = edges, []
    ranked = sorted(interior, key=len, reverse=True) + sorted(edges, key=len, reverse=True)
    anchors: list[str] = []
    for line in ranked:
        anchor = line[:MAX_ANCHOR_CHARS].strip()
        if len(anchor) >= MIN_ANCHOR_CHARS and anchor not in anchors:
            anchors.append(anchor)
        if len(anchors) >= MAX_ANCHOR_CANDIDATES:
            break
    return anchors


def normalise_for_match(value: str) -> str:
    """Whitespace-insensitive form; PDF text lines space CJK characters freely."""

    return "".join((value or "").split())


def page_lines(page: Any) -> list[dict[str, Any]]:
    """The page's own text lines with their real rectangles.

    The parser's page text and this line list come from the same engine, so a
    snippet line is a page line -- which makes "how many times does this text
    appear here" an exact count rather than a guess about geometry.
    """

    lines: list[dict[str, Any]] = []
    try:
        payload = page.get_text("dict")
    except Exception:  # a page whose structure cannot be read locates nothing
        return lines
    for block in payload.get("blocks", []) or []:
        for line in block.get("lines", []) or []:
            spans = line.get("spans", []) or []
            content = "".join(str(span.get("text") or "") for span in spans)
            rect = _clean_bbox(line.get("bbox"))
            if not content.strip() or rect is None:
                continue
            lines.append({"text": content, "normalised": normalise_for_match(content), "bbox": rect})
    return lines


def _anchor_record(
    anchor: str, kind: str, *, occurrence_count: int, accepted: bool, narrowed: bool = False
) -> dict[str, Any]:
    """Enough to re-run the search, without restating licensed text in bulk.

    A rejected anchor stays in the record: "this text is on the page twice, so
    we did not box either one" is the evidence that no box was guessed.
    """

    flat = " ".join(anchor.split())
    preview = flat if len(flat) <= ANCHOR_PREVIEW_LIMIT else f"{flat[:ANCHOR_PREVIEW_LIMIT]}…"
    return {
        "kind": kind,
        "preview": preview,
        "char_length": len(anchor),
        "sha256": hashlib.sha256(anchor.encode("utf-8")).hexdigest(),
        "matched_page_line_count": occurrence_count,
        "accepted": accepted,
        # A narrowed anchor is boxed at the exact hit inside its line; an
        # un-narrowed one is boxed at the whole line that uniquely contains it.
        "narrowed_within_line": narrowed,
        "rejection_reason": (
            None
            if accepted
            else "ambiguous: the text appears on more than one line of this page"
        ),
    }


def _union(
    rects: Sequence[tuple[float, float, float, float]]
) -> tuple[float, float, float, float]:
    return (
        min(rect[0] for rect in rects),
        min(rect[1] for rect in rects),
        max(rect[2] for rect in rects),
        max(rect[3] for rect in rects),
    )


def _search(page: Any, needle: str, clip: Any = None) -> list[tuple[float, float, float, float]]:
    try:
        found = page.search_for(needle, clip=clip) if clip is not None else page.search_for(needle)
    except Exception:  # a search that cannot run locates nothing; it invents nothing
        return []
    rects: list[tuple[float, float, float, float]] = []
    page_rect = page.rect
    for rect in found or []:
        candidate = _clean_bbox((rect.x0, rect.y0, rect.x1, rect.y1))
        if candidate is None:
            continue
        if not (
            candidate[0] >= page_rect.x0 - 1
            and candidate[1] >= page_rect.y0 - 1
            and candidate[2] <= page_rect.x1 + 1
            and candidate[3] <= page_rect.y1 + 1
        ):
            continue
        rects.append(candidate)
    return rects


def localise_evidence(page: Any, capture: EvidenceCapture) -> LocalisedRegion:
    """Locate the cited text on this page, or fall back and say so.

    Priority: text from the snippet, then the keywords the retriever actually
    matched, then the parser's page-level union.  Each step is labelled with the
    granularity it earned, so a page union can never be read as a snippet box.

    Only a unique match counts.  Text that appears on more than one line of the
    page cannot tell us which line the Evidence came from, and a box drawn on
    the wrong one would be a false claim about where the risk was found.
    """

    lines = page_lines(page)

    def _collect(candidates: Sequence[str], kind: str) -> tuple[list, list]:
        rects: list[tuple[float, float, float, float]] = []
        records: list[dict[str, Any]] = []
        accepted = 0
        seen: set[str] = set()
        for candidate in candidates:
            needle = candidate.strip()[:MAX_ANCHOR_CHARS].strip()
            normalised = normalise_for_match(needle)
            if len(normalised) < MIN_ANCHOR_CHARS or normalised in seen:
                continue
            seen.add(normalised)
            matches = [line for line in lines if normalised in line["normalised"]]
            if not matches:
                continue
            if len(matches) > 1:
                records.append(
                    _anchor_record(needle, kind, occurrence_count=len(matches), accepted=False)
                )
                continue
            line = matches[0]
            # Inside the one line that contains it, the hit itself is a tighter
            # box of the same real geometry; the whole line is used when the
            # search cannot resolve it, which happens when that line spaces its
            # characters differently from the text we matched.
            within = _search(page, needle, clip=line["bbox"])
            # One anchor is one box.  The hits inside a line are the fragments
            # of that single match, and their union cannot exceed the line we
            # would otherwise have drawn, so joining them overstates nothing.
            rects.append(_union(within) if within else line["bbox"])
            records.append(
                _anchor_record(
                    needle, kind, occurrence_count=1, accepted=True, narrowed=bool(within)
                )
            )
            accepted += 1
            if accepted >= MAX_ANCHORS_USED:
                break
        return rects, records

    rects, anchors = _collect(snippet_anchors(capture.snippet), "snippet_line")
    if rects:
        return LocalisedRegion(
            granularity=GRANULARITY_SNIPPET,
            method=METHOD_SNIPPET_SEARCH,
            rects=tuple(rects),
            anchors=tuple(anchors),
        )

    keyword_rects, keyword_anchors = _collect(
        capture.matched_keywords[:MAX_KEYWORD_ANCHORS], "matched_keyword"
    )
    anchors = anchors + keyword_anchors
    if keyword_rects:
        return LocalisedRegion(
            granularity=GRANULARITY_KEYWORD,
            method=METHOD_KEYWORD_SEARCH,
            rects=tuple(keyword_rects),
            anchors=tuple(anchors),
        )

    # Validated here as well as at collection time: a caller handing us a raw
    # payload must not be able to put a malformed box on a page.
    recorded = _clean_bbox(capture.recorded_bbox)
    if recorded is not None:
        return LocalisedRegion(
            granularity=capture.recorded_bbox_granularity or GRANULARITY_PAGE_UNION,
            method=METHOD_PARSER_BBOX,
            rects=(recorded,),
            anchors=tuple(anchors),
        )
    return LocalisedRegion(
        granularity=GRANULARITY_UNAVAILABLE, method=METHOD_NONE, anchors=tuple(anchors)
    )


def screenshot_filename(capture: EvidenceCapture) -> str:
    """Deterministic name: the page it shows and the Evidence it belongs to."""

    page = capture.page if isinstance(capture.page, int) and capture.page >= 1 else 0
    return f"page{page:04d}_{capture.evidence_id}.png"


def _render(page: Any, region: LocalisedRegion, dpi: int) -> tuple[bytes, int, int]:
    import pymupdf

    for rect in region.rects:
        rectangle = pymupdf.Rect(*rect)
        if rectangle.is_empty:
            continue
        annotation = page.add_rect_annot(rectangle)
        annotation.set_colors(stroke=_HIGHLIGHT_RGB)
        annotation.set_border(width=_HIGHLIGHT_BORDER_WIDTH)
        annotation.update(opacity=0.9)
    pixmap = page.get_pixmap(dpi=dpi)
    return pixmap.tobytes("png"), pixmap.width, pixmap.height


class EvidenceCaptureError(RuntimeError):
    """This Evidence item cannot be shown, with the reason it cannot.

    ``code`` is one of the item statuses, so a caller -- the export or the
    Evidence Viewer -- reports the same refusal the manifest would record.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def capture_evidence_page(
    pdf_bytes: bytes,
    capture: EvidenceCapture,
    *,
    dpi: int = DEFAULT_RENDER_DPI,
) -> tuple[bytes, LocalisedRegion, int, int]:
    """One rendered page with the located region outlined, and what was located.

    The Evidence Viewer and the screenshot export share this so that what a
    reviewer sees on screen is the same geometry, found the same way, as the
    image the submission ships.
    """

    import pymupdf

    if not pdf_bytes:
        raise EvidenceCaptureError(
            STATUS_RENDER_FAILED, "no prospectus bytes are available for this run"
        )
    if not isinstance(capture.page, int) or capture.page < 1:
        raise EvidenceCaptureError(
            STATUS_NO_PAGE,
            "the Evidence carries no 1-indexed physical page, so no page can be shown",
        )
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        if capture.page > document.page_count:
            raise EvidenceCaptureError(
                STATUS_PAGE_OUT_OF_RANGE,
                f"page {capture.page} is beyond the document's "
                f"{document.page_count} physical page(s)",
            )
        page = document.load_page(capture.page - 1)
        region = localise_evidence(page, capture)
        image, width, height = _render(page, region, dpi)
    return image, region, width, height


def _capture_item(
    pdf_bytes: bytes,
    capture: EvidenceCapture,
    *,
    output_dir: Path | None,
    dpi: int,
) -> dict[str, Any]:
    """Render one Evidence item, or record exactly why it was not rendered."""

    row: dict[str, Any] = {
        "evidence_id": capture.evidence_id,
        "risk_ids": list(capture.risk_ids),
        "risk_codes": list(capture.risk_codes),
        "page": capture.page,
        "recorded_bbox": list(capture.recorded_bbox) if capture.recorded_bbox else None,
        "recorded_bbox_granularity": capture.recorded_bbox_granularity,
    }
    unrendered = {
        "localisation": LocalisedRegion(GRANULARITY_UNAVAILABLE, METHOD_NONE).as_payload(),
        "highlight_drawn": False,
        "screenshot": None,
    }
    try:
        image, region, width, height = capture_evidence_page(pdf_bytes, capture, dpi=dpi)
    except EvidenceCaptureError as exc:
        return {**row, "status": exc.code, "reason": str(exc), **unrendered}
    except Exception as exc:  # a failed render is reported, never approximated
        return {
            **row,
            "status": STATUS_RENDER_FAILED,
            "reason": f"{type(exc).__name__}: {exc}",
            **unrendered,
        }

    filename = screenshot_filename(capture)
    if output_dir is not None:
        (output_dir / filename).write_bytes(image)
    return {
        **row,
        "status": STATUS_RENDERED,
        "reason": None,
        "localisation": region.as_payload(),
        "highlight_drawn": bool(region.rects),
        "screenshot": {
            "filename": filename,
            "sha256": hashlib.sha256(image).hexdigest(),
            "byte_size": len(image),
            "pixel_width": width,
            "pixel_height": height,
            "render_dpi": dpi,
        },
    }


def build_evidence_screenshots(
    *,
    case_id: str,
    stock_code: str,
    result: dict[str, Any],
    pdf_bytes: bytes | None,
    expected_pdf_sha256: str | None = None,
    output_dir: Path | None = None,
    dpi: int = DEFAULT_RENDER_DPI,
) -> dict[str, Any]:
    """Render every cited Evidence item and return the hash-bound manifest.

    ``output_dir`` may be ``None`` to compute the manifest without writing PNGs;
    the recorded image hashes are of the same bytes either way.
    """

    captures = collect_cited_evidence(result)
    source: dict[str, Any] = {
        "sha256": hashlib.sha256(pdf_bytes).hexdigest() if pdf_bytes else None,
        "byte_size": len(pdf_bytes) if pdf_bytes else None,
        "expected_sha256": expected_pdf_sha256,
        "sha256_matches_expected": None,
        # The prospectus is licensed and lives outside the repository: it is
        # identified by hash, never by a local path.
        "path_recorded": False,
    }
    if pdf_bytes:
        source["sha256_matches_expected"] = (
            None if expected_pdf_sha256 is None else source["sha256"] == expected_pdf_sha256
        )

    def _manifest(status: str, statement: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        rendered = [item for item in items if item["status"] == STATUS_RENDERED]
        precise = [
            item
            for item in rendered
            if item["localisation"]["precise_snippet_localisation"] is True
        ]
        granularities: dict[str, int] = {}
        for item in rendered:
            key = str(item["localisation"]["granularity"])
            granularities[key] = granularities.get(key, 0) + 1
        return {
            "schema_version": SCREENSHOT_MANIFEST_SCHEMA_VERSION,
            "case_id": case_id,
            "stock_code": stock_code,
            "status": status,
            "statement": statement,
            "render_dpi": dpi,
            "render_engine": "pymupdf",
            "source_pdf": source,
            "cited_evidence_count": len(captures),
            "screenshot_count": len(rendered),
            "precise_localisation_count": len(precise),
            "page_level_fallback_count": sum(
                1
                for item in rendered
                if item["localisation"]["method"] == METHOD_PARSER_BBOX
            ),
            "no_geometry_count": sum(
                1
                for item in rendered
                if item["localisation"]["granularity"] == GRANULARITY_UNAVAILABLE
            ),
            "unrendered_count": len(items) - len(rendered),
            "ambiguous_anchor_count": sum(
                1
                for item in rendered
                for anchor in item["localisation"]["anchors"]
                if anchor.get("accepted") is False
            ),
            "granularity_counts": granularities,
            "granularity_note": (
                "snippet_line_match / keyword_match are PDF coordinates PyMuPDF found for text "
                "that is in the retrieved snippet. page_text_union is the parser's page-level "
                "region and is never reported as a snippet box. unavailable means the page was "
                "rendered with no box drawn."
            ),
            "items": items,
        }

    if not captures:
        return _manifest(
            MANIFEST_STATUS_NO_EVIDENCE,
            "No risk in this run cites Evidence, so there is nothing to screenshot.",
            [],
        )
    if not pdf_bytes:
        return _manifest(
            MANIFEST_STATUS_UNAVAILABLE_PDF,
            "The source prospectus bytes were not available, so no page was rendered. "
            "No image is produced from any other source.",
            [],
        )
    if source["sha256_matches_expected"] is False:
        return _manifest(
            MANIFEST_STATUS_PDF_MISMATCH,
            "The supplied PDF does not match the SHA-256 the run verified, so it is refused. "
            "A screenshot of a different document would misattribute the Evidence.",
            [],
        )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
    items = [
        _capture_item(pdf_bytes, capture, output_dir=output_dir, dpi=dpi) for capture in captures
    ]
    return _manifest(
        MANIFEST_STATUS_RENDERED,
        "Each image is one physical prospectus page as it is, with the located region outlined; "
        "the manifest binds it to the source PDF hash, the page, the geometry and the image hash.",
        items,
    )


def summarise_screenshot_manifests(manifests: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Matrix-level view: how much of the cited Evidence is precisely located."""

    collected = list(manifests)
    cited = sum(int(manifest.get("cited_evidence_count") or 0) for manifest in collected)
    rendered = sum(int(manifest.get("screenshot_count") or 0) for manifest in collected)
    precise = sum(int(manifest.get("precise_localisation_count") or 0) for manifest in collected)
    return {
        "schema_version": SCREENSHOT_MANIFEST_SCHEMA_VERSION,
        "case_count": len(collected),
        "cases_with_screenshots": sum(
            1 for manifest in collected if int(manifest.get("screenshot_count") or 0) > 0
        ),
        "cited_evidence_count": cited,
        "screenshot_count": rendered,
        "precise_localisation_count": precise,
        "precise_localisation_rate": round(precise / rendered, 4) if rendered else None,
        "page_level_fallback_count": sum(
            int(manifest.get("page_level_fallback_count") or 0) for manifest in collected
        ),
        "no_geometry_count": sum(
            int(manifest.get("no_geometry_count") or 0) for manifest in collected
        ),
        "unrendered_count": sum(
            int(manifest.get("unrendered_count") or 0) for manifest in collected
        ),
        "case_statuses": {
            str(manifest.get("case_id")): manifest.get("status") for manifest in collected
        },
        "statement": (
            "Rendered screenshots cover the Evidence the risks cite. The precise count is the "
            "subset located from snippet text; the rest keep the parser's page-level region and "
            "are labelled as such."
        ),
    }


__all__ = [
    "DEFAULT_RENDER_DPI",
    "EvidenceCapture",
    "EvidenceCaptureError",
    "GRANULARITY_KEYWORD",
    "GRANULARITY_PAGE_UNION",
    "GRANULARITY_SNIPPET",
    "GRANULARITY_UNAVAILABLE",
    "LocalisedRegion",
    "MANIFEST_STATUS_NO_EVIDENCE",
    "MANIFEST_STATUS_PDF_MISMATCH",
    "MANIFEST_STATUS_RENDERED",
    "MANIFEST_STATUS_UNAVAILABLE_PDF",
    "METHOD_KEYWORD_SEARCH",
    "METHOD_NONE",
    "METHOD_PARSER_BBOX",
    "METHOD_SNIPPET_SEARCH",
    "SCREENSHOT_MANIFEST_SCHEMA_VERSION",
    "STATUS_NO_PAGE",
    "STATUS_PAGE_OUT_OF_RANGE",
    "STATUS_RENDERED",
    "STATUS_RENDER_FAILED",
    "build_evidence_screenshots",
    "capture_evidence_page",
    "collect_cited_evidence",
    "localise_evidence",
    "normalise_for_match",
    "page_lines",
    "screenshot_filename",
    "snippet_anchors",
    "summarise_screenshot_manifests",
]
