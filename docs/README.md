# Documentation Index

> Audit date: **2026-08-25**  
> PR-A–PR-G: **COMPLETE / FROZEN**  
> PR-H: **PARTIAL / BLOCKED**  
> Current mode: **Competition Final Sprint — five parallel ownership lanes**

本目录采用“少量 active docs + frozen completion records + stable technical references”的维护方式。当前 active docs 已统一为五人固定责任线，不再按 Day 1/Day 2 形式拆计划。

## 1. Source-of-truth hierarchy

发生冲突时：

1. executable contracts / Pydantic / Protocol / validator；
2. `reports/frozen/*.json`；
3. formal completion report / Gate review；
4. current active docs；
5. stable research reference / Git history。

Active planning 不改写 frozen historical facts。

## 2. Active documents

| Document | Current purpose |
| --- | --- |
| [`ROADMAP.md`](ROADMAP.md) | 当前比赛硬要求、五条并行工作流、最终 Gate |
| [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) | 从现有 baseline 到 Competition Release 的总链路 |
| [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md) | A/B/C/D/E 详细 ownership、依赖与交付 |
| [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) | 赛题要求逐项映射、验收与 submission |
| [`PROJECT_SPEC.md`](PROJECT_SPEC.md) | Competition product scope / LLM responsibility / definition of done |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | LLM + deterministic + Market + Supervisor + Product 边界 |
| [`DATA_SCHEMA.md`](DATA_SCHEMA.md) | frozen baseline 与 competition runtime sidecars/contracts |
| [`COMPETITION_DATA_OVERVIEW.md`](COMPETITION_DATA_OVERVIEW.md) | 赛题数据宇宙、1D/5D/20D/60D 与 PIT 数据要求 |
| [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) | 当前 measured readiness 与缺口 |

`UI_DESIGN_REFERENCE_2026-08-24.md` 只保留为设计参考，不作为 Gate 或开发顺序来源。

## 3. Current execution model

```text
A  Integration / CI / Release / Submission
B  LLM Document Intelligence / Evidence / Benchmark
C  Market Intelligence / Skills / LLM Interpretation
D  Outcome / Model Runtime / Evaluation
E  LLM Final Supervisor / Conflict / Trace / Product
```

五条 lane 并行，A 高频集成。任何工作都必须直接对应赛题硬要求、真实 E2E blocker 或最终 submission artifact。

## 4. Competition hard requirements

```text
关键风险要素抽取准确率      >= 80%
关键 Evidence Recall         >= 85%
Agent / Tool / Evidence trace = 100%
上市首日 / 5D / 20D / 60D    required
可运行原型 / API / UI         required
测试预测表 / 推理日志 / Evidence / 典型案例 required
人机复核能力                  required
```

## 5. Current product target

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial + Legal + Business Agents
→ LLM semantics where appropriate
→ deterministic Calculation / Verifier
→ governed Market Skills + LLM Market Agent
→ Model/Rule auxiliary signals
→ LLM Final Supervisor
→ conflict / targeted re-check / uncertainty
→ Report / Evidence Viewer / Agent Trace / Human Review
```

## 6. Frozen measured facts

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

## 7. Historical records

Completion reports、Gate reviews、research contracts 与 `reports/frozen/*.json` 保持历史不可变。不要为了新的五人计划重写过去阶段结果。

## 8. Documentation rule

不再新增长篇探索性计划、handoff 或 story 文档。实现细节优先写 PR body / issue；只有 materially changed execution contract 才更新 active docs。
