"""Run the E-lane competition chain over the declared demo cases.

For each declared case this resolves the prospectus through the frozen catalog,
verifies its bytes, then executes the full governed chain -- parse, agents,
verifier, Document Supervisor, governed market context, rule signal, conflict
detection, one bounded targeted re-check per conflict, LLM Final Supervisor
synthesis and trace assembly -- and writes the per-case artifacts the submission
package needs: the analysis result, the conflict / re-check / trace sidecars, an
agent reasoning log, a case report, the Evidence and Human Review exports and
the Gate E1 acceptance evidence.

The Gate E1 evidence is produced by the run itself rather than read off the
artifacts afterwards.  It records whether a real remote provider actually
arbitrated, whether its call trace was retained and whether the out-of-scope
guard passed on a real response; an honest deterministic fallback leaves the
Gate unmet and says so, which is the only reading of it that can be trusted.

Prospectus resolution is deliberately indirect.  The licensed PDFs live outside
the repository, so the case list carries only a ``case_id``; the filename, the
expected SHA-256, the byte size and the page count all come from the frozen
``ipo_prospectus_manifest.csv``.  The archive root is supplied at run time by
``--prospectus-root`` or ``IPO_RISK_PROSPECTUS_ROOT``, so no local absolute path
is ever committed.

Integrity fails closed: a prospectus whose bytes do not match the frozen
SHA-256 and size is never analysed.  A declared case whose PDF is absent is
reported ``unavailable_prospectus``.  Nothing is substituted or silently dropped.

Only pre-listing inputs are read.  No outcome label of any year is opened.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
from dataclasses import replace
from datetime import date
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.core.config import load_settings
from ipo_risk.runtime.submission_exports import (
    build_evidence_export,
    build_human_review_export,
    render_evidence_export_csv,
)
from ipo_risk.runtime.submission_artifacts import (
    CaseRunArtifacts,
    build_agent_reasoning_log,
    build_gate_e1_evidence,
    render_agent_reasoning_log,
    render_case_report,
    summarise_gate_e1,
)
from ipo_risk.schemas import IPOAnalysisRequest, IPOAnalysisResult
from ipo_risk.services.analysis_service import IPOAnalysisService
from ipo_risk.services.human_review_service import HumanReviewService

DEMO_VERSION = "v045_role_e_demo_v2"
DEFAULT_CASES = Path("configs/v045_demo_cases.json")
DEFAULT_CONFIG = "configs/v045_competition_offline.yaml"
DEFAULT_OUTPUT = Path("reports/v045_role_e")
DEFAULT_CATALOG = Path("data/catalog/ipo_prospectus_manifest.csv")
DEFAULT_BRIDGE = Path("data/catalog/ipo_official_master_bridge.csv")
PROSPECTUS_ROOT_ENV = "IPO_RISK_PROSPECTUS_ROOT"


class ProspectusIntegrityError(RuntimeError):
    """The located prospectus does not match its frozen catalog record."""


def _sha(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str | None:
    """SHA-256 over the file's bytes, or ``None`` when it cannot be read.

    ``None`` is deliberate: an input we could not hash is reported as absent so
    the provenance audit stays blocked, rather than being given a placeholder
    that would let the matrix claim an identity it cannot prove.
    """

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def resolve_code_base_sha(repo_root: Path) -> tuple[str | None, bool | None]:
    """The git commit this matrix ran from, and whether its tree was dirty.

    Returns ``(None, None)`` when git cannot answer -- outside a checkout, or
    with no git binary.  The identity is then absent rather than guessed, which
    leaves the readiness provenance/determinism audits blocked instead of
    asserting a code provenance we have no evidence for.

    A dirty tree still reports its ``HEAD`` sha, paired with ``dirty=True``.
    The commit alone would misdescribe what actually ran, so the two are always
    written together and never collapsed into a single clean-looking field.
    """

    def _git(*args: str) -> str | None:
        try:
            completed = subprocess.run(
                ("git", *args),
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout.strip()

    head = _git("rev-parse", "HEAD")
    if not head:
        return None, None
    status = _git("status", "--porcelain")
    if status is None:
        return head, None
    return head, bool(status.strip())


def _read_catalog(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row[key]: row for row in csv.DictReader(handle)}


def deterministic_request_id(stock_code: str, listing_date: date, prospectus_sha256: str) -> str:
    """Same identity convention the PR-G/PR-H freeze runs use."""

    return str(
        uuid5(NAMESPACE_URL, f"v04-real-e2e:{stock_code}:{listing_date.isoformat()}:{prospectus_sha256}")
    )


def resolve_prospectus(
    catalog_row: dict[str, str], root: Path | None, override: str | None
) -> tuple[Path, dict[str, object]]:
    """Locate the prospectus and prove it is the frozen one, or refuse it."""

    if override:
        path = Path(override)
    elif root is not None:
        path = root / catalog_row["relative_path"]
    else:
        raise FileNotFoundError(
            f"no prospectus root supplied; pass --prospectus-root or set {PROSPECTUS_ROOT_ENV}"
        )
    if not path.exists():
        raise FileNotFoundError(f"declared prospectus is not present locally: {path}")

    content = path.read_bytes()
    actual_sha = hashlib.sha256(content).hexdigest()
    expected_sha = catalog_row["sha256"]
    expected_size = int(catalog_row["file_size_bytes"])
    if actual_sha != expected_sha or len(content) != expected_size:
        raise ProspectusIntegrityError(
            f"{path} does not match the frozen catalog record "
            f"(sha256 {actual_sha[:12]}… vs {expected_sha[:12]}…, "
            f"{len(content)} vs {expected_size} bytes)"
        )
    expected_pages = int(catalog_row["pdf_page_count"])
    actual_pages = _page_count(content)
    if actual_pages != expected_pages:
        raise ProspectusIntegrityError(
            f"{path} has {actual_pages} physical pages, the frozen catalog records {expected_pages}"
        )
    verification = {
        "source_filename": catalog_row["source_filename"],
        "sha256": actual_sha,
        "sha256_matches_frozen_catalog": True,
        "file_size_bytes": len(content),
        "size_matches_frozen_catalog": True,
        "pdf_page_count": actual_pages,
        "page_count_matches_frozen_catalog": True,
        "dataset_split": catalog_row["dataset_split"],
        # The path is deliberately not recorded: it is a local, licensed location.
        "path_recorded": False,
    }
    return path, verification


def _page_count(content: bytes) -> int:
    """Physical page count, so a same-size different document cannot pass."""

    import pymupdf

    with pymupdf.open(stream=content, filetype="pdf") as document:
        return document.page_count


def run_case(
    case: dict,
    config: str,
    output_dir: Path,
    catalog: dict[str, dict[str, str]],
    bridge: dict[str, dict[str, str]],
    root: Path | None,
) -> dict:
    case_id = case["case_id"]
    catalog_row = catalog.get(case_id)
    bridge_row = bridge.get(case_id)
    if catalog_row is None or bridge_row is None:
        return {
            "case_id": case_id,
            "status": "unknown_case",
            "reason": "case_id is not present in the frozen prospectus catalog or official bridge",
        }
    stock_code = bridge_row["stock_code_wind"]
    listing_date = date.fromisoformat(bridge_row["official_listed_date"])
    try:
        prospectus, verification = resolve_prospectus(catalog_row, root, case.get("prospectus_path"))
    except ProspectusIntegrityError as exc:
        return {"case_id": case_id, "stock_code": stock_code, "status": "integrity_failed", "reason": str(exc)}
    except FileNotFoundError as exc:
        return {
            "case_id": case_id,
            "stock_code": stock_code,
            "status": "unavailable_prospectus",
            "reason": str(exc),
        }

    request_id = deterministic_request_id(stock_code, listing_date, verification["sha256"])
    settings = load_settings(config)
    result = IPOAnalysisService(settings=settings).analyze(
        IPOAnalysisRequest(
            request_id=request_id,
            company_name=case["company_name"],
            stock_code=stock_code,
            listing_date=listing_date,
            prospectus_path=str(prospectus),
            use_mock=False,
        )
    )
    return _write_artifacts(
        case_id, case, stock_code, listing_date, result, config, verification, request_id, output_dir
    )


def _write_artifacts(
    case_id: str,
    case: dict,
    stock_code: str,
    listing_date: date,
    result: IPOAnalysisResult,
    config: str,
    verification: dict[str, object],
    request_id: str,
    output_dir: Path,
) -> dict:
    diagnostics = result.metadata.get("component_diagnostics", {})
    runtime = diagnostics.get("competition_runtime", {})
    final = result.metadata.get("final_supervision", {})
    supervision_llm = diagnostics.get("final_supervision_llm", {})
    conflicts = diagnostics.get("conflict_detection", {})
    rechecks = diagnostics.get("targeted_recheck", {})

    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    run_artifacts = CaseRunArtifacts(
        case_id=case_id,
        company_name=case["company_name"],
        stock_code=stock_code,
        listing_date=listing_date.isoformat(),
        config=config,
        result=json.loads(result.model_dump_json()),
        sidecar=runtime.get("sidecar") or {},
        composition=final,
        supervision_llm=supervision_llm,
        conflicts=conflicts,
        rechecks=rechecks,
        traceability=runtime.get("traceability") or {},
        verification=verification,
    )
    reasoning_log = build_agent_reasoning_log(run_artifacts)
    gate_e1 = build_gate_e1_evidence(run_artifacts)
    evidence_export = build_evidence_export(
        case_id=case_id, stock_code=stock_code, result=run_artifacts.result
    )
    # Reviewer decisions live in their own sidecar store and are read, never
    # merged: a case nobody reviewed is exported as unreviewed.
    human_review_export = build_human_review_export(
        case_id=case_id,
        analysis_id=result.analysis_id,
        reviews=HumanReviewService().history(result.analysis_id),
    )

    artifacts = {
        "analysis_result.json": run_artifacts.result,
        "final_supervision.json": {"composition": final, "llm_synthesis": supervision_llm},
        "conflicts.json": conflicts,
        "rechecks.json": rechecks,
        "trace_sidecar.json": runtime.get("sidecar"),
        "traceability.json": runtime.get("traceability"),
        "prospectus_verification.json": verification,
        "agent_reasoning_log.json": reasoning_log,
        "gate_e1_evidence.json": gate_e1,
        "evidence_export.json": evidence_export,
        "human_review_export.json": human_review_export,
    }
    for name, payload in artifacts.items():
        (case_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (case_dir / "evidence_export.csv").write_text(
        render_evidence_export_csv(evidence_export), encoding="utf-8"
    )
    (case_dir / "agent_reasoning_log.md").write_text(
        render_agent_reasoning_log(reasoning_log), encoding="utf-8"
    )
    (case_dir / "case_report.md").write_text(
        render_case_report(run_artifacts, reasoning_log, gate_e1), encoding="utf-8"
    )

    conflict_statuses: dict[str, int] = {}
    for conflict in conflicts.get("conflicts", []):
        conflict_statuses[conflict["status"]] = conflict_statuses.get(conflict["status"], 0) + 1
    return {
        "case_id": case_id,
        "stock_code": stock_code,
        "listing_date": listing_date.isoformat(),
        "status": result.status.value,
        "config": config,
        "prospectus_verification": verification,
        "deterministic_request_id": request_id,
        "analysis_id": result.analysis_id,
        "parsed_chunk_count": result.metadata.get("document", {}).get("parsed_chunk_count"),
        "verified_risk_count": len(result.verified_risks),
        "pending_risk_count": len(result.pending_risks),
        "rejected_risk_count": len(result.rejected_risks),
        "report_section_count": len(result.report_sections),
        "structured_error_count": len(result.errors),
        "channel_states": {
            item["channel"]: item["status"] for item in final.get("channel_states", [])
        },
        "conflict_count": conflicts.get("conflict_count", 0),
        "conflict_statuses": conflict_statuses,
        "recheck_attempted": rechecks.get("attempted", 0),
        "llm_synthesis_status": supervision_llm.get("status"),
        "llm_synthesis_outcome": supervision_llm.get("outcome"),
        "evidence_export_row_count": evidence_export["evidence_row_count"],
        "human_review_count": human_review_export["review_count"],
        "llm_synthesis_reason": supervision_llm.get("reason"),
        "gate_e1": gate_e1,
        "deterministic_severity_floor": supervision_llm.get("deterministic_severity_floor"),
        "traceability": runtime.get("traceability"),
        "final_supervision_content_hash": _sha(final),
        "probability_claimed": final.get("metadata", {}).get("probability_claimed"),
        "creates_no_new_risk": final.get("metadata", {}).get("creates_no_new_risk"),
        "artifact_dir": str(case_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument(
        "--prospectus-root",
        type=Path,
        default=None,
        help=f"local archive root; defaults to ${PROSPECTUS_ROOT_ENV}. Never committed.",
    )
    parser.add_argument("--case-id", action="append", default=None, help="run only these case ids")
    arguments = parser.parse_args()

    root = arguments.prospectus_root
    if root is None and os.getenv(PROSPECTUS_ROOT_ENV):
        root = Path(os.environ[PROSPECTUS_ROOT_ENV])

    manifest = json.loads(arguments.cases.read_text(encoding="utf-8"))
    catalog = _read_catalog(arguments.catalog, "case_id")
    bridge = _read_catalog(arguments.bridge, "case_id")
    cases = [
        case for case in manifest["cases"]
        if arguments.case_id is None or case["case_id"] in set(arguments.case_id)
    ]
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    results = [
        run_case(case, arguments.config, arguments.output_dir, catalog, bridge, root)
        for case in cases
    ]
    executed = [item for item in results if item.get("traceability") is not None]
    code_base_sha, code_base_dirty = resolve_code_base_sha(Path(__file__).resolve().parents[1])
    summary = {
        "demo_version": DEMO_VERSION,
        "config": arguments.config,
        "cases_manifest": str(arguments.cases),
        "cases_manifest_version": manifest.get("manifest_version"),
        # Matrix identity: which code, which case list and which config produced
        # this run.  The provenance and determinism audits refuse the matrix
        # without all three, and a dirty tree is reported rather than hidden.
        "code_base_sha": code_base_sha,
        "code_base_dirty": code_base_dirty,
        "cases_manifest_sha256": _file_sha256(arguments.cases),
        "config_sha256": _file_sha256(Path(arguments.config)),
        "prospectus_root_supplied": root is not None,
        "declared_case_count": len(cases),
        "executed_case_count": len(executed),
        "unexecuted_case_count": len(cases) - len(executed),
        "minimum_required_demo_cases": 3,
        "minimum_demo_cases_met": len(executed) >= 3,
        "all_prospectus_sha256_verified": all(
            item.get("prospectus_verification", {}).get("sha256_matches_frozen_catalog") is True
            for item in executed
        ),
        "outcome_labels_accessed": False,
        "blind_2025_y_accessed": False,
        "gate_e1": summarise_gate_e1(
            [item["gate_e1"] for item in executed if item.get("gate_e1")], len(cases)
        ),
        "cases": results,
    }
    (arguments.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    # A missing or mismatched local prospectus is a declared, reported state, not a
    # script failure; the summary is what records whether the demo bar was met.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
