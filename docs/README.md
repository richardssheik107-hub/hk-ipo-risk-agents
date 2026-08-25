# Documentation Index

> Audit date: **2026-08-25**  
> PR-A–PR-G: **COMPLETE / FROZEN**  
> Historical PR-H formal freeze: **PARTIAL / BLOCKED**  
> v0.4.5 competition runtime: **IMPLEMENTED / HARDENING**  
> Current mode: **Competition closure — real-case validation + metrics + submission**

本目录采用“少量 active docs + frozen completion records + stable technical references”的维护方式。Active docs 描述当前比赛状态；frozen completion reports 与 `reports/frozen/*.json` 只记录历史事实，不为了新开发结果回写。

## 1. Source-of-truth hierarchy

发生冲突时：

1. executable contracts / Pydantic / Protocol / validator；
2. `reports/frozen/*.json`；
3. formal completion report / Gate review；
4. current active docs；
5. stable research reference / Git history。

## 2. Active documents

| Document | Current purpose |
| --- | --- |
| [`V0.4_RELEASE_ACCEPTANCE.md`](V0.4_RELEASE_ACCEPTANCE.md) | 当前 v0.4.0 / v0.4.5 验收、已关闭项与剩余 blocker |
| [`ROADMAP.md`](ROADMAP.md) | 从“继续开发”切换到 competition closure 的最短路径 |
| [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md) | A/B/C/D/E ownership 与依赖边界 |
| [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) | 从 baseline 到 Competition Release 的总链路 |
| [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) | 赛题要求逐项映射、验收与 submission |
| [`PROJECT_SPEC.md`](PROJECT_SPEC.md) | Competition product scope / LLM responsibility / definition of done |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | LLM + deterministic + Market + Supervisor + Product 边界 |
| [`DATA_SCHEMA.md`](DATA_SCHEMA.md) | frozen baseline 与 competition runtime sidecars/contracts |
| [`COMPETITION_DATA_OVERVIEW.md`](COMPETITION_DATA_OVERVIEW.md) | 数据宇宙、1D/5D/20D/60D 与 PIT 数据要求 |
| [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) | measured readiness 与数据缺口 |

Historical implementation evidence such as [`V04_ROLE_E_COMPLETION_REPORT.md`](V04_ROLE_E_COMPLETION_REPORT.md) stays as a completion record and is not a live roadmap.

## 3. Current implemented competition chain

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial / Legal / Business Agents
→ deterministic Calculation + Verifier
→ governed Market-X
→ IPO Heat / Market Regime Skills
→ Market Intelligence + bounded LLM interpretation
→ Rule + optional frozen Model channel
→ Conflict detection
→ bounded targeted re-check
→ LLM Final Supervisor
→ Agent / Tool / Evidence Trace
→ Evidence Viewer / Human Review / Final Report
```

PR #126 closed formal Market Intelligence runtime wiring. PR #128 implemented the E-lane LLM Final Supervisor, conflict/re-check, trace and product surface. These are no longer roadmap-only features.

## 4. Current hardening issue closed in code

A real 2410.HK v0.4.5 AI smoke exposed a Core-only Market Intelligence integration defect:

```text
stage       market_intelligence
code        component_failure
message     'NoneType' object has no attribute 'missing_reason'
recoverable true
```

Root cause: a Market Skill treated “expected feature absent from `observations`” as though a `MarketObservation` object existed. The contract now distinguishes:

```text
explicit unavailable observation  → preserve its governed missing_reason
absent optional source feature     → source_unavailable
available observation              → consume only its numeric governed value
```

This applies to both `IPOHeatSkill` and `MarketRegimeSkill`. Core-only Market-X therefore degrades to deterministic `INSUFFICIENT_DATA` where necessary instead of raising `component_failure`. No Extended value is imputed and no threshold is changed.

Real-case re-run is still required after pulling the fix; code-level closure is not the same as case-level acceptance.

## 5. Competition hard requirements

```text
关键风险要素抽取准确率       >= 80%
关键 Evidence Recall          >= 85%
Agent / Tool / Evidence trace = 100%
上市首日 / 5D / 20D / 60D    required
可运行原型 / API / UI         required
测试预测表 / 推理日志 / Evidence / 典型案例 required
人机复核能力                  required
```

## 6. Current closure status

```text
Remote LLM provider boundary          IMPLEMENTED
Legal / Business LLM path             IMPLEMENTED, benchmark pending
Market Agent runtime wiring           COMPLETE
Market missing-feature safety         FIXED IN CODE, real-case rerun pending
Conflict / controlled re-check        COMPLETE
LLM Final Supervisor implementation   COMPLETE, final online case validation pending
Agent Trace                            COMPLETE; E real case measured 1.0
Evidence Viewer / Human Review        COMPLETE
3+ stable real E2E cases              OPEN
1D / 5D / 20D / 60D package          OPEN
Risk / Evidence benchmark             OPEN
Frozen PR-F per-case handoff           OPEN / explicit unavailable allowed
Submission package                    OPEN
2025 Blind y accessed                 NO
```

## 7. Frozen measured facts

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

## 8. Documentation rule

- 不再新增按日期拆分的计划文档。
- 不用 story 文档替代测试、artifact 或真实 E2E 证据。
- 只有 execution contract、Gate 状态或 materially changed integration behavior 变化时更新 active docs。
- 真实运行失败必须写成已知缺口；代码修复后必须区分“regression test 通过”和“真实案例已复跑通过”。
- Frozen completion report 不回写为新的 current status；Current status 统一收敛到本索引、`ROADMAP.md` 与 `V0.4_RELEASE_ACCEPTANCE.md`。
