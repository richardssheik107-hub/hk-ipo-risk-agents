"""Retriever V3 evaluation dataset built from audited Expert Annotation evidence.

This module is evaluation-only. It never edits pass1 annotations and never changes
production Retriever behavior. Financial audit overlays affect only the risk-state
metadata attached to retrieval Gold rows; Evidence page/text records remain the
immutable pass1 Evidence supplied by the expert annotation bundle.
"""

from __future__ import annotations

from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES
from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle


DEFAULT_SPLIT_PATH = Path("configs/retriever_v3_split_manifest.json")
DEFAULT_EXPERT_ROOT = Path("expert_results")
DEFAULT_SOURCE_MANIFEST = Path("docs/annotation/gpt_expert_v1_1/source_manifest.csv")


class RetrieverV3SplitManifest(BaseModel):
    """Frozen 60-case development/locked-validation split."""

    model_config = ConfigDict(extra="forbid")

    split_version: str
    source_taskset_version: str
    source_case_scope: str
    source_case_count: int = Field(gt=0)
    development_case_count: int = Field(gt=0)
    locked_validation_case_count: int = Field(gt=0)
    selection_namespace: str
    selection_policy: dict[str, Any]
    known_retrieval_exposed_cases: list[str]
    manual_annotation_review_exclusions: list[str]
    development_cases: list[str]
    locked_validation_cases: list[str]
    integrity: dict[str, str]

    @model_validator(mode="after")
    def validate_split(self) -> "RetrieverV3SplitManifest":
        development = set(self.development_cases)
        locked = set(self.locked_validation_cases)
        all_cases = development | locked
        if development & locked:
            raise ValueError("development and locked validation cases must be disjoint")
        if len(self.development_cases) != len(development):
            raise ValueError("development cases must be unique")
        if len(self.locked_validation_cases) != len(locked):
            raise ValueError("locked validation cases must be unique")
        if len(all_cases) != self.source_case_count:
            raise ValueError("split case count does not match source_case_count")
        if len(development) != self.development_case_count:
            raise ValueError("development case count mismatch")
        if len(locked) != self.locked_validation_case_count:
            raise ValueError("locked validation case count mismatch")
        if set(self.known_retrieval_exposed_cases) - development:
            raise ValueError("previous retrieval cases must remain in development")
        if set(self.manual_annotation_review_exclusions) & locked:
            raise ValueError("manually inspected annotation cases cannot be locked validation")
        expected = {
            "development_cases_sorted_sha256": _digest_lines(self.development_cases, sort=True),
            "locked_validation_cases_sorted_sha256": _digest_lines(self.locked_validation_cases, sort=True),
        }
        for key, value in expected.items():
            if self.integrity.get(key) != value:
                raise ValueError(f"split integrity mismatch: {key}")
        return self

    @property
    def all_cases(self) -> set[str]:
        return set(self.development_cases) | set(self.locked_validation_cases)

    def split_for(self, case_id: str) -> str:
        if case_id in self.development_cases:
            return "development"
        if case_id in self.locked_validation_cases:
            return "locked_validation"
        raise KeyError(case_id)


class RetrievalGoldRow(BaseModel):
    """One expert Evidence record normalized for retrieval evaluation."""

    model_config = ConfigDict(extra="forbid")

    row_id: str
    case_id: str
    stock_code: str
    company_name: str
    document_id: str
    source_year: int
    retrieval_split: str
    risk_code: str
    evidence_index: int = Field(ge=0)
    page: int = Field(ge=1)
    exact_text: str
    evidence_role: str
    requirement: str
    source_authority: str
    confidence: float
    gold_grade: int = Field(ge=1, le=3)
    risk_applicable: bool
    risk_expected_status: str
    risk_expected_level: str | None
    risk_state_source: str
    risk_review_state: bool
    authoritative_source: bool


class SourceManifestRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    case_id: str
    stock_code: str
    company_name: str
    source_year: int
    page_count: int
    pdf_sha256: str


def _digest_lines(values: Iterable[str], *, sort: bool) -> str:
    rows = list(values)
    if sort:
        rows.sort()
    return sha256("\n".join(rows).encode("utf-8")).hexdigest()


def load_split_manifest(path: Path = DEFAULT_SPLIT_PATH) -> RetrieverV3SplitManifest:
    return RetrieverV3SplitManifest.model_validate_json(path.read_text(encoding="utf-8"))


def load_source_manifest(path: Path = DEFAULT_SOURCE_MANIFEST) -> dict[str, SourceManifestRecord]:
    records: dict[str, SourceManifestRecord] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            case_id = row.get("case_id", "")
            if not case_id:
                continue
            records[case_id] = SourceManifestRecord(
                case_id=case_id,
                stock_code=row["stock_code"],
                company_name=row["company_name"],
                source_year=int(row["source_year"]),
                page_count=int(row["page_count"]),
                pdf_sha256=row["pdf_sha256"].lower(),
            )
    return records


def _gold_grade(requirement: str, role: str) -> int:
    if requirement == "required" and role == "primary":
        return 3
    if requirement == "required":
        return 2
    return 1


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _risk_states(case_dir: Path, bundle: ExpertAnnotationBundle) -> dict[str, dict[str, Any]]:
    """Apply audit overlays to risk-state metadata without touching Evidence."""
    states = {
        risk.risk_code: {
            "applicable": risk.applicable,
            "expected_status": risk.expected_status.value,
            "expected_level": risk.expected_level.value if risk.expected_level is not None else None,
            "source": "pass1",
        }
        for risk in bundle.risks
    }

    corrections = case_dir / "audit" / "deterministic_corrections_v1.json"
    if corrections.exists():
        payload = _load_json(corrections)
        for item in payload.get("corrections", []):
            replacement = item.get("replacement") or {}
            risk_code = item.get("risk_code")
            if risk_code in states and replacement:
                states[risk_code] = {
                    "applicable": bool(replacement["applicable"]),
                    "expected_status": str(replacement["expected_status"]),
                    "expected_level": replacement.get("expected_level"),
                    "source": "deterministic_corrections_v1",
                }

    resolution = case_dir / "audit" / "financial_resolution_v1.json"
    if resolution.exists():
        payload = _load_json(resolution)
        for item in payload.get("entries", []):
            if item.get("closure_status") != "CLOSED":
                raise ValueError(f"unclosed Phase-2c resolution: {case_dir.name}/{item.get('risk_code')}")
            resolved = item.get("resolved_state") or {}
            risk_code = item.get("risk_code")
            if risk_code in states and resolved:
                states[risk_code] = {
                    "applicable": bool(resolved["applicable"]),
                    "expected_status": str(resolved["expected_status"]),
                    "expected_level": resolved.get("expected_level"),
                    "source": "financial_resolution_v1",
                }
    return states


def build_retrieval_gold_rows(
    *,
    expert_root: Path = DEFAULT_EXPERT_ROOT,
    split_manifest: RetrieverV3SplitManifest,
) -> list[RetrievalGoldRow]:
    """Build the 60-case Evidence dataset from immutable pass1 + audit state overlays."""
    rows: list[RetrievalGoldRow] = []
    missing: list[str] = []
    for case_id in sorted(split_manifest.all_cases):
        path = expert_root / case_id / "pass1" / "expert_annotation_v1.json"
        if not path.exists():
            missing.append(case_id)
            continue
        bundle = ExpertAnnotationBundle.model_validate(_load_json(path))
        if bundle.case_id != case_id:
            raise ValueError(f"case identity mismatch: {case_id} != {bundle.case_id}")
        case_dir = expert_root / case_id
        states = _risk_states(case_dir, bundle)
        year_match = re.match(r"^ipo_(\d{4})_", case_id)
        if year_match is None:
            raise ValueError(f"invalid case id year: {case_id}")
        source_year = int(year_match.group(1))
        split = split_manifest.split_for(case_id)
        for evidence_index, evidence in enumerate(bundle.evidence):
            state = states[evidence.risk_code]
            stable = (
                f"{case_id}|{evidence.risk_code}|{evidence_index}|{evidence.page}|"
                f"{evidence.evidence_role.value}|{evidence.requirement.value}|{evidence.exact_text}"
            )
            rows.append(RetrievalGoldRow(
                row_id=sha256(stable.encode("utf-8")).hexdigest()[:24],
                case_id=case_id,
                stock_code=bundle.stock_code,
                company_name=bundle.company_name,
                document_id=bundle.document_id,
                source_year=source_year,
                retrieval_split=split,
                risk_code=evidence.risk_code,
                evidence_index=evidence_index,
                page=evidence.page,
                exact_text=evidence.exact_text,
                evidence_role=evidence.evidence_role.value,
                requirement=evidence.requirement.value,
                source_authority=evidence.source_authority.value,
                confidence=evidence.confidence,
                gold_grade=_gold_grade(evidence.requirement.value, evidence.evidence_role.value),
                risk_applicable=bool(state["applicable"]),
                risk_expected_status=str(state["expected_status"]),
                risk_expected_level=state.get("expected_level"),
                risk_state_source=str(state["source"]),
                risk_review_state=state["expected_status"] == "needs_review",
                authoritative_source=evidence.source_authority.value not in {"summary", "risk_factors", "other"},
            ))
    if missing:
        raise FileNotFoundError(f"missing pass1 annotation cases: {missing}")
    if len({row.case_id for row in rows}) != split_manifest.source_case_count:
        raise ValueError("not all split cases produced Evidence rows")
    if len({row.row_id for row in rows}) != len(rows):
        raise ValueError("retrieval Gold row_id collision")
    return rows


def validate_gold_against_source_manifest(
    rows: list[RetrievalGoldRow],
    *,
    split_manifest: RetrieverV3SplitManifest,
    source_manifest: dict[str, SourceManifestRecord],
) -> dict[str, Any]:
    """Validate case identities and Evidence page ranges using catalog metadata only."""
    errors: list[str] = []
    for case_id in sorted(split_manifest.all_cases):
        if case_id not in source_manifest:
            errors.append(f"source_manifest_missing:{case_id}")
    for row in rows:
        source = source_manifest.get(row.case_id)
        if source is None:
            continue
        if row.page > source.page_count:
            errors.append(f"page_out_of_range:{row.case_id}:{row.risk_code}:{row.page}>{source.page_count}")
        if row.stock_code != source.stock_code:
            errors.append(f"stock_code_mismatch:{row.case_id}")
    source_order = [case_id for case_id in source_manifest if case_id in split_manifest.all_cases]
    taskset_hash = _digest_lines(source_order, sort=False)
    expected_taskset_hash = split_manifest.integrity.get("all_cases_sha256")
    if taskset_hash != expected_taskset_hash:
        errors.append("taskset_order_hash_mismatch")
    return {
        "valid": not errors,
        "errors": errors,
        "case_count": len({row.case_id for row in rows}),
        "evidence_count": len(rows),
        "required_evidence_count": sum(row.requirement == "required" for row in rows),
        "primary_evidence_count": sum(row.evidence_role == "primary" for row in rows),
        "review_state_evidence_count": sum(row.risk_review_state for row in rows),
        "taskset_order_sha256": taskset_hash,
    }


def evidence_pattern_summary(rows: list[RetrievalGoldRow]) -> dict[str, Any]:
    """Mine Gold-only evidence patterns; never changes retrieval queries or ranks."""
    def signals(text: str) -> dict[str, int | bool]:
        numeric_tokens = re.findall(r"(?:\d[\d,]*(?:\.\d+)?)", text)
        year_tokens = re.findall(r"(?:19|20)\d{2}", text)
        return {
            "contains_percent": "%" in text or "％" in text,
            "contains_currency": bool(re.search(r"\b(?:RMB|HKD|HK\$|USD)\b|人民幣|人民币|港元|美元", text, re.I)),
            "numeric_token_count": len(numeric_tokens),
            "year_token_count": len(year_tokens),
            "table_like": len(numeric_tokens) >= 4 or text.count("%") + text.count("％") >= 2,
        }

    by_risk: dict[str, Any] = {}
    for risk_code in sorted(V03_ENABLED_RISK_CODES):
        selected = [row for row in rows if row.risk_code == risk_code]
        signal_rows = [signals(row.exact_text) for row in selected]
        by_risk[risk_code] = {
            "evidence_count": len(selected),
            "required_count": sum(row.requirement == "required" for row in selected),
            "primary_count": sum(row.evidence_role == "primary" for row in selected),
            "source_authority": dict(sorted(Counter(row.source_authority for row in selected).items())),
            "evidence_role": dict(sorted(Counter(row.evidence_role for row in selected).items())),
            "requirement": dict(sorted(Counter(row.requirement for row in selected).items())),
            "contains_percent_rate": _mean_bool(item["contains_percent"] for item in signal_rows),
            "contains_currency_rate": _mean_bool(item["contains_currency"] for item in signal_rows),
            "table_like_rate": _mean_bool(item["table_like"] for item in signal_rows),
            "mean_numeric_token_count": _mean_number(item["numeric_token_count"] for item in signal_rows),
            "mean_year_token_count": _mean_number(item["year_token_count"] for item in signal_rows),
            "mean_exact_text_chars": sum(len(row.exact_text) for row in selected) / len(selected) if selected else 0.0,
        }
    return {
        "case_count": len({row.case_id for row in rows}),
        "evidence_count": len(rows),
        "required_evidence_count": sum(row.requirement == "required" for row in rows),
        "by_risk": by_risk,
    }


def _mean_bool(values: Iterable[bool]) -> float:
    rows = list(values)
    return sum(bool(value) for value in rows) / len(rows) if rows else 0.0


def _mean_number(values: Iterable[int | float]) -> float:
    rows = list(values)
    return sum(float(value) for value in rows) / len(rows) if rows else 0.0


def write_preflight_outputs(
    *,
    rows: list[RetrievalGoldRow],
    split_manifest: RetrieverV3SplitManifest,
    validation: dict[str, Any],
    output_dir: Path,
) -> list[Path]:
    """Persist development Gold + redacted locked manifest for reproducible preflight."""
    output_dir.mkdir(parents=True, exist_ok=True)
    development = [row for row in rows if row.retrieval_split == "development"]
    locked = [row for row in rows if row.retrieval_split == "locked_validation"]

    manifest_path = output_dir / "gold_dataset_manifest.json"
    manifest_payload = {
        "dataset_version": "retriever_v3_gold_v1",
        "split_version": split_manifest.split_version,
        "validation": validation,
        "development": evidence_pattern_summary(development),
        "locked_validation": {
            "case_count": len({row.case_id for row in locked}),
            "case_ids": list(split_manifest.locked_validation_cases),
            "evidence_details_exported": False,
            "metrics_unlocked": False,
        },
        "gold_source": "pass1 Evidence + audit overlay risk-state metadata",
        "pass1_modified": False,
    }
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_path = output_dir / "development_gold_evidence.csv"
    fieldnames = list(RetrievalGoldRow.model_fields)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in development:
            writer.writerow(row.model_dump(mode="json"))

    pattern_path = output_dir / "development_evidence_patterns.json"
    pattern_path.write_text(json.dumps(evidence_pattern_summary(development), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    locked_path = output_dir / "locked_validation_manifest.json"
    locked_path.write_text(json.dumps({
        "split_version": split_manifest.split_version,
        "case_ids": split_manifest.locked_validation_cases,
        "case_count": split_manifest.locked_validation_case_count,
        "gold_evidence_exported": False,
        "default_evaluator_access": "denied_until_explicit_unlock",
        "strict_blind_claim": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [manifest_path, csv_path, pattern_path, locked_path]
