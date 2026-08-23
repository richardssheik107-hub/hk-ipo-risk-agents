# v0.4 Oracle Gold 覆盖与资格审计

> Status: **RE-AUDITED / ADVISORY —— 不构成任何正式 Gate 的启动或通过**
> Owner: **E — Oracle / Product Integration**
> First audit: **2026-08-21**（61 份 pass1）
> **Re-audit: 2026-08-23**（101 份 pass1，2023/2024 盲标已落地）
> 当前正式 Gate: **PR-C**（PR-A / PR-B frozen；PR-D engineering prep merged）
> 可复现入口：`scripts/audit_oracle_gold_coverage.py`
> 机器可读产物：[`../reports/oracle_gold_audit/oracle_gold_coverage_summary.json`](../reports/oracle_gold_audit/oracle_gold_coverage_summary.json)

## 0. 本次 re-audit 改变了什么

首次审计时 Oracle 只有 60 个 case、**validation 覆盖为 0**，据此判定 PR-E 的 O / OM 臂无法按既定协议评估。2023/2024 的盲标落地后（pass1 从 61 增至 101），该结论**已被推翻的部分与仍然成立的部分如下**：

| 首次审计的结论 | re-audit 后 |
|---|---|
| Oracle 只有 60 个 | ❌ 已推翻 → **98**（official 内） |
| validation 覆盖 = 0 | ❌ 已推翻 → **19**（可用 17） |
| `train_holdout` 对 O / OM 不可用 | ❌ 已推翻 → 现在可用 |
| 剩余 38 个 packet 待标注 | ❌ 已清零 |
| 身份缺陷会在标注 2024 时引爆 | ✅ **已引爆**，见 §3 |
| 统计功效不足以支撑 PR-E 结论 | ✅ **仍然成立，且证据更强**，见 §4 |

原先那条「Oracle 无 validation」的可执行断言(`test_oracle_has_no_validation_coverage`)按其 docstring 的承诺**如期失败**，已替换为 `test_oracle_now_has_validation_coverage`。

审计全程只读 reviewed annotation 资产与受控 official bridge metadata，不运行 production pipeline、不读市场数值或 outcome label、不接触 2025 blind cohort（`blind_2025_accessed = false`）。

---

## 1. 漏斗：101 → 101 → 100 → 98

```text
case packets 准备                              101
pass1 盲标存在                                 101      （五年各 20 + real_case_001）
audit overlay 存在                              87
Oracle feature 可构建                          100      （real_case_001 schema 非法）
  └─ 属于 official 438 universe                 98      （另 2 个 2024 packet 不在 universe 内）
official universe 内无 reviewed gold           340
                                              ─────
98 + 340 = 438                                 ✓
```

三个不在 official universe 内的 packet：`ipo_2024_00805`、`ipo_2024_02613`、`real_case_001`。

`real_case_001` 是遗留的 v0.2 fixture，其 payload 在 `validate_expert_annotation_payload` 下报 `SCHEMA_INVALID`。**它不是缺陷，也不应被「修好」以凑数** —— 它本来就不是一个 official IPO。

### 1.1 PR-A 冻结记录已过时

`reports/frozen/v04_pr_a_document_materialization_manifest.json` 仍记录：

```text
oracle_materialized_count            = 60
no_reviewed_gold_count               = 378
production_oracle_intersection_count = 60
source_git_revision                  = 13e0281f...
```

现实为 98 / 340。**这不是任一方的缺陷** —— PR-A 在 `13e0281f` 时点正确冻结了当时存在的内容，标注是之后才补的。

> **需要 A 决定：PR-A 的 Oracle 侧是否需要重新物化并重新冻结？**

该分歧已由 `test_frozen_pr_a_record_no_longer_matches_reality` 固化为断言，避免被遗忘。

### 1.2 诚实性声明

PR-A 的批量运行产物（`reports/v04_pr_a_full_13e0281/`）**不在本机**，因此本审计**无法**将 content hash 与 PR-A 当时产出的逐 case hash 对照。`oracle_gold_coverage.csv` 中提交的 hash 清单是一份**独立重建记录**，供持有 PR-A 机器的成员 diff；它**不是对 PR-A 的再验证**。

本机确定性已验证：连续两次独立全量重建，content hash 逐一相同。

---

## 2. Oracle 覆盖：validation 缺口已关闭

按官方上市年份：

| official split | official year | Oracle 可构建 |
|---|---|---:|
| development | 2020 | 18 |
| development | 2021 | 22 |
| development | 2022 | 19 |
| development | 2023 | 20 |
| **development 合计** | 2020–2023 | **79** |
| **validation** | 2024 | **19** |
| blind | 2025 | 0（且从未读取） |

> **注意**：`case_id` 前缀里的年份是 **source_year（文档年份）**，不是官方上市年份。按前缀看是五年各 20；按**权威上市年份**看是 18/22/19/20/19。本表以官方上市年份为准，因为切分治理以上市年份定义。

### 2.1 真正能进 PR-E 的队列：75 / 17

「可构建」不等于「可建模」。PR-C 与 PR-D 会各自拒绝一部分：

| split | Oracle 可构建 | − outcome 缺失<br>（PR-C 拒） | − 身份不符<br>（PR-D 拒） | **真正可用** |
|---|---:|---:|---:|---:|
| development | 79 | 1 | 3 | **75** |
| validation | 19 | 0 | **2** | **17** |
| **合计** | **98** | **1** | **5** | **92** |

- PR-C 拒绝理由：`unavailable PR-C target cannot enter PR-D modeling data`
- PR-D 拒绝理由：`canonical artifact identity mismatch: oracle.cohort_year`

**身份缺陷吃掉了 19 个 validation 里的 2 个** —— 打在最稀缺的那一臂上。成因见 §3。

---

## 3. 身份缺陷已从预警引爆为事实

`src/ipo_risk/modeling/oracle_document.py:158`：

```python
"cohort_year": int(meta["source_year"]),   # meta = 标注 case packet 的 metadata
```

取的是**文档年份**，不是**官方上市年份**。而 `join_oracle_outcome` 与 PR-D 的 `_identity_mismatches()` **都比较 `cohort_year` 与 `dataset_split`**，任何不符即硬失败。

| case | 不符字段 | 状态 |
|---|---|---|
| `ipo_2020_08489` | `cohort_year` | 首次审计即存在 |
| `ipo_2020_09600` | `cohort_year` | 首次审计即存在 |
| `ipo_2022_02450` | `cohort_year` | 首次审计即存在 |
| **`ipo_2023_02503`** | **`cohort_year` + `dataset_split`** | **本次新增（validation）** |
| **`ipo_2024_02410`** | **`dataset_split`** | **本次新增（validation）** |

首次审计把后两个标记为 *latent mismatch if annotated*，并写明：

> 「一旦团队按建议去标注 2024，这个缺陷就会精确地在那一刻引爆。」

**标注落地，缺陷如期引爆。** 现在 `latent_mismatch_if_annotated` 为空 —— 因为已无未标注的 official packet，所有潜在项都已转为实际项。

细节：`ipo_2023_02503` 官方上市日为 **2024-01-09**（official split = `validation`），但其 packet 写 `development`；`ipo_2024_02410` 的 packet 写 `development_exception` —— **该值不在 `MarketDatasetSplit` 枚举（development / validation / blind）中**。

### 3.1 E 为什么仍不直接修

从根修复需让 `oracle_document.py` 改查 official bridge，这会：

1. 改变受影响 artifact 的 `content_hash`，**使 PR-A 已冻结的 Oracle hash 失效**（而该记录本就已过时，见 §1.1，两件事应一并决定）；
2. 给 evaluation-only 的 Oracle 模块引入对 providers 层的新依赖。

两者都需要 A 的解冻决策。**E 只报告，不修改。**

可选路径：**A 批准解冻**从根修并重新物化（可与 §1.1 的 PR-A 重新冻结合并处理）；或 **D 在消费侧规避**，canonical dataset builder 中 Oracle 侧身份一律以 official bridge 为准。

---

## 4. 评估协议与功效分析

### 4.1 两种协议现在都可用，且都应报告

validation 覆盖恢复后，`train_holdout` 对 O / OM 可用了。但**它的功效比 development-only CV 更差**：

| 协议 | 评估集 n | **最小可检测 AUC 差异** | 诚实性 |
|---|---:|---:|---|
| `holdout`（fit development / eval 2024） | 17 | **0.417** | 真 out-of-sample，协议合规 |
| `development_only_time_aware_cv` | 58 | **0.221** | 乐观（development 曝光），但两臂同偏差 |

（CV 的 58 = 75 个可用 development 减去首年 2020 的 17 个 —— forward-chaining 下首年只做训练不做评估。）

**建议 PR-E 两个都跑、两个都报**，而不是二选一：

- `holdout` 给出协议合规的 out-of-sample 数字；
- CV 给出功效更高、但**明确标注不可与 holdout 并列**的诊断数字；
- 两臂（OM 与 PM）在每种协议下都必须用**同一队列、同一协议**，否则差值不是 pipeline gap。

实现层面由 `OracleCrossValidationResult.comparability_warning`（必带字段）与 `assert_comparable()` 强制。

**明确不采纳：「从 development 里抠一块当 validation」** —— 得到的是随机 holdout 而非时间 holdout，与用真 2024 的 M / P / PM 不可比，且需要修改冻结的 `expected_market_split()`（docstring 明写 "with no exceptions"）。

### 4.2 功效仍然不足 —— 这条结论没有被新数据推翻

Hanley-McNeil，假设真实 AUC = 0.70、正样本率 30%，两臂比较的最小可检测差异：

| 评估集 n | **可区分的最小 AUC 差异** | 对应场景 |
|---:|---:|---|
| 10 | 0.550 | 曾被考虑的「从 dev 抠 10 个」 |
| **17** | **0.417** | **真实 validation 臂（holdout）** |
| **58** | **0.221** | **真实 CV pooled 臂** |
| 92 | 0.174 | 假设身份缺陷修复后的全部可用 Oracle |
| 368 | 0.087 | 完整 development（Production 侧） |

这类信号的实际量级通常在 **0.03 – 0.10**。因此：

> **两种协议都无法在统计上区分 OM 与 PM。** 补标注解决了「协议不可执行」，但**没有**解决「功效不足」—— validation 臂只有 17 个，比补标注前用来做 CV 的 development 队列还小。

`minimum_detectable_auc_difference()` 随每个结果一并输出（`metrics.minimum_detectable_auc_difference`），使功效不足无法被当作 null finding 阅读。

### 4.3 PR-E 应当预先声明的三条

1. O / OM 结论为 **directional**，所有点估计配 bootstrap 置信区间；
2. **不得**把「未发现显著差异」解读为「不存在差距」；
3. 若 OM 与 PM 无法区分，正确结论是：

> **Oracle 诊断在当前样本量下功效不足，无法在统计上区分 OM 与 PM；因此 v0.5 是否重开 Retriever / LLM / Agent 优化不能依赖这个诊断，需要另找依据。**

### 4.4 实现落点

`src/ipo_risk/modeling/oracle_baseline.py` 直接消费 PR-D 的 canonical model matrix，**不自行做列选择** —— `project_model_matrix()` 已按冻结的组件顺序投影出每个 M / P / O / PM / OM 矩阵并加了组件前缀。

| 函数 | 协议 |
|---|---|
| `train_holdout` | `holdout` |
| `train_time_aware_cv` | `development_only_time_aware_cv` |
| `assert_comparable` | 相减前的前置校验 |

`cohort_years` 按 **case_id 键控**而非位置传入，一行不可能静默拿到别的 case 的年份。

---

## 5. 交给其他角色

| 收件人 | 事项 |
|---|---|
| **A** | ① §1.1 PR-A 的 Oracle 侧是否重新物化并重新冻结；② §3.1 是否解冻 `oracle_document.py` 从根修身份字段（建议与 ① 合并决定）。 |
| **D** | ① §2.1 队列口径改为 **75 / 17**，不是 98；② §4.1 两种协议都跑、都报，且两臂同队列同协议；③ §4.3 预先声明功效限制；④ canonical dataset 每条记录需带 `cohort_year`（CV 按它分折）；⑤ 5 个身份不符 case 需显式处理而非静默过滤。 |
| **B** | 标注 backlog 已清零，无待办。 |

---

## 6. 复现方式

```bash
.venv/bin/python scripts/audit_oracle_gold_coverage.py --root . --output-dir reports/oracle_gold_audit
```

```bash
.venv/bin/python -m pytest tests/unit/test_oracle_gold_coverage_audit.py tests/unit/test_oracle_baseline.py -q
```

确定性重建（产物走 gitignore 路径，不入库）：

```bash
.venv/bin/python scripts/build_oracle_document_features.py --all-eligible --root . --output-dir reports/oracle_local_repro/run1
```

---

## 7. 边界声明

本审计属于 `V04_FIVE_PERSON_EXECUTION_PLAN.md` §11 分配给 E 的 **`Oracle re-audit preparation`**：

- 不启动、不声称通过任何正式 Gate；当前正式 Gate 为 **PR-C**；
- 不读取市场数据、EOD store、outcome label 或 2025 blind cohort；
- 不写入 `reports/frozen/`，不重跑 `scripts/run_v04_pr_a.py`；
- 不修改任何已冻结的 Document Intelligence、Oracle、PR-C 或 PR-D 逻辑；
- 不产出任何真实 O / OM 指标 —— 那属于 PR-E。
