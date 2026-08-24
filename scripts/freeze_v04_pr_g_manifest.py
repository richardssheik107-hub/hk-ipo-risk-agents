"""Validate a real PR-G draft and write the deterministic A-approved freeze manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ipo_risk.schemas.canonical_modeling import canonical_hash

OUTPUT_NAME = "v04_pr_g_final_supervision_manifest.json"
PR_F_MANIFEST_NAME = "v04_pr_f_lightgbm_manifest.json"
EXPECTED_DRAFT_VERSION = "v04_pr_g_freeze_manifest_v1"
EXPECTED_PR_G_VERSION = "v04_pr_g_final_supervision_v1"
EXPECTED_SCORE_SEMANTICS = "uncalibrated_model_score"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


class PRGFreezeError(ValueError):
    """The PR-G draft cannot be frozen under the approved governance contract."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PRGFreezeError(f"invalid JSON: {path.name}") from exc
    if not isinstance(payload, dict):
        raise PRGFreezeError(f"expected JSON object: {path.name}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PRGFreezeError(message)


def _official_row(bridge: Path, stock_code: str) -> dict[str, str]:
    try:
        rows = list(csv.DictReader(bridge.open(encoding="utf-8-sig", newline="")))
    except OSError as exc:
        raise PRGFreezeError("official catalog bridge is unavailable") from exc
    matches = [row for row in rows if row.get("stock_code_wind") == stock_code]
    _require(len(matches) == 1, "stock code must resolve to exactly one official catalog row")
    _require(matches[0].get("official_match_status") == "matched", "official case is not matched")
    return matches[0]


def freeze(
    *,
    draft_path: Path,
    prospectus_path: Path,
    official_bridge_path: Path,
    frozen_dir: Path,
    source_revision: str,
    a_review_path: Path,
) -> dict[str, Any]:
    """Validate all PR-G gate invariants and return deterministic frozen content."""
    draft = _read_json(draft_path)
    _require(REVISION_RE.fullmatch(source_revision) is not None, "source revision must be a full Git SHA")
    _require(a_review_path.is_file(), "A gate review is missing")
    review_text = a_review_path.read_text(encoding="utf-8")
    _require("GATE REVIEW PASS" in review_text, "A gate review does not record PASS")

    _require(draft.get("manifest_version") == EXPECTED_DRAFT_VERSION, "draft manifest version mismatch")
    _require(draft.get("pr_g_version") == EXPECTED_PR_G_VERSION, "PR-G version mismatch")
    _require(draft.get("status") == "implementation_complete_awaiting_gate_review", "draft status is not freezeable")
    _require(draft.get("formal_gate_passed") is False, "draft must not pre-approve its own gate")
    _require(draft.get("blind_2025_y_accessed") is False, "draft reports 2025 Blind access")
    _require(draft.get("creates_no_new_risk") is True, "Final Supervisor creates a new risk")
    _require(draft.get("probability_claimed") is False, "uncalibrated model score was called a probability")

    identity = draft.get("case_identity") or {}
    for key in ("company_name", "stock_code", "listing_date"):
        _require(isinstance(identity.get(key), str) and bool(identity[key]), f"case identity {key} is missing")
    official = _official_row(official_bridge_path, identity["stock_code"])
    _require(identity["listing_date"] == official.get("official_listed_date"), "listing date differs from official catalog")
    _require(identity["company_name"] == official.get("selected_name"), "company name differs from official catalog")

    _require(prospectus_path.is_file(), "real prospectus is unavailable")
    closed_loop = draft.get("closed_loop") or {}
    actual_pdf_hash = _sha256(prospectus_path)
    _require(SHA256_RE.fullmatch(str(closed_loop.get("prospectus_sha256"))) is not None, "prospectus hash is invalid")
    _require(closed_loop["prospectus_sha256"] == actual_pdf_hash, "prospectus bytes do not match the draft hash")
    _require(closed_loop.get("analysis_status") == "completed", "analysis is not completed")
    _require(closed_loop.get("report_section_count") == 13, "PR-G report must contain exactly 13 sections")
    _require(isinstance(closed_loop.get("verified_risk_count"), int), "verified risk count is invalid")

    traceability = draft.get("traceability") or {}
    _require(traceability.get("all_references_resolve") is True, "Evidence traceability failed")
    _require(traceability.get("referenced_evidence_count", 0) > 0, "real run contains no referenced Evidence")
    _require(traceability.get("referenced_evidence_count") <= traceability.get("indexed_evidence_count", -1),
             "referenced Evidence exceeds indexed Evidence")
    _require(SHA256_RE.fullmatch(str(draft.get("final_supervision_content_hash"))) is not None,
             "final-supervision content hash is invalid")

    pr_f = _read_json(frozen_dir / PR_F_MANIFEST_NAME)
    model = draft.get("model_channel") or {}
    _require(pr_f.get("status") == "complete_frozen" and pr_f.get("formal_gate_passed") is True,
             "PR-F is not complete and frozen")
    _require(pr_f.get("blind_2025_y_accessed") is False, "frozen PR-F reports 2025 Blind access")
    _require(model.get("frozen_pr_f_manifest") == PR_F_MANIFEST_NAME, "draft names the wrong PR-F manifest")
    _require(model.get("frozen_pr_f_manifest_hash") == pr_f.get("freeze_manifest_hash"),
             "draft PR-F identity differs from the frozen manifest")
    _require(model.get("score_semantics") == EXPECTED_SCORE_SEMANTICS, "model score semantics mismatch")

    payload = {
        "manifest_version": EXPECTED_DRAFT_VERSION,
        "pr_g_version": EXPECTED_PR_G_VERSION,
        "status": "complete_frozen",
        "formal_gate_passed": True,
        "source_revision": source_revision,
        "source_draft_sha256": _sha256(draft_path),
        "a_gate_review": str(a_review_path.as_posix()),
        "case_identity": identity,
        "closed_loop": closed_loop,
        "channel_states": draft.get("channel_states", []),
        "market_channel": draft.get("market_channel", {}),
        "model_channel": model,
        "traceability": traceability,
        "creates_no_new_risk": True,
        "probability_claimed": False,
        "blind_2025_y_accessed": False,
        "final_supervision_content_hash": draft["final_supervision_content_hash"],
    }
    payload["freeze_manifest_hash"] = canonical_hash(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--prospectus", type=Path, required=True)
    parser.add_argument("--official-bridge", type=Path, default=Path("data/catalog/ipo_official_master_bridge.csv"))
    parser.add_argument("--frozen-dir", type=Path, default=Path("reports/frozen"))
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--a-review", type=Path, default=Path("docs/V04_PR_G_A_GATE_REVIEW.md"))
    args = parser.parse_args()
    payload = freeze(
        draft_path=args.draft,
        prospectus_path=args.prospectus,
        official_bridge_path=args.official_bridge,
        frozen_dir=args.frozen_dir,
        source_revision=args.source_revision,
        a_review_path=args.a_review,
    )
    args.frozen_dir.mkdir(parents=True, exist_ok=True)
    target = args.frozen_dir / OUTPUT_NAME
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "freeze_manifest_hash": payload["freeze_manifest_hash"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
