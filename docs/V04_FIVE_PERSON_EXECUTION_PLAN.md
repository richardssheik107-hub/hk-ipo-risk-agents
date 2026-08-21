# v0.4 五人执行计划

> Status: **ACTIVE — PR-A/PR-B COMPLETE / FROZEN; PR-C NEXT / NOT STARTED**
> Date: **2026-08-21**
> Strategy: **End-to-End Closed Loop First**  
> Governance: **正式 milestone / Gate / mainline merge 严格顺序推进；准备性工作允许并行。**

---

## 1. 计划目标

本计划把 v0.4 路线转换成适合 **5 人协作** 的执行方案，同时避免把“可以提前准备”误解成“正式 Gate 可以并行越过”。

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

### 正式治理原则

正式 milestone / Gate / mainline merge 顺序固定为：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
→ PR-B Market-X Core + Governed EOD Store            COMPLETE / FROZEN
→ PR-C 5D Outcome Policy Freeze                      NEXT / NOT STARTED
→ PR-D Canonical Model-ready Dataset
→ PR-E Baseline + Oracle Diagnostic
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + Real-case Demo
→ v0.4 Freeze
```

**允许并行的是准备性工作，不是正式 Gate。**

准备性工作可以包括：

- 数据源调研；
- 接口草案；
- 本地实验；
- 测试夹具；
- 文档准备；
- UI skeleton；
- 不改变冻结边界的分析脚本。

但准备工作：

- 不得被标记为后续正式 milestone 已开始 / 已通过；
- 不得越过前置 Gate 合并到 `main`；
- 不得读取或利用不应提前使用的 2025 blind outcome；
- 不得修改已冻结的 Document Intelligence 逻辑来“顺便优化”。

---

# 2. 五人固定角色

## A — Tech Lead / Pipeline

**定位：系统集成、运行编排、质量门禁、跨阶段一致性。**

主要负责：

- PR-A 总负责人；
- orchestration / batch / resume / provenance；
- coverage / reproducibility；
- CI / integration；
- 各正式 Gate 的接口与数据一致性检查；
- 后续 PR-B～PR-H 的 pipeline / integration 支持。

不负责：重新实现 Parser、Retriever、Agent 的业务逻辑。

### A 的核心交付

```text
canonical orchestration
run manifest / provenance
coverage / reproducibility
integration tests
Gate review
cross-module contract checks
```

---

## B — Document / Agent

**定位：Production Document Intelligence 质量负责人。**

主要负责：

- Parser / Retriever / Financial / Legal / Business Agent / Verifier / Supervisor 接口与质量；
- Evidence / Calculation / page provenance QA；
- Document feature 解释；
- 后续 PR-G 的 Document explanation 接口。

当前边界：

- v0.3 / PR-A Document Intelligence 已冻结；
- 不因普通召回率或 prompt 改进空间重开主线；
- 只有数据泄漏、公共 Schema 错误、不可复现或闭环阻断才允许申请解冻修复。

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

PR-B Owner 任务已完成并冻结。PR-C 为下一正式里程碑，但尚未启动。

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

PR-C 前可以做 preparation，但正式 Outcome policy 只有 PR-B Gate 后才进入正式冻结流程。

---

## E — Oracle / Product Integration

**定位：Oracle 旁路、最终 Supervisor 和产品化。**

主要负责：

- Oracle Gold / Oracle Document Feature 研究旁路；
- Final Supervisor；
- Market Agent integration；
- 最终报告；
- Streamlit / Demo / E2E integration。

Oracle 永久保持 `evaluation_only`，不得进入 Production X。

UI skeleton 可以提前准备，但不得绑定尚未冻结的 Market / Model 逻辑并作为正式 E2E Gate 通过。

---

# 3. 当前状态

## PR-A — COMPLETE / FROZEN

PR-A 冻结结果：

```text
Official 2020–2024 cases       438
Production analysis            438 / 438
Authoritative snapshots        438 / 438
Production Document-X          438 / 438
Feature schema                 v04_document_features_v1
Feature dimension              100
Production failures            0
Silent drops                   0
Oracle materialized            60
No reviewed Gold               378
Production ∩ Oracle            60
2025 blind access              NO
A6 checked                     438
A6 mismatches                  0
A6 determinism                 PASS
```

Document materialization source revision：

```text
13e0281f5e65a970caaf1255e56d08597e1ead70
```

详细冻结记录：

- [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)
- [`../reports/frozen/v04_pr_a_document_materialization_manifest.json`](../reports/frozen/v04_pr_a_document_materialization_manifest.json)

PR-A A0–A6 已全部完成：

```text
A0  execution context / hashes       DONE
A1  canonical thin CLI + tests       DONE
A2  deterministic real pilot         DONE
A3  full 438 Production              DONE
A4  Oracle materialization           DONE
A5  unified coverage                 DONE
A6  full determinism                 DONE
```

---

# 4. PR-B：Market-X Core + Governed EOD Store — COMPLETE / FROZEN

## Owner

**C 主导，A 提供 pipeline / integration 支持，D 做 feature sanity check。**

## 目标

建立受 point-in-time 治理的：

```text
PreListingMarketFeatureBuilder
```

把 IPO 上市前真正可获得的信息转换为 Market X。

重点：

- IPO structure；
- listing / issue context；
- prior-IPO historical context；
- HSI / broad market；
- authoritative industry benchmark；
- total-market turnover；
- feature missingness；
- source / version / checksum / PIT provenance。

### 硬 Gate

对 listing date = T：

```text
所有 Market X 原始信息必须在 T 时点可得
```

不得静默使用：

- T+1 或更晚数据；
- 不等价 proxy；
- 未受治理的 HSI / industry mapping / turnover；
- 2025 blind outcome。

### 交付

```text
Market Feature Manifest
Market Feature Builder
Governed EOD/source record
Market Coverage Report
PIT Audit Report
```

PR-B 已 PASS；PR-C 是下一正式里程碑，但仍为 **NOT STARTED**。

---

# 5. PR-C：5D Outcome Policy Freeze

## Owner

**D 主导，C 提供 governed EOD 数据，A 做 schema / reproducibility review。**

定义并冻结：

```text
raw_return_5d
abnormal_return_5d
poor_performer_5d
```

时间治理：

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

分类阈值只能根据 Development 制定。

### 交付

```text
Outcome Builder
Outcome Manifest
Label QA
Leakage Tests
```

PR-C PASS 后才正式进入 PR-D。

---

# 6. PR-D：Canonical Model-ready Dataset

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

必须检查：

```text
case_id 一一对应
无重复
无 orphan
split 正确
2025 blind policy 正确
Document / Market feature schema 一致
Outcome horizon 一致
provenance 可重建
```

---

# 7. PR-E：Baseline + Oracle Diagnostic

## Owner

**D 主导，全员参与解释。**

正式比较：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

核心问题：

> Production Document X 是否提供 Market X 之外的增量预测价值？

以及：

> 如果 Oracle 有效而 Production 较弱，差距是否主要来自 Document Pipeline？

PR-E 是是否重开 v0.5 Retriever / LLM / Agent 优化的重要研究 Gate。

---

# 8. PR-F：LightGBM + Explainability

## Owner

**D 主导，B/C 提供 feature interpretation，A 负责 experiment reproducibility。**

只有 PR-E 证明 signal 值得继续后，才正式进入复杂模型。

内容：

```text
LightGBM
SHAP
Feature importance
Calibration
Error analysis
```

---

# 9. PR-G：Market Agent + Final Supervisor

## Owner

**E 主导，B 负责 Document evidence，C 负责 Market explanation，D 提供模型解释。**

统一：

```text
Financial Agent
Legal Agent
Business Agent
Document Supervisor
Market Agent
Model prediction
→ Final Supervisor
```

最终输出必须同时回答：

- 风险结论；
- Document Evidence；
- 页码 / Calculation；
- Market context；
- 模型驱动因素；
- 不确定性与缺失状态。

---

# 10. PR-H：Streamlit Full E2E + Real-case Demo

## Owner

**E 主导，A 做 backend/integration，B 做 evidence UI，C 做 market UI，D 做 model visualization。**

最终页面链路：

```text
Upload Prospectus
↓
Document Analysis
↓
Document Risk Features
↓
Market Features
↓
Prediction
↓
Evidence / Explainability
↓
Final Supervisor
↓
Final Risk Report
```

至少完成 3–5 个真实 IPO 的完整 E2E Demo。

---

# 11. 准备性并行规则

正式 Gate 严格串行不等于五个人必须空等。

PR-B 已完成并处于发布审查阶段。PR-C 尚未正式启动；在获得独立任务授权前，只允许不冻结 policy 的准备性工作：

```text
A  PR-B release / integration / reproducibility audit
B  Document explanation / downstream interface QA
C  governed EOD / Market-X Core frozen-source support
D  PR-C outcome methodology preparation（不冻结正式 policy）
E  Product / Final Supervisor / UI skeleton preparation（不绑定未冻结模型）
```

同理，未来每个阶段都允许做**不会越过当前 Gate**的准备。

判断标准：

> 如果一项工作失败或被推翻，会不会改变当前正式 Gate 的冻结结论？

- 如果会：它属于正式 milestone，应按顺序进入；
- 如果不会：可以作为 preparation 并行。

---

# 12. Git / PR 协作规则

原则：

- 一个 PR 一个正式逻辑主题；
- 当前正式 Gate 合并后再推进下一正式 Gate；
- CI 不通过不合并；
- 修改公共 Schema 前必须全员可见；
- 不把生成的大型 runtime artifact 或 PDF 提交到普通 Git；
- 本地绝对路径、API key、Token、环境 secret 禁止进入 repository；
- 2025 blind outcome 禁止在 policy freeze 前进入开发链；
- PR description 必须写清输入、输出、验证方式、provenance 与 blind/schema 影响；
- 不 force-push `main`；
- 多 worker 不得共享会发生覆盖的 runtime output directory。

---

# 13. Gate Checklist

## Gate PR-A — COMPLETE

```text
[x] 438 official cases 全部进入 Coverage
[x] 438 / 438 Production Document-X
[x] 60 Oracle / 378 no_reviewed_gold
[x] 0 Production failure
[x] 0 silent drop
[x] 2025 未读取
[x] Feature / Snapshot provenance 可追溯
[x] A6 determinism PASS
[x] CI green
```

## Gate PR-B — COMPLETE / FROZEN

已完成：

```text
[x] Governed Market source record
[x] Market Feature Manifest
[x] Market-X coverage 438 / 438
[x] PIT audit PASS
[x] No post-listing leakage
[x] Determinism 438 checked / 0 mismatches
[x] 2025 blind y not accessed
```

## Gate PR-C

必须得到：

```text
Frozen 5D outcome policy
Development-only threshold policy
Label manifest
Leakage tests
```

## Gate PR-D

必须得到：

```text
Document X
Market X
Outcome Y
Canonical model-ready dataset
Dataset provenance / rebuild path
```

## Gate PR-E

必须回答：

```text
Document 是否有增量价值？
Oracle 上限是多少？
Production 与 Oracle 差距在哪里？
```

## Gate PR-H

必须完成：

```text
Real prospectus
→ full pipeline
→ prediction
→ evidence
→ final report
```

---

# 14. 什么情况下暂停 / 解冻

不要因为普通性能改进空间就重新打开冻结的 Document Intelligence。

只有出现以下情况才申请暂停当前主线或解冻边界：

- 数据泄漏；
- public schema 错误；
- provenance 无法追溯；
- Production 结果不可复现；
- 现有 Agent 语义错误真正阻断闭环；
- Market-X 无法满足 point-in-time；
- 2025 blind 被意外读取。

普通的：

- Retriever 指标还能更高；
- 某些风险召回率还能提高；
- 某个 Agent prompt 可以更好；
- LLM 可以 fine-tune；

都不应阻断 v0.4 闭环，留给 PR-E diagnostic 后的 v0.5+ 决策。

---

# 15. v0.4 完成定义

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
- 至少 3–5 个真实 case 可以完整 Demo；
- CI 为 GREEN；
- 文档、Schema、运行入口与实际代码一致；

则：

> **v0.4 End-to-End Closed Loop = COMPLETE / FROZEN**。

之后再依据 Oracle diagnostic 决定是否进入 v0.5 Retriever / LLM / Agent 优化。
