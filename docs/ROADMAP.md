# Roadmap

> Status snapshot: **2026-08-24**
> Current formal Gate: **PR-G — A review passed; local freeze materialization pending**
> Next Gate preparation: **PR-H — Streamlit Full E2E + 3–5 real IPO demo — UNBLOCKED**
> Strategy: **End-to-End Closed Loop First, Competition Hardening Second**

## 1. Current state

| Phase | Status | Frozen / active result |
| --- | --- | --- |
| v0.3 Document Intelligence | COMPLETE / FROZEN | real PDF → Evidence → Agents → Verifier → Supervisor |
| PR-A Document materialization | COMPLETE / FROZEN | 438/438 Production Document-X, 100 dims |
| PR-B Market-X Core | COMPLETE / FROZEN | 438/438, 30 positions, PIT audited |
| PR-C 5D Outcome | COMPLETE / FROZEN | 424 available / 14 explicit unavailable |
| PR-D Canonical Dataset | COMPLETE / FROZEN | 424 = 354 Development + 70 Validation |
| Oracle v2 | COMPLETE / FROZEN | 98 materialized / 96 strict usable = 77 Dev + 19 Val |
| PR-E Baseline + Oracle Diagnostic | COMPLETE / FROZEN | 48 formal results; reproducibility and Blind guard passed |
| PR-F LightGBM + Explainability | COMPLETE / FROZEN | 8 results, 16 models, SHAP/calibration/ablation/error analysis |
| PR-G Market Agent + Final Supervisor | **A GATE REVIEW PASS / FREEZE PENDING** | implementation merged; real PDF 13-section path attested; local freeze manifest still required |
| PR-H Streamlit Full E2E | **PREPARATION UNBLOCKED** | runtime Market-X + PR-F case-score handoff are preflight items |
| CH-0..CH-6 Competition Hardening | PLANNED | starts after PR-H baseline E2E |

## 2. Current measured data anchors

```text
Official 2020–2024 universe           438
Production Document-X                 438 / 438
Production feature width              100
Market-X Core                         438 / 438
Market Core width                      30
5D outcome available                  424 / 438
5D outcome unavailable                 14
  missing_base_price                   12
  no_eligible_session                   2
Canonical model-ready                 424
Development / Validation              354 / 70
Oracle v1                             historical immutable: 60 materialized
Oracle v2                             98 materialized / 96 strict usable
Oracle v2 Development / Validation     77 / 19
2025 Blind y accessed                 NO
```

Market-X Extended 已接入 governed CSMAR HSI daily close；438 / 438 官方 case 的两项 HSI return 与 20-session volatility 已通过 PIT readiness。authoritative industry benchmark mapping/history 与 HK total-market turnover 仍缺；这些是 Extended limitations，不重开 PR-B，也不阻塞当前 Core baseline。

## 3. Frozen PR-E / PR-F findings

PR-E 正式比较：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

Production / Oracle 比较已使用相同 cohort、split、target、preprocessing、model family。

核心解释量：

```text
Production Increment     = PM - M
Document Signal Ceiling  = OM - M
Pipeline Gap              = OM - PM
```

Development evaluation 使用 time-aware protocol：

```text
train 2020       → evaluate 2021
train 2020–2021  → evaluate 2022
train 2020–2022  → evaluate 2023
```

正式 Validation：

```text
fit 2020–2023 Development
→ evaluate untouched 2024 Validation
```

PR-E 正式运行未使用 random/shuffled time-mixing CV，也未访问 2025 Blind y。2024 Validation 的分类增量为 `PM-M ROC-AUC -0.0157`、`OM-M ROC-AUC -0.0571`；Oracle Validation 仅 19 例，应解释为不稳定而不是“无信号”。

PR-F frozen LightGBM 进一步得到：

```text
Full Production 2024
M   ROC-AUC 0.4246
P   ROC-AUC 0.5000
PM  ROC-AUC 0.4246
```

PM 与 M 在 frozen tree policy 下预测完全等价，Production Document 100 维特征未获得 split / gain / SHAP 使用。Oracle `OM-M ROC-AUC = -0.0143`，95% paired-bootstrap interval `[-0.3171, 0.2917]`。这是当前 target / feature / sample / model 条件下的正式失败与不稳定发现，不是“招股书本身无价值”的证明，也不能通过查看 2024 后反转分数、反复调参或重写口径来修饰。

## 4. PR-G A review decision

PR #104 已将 Market Context、frozen PR-F evidence adapter、Final Supervisor、v0.4 13-section report 与 opt-in wiring 合入 main。PR #104 head 的 `tests` 与 `expert-annotation-phase2` CI 均成功，完成报告记录了一份 706 页真实招股书的 `status=completed` 闭环与 Evidence 引用解析。

A 的正式审阅结论见 [`V04_PR_G_A_GATE_REVIEW.md`](V04_PR_G_A_GATE_REVIEW.md)：

```text
PR-G implementation / contract review     PASS
PR-G local freeze manifest materialization REQUIRED_LOCAL_ACTION
PR-H preparation                           UNBLOCKED
```

A 同时裁定：

- runtime market 不把受控 `PreListingMarketFeatureSnapshot` 有损降级成 v0.2 `MarketSnapshot` 并冒充 PR-B lineage；PR-H 应建立 governed runtime path；
- PR-F 完整 runtime/model bulk 继续不进 Git；PR-H 通过 `pr_f_run_dir` 消费 checksum + frozen hash 绑定的最小本地 handoff；
- PR-G 引入的结构化 `MarketObservation` / `ModelDriver` protected-interface 变更接受；
- stale PR-B/PR-F UI blocking-gate wording 归 PR-H 清理。

PR-G 仍差一个必须在本地完成的机械冻结动作：用真实 prospectus/runtime 运行 `scripts/build_v04_pr_g_manifest.py`，由 A 校验并提交最终 `reports/frozen` manifest。远程审阅不得猜测本地 prospectus hash 或 final-supervision content hash。

## 5. Post-PR-F strategic decision

PR-F 结果不触发主线回滚。v0.4 继续严格完成 PR-G / PR-H，把研究组件变成稳定产品闭环；Competition Hardening 再按直接 benchmark 定向增强。

当前采用“两条腿”策略：

```text
Risk Intelligence / Auditability
→ 风险抽取质量
→ Evidence / Calculation / page / bbox
→ Verifier / conflict / human review

Market Warning / Predictive Validation
→ Market context / sentiment
→ governed model score + SHAP + uncertainty
→ 1D / 5D / 20D / 60D validation
```

PR-G / PR-H 的 Gate 不要求把 5D AUC 调高。它们要求：正确消费 frozen score、保持 `uncalibrated_model_score` 语义、可追溯 Evidence、明确 uncertainty，并完成真实 PDF → Final Report 闭环。

## 6. Strict formal sequence

```text
PR-A  COMPLETE / FROZEN
→ PR-B COMPLETE / FROZEN
→ PR-C COMPLETE / FROZEN
→ PR-D COMPLETE / FROZEN
→ PR-E COMPLETE / FROZEN
→ PR-F LightGBM + Explainability COMPLETE / FROZEN
→ PR-G implementation REVIEW PASS
→ PR-G local freeze manifest FINALIZE
→ PR-H Streamlit Full E2E + 3–5 real IPO demo
→ v0.4.3 Baseline E2E Freeze
→ CH-0 Competition Scope Lock
→ CH-1 Multi-horizon outcomes
→ CH-2 Competition Document Risk Hardening
→ CH-3 Market Sentiment + Competition Skills
→ CH-4 Conflict Resolution + Traceability
→ CH-5 Evidence Screenshot + Human Review
→ CH-6 Competition Evaluation + Submission Freeze
→ v0.4.5 COMPETITION_READY
```

## 7. Competition improvement logic

Competition Hardening 的直接硬目标是：

```text
关键风险要素抽取准确率           >= 80%
关键 Evidence recall            >= 85%
Agent / Tool / Evidence trace   = 100%
```

预测表现继续真实报告，但不通过 2024 Validation 事后优化来制造更高分。增强路线按以下证据决定：

- CH-1：验证结构性 Document 风险是否在 20D / 60D 比 5D 更有价值；
- CH-2：按风险类别直接测 Precision / Recall / F1 / Evidence Recall；只有失败类别才进入 targeted enhancement；
- 如果 error attribution 指向语义理解，再引入 Hybrid Retrieval / LLM semantic layer，而不是无差别重跑 438 PDF；
- CH-3：短期 1D / 5D 预测提升优先研究 point-in-time IPO heat、近期破发表现、同行业 IPO context、liquidity/activity，以及取得 authoritative source 后的 HSI / industry / turnover；
- CH-4 / CH-5：把多 Agent 冲突、Evidence trace、截图和人工复核做成可展示、可审计能力。

## 8. What is intentionally not reopened now

当前 PR-E / PR-F 没有验证出稳定 Oracle ceiling，因此既不能据此宣布“Document 无信号”，也不能据此直接启动大规模 LLM 重构。以下工作不作为 PR-G / PR-H 前置条件：

- Retriever tuning；
- LLM Reranker；
- Fine-tuning / LoRA；
- 大规模 Prompt 重写；
- 新专业 Agent；
- 深度模型市场预测；
- 无边界 UI 重构；
- 根据 2024 结果反转预测方向或继续调参。

Document Pipeline 是否重开研究，由 CH-2 的直接风险抽取 benchmark + error attribution 决定；Market 侧增强由 CH-3 的 point-in-time 数据可得性和多 horizon 结果决定。

## 9. Version targets

```text
v0.4.3  Baseline E2E Freeze
v0.4.5  Competition Submission Freeze
v0.5.0  Retriever / LLM / Agent research only if direct benchmarks justify it
```

当前详细数据事实见 [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)，当前任务分工见 [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md)。
