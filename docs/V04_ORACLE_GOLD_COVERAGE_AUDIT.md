# v0.4 Oracle Gold 覆盖与资格审计

> Status: **PREPARATION / ADVISORY — 不构成任何正式 Gate 的启动或通过**
> Owner: **E — Oracle / Product Integration**
> Audit date: **2026-08-21**
> 当前正式 Gate 仍为 **PR-B Market-X Core（NOT STARTED / NEXT）**
> 可复现入口：`scripts/audit_oracle_gold_coverage.py`
> 机器可读产物：[`../reports/oracle_gold_audit/oracle_gold_coverage_summary.json`](../reports/oracle_gold_audit/oracle_gold_coverage_summary.json)、[`../reports/oracle_gold_audit/oracle_gold_coverage.csv`](../reports/oracle_gold_audit/oracle_gold_coverage.csv)

本文件回答一个 PR-A 已给出数字、但从未给出解释的问题：

> **Oracle 为什么只有 60 个 case？这 60 个落在哪个 split？对 PR-E 意味着什么？**

审计全程只读 reviewed annotation 资产与受控 official bridge metadata，不运行 production pipeline、不读市场数值或 outcome label、不接触 2025 blind cohort（`blind_2025_accessed = false`，`blind_2025_rows_excluded = 0`）。

---

## 1. 漏斗：101 → 61 → 60

```text
case packets 准备                              101
  └─ 属于 official 438 universe                 98      (3 个不属于)
pass1 专家标注实际存在                          61
  └─ 属于 official 438 universe                 60      (real_case_001 不属于)
Oracle feature 可构建                           60
  └─ official universe 内                       60
official universe 内无 reviewed gold           378
                                              ─────
60 + 378 = 438                                 ✓
```

三个不在 official universe 内的 packet：`ipo_2024_00805`、`ipo_2024_02613`、`real_case_001`。

`real_case_001` 是遗留的 v0.2 fixture，其 payload 在 `validate_expert_annotation_payload` 下报 `SCHEMA_INVALID`，因此 61 个 pass1 中只有 60 个可构建。**它不是 pipeline 缺陷，也不应被"修好"以凑数**——它本来就不是一个 official IPO。

本审计独立复现的 60 / 378 与 PR-A 冻结 manifest 的 `oracle_materialized_count` / `no_reviewed_gold_count` **完全一致**。

### 1.1 诚实性声明

PR-A 的批量运行产物（`reports/v04_pr_a_full_13e0281/oracle_status.json`）**不在本机**。因此本审计**无法**把这 60 个 `content_hash` 与 PR-A 当时产出的逐 case hash 做对照。

`oracle_gold_coverage.csv` 中提交的 hash 清单是一份**独立重建记录**，供持有 PR-A 机器的成员来 diff；它**不是对 PR-A 的再验证**，也不改变 PR-A 的任何冻结结论。

本机确定性已验证：`build_oracle_document_features` 连续两次独立全量运行，60 个 `content_hash` 逐一相同，失败集恒为 `{real_case_001}`。

---

## 2. 核心发现：Oracle 没有 validation split

按官方上市年份计算的 Oracle 覆盖：

| official split | official year | Oracle 可构建数 |
|---|---|---:|
| development | 2020 | 18 |
| development | 2021 | 22 |
| development | 2022 | 19 |
| development | 2023 | 1 |
| **development 合计** | 2020–2023 | **60** |
| **validation** | 2024 | **0** |
| blind | 2025 | 0（且从未读取） |

> **注意**：`case_id` 前缀里的年份是 **source_year（文档年份）**，不是官方上市年份。按 case_id 前缀看是 2020/2021/2022 各 20 个；按**权威上市年份**看则是 18/22/19/1。本表以官方上市年份为准，因为切分治理以上市年份定义。

`expert_results/ipo_2023_*/pass1/` 与 `expert_results/ipo_2024_*/pass1/` 是**空目录**——packet 已备好，标注从未进行。

> **可用队列是 56，不是 60。**（2026-08-21 复核，PR-D builder 合并后实测）
>
> | 扣减项 | 数量 | 被谁拒绝 |
> |---|---:|---|
> | Oracle 可构建 | 60 | — |
> | `ipo_2020_06688` outcome 不可得 | −1 | PR-C：`unavailable PR-C target cannot enter PR-D modeling data` |
> | `ipo_2020_08489` / `ipo_2020_09600` / `ipo_2022_02450` 身份不符 | −3 | PR-D：`canonical artifact identity mismatch: oracle.cohort_year` |
> | **真正能进 Oracle intersection cohort** | **56** | |
>
> 后续功效计算均以 **56** 为准。第二项扣减的成因见 §3，它现在是**活的阻塞**，不再是预警。

### 2.1 对 PR-E 的后果

PR-E 的正式协议是 **fit on development / evaluate on untouched validation**（`train_oracle_logistic_regression` 的签名本身就强制要求 `validation_x` / `validation_y`）。

- 对 **M / P / PM**：full production cohort 的 2024 有 70 个 official case，协议成立。
- 对 **O / OM**：validation 样本数为 **0**，协议不成立。
- 更关键的是，PR-E 的核心量 **`Pipeline Gap ≈ OM − PM`** 必须在 **Production ∩ Oracle 的 intersection cohort（60 个，可用 59 个）** 上计算，而该 cohort 的 validation 样本数同样为 **0**。

> **因此：不只是 Oracle 单臂，而是整条"Production vs Oracle 公平诊断链"在当前数据下都无法按 PR-E 既定协议执行。**

这一后果此前没有出现在任何文档中。PR-A 报出的 `60` 是正确的；**被遗漏的是这个 60 的构成**。

**处置**：不通过补 validation 解决，改为让两臂在同一队列上跑 development-only 时间感知 CV，使 `OM − PM` 这个**差值**有效。见 §4.1。

本发现已编码为可执行断言：`tests/unit/test_oracle_gold_coverage_audit.py::test_oracle_has_no_validation_coverage`。该断言开始失败之日，即 Oracle 臂变为可评估之时，本文件必须在同一次改动中修订。

---

## 3. 第二发现（已从预警升级为活的阻塞）：Oracle artifact 的身份字段来自标注 packet，而非权威 bridge

`build_oracle_document_features` 从 case packet metadata 取 `cohort_year`（实为 `source_year`）与 `dataset_split`，**不查 official bridge**。而 `join_oracle_outcome` 在建模 join 时**恰好比较这两个字段**：

```python
for key in ("case_id", "stock_code", "cohort_year", "dataset_split"):
    ...  raise ValueError(f"oracle/outcome identity mismatch: {key}")
```

审计结果：

| 类别 | 数量 | case | 字段 |
|---|---:|---|---|
| 已物化且身份不一致 | **3** | `ipo_2020_08489`、`ipo_2020_09600`、`ipo_2022_02450` | `cohort_year` |
| 尚未标注、一旦标注即不一致 | 2 | `ipo_2023_02503` | `cohort_year` + `dataset_split` |
| | | `ipo_2024_02410` | `dataset_split` |

**今天的影响：** 3 / 60 个已物化 Oracle artifact 的 `cohort_year` 与官方上市年份不符（均在 development 内部漂移，故 split 仍正确）。这 3 个 case 会在 PR-D / PR-E 的 `join_oracle_outcome` 处**硬失败**，而不是静默错配——fail-closed 行为本身是正确的。

**明天的风险：** `ipo_2023_02503` 官方上市日为 2024-01-09（official split = `validation`），但其 packet 标注 `development`；`ipo_2024_02410` 的 packet 标注 `development_exception`——这个值**根本不在 `MarketDatasetSplit` 枚举（development / validation / blind）中**。也就是说：**一旦团队按第 4 节的建议去标注 2024，这个缺陷就会精确地在那一刻引爆。**

标注 packet 的 split 词汇表（98 个 official packet）：`development` 80、`validation` 17、`development_exception` 1 —— 与官方 79 / 19 的切分**不一致**。

### 3.1 E 为什么不在本批修它

修复需要让 `oracle_document.py` 改从 official bridge 取身份字段，这会：

1. 改变受影响 artifact 的 `content_hash`，从而**使 PR-A 已冻结的 Oracle hash 失效**；
2. 给 evaluation-only 的 Oracle 模块引入对 providers 层的新依赖。

两者都超出 preparation 的边界。**因此 E 只报告，不修改**，并把它登记为 PR-D 的前置条件（见第 5 节）。

---

## 4. 评估协议决策与功效分析

official universe 内已备 packet 但无 pass1 的 case 共 **38** 个：

| official split | 数量 | 说明 |
|---|---:|---|
| development | 19 | 主要为 2023 |
| **validation** | **19** | 2024；**这是唯一能给 Oracle 补出 validation 臂的池子** |

完整 case id 清单见 `oracle_gold_coverage_summary.json` 的 `annotation_opportunity.case_ids`。

> 注意是 **19** 而非 20：`ipo_2024_00805` 与 `ipo_2024_02613` 两个 2024 packet 不在 official 438 universe 内。

### 4.1 决策：方案 B（development-only 时间感知 CV）—— 已采纳

> **2026-08-21 更新：本节推荐顺序已翻转。** 初版把「标注 2024」列为首选，那个排序基于一个未经检验的假设——补上 validation 就能让诊断成立。功效分析证明该假设不成立，见 4.2。

**方案 B — O / OM 与 PM 同队列、同协议，跑 development-only 时间感知 CV（采纳）**

PR-E 的核心量是一个**差值**：

```text
Pipeline Gap ≈ OM − PM
```

差值有效只需要两臂使用**完全相同的协议与完全相同的队列**，并不需要那个队列是 2024。因此：

- O / OM / PM 全部在同一批 **56 个交集 case** 上跑 forward-chaining CV（train 2020 → test 2021；train 2020–21 → test 2022），汇总 out-of-fold 预测后统一评估；
- 保留时间顺序，不引入随机切分的乐观偏差；
- 不动冻结的 `expected_market_split()`，不占用 2024 validation；
- 56 个全部参与训练，不像「从 dev 抠一块当 val」那样白白损失训练样本。

**必须同时声明的两条限制：**

1. 这些数字**不得与 M / P / PM 在 2024 validation 上的数字并列**。实现层面由 `OracleCrossValidationResult.comparability_warning` 强制携带，无法省略。
2. 残留偏差不对称：Production 特征在开发期接触 development 数据多于 Oracle 特征，因此相减不能完全抵消乐观程度。这一条必须写进 PR-E 结论。

**为什么不是「从 development 里抠 10 个当 validation」**

该做法在讨论中被提出，不予采纳：

- 得到的是**随机 holdout**，不是时间 holdout。训练与评估同属 2020–2022 同一市场环境，分数虚高，而时间切分存在的意义就是防这个；
- 与 M / P / PM 不可比——那三臂用真正的 2024，拿「2020–2022 随机 holdout 的 OM」减「2024 的 PM」，差异里混入的是市场周期而非 pipeline 差异；
- 需要修改 `src/ipo_risk/schemas/market.py:90` 的 `expected_market_split()`（docstring 明写 "with no exceptions"），并波及 `market/validation.py`、`market/governance.py`、`schemas/modeling.py` 及 5 个测试，属于跨 Gate 的治理变更；
- 且功效为零，见下表。

**方案 A — 标注 19 个 official 2024 packet（不推荐作为诊断手段）**

packet 已备好，边际成本只剩标注。但由 4.2 可知，19 个 validation 需要 0.383 的 AUC 差异才显著，**标了也大概率不显著**。若出于其他目的（扩充 Oracle 队列、覆盖更晚市场环境）仍值得做，但不应以「让 PR-E 诊断成立」为理由。

若采纳，必须**先**修复第 3 节的身份缺陷，否则新标注的 2024 case 会带着错误的 `dataset_split` 进入数据集。

**方案 C — 移出正式 Gate（下策）**：PR-E 只回答 M / P / PM，v0.4 失去 Document 信号上限这一决策依据。

### 4.2 功效分析：这个诊断在任何方案下都可能测不出来

Hanley-McNeil，假设真实 AUC = 0.70、正样本率 30%，两臂比较的最小可检测差异：

| 评估集 n | 正 / 负 | SE(AUC) | 95% CI 半宽 | **可区分的最小 AUC 差异** | 对应方案 |
|---:|---:|---:|---:|---:|---|
| 10 | 3 / 7 | 0.198 | 0.389 | **0.550** | 从 dev 抠 10 个 |
| 19 | 6 / 13 | 0.138 | 0.271 | **0.383** | 标注 2024（方案 A） |
| 56 | 17 / 39 | 0.080 | 0.157 | **0.222** | **真实 Oracle intersection 队列（方案 B）** |
| 70 | 21 / 49 | 0.072 | 0.141 | **0.199** | 完整 2024 validation |
| 368 | 110 / 258 | 0.031 | 0.061 | **0.087** | 完整 development |

这类信号的实际量级通常在 **0.03–0.10**。也就是说：

> **即使 Oracle 覆盖满整个 development（368 个），也刚好处在可检测边缘；在 59 个上做诊断，只有当 pipeline 差距大到 0.216 才能被统计上区分。**

因此 PR-E 应当**预先声明**：O / OM 结论为 directional，所有点估计必须配 bootstrap 置信区间，且**不得**把「未发现显著差异」解读为「不存在差距」。

实现层面已固化这一点：`minimum_detectable_auc_difference()` 随每个结果一并输出（`metrics.minimum_detectable_auc_difference`），使功效不足无法被当作 null finding 阅读。

### 4.4 实现落点

方案 B 由 `src/ipo_risk/modeling/oracle_baseline.py` 提供，直接消费 PR-D 的 canonical model matrix，**不自行做列选择**——`project_model_matrix()` 已经按冻结的组件顺序投影出每个 M / P / O / PM / OM 矩阵，并给特征名加了组件前缀。

| 函数 | 协议 | 用于 |
|---|---|---|
| `train_holdout` | `holdout` | M / P / PM，fit development / eval untouched validation |
| `train_time_aware_cv` | `development_only_time_aware_cv` | O / OM，以及与之相减的 PM |
| `assert_comparable` | — | 相减前的前置校验 |

三条约束由类型强制，无法被省略：

- `OracleCrossValidationResult.comparability_warning` 是**必带字段**，CV 数字不可能被当作 holdout 数字阅读；
- `minimum_detectable_auc_difference()` 随每个结果输出；
- `assert_comparable()` 要求两臂的 `source_dataset_hash` / `cohort` / `dataset_split` / `target_policy_hash` / `target_threshold_hash` 与 `case_ids` **完全一致**，只允许 feature group 不同。否则相减得到的不是 pipeline gap。

`cohort_years` 按 **case_id 键控**而非位置传入，一行不可能静默拿到别的 case 的年份。

### 4.3 一个负面但有用的结论

如果 PR-E 跑完后 OM 与 PM 无法区分，正确的结论不是「Document pipeline 没有信息损失」，而是：

> **Oracle 诊断在当前样本量下功效不足，无法在统计上区分 OM 与 PM；因此 v0.5 是否重开 Retriever / LLM / Agent 优化不能依赖这个诊断，需要另找依据。**

这个结论本身对项目有价值，且今天就能得出——它不需要任何额外标注。

## 5. 交给其他角色的前置条件

| 收件人 | 事项 |
|---|---|
| **D（PR-D / PR-E owner）** | ① 确认 §4.1 方案 B，并在 PR-E 预先声明 O / OM 结论为 directional；② canonical dataset 的每条记录需带 `cohort_year`，CV 协议按它分折；③ Oracle 侧身份必须以 official bridge 为准，不能采信 Oracle artifact 自带的 `cohort_year` / `dataset_split`；④ 已知 3 个 case 会在 `join_oracle_outcome` 硬失败，需显式处理而非过滤掉。 |
| **A（Tech Lead）** | ① 第 3 节的身份缺陷若要真正修复在 `oracle_document.py`，会使 PR-A 冻结的 Oracle content hash 失效，属于需要解冻决策的改动；② §4.1 已排除修改 `expected_market_split()` 的做法，该函数保持冻结。 |
| **B（Document / Agent）** | 2024 标注**不作为 PR-E 前置**（见 §4.1 方案 A）。若出于扩充队列等其他目的推进，执行归属需另行明确。 |

---

## 6. 复现方式

```bash
.venv/bin/python scripts/audit_oracle_gold_coverage.py --root . --output-dir reports/oracle_gold_audit
```

```bash
.venv/bin/python -m pytest tests/unit/test_oracle_gold_coverage_audit.py -q
```

Option B 评估协议（合成数据 smoke；真实 O / OM 指标属于 PR-E，本阶段不产出）：

```bash
.venv/bin/python -m pytest tests/unit/test_oracle_baseline.py -q
```

确定性重建（产物走 gitignore 路径，不入库）：

```bash
.venv/bin/python scripts/build_oracle_document_features.py --all-eligible --root . --output-dir reports/oracle_local_repro/run1
```

---

## 7. 边界声明

本审计属于 `V04_FIVE_PERSON_EXECUTION_PLAN.md` §11 允许的**准备性工作**：

- 不启动、不声称通过任何正式 Gate；当前正式 Gate 仍为 **PR-B**；
- 不读取市场数据、EOD store、outcome label 或 2025 blind cohort；
- 不写入 `reports/frozen/`，不重跑 `scripts/run_v04_pr_a.py`；
- 不修改任何已冻结的 Document Intelligence 或 Oracle 逻辑；
- 本文件全部结论即使被推翻，PR-A 的冻结 manifest 与 PR-B 的范围均不受影响。
