# HK IPO Risk Agents — v1.0.0

面向东吴证券港股 IPO 赛题的多智能体风险分析与上市后预警系统。

> Release：`v1.0.0`  
> Competition runtime protocol：`v0.4.5`  
> Role-B evaluation track：`v0.4.6`  
> Metric protocol：`v045_competition_metric_protocol_v2_existing_gold_only`  
> Runtime freeze main：`ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> 状态日期：`2026-08-30`  
> Release status：**COMPETITION SUBMISSION PRODUCT RELEASE**  
> Internal readiness：**NOT COMPETITION_READY under the self-defined G2 gate**

`v1.0.0` 是本项目的比赛最终产品发布版：功能、运行时、Market-X、Frozen Model / SHAP、前端、能力证明和提交文档均已进入冻结/回归保护状态。该版本不把未达到的内部 G2 指标改写成 PASS；“正式发布”表示产品版本完成并可用于比赛提交，不等于内部自定义 `COMPETITION_READY` 条件全部满足。

## Final Development truth

| 模式 | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | **70/102 = 68.63%** | **103/191 = 53.93%** |
| Real LLM gated | 79/79 | **61/102 = 59.80%** | **93/191 = 48.69%** |

正式 provider-backed Development 结果是 Real LLM gated。较高的 offline 结果仅保留为工程参考，不能替代真实 LLM 指标。

仓库自定义 G2 门槛仍为：

```text
ALL79 Development
M1 >= 80%
M2 >= 85%
real_llm_cases = 79/79
```

因此 G2 保持 **BLOCKED**。

## v1.0.0 核心能力

```text
Real prospectus PDF parsing + physical-page Evidence
Financial / Legal / Business Agents
Calculation + specialized Verifier
Document supervision + Final Supervisor
Conflict detection + bounded re-check
Dynamic Market-X with PIT-safe provenance and honest missingness
Frozen Role-D V2 runtime inference + native SHAP
Offline Demo Replay
Historical Governed IPO
Fresh New-IPO Analysis
Judge-facing Streamlit workspace
Evidence screenshot / trace / single-case report / batch report
API / UI product surfaces
```

## 回归保护基线

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

`v1.0.0` 的产品发布决议不会修改这些 Gate 的真实状态。

## 正式机器事实源

```text
reports/v045_role_b/document_benchmark_summary.json
reports/final_status/final_freeze_manifest.json
reports/final_status/submission_closeout_status.json
reports/final_status/product_acceptance.json
reports/final_status/capability_manifest.json
reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json
```

## 三种产品模式

1. **Offline Demo Replay** — 无需 PDF、API key 或网络，使用 hash-bound canonical replay。
2. **Historical Governed IPO** — 对受治理历史案例运行真实 Market / Model / Document 链路。
3. **Fresh New-IPO Analysis** — 对新 PDF 进行实时文档分析，并在合法 PIT 数据覆盖范围内生成 Market-X / frozen model / SHAP；覆盖不足时诚实返回 `PARTIAL / UNAVAILABLE`。

所有 `AVAILABLE / PARTIAL / UNAVAILABLE / ERROR` 均来自 runtime contract。UI 不补 Market、Model 或 Evidence，也不把模型异常解释为低风险。

## 快速开始

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

python -m pip install --upgrade pip
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

答辩/演示入口：

| 入口 | Windows | macOS / Linux |
|---|---|---|
| 统一分析工作台 | `START_DEMO.bat` | `./start_demo.sh` |
| 统一评审入口（兼容命令） | `START_JUDGE_DEMO.bat` | `./start_judge_demo.sh` |

启动脚本会先执行 runtime / clone-ready preflight；失败时不会继续启动半可用界面。

## 治理边界

- Existing Gold immutable，`UNJUDGED != negative`；
- Gold 不进入 runtime Retriever / Prompt / Agent；
- 2024 Validation 只允许冻结后 one-shot；
- 2025 Blind outcome 不用于优化；
- 不按公司、股票、case、页码、Gold 文本 hardcode；
- LLM 不 invent Evidence / market fact；
- exact numeric claim 由 deterministic Calculation 支撑；
- Market PIT-safe，missing 不等于 zero；
- model score 是 `uncalibrated_model_score`，不是概率；
- fallback 不冒充 real-provider success；
- Secret、授权 PDF、raw EOD、raw provider journal、本地绝对路径不进入公开仓库或 submission bundle。

## v1.0.0 提交后仍需在授权环境完成

这些是比赛提交治理/包装动作，不再属于产品功能研发：

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

- [`docs/RELEASE_NOTES_V1.0.0.md`](docs/RELEASE_NOTES_V1.0.0.md) — v1.0.0 正式发布说明
- [`docs/V1_RELEASE_ACCEPTANCE.md`](docs/V1_RELEASE_ACCEPTANCE.md) — **v1.0.0 Release / Gate 真相源**
- [`docs/FINAL_SUBMISSION_STATUS.md`](docs/FINAL_SUBMISSION_STATUS.md) — 最终比赛提交状态与材料清单
- [`docs/COMPETITION_CLOSURE_PLAN.md`](docs/COMPETITION_CLOSURE_PLAN.md) — 冻结后的最终收口状态
- [`docs/COMPETITION_METRIC_PROTOCOL.md`](docs/COMPETITION_METRIC_PROTOCOL.md) — 冻结指标协议
- [`docs/SUBMISSION_RUNBOOK.md`](docs/SUBMISSION_RUNBOOK.md) — Validation / fresh clone / secure package 操作手册
- [`docs/TEAM_QUICKSTART.md`](docs/TEAM_QUICKSTART.md) — fresh clone / canonical replay
- [`docs/ROLE_D_MODEL_DECISION.md`](docs/ROLE_D_MODEL_DECISION.md) — Role-D V2 决策与模型边界

历史 v0.4 / Batch / Bundle / research 文档仅用于 provenance 与技术追溯，不再作为当前版本状态源。
