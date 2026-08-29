# Role-B v0.4.6 — Concentration Fact Conversion Batch 004

## Decision

```text
BATCH_004 = ACCEPTED
production_commit = a0ae90a
```

The change preserves a parsed, bounded customer/supplier percentage as an
Evidence-grounded `pending` RiskItem when deterministic period/value
reconciliation cannot produce a verified calculation. It does not invent a
percentage, threshold, calculation, Evidence item, or verified severity.

An explicit disclosure that the issuer does not depend on a single
counterparty, or that a top-five set cannot be identified, remains negative
concentration evidence. An unrelated ownership percentage in such a paragraph
cannot create a concentration risk.

## Fixed-journal result

Identity:

```text
fixed10_hash = 5758b9f0b38fe0dabffade07d1da850938406b98ebe021dc65c93e806a1f3b6a
gold_manifest_hash = fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c
journal_hash = 8d5cb474aaf6db3dcc504b9b7f926ac5948834709d9798dd2bf11252e0dce5e2
provider = openai_responses
model = ark-code-latest
network_calls = 0
```

| Metric | Frozen floor | Batch 004 | Change |
|---|---:|---:|---:|
| M1 | 10/30 (33.33%) | 12/30 (40.00%) | +2 units |
| M2 | 14/48 (29.17%) | 17/48 (35.42%) | +3 units |

Per-risk M1 remained non-regressive:

```text
cash_runway             1/5
customer_concentration  4/8
supplier_concentration  3/9
redemption_rights       4/8
```

Customer and supplier existence precision both remained 100%. Redemption
Evidence remained 5/11. The first broad candidate created one proven false
positive from an unrelated shareholding percentage; that candidate was not
accepted. A generic negative-disclosure guard removed the false positive while
retaining the metric gains.

The replay runner forbids `shadow` together with `--replay-journal`; therefore
formal offline/shadow/gated monotonicity is recorded as `NOT_PROVEN` for this
zero-network replay rather than reported as a false PASS.

## Validation

```text
targeted tests              163 passed
full pytest                 2196 passed, 3 warnings
compileall                  PASS
validate_project            PASS
validate_competition_data   PASS
validate_competition_runtime PASS
git diff --check            PASS
Validation opened           false
2025 Blind accessed         false
Existing Gold modified      false
```

## Next root

Batch 004 closes only the safe pending-conversion gap. Verified concentration
units that still lack a complete deterministic fact remain unresolved. The next
ranked root is `concentration_exact_fact_extraction`, followed by period-candidate
generation, parser preservation, numeric extraction, and LLM Evidence stability.
