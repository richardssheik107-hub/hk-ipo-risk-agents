# Role-B v0.4.6 — Concentration Exact-Fact Batch 005

## Decision

```text
BATCH_005 = ACCEPTED_DETERMINISTIC_GAIN
base = 0fe75521f27c6650575cf3ffe213df2c38273565
production_head = bfb18ef3680e99e7890885e3ad94cea2d1b3c04b
```

This batch closes one generic concentration exact-fact failure caused by PDF
layout whitespace around decimal separators and by an adjacent, unrelated date
overriding the period attached to the local percentage series. The verifier now
recognizes only digit-bounded spaced decimal separators such as `32 .7`; it does
not relax numeric, Evidence, calculation, severity, or schema validation.

No issuer, stock, case, page, Evidence ID, or Gold-specific rule was added.

## Frozen-journal result

The canonical replay used the same frozen journal as Batch 004:

```text
fixed10_hash = 5758b9f0b38fe0dabffade07d1da850938406b98ebe021dc65c93e806a1f3b6a
gold_manifest_hash = fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c
journal_hash = 8d5cb474aaf6db3dcc504b9b7f926ac5948834709d9798dd2bf11252e0dce5e2
network_calls = 0
```

| Metric | Batch 004 | Batch 005 | Change |
|---|---:|---:|---:|
| M1 | 12/30 (40.00%) | 12/30 (40.00%) | 0 |
| M2 | 17/48 (35.42%) | 18/48 (37.50%) | +1 unit |

Per-risk M1 remained non-regressive:

```text
cash_runway             1/5
customer_concentration  4/8
supplier_concentration  3/9
redemption_rights       4/8
```

Customer and supplier existence precision remained 100%. The recovered unit is
the supplier-concentration Evidence unit for `ipo_2020_09600`. Its deterministic
values are `32.7` and `67.2`, bound to the local six-month period ended
2020-06-30. The final risk remains `medium` while Existing Gold is `high`; this
severity mismatch is retained rather than changing the frozen policy to improve
M1.

An earlier non-canonical replay used `forensic_013` journal hash `950092...` and
was rejected as incomparable. It was not used in the acceptance decision.

## Fresh checkpoint

Exactly one fresh fixed-10 run was executed after the deterministic gate:

```text
offline M1/M2 = 8/30, 13/48
shadow M1/M2  = 8/30, 13/48
gated M1/M2   = 11/30, 17/48
monotonicity  = PASS
structured valid = 38/40
fallbacks = 2
transport failures = 0
scope rejections = 0
fresh journal hash = da2361fd34f88d1402be85ed75c87ef6fb32ba2dd755265642599330b35dbeb4
```

The one-unit M1 and M2 gaps versus the fixed journal are recorded as runtime
LLM/Evidence variance. The fresh run was not retried and did not drive further
code changes.

## Validation

```text
targeted tests                 167 passed
full pytest                    2208 passed, 3 warnings
compileall                     PASS
validate_project               PASS
validate_competition_data      PASS
validate_competition_runtime   PASS
Role-D receipt validation      PASS
git diff --check               PASS
Validation opened              false
2025 Blind accessed            false
Existing Gold modified         false
```

## Scope and remaining roots

Changed production modules are limited to Financial deterministic extraction,
concentration reconciliation diagnostics, and numeric Evidence verification.
Retriever, Parser, Prompt, provider/model, evaluator, fixed-10, Gold, Legal, and
Role-D frozen artifacts were not changed.

The next ranked deterministic root is `period_candidate_generation`, followed
by parser preservation and numeric extraction. M4 Human Review remains an
external blocker and is not bypassed.
