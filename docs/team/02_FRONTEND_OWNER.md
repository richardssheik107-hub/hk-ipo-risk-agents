# Person 2 — Competition Frontend / Product Experience Owner

> 状态日期：2026-08-29  
> 建议分支：`codex/final-product-ui`  
> 主优先级：**P1，临近提交升为 P0**  
> 核心职责：把已有真实能力展示成稳定、清晰、成熟、适合答辩的产品

## 1. 主目标

这个岗位不负责重新发明算法，核心任务是把现有系统做到：

```text
评委第一次打开
→ 立刻知道系统解决什么问题
→ 立刻知道当前案例跑到哪一步
→ 能清楚看到 Risk / Evidence / Market / Model / Supervisor
→ 能一键追到原文证据
→ 能看懂为什么给出风险判断
→ 不会因为换案例而出现空白、假绿色或语义混乱
```

最终前端要同时支持三种明确模式：

```text
1. Offline Demo Replay
2. Historical Governed IPO
3. Fresh New-IPO Analysis
```

三种模式必须在 UI 上有清楚标识，不能让用户误以为 Replay 是实时推理。

## 2. 当前稳定基线

当前 canonical final-three 已完整：

```text
3 cases
Market = 3/3
Model = 3/3
Final Supervisor E1 = 3/3
M3 = 1.0 x 3
rechecks = 17/17
budget skipped = 0
seven-stage = 21/21
Evidence screenshots = 17/17 precise
canonical demo bundle = 66 files
fresh clone = PASS
Streamlit smoke = PASS
```

前端必须保护这个已知稳定基线，不得因为视觉重构破坏三案例 Replay。

## 3. 负责范围

本岗位可以修改：

- `app/` 下的 Streamlit 页面与 presenter；
- competition runtime view；
- page layout / information hierarchy；
- case selector；
- Demo / Historical / Fresh mode selector；
- stage progress；
- Risk cards；
- Evidence Viewer；
- screenshot / page navigation；
- Market-X panel；
- Model / SHAP panel；
- Conflict / Recheck panel；
- Final Supervisor panel；
- single / batch report 展示；
- download/export controls；
- user-facing error / partial / unavailable messages；
- UI smoke / presenter / stage tests。

本岗位**不负责**：

- 修改 M1/M2 evaluator；
- 修改 Risk extraction 算法；
- 修改 Market-X 数值计算；
- 训练或调参模型；
- 为页面好看伪造 available 状态；
- 修改 Final Supervisor 安全 guard。

## 4. 最重要的 UI 语义

必须严格区分：

```text
stage completed
!=
all optional channels available
```

新案例可能出现：

```text
Document      AVAILABLE
Market-X      PARTIAL / UNAVAILABLE
Model         PARTIAL / UNAVAILABLE
Supervisor    AVAILABLE
Evidence      AVAILABLE
Report        AVAILABLE
```

这仍然可以是“流程完成”，但不能把缺失的 Market / Model 染成绿色伪装成有数据。

所有可选通道必须支持：

```text
AVAILABLE
PARTIAL
UNAVAILABLE
```

并显示：

- reason code；
- missing source / missing feature；
- 是否影响后续模块；
- 是否可以通过重新配置/提供数据恢复。

## 5. 页面结构建议

### 5.1 首页 / Landing

首页必须在首屏说明：

```text
输入：港股 IPO 招股书
输出：Document Risk + Market Context + Model Signal + Evidence + Supervisor + Report
```

同时给出三个入口：

- 预置 Demo；
- 历史 IPO；
- 上传新招股书。

避免把内部版本号、debug path、开发者术语放在首屏核心位置。

### 5.2 Case Overview

顶部固定显示：

```text
issuer
stock code
listing date
run mode
runtime status
provenance identity
```

然后展示七阶段 Progress。

### 5.3 Risk Summary

风险卡片优先显示：

```text
risk title
severity
owner agent
verification status
key Evidence count
是否有 conflict / recheck
```

不让用户先看到大段 JSON。

### 5.4 Evidence Viewer

必须做到：

```text
Risk → Evidence → page → screenshot / bbox → quote
```

要求：

- 页码清晰；
- quote 可读；
- bbox 真实；
- unavailable 要诚实解释；
- 不从 UI 猜 bbox；
- 不把 Evidence 截图当原始 PDF 文件上传。

### 5.5 Market-X

Market 面板必须同时显示：

- availability；
- feature value；
- unit；
- time window；
- derivation；
- PIT cutoff；
- provenance；
- missingness。

如果 Dynamic Market-X 尚未完成，不允许对新案例显示 final-three 的旧值。

### 5.6 Model / SHAP

Model 面板必须显示：

```text
model identity
feature / handoff identity
score
score semantics = uncalibrated_model_score
classification / alert output
SHAP / signed drivers
availability / missing reason
```

禁止将 score 写成 probability / 概率。

### 5.7 Conflict / Recheck

必须区分：

```text
conflict detected
recheck attempted
resolved
partially resolved
unresolved
not document-actionable
```

不要再把所有未处理状态都粗暴显示为“受控预算未执行”。

### 5.8 Final Supervisor

展示：

- overall risk；
- supplied-channel summary；
- unresolved facts；
- cited Risk/Evidence IDs；
- provider/model/prompt identity；
- accepted / fallback；
- scope / severity floor 状态。

禁止把 Final Supervisor 文案变成投资建议或价格预测。

### 5.9 Final Report

最终报告页应有：

```text
Executive Summary
Document Risks
Market Context
Model Signal
Conflicts / Rechecks
Final Supervisor
Evidence Appendix
Trace / Provenance
```

重点信息先展示，完整审计细节允许折叠。

## 6. 视觉与交互原则

目标是“证券研究/风控工作台”，不是“开发者 debug dashboard”。

要求：

- 信息层级明显；
- 字号可读；
- 不堆满全屏小字；
- 核心数字、风险等级、Evidence 状态一眼可见；
- 高密度表格可以折叠；
- 不使用内部讨论语气；
- 中文术语统一；
- 英文技术字段只在审计/高级详情中出现；
- 空状态有解释；
- 错误状态有恢复建议；
- 页面刷新不应随机切回旧 bundle。

## 7. Canonical Demo 发现规则

必须保持优先级：

```text
1. IPO_RISK_DEMO_BUNDLE
2. reports/v045_demo_bundle
3. unavailable
```

不要默认扫描：

```text
_current
_old
_final2
_v3_final
```

避免加载旧 artifact。

## 8. 与 Dynamic Market / Model 的接口

Frontend 不直接计算 Market 或 Model。

只消费正式 contract：

```text
MarketContext
ModelSignal
channel state
provenance
missing reason
```

如果 Person 3 / Person 4 新增字段，要求先进入 versioned schema/presenter，再进入 UI；禁止 UI 自己解析内部临时文件结构。

## 9. 测试矩阵

### 必测 A — canonical final-three

```text
2410
2460
1318
```

每案检查：

```text
7/7 stages
Risk cards
Market
Model
SHAP
Conflict/Recheck
Final Supervisor
Evidence Viewer
Report
```

### 必测 B — historical governed cases

在 Person 3 / Person 4 完成后，选择至少 5–10 个非 canonical 历史案例。

要求：

- 不写 case-specific UI；
- identity 正确；
- Market / Model 状态正确；
- Evidence 不串公司；
- report 可读。

### 必测 C — fresh new PDF

在 Dynamic New-IPO path 完成后选择至少 3–5 个新案例。

重点看：

```text
upload
identity
progress
partial/unavailable semantics
Market-X
Model
Evidence
Supervisor
report
```

## 10. 自动化验收

至少维护/增加：

```text
presenter tests
pipeline stage tests
competition runtime view tests
Evidence viewer compatibility tests
Demo discovery tests
Streamlit AppTest / smoke where available
```

前端重构不得破坏：

```text
Team demo runtime CI
Role D runtime CI
full tests
```

## 11. 交付物

最终交给 Release Owner：

```text
final app code
UI smoke result
canonical 3-case screenshots
historical-case UI evidence
fresh-case UI evidence
UI mode/state contract说明
known limitations
```

## 12. 禁止事项

禁止：

- 为特定三家公司写 UI if/else；
- 把 unavailable 显示成 available；
- 复制旧 Market / Model 数值到新案例；
- 修改 Evidence bbox；
- 改 score 语义为概率；
- 从 raw Gold / Blind 读取内容；
- 为展示效果删除 provenance / missingness。

## 13. 完成定义

本岗位 DONE 条件：

```text
canonical 3-case replay 无回归
Historical / Fresh 模式边界清晰
所有 channel state truthful
关键功能首屏可理解
Evidence 一键追溯
Market / Model / SHAP 可读
Final Supervisor / report 可读
无旧 bundle 混用
无 case-specific UI
UI tests / smoke PASS
```

最终目标不是“页面更花哨”，而是让评委在最短时间内看懂系统的真实性、完整性和可解释性。