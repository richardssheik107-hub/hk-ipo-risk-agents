# Annotation Instructions

1. Confirm the conversation contains no prior Golden or model output.
2. Read the full prospectus and assess all eight active risks independently.
3. Prefer authoritative formal sources; record all required evidence pages.
4. Distinguish evidence role and requirement; do not create duplicate risks for
   multiple pages.
5. Financial facts must preserve period, currency, unit and sign.
6. Follow resolved policies in Protocol v1.1.1 and report every open-policy ambiguity.
7. Use `needs_review` where evidence or policy is insufficient. An applicable
   unresolved risk may use JSON `null` for `expected_level`; never guess a level.
8. Return one JSON object only, without Markdown fences or commentary.
9. Do not include secrets, local paths, Human Golden, Retriever or Agent output.
10. Every risk-level and evidence-level `confidence` must be a JSON number in
    the inclusive range `0.0` to `1.0`. Do not use percentages, strings or
    values such as `80`.
11. The final JSON must validate directly as `ExpertAnnotationBundle`. Do not
    add fields outside the bundle, risk, evidence or metadata contracts.
12. `calculation_inputs` and `calculation_result` MUST each be a JSON object or
    JSON `null`. Never use prose strings, Markdown, comma-separated text, or an
    equation embedded in one string for either field.
13. For non-negative operating cash flow, preserve the signed value and use
    `monthly_operating_cash_burn=null` and `cash_runway_months=null`; never treat
    a positive inflow as burn by taking its absolute value.
14. Concentration calculations may use an exact ratio or an authoritative formal
    bound proof. Bound proofs must preserve strict operators such as `<`.

## Calculation Object Examples

Positive operating cash flow:

```json
{
  "calculation_inputs": {
    "period": "six months ended 30 September 2019",
    "currency": "MYR",
    "unit": "RM'000",
    "cash_and_cash_equivalents": 39079,
    "net_cash_from_operating_activities": 21817,
    "period_months": 6
  },
  "calculation_result": {
    "monthly_operating_cash_burn": null,
    "cash_runway_months": null,
    "assessment": "no_operating_cash_burn"
  }
}
```

Concentration threshold-exclusion bound:

```json
{
  "calculation_method": "threshold_exclusion_bound",
  "calculation_inputs": {
    "single_customer_upper_bound_pct": 10,
    "maximum_customers_considered": 5,
    "bound_operator": "<"
  },
  "calculation_result": {
    "largest_customer_bound": "<10%",
    "top_five_customer_bound": "<50%",
    "medium_threshold_excluded": true
  }
}
```

## Evidence Object Schema

Every element of the top-level `evidence` array must be one object with exactly
these fields:

```json
{
  "case_id": "ipo_YYYY_NNNNN",
  "risk_code": "one active risk code",
  "page": 1,
  "evidence_role": "primary",
  "requirement": "required",
  "source_authority": "financial_information",
  "exact_text": "verbatim prospectus text",
  "evidence_reason": "why this evidence supports the assessment",
  "confidence": 0.85
}
```

Field constraints:

- `case_id`: non-empty string and exactly equal to the bundle `case_id`.
- `risk_code`: one of the eight risk codes present in `risks`.
- `page`: integer greater than or equal to 1, using the physical PDF page.
- `evidence_role`: exactly one of `primary`, `supporting`, `context`,
  `cross_check`.
- `requirement`: exactly one of `required`, `alternative`, `supporting_only`.
- `source_authority`: exactly one of `audited_financial_statement`,
  `accountants_report`, `financial_information`, `business_section`,
  `legal_disclosure`, `corporate_structure`, `pre_ipo_investment`, `summary`,
  `risk_factors`, `other`.
- `exact_text`: non-empty verbatim text from the PDF.
- `evidence_reason`: non-empty explanation of the evidence relationship.
- `confidence`: JSON number in the inclusive range `0.0` to `1.0`.

Do not add `evidence_id`, `document_id`, `chunk_id`, `section`, `metadata` or
other fields to an Evidence Object. They are not part of
`ExpertEvidenceAnnotation` and would make the final bundle fail validation.

Every risk with `applicable=true` must have at least one matching Evidence
Object. Non-applicable risks may have no evidence. The example above describes
the shape only; replace every example value with actual case evidence.
