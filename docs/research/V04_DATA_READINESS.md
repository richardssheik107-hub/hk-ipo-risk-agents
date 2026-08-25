# V04 Data Readiness — Current Reference Snapshot

> Audit snapshot: **2026-08-25**  
> Status: **PR-A–PR-G COMPLETE / FROZEN; PR-H PARTIAL / BLOCKED**  
> This file records measured readiness plus the remaining competition-required data artifacts.

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
Determinism                    PASS
2025 Blind y accessed          NO
```

Competition gap is not corpus coverage; it is **real LLM semantic quality + submission-ready Risk/Evidence benchmark**.

## 3. Market-X Core — COMPLETE / FROZEN

```text
schema                         v04_ipo_market_context_features_v1
positions                      15 raw + 15 missing indicators = 30
Official coverage              438 / 438
PIT failures                   0
Determinism                    PASS
```

## 4. Market-X Extended — governed where available

```text
hsi_return_5d                  438 / 438
hsi_return_20d                 438 / 438
market_volatility_20d          438 / 438
market_turnover_20d_mean       438 / 438
recent_ipo_1d_sample_count     438 / 438
recent_ipo_5d_sample_count     438 / 438
recent_ipo_break_rate          244 / 438 available
recent_ipo_return_5d           243 / 438 available
```

Industry remains blocked:

```text
production industry_return_5d    0 / 438
production industry_return_20d   0 / 438
INDUSTRY_MAPPING_PIT_BLOCKED    432 cases
MISSING_INDUSTRY_CLASSIFICATION   6 cases
```

Competition Market Agent can proceed without industry return; missing remains explicit.

## 5. Frozen 5D Outcome — COMPLETE / FROZEN

```text
Official coverage              438
Outcome available              424
Outcome unavailable             14
Development available          354 / 368
Validation available            70 / 70
missing_base_price              12
no_eligible_session              2
Determinism                    PASS
```

## 6. Competition multi-horizon outcome — REQUIRED / NOT YET FROZEN

赛题要求的上市表现窗口：

```text
1D
5D
20D
60D
```

当前 5D 已 frozen；Final Sprint 仍需独立 versioned sidecar：

```text
return_1d          REQUIRED
return_20d         REQUIRED
return_60d         REQUIRED
```

建议同时：

```text
break_flag_1d
significant_drop_5d
max_drawdown_20d
max_drawdown_60d
```

## 7. PR-D Canonical Dataset — COMPLETE / FROZEN

```text
Model-ready                    424
Development                    354
Validation                      70
Schema                         v04_canonical_modeling_dataset_v1
Generation failures              0
Silent drops                     0
Identity mismatch                0
Feature-order drift              0
2025 Blind y accessed           NO
```

Final Sprint 不重写 frozen canonical matrix。

## 8. Oracle readiness

```text
Oracle v2 materialized          98
strict usable                   96
Development / Validation        77 / 19
feature count                  142
evaluation_only               true
production_consumable         false
```

Oracle 继续只用于 evaluation，不进入 production LLM runtime。

## 9. Frozen PR-F readiness

Frozen model results remain complete historically, but PR-H current workspace still lacks the original per-case runtime/handoff.

```text
historical PR-F gate             COMPLETE / FROZEN
product runtime handoff          MISSING in current PR-H workspace
allowed action                   recover original / valid hash-bound handoff
forbidden action                 retrain / reconstruct / retune for UI
```

If unrecovered: `ModelSignal.status = unavailable`.

## 10. LLM runtime readiness

Architecture already contains LLM provider and Legal/Business integration points. Final Sprint still must prove on real cases:

```text
real provider connectivity
Legal structured semantic extraction
Business structured semantic extraction
Evidence scope validation
provider failure degradation
LLM Market interpretation
LLM Final Supervisor
conflict / targeted re-check
```

This is the main runtime capability gap, not a need to redesign the whole framework.

## 11. Competition benchmark readiness

Still required for submission:

```text
Risk benchmark artifact
Evidence benchmark artifact
AI-vs-Offline minimal effect artifact
```

Target metrics:

```text
关键风险要素抽取准确率 >= 80%
关键 Evidence Recall    >= 85%
```

The benchmark should be submission-focused and representative; it does not need to become a new broad research program.

## 12. Trace / product readiness

Current backend already has substantial provenance, but final Competition artifact must make it explicit and consumable:

```text
Agent / Tool / Evidence trace   REQUIRED 100%
Evidence page / bbox Viewer     REQUIRED where source bbox exists
Human Review                    REQUIRED
reasoning logs                  REQUIRED
3–5 stable real IPO cases       REQUIRED
```

## 13. Current source status table

| Source / artifact | Status | Final Sprint use |
| --- | --- | --- |
| Official IPO identity | AVAILABLE 438/438 | identity / split |
| Prospectus corpus | AVAILABLE | Document runtime |
| Production Document-X | FROZEN 438/438 | historical P / PM |
| Market-X Core | FROZEN 438/438 | Market facts |
| HSI Extended | READY 438/438 | Market Agent |
| HKEX turnover | READY 438/438 | Market Agent |
| Recent IPO context | PARTIAL / governed | IPO Heat |
| Industry return | PIT_BLOCKED | remain unavailable |
| 5D Outcome | FROZEN 424/438 | required 5D validation |
| 1D/20D/60D Outcome | REQUIRED / not frozen | D deliverable |
| PR-F per-case handoff | MISSING in current workspace | optional model channel blocker |
| Real LLM provider path | architecture ready / runtime proof needed | B/C/E deliverable |
| Risk/Evidence benchmark | REQUIRED | B/D deliverable |
| Agent trace product | REQUIRED | E deliverable |

## 14. Final competition readiness gaps

```text
B  real LLM Document semantics + benchmark
C  Market Agent / Skills / interpretation
D  1D/20D/60D + PR-F state + evaluation tables
E  LLM Supervisor / conflict / trace / Human Review / product
A  integrated real-case matrix + CI + submission package
```

## 15. Gate state

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
COMPETITION_FINAL_SPRINT  ACTIVE
2025_BLIND_Y              NOT ACCESSED
```
