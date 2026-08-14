"""Deterministic preservation audit for parser text against expert evidence."""

from __future__ import annotations

from collections import Counter
import csv
from difflib import SequenceMatcher
from enum import StrEnum
import hashlib
from pathlib import Path
import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle, ExpertEvidenceAnnotation
from ipo_risk.schemas import AnalysisError, DocumentChunk


class TextMatch(StrEnum):
    EXACT = "exact"
    PARTIAL = "partial"
    NONE = "none"


class StructureType(StrEnum):
    TEXT = "TEXT"
    FINANCIAL_TABLE = "FINANCIAL_TABLE"
    BUSINESS_TABLE = "BUSINESS_TABLE"
    DIAGRAM = "DIAGRAM"
    MIXED = "MIXED"


class StructureRecoverability(StrEnum):
    FULLY_RECOVERABLE = "FULLY_RECOVERABLE"
    PARTIALLY_RECOVERABLE = "PARTIALLY_RECOVERABLE"
    NOT_RECOVERABLE = "NOT_RECOVERABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvidenceAuditStatus(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"


class FailureCode(StrEnum):
    PARSER_PAGE_MISSING = "PARSER_PAGE_MISSING"
    PARSER_TEXT_MISSING = "PARSER_TEXT_MISSING"
    PARSER_NUMERIC_MISSING = "PARSER_NUMERIC_MISSING"
    TABLE_STRUCTURE_PARTIAL = "TABLE_STRUCTURE_PARTIAL"
    TABLE_STRUCTURE_BROKEN = "TABLE_STRUCTURE_BROKEN"
    DIAGRAM_RELATIONSHIP_LOST = "DIAGRAM_RELATIONSHIP_LOST"
    READING_ORDER_DISTORTED = "READING_ORDER_DISTORTED"
    NORMALIZATION_ONLY_DIFFERENCE = "NORMALIZATION_ONLY_DIFFERENCE"
    NONE = "NONE"


class EvidencePreservationRecord(BaseModel):
    """One independently assessed Expert Evidence record."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    risk_code: str
    evidence_index: int = Field(ge=0)
    page: int = Field(ge=1)
    evidence_role: str
    requirement: str
    source_authority: str
    gold_exact_text: str
    gold_text_sha256: str
    parser_page_present: bool
    parser_text_sha256: str | None = None
    normalized_text_match: TextMatch
    core_text_preserved: bool
    core_text_coverage: float = Field(ge=0.0, le=1.0)
    numeric_values_expected: list[str] = Field(default_factory=list)
    numeric_values_found: list[str] = Field(default_factory=list)
    numeric_preservation_rate: float = Field(ge=0.0, le=1.0)
    structure_type: StructureType
    structure_recoverability: StructureRecoverability
    final_status: EvidenceAuditStatus
    failure_codes: list[FailureCode] = Field(default_factory=list)
    notes: str = ""


class ParserPreservationSummary(BaseModel):
    """Aggregate diagnostic metrics for one prospectus."""

    model_config = ConfigDict(extra="forbid")

    total_evidence: int
    required_evidence: int
    page_preservation_rate: float
    normalized_exact_text_match_rate: float
    core_text_preservation_rate: float
    numeric_preservation_rate: float
    required_evidence_preservation_rate: float
    required_pass_or_partial_rate: float
    table_evidence_count: int
    table_fully_recoverable_rate: float
    table_at_least_partial_recoverable_rate: float
    diagram_evidence_count: int
    pass_count: int
    partial_count: int
    fail_count: int
    failure_taxonomy_counts: dict[str, int]
    diagnostic_status: str


class ParserPreservationAudit(BaseModel):
    """Machine-readable outcome for one parser/case combination."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    stock_code: str
    company_name: str
    annotation_version: str
    annotation_sha256: str
    pdf_sha256: str
    pdf_page_count: int
    parser: str
    parser_chunk_count: int
    parser_errors: list[dict[str, object]] = Field(default_factory=list)
    retriever_used: bool = False
    llm_used: bool = False
    agent_used: bool = False
    human_golden_used: bool = False
    market_outcome_used: bool = False
    blind_2025_accessed: bool = False
    production_parser_changed: bool = False
    retriever_changed: bool = False
    agent_changed: bool = False
    verifier_changed: bool = False
    supervisor_changed: bool = False
    records: list[EvidencePreservationRecord]
    summary: ParserPreservationSummary
    parser_decision: str
    recommend_retriever_audit: bool
    table_aware_enhancement: str


_DOT_LEADERS = re.compile(r"[\.·•‧…⋯]{2,}")
_WHITESPACE = re.compile(r"\s+")
_NUMBER_BODY = r"-?\d[\d,]*(?:\.\d+)?"
_NUMERIC_TOKEN = re.compile(rf"(?<![\d.,])(?:\({_NUMBER_BODY}\)|{_NUMBER_BODY})\s*%?")
_NON_CORE = re.compile(r"[^0-9A-Za-z\u3400-\u9fff]+")


def normalize_text(text: str) -> str:
    """Normalize layout noise without removing economic punctuation or signs."""
    normalized = unicodedata.normalize("NFKC", text).lower().replace("\u00ad", "")
    normalized = _DOT_LEADERS.sub(" ", normalized)
    return _WHITESPACE.sub(" ", normalized).strip()


def comparison_text(text: str) -> str:
    """Produce the deterministic layout-insensitive comparison representation."""
    return _WHITESPACE.sub("", normalize_text(text))


def _decimal_token(raw: str) -> str:
    token = _WHITESPACE.sub("", raw)
    percent = token.endswith("%")
    if percent:
        token = token[:-1]
    negative_parentheses = token.startswith("(") and token.endswith(")")
    if negative_parentheses:
        token = token[1:-1]
    token = token.replace(",", "")
    if token.startswith("+"):
        token = token[1:]
    if negative_parentheses and not token.startswith("-"):
        token = "-" + token
    try:
        number = float(token)
    except ValueError:
        canonical = token
    else:
        canonical = format(number, ".15g")
        if canonical == "-0":
            canonical = "0"
    return canonical + ("%" if percent else "")


def extract_numeric_tokens(text: str) -> list[str]:
    """Extract normalized numeric tokens while preserving sign and percent semantics."""
    return [_decimal_token(match.group(0)) for match in _NUMERIC_TOKEN.finditer(normalize_text(text))]


def extract_critical_numeric_tokens(text: str) -> list[str]:
    """Exclude likely years, row indices and note references from critical facts."""
    critical: list[str] = []
    for match in _NUMERIC_TOKEN.finditer(normalize_text(text)):
        raw = match.group(0)
        token = _decimal_token(raw)
        numeric = token.removesuffix("%")
        try:
            value = float(numeric)
        except ValueError:
            continue
        is_year = not token.endswith("%") and value.is_integer() and 1900 <= value <= 2100
        if is_year:
            continue
        if token.endswith("%") or value < 0 or abs(value) >= 1000 or "." in raw:
            critical.append(token)
    return critical


def _ordered_coverage(gold: str, parsed: str) -> float:
    if not gold:
        return 1.0
    matcher = SequenceMatcher(None, gold, parsed, autojunk=False)
    return min(1.0, sum(block.size for block in matcher.get_matching_blocks()) / len(gold))


def _core_text(text: str) -> str:
    without_numbers = _NUMERIC_TOKEN.sub("", normalize_text(text))
    return _NON_CORE.sub("", without_numbers)


def classify_structure(evidence: ExpertEvidenceAnnotation) -> StructureType:
    """Classify evidence using domain semantics and flattened-text characteristics."""
    numbers = extract_numeric_tokens(evidence.exact_text)
    percent_count = sum(token.endswith("%") for token in numbers)
    authority = evidence.source_authority.value
    if authority == "corporate_structure" and percent_count >= 3:
        return StructureType.DIAGRAM
    if authority in {"accountants_report", "audited_financial_statement", "financial_information"} and len(numbers) >= 2:
        return StructureType.FINANCIAL_TABLE
    if authority == "business_section" and evidence.risk_code in {"customer_concentration", "supplier_concentration"} and len(numbers) >= 2:
        return StructureType.BUSINESS_TABLE
    if authority == "business_section" and evidence.risk_code == "precommercial_product" and len(numbers) >= 3:
        return StructureType.MIXED
    return StructureType.TEXT


def _numeric_preservation(expected: list[str], parsed_text: str) -> tuple[list[str], float]:
    if not expected:
        return [], 1.0
    available = Counter(extract_numeric_tokens(parsed_text))
    found: list[str] = []
    for token in expected:
        if available[token] > 0:
            found.append(token)
            available[token] -= 1
    return found, len(found) / len(expected)


def audit_evidence(
    bundle: ExpertAnnotationBundle,
    chunks: list[DocumentChunk],
) -> list[EvidencePreservationRecord]:
    """Compare every Expert Evidence record with the parser's physical-page chunk."""
    pages = {chunk.page: chunk for chunk in chunks}
    records: list[EvidencePreservationRecord] = []
    for index, evidence in enumerate(bundle.evidence):
        chunk = pages.get(evidence.page)
        structure_type = classify_structure(evidence)
        expected_numbers = extract_critical_numeric_tokens(evidence.exact_text)
        gold_hash = hashlib.sha256(evidence.exact_text.encode("utf-8")).hexdigest()
        if chunk is None:
            records.append(EvidencePreservationRecord(
                case_id=evidence.case_id,
                risk_code=evidence.risk_code,
                evidence_index=index,
                page=evidence.page,
                evidence_role=evidence.evidence_role.value,
                requirement=evidence.requirement.value,
                source_authority=evidence.source_authority.value,
                gold_exact_text=evidence.exact_text,
                gold_text_sha256=gold_hash,
                parser_page_present=False,
                normalized_text_match=TextMatch.NONE,
                core_text_preserved=False,
                core_text_coverage=0.0,
                numeric_values_expected=expected_numbers,
                numeric_preservation_rate=0.0 if expected_numbers else 1.0,
                structure_type=structure_type,
                structure_recoverability=StructureRecoverability.NOT_RECOVERABLE,
                final_status=EvidenceAuditStatus.FAIL,
                failure_codes=[FailureCode.PARSER_PAGE_MISSING],
                notes="No non-blank DocumentChunk exists for the physical page.",
            ))
            continue

        parsed_text = chunk.text
        gold_comparison = comparison_text(evidence.exact_text)
        parser_comparison = comparison_text(parsed_text)
        normalized_exact = bool(gold_comparison) and gold_comparison in parser_comparison
        core_coverage = _ordered_coverage(_core_text(evidence.exact_text), _core_text(parsed_text))
        core_preserved = normalized_exact or core_coverage >= 0.85
        text_match = TextMatch.EXACT if normalized_exact else (TextMatch.PARTIAL if core_preserved else TextMatch.NONE)
        found_numbers, numeric_rate = _numeric_preservation(expected_numbers, parsed_text)

        if structure_type is StructureType.TEXT:
            recoverability = StructureRecoverability.NOT_APPLICABLE
        elif structure_type is StructureType.DIAGRAM:
            recoverability = (
                StructureRecoverability.PARTIALLY_RECOVERABLE
                if core_preserved and numeric_rate == 1.0
                else StructureRecoverability.NOT_RECOVERABLE
            )
        elif normalized_exact and numeric_rate == 1.0:
            recoverability = StructureRecoverability.FULLY_RECOVERABLE
        elif core_preserved and numeric_rate >= 0.8:
            recoverability = StructureRecoverability.PARTIALLY_RECOVERABLE
        else:
            recoverability = StructureRecoverability.NOT_RECOVERABLE

        failures: list[FailureCode] = []
        if not core_preserved:
            failures.append(FailureCode.PARSER_TEXT_MISSING)
        if numeric_rate < 1.0:
            failures.append(FailureCode.PARSER_NUMERIC_MISSING)
        if normalized_exact and evidence.exact_text not in parsed_text:
            failures.append(FailureCode.NORMALIZATION_ONLY_DIFFERENCE)
        elif text_match is TextMatch.PARTIAL:
            failures.append(FailureCode.READING_ORDER_DISTORTED)
        if structure_type is StructureType.DIAGRAM and recoverability is not StructureRecoverability.NOT_RECOVERABLE:
            failures.append(FailureCode.DIAGRAM_RELATIONSHIP_LOST)
        elif structure_type in {StructureType.FINANCIAL_TABLE, StructureType.BUSINESS_TABLE, StructureType.MIXED}:
            if recoverability is StructureRecoverability.PARTIALLY_RECOVERABLE:
                failures.append(FailureCode.TABLE_STRUCTURE_PARTIAL)
            elif recoverability is StructureRecoverability.NOT_RECOVERABLE:
                failures.append(FailureCode.TABLE_STRUCTURE_BROKEN)

        hard_failure = (
            not core_preserved
            or numeric_rate < 1.0
            or recoverability is StructureRecoverability.NOT_RECOVERABLE
        )
        if hard_failure:
            final_status = EvidenceAuditStatus.FAIL
        elif recoverability is StructureRecoverability.PARTIALLY_RECOVERABLE or text_match is TextMatch.PARTIAL:
            final_status = EvidenceAuditStatus.PARTIAL
        else:
            final_status = EvidenceAuditStatus.PASS
        if not failures:
            failures = [FailureCode.NONE]

        records.append(EvidencePreservationRecord(
            case_id=evidence.case_id,
            risk_code=evidence.risk_code,
            evidence_index=index,
            page=evidence.page,
            evidence_role=evidence.evidence_role.value,
            requirement=evidence.requirement.value,
            source_authority=evidence.source_authority.value,
            gold_exact_text=evidence.exact_text,
            gold_text_sha256=gold_hash,
            parser_page_present=True,
            parser_text_sha256=hashlib.sha256(parsed_text.encode("utf-8")).hexdigest(),
            normalized_text_match=text_match,
            core_text_preserved=core_preserved,
            core_text_coverage=core_coverage,
            numeric_values_expected=expected_numbers,
            numeric_values_found=found_numbers,
            numeric_preservation_rate=numeric_rate,
            structure_type=structure_type,
            structure_recoverability=recoverability,
            final_status=final_status,
            failure_codes=failures,
            notes=(
                "Flattened parser text preserves content but not diagram relationships."
                if structure_type is StructureType.DIAGRAM and final_status is EvidenceAuditStatus.PARTIAL
                else ""
            ),
        ))
    return records


def summarize_records(records: list[EvidencePreservationRecord]) -> ParserPreservationSummary:
    """Compute the frozen diagnostic metrics from evidence-level records."""
    total = len(records)
    required = [record for record in records if record.requirement == "required"]
    tables = [record for record in records if record.structure_type in {
        StructureType.FINANCIAL_TABLE, StructureType.BUSINESS_TABLE, StructureType.MIXED,
    }]
    diagrams = [record for record in records if record.structure_type is StructureType.DIAGRAM]
    expected_numeric = sum(len(record.numeric_values_expected) for record in records)
    found_numeric = sum(len(record.numeric_values_found) for record in records)

    def rate(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 1.0

    taxonomy = Counter(
        code.value
        for record in records
        for code in record.failure_codes
        if code is not FailureCode.NONE
    )
    page_rate = rate(sum(record.parser_page_present for record in records), total)
    exact_rate = rate(sum(record.normalized_text_match is TextMatch.EXACT for record in records), total)
    core_rate = rate(sum(record.core_text_preserved for record in records), total)
    numeric_rate = rate(found_numeric, expected_numeric)
    required_pass_rate = rate(sum(record.final_status is EvidenceAuditStatus.PASS for record in required), len(required))
    required_usable_rate = rate(sum(record.final_status is not EvidenceAuditStatus.FAIL for record in required), len(required))
    table_full_rate = rate(sum(record.structure_recoverability is StructureRecoverability.FULLY_RECOVERABLE for record in tables), len(tables))
    table_usable_rate = rate(sum(record.structure_recoverability in {
        StructureRecoverability.FULLY_RECOVERABLE,
        StructureRecoverability.PARTIALLY_RECOVERABLE,
    } for record in tables), len(tables))
    threshold_pass = (
        page_rate >= 0.98
        and core_rate >= 0.95
        and numeric_rate >= 0.99
        and required_usable_rate >= 0.95
        and table_usable_rate >= 0.90
    )
    fail_count = sum(record.final_status is EvidenceAuditStatus.FAIL for record in records)
    diagnostic = "PASS" if threshold_pass and fail_count == 0 else ("CAUTION" if fail_count == 0 else "FAIL")
    return ParserPreservationSummary(
        total_evidence=total,
        required_evidence=len(required),
        page_preservation_rate=page_rate,
        normalized_exact_text_match_rate=exact_rate,
        core_text_preservation_rate=core_rate,
        numeric_preservation_rate=numeric_rate,
        required_evidence_preservation_rate=required_pass_rate,
        required_pass_or_partial_rate=required_usable_rate,
        table_evidence_count=len(tables),
        table_fully_recoverable_rate=table_full_rate,
        table_at_least_partial_recoverable_rate=table_usable_rate,
        diagram_evidence_count=len(diagrams),
        pass_count=sum(record.final_status is EvidenceAuditStatus.PASS for record in records),
        partial_count=sum(record.final_status is EvidenceAuditStatus.PARTIAL for record in records),
        fail_count=fail_count,
        failure_taxonomy_counts=dict(sorted(taxonomy.items())),
        diagnostic_status=diagnostic,
    )


def build_audit(
    *,
    bundle: ExpertAnnotationBundle,
    chunks: list[DocumentChunk],
    pdf_sha256: str,
    pdf_page_count: int,
    annotation_sha256: str,
    parser_errors: list[AnalysisError] | None = None,
) -> ParserPreservationAudit:
    """Build a complete parser-only audit without invoking retrieval or Agents."""
    records = audit_evidence(bundle, chunks)
    summary = summarize_records(records)
    broken_tables = summary.failure_taxonomy_counts.get(FailureCode.TABLE_STRUCTURE_BROKEN.value, 0)
    if summary.numeric_preservation_rate < 0.99:
        decision = "BLOCK_RETRIEVER_OPTIMIZATION"
    elif broken_tables > 0 or summary.table_at_least_partial_recoverable_rate < 0.90:
        decision = "TABLE_AWARE_PARSER_REQUIRED"
    elif summary.page_preservation_rate < 0.98:
        decision = "OCR_FALLBACK_REQUIRED"
    else:
        decision = "KEEP_CURRENT_PARSER_FOR_RETRIEVAL_EXPERIMENTS"
    return ParserPreservationAudit(
        case_id=bundle.case_id,
        stock_code=bundle.stock_code,
        company_name=bundle.company_name,
        annotation_version=bundle.annotation_version,
        annotation_sha256=annotation_sha256,
        pdf_sha256=pdf_sha256,
        pdf_page_count=pdf_page_count,
        parser="pymupdf",
        parser_chunk_count=len(chunks),
        parser_errors=[error.model_dump(mode="json") for error in (parser_errors or [])],
        records=records,
        summary=summary,
        parser_decision=decision,
        recommend_retriever_audit=decision == "KEEP_CURRENT_PARSER_FOR_RETRIEVAL_EXPERIMENTS",
        table_aware_enhancement="FUTURE_CANDIDATE",
    )


def write_audit_outputs(audit: ParserPreservationAudit, output_dir: Path) -> tuple[Path, Path, Path]:
    """Write machine-readable JSON, flat CSV and a copyright-safe summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "parser_preservation_audit.json"
    csv_path = output_dir / "parser_preservation_audit.csv"
    summary_path = output_dir / "parser_preservation_summary.md"
    json_path.write_text(audit.model_dump_json(indent=2) + "\n", encoding="utf-8")

    fields = [
        "case_id", "stock_code", "risk_code", "evidence_index", "page",
        "evidence_role", "requirement", "source_authority", "structure_type",
        "page_present", "normalized_text_match", "core_text_preserved",
        "numeric_expected_count", "numeric_found_count", "numeric_preservation_rate",
        "structure_recoverability", "final_status", "failure_codes",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in audit.records:
            writer.writerow({
                "case_id": audit.case_id,
                "stock_code": audit.stock_code,
                "risk_code": record.risk_code,
                "evidence_index": record.evidence_index,
                "page": record.page,
                "evidence_role": record.evidence_role,
                "requirement": record.requirement,
                "source_authority": record.source_authority,
                "structure_type": record.structure_type.value,
                "page_present": record.parser_page_present,
                "normalized_text_match": record.normalized_text_match.value,
                "core_text_preserved": record.core_text_preserved,
                "numeric_expected_count": len(record.numeric_values_expected),
                "numeric_found_count": len(record.numeric_values_found),
                "numeric_preservation_rate": record.numeric_preservation_rate,
                "structure_recoverability": record.structure_recoverability.value,
                "final_status": record.final_status.value,
                "failure_codes": "|".join(code.value for code in record.failure_codes),
            })

    summary = audit.summary
    non_pass = [record for record in audit.records if record.final_status is not EvidenceAuditStatus.PASS]
    lines = [
        f"# Parser Preservation Audit — {audit.case_id}",
        "",
        "This audit measures the existing `page.get_text(\"text\")` output. It does not claim table-aware parsing.",
        "",
        f"- Annotation: `{audit.annotation_version}`",
        f"- PDF pages: `{audit.pdf_page_count}`",
        f"- Parser chunks: `{audit.parser_chunk_count}`",
        f"- Total Evidence: `{summary.total_evidence}`",
        f"- Required Evidence: `{summary.required_evidence}`",
        f"- Page preservation: `{summary.page_preservation_rate:.2%}`",
        f"- Normalized exact-text match: `{summary.normalized_exact_text_match_rate:.2%}`",
        f"- Core-text preservation: `{summary.core_text_preservation_rate:.2%}`",
        f"- Numeric preservation: `{summary.numeric_preservation_rate:.2%}`",
        f"- Required PASS: `{summary.required_evidence_preservation_rate:.2%}`",
        f"- Required PASS-or-PARTIAL: `{summary.required_pass_or_partial_rate:.2%}`",
        f"- Table fully recoverable: `{summary.table_fully_recoverable_rate:.2%}`",
        f"- Table at least partially recoverable: `{summary.table_at_least_partial_recoverable_rate:.2%}`",
        f"- PASS / PARTIAL / FAIL: `{summary.pass_count} / {summary.partial_count} / {summary.fail_count}`",
        f"- Diagnostic: `{summary.diagnostic_status}`",
        f"- Parser decision: `{audit.parser_decision}`",
        "",
        "## PARTIAL / FAIL",
        "",
    ]
    if not non_pass:
        lines.append("None.")
    else:
        for record in non_pass:
            codes = ", ".join(code.value for code in record.failure_codes)
            lines.append(f"- `{record.risk_code}` page `{record.page}`: `{record.final_status.value}` — {codes}")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, csv_path, summary_path
