# 浙江同源康医药股份有限公司 (2410.HK) — Competition case report

- case_id: `ipo_2024_02410`
- listing_date: `2024-08-20`
- config: `configs/v045_competition_ai.yaml`
- analysis status: `completed` · analysis_id `c67f05f0-f72b-4e5f-9e3c-31c2972021fa`
- workflow: `enhanced_v2` · schema `1.0`
- parsed chunks: 706 · report sections: 13 · structured errors: 0

## Source integrity

- source file: `02410_12-08-2024_同源康醫藥－Ｂ_全球發售.pdf`
- SHA-256: `6c8179a58ac265d5a729895ef30db910dc15cee0a53ce653e866d487d29655cb` (matches the frozen catalog)
- size: 7668322 bytes · physical pages: 706
- dataset split: `development_exception`

The archive path is licensed local state and is deliberately not recorded. A prospectus whose bytes or page count differ from the frozen catalog is refused, never analysed.

## Channel states

- `document`: `available`
- `market`: `available`
- `model`: `available`
- `rule`: `available`

## Verified risks

- **cash_runway** · critical · verified · agent `financial`
  - conclusion: Based on reported cash of 77208 CNY thousand and 3-month operating cash outflow of 83918 CNY thousand, the estimated cash runway is approximately 2.76 months. This is a deterministic rule calculation, not a probability of post-listing price decline.
  - calculation `cash_runway` v1.1: `cash / (abs(operating_cash_flow) / period_months)` = 2.760122977192020782192139946 months
  - evidence `67ef7838-6af…` · page 563 · section `unknown`
  - evidence `60dd7129-941…` · page 562 · section `unknown`
  - verifier: Evidence passed; Calculation was independently recalculated; risk level and deterministic rule score matched policy. The score is not a probability.

## Pending risks

- **redemption_rights** · medium · needs_review · 3 evidence — legal_rights_verifier needs_review: holder_not_supported_by_evidence
- **material_litigation_compliance** · medium · needs_review · 3 evidence — litigation_compliance_verifier needs_review: closure_status_not_established, pending_status_not_supported_by_evidence, manual_legal_judgment_required

## Cross-agent conflicts and targeted re-check

- `partially_resolved` — legal produced 1 material_litigation_compliance risk item(s) that the Verifier left as needs_review; the assertion and its verification disagree.
  - re-check: targeted re-retrieval added 3 new evidence item(s); the Verifier settled 0 of 1 challenged risk item(s) and the rest remain unsettled
- `partially_resolved` — legal produced 1 redemption_rights risk item(s) that the Verifier left as needs_review; the assertion and its verification disagree.
  - re-check: targeted re-retrieval added 2 new evidence item(s); the Verifier settled 0 of 1 challenged risk item(s) and the rest remain unsettled
- `unresolved` — business held 9 bounded Evidence item(s) for precommercial_product and reported conflicting_values, while the document channel asserts nothing about precommercial_product: Commercialization or revenue facts conflict.
  - re-check: targeted re-retrieval found no in-scope Evidence beyond what the agent already held, so the gap is in extraction rather than retrieval; the machine asserts no risk for this code
- `partially_resolved` — financial held 3 bounded Evidence item(s) for continuous_loss and reported conflicting_values, while the document channel asserts nothing about continuous_loss: Retrieved financial Evidence could not be mapped to clean facts.
  - re-check: targeted re-retrieval surfaced 5 in-scope Evidence item(s) the agent did not use, so the gap is at least partly retrieval; the machine still asserts no risk for this code and the new Evidence is routed to human review
- `partially_resolved` — financial held 1 bounded Evidence item(s) for customer_concentration and reported needs_review, while the document channel asserts nothing about customer_concentration: Retrieved financial Evidence could not be mapped to clean facts.
  - re-check: targeted re-retrieval surfaced 5 in-scope Evidence item(s) the agent did not use, so the gap is at least partly retrieval; the machine still asserts no risk for this code and the new Evidence is routed to human review
- `partially_resolved` — financial held 2 bounded Evidence item(s) for revenue_growth and reported conflicting_values, while the document channel asserts nothing about revenue_growth: Retrieved financial Evidence could not be mapped to clean facts.
  - re-check: targeted re-retrieval surfaced 5 in-scope Evidence item(s) the agent did not use, so the gap is at least partly retrieval; the machine still asserts no risk for this code and the new Evidence is routed to human review
- `unresolved` — The frozen model's strongest driver market_core__log_prior_ipo_funds_raised_30d decreases risk while the document channel reports 1 high or critical verified document risk(s); the uncalibrated score direction disagrees with the document.
  - re-check: conflict rule document_model_divergence spans channels outside the document, so no document re-retrieval can settle it; it is carried to the Final Supervisor unresolved

## Final Supervisor

- LLM synthesis: `available` / `accepted` — grounded supervisory synthesis available
- deterministic severity floor: `critical`
- scope corrections: 0
- Gate E1 for this case: satisfied

## Traceability

- trace events: 33 (step by step in `agent_reasoning_log.md`)
- agent / tool / evidence traceability: 1.0 / 1.0 / 1.0
- overall measured traceability: 1.0

## What this report does not demonstrate

- every channel in this run was available and arbitrated.

The rule and model scores are not probabilities. This report is not investment, legal or
listing advice.
