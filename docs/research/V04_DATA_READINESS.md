# V04 Data Readiness — Current Reference Snapshot

> Audit snapshot: **2026-08-25**  
> Status: **PR-A–PR-G COMPLETE / FROZEN; PR-H PARTIAL / BLOCKED**  
> This file records measured readiness only; plans do not change counts.

## 1. Official modeling universe

Official 2020–2024 listing-year universe: **438 cases**.

```text
2020  125
2021   97
2022   78
2023   68
2024   70
```

Split authority is `official_listed_date.year`, not document `source_year`.

## 2. Production Document readiness — COMPLETE / FROZEN

```text
Official cases                 438
Production analyses            438 / 438
Authoritative snapshots        438 / 438
Production Document-X          438 / 438
Feature schema                 v04_document_features_v1
Feature dimension              100
Production failures            0
Silent drops                   0
Determinism                    438 checked / 0 mismatch / PASS
2025 Blind y accessed          NO
```

Frozen Production artifact-set hash:

```text
9197b0f4f90e6d43277586ac40160679d40f91e3b30223578d0853d9dc288bf3
```

Recent opt-in table-path work improves mixed annual/interim statement extraction but does not rewrite the frozen PR-A Production artifact set.

## 3. Governed IPO EOD foundation

```text
rows                           433,776
target securities matched      432 / 438
missing EOD                       6
raw EOD SHA256                  190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152
official bridge SHA256          751de6968ad8935ad45a8cd2841adbdc498d2bce6bb87153a1930959f4f85198
```

EOD match is not Outcome availability.

## 4. Market-X Core — COMPLETE / FROZEN

```text
schema                         v04_ipo_market_context_features_v1
policy                         ipo_market_context_policy_v1
positions                      15 raw + 15 missing indicators = 30
Official coverage              438 / 438
Failures / silent drops        0 / 0
PIT failures                   0
Development / Validation       368 / 70
Determinism                    PASS
2025 Blind y accessed          NO
```

Target IPO post-listing facts do not enter its own X.

## 5. Market-X Extended — PARTIAL, governed where available

### HSI / broad market

Governed HSI-derived pre-listing return/volatility features are ready for the official 438-case cohort:

```text
hsi_return_5d                  438 / 438
hsi_return_20d                 438 / 438
market_volatility_20d          438 / 438
PIT / future-row audit         PASS
```

### HKEX turnover

Official HKEX Main Board + GEM turnover integration is accepted:

```text
market_turnover_20d_mean       438 / 438
source status                  ACCEPT
PIT                            PASS
```

### HSCI industry indexes

```text
official series accepted       12 / 12
coverage                       2021-08-19 ... 2025-12-30
```

However company industry classification is not PIT-safe:

```text
production industry_return_5d    0 / 438
production industry_return_20d   0 / 438
INDUSTRY_MAPPING_PIT_BLOCKED    432 cases
MISSING_INDUSTRY_CLASSIFICATION   6 cases
```

Static current classification cannot be promoted to listing-time classification. Older HSCI price history alone does not resolve this blocker.

### Recent IPO context measured in current readiness audit

```text
recent_ipo_1d_sample_count      438 / 438
recent_ipo_5d_sample_count      438 / 438
recent_ipo_break_rate           244 / 438 available
recent_ipo_return_5d            243 / 438 available
```

Missingness remains explicit where no eligible prior-IPO sample exists.

## 6. PR-C 5D Outcome — COMPLETE / FROZEN

```text
Official coverage              438
Outcome available              424
Outcome unavailable             14
Development available          354 / 368
Validation available            70 / 70
missing_base_price              12
no_eligible_session              2
Development q25 threshold      -0.1000
Determinism                    PASS
2025 Blind y accessed          NO
```

Frozen target-set hash:

```text
5e0dedc8d207c8e73ca6439efb72f463c6b6f276c1c6c48e3ad7a989ad1533f4
```

## 7. PR-D Canonical Dataset — COMPLETE / FROZEN

```text
Model-ready                    424
Explicit exclusions             14
Development                    354
Validation                      70
Schema                         v04_canonical_modeling_dataset_v1
Generation failures              0
Silent drops                     0
Identity mismatch                0
Feature-order drift              0
Same-provenance resume          PASS
2025 Blind y accessed           NO
```

Frozen PR-D manifest hash:

```text
f6900c707187c23c5d01fa98fc8d9d21d040ce2c3ffa0a2a6340a0947f78e80d
```

## 8. Oracle readiness

### Oracle v1 — historical immutable

```text
materialized        60
current eligible    55
Development         55
Validation           0
```

### Oracle v2 — COMPLETE / FROZEN / EVALUATION-ONLY

```text
annotation inventory       101
valid annotations          100
materialized                98
strict usable               96
Development usable          77
Validation usable           19
feature count              142
identity unresolved          0
evaluation_only            true
production_consumable      false
2025 Blind y accessed      false
```

## 9. Frozen PR-E / PR-F data usage

Formal model cohorts:

```text
Full Production        354 Dev / 70 Val
Oracle fair intersection 77 Dev / 19 Val
```

Frozen PR-F Full Production 2024:

```text
M   ROC-AUC 0.4246
P   ROC-AUC 0.5000
PM  ROC-AUC 0.4246
```

PM=M under the frozen LightGBM policy. Oracle OM-M is -0.0143 with a wide interval crossing zero. These are measured findings, not readiness failures.

## 10. PR-G / PR-H product readiness

PR-G is COMPLETE / FROZEN on a real 2410.HK prospectus and deterministic Final Supervisor/report output.

PR-H infrastructure is implemented but formal gate remains blocked:

```text
Document runtime         available on governed real case
Market runtime           available on governed PR-B Core
Rule runtime             available
Model runtime            disabled without original frozen PR-F handoff
real governed demo count 1 in the formal completion record
formal requirement       3–5 2024 cases with all required channels
```

The missing model runtime is an immutable-input availability problem, not authorization to rerun or tune PR-F.

## 11. Competition-stage planned data work

Not yet frozen / not claimed complete:

```text
CH-1  1D / 20D / 60D outcomes
      market-adjusted return
      20D / 60D drawdown / volatility

CH-2  per-risk Document benchmark labels/metrics

CH-3  versioned Competition Market / IPO Heat features
      PIT-safe comparable context
```

Every new dataset must preserve Development / Validation / Blind governance and version independently from frozen PR-A–PR-D artifacts.

## 12. Current source status table

| Source / artifact | Status | Use |
| --- | --- | --- |
| Official IPO identity | AVAILABLE 438/438 | identity / split |
| Prospectus | AVAILABLE 438/438 baseline corpus | Document |
| Production Document-X | FROZEN 438/438 | P / PM |
| Governed IPO EOD | 432/438 securities | Core / Outcome |
| Market-X Core | FROZEN 438/438 | M / PM |
| HSI Extended | READY 438/438 | optional governed Market context |
| HKEX turnover | READY 438/438 | optional governed Market context |
| Industry return | PIT_BLOCKED 0/438 | unavailable until temporal mapping exists |
| 5D Outcome | FROZEN 424/438 | baseline y |
| Canonical Dataset | FROZEN 424 | baseline modeling |
| Oracle v2 | FROZEN 98 / 96 strict | evaluation-only O / OM |
| PR-F per-case runtime handoff | MISSING in current PR-H workspace | product model channel blocker |

## 13. Gate state

```text
PR-A_DOCUMENT_GATE        PASS / FROZEN
PR-B_MARKET_CORE_GATE     PASS / FROZEN
PR-C_OUTCOME_GATE         PASS / FROZEN
PR-D_MODEL_READY_GATE     PASS / FROZEN
ORACLE_V2_GATE            PASS / FROZEN
PR-E_BASELINE_GATE        PASS / FROZEN
PR-F_LIGHTGBM_GATE        PASS / FROZEN
PR-G_SUPERVISOR_GATE      PASS / FROZEN
PR-H_FULL_E2E_GATE        PARTIAL / BLOCKED
v0.4.3                    NOT CREATED
2025_BLIND_Y              NOT ACCESSED
```
