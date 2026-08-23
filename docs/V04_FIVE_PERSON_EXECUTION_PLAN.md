# v0.4 五人执行计划

> Status: **ACTIVE — PR-A/PR-B/PR-C COMPLETE / FROZEN; PR-D FORMAL MATERIALIZATION NEXT**
> Date: **2026-08-23**
> Strategy: **End-to-End Closed Loop First, Competition Hardening Second**  
> Governance: **正式 milestone / Gate / mainline merge 严格顺序推进；准备性工作允许并行。**

---

## 1. 计划目标

本计划把 v0.4 路线转换成适合 **5 人协作** 的执行方案，同时避免把“可以提前准备”误解成“正式 Gate 可以并行越过”。

最终 baseline E2E 目标：

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
→ Baseline E2E Freeze
```

随后进入赛题专项强化：

```text
Competition Scope Lock
→ 1D / 20D / 60D Outcome Extension（5D remains primary）
→ Competition-specific Document Risk Hardening
→ Market Sentiment + Competition Skills
→ Multi-Agent Conflict Resolution / Traceability
→ Evidence Screenshot / Human Review / Competition Report
→ Competition Evaluation / Case Study
→ Submission Freeze
```

### 正式治理原则

当前正式 milestone / Gate / mainline merge 顺序固定为：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
→ PR-B Market-X Core + Governed EOD Store            COMPLETE / FROZEN
→ PR-C 5D Outcome Policy Freeze                      COMPLETE / FROZEN
→ PR-D Canonical Model-ready Dataset                 ACTIVE / FORMAL MATERIALIZATION NEXT
→ PR-E Baseline + Oracle Diagnostic
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + Real-case Demo
→ v0.4.3 Baseline E2E Freeze
→ CH-0..CH-6 Competition Hardening
→ v0.4.5 Competition Submission Freeze
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

- PR-A 历史总负责人；
- orchestration / batch / resume / provenance；
- coverage / reproducibility；
- CI / integration；
- 各正式 Gate 的接口与数据一致性检查；
- 后续 PR-C～PR-H 的 pipeline / integration 支持。

不负责：重新实现 Parser、Retriever、Agent 的业务逻辑，也不代替 D 决定 Outcome / threshold 等研究 policy。

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

PR-B Owner 任务已完成并冻结在 `main`。当前支持 PR-C governed materialization / EOD provenance；Extended authoritative-source research 可并行，但不得用错误 proxy 阻断或污染 Core。

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

PR-C governed full materialization、Development-only q25、438 targets、determinism、freeze manifest 与 A final sign-off 已完成。当前正式任务是 PR-D canonical materialization；正式 PR-E 仍必须采用 time-aware evaluation protocol，而不是随机时间混合 CV。

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

# 4. PR-B：Market-X Core + Governed EOD Store — COMPLETE / FROZEN ON MAIN

## Owner

**C 主导，A 提供 pipeline / integration 支持，D 做 feature sanity check。**

## 目标

建立受 point-in-time 治理的 Market-X Core，把 IPO 上市前真正可获得的信息转换为可重建的市场上下文 X。

重点：

- IPO structure；
- listing / issue context；
- prior-IPO historical context；
- feature missingness；
- source / version / checksum / PIT provenance。

HSI / authoritative industry benchmark / total-market turnover 属于独立 Market-X Extended source families，当前仍显式 missing，不是 PR-B Core 必须伪造的输入。

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

PR-B 已 PASS 并完成 mainline publication；当前正式 Gate 已推进到 PR-C。

---

# 5. PR-C：5D Outcome Policy Freeze — COMPLETE / FROZEN

## Owner

**D 主导，C 提供 governed EOD 数据，A 做 schema / reproducibility / blind-Gate review。**

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

当前已完成：policy / schema / implementation / A static audit / 424-14 Gate correction。正式 materialization 目标固定为：

```text
Official cases                 438
5D target available            424
5D target unavailable           14
Development available          354
Validation available             70
missing_base_price              12
no_eligible_session              2
```

### 正式 Gate 交付

```text
real Development-only q25
438 target artifacts
438 determinism checks / 0 mismatch
Outcome Manifest
Label QA
Leakage Tests
small freeze manifest
A final sign-off
```

PR-C 已 PASS；PR-D formal materialization 现已解除前置阻塞并成为下一正式 Gate。

---

# 6. PR-D：Canonical Model-ready Dataset

## Owner

**D 主导，A 做数据工程 / contract integration 支持，B/C/E 分别负责 Document / Market / Oracle QA。**

输入：

```text
Document X
Market-X Core
optional Market-X Extended
Outcome Y
```

输出：

```text
versioned canonical V04 modeling dataset
```

必须检查：

```text
case_id 一一对应
无重复
无 orphan
split 正确
2025 blind policy 正确
Document / Market feature schema 一致
Core / Extended feature group order 显式版本化
Outcome horizon 一致
provenance 可重建
```

PR-D engineering prep 已在 `main`；正式 materialization 只接受新的 424 / 14 PR-C contract，预期 Full Production model-ready = 424、Development = 354、Validation = 70。

不得静默把新的 30-position Core 插入现有历史 120-position Extended join。

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

PR-E 是是否重开 v0.5 Retriever / LLM / Agent 优化的重要研究 Gate。正式 Development evaluation 必须 time-aware；Oracle coverage 需在新增 annotations 后重新审计。

---

# 8. PR-F：LightGBM + Explainability

## Owner

**D 主导，B/C 提供 feature interpretation，A 负责 experiment reproducibility。**

只有 PR-E 完整、可复现后正式进入复杂模型。

内容：

```text
LightGBM
SHAP
Feature importance
Calibration assessment
Ablation
Error analysis
```

模型输出在未完成校准前只能表述为 `score` / prediction，不得无依据称为真实概率。

---

# 9. PR-G：Market Agent + Final Supervisor

## Owner

**E 主导，A 负责 cross-module integration，B 负责 Document evidence，C 负责 Market explanation，D 提供模型解释。**

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

A-side contract 已冻结以下边界：MarketContext 不得冒充 RiskAgent；Final Supervisor 不得创造 Evidence / Risk；Model score 不得冒充 Evidence 或 calibrated probability。

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

PR-H 的含义是先获得稳定 **baseline E2E**。赛题专项增强在其后进行，不要求在 PR-C～PR-H 期间提前完成全部比赛增强功能。

---

# 11. 准备性并行规则

正式 Gate 严格串行不等于五个人必须空等。

当前状态：PR-A / PR-B / PR-C frozen；PR-D formal materialization next。当前允许的并行准备包括：

```text
A  PR-D integration Gate + downstream provenance/reproducibility review
B  Document explanation / downstream interface QA
C  PR-D governed source support + Extended authoritative-source research
D  PR-D formal materialization + PR-E/F method preparation（不越过正式 Gate）
E  Oracle re-audit preparation + Final Supervisor / UI skeleton reconciliation
```

赛题 CH-0..CH-6 的正式开发在 PR-H baseline E2E 后启动；当前只允许文档、benchmark 设计、数据源调研等不改变当前 Gate 的 preparation。

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

```text
[x] Governed Market source record
[x] Market Feature Manifest
[x] Market-X coverage 438 / 438
[x] PIT audit PASS
[x] No post-listing leakage
[x] Determinism 438 checked / 0 mismatches
[x] 2025 blind y not accessed
[x] PR #80 / #81 mainline publication and documentation closure
```

## Gate PR-C — COMPLETE / FROZEN

必须得到：

```text
438 coverage rows
424 available / 14 unavailable
354 Development / 70 Validation available
12 missing_base_price / 2 no_eligible_session
real Development-only q25
Validation did not fit threshold
438 target artifacts
438 determinism / 0 mismatch
no 2025 blind y
freeze manifest
A final sign-off
```

## Gate PR-D

必须得到：

```text
Document X
Market-X Core
optional Market-X Extended
Outcome Y
424 Canonical model-ready rows
354 Development / 70 Validation
14 explicit exclusions
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

并且至少 3–5 个真实 IPO E2E demo 通过。

---

# 14. 什么情况下暂停 / 解冻

不要因为普通性能改进空间就重新打开冻结的 Document Intelligence 或 PR-B Market-X Core。

只有出现以下情况才申请暂停当前主线或解冻边界：

- 数据泄漏；
- public schema 错误；
- provenance 无法追溯；
- Production 结果不可复现；
- 现有 Agent 语义错误真正阻断闭环；
- Market-X 无法满足 point-in-time；
- PR-B frozen artifact 与 source provenance 不一致；
- 2025 blind 被意外读取。

普通的：

- Retriever 指标还能更高；
- 某些风险召回率还能提高；
- 某个 Agent prompt 可以更好；
- LLM 可以 fine-tune；
- Extended source 仍缺但 Core 已受治理；

都不应阻断 baseline E2E。PR-H 完成后，赛题明确要求的专项能力按 CH-0..CH-6 增量开发；更广泛的 Retriever / LLM / Agent 研究仍由 PR-E Oracle gap 或冻结比赛指标决定。

---

# 15. Baseline v0.4 完成定义

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

> **v0.4.3 Baseline End-to-End Closed Loop = COMPLETE / FROZEN**。

这不是比赛工作的终点；随后进入 Competition Hardening。

---

# 16. Competition Hardening — 五人后续执行计划

完整 requirement → component → owner → metric → deliverable → Gate 见 [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)。本节只冻结五人执行顺序。

## CH-0 — Scope Lock / Acceptance Matrix

**A 主导，全员确认。**

逐项映射赛题全部任务、技术指标、交付物，不允许存在无人负责的 requirement。

## CH-1 — 1D / 20D / 60D Outcome Extension

**D 主导，C/A/E 支持。**

在 frozen 5D primary target 之外增加 1D / 20D / 60D 真实表现验证；不得反向修改 5D threshold。

## CH-2 — Competition-specific Document Risk Hardening

**B 主导，D/A/E 支持。**

专项覆盖：

```text
现金消耗
对赌 / 赎回条款
关联交易
客户 / 供应商集中度
核心管线进度
文本粉饰度高的原文切片与可解释 diagnostic
```

先测当前能力，再只对不达标部分做最小范围 enhancement。

## CH-3 — Market Sentiment + Competition Skills

**C 主导数据/PIT，E 主导 Agent integration。**

正式补齐：

```text
Market Sentiment Agent
LongDocumentRetrievalSkill
ComparableValuationSkill
CashBurnSkill
SentimentHeatSkill
```

可选 HSI / industry benchmark / total-market turnover 只有在 governed authoritative source 可得时才接入。

## CH-4 — Multi-Agent Conflict Resolution / Traceability

**E 主导，A 做 trace contract / integration。**

实现：

```text
conflict detection
→ targeted evidence re-check
→ Skill / Verifier challenge
→ arbitration
→ resolved / needs_review
```

Agent 角色、推理步骤、工具调用、Evidence 来源追踪率目标 = 100%。

## CH-5 — Evidence Screenshot / Human Review / Competition Report

**E 主导，B/C/D/A 分别负责 Evidence / Market / Model / service。**

利用现有 page+bbox 完成 PDF 页码、段落、表格高亮/截图，并形成《IPO 风险穿透预警报告》与 reviewer audit trail。

## CH-6 — Competition Evaluation / Submission Freeze

**A 负责最终 Gate，全员交付。**

必须正式达到或记录：

```text
关键风险要素抽取准确率 >= 80%
关键 Evidence 片段召回率 >= 85%
Agent / Tool / Evidence traceability = 100%
1D / 5D / 20D / 60D validation table
5D primary risk warning + explanation
可运行 Streamlit / API
测试集预测结果表
多智能体推理 / tool / verifier logs
关键 Evidence
典型案例报告
环境配置 / run scripts
3–5 real demos
```

只有 CH-6 PASS 才标记：

> **v0.4.5 COMPETITION_READY / SUBMISSION FROZEN**。

---

# 17. Competition Hardening 后的研究优化

赛题专项补齐不等于无边界重新做 AI 研究：

```text
Evidence recall < 85%
→ 定向 Retriever / evidence targeting 修复

Risk accuracy < 80% 且 Evidence 正确
→ Agent / Verifier / Skill 语义修复

Oracle strong / Production weak
→ 有充分证据进入更大规模 Retriever / LLM / Agent 优化

指标已达标
→ 不为了技术炫技强行 Fine-tuning / LoRA
```

历史 Retriever Locked 10 已消费，任何新增调优必须使用新的受治理 evaluation / holdout。
