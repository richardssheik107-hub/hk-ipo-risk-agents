# v0.4 → Competition Submission 五人执行计划（5-Day Sprint）

> Status snapshot: **2026-08-25**  
> Remaining window: **5 days**  
> Primary objective: **回归赛题本身，减少探索实验，最大化真实 LLM 带来的功能提升，完成可稳定提交版本**

## 1. 固定角色与五天目标

| Role | 这五天唯一主线 | 最终交付 |
| --- | --- | --- |
| A — Tech Lead / Integration | 集成、接口、CI、release、submission | 每晚 main 可运行；最终版本可复现、可提交 |
| B — Document + LLM | Legal / Business 语义理解、Evidence、Verifier | 真实 LLM 能从招股书 Evidence 解决复杂语义 |
| C — Market + LLM | 现有 Market-X / HSI / turnover → Market interpretation | PIT-safe 的市场环境判断，不继续堆新数据源 |
| D — Model / Evaluation Support | 恢复 frozen PR-F handoff；最小 AI-vs-offline 效果检查 | 模型通道可用则接入；不可用则诚实降级；不给 sprint 制造研究负担 |
| E — LLM Supervisor / Product | Final Supervisor、conflict/re-check、Evidence/AI Trace、UI | 让大模型能力在产品中可见、可追溯、可演示 |

协同主线：

```text
B  real Document + LLM semantics ───────┐
C  governed Market facts + LLM view ───┼→ E LLM Final Supervisor → Product
D  frozen model / minimal effect check ─┘

A = interface + merge + CI + real-case regression + release
```

## 2. 全员停止项

比赛提交前，大幅压缩以下工作：

```text
full multi-horizon research
broad feature audit / P-Core research
new model families / tuning
large Retriever rewrite
industry PIT research
new broad market source expansion
full-corpus benchmark project
story-only features / presentation-only engineering
```

任何新任务必须至少满足一个条件：

```text
直接满足赛题要求
解决真实 E2E blocker
提升 Legal/Business/Market/Supervisor 的 LLM 能力
修复高影响错误
提升最终 demo 的稳定性与可理解性
```

## 3. Day 1 — Real LLM Document Intelligence

### A

- 从最新 `main` 冻结 5-day sprint 接口；
- 确认 `v04_ai.yaml` / provider 配置与 secret policy；
- 建立 real-case smoke 命令；
- 保证 LLM metadata 能向上层传播或至少可审计。

### B — 当天核心负责人

重点只做两条链：

```text
Legal Evidence
→ LLM structured extraction
→ legal fact
→ Risk builder
→ Verifier

Business Evidence
→ deterministic extraction
+ LLM semantic cross-check / gap fill
→ Risk builder
→ Verifier
```

必须在至少 1 个真实 PDF 上成功调用真实 Provider。

优先解决：

```text
redemption rights 的当前有效性 / 上市后存续 / termination condition
litigation/compliance 的事实 vs 模板化风险提示
core product / commercialization stage / product revenue semantics
```

Financial Agent 继续 deterministic-first；只有明确文本歧义且已有 Evidence 时才允许加 LLM assist，禁止让 LLM 负责精确金融计算。

### C

- 只整理现有可用 Market facts：Core + HSI + turnover + volatility / prior IPO context；
- 定义给 LLM 的结构化 MarketContext 输入；
- 不新增大数据工程。

### D

- 用半天优先恢复原 frozen PR-F per-case handoff；
- 不 retrain / reconstruct / retune；
- 若恢复失败，明确记录 blocker，不阻塞 B/C/E。

### E

- 建立 LLM Final Supervisor schema / prompt contract；
- 输入只允许 Document risks/Evidence、Market facts、model/rule signal；
- 输出至少包含：`overall_assessment / key_findings / conflicts / uncertainty / recheck_requests`。

### Day 1 Gate

```text
real LLM provider call succeeds
Legal or Business produces validated structured output
Evidence IDs remain in-scope
no hallucinated facts
same case can reach Verifier/Supervisor input
```

## 4. Day 2 — LLM Market + LLM Supervisor + Real Collaboration

### B

- 稳定 Legal / Business 的 1–2 个真实 case；
- 对失败只做 targeted fix，不重写整个 Retriever。

### C

实现：

```text
governed MarketContext
→ LLM Market interpretation
→ market_regime / risk_level / key_drivers / uncertainty
```

LLM 只能解释输入事实，不生成新的市场数据。

### D

- 若 frozen model runtime 恢复：提供 per-case score + top SHAP + model identity；
- 若未恢复：保持 `Model Channel = unavailable`，不造假。

### E — 当天核心负责人

跑通：

```text
Financial Agent
Legal Agent
Business Agent
Market interpretation
Model/Rule signal
↓
LLM Final Supervisor
↓
conflict detection
↓
1-step re-check request
↓
Verifier / targeted retrieval result
↓
final synthesis
```

五天版本只要求**简单、真实、可控的一轮 re-check**，不实现复杂无限 autonomous loop。

### A

晚间做第一次全链集成，要求 main 候选分支可跑。

### Day 2 Gate

```text
Document + Market + Supervisor all run on one real case
at least one conflict/uncertainty can be represented
Supervisor does not create new Evidence
LLM metadata / provider state is observable
```

## 5. Day 3 — 3–5 Real Cases + Targeted Quality Fixes

### 全员共同目标

把系统从“单 case 成功”变成“比赛可演示”。

候选 case 至少覆盖：

```text
Case A  Financial / Calculation 清晰
Case B  Legal or Business LLM semantic value 清晰
Case C  Document vs Market / Agent conflict 清晰
```

目标 3–5 个真实 IPO，不为了数量牺牲稳定性。

### B

- 修 selected cases 中最影响结果的 Document semantic errors；
- 不做全量 benchmark。

### C

- 验证所有 demo cases 的 PIT / provenance / missingness；
- market interpretation 输出稳定。

### D

做一个很小的同 case 对照：

```text
Offline deterministic
vs
AI enhanced
```

只记录：

```text
semantic fields resolved
risk resolution count
needs_review / extraction_failed count
Evidence grounding validity
structured-output validity
```

不做大规模统计研究。

### E

- 为 selected cases 固化 Agent Trace；
- 确认 Supervisor conflict/re-check/uncertainty 能被前端消费。

### A

- 真实 case smoke；
- full CI；
- 只合并通过 regression 的改动。

## 6. Day 4 — Competition Product Integration

E 主导，不再扩页面数量。最终产品优先三块：

### 1. Risk Command Center

```text
Overall assessment
Top Financial / Legal / Business risks
Market Environment
Model / Rule state
uncertainty
```

### 2. Evidence + AI Analysis

```text
left: PDF page / bbox / Evidence
right:
Agent
LLM task
structured semantic result
Calculation if any
Verifier
AI contribution
```

必须能区分：

```text
Deterministic-only
LLM-assisted
LLM-required semantic extraction
```

### 3. Agent Trace + Final Supervisor

```text
Parser / Retriever
→ Financial / Legal / Business
→ Market
→ Verifier
→ conflict/re-check
→ Final Supervisor
```

显示真实 provider/model/prompt version/latency/token usage 等已有 metadata；不要展示 raw secrets 或不必要 remote payload。

B/C/D 只向 E 提供稳定结构化结果，不再临时扩 schema；A 控制接口变更。

## 7. Day 5 — Freeze + Submission

Day 5 原则：**停止新增功能。**

### A — Submission Owner

- full test / integration / real-case regression；
- secret/path/licensed-data scan；
- release identity / tag / runbook；
- 保证 `clone → install → configure → run`；
- 最终提交。

### B

- 固化 2–3 个最能体现 LLM 文档语义价值的 Evidence case；
- 检查引用页码 / bbox / Verifier。

### C

- 固化 Market methodology / PIT provenance；
- 验证 market explanation 与原始输入一致。

### D

- 固化 model availability、SHAP（若有）与 offline-vs-AI quick check；
- 不在最后一天追指标。

### E

- final Streamlit；
- final report；
- demo screenshots；
- 3–5 case demo flow；
- 现场演示脚本只描述真实功能，不补虚构结果。

## 8. 5-Day Definition of Done

最终必须满足：

```text
>= 3 stable real IPO cases
real LLM provider in production-like AI path
Legal/Business semantic extraction visibly useful
Market LLM interpretation grounded in PIT facts
LLM Final Supervisor synthesizes / detects conflict / preserves uncertainty
Evidence / Calculation / Verifier remain authoritative boundaries
Agent + LLM trace visible
no fabricated model/market/Evidence facts
2025 Blind y not accessed
full CI + real-case smoke pass
submission package reproducible
```

## 9. Model / PR-H special rule

D 必须优先恢复 frozen PR-F handoff，但最多占用有限时间。若不可恢复：

```text
formal PR-H all-channel Gate stays BLOCKED
Model channel displays unavailable honestly
competition sprint continues with Document + Market + Rule + LLM Supervisor
```

严禁为了“界面完整”重新训练 PR-F 或伪造 per-case model score。

## 10. Git 协作节奏

这五天改为高频合流：

```text
上午：每人确认当天唯一 deliverable
下午：短分支 / 小 PR
晚上：A integration + CI + real-case smoke
```

原则：

- 单 PR 单功能；
- main 每晚保持可运行；
- 不保留长寿命实验分支；
- 不新增长篇 exploration 文档；
- 失败方向当天止损，不跨日继续无边界研究。
