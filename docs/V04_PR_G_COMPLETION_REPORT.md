# v0.4 PR-G 完成报告 — Market Agent + Final Supervisor

> Status: **COMPLETE / FROZEN**
> Owner: **E — Oracle / Product Integration**
> Review: **A — cross-module contract / provenance / reproducibility**
> Date: **2026-08-24**
> Frozen manifest: `reports/frozen/v04_pr_g_final_supervision_manifest.json`

## 1. Gate 要求与达成情况

`docs/ROADMAP.md` 对 PR-G 的要求:

> 正确消费 frozen score、保持 `uncalibrated_model_score` 语义、可追溯 Evidence、明确 uncertainty,并完成真实 PDF → Final Report 闭环。

| 要求 | 达成方式 | 验证 |
|---|---|---|
| 正确消费 frozen score | `modeling/frozen_model_evidence.py` 读已提交的 PR-F freeze manifest,fail-closed 校验 status / gate / blind / 校准状态 / 语义 | `tests/unit/test_frozen_model_evidence.py` |
| `uncalibrated_model_score` 语义 | `ModelPredictionView.score_semantics` 默认即该术语(与 PR-F `lightgbm_modeling.py:156` 一致),且**没有 `probability` 字段** | 契约测试内省 `model_fields` |
| 可追溯 Evidence | Final Supervisor 引用的每个 risk / evidence id 均为输入子集;报告第 9 节引用的 evidence 全部可在第 10 节索引解析 | 真实 PDF 实测 `referenced=2 indexed=2 全部可解析=True` |
| 明确 uncertainty | 四通道 `ChannelState` + `uncertainty_statement`,按固定顺序拼装 | `tests/contract/test_v04_final_supervisor.py` |
| 真实 PDF → Final Report 闭环 | 7.6 MB / 706 页真实招股书跑通 `configs/v04_offline.yaml`,产出 13 节报告 | 下方 §3 |

## 2. 交付内容

| 组件 | 位置 |
|---|---|
| 冻结 PR-F 证据适配器(两层) | `src/ipo_risk/modeling/frozen_model_evidence.py` |
| 市场情境 provider | `src/ipo_risk/agents/market_context.py::SnapshotMarketContextProvider` |
| Final Supervisor | `src/ipo_risk/agents/final_supervisor.py::V04FinalSupervisor` |
| 结构化通道类型 | `src/ipo_risk/schemas/final_supervision.py`(新增 `MarketObservation` / `ModelDriver`,`FinalSupervisionResult` 新增 `conflicts` / `market_context` / `model_prediction`) |
| 13 节报告 | `src/ipo_risk/reporting/v04.py::V04ReportGenerator` |
| 配置 | `configs/v04_offline.yaml`、`configs/v04_ai.yaml` |
| 冻结 manifest 草案生成 | `scripts/build_v04_pr_g_manifest.py` |
| Deterministic A freezer | `scripts/freeze_v04_pr_g_manifest.py` |
| Frozen manifest | `reports/frozen/v04_pr_g_final_supervision_manifest.json` |

## 3. 真实闭环实测

```text
config: v04_offline | parser=pymupdf retriever=keyword
        market_context=snapshot final_supervisor=v04 report=v04

status=completed  verified=1  sections=13

[7] Market Context
    Market context unavailable_error: real_market_data_not_integrated_in_v0.2.
    No market observation is reported.

[8] Model Signal and Uncertainty
    No per-case model score is available for this IPO. The frozen cohort evidence
    below states what the model was and was not able to establish.

[9] Final Supervisor Synthesis
    Channels: document=available, market=unavailable_error, model=disabled, rule=available.

追踪性:referenced=2  indexed=2  全部可解析=True
```

## 4. 三个刻意的诚实降级

**市场通道在当前所有 config 下都不可用,这是正确结果。** `CompetitionCSVMarketDataProvider.get_snapshot()` 返回 `source="unavailable"`,provider 自己的 reason 被**逐字透传**而非改写。`MockMarketDataProvider` 返回编造数值(`hsi_return_5d=-0.04` 等),因此 mock 快照一律判为 `DISABLED` 且 `observations=()` —— 有测试硬断言那几个数字从不出现在序列化视图中。

**模型通道只有队列级证据,没有逐 case 分数。** PR-F 的运行产物 `runtime_artifacts_committed: false`,不在仓库中。Tier 2(逐 case 分数 + SHAP drivers)代码完整并有合成 fixture 测试,消费前先用 `model_result_hash` 与冻结值绑定,不符即整体拒绝;产物就位后无需改代码即生效。

**冻结区间跨零时不呈现正负号。** PR-F 的 `production_pm_minus_m` 区间为 `[0.0, 0.0]`、`oracle_om_minus_m` 为 `[-0.3171, 0.2917]`,两者都跨零。报告只输出「not validated at this sample size」,**不输出 `-0.0143`**。`docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md` 禁止的 useless / no signal 等措辞由测试词表拦截。

## 5. 接线是严格 opt-in

`Settings.market_context` / `final_supervisor` 默认 `"none"`(容器级哨兵,不构建任何组件),`pr_f_run_dir` 默认为空。

```text
configs/mock.yaml       13 nodes   market_context=none      final_supervisor=none
configs/v03_offline.yaml 13 nodes   market_context=none      final_supervisor=none
configs/v04_offline.yaml 15 nodes   market_context=snapshot  final_supervisor=v04
```

图节点顺序被强制:`market_context` 紧随 `load_market_snapshot`(失败被 `_safe` 隔离并单独记 `AgentLog`),`final_supervisor` 位于 `predictor` 与 `report` 之间(它消费 rule prediction)。既有 9 位置参数构造 workflow 的调用点保持可用 —— 新参数是 keyword-only。

`tests/contract/test_v04_wiring_is_opt_in.py` 对 7 个既有 config 断言节点集合不变、两个通道为 `None`。

## 6. 需要 A 审阅的受保护改动

| 文件 | 改动 | 理由 |
|---|---|---|
| `src/ipo_risk/agents/base.py` | `MarketContextProvider.context()` 增 `market` 参数 | 否则 provider 需自取快照,一次分析内可能出现两个不同快照,是 provenance 隐患 |
| `src/ipo_risk/core/config.py` | 三个新 `Settings` 字段,默认全关 | 接线开关;`load_settings` 会静默丢弃未声明的 YAML 键 |
| `src/ipo_risk/core/container.py` | 注册两个通道 + `V04ReportGenerator`;`NO_COMPONENT` 哨兵 | — |
| `src/ipo_risk/workflows/state.py` | 三个替换型键 | 纯追加 |
| `src/ipo_risk/workflows/mvp_v1.py` | 两个条件节点 | 条件构建,legacy config 图形不变 |
| `src/ipo_risk/services/analysis_service.py` | 按存在性 surface 两个通道 | 未运行的通道不增任何键,`component_modes` 亦然 |

## 7. 明确未做

- **不做实时模型推理** —— 不加载 `models/*.txt` 给新 IPO 打分;`case_predictions` 之外没有分数;
- **不做冲突仲裁** —— conflicts 逐字保留,`unresolved_conflict_count` 如实计数。仲裁链路是 CH-4,在 PR-H 之后;
- **不加 `probability` / 校准 / horizon 字段** —— 校准是未来 PR-F 交付物,1D/20D/60D 由计划单独版本化,不得反向篡改冻结的 5D policy;
- **不原地改 `V03ReportGenerator`** —— 其十节形状被测试钉死,v0.4 用子类扩展;
- **未触碰任何冻结模块或 `reports/frozen/`**。

## 8. Final local freeze

The final A freeze used the authoritative 2410.HK catalog identity and listing date (`2024-08-20`) with the real 706-page prospectus. The run completed with 13 report sections and resolved all 2/2 referenced Evidence ids. It honestly retained `market=unavailable_error` and `model=disabled`; it did not fabricate data merely to make the manifest look complete.

```text
prospectus_sha256              6c8179a58ac265d5a729895ef30db910dc15cee0a53ce653e866d487d29655cb
final_supervision_content_hash aed6b40ff10afe0e41f9aefcaedf8c6cb48626ac4dbdda8fc2fa2489055a7564
freeze_manifest_hash           84b349fd912e56dbd5aa9768ea0fd462ce22da25e11dfe4cd581f40a0c1bcd97
formal_gate_passed             true
blind_2025_y_accessed          false
```

## 9. 验证

```bash
.venv/bin/python -m pytest -q --ignore=tests/ranking
```

```bash
PYTHONPATH=src .venv/bin/python scripts/build_v04_pr_g_manifest.py \
  --prospectus <LOCAL_PROSPECTUS> --company <NAME> --stock-code <CODE> \
  --output-dir reports/v04_pr_g
```

该脚本**拒绝** `--output-dir reports/frozen`。冻结是 A 的 Gate review 动作,`formal_gate_passed` 只能由 A 置为 true。

`tests/ranking/` 本地因缺系统 `libomp` 排除;CI 装 extra 跑全量。
