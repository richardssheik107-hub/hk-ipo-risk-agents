# HK IPO Risk Agents

面向东吴证券港股 IPO 赛题的多智能体风险分析与上市后预警原型。

> Package checkpoint：`v0.4.0`
>
> Competition runtime：`v0.4.5`
>
> Role-B diagnostic track：`v0.4.6`
>
> 状态日期：`2026-08-29`
>
> 当前结论：**NOT COMPETITION_READY**

## 当前执行模式

项目已经有一个稳定、可 fresh-clone 的三案例产品基线。当前不再把前端是否全绿作为主要问题，后续重点转向：

```text
B ALL79 M1/M2
+ Dynamic New-IPO full path
+ D 模型正式决议
+ 赛题特色能力覆盖
+ freeze / one-shot Validation / final package
```

Human Review UI / export 继续保留为可选的人机协同能力，但**不再要求额外真人标注，不再要求 3 案 × 2 reviewer，也不再作为 Competition Ready / Release Gate**。

## 赛题目标

1. 对数百页港股招股书进行防幻觉解析，抽取财务、法务和业务隐性风险；
2. 让 Financial、Legal、Business、Market 与 Final Supervisor 协作、冲突查证并保留完整 Trace；
3. 输出带原 PDF 页码、Evidence / bbox / 截图的风险报告，并用上市后 1D / 5D / 20D / 60D 表现验证业务参考价值；
4. 让预置三案例只是稳定离线回放，而不是系统能力边界，逐步补齐 Dynamic New-IPO Market / Model inference。

## 最新状态

| 维度 | 当前已合入事实 | 最终关闭标准 |
|---|---|---|
| B M1 | fixed-journal `12/30 = 40.00%` | ALL 79 Development `>=80%` |
| B M2 | fixed-journal `18/48 = 37.50%` | ALL 79 Development `>=85%` |
| B fresh gated | `11/30` M1、`17/48` M2；`38/40` structured valid；2 fallback；0 transport/scope failure | 继续 Development 泛化，先修 deterministic fact formation，再处理 retrieval candidate miss |
| M3 Traceability | final-three 三案例均 `1.0` | 保持 100% |
| Final Supervisor | Gate E1 `3/3`；real-provider 首轮接受 `3/3`；correction `0`；fallback `0`；severity floor `3/3` | 保持 scope / vocabulary / severity contract |
| Market | final-three `3/3 available`；已提交 438 个 governed frozen Market-X Core artifacts | 历史 universe 保持 PIT/provenance；继续补 Dynamic New-IPO path |
| Model | final-three frozen Model `3/3 available` | 完成 D promote/retain 决议；补 frozen-model dynamic inference，而不是只读 final-three handoff |
| Evidence screenshot | `17/17`，精确定位 `100%` | 保持 PDF hash / page / bbox / screenshot hash 绑定 |
| Re-check | `17/17` actionable attempted；budget-skipped `0` | 保持 bounded / fail-closed |
| 产品 | final-three 七阶段 `21/21`；canonical replay `66` files；hash verify / team clone / Streamlit smoke 均 PASS | Dynamic New-IPO + capability demos + final submission |
| M5 formal | current-main 70-case 四文件与 receipt 哈希一致；D1 `12/12 PASS` | 保持 deterministic / Blind 边界 |
| M5 v2 candidate | Recall `52.17%`、F1 `42.11%`、PR-AUC `38.12%`、ROC-AUC `0.4875`，未晋升 | A governance decision + 新 freeze/handoff（若 promote） |
| Human Review | UI / export 能力保留 | **Optional；不需要真人标注，不是 Release Gate** |

Frozen PR-F 的五日 Recall `4.35%`、ROC-AUC `0.4246` 仍不足以宣称强预测效果。v2 candidate 改善了高召回 operating point，但正式产品在新 promotion/freeze 前不能把它冒充 frozen model。

## 当前优先级

### P0 — Role-B M1/M2

当前已经排除“广泛 Parser preservation”和“period candidate generation”作为主根因。下一主根因顺序：

```text
deterministic_fact_missing
→ isolated retrieval_candidate_miss
→ numeric extraction / true conflict
→ LLM / Evidence variance
```

fixed-10 只是快速诊断。最终必须跑 ALL 79 Development：

```text
M1 >= 0.80
M2 >= 0.85
real_llm_cases = 79
Validation = false
Blind input/outcome not used for optimization
```

### P0 — Dynamic New-IPO Full Path

当前三案例是稳定、完整、可离线回放的黄金演示路径，但任意新 IPO 仍可能缺少 Market / frozen Model per-case signal。

下一阶段采用独立 feature branch，不破坏稳定主线：

```text
Phase 1: 438 historical frozen universe
Market-X → frozen model inference → native SHAP → Final Supervisor

Phase 2: arbitrary new IPO
listing-date PIT history → Dynamic Market-X → frozen model inference → SHAP → report
```

目标是让 `2410 / 2460 / 1318` 只是预置 Demo，不是产品能力边界。

### P0 — Role-D 模型决议

A 只做一次 promote/retain 决议：

- promote v2：新建 versioned freeze / receipt / handoff，不再按 2024 调参；
- retain frozen PR-F：保留弱辅助信号定位，并诚实披露模型局限。

### P1 — Capability + Final Release

补齐真实、可审计的：

- core pipeline progress；
- text embellishment；
- related-party transaction；
- comparable IPO valuation；
- Dynamic New-IPO product path；
- one-shot Validation；
- provenance / determinism / security audits；
- secure submission ZIP + SHA-256 manifest。

无 Existing Gold 的能力作为 `qualitative demonstration`，不混入 M1/M2。

## 系统架构

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial deterministic analysis
→ Legal / Business structured LLM
→ Verifier / Document Supervisor
→ governed Market Context + Skills
→ authentic model signal when governed input exists
→ Conflict / bounded re-check
→ LLM Final Supervisor + explicit deterministic fallback
→ Agent / Tool / Evidence Trace
→ Report / UI / API
→ optional Human Review
→ M1 / M2 / M3 / M5 evaluation + release audits
```

## 指标与治理

```text
M1 Existing-Gold Risk Accuracy >=0.80
M2 Existing-Gold Evidence Coverage Recall >=0.85
M3 Traceability =1.0
M5 = 1D / 5D / 20D / 60D，5D 重点
```

`COMPETITION_METRIC_PROTOCOL.md` 中历史 M4 explanation rubric 继续保留用于可选质量诊断和 Human Review 功能，但**不要求新增真人标注，也不参与当前 Release Gate**。

提交期加速不改变硬边界：

- Existing Gold immutable，`UNJUDGED != negative`；
- Gold 不进入 runtime Retriever / Prompt / Agent；
- Validation 只能 freeze 后 one-shot；
- 2025 Blind 不用于优化；
- LLM 不得创造越界 Evidence / market fact；
- 精确财务数值由 deterministic `Calculation` 支撑；
- Market PIT-safe，缺失不补零、不造 proxy；
- fallback 不冒充 real-provider accepted；
- UI 不伪造 Market / Model / Evidence / bbox；
- 不提交 Secret、授权 PDF、raw EOD、本地绝对路径或未授权模型。

## 快速入口

```bash
pip install -e ".[dev,retrieval-research]"
python -m compileall -q app src scripts
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_competition_runtime.py
python scripts/validate_v045_role_d_receipt.py
python scripts/check_v045_product_runtime.py
python scripts/check_v045_team_clone_ready.py
```

## 离线三案例回放

仓库自带 hash-bound canonical replay：`reports/v045_demo_bundle`。

```text
recorded runtime SHA = 3d81e5d0d71aeb5ffc76e3f123e8eecb5c75af8d
runtime-equivalent release baseline = 802bf5095e0db6a604dcb762e1070563f8cb1b34
team-ready merge = PR #185 / 732c5fd7b609b1a6589630b6e6a559c117206747
Gate E1 = 3/3
M3 = 1.0 x 3
Market / Model = 3/3
recheck = 17/17; budget-skipped = 0
seven-stage = 7/7 x 3
Evidence screenshot = 17/17 precise
bundle = 66 files / 7,528,749 bytes / hash verification PASS
fresh clone / Streamlit smoke / CI = PASS
```

```bash
python scripts/check_v045_team_clone_ready.py
# Windows
START_DEMO.bat
# macOS / Linux
./start_demo.sh
```

回放不需要招股书 PDF、API key 或 provider 网络；它不是新 PDF 的实时分析。完整说明见 [`docs/TEAM_QUICKSTART.md`](docs/TEAM_QUICKSTART.md)。

使用授权行情 ZIP 重建完整 438 案例 Market-X：

```bash
python scripts/prepare_v045_market_runtime.py --eod-archive <hkshareeodprices.zip>
```

## 文档入口

- 当前统一计划：[`docs/COMPETITION_CLOSURE_PLAN.md`](docs/COMPETITION_CLOSURE_PLAN.md)
- 最终 Release Gate：[`docs/V0.4_RELEASE_ACCEPTANCE.md`](docs/V0.4_RELEASE_ACCEPTANCE.md)
- B 线计划：[`docs/ROLE_B_M1_M2_PLAN.md`](docs/ROLE_B_M1_M2_PLAN.md)
- D 模型决议：[`docs/ROLE_D_MODEL_DECISION.md`](docs/ROLE_D_MODEL_DECISION.md)
- 冻结指标协议：[`docs/COMPETITION_METRIC_PROTOCOL.md`](docs/COMPETITION_METRIC_PROTOCOL.md)
- 最终提交：[`docs/SUBMISSION_RUNBOOK.md`](docs/SUBMISSION_RUNBOOK.md)

`COMPETITION_READY` 只能在当前 Release Acceptance 中仍然有效的真实 Gate、one-shot Validation、CI、Blind/provenance/determinism/security 与最终封包通过后使用。