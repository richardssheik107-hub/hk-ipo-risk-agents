# Annotation Instructions

1. Confirm the conversation contains no prior Golden or model output.
2. Read the full prospectus and assess all eight active risks independently.
3. Prefer authoritative formal sources; record all required evidence pages.
4. Distinguish evidence role and requirement; do not create duplicate risks for
   multiple pages.
5. Financial facts must preserve period, currency, unit and sign.
6. Follow resolved policies in Protocol v1.1 and report every open-policy ambiguity.
7. Use `needs_review` where evidence or policy is insufficient.
8. Return one JSON object only, without Markdown fences or commentary.
9. Do not include secrets, local paths, Human Golden, Retriever or Agent output.
10. Every risk-level and evidence-level `confidence` must be a JSON number in
    the inclusive range `0.0` to `1.0`. Do not use percentages, strings or
    values such as `80`.
11. The final JSON must validate directly as `ExpertAnnotationBundle`. Do not
    add fields outside the bundle, risk, evidence or metadata contracts.

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
