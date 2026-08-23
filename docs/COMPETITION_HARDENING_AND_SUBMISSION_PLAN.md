# 港股 IPO 风险预警赛题强化与提交总计划

> Status: **PLANNED — START ONLY AFTER CURRENT v0.4 BASELINE E2E IS RUNNING END TO END**  
> Date: **2026-08-22**  
> Competition: **第五届中国研究生金融科技创新大赛 — 东吴证券“基于多智能体协同的港股 IPO 招股书解析与上市后风险预警探索”**  
> Strategy: **先完成现有 PR-C → PR-H 闭环，再做赛题专项强化；不为了补赛题功能提前打断当前正式 Gate。**

---

## 1. 为什么把赛题强化放在当前闭环之后

当前主线已经覆盖赛题主体：

```text
Prospectus PDF
→ Parser / Retriever
→ Financial / Legal / Business Agents
→ Deterministic Skills
→ Verifier / Document Supervisor
→ Production Document X
→ Pre-IPO Market X
→ 5D Outcome Y
→ Canonical Dataset
→ Baseline / LightGBM / Explainability
→ Market Agent / Final Supervisor
→ Streamlit / Final Report
```

因此当前不需要为了赛题重新设计底层架构。先完成 PR-C～PR-H，得到一条真实可运行、可重建、可审计的 PDF → Final Report baseline；随后在稳定基线之上补齐赛题专项能力和验收指标。

正式顺序：

```text
CURRENT BASELINE E2E
PR-C → PR-D → PR-E → PR-F → PR-G → PR-H
        ↓
BASELINE E2E GATE
真实 PDF 可以一键跑到 Prediction + Evidence + Final Report
        ↓
COMPETITION HARDENING
CH-0 → CH-1 → CH-2 → CH-3 → CH-4 → CH-5 → CH-6
        ↓
COMPETITION ACCEPTANCE / SUBMISSION FREEZE
```

赛题强化是当前架构的增量层，不允许回滚 PR-A / PR-B 的 frozen provenance，也不允许破坏 2025 Blind 治理。

---

## 2. 赛题完整要求清单

本节作为提交前的 coverage checklist。最终版本必须逐项回答，而不是只完成其中一部分。

### 2.1 任务 1 — 招股书“防幻觉”解析与非标隐性风险抽取

需要支持数百页港股招股书 PDF，并覆盖：

- 标准化财务指标抽取；
- 未盈利企业现金消耗率 / 现金流消耗压力；
- 特殊股东对赌 / 赎回条款；
- 关联交易；
- 客户或供应商集中度；
- 核心管线进度等非标风险信息；
- “文本粉饰度”较高的原文切片；
- 风险结论必须绑定真实原文 Evidence，不允许 LLM 无证据生成正式风险。

### 2.2 任务 2 — 多角色尽调 Agent 协作架构与 Skill 编排

正式产品至少覆盖以下角色语义：

```text
法务合规 Agent
财务穿透 Agent
市场情绪 Agent
总控决策 / Final Supervisor
```

并提供可复用 Skills：

```text
长文档检索
同行估值比对
现金流消耗测算
情绪热度打分
以及现有 deterministic financial / risk calculations
```

不同 Agent 发生逻辑冲突时，需要显式的：

```text
conflict detection
→ autonomous plan / challenge
→ evidence re-check
→ verification / arbitration
→ retained conflict or resolved conclusion
```

不得为了“统一答案”删除真实冲突。

### 2.3 任务 3 — 可解释新股预警报告与投研复核工具

最终系统需要：

- 自动生成单家或批量《IPO 风险穿透预警报告》；
- 清晰展示高风险核心诱因；
- 精确映射招股书 PDF 页码、段落和表格；
- 能利用 page / bbox 生成或定位证据截图；
- 展示当前预测时间窗及风险预测；
- 提供可运行原型系统、API 服务或 Agent 可视化交互界面；
- 支持投研人员进行人机协同复核。

### 2.4 技术验收指标

最终比赛版本必须正式测量，而不是口头声明：

```text
关键风险要素抽取准确率      >= 80%
关键证据片段召回率          >= 85%
Agent 角色 / 推理 / 工具 / 证据来源可追踪率 = 100%
逻辑解释有效性              专家评审或 LLM 辅助评审
```

### 2.5 上市后风险预警业务验证

必须覆盖真实上市后表现：

```text
首日 / 1D
5 个交易日 / 5D     ← 核心、高权重
20 个交易日 / 20D
60 个交易日 / 60D
```

现有 PR-C 的正式主目标继续保持 5D；1D / 20D / 60D 在 baseline E2E 跑通后作为 competition outcome extension 独立版本化，不反向篡改已经冻结的 5D policy。

### 2.6 最终成果交付

提交包至少包含：

- 数据处理、PDF 解析、特征构建、风险预测、多智能体编排、报告生成完整源代码；
- 环境配置与运行脚本，或可复用 IPO 风险预警 Skill；
- 可运行原型系统或 API；
- 支持公司名称、股票代码或招股书文件输入；
- 测试集预测结果表；
- 多智能体推理 / tool-call / verification 日志；
- 关键 Evidence 片段；
- 典型案例分析报告；
- 3–5 个高质量现场演示案例，同时保留批量运行能力。

---

## 3. 当前系统与赛题要求的映射

| 赛题要求 | 当前基础 | Baseline E2E 后仍需补齐 |
| --- | --- | --- |
| 数百页 PDF 解析 | PyMuPDF Parser / DocumentChunk / page+bbox | 赛题案例专项 QA |
| 长文档检索 | frozen Retriever V3 / BM25 / table lane | 若指标不足再做定向优化 |
| 财务穿透 | Financial Agent + deterministic Skills | 现金消耗专项呈现 / 未盈利企业案例强化 |
| 法务合规 | Legal Agent | 对赌 / 赎回条款专项 benchmark |
| 商业风险 | Business Agent | 核心管线 / 集中度专项 benchmark |
| 防幻觉 | Evidence + Verifier + pending/rejected | 比赛指标化与推理日志展示 |
| 市场环境 | Market-X Core 30 positions | Market Sentiment 语义层；可选 governed Extended |
| 市场情绪 Agent | PR-G planned Market Agent | 对齐“市场情绪 Agent”赛题角色和情绪热度解释 |
| 总控 Agent | Document Supervisor + Final Supervisor contract | 冲突查证 / 仲裁链路强化 |
| 同行估值比对 | 尚非正式 Competition Skill | 新增 governed Comparable Valuation Skill |
| 文本粉饰度 | 尚非正式风险能力 | 新增 Text Embellishment / Disclosure Softening diagnostic |
| 5D 预警 | PR-C / PR-E / PR-F 主线 | 正式业务指标与案例呈现 |
| 1D / 20D / 60D | 部分历史 market foundation 能力 | 正式 outcome extension + validation tables |
| PDF 证据截图 | page/bbox 基础存在 | 前端截图 / 高亮 / 下载报告 |
| 人机复核 | Streamlit / service foundations | reviewer action / notes / audit trail |
| 100% 追踪 | provenance / manifests / Evidence | Agent plan/tool/conflict trace 统一展示 |

---

# CH-0 — Competition Scope Lock & Acceptance Matrix

## 4. 目标

PR-H baseline E2E 通过后，先冻结比赛 acceptance matrix，不立即开始大规模调参。

必须建立一张 machine-readable + human-readable checklist：

```text
competition_requirement_id
requirement
current_component
owner
status
metric_or_gate
evidence_artifact
blocking_issue
```

### PASS Gate

- 赛题任务 1/2/3 全部映射到明确组件；
- 所有技术指标都有计算脚本或人工评审协议；
- 所有交付物都有 owner 和产物路径；
- 不存在“赛题明确要求但无人负责”的项目。

---

# CH-1 — Multi-horizon Outcome Extension

## 5. 目标

在 frozen 5D outcome 之外建立：

```text
raw_return_1d
raw_return_20d
raw_return_60d
```

必要时可增加对应 warning / poor-performer 辅助标签，但必须独立 versioned，并明确阈值是否仅用于展示、研究还是正式分类。

### 硬规则

- 5D 仍是核心主目标，不因新增 horizon 重新调 5D threshold；
- trading-session / suspension / missing-price 规则与 PR-C 一致或显式版本化差异；
- Development / Validation / Blind 治理不变；
- 不提前使用 2025 y；
- 结果表同时报告 1D / 5D / 20D / 60D。

### 主要 Owner

D 主导；C 提供行情与 session QA；A 做 reproducibility / manifest；E 做最终报告呈现。

---

# CH-2 — Competition-specific Document Risk Hardening

## 6. 目标

在不破坏 frozen Production 路径的前提下，对赛题明确点名的风险建立专项评测 / 必要的新增版本：

```text
cash burn / cash runway
redemption / repurchase / VAM clauses
related-party transactions
customer concentration
supplier concentration
core pipeline progress
text embellishment / disclosure softening
```

### 实施策略

1. 先评估当前 Agent / Retriever 已覆盖多少；
2. 达标能力只补 benchmark、解释和 UI，不无意义重写；
3. 不达标能力再做最小范围 enhancement；
4. 任何新增正式 RiskItem 必须继续满足 Evidence / Verifier 边界；
5. 数值项继续交给 deterministic Skill；
6. “文本粉饰度”只能作为可解释 diagnostic / score，不得无证据地给公司贴主观标签。

### 文本粉饰度建议输出

```text
source_excerpt
page / bbox
linguistic_signal
contradictory_or_qualifying_evidence
score_semantics
uncertainty
```

不得输出无法解释来源的单一黑箱分数。

### 主要 Owner

B 主导；D 负责评测协议；A 审 public contract / regression；E 做前端展示。

---

# CH-3 — Market Sentiment + Skill Hardening

## 7. Market Sentiment Agent

把 PR-G Market Agent 对齐为赛题要求的“市场情绪 Agent”，但保持现有治理：

```text
Market-X / governed market facts
+ frozen model drivers
→ Market Sentiment interpretation
```

它不是第二个预测模型，也不能制造市场事实。

### 需要补齐的解释能力

- 发行期整体 IPO 冷暖；
- 近期 IPO 破发 / 5D 表现；
- 同行业历史 IPO context；
- 流动性 / activity signal；
- 如果取得可靠数据，再接入 governed HSI / industry benchmark / total-market turnover Extended；
- 不允许用错误 proxy 为了“覆盖赛题”制造市场情绪。

## 8. Competition Skills

新增或正式包装：

```text
LongDocumentRetrievalSkill      # 已有 Retriever 能力的 Skill 化接口
CashBurnSkill                   # 复用 deterministic calculations
ComparableValuationSkill        # 同行估值比对，要求 PIT 和来源 provenance
SentimentHeatSkill              # 基于 governed Market-X 的可解释情绪热度
```

Comparable valuation / sentiment heat 只使用目标上市时点之前可得信息。

### 主要 Owner

C 主导市场数据 / PIT；B 协助 Document-derived peer facts；D 审金融定义；A 审 provenance；E 集成 Agent / UI。

---

# CH-4 — Multi-Agent Conflict Resolution & Full Traceability

## 9. 目标

赛题不仅要求多个 Agent，还要求逻辑冲突时通过规划、辩论与查证形成自洽结论。因此 baseline Final Supervisor 之后增加显式 conflict workflow：

```text
Agent findings
→ conflict detector
→ evidence comparison
→ targeted re-retrieval / Skill check
→ verifier challenge
→ supervisor arbitration
→ resolved / unresolved conflict
```

### 必须记录

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

### 硬规则

- Verifier / Supervisor 不能创造原始 Evidence；
- unresolved conflict 可以保留为 `needs_review`；
- 不为了生成“漂亮的最终答案”强行一致；
- reasoning trace 对用户展示结构化摘要，不要求暴露内部不可审计自由文本思维链；
- 赛题要求的角色 / 工具 / Evidence 来源追踪率目标 = 100%。

### 主要 Owner

E 主导 workflow / Supervisor；A 做 contract / trace schema / integration；B/C/D 分别负责专业冲突规则。

---

# CH-5 — Evidence Screenshot, Human Review & Competition Report

## 10. 证据层

利用现有 `page + bbox + source document` 实现：

```text
RiskItem
→ Evidence
→ PDF page
→ bbox highlight
→ screenshot / excerpt card
```

必须能够把关键结论映射到原 PDF 页码、段落或表格；截图只是展示层，不替代 canonical Evidence。

## 11. 人机复核

UI 至少支持：

- 查看原文证据；
- 查看 Calculation；
- 查看 Market context / model driver；
- 查看 Agent / Skill / Verifier trace；
- 标记需要人工复核的结论；
- reviewer note / decision 保留 audit trail。

## 12. 《IPO 风险穿透预警报告》

至少包含：

```text
IPO Overview
Financial / Legal / Business Risks
Non-standard hidden risks
Document Evidence + page/screenshot
Market Sentiment
1D / 5D / 20D / 60D prediction/validation view
Model score + calibrated-status semantics
SHAP / top drivers
Agent conflicts / uncertainty / missingness
Final Supervisor synthesis
Provenance / model / data / run versions
```

### 主要 Owner

E 主导；B 做 Evidence UI；C 做 Market UI；D 做 model/outcome visualization；A 做 service / provenance / E2E integration。

---

# CH-6 — Competition Evaluation, Case Study & Submission Freeze

## 13. 文档解析指标

建立 reviewed competition evaluation set，正式计算：

```text
risk_element_precision_or_accuracy >= 0.80
key_evidence_recall              >= 0.85
```

需要按风险类型拆分，至少单独报告：

```text
redemption / VAM
related-party transactions
customer/supplier concentration
cash burn
core pipeline progress（存在适用样本时）
text embellishment diagnostic（独立人工评审）
```

不能只给一个 aggregate 分数掩盖某类完全失效。

## 14. Agent / explainability 指标

```text
traceability = 100%
```

每条正式风险 / 市场判断 / 模型输出都能够追溯至对应 source / Evidence / Skill / model version。

逻辑解释有效性使用预先定义 rubric，由专家或 LLM-assisted reviewer 打分，并保留 reviewer version / prompt / decision record。

## 15. 业务参考价值

在固定 evaluation protocol 下报告：

```text
1D outcome
5D outcome     # primary / higher-weight
20D outcome
60D outcome
```

5D 的分类 / ranking / calibration / case analysis 为重点，其他 horizon 作为辅助验证，不反向调优已经冻结的 5D policy。

## 16. 典型案例

至少准备：

- 3–5 个完整现场 Demo；
- 至少 1 个未盈利 / 高现金消耗案例；
- 至少 1 个法务 / 特殊条款案例；
- 至少 1 个市场环境与基本面“共振”案例；
- 至少 1 个 Agent 冲突后通过查证得到 resolved / needs_review 的案例；
- 成功案例与失败案例都要有，避免只展示 cherry-picked positives。

## 17. Submission Freeze Gate

只有以下全部满足才允许标记 `COMPETITION_READY`：

```text
[ ] Current PR-C → PR-H baseline E2E complete
[ ] PDF / company name / stock code input path works
[ ] financial + legal + business + market sentiment + final supervisor roles available
[ ] required Skills available and logged
[ ] key risk extraction metric >= 80%
[ ] key Evidence recall >= 85%
[ ] agent/tool/evidence traceability = 100%
[ ] 1D / 5D / 20D / 60D validation table produced
[ ] 5D primary warning result and explanation produced
[ ] Evidence page / paragraph / screenshot works
[ ] human-review flow works
[ ] prediction table / reasoning logs / evidence / case reports packaged
[ ] environment + run scripts reproduce the demo
[ ] no secrets / local absolute paths / raw confidential inputs committed
[ ] 2025 blind policy respected until formal opening
[ ] CI green and full E2E smoke passes
```

---

## 18. 五人赛题强化分工

| Member | Competition Hardening 主要职责 |
| --- | --- |
| A — Tech Lead / Pipeline | CH-0 acceptance matrix、multi-horizon/provenance integration、trace schema、CI、E2E、submission freeze Gate |
| B — Document / Agent | 非标风险专项、文本粉饰度、Evidence/page/bbox QA、Document explanation |
| C — Market / PIT | Market Sentiment data、Comparable Valuation/PIT、SentimentHeat、可选 Extended authoritative sources |
| D — Quant / ML | 1D/5D/20D/60D outcome、metrics、time-aware evaluation、model/SHAP/calibration、case statistics |
| E — Oracle / Product | Market Sentiment Agent、conflict workflow、Final Supervisor、report、human review、Streamlit/demo |

正式 Gate 仍由 A 做 cross-module acceptance；业务 / 模型 policy 仍由对应 owner 决定，不因比赛时间紧张而绕过 provenance / leakage review。

---

## 19. 与 v0.5 Retriever / LLM 优化的关系

Competition Hardening **不等于立即重新做大规模 Retriever / LLM 研究**。

顺序保持：

```text
先跑通 baseline E2E
→ PR-E / competition benchmark 找真实瓶颈
→ 再决定最小范围优化
```

如果：

- Evidence recall < 85%，优先做 Retriever / table / evidence targeting 的定向修复；
- 风险准确率 < 80% 且 Evidence 已正确，优先做 Agent / Verifier / Skill 语义修复；
- Oracle 明显强于 Production，才有强证据支持更大规模 Retriever / LLM / Agent 研究；
- 两者都已经达标，则不为了技术炫技做 Fine-tuning / LoRA。

任何重新调优都必须使用新的、明确治理的 evaluation / holdout；历史 Retriever Locked 10 已经消费，不得重新当 blind。

---

## 20. 最终项目形态

比赛提交时目标链路为：

```text
公司名称 / 股票代码 / Prospectus PDF
        ↓
Document Parser + Retriever
        ↓
Financial / Legal / Business Due-Diligence Agents
        ↓
Skills + Evidence + Verifier
        ↓
Document Supervisor
        ↓
Production Document X
        +
Pre-IPO Market X / Market Sentiment
        ↓
Frozen 5D Primary Model
+ 1D / 20D / 60D auxiliary validation
        ↓
SHAP / Drivers / Calibration Status
        ↓
Conflict-aware Final Supervisor
        ↓
Evidence Screenshot + Human Review
        ↓
《IPO 风险穿透预警报告》
        ↓
Streamlit / API / Batch Prediction Table
```

这条链路完成后，赛题的“招股书深度解析、多角色智能体协同、市场情绪共振、上市后表现验证、风险诱因归因、可解释报告、人机协同复核、可运行原型和提交材料”均有明确对应模块和正式验收 Gate。