"""Prepare blind, local-only external GPT annotation packets for three cases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import fitz

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES


TARGETS = ("2410.HK", "2517.HK", "1167.HK")
ALLOWED_SPLITS = {"development", "development_exception"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _protocol() -> str:
    return """# GPT Expert Blind Annotation Protocol v1.1

This is an independent blind review of the original prospectus. Human Golden,
Retriever output, Agent output, and prior evaluation results must not be shown.

## Frozen scope

Contract version: `v03_contract_v1`. Assess every enabled code for every case:

| Risk code | Domain | Frozen decision rule / threshold |
|---|---|---|
| `cash_runway` | Financial | Cash divided by absolute monthly operating cash burn. `<3` months critical, `<6` high, `<12` medium. |
| `continuous_loss` | Financial | At least 3 comparable loss periods high; 2 comparable periods medium; non-comparable periods require review. |
| `revenue_growth` | Financial | Comparable growth `<= -20%` high; `<0%` medium. |
| `customer_concentration` | Financial | Largest customer `>=50%` or top five `>=80%` high; largest `>=30%` or top five `>=60%` medium. |
| `supplier_concentration` | Financial | Largest supplier `>=50%` or top five `>=80%` high; largest `>=30%` or top five `>=60%` medium. |
| `redemption_rights` | Legal | Review actual effective or restorable shareholder redemption/special rights; ambiguity about termination/restoration is `needs_review`. Candidate severity is provisional `medium / 50`. |
| `material_litigation_compliance` | Legal | Review material pending matters or unresolved regulatory/licence impact; ambiguity about materiality or resolution is `needs_review`. Candidate severity is provisional `medium / 50`. |
| `precommercial_product` | Business | Applies when the core product is not commercialized and there is no product-sales revenue; unclear product stage or revenue attribution is `needs_review`. |

All applicable risks require source evidence. Financial values must preserve period,
currency, unit, sign, and the exact source text. Do not infer missing numbers.

## Resolved policy additions in v1.1

- Cash runway uses cash-flow-statement cash and cash equivalents. Do not add back
  time deposits with original maturity over three months. Retain conflicting formal
  definitions and report `ACCOUNTING_DEFINITION_CONFLICT`.
- When `applicable=false`, status is `rejected` and level is `not_applicable`.
- Cash runway, revenue growth, customer concentration and supplier concentration
  require deterministic calculations; continuous loss records comparable periods.
- Dash, blank and N/A are not zero unless the same formal disclosure system proves
  zero with supporting evidence. Otherwise use `needs_review`.

Do not resolve OPEN-01 zero-revenue concentration, OPEN-02 precommercial-product
severity, or OPEN-03 Expert Fact/Policy Label separation. Report the ambiguity.

## Evidence authority

Financial: audited financial statements / accountants' report > formal Financial
Information > formal business tables > Summary > generic Risk Factors.

Legal: specific contracts, shareholder rights, corporate structure, litigation,
regulatory or licence disclosures > formal Business/Legal disclosure > Summary >
generic Risk Factors.

Business: formal Business/Product/Pipeline disclosure > formal Summary business
description > generic Risk Factors.

Do not choose a Summary page as primary merely because it is easier to find.

## Multiple-page evidence

- `required`: all marked pages are jointly necessary (for example cash and operating
  cash outflow on different pages for cash runway).
- `alternative`: either page proves the same fact; prefer the higher-authority source
  as `primary`, and use the other as `cross_check`.
- `supporting_only`: contextual information that does not independently prove the fact.

One risk may have any number of evidence records. Do not create duplicate risk
instances merely because a fact spans several pages.

## Legal distinctions

Distinguish actual rights from generic clauses, terminated rights from restorable
rights, issuer obligations from shareholder obligations, actual litigation from
prospective boilerplate, and material matters from immaterial matters.

## Business distinctions

Distinguish non-commercialized products, absence of product sales, licensing or
milestone income versus product-sales revenue, and dependency on a core product.

Use `needs_review` when the prospectus does not support a confident conclusion.
Never force `verified` merely to complete the form.
"""


def _instructions(stock_code: str) -> str:
    return f"""# Annotation instructions — {stock_code}

1. Upload the original prospectus PDF, the root `GPT_EXPERT_ANNOTATION_PROTOCOL.md`,
   and this case's `blank_annotation.json` to a fresh external ChatGPT conversation.
2. State that this is a blind annotation. Do not request or reference Human Golden,
   previous annotations, Retriever results, Agent results, or evaluation output.
3. Read the original prospectus and independently assess **all eight** risk codes.
4. Replace every placeholder in `blank_annotation.json`; do not remove risk entries.
5. Record every necessary physical PDF page and exact quotation. Use multiple
   evidence records where a risk requires multiple pages.
6. Financial calculations must record periods, currency, unit, inputs, method, and result.
7. Return JSON only, following the template. Do not add markdown fences.
8. Do not treat absence of an easy keyword hit as proof that a risk is not applicable.
"""


def _blank(case: dict[str, object]) -> dict[str, object]:
    risks = []
    for code in sorted(V03_ENABLED_RISK_CODES):
        risks.append({
            "annotation_version": "gpt_expert_v1.1",
            "case_id": case["case_id"],
            "stock_code": case["stock_code"],
            "company_name": case["company_name"],
            "document_id": case["document_id"],
            "risk_code": code,
            "applicable": None,
            "expected_status": None,
            "expected_level": None,
            "confidence": None,
            "reasoning": None,
            "calculation_required": None,
            "calculation_method": None,
            "calculation_inputs": None,
            "calculation_result": None,
            "review_outcome": "expert_first_pass",
            "annotator_type": "external_gpt_expert",
        })
    return {
        "annotation_version": "gpt_expert_v1.1",
        "case_id": case["case_id"],
        "stock_code": case["stock_code"],
        "company_name": case["company_name"],
        "document_id": case["document_id"],
        "risks": risks,
        "evidence": [],
        "metadata": {
            "blind_annotation": True,
            "human_golden_visible_to_annotator": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--competition-root", type=Path, required=True)
    parser.add_argument("--local-2410", type=Path, default=Path("data/local/real_case_001/prospectus.pdf"))
    parser.add_argument("--output", type=Path, default=Path("reports/gpt_expert_annotation_pilot"))
    args = parser.parse_args()

    with args.catalog.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = {row["stock_code_wind"]: row for row in rows if row["stock_code_wind"] in TARGETS}
    if set(selected) != set(TARGETS):
        raise SystemExit(f"catalog mapping incomplete: found={sorted(selected)}")

    args.output.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, object]] = []
    for stock_code in TARGETS:
        row = selected[stock_code]
        if row["dataset_split"] not in ALLOWED_SPLITS:
            raise SystemExit(f"forbidden dataset split for {stock_code}: {row['dataset_split']}")
        pdf_path = args.local_2410 if stock_code == "2410.HK" else args.competition_root / row["relative_path"]
        exists = pdf_path.is_file()
        page_count = None
        actual_sha = None
        if exists:
            actual_sha = _sha256(pdf_path)
            with fitz.open(pdf_path) as document:
                page_count = document.page_count
        case = {
            "case_id": row["case_id"],
            "stock_code": stock_code,
            "company_name": row["company_short_name"],
            "document_id": row["case_id"],
            "pdf_path": str(pdf_path.resolve()),
            "pdf_exists": exists,
            "pdf_sha256": actual_sha,
            "catalog_sha256": row["sha256"],
            "dataset_split": row["dataset_split"],
            "page_count": page_count,
        }
        cases.append(case)
        case_dir = args.output / stock_code.replace(".", "_")
        case_dir.mkdir(parents=True, exist_ok=True)
        public_metadata = {key: value for key, value in case.items() if key != "pdf_path"}
        (case_dir / "case_metadata.json").write_text(json.dumps(public_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        (case_dir / "blank_annotation.json").write_text(json.dumps(_blank(case), ensure_ascii=False, indent=2), encoding="utf-8")
        (case_dir / "annotation_instructions.md").write_text(_instructions(stock_code), encoding="utf-8")
        (case_dir / "source_pdf_path.txt").write_text(str(pdf_path.resolve()), encoding="utf-8")

    inventory = {
        "pilot": "Phase 0.6A GPT Expert Blind Annotation Preparation",
        "blind_annotation": True,
        "human_golden_accessed": False,
        "2025_blind_accessed": False,
        "cases": cases,
    }
    (args.output / "source_inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "GPT_EXPERT_ANNOTATION_PROTOCOL.md").write_text(_protocol(), encoding="utf-8")
    print(json.dumps(inventory, ensure_ascii=False, indent=2))
    return 0 if all(case["pdf_exists"] for case in cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
