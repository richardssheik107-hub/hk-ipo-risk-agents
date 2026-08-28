# Competition Closure Plan — 赛题对齐后的统一收口计划

> 状态日期：`2026-08-28`
>
> 基线提交：`a2d1f16f6e72e5520881b362e356bdf2d09e2809`
>
> 当前结论：**NOT COMPETITION_READY**

本文档是项目从当前状态走向比赛交付的唯一操作计划。指标口径仍以 `COMPETITION_METRIC_PROTOCOL.md` 为准，实时 Gate 以 `V0.4_RELEASE_ACCEPTANCE.md` 为准。

## 1. 赛题要求与仓库现状

赛题要求形成一条完整闭环：

```text
数百页招股书防幻觉解析
→ 财务 / 法务 / 业务隐性风险抽取
→ 多 Agent 协作与冲突查证
→ 基本面与市场情绪融合
→ 1D / 5D / 20D / 60D 上市后验证
→ 原 PDF 页码、段落、截图与可运行工具
```

### 任务 1：招股书解析与风险抽取

已具备：

- PyMuPDF / table-aware 解析；
- Financial deterministic-first；
- Legal / Business structured LLM；
- Evidence scope guard、Verifier 与 Existing-Gold evaluator；
- v0.4.6 offline / shadow / gated 对照、LLM journal、retrieval waterfall。

未关闭：

- M1 当前 fixed-10 仅 `23.33%`，目标 `>=80%`；
- M2 当前 fixed-10 仅 `18.75%`，目标 `>=85%`；
- v0.4.6 诊断框架尚未形成一份完整 fixed-10 实测；
- 核心管线进度、文本粉饰度、关联交易缺少正式能力展示；
- Evidence bbox / 精确截图尚未成为稳定交付链。

### 任务 2：多 Agent 协作与 Skill 编排

已具备：

- Financial、Legal、Business、Market、Final Supervisor；
- IPOHeatSkill、MarketRegimeSkill、现金流计算；
- Conflict detection、bounded re-check、Verifier challenge；
- Agent / Tool / Evidence trace；
- M3 三案例实测 `3/3 = 1.0`。

未关闭：

- Final Supervisor real-provider accepted 当前 `2/3`；
- Market strict observation contract 当前 `1/3`；
- 同行估值比对尚无正式 Skill；
- M4 尚无 6 份独立真人评审。

### 任务 3：可解释报告与投研复核工具

已具备：

- Streamlit 多工作区；
- Human Review sidecar；
- 风险报告、Trace、Evidence Viewer、submission tooling；
- Role-D 1D / 5D / 20D / 60D 物化证据已记录。

未关闭：

- 关键风险原 PDF 精确高亮截图；
- 三个正式案例的完整 AI 报告与 M4 评审；
- current-main Role-D strict revalidation 与 D→E final-three package；
- final prediction table、案例报告、artifact index 和安全封包。

## 2. 当前真实状态

| 赛题维度 | 当前状态 | 关闭标准 |
|---|---|---|
| M1 风险抽取 | fixed-10 `23.33%` | ALL 79 Development `>=80%` |
| M2 证据召回 | fixed-10 `18.75%` | ALL 79 Development `>=85%` |
| M3 可追踪性 | 三案例 `3/3 = 1.0` | 保持 100%，最终包可复核 |
| M4 解释质量 | `0/6` 真人评审 | 每案 2 名独立评审并通过 rubric |
| M5 业务验证 | 70-case 物化已记录 | current-main strict revalidation + final-three handoff |
| Market 融合 | explicit state 3/3；strict contract 1/3 | strict contract 3/3，无伪造数值 |
| Final Supervisor | accepted 2/3 | real-provider accepted 3/3 |
| 产品交付 | UI / report / tooling 已存在 | 截图、案例、预测表、日志、API/UI、bundle 齐全 |

## 3. 距离比赛还剩 6 个阶段

### 阶段 1 — B 线全链路取证与可信基线

目标：先证明每个 M1/M2 失分的最早失败阶段，不再把所有最终缺失都笼统归为 `semantic_extraction_miss`。

执行：

1. 校验 fixed-10、Gold、代码、Prompt、provider、journal 身份；
2. 运行 v0.4.6 structured smoke；
3. 运行 offline / shadow / gated 同口径 fixed-10；
4. 生成 parser、retrieval、LLM、builder、reconciliation、verifier、binding 瀑布；
5. 形成逐 Risk Unit / Evidence Unit 根因矩阵。

退出条件：

- 至少 90% Risk Unit 和 Evidence Unit 有可证明的最早失败阶段；
- offline / shadow / gated 身份一致；
- shadow 不改变 offline 结果；
- gated 不额外调用网络；
- 输出唯一的第一优先修复项。

### 阶段 2 — B 线指标提升与 Full Development

目标：用通用修复而非样本特判关闭 M1/M2。

执行：

1. 按已证明根因安排修复包；
2. 每个修复包有独立回归测试和前后消融；
3. fixed-10 达标后进入较大 Development checkpoint；
4. 运行 ALL 79 Development；
5. 冻结代码、Prompt、Retriever、Schema、Verifier、Evaluator 与运行配置。

退出条件：

```text
ALL 79 Development
M1 >=0.80（目标 >=0.85）
M2 >=0.85（目标 >=0.88）
real_llm_cases = 79
Validation = false
Blind = false
```

### 阶段 3 — C / E 三案例最终闭环

并行完成：

1. 2410 / 2460 / 1318 real-provider accepted `3/3`；
2. Market strict observation metadata `3/3`；
3. M3 保持 `1.0`；
4. 每案两名独立真人完成 M4，共 6 份评审；
5. 输出三个完整、可复核的典型案例。

退出条件：E1、C1、M3、M4 全部通过，fallback 不冒充远程成功。

### 阶段 4 — 补齐赛题能力与产品展示缺口

这是比赛覆盖任务，不混入 Existing-Gold M1/M2 分数：

1. 核心管线进度能力案例；
2. 文本粉饰度原文切片能力案例；
3. 关联交易能力案例；
4. 同行估值比对 Skill 或明确的可审计替代方案；
5. Evidence bbox / 唯一精确匹配 / 高亮截图；
6. 单家与批量报告、API/UI 人机复核路径。

退出条件：每项至少有一条真实案例、Evidence、Trace 和可展示产物；无法正式量化的能力明确标为 qualitative demonstration。

### 阶段 5 — 冻结、复验与一次性 Validation

并行执行：

1. Role-D current-main strict revalidation；
2. Role-D resume 与 fresh-directory byte-identical；
3. D→E final-three label-free package；
4. B 线冻结后一次性运行 ALL 19 Validation；
5. latest-main CI、Blind、provenance、determinism 审计。

Validation 运行后不得回头调整 Prompt、Retriever、Verifier、阈值或 evaluator。

### 阶段 6 — 最终交付与答辩封包

必须形成：

- 完整源码、环境配置和运行脚本；
- 可运行原型系统或 API；
- 测试集预测表；
- 多 Agent 推理日志；
- 关键 Evidence 与截图；
- 三个典型案例报告；
- 指标总表、artifact index、release note；
- 安全扫描通过的 submission ZIP 与 SHA-256 manifest。

全部硬 Gate 真实通过后，才允许标记 `COMPETITION_READY`。

## 4. 关键路径与并行关系

```text
B 取证
→ B 通用修复
→ ALL 79 Development
→ B 冻结
→ one-shot Validation
→ A final readiness / bundle
```

可并行：

```text
D release revalidation
C/E final-three closure
M4 human review
赛题能力案例与 Evidence screenshot
文档与答辩材料
```

B 是当前最长关键路径；D、C/E、产品展示不能等待 B 完成后才启动。

## 5. 本轮移除的过度流程限制

以下旧限制不再作为绝对规则：

- 不再固定“最多 2–4 轮”；改为基于根因覆盖、指标增益和停止条件；
- 不再要求所有工作都采用 Runner-only；诊断、消融、代码审计和修复可以分别执行；
- 不再限制 Codex 只能读取两个 summary 文件；允许读取与根因直接相关的完整代码、Trace 和 artifact；
- 不再禁止完整 Retriever 改造；允许 Development-only、无 Gold 泄漏、可消融的通用检索改造；
- 不再禁止模型 / transport 对照；允许在 Development 上做身份冻结、预算受控的比较；
- 不再强制每次只能修改一个文件或一个函数；允许一个有清晰假设、测试和消融的原子修复包；
- fixed-10 不再被视为最终目标，只是快速诊断集；
- Evidence screenshot 不再作为可有可无的 P2，而是赛题任务 3 的正式交付项。

## 6. 继续保留的硬边界

这些不是“多余限制”，不得移除：

- Existing Gold 不新增、不修改，不把 `UNJUDGED` 当 negative；
- Gold 不进入 runtime Retriever、Prompt 或 Agent；
- Validation 冻结后一次性运行，不用于调参；
- 2025 Blind outcome 未授权前不访问；
- 不按公司、股票、case_id、页码硬编码；
- LLM 不得创造 Evidence ID 或越过 scope；
- 精确财务数值由 deterministic Calculation 负责；
- Market 必须 PIT-safe，缺失不补零、不造 proxy；
- fallback 不冒充 real-provider accepted；
- 不提交 Secret、授权 PDF、raw EOD、本地绝对路径或未授权模型；
- `COMPETITION_READY` 只能由完整实测证据得出。

## 7. 停止条件

任何工作流出现以下情况应停止并保留最佳可复现版本：

- 连续两个修复包没有 M1/M2 净增益；
- fixed-10 提升但 Full Development 明显退化；
- 需要查看 Validation 才能决定参数；
- 需要修改 Gold 或 evaluator 才能继续；
- 需要访问 Blind outcome；
- 模型 / transport 结构化合同不稳定且无法在有界预算内修复；
- 新功能不能产生真实 Evidence、Trace 或可复现 artifact。

## 8. 完成定义

```text
M1 >=80%
+ M2 >=85%
+ M3 =100%
+ M4 PASS
+ M5 current-main strict revalidation PASS
+ Market final validation 3/3
+ Final Supervisor real-provider accepted 3/3
+ Evidence screenshots / reports / API or UI ready
+ one-shot Validation completed under freeze
+ CI / Blind / provenance / determinism / security / package PASS
= COMPETITION_READY
```
