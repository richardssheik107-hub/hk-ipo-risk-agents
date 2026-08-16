"""Tolerant, evaluation-only reader for expert retrieval annotations."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class GoldEvidence:
    case_id: str
    stock_code: str
    risk_code: str
    page: int
    evidence_role: str
    requirement: str
    source_authority: str
    exact_text: str
    confidence: float | None
    section: str | None
    evidence_id: str
    annotation_file: str


@dataclass(frozen=True)
class AnnotationCase:
    case_id: str
    stock_code: str
    risk_codes: tuple[str, ...]
    evidence: tuple[GoldEvidence, ...]
    annotation_file: str


def discover_annotation_files(root: Path) -> list[Path]:
    """Find annotations regardless of the intermediate pass directory."""
    return sorted(path for path in root.rglob("expert_annotation_v1.json") if path.is_file())


def _items(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for key in ("evidence", "evidences", "gold_evidence"):
        value = payload.get(key)
        if isinstance(value, list):
            yield from (item for item in value if isinstance(item, dict))
            return
    for risk in payload.get("risks", []):
        if not isinstance(risk, dict):
            continue
        for item in risk.get("evidence", []):
            if isinstance(item, dict):
                yield {"risk_code": risk.get("risk_code"), **item}


def _text(value: Any, default: str = "unknown") -> str:
    return str(value).strip() if value not in (None, "") else default


def load_annotation(path: Path, *, repository_root: Path | None = None) -> AnnotationCase:
    """Load known schema variants while safely defaulting optional fields."""
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    case_id = _text(payload.get("case_id"), path.parent.parent.name)
    stock_code = _text(payload.get("stock_code"))
    risks = payload.get("risks", [])
    risk_codes = tuple(dict.fromkeys(
        _text(item.get("risk_code")) for item in risks
        if isinstance(item, dict) and item.get("risk_code")
    ))
    base = (repository_root or path.parent).resolve()
    annotation_file = str(path.resolve().relative_to(base))
    evidence: list[GoldEvidence] = []
    for index, item in enumerate(_items(payload)):
        raw_page = item.get("page", item.get("physical_page", item.get("pdf_page")))
        try:
            page = int(raw_page)
        except (TypeError, ValueError):
            continue
        if page < 1:
            continue
        risk_code = _text(item.get("risk_code"))
        evidence_id = _text(item.get("evidence_id"), f"{case_id}:{risk_code}:{index}")
        evidence.append(GoldEvidence(
            case_id=case_id,
            stock_code=stock_code,
            risk_code=risk_code,
            page=page,
            evidence_role=_text(item.get("evidence_role"), "unspecified"),
            requirement=_text(item.get("requirement"), "required"),
            source_authority=_text(item.get("source_authority")),
            exact_text=_text(item.get("exact_text"), ""),
            confidence=float(item["confidence"]) if isinstance(item.get("confidence"), (int, float)) else None,
            section=_text(item.get("section"), "") or None,
            evidence_id=evidence_id,
            annotation_file=annotation_file,
        ))
    if not risk_codes:
        risk_codes = tuple(dict.fromkeys(item.risk_code for item in evidence))
    return AnnotationCase(case_id, stock_code, risk_codes, tuple(evidence), annotation_file)


def required_gold_pages(case: AnnotationCase, risk_code: str) -> set[int]:
    """Return unique physical pages for required evidence of one risk."""
    return {item.page for item in case.evidence if item.risk_code == risk_code and item.requirement == "required"}
