# v0.4 PR-G 实施期发现清单

> Status: **FINDINGS / ADVISORY —— 交 A 审计裁定**
> Owner: **E — Oracle / Product Integration**
> Date: **2026-08-24**
> Base revision: `d9c640d`(PR-A…PR-F + Oracle v2 均 COMPLETE / FROZEN)
> 全部结论可由 `tests/` 与 `scripts/build_v04_pr_g_manifest.py` 复现

本文件记录在实现 PR-G 过程中发现的问题。**E 已在本 PR 内修复的**与**需要他人决定的**分开列出,措辞尽量贴近实测,不做推断性归因。

## 摘要

| # | 问题 | 归属 | 状态 |
|---|---|---|---|
| 1 | 运行时市场数据形状与受控 Market-X 是两套,运行时那套无人供给 | **C / A** | 🔴 未解决,PR-G 只能诚实降级 |
| 2 | PR-F 运行产物不入库,产品无法展示任何逐 case 模型分数 | **D / A** | 🔴 未解决,PR-G 只能给队列级证据 |
| 3 | 两个 blocking gate 常量指向已冻结的 Gate | E | ✅ 本 PR 修复 |
| 4 | `FinalSupervisionResult` 静默丢弃 conflicts | E | ✅ 本 PR 修复 |
| 5 | mock 市场快照会被朴素实现渲染成真实市场情境 | E | ✅ 本 PR 加护栏 |
| 6 | `presenters.markdown_report` 的 `!= 10` 分支 | E | ✅ 本 PR 修复 |
| 7 | `ReportSection.section_id` 默认 uuid4,报告不可内容寻址 | A | 🟡 v0.4 报告内已规避,公共 schema 未改 |
| 8 | `pipeline_stages` 阶段 3/4/5 仍写着已冻结的 Gate | E | 🟡 刻意留给 PR-H |
| 9 | 缺依赖时 pytest 是 collection 崩溃而非 skip | **A** | 🟢 沿用先前发现,未处理 |

---

## 1. 🔴 运行时市场数据形状与受控 Market-X 是两套

**归属:C(Market Data / PIT)/ A(跨模块契约)。这是 PR-G 市场通道无法可用的根本原因。**

仓库里存在两种市场数据形状:

| | 受控建模路径 | 运行时分析路径 |
|---|---|---|
| 类型 | `PreListingMarketFeatureSnapshot` | `MarketSnapshot`(v0.2 遗留) |
| 规模 | PR-B Core 30 维,438/438,PIT 已审计 | 9 个 float 字段 |
| 冻结记录 | `reports/frozen/v04_pr_b_market_x_core_manifest.json` | 无 |
| 谁消费 | PR-D canonical dataset → PR-E / PR-F | `MVPWorkflow.load_market` → Agent / Final Supervisor |

**三个受控 provider 的 `get_snapshot()` 都刻意返回 `source="unavailable"`:**

```python
# providers/competition_market.py:384
"reason": "legacy snapshot is not produced by the governed EOD adapter"

# providers/filtered_eod_v2.py:461
"reason": "legacy snapshot is not produced by the filtered EOD adapter"
```

`FilteredEODV2MarketDataProvider` 甚至**没有注册进 `market_data_provider` registry**(容器里只有 `mock` / `unavailable`),它只被 PR-C 的 label readiness 路径按类导入使用。

**后果:** 无论选哪个 config,运行时市场通道都只有两种结果 —— mock 的编造值(不可用)或 `unavailable`。PR-B 交付的受控 Market-X **无法为一次真实分析提供任何市场事实**。

**E 在 PR-G 中的处理:** 如实报 `UNAVAILABLE_ERROR` 并逐字透传 provider 自己的 reason,不猜测、不代偿、不用 mock 顶替。`SnapshotMarketContextProvider` 的 `feature_manifest_hash` 恒为 `None`,并在 provenance 标注 `legacy_market_snapshot_not_v04_market_x` —— **snapshot 派生的视图不得声称 PR-B 血统**。

**需要 C / A 决定:** 是否要一个 `PreListingMarketFeatureSnapshot → MarketSnapshot` 的适配器,或让 `MarketContextProvider` 直接消费受控形状。**这不是 E 能单方面决定的** —— 它改变运行时消费的市场数据契约,属于 C 的 lane 与 A 的跨模块审查范围。

---

## 2. 🔴 PR-F 运行产物不入库,产品拿不到逐 case 模型分数

**归属:D(Quant / ML)/ A(产物政策)。**

`reports/frozen/v04_pr_f_lightgbm_manifest.json` 记录 `runtime_artifacts_committed: false`,`reports/v04_pr_f/` 不在仓库中。逐 case 分数与 SHAP drivers 只存在于 `model_results.json`,而该文件不入库。

**后果:** 全新 checkout 上,任何 IPO 都拿不到模型分数。产品能说的只有队列级事实。

**E 在 PR-G 中的处理:** 两层设计。

- **Tier 1(队列级,始终可用)** —— 从已提交的 freeze manifest 读模型身份、校准状态与两组 ablation 区间,fail-closed 校验 `status` / `formal_gate_passed` / **`blind_2025_y_accessed`** / 校准状态 / 语义;
- **Tier 2(逐 case,可选)** —— 若配置了本地 PR-F 运行目录,**先用 `model_result_hash` 与冻结值绑定再消费任何数字**,不符即整体拒绝(`local_pr_f_artifacts_do_not_match_the_frozen_hash`),绝不部分采用。代码与合成 fixture 测试已完整,产物就位后无需改代码即生效。

**需要 D / A 决定:** 是否把 `case_predictions` 与 `single_ipo_drivers` 以受控小体量形式入库(它们不含 2025 blind y),还是接受产品长期只能给队列级证据。

---

## 3. ✅ 两个 blocking gate 常量指向已冻结的 Gate

`agents/market_context.py:14 PENDING_MARKET_GATE = "PR-B"` 与 `agents/final_supervisor.py:19 PENDING_MODEL_GATE = "PR-F"` —— 两个 Gate 都已 COMPLETE / FROZEN。

一份写着「market channel blocked by PR-B」的报告,是**治理关键产物里的事实错误**。真正缺的不是 Gate,是运行时接线与产物(见 §1 / §2)。

**已修复:** 缺席通道判为 `DISABLED` 且 `blocking_gate=None`,reason 为「not configured in this runtime」—— 能力陈述,而非 Gate 陈述。`metadata["blocking_gates"]` 为 `[]`。契约测试同步更新。

## 4. ✅ `FinalSupervisionResult` 静默丢弃 conflicts

`V03Supervisor` 确实产出 `RiskConflict`(如 `revenue_semantics`),但 `FinalSupervisionResult` 此前**没有 conflicts 字段**,组合时被静默丢弃 —— 与 `V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md` §7.2 自称的「保留冲突」直接矛盾。

**已修复:** 新增 `conflicts: tuple[RiskConflict, ...]`,逐字保留并计入 `metadata["unresolved_conflict_count"]`。**仍不做仲裁** —— 仲裁链路是 CH-4,在 PR-H 之后。

## 5. ✅ mock 市场快照的编造值会被朴素实现渲染出来

`MockMarketDataProvider` 返回 `hsi_return_5d=-0.04`、`recent_ipo_break_rate=0.42`、`market_volatility=0.31`、`sentiment_score=35` —— 全是 fixture 值。一个「字段非空即渲染」的实现会把它们当成真实市场情境。

**已加护栏:** 可用性**以 `snapshot.source` 判定,不以字段非空判定**;mock 源一律 `DISABLED` 且 `observations=()`。两处测试硬断言那四个数字从不出现在序列化视图中(`test_market_context_provider.py`、`test_v04_final_supervision_pipeline.py`)。

## 6. ✅ `presenters.markdown_report` 的 `!= 10` 分支

`app/presenters.py` 原本按 `len(result.report_sections) != 10` 决定是否渲染完整风险明细。任何非十节报告(包括 mock 的短报告)都会在**每一节**重复渲染全部风险。

**已修复:** 改为 `< 10`,三种情况行为都正确(mock < 10 全渲染;v0.3 == 10 只渲染 3/4/5;v0.4 == 13 只渲染 3/4/5)。

## 7. 🟡 `ReportSection.section_id` 默认 uuid4

`schemas/__init__.py:318` 用 `uuid4` 作默认,同一份输入两次生成的报告 section_id 不同,**报告不可内容寻址**。

**E 的处理:** 只在 `V04ReportGenerator` 内设 `section_id=f"v04-section-{order:02d}"`,**不改公共 schema** —— 改默认值会影响 v0.3 已冻结的报告契约。

**需要 A 决定:** 公共 schema 是否应改为确定性 id。PR-H 若要对最终报告做内容寻址或审计留痕,这条会再次出现。

## 8. 🟡 `pipeline_stages` 阶段 3/4/5 仍写着已冻结的 Gate

UI 阶段模型里,Market Features 仍标 `PR-B`、Prediction 与 Explainability 仍标 `PR-F` —— 与 §3 同类的过时表述。

**刻意未改:** 那是 PR-H 的阶段模型,改动会连带影响四条断言。本 PR 只修了阶段 6(Final Supervisor),因为它正是 PR-G 交付的对象。**PR-H 应一并清理 3/4/5。**

## 9. 🟢 缺依赖时 pytest 是 collection 崩溃而非 skip

沿用先前发现,未变化。仓库没有 `conftest.py`、没有注册 marker、没有 `importorskip`;`tests/ranking/` 硬 import lightgbm,缺失时整个 suite 中断。macOS 还需系统级 `brew install libomp`。

「缺依赖时 skip 还是 hard-fail」是治理决策 —— 改成 skip 而 CI 某天掉了 extra,PR-F 的真实回归会静默变绿。**建议 A 决定,并配一个「CI 确实装了预期 extra」的断言。**

---

## 附:本 PR 中被既有护栏抓住的一次错误

实现接线时,E 曾无条件给 `_component_modes()` 增加两行,导致
`tests/integration/test_real_financial_workflow.py` 失败(它断言 `component_modes` 的精确字典)。

**修的是代码,不是护栏** —— 改为「未构建的通道不增任何键」,与 metadata surface 的判断口径一致。这条记录在此,是因为它证明那批「必须保持不变的回归护栏」确实在起作用。
