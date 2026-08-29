# 华润饮料控股有限公司 (2460.HK) — Competition case report

- case_id: `ipo_2024_02460`
- listing_date: `2024-10-23`
- config: `configs/v045_competition_ai.yaml`
- analysis status: `completed` · analysis_id `a8b0f43e-e2a1-4265-9fc8-b28976d0eef3`
- workflow: `enhanced_v2` · schema `1.0`
- parsed chunks: 578 · report sections: 13 · structured errors: 0

## Source integrity

- source file: `02460_15-10-2024_華潤飲料_全球發售.pdf`
- SHA-256: `036c61af76dc6e9e4aad070e8643e9c735c020f514cd3a3682ad2e6a43346485` (matches the frozen catalog)
- size: 8504745 bytes · physical pages: 579
- dataset split: `validation`

The archive path is licensed local state and is deliberately not recorded. A prospectus whose bytes or page count differ from the frozen catalog is refused, never analysed.

## Channel states

- `document`: `available`
- `market`: `available`
- `model`: `available`
- `rule`: `available`

## Verified risks

- none. The document channel asserted no formal risk in this run; nothing was written in to fill the gap.

## Pending risks

- **redemption_rights** · medium · needs_review · 2 evidence — legal_rights_verifier needs_review: holder_not_supported_by_evidence
- **material_litigation_compliance** · medium · needs_review · 1 evidence — litigation_compliance_verifier needs_review: actual_matter_not_established, closure_status_not_established, remediation_metadata_not_supported_by_evidence, material_impact_not_supported_by_evidence, manual_legal_judgment_required

## Cross-agent conflicts and targeted re-check

- `partially_resolved` — legal produced 1 material_litigation_compliance risk item(s) that the Verifier left as needs_review; the assertion and its verification disagree.
  - re-check: targeted re-retrieval added 4 new evidence item(s); the Verifier settled 0 of 1 challenged risk item(s) and the rest remain unsettled
- `partially_resolved` — legal produced 1 redemption_rights risk item(s) that the Verifier left as needs_review; the assertion and its verification disagree.
  - re-check: targeted re-retrieval added 3 new evidence item(s); the Verifier settled 0 of 1 challenged risk item(s) and the rest remain unsettled
- `partially_resolved` — financial held 3 bounded Evidence item(s) for continuous_loss and reported conflicting_values, while the document channel asserts nothing about continuous_loss: Retrieved financial Evidence could not be mapped to clean facts.
  - re-check: targeted re-retrieval surfaced 5 in-scope Evidence item(s) the agent did not use, so the gap is at least partly retrieval; the machine still asserts no risk for this code and the new Evidence is routed to human review
- `partially_resolved` — financial held 2 bounded Evidence item(s) for revenue_growth and reported conflicting_values, while the document channel asserts nothing about revenue_growth: Retrieved financial Evidence could not be mapped to clean facts.
  - re-check: targeted re-retrieval surfaced 5 in-scope Evidence item(s) the agent did not use, so the gap is at least partly retrieval; the machine still asserts no risk for this code and the new Evidence is routed to human review
- `unresolved` — The frozen model's strongest driver market_core__log_prior_ipo_funds_raised_30d increases risk while the document channel reports no high or critical verified document risk; the uncalibrated score direction disagrees with the document.
  - re-check: conflict rule document_model_divergence spans channels outside the document, so no document re-retrieval can settle it; it is carried to the Final Supervisor unresolved

## Final Supervisor

- LLM synthesis: `available` / `accepted` — grounded supervisory synthesis available
- deterministic severity floor: `low`
- scope corrections: 0
- Gate E1 for this case: satisfied

## Traceability

- trace events: 29 (step by step in `agent_reasoning_log.md`)
- agent / tool / evidence traceability: 1.0 / 1.0 / 1.0
- overall measured traceability: 1.0

## What this report does not demonstrate

- No formal RiskItem was verified in this run. The chain executed end to end and Evidence was retrieved, so this case demonstrates chain integrity and traceability, not document extraction quality (Role B coverage).

The rule and model scores are not probabilities. This report is not investment, legal or
listing advice.
