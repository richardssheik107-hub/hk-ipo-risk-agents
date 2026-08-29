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

## 当前冲刺模式

项目已切换到 **Frontend-First Parallel Submission Sprint**：

```text
当前案例阶段真实跑完 → 前端可以绿色“已完成”
可选 Market / Model / real-LLM 缺失 → 在绿色阶段内部明确 unavailable / fallback
最终 M1/M2/M4/D/C/E/Validation Gate → 继续严格保留，只卡最终提交宣称
```

这意味着团队不再按旧 Gate 串行排队。B/C/D/E、UI/API、Report、Trace、Evidence、capability demo 可以并行补齐；普通安全 PR 不需要等待所有最终比赛指标先通过。

## 赛题目标

1. 对数百页港股招股书进行防幻觉解析，抽取财务、法务和业务隐性风险；
2. 让 Financial、Legal、Business、Market 与 Final Supervisor 协作、冲突查证并保留完整 Trace；
3. 输出带原 PDF 页码、Evidence / bbox / 截图的风险报告，并用上市后 1D / 5D / 20D / 60D 表现验证业务参考价值。

## 最新状态

| 维度 | 当前已合入事实 | 最终关闭标准 |
|---|---|---|
| B M1 | fixed-journal `12/30 = 40.00%` | ALL 79 Development `>=80%` |
| B M2 | fixed-journal `17/48 = 35.42%` | ALL 79 Development `>=85%` |
| B fresh gated | `10/30` M1、`15/48` M2；37/40 structured valid | 继续 Development 泛化 |
| M3 Traceability | final-three 三案例 `3/3 = 1.0`，已进入 canonical replay | 保持 100% |
| Final Supervisor | Gate E1 `3/3`；real-provider 首次接受 `3/3`；correction/fallback `0` | final evidence 稳定；fallback 不计 remote success |
| Market | final-three receipt-bound Core runtime `3/3 available`；全量 438 案例可由授权 ZIP 一键重建 | 保持 PIT / provenance 合同 |
| Evidence screenshot | final-three `17/17`，精确 quote/snippet 定位 `100%` | 保持 PDF hash / page / bbox / screenshot hash 绑定 |
| M4 | `0/6` 真人评审 | 每案 2 名独立评审并通过 rubric |
| M5 formal | current-main 70-case 四文件与 receipt 哈希一致；D1 `12/12 PASS` | 保持 deterministic / Blind 边界 |
| M5 v2 candidate | Recall `52.17%`、F1 `42.11%`、PR-AUC `38.12%`，未晋升 | A governance decision + 新 freeze/handoff |
| 产品 | final-three Market / frozen Model `3/3 available`；每案七阶段 `7/7`；canonical bundle `66` 文件并通过哈希验证 | capability demos + final submission bundle |

Frozen PR-F 的五日 Recall `4.35%`、ROC-AUC `0.4246` 仍不足以宣称强预测效果。v2 candidate 改善了高召回 operating point，但正式产品在新 promotion/freeze 前不能把它冒充 frozen model。

## 当前优先级

### P0 — 尽快看到完整产品结果

让一个真实 current-case 直接走通：

```text
Document Analysis
→ Document Risk Features
→ Market Features
→ Prediction
→ Evidence / Explainability
→ Final Supervisor
→ Final Risk Report
```

阶段绿色只表示本次产品步骤真实完成；Market/Model/LLM 等可选通道若缺失，继续在页面内诚实显示 unavailable/fallback。

### 并行推进

- **B**：Parser / retrieval / extraction / fact conversion / LLM stability / binding → ALL 79 Development；
- **C**：Market final-three strict runtime、comparable IPO / valuation；
- **D**：model decision、strict revalidation、final-three handoff、prediction table；
- **E**：Supervisor 稳定性、Human Review、case reports；
- **Product**：pipeline/text embellishment/related-party/valuation cases、精确 Evidence screenshot、API/UI、演示备份。

完整计划：[`docs/COMPETITION_CLOSURE_PLAN.md`](docs/COMPETITION_CLOSURE_PLAN.md)。

## 系统架构

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial deterministic analysis
→ Legal / Business structured LLM
→ Verifier / Document Supervisor
→ governed Market Context + Skills
→ optional authentic model signal
→ Conflict / bounded re-check
→ LLM Final Supervisor + explicit deterministic fallback
→ Agent / Tool / Evidence Trace
→ Human Review / Report / UI
→ M1–M5 evaluation / readiness / package
```

Role-B v0.4.6 提供：

```text
offline baseline
+ real-LLM shadow probe
+ journal-replayed gated result
+ read-only persisted-result Evidence audit
→ monotonicity / retrieval waterfall / LLM quality / provenance diagnostics
```

## 指标与治理

```text
M1 Existing-Gold Risk Accuracy >=0.80
M2 Existing-Gold Evidence Coverage Recall >=0.85
M3 Traceability =1.0
M4 Explanation Quality = human-review rubric
M5 = 1D / 5D / 20D / 60D，5D 重点
```

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

仓库自带 hash-bound canonical replay：`reports/v045_demo_bundle`。它保留真实运行
SHA `3d81e5d0d71aeb5ffc76e3f123e8eecb5c75af8d`；该运行与发布基线
`802bf5095e0db6a604dcb762e1070563f8cb1b34` 的 Git 审计差异只有 Role-D CI workflow，
因此没有改写 provenance，也不需要重复消耗一次真实 provider 运行。

```bash
python scripts/check_v045_team_clone_ready.py
# Windows
START_DEMO.bat
# macOS / Linux
./start_demo.sh
```

回放不需要招股书 PDF、API key 或 provider 网络；它不是新 PDF 的实时分析。完整说明见
[`docs/TEAM_QUICKSTART.md`](docs/TEAM_QUICKSTART.md)。

使用授权行情 ZIP 重建完整 438 案例 Market-X（CSV 会在系统临时目录解压，
不会写入 Git checkout）：

```bash
python scripts/prepare_v045_market_runtime.py --eod-archive <hkshareeodprices.zip>
```

Role-B：

```bash
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
python scripts/run_v046_role_b_ablation.py --subset-only
python scripts/check_v046_role_b_structured_smoke.py
python scripts/run_v046_role_b_ablation.py --run-id <RUN_ID> --modes all --execute
```

真实运行需要本地授权招股书目录与 provider 凭证；不得使用 mock 冒充 real-LLM。

## 文档入口

- 当前统一计划：[`docs/COMPETITION_CLOSURE_PLAN.md`](docs/COMPETITION_CLOSURE_PLAN.md)
- 最终 Release Gate：[`docs/V0.4_RELEASE_ACCEPTANCE.md`](docs/V0.4_RELEASE_ACCEPTANCE.md)
- B 线计划：[`docs/ROLE_B_M1_M2_PLAN.md`](docs/ROLE_B_M1_M2_PLAN.md)
- D 模型决议：[`docs/ROLE_D_MODEL_DECISION.md`](docs/ROLE_D_MODEL_DECISION.md)
- 指标协议：[`docs/COMPETITION_METRIC_PROTOCOL.md`](docs/COMPETITION_METRIC_PROTOCOL.md)
- 最终提交：[`docs/SUBMISSION_RUNBOOK.md`](docs/SUBMISSION_RUNBOOK.md)

`COMPETITION_READY` 只能在全部真实 Release Gates、one-shot Validation、CI、Blind/provenance/determinism/security 与最终封包通过后使用。
