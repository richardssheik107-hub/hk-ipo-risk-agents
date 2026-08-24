# 港股 IPO 风险预警赛题强化与提交总计划

> Status: **PLANNED — START ONLY AFTER PR-H BASELINE E2E FREEZE**  
> Audit date: **2026-08-23**  
> Current baseline Gate: **PR-G — Market Agent + Final Supervisor**  
> Competition: **第五届中国研究生金融科技创新大赛 — 东吴证券“基于多智能体协同的港股 IPO 招股书解析与上市后风险预警探索”**

## 1. Why competition hardening comes later

PR-A / PR-B / PR-C / PR-D / Oracle v2 / PR-E / PR-F 已冻结，当前正式主线为：

```text
PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + real-case demo
→ v0.4.3 Baseline E2E Freeze
→ CH-0..CH-6 Competition Hardening
→ v0.4.5 Competition Submission Freeze
```

赛题强化是稳定 baseline 的增量层，不重写已经冻结的 PR-A-F provenance，不破坏 2025 Blind 治理，也不为了补功能提前跳过当前 Gate。

PR-F 的 2024 预测结果较弱：Full Production `M ROC-AUC = 0.4246`、`P = 0.5000`、`PM = 0.4246`，且 PM 与 M 在 frozen LightGBM 下预测等价；Oracle 19-case Validation 的 `OM-M ROC-AUC = -0.0143` 且 95% bootstrap interval 跨零。该结果必须作为诚实 baseline 保存，不允许通过看过 2024 后反转 score、反复调参或挑选口径来“修漂亮”。Competition Hardening 的任务不是掩盖这个结果，而是通过直接风险 benchmark、多 horizon、Market Sentiment、冲突治理和产品审计能力把系统真正做强。

## 2. Competition strategy after PR-F

比赛版本采用“两条腿”策略：

### A. Risk Intelligence / Auditability

```text
Prospectus
→ risk extraction
→ Evidence / Calculation / page / bbox
→ Verifier
→ conflict handling
→ human review
→ auditable Final Supervisor output
```

这条线直接对应赛题的长文档、多智能体、风险穿透、证据链和可解释要求，不依赖 5D AUC 才成立。

### B. Market Warning / Predictive Validation

```text
Market context / sentiment
+ governed model score
+ SHAP / uncertainty
+ 1D / 5D / 20D / 60D outcomes
→ explainable warning
```

5D 继续保留为 frozen primary target，但不预设结构性 Document 风险必须在 5D 最强。CH-1 将正式检验更长 horizon；CH-3 将把短期预测增强重点放在 point-in-time IPO heat、近期破发/5D 表现、同行业 IPO context、liquidity/activity 和 authoritative market benchmark 上。

## 3. Competition acceptance scope

最终版本必须逐项覆盖：

### Document risk / anti-hallucination

- 数百页港股招股书 PDF；
- 标准财务指标；
- 现金消耗 / cash runway；
- 对赌 / 赎回；
- 关联交易；
- 客户 / 供应商集中度；
- 核心管线进度；
- 文本粉饰度 / disclosure softening diagnostic；
- 每个正式风险绑定真实 Evidence / page / bbox；
- 数值结论通过 deterministic Skill。

### Multi-agent collaboration

正式角色语义至少覆盖：

```text
Financial / 财务穿透
Legal / 法务合规
Business
Market Sentiment
Final Supervisor / 总控决策
```

Agent 冲突不能被静默抹平，需要：

```text
conflict detection
→ evidence re-check
→ targeted retrieval / Skill check
→ verifier challenge
→ supervisor arbitration
→ resolved / unresolved
```

### Explainable warning report

最终系统应支持：

- 单家 / 批量 IPO 风险穿透报告；
- Document Evidence 精确页码与 bbox；
- 市场环境；
- 模型分数、score semantics、calibration status；
- 模型驱动因素；
- Evidence screenshot / highlight；
- human-in-the-loop reviewer notes / audit trail；
- Streamlit / API / batch 运行路径。

## 4. Formal competition metrics

最终必须真实测量：

```text
关键风险要素抽取准确率           >= 80%
关键 Evidence recall            >= 85%
Agent / Tool / Evidence trace   = 100%
逻辑解释有效性                  expert or governed review protocol
```

业务验证至少覆盖：

```text
1D
5D   ← primary frozen baseline
20D
60D
```

5D frozen PR-C policy 不因新增 horizon 被反向修改；1D / 20D / 60D 独立 versioned。

预测结果需要完整报告 ROC-AUC / PR-AUC / Brier / regression metrics / uncertainty，但本计划不人为规定一个事后选择的 5D AUC 门槛。任何新增模型选择和阈值规则必须只使用允许的 Development protocol；2024 frozen Validation 不重新变成调参集。

## 5. CH-0 — Competition Scope Lock

建立 machine-readable + human-readable acceptance matrix：

```text
requirement_id
requirement
current_component
owner
status
metric_or_gate
evidence_artifact
blocking_issue
```

额外冻结 improvement protocol：

```text
Document improvement 由 CH-2 direct benchmark 触发
Market improvement   由 CH-1/CH-3 multi-horizon + PIT metrics 触发
2024 frozen result   不作为新的 tuning target
2025 Blind y         仍不可访问
```

PASS：任务 1/2/3 全映射、所有 metric 有计算/评审协议、所有 deliverable 有 owner、无无人负责项。

## 6. CH-1 — Multi-horizon Outcome Extension

新增并版本化：

```text
raw_return_1d
raw_return_20d
raw_return_60d
```

规则：

- 5D remain primary；
- session / suspension / missing-price semantics 与 PR-C 一致或显式版本化；
- Development / Validation / Blind 治理不变；
- 不提前使用 2025 y；
- 最终报告同时展示 1D / 5D / 20D / 60D；
- 不以“挑出最漂亮 horizon”为目的，而是检验不同风险信号的时间尺度。

重点研究问题：

```text
结构性 Document 风险是否在 20D / 60D 比 5D 更稳定？
Market Sentiment 是否主要解释 1D / 5D？
Document + Market 是否在不同 horizon 具有互补性？
```

Owner：D 主导；C market/session QA；A reproducibility；E report。

## 7. CH-2 — Competition-specific Document Risk Hardening

专项评测：

```text
cash burn / cash runway
redemption / repurchase / VAM
related-party transactions
customer concentration
supplier concentration
core pipeline progress
text embellishment / disclosure softening
```

每个风险类别至少独立报告：

```text
Precision
Recall
F1
Evidence Recall
Evidence page correctness / sample audit
failure attribution
```

先 benchmark 当前能力，达标只补测试 / UI；不达标才最小范围增强。任何新增 RiskItem 继续满足 Evidence / Verifier boundary。

增强决策必须基于 error attribution：

```text
retrieval miss
→ Hybrid / semantic retrieval enhancement

Evidence found but condition/context misunderstood
→ LLM semantic extraction / reranking

structured fact correct but feature lost
→ schema / representation adjustment

Verifier rejected correct evidence
→ verifier policy correction
```

不得因为 PR-F 的 5D AUC 低就默认“全部 438 PDF 必须重新用 LLM 跑一遍”。LLM 只在直接 benchmark 证明语义理解是主要瓶颈时进入正式 Production enhancement；deterministic financial calculations、schema、hash、feature vectorization、provenance 仍由代码负责。

Owner：B 主导；D evaluation；A contract regression；E UI。

## 8. CH-3 — Market Sentiment + Reusable Skills

把 PR-G Market Agent 扩成受治理的 Market Sentiment interpretation，而不是第二个黑箱预测模型。

优先解释短期 1D / 5D 的 point-in-time 信号：

- 发行期 IPO 冷暖；
- 近期 IPO 破发 / 5D 表现；
- 同行业历史 IPO context；
- liquidity / activity；
- 如取得 authoritative source，再接 governed HSI / industry / turnover Extended。

Competition Skills：

```text
LongDocumentRetrievalSkill
CashBurnSkill
ComparableValuationSkill
SentimentHeatSkill
```

Comparable / sentiment 输入必须 point-in-time。不得用未来 IPO 表现、target listing 后信息或 fake benchmark 补齐缺失特征。

CH-3 的评估必须与 CH-1 multi-horizon 配套，重点判断新增 Market Sentiment 对 1D / 5D 是否提供稳定增量，而不是继续把结构性 Document 风险强行映射为极短期涨跌。

## 9. CH-4 — Conflict Resolution + Full Traceability

统一记录：

```text
agent_name
input_task
plan_step
tool_or_skill_call
input_evidence_ids
calculation_ids
claim
verifier_status
conflict_id
resolution_action
final_status
```

Verifier / Supervisor 不创造原始 Evidence；unresolved conflict 必须保留并展示 uncertainty。

Competition target：Agent / Tool / Evidence traceability `= 100%`。

## 10. CH-5 — Evidence Screenshot + Human Review

要求：

- page / bbox 定位；
- screenshot / highlight；
- reviewer decision / note；
- 原结论与人工调整分开记录；
- reviewer audit trail 可追踪。

这一阶段同时完成 3–5 个代表性真实 IPO 的人工可读案例材料，为最终展示准备“风险结论 → 原文证据 → Agent/Skill → 模型/市场 → Final Supervisor”的完整链路。

## 11. CH-6 — Formal Evaluation + Submission Package

最终正式报告至少分四类结果，而不是只展示单一 AUC：

```text
A. Risk extraction
   accuracy / precision / recall / F1 by risk category

B. Evidence / governance
   Evidence recall / page correctness / traceability / human review

C. Predictive validation
   1D / 5D / 20D / 60D
   M / P / PM where applicable
   ROC-AUC / PR-AUC / Brier / regression metrics / uncertainty

D. Product E2E
   3–5 real IPO cases
   multi-agent trace
   Evidence screenshot
   Final Supervisor report
```

最终提交包至少包括：

```text
source code
reproducible environment / scripts
prediction tables
multi-agent trace / tool logs
Evidence artifacts
metric reports
3–5 representative real-case reports
Streamlit / API / batch demo
submission README
```

只有所有 acceptance matrix 项有证据并通过冻结审核，才允许标记：

```text
v0.4.5 COMPETITION_READY
```

## 12. Non-goals

Competition Hardening 不自动授权：

- 打开 2025 Blind y；
- 回滚 PR-A-F frozen contracts；
- 使用 fake market proxy；
- 根据 2024 frozen Validation 反转 score 或继续调参；
- 无 direct benchmark 地大规模重写 Retriever / LLM / Prompt / Agent；
- 把 model score 包装成真实概率；
- 只挑一个最漂亮 horizon / metric 代表整个系统能力。

若 CH-2 direct benchmark 显示 Document Pipeline 是真实瓶颈，再按 error attribution 启动 targeted Retriever / LLM / Agent enhancement；若 CH-1/CH-3 显示短期预测主要由 Market Sentiment 驱动，则把 1D / 5D 的预测优化重点放在受治理的 Market side，同时保留 Document side 的结构性风险解释价值。
