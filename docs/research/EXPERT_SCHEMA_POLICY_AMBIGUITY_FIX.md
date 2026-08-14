# Expert Schema / Protocol Policy-Ambiguity Fix

## Scope

This change aligns the evaluation-only `ExpertRiskAnnotation` model with GPT
Expert Annotation Protocol v1.1. It does not change production `RiskItem`, any
public Pydantic schema, a risk threshold, or runtime Agent behavior.

## Contract conflict

Protocol v1.1 requires annotators to report unresolved policy rather than force a
complete-looking answer. `OPEN-01` covers zero-revenue or undefined-denominator
concentration, while `OPEN-02` keeps `precommercial_product` severity open. The
previous evaluation model nevertheless required every `expected_level` to be an
enum value and could not represent an applicable `needs_review` risk whose level
was intentionally unresolved.

The evaluation contract now distinguishes:

- `not_applicable`: the risk is not triggered; it must be
  `applicable=false + rejected`;
- `null`: the risk fact/candidate is applicable and needs review, but the frozen
  policy cannot yet determine severity.

`null` is legal only for `applicable=true + expected_status=needs_review`.
Verified risks still require a concrete level. The validator validates the
representation and never infers or fills severity.

## 1167.HK revalidation

The original `ipo_2020_01167` pass1 annotation remains byte-for-byte unchanged.
Its prior `validation_result.json` is retained as the historical result. Under
the corrected evaluation contract, the three null-level schema errors for
`revenue_growth`, `customer_concentration`, and `precommercial_product` are no
longer errors.

`customer_concentration` remains governed by `OPEN-01` and
`precommercial_product` by `OPEN-02`; neither policy item is resolved here.

## Revenue basis review item

`REVENUE_BASIS_REVIEW_REQUIRED = true`

The 1167 annotation uses product-sales revenue as the basis for
`revenue_growth`. Protocol v1.1 does not yet freeze whether that risk must use
reported accounting revenue or product-sales revenue. Licensing, milestone,
service, collaboration, and other accounting revenue may differ from product
sales. This commit does not change the annotation, recalculate growth, or select a
basis. A later independent audit and policy review must resolve that definition.

## Governance flags

```text
EXPERT_EVALUATION_SCHEMA_CHANGED = true
PRODUCTION_SCHEMA_CHANGED = false
PROTOCOL_POLICY_CHANGED = false
OPEN_01_RESOLVED = false
OPEN_02_RESOLVED = false
REVENUE_GROWTH_BASIS_RESOLVED = false
ORIGINAL_1167_ANNOTATION_MODIFIED = false
```
