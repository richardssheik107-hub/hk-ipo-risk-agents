# Roadmap

> Status snapshot: **2026-08-23**
> 当前唯一主线：**End-to-End Closed Loop First**。  
> PR-A：**COMPLETE / FROZEN**；PR-B：**COMPLETE / FROZEN ON MAIN**。  
> PR-C：**COMPLETE / FROZEN**。
> PR-D：**COMPLETE / FROZEN**。
> 当前正式 Gate：**PR-E — READY / FORMAL BASELINE NEXT / NOT STARTED**。
> Oracle v2：**FREEZE CANDIDATE / READY FOR A FINAL SIGN-OFF**；PR-E 训练仍未开始。
> Competition strategy：**先完成 PR-C → PR-H baseline E2E，再进入赛题专项强化；赛题要求不提前打断当前 Gate。**

## 版本路线

| 版本 / Track | 目标 | 状态 |
| --- | --- | --- |
| v0.2.0 | 真实文档纵向切片与数据治理 | RELEASED / HISTORICAL |
| v0.3.0 | Financial / Legal / Business 多 Agent 文档风险分析 | RELEASED / FROZEN |
| Retriever V3 research | BM25 / Table / LambdaMART / Locked evaluation | MERGED / FROZEN |
| Oracle Document Modeling | Expert Gold 上限特征 + baseline foundations | MERGED / EVALUATION-ONLY |
| v0.4-MVP | Document Risk → Market Outcome 完整闭环 | **ACTIVE** |
| v0.4.1 | LightGBM + Explainability | PLANNED |
| v0.4.2 | Market Agent + Final Supervisor | PLANNED |
| v0.4.3 | Streamlit Full E2E Demo / Baseline E2E Freeze | PLANNED |
| v0.4.4 | Competition Hardening：赛题专项能力与指标补齐 | **PLANNED AFTER PR-H** |
| v0.4.5 | Competition Submission Freeze：完整验收与提交包 | PLANNED |
| v0.5.0 | Retriever / LLM / Agent / Verifier 研究级优化 | DEFERRED / ORACLE-GAP-OR-METRIC-DEPENDENT |
| v0.6.0 | 正式评测、消融、失败分析、Blind Test | PLANNED |
| v1.0.0 | 最终发布 / 比赛 / 作品集版本 | PLANNED |

## 已完成并冻结

### v0.3 Document Intelligence

当前稳定基线已具备真实 PDF Parser、稳定 Production Retriever、Financial/Legal/Business Agents、8 类正式文档风险、deterministic Skills/Calculations、Specialized Verifier、Document Supervisor、Service、Streamlit、Markdown/JSON 报告和 Mock/offline/optional-AI 降级路径。

**CL-1 已完成。** v0.4 不再要求先提高 Retriever 指标。

### Retriever research

Retriever V3、BM25、table-aware lane、LambdaMART LTR 与最终 Locked evaluation 已进入主线并冻结。历史 Locked 10 已消费；未来若重启研究必须建立新的 unseen/external/temporal holdout。

### Oracle Document Modeling

Oracle track 已合入主线，定位为 evaluation ceiling / error attribution，不是生产路径。Oracle 不能进入 Production runtime，也不能读取 2025 blind y。Oracle v2 已完成独立版本物化与复现（98 materialized / 96 strict usable / 77 Dev / 19 Val），当前是待 A 最终签核的 freeze candidate，尚未宣称 frozen on main。

### PR-A Document + Oracle Materialization & Coverage

PR-A 已完成并冻结。正式物化 source revision：

```text
13e0281f5e65a970caaf1255e56d08597e1ead70
```

冻结结果：

```text
official 2020–2024 cohort     438 / 438
Production analysis           438 / 438
authoritative snapshots       438 / 438
Production Document-X         438 / 438
feature schema                v04_document_features_v1 / 100 dims
Production failures           0
silent drops                  0
Oracle materialized           60
no_reviewed_gold              378
Production ∩ Oracle           60
A6 determinism                438 checked / 0 mismatches / PASS
2025 blind access             NO
```

Frozen records:

- [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)
- [`../reports/frozen/v04_pr_a_document_materialization_manifest.json`](../reports/frozen/v04_pr_a_document_materialization_manifest.json)

## 当前真实 readiness

以下数字区分 PR-B EOD/session coverage 与 PR-C 可执行 5D outcome coverage；两者不得混用。

| 项目 | 当前状态 |
| --- | --- |
| Official 2020–2024 IPO universe | 438 / 438 available |
| Local prospectus coverage | 438 / 438 |
| PR-B EOD/session-ready coverage | 432 / 438 |
| PR-C 5D outcome available | 424 / 438 |
| PR-C 5D outcome unavailable | 14 / 438 = 12 missing_base_price + 2 no_eligible_session |
| PR-C Development available | 354 / 368 |
| PR-C Validation available | 70 / 70 |
| Authoritative snapshots | 438 / 438 |
| Production Document-X | 438 / 438, 100 dimensions |
| Oracle Document-X | immutable v1: 60 materialized / 55 Dev + 0 Val；v2 freeze candidate: 98 materialized / 96 strict usable = 77 Dev + 19 Val，待 A 最终签核 |
| Production failures / silent drops | 0 / 0 |
| PR-B Core code/tests | COMPLETE / FROZEN |
| PR-B Core real coverage | 438 / 438 materialized; 0 failed; 0 silent drops |
| HSI history | MISSING — Extended |
| Industry benchmark mapping / history | MISSING — Extended |
| Total-market turnover | MISSING — Extended |
| PR-B Gate | PASS / COMPLETE / FROZEN |
| PR-C Gate | PASS / COMPLETE / FROZEN |
| Full Model-ready data gate | PASS / 424 = 354 Development + 70 Validation |
| Competition Hardening | PLANNED AFTER PR-H BASELINE E2E |

## PR-B frozen boundary

### Market-X Core

Current Core contract:

```text
v04_ipo_market_context_features_v1
ipo_market_context_policy_v1
15 raw prior-IPO context features
+ 15 adjacent missing indicators
= 30 positions
```

Frozen implementation:

```text
src/ipo_risk/market/ipo_market_context_features.py
scripts/build_v04_ipo_eod_store.py
scripts/run_v04_pr_b.py
```

Governance already implemented and validated:

- target cohort selected by authoritative `official_listed_date.year`, not `source_year`；
- governed EOD filter retains `OBJECT_ID` provenance；
- `S_DQ_AMOUNT` cannot become total-market turnover；
- target IPO post-listing data cannot enter target X；
- prior outcome is usable only after its target session occurred strictly before target listing；
- 2025 blind y is rejected；
- one-case failure remains visible in coverage；
- resume is conflict-safe；
- deterministic rebuild passed 438 / 438 with 0 mismatches。

### Market-X Extended

Existing frozen 20-position reference-market contract remains separate:

```text
v04_prelisting_market_features_v1
v04_market_features_v1
```

HSI / authoritative industry benchmark / HKEX total-market turnover are still missing. These are explicit Extended limitations, **not inputs that PR-B Core is allowed to fake**。

## Closed Loop execution state

| Phase / PR | 内容 | 状态 | 进入下一阶段的关键条件 |
| --- | --- | --- | --- |
| CL-1 | Freeze Current Document Intelligence | **COMPLETE / FROZEN** | 已完成 |
| CL-2 / PR-A | Document + Oracle Materialization & Coverage | **COMPLETE / FROZEN** | 已完成 |
| CL-3 / PR-B | Market-X Core + Governed EOD Store | **COMPLETE / FROZEN ON MAIN** | 已完成 |
| CL-4 / PR-C | Freeze 5D Outcome Policy | **COMPLETE / FROZEN** | governed full run + q25 + 438 targets + determinism + freeze manifest + A final sign-off complete |
| CL-5 / PR-D | Canonical Model-ready Dataset | **COMPLETE / FROZEN** | 438 → 424 model-ready + 14 exclusions; 354 Dev / 70 Val; deterministic resume PASS |
| CL-6 / PR-E | Baseline + Oracle Diagnostic | **READY / FORMAL BASELINE NEXT / NOT STARTED** | consume frozen PR-D + time-aware evaluation protocol；Oracle v2 freeze candidate 待 A 最终签核 |
| CL-7 / PR-F | LightGBM + Explainability | PREPARATION ONLY | PR-E formal baseline complete and reproducible |
| CL-8/9 / PR-G | Market Agent + Final Supervisor | CONTRACT PREPARATION ONLY | frozen model output contract + protected-interface review |
| CL-10 / PR-H | Streamlit Full E2E + 3–5 Real IPO Demo | UI PREPARATION ONLY | PDF → Final Report complete |
| CH-0..CH-6 | Competition Hardening + Submission Freeze | **PLANNED AFTER PR-H** | baseline E2E frozen；then complete every competition requirement and metric |

## PR-B completion evidence

```text
official coverage             438 / 438
Core materialized             438 / 438
failed / silent drops         0 / 0
PIT failures                  0
Development / Validation      368 / 70
determinism                   438 checked / 0 mismatches / PASS
coverage hash                 768b027676453d02d0cb5db8599acffbc2d58d7f5dc6e373bd9f4ddb305c974e
2025 blind y accessed         NO
```

Frozen evidence and reproducibility references:

- [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md)
- [`../reports/frozen/v04_pr_b_market_x_core_manifest.json`](../reports/frozen/v04_pr_b_market_x_core_manifest.json)
- [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)

## 后续严格顺序

正式 milestone / Gate / mainline merge 顺序固定为：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
PR-B  Market-X Core + Governed EOD Store             COMPLETE / FROZEN
PR-C  5D Outcome Policy Freeze                       COMPLETE / FROZEN
PR-D  Canonical Model-ready Dataset                  COMPLETE / FROZEN
PR-E  Baseline + Oracle Diagnostic                   READY / FORMAL BASELINE NEXT / NOT STARTED
PR-F  LightGBM + Explainability
PR-G  Market Agent + Final Supervisor
PR-H  Streamlit Full E2E + Real-case Demo
↓
v0.4.3 Baseline E2E Freeze
↓
CH-0 Competition Scope Lock / Acceptance Matrix
CH-1 1D / 20D / 60D Outcome Extension（5D remains primary）
CH-2 Competition-specific Document Risk Hardening
CH-3 Market Sentiment + Competition Skills
CH-4 Multi-Agent Conflict Resolution + 100% Traceability
CH-5 Evidence Screenshot + Human Review + Competition Report
CH-6 Competition Evaluation + Case Study + Submission Freeze
↓
v0.4.5 COMPETITION_READY
```

每个 PR / CH Gate 必须范围单一、CI/测试真实通过、manifest/report 可重复、不提交大型 runtime 数据、不虚构 readiness 数字。

完整赛题 requirement → component → owner → metric → deliverable 映射见 [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)。

## 正式建模比较

PR-D / PR-E 至少冻结：

```text
M   = Market-only
P   = Production Document-only
O   = Oracle Document-only
PM  = Production Document + Market
OM  = Oracle Document + Market
```

Production 与 Oracle 比较必须使用相同 cohort、split、target、preprocessing 和 model family。

PR-D 的 Core-first canonical contract 已作为 engineering preparation 合入主线。正式 materialization 必须先通过 `v04_pr_d_input_binding_v1`，同时绑定 PR-A/PR-B/PR-C frozen manifest identity、三路 438-case bulk aggregate 和实际 artifact contents；30-position Market-X Core 与 optional 20-position Extended contract 保持显式分离。Oracle v1 仅为历史 snapshot，正式 PR-E 前按 `V04_ORACLE_REFRESH_GOVERNANCE.md` 另行冻结 v2。

## 时间切分

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2024 用于冻结方案的正式 validation/model-family comparison，不允许反复调参后继续称 untouched validation。2025 在 feature/target/model policy 冻结前不得用于调参，Oracle 同样禁止读取 2025 blind y。Competition Hardening 也不自动授权打开 2025 y。

## 当前禁止主线化的工作

在 PR-E Oracle diagnostic 出来前，不重新把以下内容拉回主线：

- Retriever 调参；
- LLM Reranker；
- Fine-tuning / LoRA；
- 大规模 Prompt 重构；
- 新专业 Agent；
- 深度学习市场模型；
- 大规模 UI 重构。

PR-H baseline E2E 完成后，允许为了赛题明确要求做**最小范围专项强化**；是否进入大规模 Retriever / LLM / Agent 研究仍由 Oracle gap 或冻结比赛指标决定。

## Competition Hardening 完整范围

赛题专项阶段必须覆盖：

```text
1D / 5D / 20D / 60D 真实表现验证（5D primary）
标准财务 + 非标隐性风险
现金消耗 / 对赌赎回 / 关联交易 / 客户供应商集中度 / 核心管线
文本粉饰度原文切片与可解释 diagnostic
法务合规 + 财务穿透 + 市场情绪 + 总控决策 Agent
长文检索 + 同行估值 + 现金消耗 + 情绪热度 Skills
Agent 冲突检测 → 查证 → verification / arbitration
风险抽取准确率 >= 80%
关键 Evidence recall >= 85%
Agent / Tool / Evidence traceability = 100%
PDF 页码 / 段落 / bbox 截图定位
人机协同复核
测试集预测表 + 推理日志 + Evidence + 典型案例报告
可运行 Streamlit / API / batch submission package
```

这些工作全部放在当前 baseline E2E 跑通之后，不是 PR-C 当前 Gate 的前置条件。

## 当前文档入口

- 总执行计划：[`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
- 五人执行与角色边界：[`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md)
- 赛题强化与提交总计划：[`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)
- PR-C A-side Gate audit：[`V04_PR_C_A_GATE_AUDIT.md`](V04_PR_C_A_GATE_AUDIT.md)
- Role-A integration Gate handoff：[`V04_ROLE_A_INTEGRATION_GATE_HANDOFF.md`](V04_ROLE_A_INTEGRATION_GATE_HANDOFF.md)
- 当前规格：[`PROJECT_SPEC.md`](PROJECT_SPEC.md)
- 当前架构：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- Schema / modeling contracts：[`DATA_SCHEMA.md`](DATA_SCHEMA.md)
- 数据 readiness：[`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)
- PR-B 冻结报告：[`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md)
- PR-B frozen acceptance / reproducibility：[`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)
- Oracle：[`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md)

`V04_ROLE_A_CODEX_HANDOFF.md` 与 `V04_ROLE_A_CROSS_TEAM_PREP.md` 为历史审计记录，不再是当前执行入口。
