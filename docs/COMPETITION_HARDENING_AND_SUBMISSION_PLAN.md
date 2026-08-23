# 港股 IPO 风险预警赛题强化与提交总计划

> Status: **PLANNED — START ONLY AFTER PR-H BASELINE E2E FREEZE**  
> Audit date: **2026-08-23**  
> Current baseline Gate: **PR-E**  
> Competition: **第五届中国研究生金融科技创新大赛 — 东吴证券“基于多智能体协同的港股 IPO 招股书解析与上市后风险预警探索”**

## 1. Why competition hardening comes later

PR-A / PR-B / PR-C / PR-D 与 Oracle v2 已冻结，当前正式主线从 PR-E 开始：

```text
PR-E Baseline + Oracle Diagnostic
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + real-case demo
→ v0.4.3 Baseline E2E Freeze
→ CH-0..CH-6 Competition Hardening
→ v0.4.5 Competition Submission Freeze
```

赛题强化是稳定 baseline 的增量层，不重写已经冻结的 PR-A-D provenance，不破坏 2025 Blind 治理，也不为了补功能提前跳过当前 Gate。

## 2. Competition acceptance scope

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

## 3. Formal competition metrics

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
5D   ← primary
20D
60D
```

5D frozen PR-C policy 不因新增 horizon 被反向修改；1D / 20D / 60D 独立 versioned。

## 4. CH-0 — Competition Scope Lock

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

PASS：任务 1/2/3 全映射、所有 metric 有计算/评审协议、所有 deliverable 有 owner、无无人负责项。

## 5. CH-1 — Multi-horizon Outcome Extension

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
- 最终报告同时展示 1D / 5D / 20D / 60D。

Owner：D 主导；C market/session QA；A reproducibility；E report。

## 6. CH-2 — Competition-specific Document Risk Hardening

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

先 benchmark 当前能力，达标只补测试 / UI；不达标才最小范围增强。任何新增 RiskItem 继续满足 Evidence / Verifier boundary。

Owner：B 主导；D evaluation；A contract regression；E UI。

## 7. CH-3 — Market Sentiment + Reusable Skills

把 PR-G Market Agent 扩成受治理的 Market Sentiment interpretation，而不是第二个黑箱预测模型。

可解释信号：

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

Comparable / sentiment 输入必须 point-in-time。

## 8. CH-4 — Conflict Resolution + Full Traceability

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

## 9. CH-5 — Evidence Screenshot + Human Review

要求：

- page / bbox 定位；
- screenshot / highlight；
- reviewer decision / note；
- 原结论与人工调整分开记录；
- reviewer audit trail 可追踪。

## 10. CH-6 — Formal Evaluation + Submission Package

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

## 11. Non-goals

Competition Hardening 不自动授权：

- 打开 2025 Blind y；
- 回滚 PR-A-D frozen contracts；
- 使用 fake market proxy；
- 无 benchmark 地大规模重写 Retriever / LLM / Prompt / Agent；
- 把 model score 包装成真实概率。

若 PR-E / PR-F 或冻结比赛 metric 显示 Document Pipeline 是真实瓶颈，再按证据启动 v0.5 Retriever / LLM / Agent research。
