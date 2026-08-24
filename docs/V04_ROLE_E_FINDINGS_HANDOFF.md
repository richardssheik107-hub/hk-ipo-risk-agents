# v0.4 Role E 发现清单与交接

> Status: **ADVISORY —— 不要求重开任何已冻结的 Gate**
> Owner: **E — Oracle / Product Integration**
> Issued **2026-08-22** · Revised **2026-08-23** · **Closed out 2026-08-24**
> Base revision: `716cf76`（PR-A/B/C/D + Oracle v2 + PR-E + PR-F 均 COMPLETE / FROZEN；当前正式 Gate = **PR-G**）

## 摘要：8 条发现，7 条已关闭

| # | 发现 | 归属 | 现状 |
|---|---|---|---|
| 1 | PR-E 的 development CV 是随机分折 | D | ✅ **已修复** |
| 2 | Oracle 可用队列口径 | D | ⬆️ **被取代**（Oracle v2 77 / 19 为权威） |
| 3 | Oracle artifact 身份取自标注 packet | A / D | ✅ **已修复** |
| 4 | Oracle validation 覆盖为 0 | — | ✅ 已解决 |
| 6 | ROADMAP / README 状态失真 | A | ✅ 已解决 |
| 8 | PR-A 冻结记录与现实不符 | A | ✅ **政策解决** |
| 7 | 缺依赖时 pytest collection 崩溃 | **A** | 🟢 未处理，非阻塞 |
| **5** | **统计功效不足** | **D** | 🔴 **未处理 —— 唯一仍然活着的一条** |

E 在此过程中**没有修改任何冻结模块**，也不对已冻结的 PR-E 结论主张回滚。

---

## 5. 🔴 统计功效：PR-E 的两个差值都在器械分辨率以下

**归属：D。定性：中立补充，不要求重开。**

PR-E 已 COMPLETE / FROZEN，正式结论为：

```text
PM − M   −0.0157   （Full Production 2024，n=70）
OM − M   −0.0571   （Oracle v2 2024 intersection，n=19）
→「current document classification signal is not robustly validated」
```

用 PR-E 自己的参数（M ROC-AUC = 0.567，正样本率约 36%）按 Hanley-McNeil 计算：

| 队列 | n | 正 / 负 | **最小可检测差异** | 观测值 | 占门槛 |
|---|---:|---|---:|---:|---:|
| Oracle v2 2024 | 19 | 7 / 12 | **0.391** | −0.0571 | **15%** |
| Full Production 2024 | 70 | 25 / 45 | **0.201** | −0.0157 | **8%** |

> **两个观测值分别只有可分辨门槛的 15% 和 8%；在这个量级上正负号不携带信息。**

**这不是说 PR-E 错了。** 其方法论（前向分折、同队列同预处理同模型族、fail-closed 漂移检查、拒绝把 score 表述为真实概率）已经很严谨，措辞也克制（"not robustly validated" 而非 "no signal"），并且已经写明「the small Oracle Validation cohort must not be repeatedly tuned against」。

问题只在于：**报告给出点估计但没有给出该队列的分辨极限**，而这个负号正在支撑 post-PR-F 的战略判断。`baselines.py` 中也没有任何 `detectable` / `bootstrap` / `confidence_interval`。

### 建议（仅限后续引用时）

1. 引用 `PM − M` / `OM − M` / `OM − PM` 时**同时给出队列规模与可分辨门槛**；
2. PR-G / PR-H 在 UI 与最终报告中呈现模型驱动因素时，**不要把负号表述为「文档特征无用」**，正确表述是「在当前样本量下未能验证」；
3. 未来 CH-6 若要重新评估文档信号价值，**先做功效估算再定队列规模** —— 即使用完整 368 个 development，门槛也有 0.087，而这类信号的实际量级通常在 0.03–0.10。

### 可直接复用的工具

```python
from ipo_risk.modeling.statistical_power import assess_comparison

assess_comparison(-0.0571, positive_count=7, negative_count=12, assumed_auc=0.567).statement()
# "observed gap -0.0571 is 15% of the minimum detectable difference of 0.391
#  for this cohort (7 positive / 12 negative); its sign is not informative at
#  this sample size"
```

`ComparisonPower.resolvable` 可用于让渲染层在差值不可分辨时隐藏正负号 —— 这对 PR-G「明确 uncertainty」的 Gate 要求直接有用。

---

## 7. 🟢 缺依赖时测试是 collection 崩溃而非 skip

**归属：A（experiment reproducibility）。未处理，非阻塞。**

仓库没有 `conftest.py`、没有注册 pytest marker、没有 `importorskip`。`tests/ranking/` 硬 import lightgbm，缺失时**整个 suite 中断**而非跳过。macOS 上还需系统级 `brew install libomp`，`pip install lightgbm` 不够。

E 未擅自修改：「缺依赖时 skip 还是 hard-fail」是治理决策 —— 若改成 skip 而 CI 某天掉了 extra，PR-F 的真实回归会静默变绿。建议 A 决定，并配一个「CI 确实装了预期 extra」的断言。

---

## 已关闭的发现（保留记录）

**1. PR-E 随机分折 → 已修复。** main 现为 `evaluate_development_forward_chaining_baselines`，协议 `development_expanding_year_forward_oof`，`cohort_year_by_case` 按 case_id 键控；`V04_BASELINE_ORACLE_DIAGNOSTIC.md` 明写 *Random or shuffled cross-validation is prohibited*。

**2. 队列口径 → 被取代。** E 曾算出 75 dev / 17 val（扣除 outcome 缺失与身份不符）。Oracle v2 通过身份 rebind 收回了被身份问题挡掉的 case，权威口径为 **77 development / 19 validation**（outcome-usable 96）。以 Oracle v2 冻结 manifest 为准。

**3. 身份字段 → 已修复。** `oracle_document_v2.load_official_identities()` 从 production feature artifact 读官方身份，与标注声明比对后 rebind，并记录 `reconciliation_status = annotation_identity_rebound_to_official`。E 曾提出的两条路径（A 解冻从根修 / D 消费侧规避），实际采用的是后者。

**4. Oracle validation 覆盖为 0 → 已解决。** 2023/2024 盲标落地（pass1 61 → 101）。首次审计埋的 `test_oracle_has_no_validation_coverage` 是一条**故意写成会失败**的断言，docstring 承诺「此断言开始失败之日，即 Oracle 臂变为可评估之时」—— 它如期触发，被推翻的结论已在文档中标记为 overturned 而非悄悄改写。

**6. 文档 Gate 状态失真 → 已解决。** A 已修正，且此后文档体系整体重构。

**8. PR-A 冻结记录 → 政策解决。** `V04_BASELINE_ORACLE_DIAGNOSTIC.md` 明确：PR-A Oracle v1 快照（55 eligible development、0 validation）**保留为 historical**，Oracle v2 为当前正式 ceiling。无需重新物化。

---

## 附：E 已交付的内容

| 交付 | 位置 |
|---|---|
| AUC 比较功效工具 | `src/ipo_risk/modeling/statistical_power.py` |
| 功效复核记录 | `docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md` |
| Oracle 覆盖交叉校验（只读） | `scripts/audit_oracle_gold_coverage.py`、`reports/oracle_gold_audit/` |
| Final Supervisor / Market context 契约（**PR-G 的起点**） | `docs/V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md` |
| Streamlit 七阶段骨架（PR-H 准备） | `app/pipeline_stages.py` |

E 未触碰任何冻结模块：`features.py`、`snapshot.py`、`materialization.py`、`oracle_document.py`、`oracle_document_v2.py`、`canonical_dataset.py`、`pr_c_freeze.py`、`baselines.py`、`lightgbm_modeling.py`、`schemas/market.py`、`market/`。

### 本轮主动退休的内容

E 曾自建 `feature_blocks.py`（被 PR-D 的 `project_model_matrix` 取代）与一套 Oracle 基线评估协议（被 main 的 `baselines.py` 取代，且后者已实现 E 推荐的前向分折）。两者均已删除或还原为 main 版本，仅保留 main 中确实缺失的功效工具。
