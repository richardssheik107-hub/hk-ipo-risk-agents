# Documentation Index

> Audit date: **2026-08-25**  
> PR-A–PR-G: **COMPLETE / FROZEN**  
> PR-H: **PARTIAL / BLOCKED**  
> Current execution mode: **5-Day Competition Submission Sprint**

本目录继续采用“少量 active docs + frozen completion records + stable technical references”的维护方式。当前 active plan 已从原 3 周 Competition Hardening 路线切换为五天提交冲刺。

## 1. Source-of-truth hierarchy

发生冲突时：

1. executable contracts / Pydantic / Protocol / validator；
2. `reports/frozen/*.json`；
3. formal completion report / Gate review；
4. current active docs；
5. stable research reference / Git history。

本次五天计划不改写 frozen historical facts。

## 2. Active documents

| Document | Current purpose |
| --- | --- |
| [`ROADMAP.md`](ROADMAP.md) | 五天比赛交付路线、停止项、最终 Gate |
| [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) | 最终产品链与 LLM-first 总策略 |
| [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md) | A/B/C/D/E 每天的并行分工 |
| [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) | 五天详细验收和 submission 计划 |
| [`PROJECT_SPEC.md`](PROJECT_SPEC.md) | 当前比赛版产品范围 / LLM 责任 / trust boundary |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 稳定技术边界；不因 sprint 随意重构 |
| [`DATA_SCHEMA.md`](DATA_SCHEMA.md) | frozen data/model contracts |
| [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) | measured readiness / current data facts |

`UI_DESIGN_REFERENCE_2026-08-24.md` 仅作为参考，不再驱动大规模 UI 探索。

## 3. Current execution chain

```text
Frozen foundation PR-A–PR-G
        ↓
5-Day Competition Sprint
        ↓
Day 1  real LLM Document Intelligence
Day 2  LLM Market + LLM Final Supervisor + controlled re-check
Day 3  3–5 real cases + targeted fixes
Day 4  Evidence / AI Analysis / Agent Trace product integration
Day 5  regression / freeze / submission
        ↓
v0.4.5 COMPETITION_READY if final Gate passes
```

PR-H remains a factual formal Gate. If its frozen PR-F model handoff remains unavailable, PR-H stays blocked and the competition runtime must show `Model unavailable`; the sprint does not fabricate or retrain merely for presentation completeness.

## 4. Current competition priority

The remaining work is judged by functional value, not research volume.

Must improve:

```text
real LLM Legal / Business semantic understanding
Evidence-grounded risk resolution
PIT-safe Market interpretation
LLM Final Supervisor synthesis / conflict / uncertainty
real Agent + LLM trace
3–5 stable real IPO demos
submission reproducibility
```

Deferred:

```text
multi-horizon research
broad feature audit
new model families / tuning
large Retriever research
industry PIT research
large new data acquisition
full benchmark program
story-only product work
```

## 5. Frozen measured facts

```text
Official cases                        438
Production Document-X                 438 / 438, 100 dims
Market-X Core                         438 / 438, 30 positions
5D outcome                            424 / 438
Canonical                             424 = 354 Dev + 70 Val
Oracle v2 strict                      96 = 77 Dev + 19 Val
HSI Extended readiness                438 / 438
HKEX turnover 20D readiness           438 / 438
production industry return              0 / 438, PIT_BLOCKED
2025 Blind y accessed                 NO
```

## 6. Completion / Gate records

Keep immutable as historical evidence:

- `V04_PR_A_COMPLETION_REPORT.md`
- `V04_PR_B_COMPLETION_REPORT.md`
- `V04_PR_C_COMPLETION_REPORT.md`
- `V04_PR_D_COMPLETION_REPORT.md`
- `V04_PR_E_COMPLETION_REPORT.md`
- `V04_PR_F_COMPLETION_REPORT.md`
- `V04_PR_G_COMPLETION_REPORT.md`
- `V04_PR_G_A_GATE_REVIEW.md`
- `V04_PR_H_COMPLETION_REPORT.md`
- `V04_ORACLE_V2_COMPLETION_REPORT.md`

## 7. Stable references

Architecture/schema/data-readiness/research contracts remain valid unless a sprint change explicitly versions an interface. Do not delete frozen governance or research references merely because their experiment is deferred.

## 8. Documentation rule for the sprint

Do not create new long planning/handoff/exploration documents. Put short implementation context in PR bodies/issues. Update only these active docs when a material execution decision changes.

Frozen completion records and `reports/frozen/*.json` remain authoritative for historical claims.
