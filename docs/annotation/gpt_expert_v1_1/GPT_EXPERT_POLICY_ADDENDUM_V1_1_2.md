# GPT Expert Policy Addendum v1.1.2

`POLICY_VERSION = gpt_expert_policy_addendum_v1.1.2`

This addendum is an **evaluation/audit policy layer** on top of the historical
`GPT Expert Blind Annotation Protocol v1.1.1`. It does not rewrite the original
blind prompt, does not alter `pass1`, and does not promote any record to final or
Human Golden.

## Why this addendum exists

Phase 1/2/2b exposed a finite set of deterministic financial audit gaps:
33 policy ambiguities and 142 records with insufficient canonical structured
inputs. The goal of v1.1.2 is to make every one of those records operationally
closed without fabricating numbers.

A record is **closed** when either:

1. the frozen numeric facts determine a unique label; or
2. the evidence cannot determine a unique numeric label and the final audit state
   is explicitly `applicable=true`, `expected_status=needs_review`,
   `expected_level=null`.

The second outcome is a valid final review state, not an unresolved software bug.

## 1. Multi-period financial policy

For `cash_runway`, `revenue_growth`, `customer_concentration`, and
`supplier_concentration`, evaluate every authoritative **valid comparable period**
that is already supported by structured facts.

When different valid periods imply different levels, retain the **most adverse
observed frozen level**:

`critical > high > medium > low > not_applicable`.

Rationale: a later improvement does not erase a material risk state that occurred
within the disclosed track-record period, and choosing only the latest period can
silently hide an observed trigger. This is an audit/risk-detection convention, not
an accounting restatement rule.

For `revenue_growth`, this is equivalent to retaining the most adverse valid
comparable growth pair. Do not compare unlike durations.

## 2. Continuous-loss comparability

Never pool unlike durations. Group loss facts by homogeneous duration (FY, H1,
9M, 8M, 7M, 6M, 5M, 4M, 3M, etc.), evaluate each group independently, and retain
the most severe group result.

Chinese period labels such as `截至2020年12月31日止年度` are normalized as FY;
this is a parser clarification, not a new accounting inference.

## 3. OPEN-01 is resolved

### 3.1 Revenue growth with an exact zero base

If authoritative evidence proves prior revenue is exactly zero and current
revenue is non-negative, a negative-growth trigger cannot occur. The audit state
is `rejected/not_applicable`.

Do **not** synthesize a percentage for `0 -> 0` or `0 -> positive`.

### 3.2 Customer concentration with exact zero revenue

If authoritative evidence proves the relevant customer/product-sales revenue
denominator is exactly zero, customer-revenue concentration is not applicable for
that scope. The audit state is `rejected/not_applicable`.

The concentration ratios remain `null`; do not convert `0/0` into `0%`.

## 4. Formal bounds and genuine evidence limits

A formal numeric bound may confirm `not_applicable` only when it is sufficient to
exclude the frozen medium threshold. Preserve strict operators.

If the cited evidence is qualitative only (for example, “no major suppliers”) or
a numeric/bound input still cannot prove a unique frozen threshold state, do not
invent a percentage or redefine an undefined business term. The closed audit state
is `needs_review/null` until new authoritative numeric evidence is added.

This rule explicitly covers `ipo_2020_02263 / supplier_concentration`: the cited
Business disclosure is useful qualitative evidence but is not a 30/50/60/80%
threshold proof.

## 5. Immutability and downstream use

- `pass1/expert_annotation_v1.json` remains byte-for-byte immutable.
- v1.1.2 resolutions are stored under `audit/` as overlays.
- Evidence text and reasoning are not rewritten.
- No result is promoted to `final/` or Human Golden by this phase.
- Semantic risks (`redemption_rights`, `material_litigation_compliance`,
  `precommercial_product`) remain on their independent semantic-review path; they
  are not part of this deterministic financial closure phase.
