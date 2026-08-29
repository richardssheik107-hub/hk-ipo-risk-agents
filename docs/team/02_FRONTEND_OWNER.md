# Person 2 — Competition Frontend / Product Experience Owner

> 状态日期：`2026-08-29`  
> 建议分支：`codex/final-product-ui`  
> 主优先级：**P0/P1**  
> 核心职责：把现有真实能力做成稳定、清晰、成熟、适合答辩的最终 UI

## 1. 主目标

前端不负责重新发明算法。最终让评委第一次打开就能快速理解：

```text
输入什么
→ 系统跑到哪一步
→ 找到了哪些 Risk / Evidence
→ Market-X 是什么状态
→ Model / SHAP 是什么状态
→ 有哪些 Conflict / Re-check
→ Final Supervisor 为什么这样判断
→ 如何追到 PDF 原文 / Trace / Report
```

最终明确支持三种模式：

```text
1. Offline Demo Replay
2. Historical Governed IPO
3. Fresh New-IPO Analysis
```

Replay 必须明确标识为 recorded run，不冒充实时推理。

## 2. 当前稳定基线

```text
final-three = 3 cases
Market = 3/3
Model = 3/3
Final Supervisor E1 = 3/3
M3 =1.0 x3
recheck =17/17
budget skipped =0
seven-stage =21/21
Evidence screenshots =17/17 precise
canonical bundle =66 files
fresh clone / Streamlit smoke =PASS
```

发行人输入已经支持 official catalog-backed 快速匹配：公司名 / 股票代码 / listing date / case id 可用于搜索并自动回填 identity，同时保留新 IPO 手工输入。

前端必须保护以上 baseline。

## 3. 当前要完成的产品工作

### A. 最终信息架构

首屏和结果页不要像 debug dashboard。优先展示：

```text
Case identity
Run mode
Overall state
Seven-stage progress
Top risks
Evidence status
Market / Model state
Final Supervisor summary
```

完整 JSON / diagnostics / provider metadata 放进高级详情或折叠区。

### B. 三种运行模式

#### Demo Replay

- canonical 3-case；
- hash-bound recorded artifacts；
- 无网络/PDF/API key 也能展示；
- 顶部明确“已记录运行回放”。

#### Historical Governed IPO

- official catalog identity；
- historical Market-X；
- Dynamic Model owner完成后接 real inference / SHAP；
- 不使用 case-specific UI。

#### Fresh New IPO

- 上传 PDF；
- issuer identity；
- Document analysis；
- Dynamic Market full/partial/unavailable；
- Model full/partial/unavailable；
- Supervisor / report 正常完成并解释 missingness。

## 4. Channel truth

必须严格区分：

```text
workflow completed
!=
all optional channels available
```

所有可选通道统一支持：

```text
AVAILABLE
PARTIAL
UNAVAILABLE
```

并显示：reason / missing source or feature / downstream impact / recoverability。

禁止通过颜色、默认值、旧 artifact 或 UI 文案伪造 available。

## 5. 页面最低要求

### Landing / Intake

- 明确输入 PDF、输出 Risk/Evidence/Market/Model/Supervisor/Report；
- issuer smart match；
- Demo / Historical / Fresh 入口清楚；
- 不把内部版本号和 debug path 放在核心位置。

### Case Overview

显示 issuer、stock、listing date、mode、runtime status、provenance 和 seven-stage progress。

### Risk / Evidence

Risk card 优先显示 severity、agent、verification、Evidence count、conflict/recheck；Evidence Viewer 一键追到 page / screenshot / bbox / quote。

### Market-X

显示 availability、value、unit/window、derivation、PIT cutoff、provenance、missing reason。新 case 不允许出现 final-three 旧值。

### Model / SHAP

显示 model identity、feature identity、`uncalibrated_model_score`、alert/classification、signed SHAP drivers、missing reason。不得把 score 称 probability。

### Conflict / Re-check

区分 detected / attempted / resolved / partial / unresolved / not-document-actionable。

### Final Supervisor / Report

显示 supplied-channel summary、overall risk、unresolved facts、Risk/Evidence refs、provider/prompt identity、accepted/fallback、scope/severity-floor，以及可读最终报告。

## 6. 与 Dynamic Market / Model 的边界

Frontend 只消费正式 contract：

```text
MarketContext
ModelSignal
channel state
provenance
missing reason
```

不读取 raw market history，不自己加载模型，不自己算 SHAP，不自己修 Evidence bbox。

Person 3/4 新增字段时先进入 versioned schema/presenter，再进入 UI。

## 7. 测试矩阵

### Canonical final-three

2410 / 2460 / 1318：7/7 stages、Risk、Evidence、Market、Model/SHAP、Conflict/Recheck、Supervisor、Report 全部无回归。

### Historical

Dynamic C/D 完成后至少测试 5–10 个非 canonical historical cases，确认 identity/channel/report 不串案。

### Fresh

至少 3–5 个 fresh PDF 覆盖 full / partial / unavailable，重点看 identity、progress、Market/Model missingness、Evidence、Supervisor、Report。

维护 presenter / stage / runtime-view / Evidence compatibility / Demo discovery / Streamlit smoke tests。

## 8. 禁止事项

- final-three company-specific UI if/else；
- unavailable 显示成 available；
- 复制旧 Market/Model/SHAP 数值；
- UI 猜 Evidence bbox；
- score 改称 probability；
- 删除 provenance / missingness 只为了页面更干净；
- 修改 M1/M2 / Market / model / Final Supervisor 算法语义。

## 9. 完成定义

```text
canonical replay no regression
Demo / Historical / Fresh mode boundary clear
all channel states truthful
key information readable at a glance
Evidence one-click traceable
Market / Model / SHAP readable
Final Supervisor / report answer-ready
no stale bundle mixing
no case-specific UI
UI tests / smoke PASS
```

最终目标是“证券研究/风控工作台”，不是开发者 dashboard。
