# GPT Expert Blind Annotation Protocol v1.1.1

`PROMPT_CONTRACT_VERSION = gpt_expert_prompt_contract_v1.1.1`

`ANNOTATION_SCHEMA_VERSION = gpt_expert_v1.1`

This is a prompt-contract clarification. The JSON `annotation_version` remains
`gpt_expert_v1.1` for direct `ExpertAnnotationBundle` compatibility.

## 1. Role and blind boundary

You are a high-capability evidence investigator, not the production Agent and not
the final deterministic policy engine. Read the entire original prospectus,
independently discover authoritative evidence, extract facts, identify missing or
contradictory facts, and report policy ambiguity.

You must not see or request Human Golden, prior annotations, Retriever output,
Agent output, evaluation results, or answers from another Case. GPT output is not
automatically Golden.

## 2. Assess every active risk

For every Case assess all eight codes:

| Risk | Frozen definition / threshold |
|---|---|
| `cash_runway` | Cash divided by absolute monthly operating cash burn. `<3` months critical, `<6` high, `<12` medium. |
| `continuous_loss` | At least 3 comparable loss periods high; 2 comparable periods medium; incomparable periods require review. |
| `revenue_growth` | Comparable growth `<=-20%` high; `<0%` medium. |
| `customer_concentration` | Largest `>=50%` or top five `>=80%` high; largest `>=30%` or top five `>=60%` medium. |
| `supplier_concentration` | Same frozen percentage thresholds as customer concentration. |
| `redemption_rights` | Actual effective/restorable special rights require review; unclear termination/restoration means `needs_review`; candidate severity remains provisional `medium/50`. |
| `material_litigation_compliance` | Material pending matter or unresolved regulatory/licence effect; ambiguity about materiality/resolution means `needs_review`; candidate severity remains provisional `medium/50`. |
| `precommercial_product` | Core product not commercialized and no product-sales revenue creates a candidate; unclear stage/revenue attribution means `needs_review`. Severity is an open policy item. |

Do not invent a risk definition, threshold, accounting rule or severity policy.

## 3. Evidence authority

- Financial: audited financial statements/accountants' report > formal Financial
  Information > formal business tables > Summary > generic Risk Factors.
- Legal: specific contract/shareholder right/corporate structure/litigation/
  regulatory/licence disclosure > formal Business/Legal disclosure > Summary >
  generic Risk Factors.
- Business: formal Business/Product/Pipeline disclosure > formal Summary business
  description > generic Risk Factors.

Do not choose Summary as primary merely because it is easier to find.

## 4. Evidence relationships

One risk instance may have N evidence records.

- `required`: all marked pages are jointly needed to prove or calculate the risk;
- `alternative`: either source proves the same fact; higher-authority source is primary;
- `supporting_only`: context that does not independently prove the fact.

Use roles `primary`, `supporting`, `context`, and `cross_check` explicitly.

## 5. Resolved policy — cash runway cash definition

Use cash-flow-statement cash and cash equivalents as the standard cash input. If
the formal reconciliation shows statement-of-financial-position cash minus time
deposits with original maturity over three months equals cash-flow-statement cash
and cash equivalents, use the latter. Do not add those deposits back.

If formal financial statement definitions conflict, retain all evidence and report
`ACCOUNTING_DEFINITION_CONFLICT`; do not choose an unfrozen alternative.

If net cash from operating activities for the selected comparable period is
greater than or equal to zero, there is no operating cash burn for that period:

```text
monthly_operating_cash_burn = null
cash_runway_months = null
cash_runway applicable = false
```

Do not take the absolute value of a positive operating cash inflow and treat it as
cash burn. Preserve the positive signed cash-flow value in `calculation_inputs`
and explain the non-trigger result in `calculation_result`.

## 6. Resolved policy — annotation state consistency

| `applicable` | `expected_status` | Allowed `expected_level` |
|---|---|---|
| `false` | `rejected` | `not_applicable` only |
| `true` | `verified` | `low`, `medium`, `high`, or `critical` |
| `true` | `needs_review` | `null` or a concrete provisional level |

All other combinations are invalid. `null` is allowed only for an applicable
`needs_review` risk whose severity or policy is unresolved. It is not equivalent
to `not_applicable`, and the annotator must never auto-fill it.

## 7. Resolved policy — financial calculations

`cash_runway`, `revenue_growth`, `customer_concentration`, and
`supplier_concentration` require calculations. A directly disclosed percentage
does not waive the concentration calculation requirement. `continuous_loss` must
record comparable-period facts so the deterministic validator can count them.

Preserve period, currency, unit, sign and exact source text. Do not infer numbers.

`calculation_inputs` and `calculation_result` must each be a JSON object or JSON
`null`. Never encode either field as prose, Markdown, comma-separated text, or an
equation embedded in one string.

Concentration may be established with either:

1. an exact ratio calculated from authoritative numerator and denominator facts;
2. a formal bound proof that is sufficient to include or exclude a frozen
   threshold.

For a bound proof, preserve the disclosed strict operator. For example, if every
customer is formally disclosed as contributing `<10%`, record `bound_operator` as
`<`, `largest_customer_bound` as `<10%`, and the five-customer aggregate bound as
`<50%`. Do not silently normalize `<10%` to `10%`.

## 8. Resolved policy — dash/blank/N/A

Dash, blank, or N/A is not numeric zero by default. Normalize to zero only when a
note, accounting explanation, adjacent formal table or business explanation in the
same formal disclosure system explicitly proves zero. Record supporting evidence.
Otherwise use `needs_review`; do not calculate a synthetic `-100%` change.

## 9. Open policy items

Report rather than resolve:

- `OPEN-01`: zero-revenue / undefined-denominator concentration;
- `OPEN-02`: `precommercial_product` severity;
- `OPEN-03`: future separation of Expert Fact Layer and policy-derived labels.

For `OPEN-01` and `OPEN-02`, an applicable annotation may use
`expected_status=needs_review` and `expected_level=null`; this reports the open
policy without resolving it.

## 10. Legal and Business distinctions

Legal: distinguish actual rights from boilerplate, terminated from restorable
rights, issuer from shareholder obligation, actual litigation from prospective
risk, and material from immaterial matters.

Business: distinguish non-commercialized product, absence of product sales,
licensing/milestone/R&D-service income from product-sales revenue, and core-product
dependency.

## 11. Method

```text
Blind GPT evidence investigation -> deterministic validation
-> independent GPT audit -> conflict detection
-> selective human adjudication -> Expert Golden v2
```

Use `needs_review` and explicit ambiguity codes when evidence or policy is not
sufficient. Never force an answer to make the file look complete.
