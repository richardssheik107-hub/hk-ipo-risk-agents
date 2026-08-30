# HK IPO Risk Agents

面向东吴证券港股 IPO 赛题的多智能体风险分析与上市后预警系统。

> Competition runtime：`v0.4.5`  
> Role-B evaluation track：`v0.4.6`  
> Metric protocol：`v045_competition_metric_protocol_v2_existing_gold_only`  
> Runtime freeze main：`ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> 状态日期：`2026-08-30`  
> 当前结论：**SUBMISSION CLOSEOUT / NOT COMPETITION_READY UNDER THE SELF-DEFINED G2 GATE**

项目已经从功能开发阶段进入最终提交收口。Market-X、Frozen Model / SHAP、前端产品、能力证明与主 CI 已关闭；Document Intelligence 的最终 ALL79 已完成，但未达到仓库自己定义的 G2 门槛。最终状态与材料清单见 [`docs/FINAL_SUBMISSION_STATUS.md`](docs/FINAL_SUBMISSION_STATUS.md)。

## Final Development truth

| 模式 | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | **70/102 = 68.63%** | **103/191 = 53.93%** |
| Real LLM gated | 79/79 | **61/102 = 59.80%** | **93/191 = 48.69%** |

正式 G2 自定义门槛仍为：

```text
ALL79 Development
M1 >= 80%
M2 >= 85%
real_llm_cases = 79/79
```

因此 G2 必须保持 **BLOCKED**。较高的 offline 结果只作为工程参考，不能替代 provider-backed real-LLM gated 结果。

## 当前稳定产品能力

```text
Real prospectus PDF parsing + physical-page Evidence
Financial / Legal / Business Agents
Calculation + specialized Verifier
Final Supervisor + conflict / re-check
Dynamic Market-X with PIT / honest missingness
Frozen Role-D V2 inference + native SHAP
Offline Demo Replay
Historical Governed IPO
Fresh New-IPO Analysis
Judge-facing Streamlit workspace
Evidence screenshot / trace / single & batch reports
```

当前回归保护基线：

```text
Final Supervisor E1 = 3/3
M3 traceability = 1.0 x 3
Market final-three = 3/3
Model final-three = 3/3
recheck = 17/17
seven-stage = 21/21
Evidence screenshots = 17/17 precise
canonical replay = 3 cases / 66 files
Team demo runtime = PASS
Role D runtime = PASS
main tests = PASS
```

## Release Gate 状态

| Gate | 状态 |
|---|---|
| G0 Runtime / contracts / CI | PASS |
| G1 Stable final-three baseline | PASS |
| G2 ALL79 Document Intelligence | **BLOCKED** |
| G3 Dynamic Market-X | PASS |
| G4 Dynamic Model / SHAP | PASS |
| G5 Final Frontend / Product | PASS |
| G6 Capability demonstrations | PASS |
| G7 Freeze / Validation / package | **PARTIAL** |

正式机器事实源：

```text
reports/v045_role_b/document_benchmark_summary.json
reports/final_status/final_freeze_manifest.json
reports/final_status/product_acceptance.json
reports/final_status/capability_manifest.json
```

One-shot Validation receipt 与最终 secure package 尚待在授权/干净环境中执行和生成。

## 三种产品模式

最终 UI 支持：

```text
1. Offline Demo Replay
2. Historical Governed IPO
3. Fresh New-IPO Analysis
```

所有 `AVAILABLE / PARTIAL / UNAVAILABLE / ERROR` 必须来自真实 runtime contract。UI 不补 Market/Model/Evidence，不把模型异常解释成低风险。

## 治理边界

- Existing Gold immutable，`UNJUDGED != negative`；
- Gold 不进入 runtime Retriever / Prompt / Agent；
- 2024 Validation 只允许 freeze 后 one-shot；
- 2025 Blind outcome 不用于优化；
- 不按公司、股票、case、页码、Gold 文本 hardcode；
- LLM 不 invent Evidence / market fact；
- exact numeric claim 由 deterministic Calculation 支撑；
- Market PIT-safe，missing 不等于 zero；
- model score 是 `uncalibrated_model_score`，不是概率；
- fallback 不冒充 real-provider success；
- Secret、授权 PDF、raw EOD、raw journal、本地绝对路径不进入 Git / submission bundle。

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
python scripts/check_final_product_capabilities.py
```

离线答辩入口：

| 入口 | Windows | macOS / Linux |
|---|---|---|
| 标准分析工作台 | `START_DEMO.bat` | `./start_demo.sh` |
| 评委展示界面 | `START_JUDGE_DEMO.bat` | `./start_judge_demo.sh` |

启动脚本会先做 runtime / clone-ready preflight；失败时不会继续启动一个半坏的界面。

## 最终提交前还要完成

```text
one-shot ALL19 Validation
→ one_shot_validation_receipt.json
→ final G5/G6 rehash
→ fresh-clone verification
→ security / licensing / path audit
→ final artifact index
→ secure submission ZIP + SHA256SUMS
→ PPT / 讲稿 / 演示视频或录屏（按比赛平台要求）
```

## 文档入口

- [`docs/FINAL_SUBMISSION_STATUS.md`](docs/FINAL_SUBMISSION_STATUS.md) — **最终提交状态、已完成/未完成、材料清单**
- [`docs/V0.4_RELEASE_ACCEPTANCE.md`](docs/V0.4_RELEASE_ACCEPTANCE.md) — **唯一实时 Release Gate**
- [`docs/COMPETITION_CLOSURE_PLAN.md`](docs/COMPETITION_CLOSURE_PLAN.md) — 最终收口执行顺序
- [`docs/COMPETITION_METRIC_PROTOCOL.md`](docs/COMPETITION_METRIC_PROTOCOL.md) — 冻结指标协议
- [`docs/SUBMISSION_RUNBOOK.md`](docs/SUBMISSION_RUNBOOK.md) — freeze / Validation / 打包 Runbook
- [`docs/TEAM_QUICKSTART.md`](docs/TEAM_QUICKSTART.md) — fresh clone / canonical replay
- [`docs/ROLE_D_MODEL_DECISION.md`](docs/ROLE_D_MODEL_DECISION.md) — Role-D frozen model 决策证据

历史 Batch / Bundle 只作为研究和 provenance 记录，不再作为当前状态源。
