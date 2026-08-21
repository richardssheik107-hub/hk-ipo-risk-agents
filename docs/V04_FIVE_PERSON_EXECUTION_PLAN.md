# v0.4 五人并行执行计划

> Status: **ACTIVE — PR-A COMPLETE / FROZEN; PR-B NOT STARTED**
> Date: **2026-08-21**
> Strategy: **End-to-End Closed Loop First**  
> Target: **先完成可运行、可审计、可展示的 v0.4 完整闭环，再决定 v0.5+ 优化。**

---

## 1. 计划目标

本计划把当前 v0.4 路线转换成一个适合 **5 人并行开发** 的执行方案。

核心原则不是把 PR-A～PR-H 平均分给五个人，而是：

1. 按稳定的技术边界分工；
2. 尽可能把原本串行的任务提前并行；
3. 每个模块有明确 owner，避免多人同时修改同一核心文件；
4. 所有结果通过统一的 CI、Schema、hash、coverage 和 point-in-time gate 汇合；
5. 先完成 v0.4 闭环，再决定是否重开 Retriever / LLM / Agent 优化。

最终 v0.4 目标：

```text
Prospectus PDF
→ Document Intelligence
→ Production Document X
→ Pre-IPO Market X
→ 5D Outcome Y
→ Model-ready Dataset
→ Baseline + Oracle Diagnostic
→ LightGBM + Explainability
→ Market Agent
→ Final Supervisor
→ Streamlit Full E2E
→ v0.4 Freeze
```

---

# 2. 五人固定角色

## A — Tech Lead / Pipeline

**定位：系统集成、运行编排、质量门禁。**

主要负责：

- PR-A 总负责人；
- `scripts/run_v04_pr_a.py`；
- batch / resume / provenance；
- coverage；
- reproducibility；
- CI / integration；
- 最终合并前的接口和数据一致性检查。

不负责：重新实现 Parser、Retriever、Agent 业务逻辑。

### A 的核心交付

```text
run_v04_pr_a.py
PR-A tests
run manifest
coverage artifact
reproducibility report
integration gate
```

---

## B — Document / Agent

**定位：Production Document Intelligence 质量负责人。**

主要负责：

- 当前 `enhanced_v2` Document Pipeline 审核；
- Parser / Retriever / Financial / Legal / Business Agent / Verifier / Supervisor 的接口确认；
- Production Snapshot / Feature 质量；
- 438-case Production 跑批中的 failure classification；
- Evidence / calculation / page provenance 检查；
- 后续 PR-G 的 Document explanation 接口。

不负责：现在重新做 Retriever V3、Prompt tuning 或 Fine-tuning。

### B 的核心交付

```text
Document pipeline audit
Production failure taxonomy
Document feature QA
Evidence quality report
Document-side integration tests
```

---

## C — Market Data / PIT

**定位：Pre-IPO Market X、数据源和防泄漏负责人。**

主要负责：

- IPO listing / issue structure data；
- IPO EOD / historical context；
- HSI；
- industry benchmark mapping / history；
- total-market turnover；
- Market Feature Builder；
- point-in-time validation；
- Market coverage / missingness；
- 2025 blind data boundary。

这是 v0.4 最重要的独立数据工程线之一，可以在 PR-A 进行时提前启动。

### C 的核心交付

```text
PreListingMarketFeatureBuilder
Market Feature Manifest
Market coverage report
PIT audit
Market data source / provenance record
```

---

## D — Quant / ML Research

**定位：Outcome、Model-ready Dataset、统计建模和实证分析负责人。**

主要负责：

- 5D Outcome policy；
- return / abnormal return / classification target；
- development / validation / blind split；
- Model-ready Dataset；
- Logistic / Ridge baseline；
- M / P / O / PM / OM diagnostic；
- LightGBM；
- SHAP / calibration / ablation / error analysis；
- 最终研究结论。

### D 的核心交付

```text
Outcome Builder
Label Manifest
V04ModelingDataset
Baseline harness
Oracle diagnostic report
LightGBM experiments
Explainability report
```

---

## E — Oracle / Product Integration

**定位：Oracle 旁路、最终 Supervisor 和产品化。**

主要负责：

- Oracle Gold inventory；
- Oracle Document Feature materialization；
- Oracle coverage；
- Streamlit skeleton；
- Final Supervisor；
- Market Agent integration；
- 最终报告；
- Demo / E2E integration。

E 可以在早期就搭建 UI skeleton，但在 PR-F / PR-G 之前不绑定尚未冻结的模型逻辑。

### E 的核心交付

```text
Oracle feature artifacts
Oracle coverage
Streamlit skeleton
Final Supervisor
Final report renderer
E2E demo
```

---

# 3. 当前第一阶段：五个人如何并行

现在不要五个人一起等待 PR-A。

推荐立即形成四条并行线：

```text
                 v0.4 NOW
                    │
      ┌─────────────┼─────────────┐
      ↓             ↓             ↓
   A + B          C / Market    D / Outcome
   PR-A           PR-B          PR-C
      │             │             │
      ↓             ↓             ↓
   Production     Market X       Y
      │             │             │
      └─────────────┬─────────────┘
                    ↓
                   PR-D
                    ↓
                   PR-E
                    ↓
             ┌──────┴──────┐
             ↓             ↓
           PR-F           PR-G
             │             │
             └──────┬──────┘
                    ↓
                   PR-H
```

E 同时承担 Oracle 和 Product Skeleton，因此从第一天开始就有独立工作，不等待 A 完成。

---

# 4. PR-A：Document + Oracle Materialization & Coverage

> Frozen result: Production analysis / snapshot / feature = 438 / 438 / 438，100 维 `v04_document_features_v1`，Production failures = 0，Oracle = 60，`no_reviewed_gold` = 378，A6 determinism = PASS。详见 [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)。

## 4.1 A：Pipeline Lead

### A0

冻结：

- base commit；
- config hash；
- official 438-case manifest hash；
- Document Feature Manifest hash；
- Oracle Feature Manifest hash；
- Python / dependency environment。

### A1

实现：

```text
scripts/run_v04_pr_a.py
```

只做 orchestration，不复制 Agent 逻辑。

必须支持：

```text
--catalog-dir
--data-root
--output-dir
--config
--limit
--case-ids
--resume
--production-only
--oracle-only
```

硬规则：

- 2025 blind fail closed；
- 不覆盖 provenance 不一致的 artifact；
- 单 case failure 不终止 batch；
- failure 必须结构化记录；
- resume 必须基于 hash / provenance。

### A2

先跑 5-case deterministic Development pilot。

验收：

- Production analysis 完成；
- Snapshot materialize；
- Feature vector 生成；
- failure report 完整；
- rerun 可复用；
- hash 一致。

### A3

pilot 通过后跑 2020–2024 全部 438 case。

运行过程中不调模型、不修改风险规则、不读取 2025。

### A5 / A6

统一生成 coverage 和 reproducibility report，并组织 PR-A Gate Review。

---

## 4.2 B：Document / Agent

PR-A 期间 B 不开发新 Agent，而是做：

1. Production pipeline audit；
2. 438-case failure taxonomy；
3. Parser / Retriever / Agent / Verifier / Supervisor failure stage 统计；
4. Snapshot / Feature QA；
5. Evidence / Calculation / page provenance 抽查；
6. 为 A 提供 batch runner 的错误处理需求。

B 必须明确区分：

```text
SUCCESS
PARTIAL
DEGRADED
FAILED
INPUT_ERROR
```

不得把 partial / degraded 自动标成 full success。

---

## 4.3 E：Oracle

并行执行：

```text
index_oracle_gold.py
→ build_oracle_document_features.py
→ Oracle coverage
```

Oracle 必须保留：

- expert annotation provenance；
- effective annotation hash；
- evaluation_only=true；
- 与 Production 完全独立的输入边界。

---

## 4.4 PR-A Gate

PR-A 只有同时满足以下条件才能关闭：

```text
[x] 438 official case 都有明确 coverage status
[x] Production success / partial / failure 均有原因
[x] 2025 未被读取
[x] Production feature hash 可追溯
[x] Oracle coverage 可追溯
[x] Production ∩ Oracle intersection 可计算
[x] 第二次运行 hash / artifact deterministic
[x] CI 全绿
[x] 无公共 Schema 未经批准的变化
```

---

# 5. PR-B：Market-X Core + Governed EOD Store

## Owner

**C 主导，A 提供 pipeline / integration 支持，D 做 feature sanity check。**

## C 要完成

建立：

```text
PreListingMarketFeatureBuilder
```

将 IPO 上市前可获得的信息转换为 Market X。

重点包括：

- IPO structure；
- listing / issue context；
- IPO historical context；
- HSI / broad market；
- industry benchmark；
- total-market turnover；
- point-in-time feature availability。

### 必须验证

对 listing date = T：

```text
所有 Market X data <= T
```

不能使用 T+1 或更晚信息。

## 交付

```text
Market Feature Manifest
Market Feature Builder
Market Coverage Report
PIT Audit Report
```

## 难度

**★★★★★**

## 时间

约 **3–7 个开发日**；数据源或历史覆盖有问题时预留 **1–2 周**。

## 并行

与 PR-A、PR-C **高度并行**。

---

# 6. PR-C：5D Outcome Policy Freeze

## Owner

**D 主导，C 提供 EOD 数据，A 做 schema / reproducibility review。**

## D 要完成

定义：

```text
raw_return_5d
abnormal_return_5d
poor_performer_5d
```

并冻结：

```text
2020–2023 Development
2024 Validation
2025 Blind
```

任何分类阈值只能根据 Development 制定。

## 交付

```text
Outcome Builder
Outcome Manifest
Label QA
Leakage Tests
```

## 难度

**★★★☆☆**

## 时间

约 **1–2 个开发日**。

## 并行

与 PR-A / PR-B **高度并行**。

---

# 7. PR-D：Canonical Model-ready Dataset

## Owner

**D 主导，A 做数据工程支持，B/C/E 分别负责 Document / Market / Oracle QA。**

输入：

```text
Document X
Market X
Outcome Y
```

输出：

```text
V04ModelingDataset
```

每个 case 至少包含：

```text
case_id
stock_code
source_year
split
label_horizon
Document features
Market features
Outcome
provenance
```

## 关键检查

```text
case_id 一一对应
无重复
无 orphan
split 正确
2025 blind
Document / Market feature schema 一致
Outcome horizon 一致
```

## 难度

**★★★★☆**

## 时间

约 **2–4 个开发日**。

---

# 8. PR-E：Baseline + Oracle Diagnostic

## Owner

**D 主导，全员参与解释。**

这是 v0.4 最重要的研究 Gate。

比较：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

核心问题：

> 招股书 Document X 是否提供 Market X 之外的增量预测价值？

以及：

> 如果 Oracle 有效但 Production 较弱，问题是否主要在 Document Pipeline，而不是信号本身？

## 交付

```text
Baseline results
Oracle ceiling report
Production vs Oracle gap
Ablation summary
Validation report
```

## 难度

**★★★★★**

## 时间

约 **3–5 个开发日**。

---

# 9. PR-F：LightGBM + Explainability

## Owner

**D 主导，B/C 提供 feature interpretation，A 负责 experiment reproducibility。**

只有 PR-E 证明 signal 值得继续后，才进入复杂模型。

内容：

```text
LightGBM
SHAP
Feature importance
Calibration
Error analysis
```

重点不是追求复杂，而是回答：

- 哪些 Document risk 最重要？
- 哪些 Market feature 最重要？
- 是否存在明显 feature interaction？
- 模型是否稳定？

## 难度

**★★★★☆**

## 时间

约 **2–4 个开发日**。

---

# 10. PR-G：Market Agent + Final Supervisor

## Owner

**E 主导，B 负责 Document evidence，C 负责 Market explanation，D 提供模型解释。**

将：

```text
Financial Agent
Legal Agent
Business Agent
Document Supervisor
Market Agent
Model prediction
```

统一进入 Final Supervisor。

最终回答：

```text
风险高不高？
为什么？
证据在哪里？
哪个风险贡献最大？
市场环境有什么影响？
模型为什么这么预测？
```

## 难度

**★★★★★**

## 时间

约 **4–7 个开发日**。

---

# 11. PR-H：Streamlit Full E2E + Real-case Demo

## Owner

**E 主导，A 做 backend/integration，B 做 evidence UI，C 做 market UI，D 做 model visualization。**

最终页面：

```text
Upload Prospectus
↓
Document Analysis
↓
Risk Features
↓
Market Features
↓
Prediction
↓
Evidence
↓
Final Supervisor
↓
Final Risk Report
```

至少展示：

- 公司基本信息；
- Financial / Legal / Business risk；
- Market risk；
- Evidence；
- 页码；
- 计算过程；
- 模型预测；
- 主要驱动因素；
- 最终综合结论。

## 难度

**★★★★☆**

## 时间

约 **3–7 个开发日**。

---

# 12. 推荐的并行时间表

## Week 1

```text
A  PR-A0/A1 + tests
B  Document pipeline audit + failure taxonomy
C  Market data acquisition + Market-X prototype
D  5D Outcome + label policy
E  Oracle materialization + Streamlit skeleton
```

目标：五个人全部有独立交付，不等待。

## Week 2

```text
A+B  PR-A2 pilot → PR-A3 438 Production
C    Market-X + PIT audit
D    Outcome QA + Baseline framework
E    Oracle coverage + UI skeleton
```

理想状态：

```text
Production X   READY / RUNNING
Oracle X       READY
Market X       READY / RUNNING
Outcome Y      FROZEN
UI skeleton    READY
```

## Week 3

```text
D  PR-D Model-ready Dataset
D  PR-E Baseline + Oracle Diagnostic
A  Reproducibility / Dataset QA
B  Document error analysis
C  Market error analysis
E  Oracle / explanation integration
```

## Week 4

如果 PR-E 证明 Document signal 有价值：

```text
D  PR-F LightGBM + SHAP
E  PR-G Market Agent + Final Supervisor
A  Integration / reproducibility
B  Evidence explanation
C  Market explanation
```

然后进入：

```text
PR-H Streamlit Full E2E
```

---

# 13. 最快完成路径

5 人并行时，项目不应该是严格串行：

```text
PR-A → PR-B → PR-C → PR-D → PR-E → PR-F → PR-G → PR-H
```

而应该是：

```text
                    ┌── PR-B Market-X ───┐
                    │                     │
PR-A ───────────────┤                     ├── PR-D
                    │                     │
                    └── PR-C Outcome ────┘
                                           ↓
                                          PR-E
                                           ↓
                                          PR-F
                                           ↓
                                  ┌────────┴────────┐
                                  ↓                 ↓
                                PR-G              PR-H
                                  └────────┬────────┘
                                           ↓
                                      v0.4 Freeze
```

PR-B 和 PR-C 可以在 PR-A 运行期间并行推进；E 的 Oracle 和 UI skeleton 也可以提前推进。

---

# 14. 时间与复杂度总表

| Phase | Owner | 难度 | 预计开发时间 | 是否可并行 |
|---|---|---:|---:|---|
| PR-A | A+B+E | ★★★★☆ | 3–6 人日 | 是，内部可拆 |
| PR-B | C | ★★★★★ | 3–7 人日 | 是 |
| PR-C | D | ★★★☆☆ | 1–2 人日 | 是 |
| PR-D | D+A | ★★★★☆ | 2–4 人日 | 部分 |
| PR-E | D+全员 | ★★★★★ | 3–5 人日 | 部分 |
| PR-F | D | ★★★★☆ | 2–4 人日 | 部分 |
| PR-G | E+B+C+D | ★★★★★ | 4–7 人日 | 部分 |
| PR-H | E+A+B+C+D | ★★★★☆ | 3–7 人日 | 是 |

在 5 人稳定投入、数据源没有重大阻塞的情况下，**2–3 周完成一个可展示的 v0.4 是积极但可实现的目标；3–5 周是更稳妥的计划窗口。**

最大不确定性来自：

1. 438-case Production LLM / PDF 跑批；
2. Market-X 历史数据源和 PIT 治理；
3. 真实 case failure 的数量与修复成本。

不要把历史单 case smoke 的耗时直接当成 438-case SLA。

---

# 15. Git / PR 协作规则

五人协作时必须保持：

```text
main
│
├── feat/pr-a-pipeline
├── feat/document-qa
├── feat/market-x
├── feat/outcome-modeling
└── feat/oracle-product
```

原则：

- 每人拥有明确文件 / 模块边界；
- 不直接 force-push main；
- 一个 PR 一个逻辑主题；
- CI 不通过不合并；
- 修改公共 Schema 前必须全员可见；
- 不把生成的大型数据 artifact 提交到 Git；
- 本地绝对路径、API key、2025 blind y 禁止进入 repository；
- 合并前 rebase / sync 最新 main；
- PR description 必须写清输入、输出、验证方式和是否影响 blind / schema。

---

# 16. 每周团队 Gate

## Gate 1 — PR-A

必须得到：

```text
438 coverage
Production X status
Oracle status
Intersection
Reproducibility
```

## Gate 2 — PR-D

必须得到：

```text
Document X
Market X
Outcome Y
Model-ready Dataset
```

## Gate 3 — PR-E

必须回答：

```text
Document 是否有增量价值？
Oracle 上限是多少？
Production 与 Oracle 差距在哪里？
```

## Gate 4 — PR-H

必须完成：

```text
Real prospectus
→ full pipeline
→ prediction
→ evidence
→ final report
```

完成 Gate 4 即认为 **v0.4 End-to-End Closed Loop Complete**。

---

# 17. 什么情况下暂停 / 回滚

不要因为一个失败 case 就重新打开整个 Document Intelligence。

只有出现以下情况才暂停当前冻结边界：

- 数据泄漏；
- public schema 错误；
- provenance 无法追溯；
- Production 结果不可复现；
- 现有 Agent 语义阻断闭环；
- Market-X 无法满足 point-in-time；
- 2025 blind 被意外读取。

普通的：

- Retriever 指标不够高；
- 某些风险召回率不高；
- 某个 Agent prompt 可以更好；
- LLM 还可以 fine-tune；

都不应该阻断 v0.4 闭环。

这些留给 v0.5+。

---

# 18. v0.4 完成定义

当以下链路在真实 case 上完整运行：

```text
Prospectus
→ Document X
→ Market X
→ 5D Y
→ Model-ready Dataset
→ Baseline / LightGBM
→ Market Agent
→ Final Supervisor
→ Streamlit
```

并且：

- 关键结果可追溯；
- 2025 blind 没有泄漏；
- Production / Oracle 边界没有泄漏；
- Dataset 可重建；
- 至少一个真实 case 可以完整 Demo；
- CI 为 GREEN；
- 文档、Schema、运行入口与实际代码一致；

则：

> **v0.4 End-to-End Closed Loop = COMPLETE / FROZEN**。

之后再进入 v0.5：Retriever / LLM / Agent 优化、更多特征、更多实验、blind result analysis 和产品性能优化。
