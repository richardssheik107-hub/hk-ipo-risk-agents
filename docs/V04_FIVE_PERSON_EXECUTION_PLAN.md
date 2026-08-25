# v0.4 → Competition Submission 五人执行计划

> Status snapshot: **2026-08-25**  
> PR-A–PR-G: **COMPLETE / FROZEN**  
> PR-H: **PARTIAL / BLOCKED — CURRENT FORMAL GATE**  
> End state: **v0.4.5 COMPETITION_READY + reproducible submission package**

本文件只回答“谁负责什么、何时交付、依赖谁”。比赛阶段详细技术范围见 [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)。

## 1. 固定角色

| Role | Position | Owns | Does not own |
| --- | --- | --- | --- |
| A | Tech Lead / Integration | architecture boundary、GitHub、CI、Gate、release、submission | 不替 B/C/D 重做领域算法 |
| B | Document Intelligence | risk extraction、Retriever、Evidence、Calculation、Document benchmark | 不因 AUC 低直接重写全部 Agent |
| C | Market Intelligence / Data | Market-X、PIT、IPO Heat、market/outcome data | 不使用未来数据或无治理 proxy |
| D | Quant / ML | multi-horizon、feature audit、model、SHAP、ablation、statistics | 不用 2024 反复调参，不重建 frozen PR-F 解阻 UI |
| E | Multi-Agent / Product | Final Supervisor、conflict、trace、Evidence Viewer、competition UI/demo | 不在展示层创造事实或模型结果 |

## 2. 协同模型

五个人不串行排队，而是四条 lane 并行、A 负责合流：

```text
B  Document Benchmark / Evidence ──────┐
C  Market / Outcome / PIT ─────────────┼→ D Quant Evaluation ─┐
B  Targeted Document fixes ────────────┘                     ├→ E Supervisor / Product
C  Market interpretation ────────────────────────────────────┘

A = interface + branch/PR + CI + integration + release
```

每 2–3 天统一一次：

```text
merge latest main
→ full tests
→ governed real-case smoke
→ schema/provenance check
→ internal checkpoint
```

每日同步只回答：

```text
昨天完成什么？
今天交付什么？
需要谁的输入？
是否阻塞 main / Gate？
```

## 3. Phase 0 — v0.4.3 收尾（Day 1–3）

### A — Gate owner

- 锁定 PR-H acceptance matrix；
- 审核 runtime Market / Model contracts；
- 汇总 B/C/D/E 的 3–5 case 输入；
- full CI、determinism、provenance、Blind audit；
- PR-H PASS 后发布 v0.4.3 baseline freeze。

**交付：** PR-H Gate record、3–5 case matrix、v0.4.3 release evidence。

### B — Real Document QA

- 选至少 3、目标 3–5 个真实 2024 IPO；
- 检查 PDF、RiskItem、Evidence、Calculation、page、bbox、Verifier；
- 为 E 提供每 case 的关键风险与已知限制。

**交付：** `case_id → prospectus → risk/evidence QA` 清单。

### C — Governed Market QA

- 验证 demo cases 的 Market-X Core；
- 接入可用 HSI / HKEX turnover Extended；
- 检查 PIT cutoff、provenance、missing semantics；
- industry mapping 继续 `PIT_BLOCKED`。

**交付：** per-case Market readiness + provenance。

### D — Frozen PR-F Runtime Support

- 恢复原 frozen runtime 或已生成 sanitized handoff；
- 为选定 cases 输出 per-case score、signed top SHAP、run/model identity、checksum；
- 不 retrain / reconstruct / retune。

**交付：** hash-bound minimal product handoff。

### E — E2E owner

- 运行 `PDF → Document → Market → Model → Rule → Final Supervisor → Report → Streamlit`；
- 记录失败 stage；
- 验证 Evidence 引用、score semantics、uncertainty、report consistency。

**交付：** 3–5 case runnable demo matrix。

## 4. CH-0 — Scorecard Lock（Day 3–4）

**A 主导，全员签字式确认。**

- B 锁定 Document benchmark risk set / metrics；
- C 锁定 Market/Outcome source policy；
- D 锁定 multi-horizon evaluation protocol；
- E 锁定 conflict/trace/demo acceptance；
- A 将所有 requirement → owner → metric → evidence artifact 映射完整。

之后没有 Scorecard 对应项的“大功能”默认不进入主线。

## 5. CH-1 / CH-2 / CH-3 并行（Day 4–12）

### B — CH-2 Document Benchmark

第一轮：

```text
Precision / Recall / F1
Evidence Recall / Evidence Precision
by risk_code
```

第二轮：error attribution：

```text
retrieval / parser-table / semantic / calculation / rule / gold
```

第三轮：只修最差 2–3 类，并提供 Before/After。

**依赖 D：** 每轮修复后检查 downstream representation / prediction 是否变化。  
**依赖 E：** 把代表错例做成可展示 case。

### C — CH-1 data + CH-3 Market

并行建立：

```text
1D / 20D / 60D outcome extensions
market-adjusted returns
20D / 60D drawdown / volatility
IPO Heat
recent IPO break/performance
HSI / turnover / activity
PIT-safe comparable context
```

输出必须同时有 numeric value + source/provenance + availability/missing reason。

**依赖 D：** 判断新增 Market features 是否有稳定增量。  
**依赖 E：** 转换成 Market Environment，而不是只显示 DataFrame。

### D — Feature / Horizon / Model Diagnosis

先做 Production Document-X audit：

```text
missing / zero / variance / prevalence / redundancy / year drift
```

按预先业务定义构造 compact `P-Core`，不能看 2024 后选 feature。

随后固定跑：

```text
M / P / P-Core / PM / O / OM
× 1D / 5D / 20D / 60D
```

输出 metrics + bootstrap CI + ablation + error analysis。

**目的：** 定位信号是死在 Document extraction、feature representation、5D horizon、Market data，还是任务本身。

### E — Case Diagnosis / Product Skeleton

这一阶段不无边界美化 UI，先建立：

- correct / FP / FN / Document-strong / Market-strong / conflict cases；
- `PDF → Evidence → Risk → Feature → Market → Model → Supervisor` case trace；
- Evidence Viewer / Agent Trace 所需接口骨架。

## 6. CH-4 — Multi-Agent Conflict（Day 10–14）

### E 主导

实现：

```text
Conflict Detection
→ Evidence Re-check
→ targeted retrieval / Skill
→ Verifier Challenge
→ Supervisor Arbitration
```

至少 3 个真实 conflict case。

### B

负责 Document-side re-check / Evidence。

### C

负责 Market-side evidence / provenance。

### A

冻结 trace / conflict interface，并审核 unresolved uncertainty 不被静默抹平。

### D

只在 conflict 涉及 model signal 时提供 score semantics / SHAP / uncertainty，不让模型替代事实。

## 7. CH-5 — Competition Product（Day 10–16）

### E 主导五个最终工作区

```text
Risk Command Center
Risk Map
Evidence Viewer
Market & Model
Agent Trace
```

### B → E

`Risk / Evidence / page / bbox / Calculation / benchmark status`

### C → E

`Market Environment / reason / provenance / missingness`

### D → E

`score semantics / SHAP / multi-horizon / uncertainty`

### A → E

`runtime state / trace / provenance / release identity`

UI 只展示受控真实结果，不通过 presentation layer 伪造 unavailable channel。

## 8. Competition Beta（Day 15–18）

A 组织 Beta Gate，五人必须同时交付：

| Role | Beta deliverable |
| --- | --- |
| A | integration + CI + reproducibility checkpoint |
| B | Document benchmark v1 + targeted fixes |
| C | Competition Market v1 + PIT audit |
| D | multi-horizon result v1 + ablation/SHAP |
| E | Evidence Viewer + Agent Trace + 3–5 demo cases |

Beta 后进入 feature freeze 倒计时，只允许修明确 bug、关键 benchmark 缺口和 demo blockers。

## 9. CH-6 — Competition Freeze（Day 18–21）

### A

- 全量 test / integration / real-case regression；
- determinism / provenance / secret/path/raw-data scan；
- release manifest / tag；
- 最终 acceptance matrix。

### B

冻结 Document Benchmark、per-risk metrics、Evidence metrics、error attribution。

### C

冻结 Competition Market feature set 与 PIT/missingness audit。

### D

冻结 1D/5D/20D/60D result、ablation、SHAP、bootstrap、error analysis、limitations。

### E

冻结 Final Supervisor、real conflicts、Evidence Viewer、Agent Trace、Competition UI。

PASS：`v0.4.5 COMPETITION_READY`。

## 10. Submission 分工

### A — Submission Owner

```text
submission/
├── README
├── source
├── configs
├── demo
├── evaluation
├── reports
├── screenshots
└── runbook
```

保证 `clone → install → run` 可复现，并负责最终提交版本身份。

### B

Document benchmark、Risk/Evidence examples、Before/After case material。

### C

Market methodology、PIT explanation、Market feature/case material。

### D

Model/multi-horizon tables、ablation、SHAP、error analysis、limitations。

### E

Final Streamlit、screenshots、3–5 star cases、demo flow、presentation script。

## 11. 答辩 ownership

```text
A  系统架构 / 治理 / E2E / reproducibility
B  Document Intelligence / Evidence / benchmark
C  Market Intelligence / PIT / IPO Heat
D  Model / multi-horizon / empirical results
E  Multi-Agent / conflict / Supervisor / live demo
```

## 12. 三类明星案例

1. **Document Case** — Risk → Evidence → Calculation → PDF bbox（B + E）；
2. **Conflict Case** — Agent disagreement → re-check → Verifier → Supervisor（E 主导）；
3. **Market / Prediction Case** — Market Environment → SHAP → multi-horizon（C + D）。

A 负责三套案例的稳定复现。

## 13. 协作与停止规则

- 已冻结 PR-A–PR-F 不因结果不好或换机器而变回未完成；
- 所有新增工作从最新 `main` 建短分支，单 PR 单主题；
- owner 不得在别人 lane 中用临时 hack 绕过 protected contract；
- 2025 Blind y 不得提前访问；
- 2024 Validation 不得被重新当 tuning set；
- 每个实验必须有 hypothesis / protocol / result / route decision；
- 不进行无限模型调参或无 benchmark 的全量 Agent 重写；
- 大型 runtime / licensed raw data / secrets 不进入 Git。
