# v0.4 Role E 发现清单与交接

> Status: **FINDINGS / ADVISORY —— 不构成任何正式 Gate 的启动或通过**
> Owner: **E — Oracle / Product Integration**
> First issued: **2026-08-22** · **Revised: 2026-08-23**（2023/2024 盲标落地后 re-audit）
> Base revision: `a1e32a9`（PR-A / PR-B frozen；PR-C active；PR-D engineering prep merged；PR-E 分支在飞）
> 全部结论可由 `scripts/audit_oracle_gold_coverage.py` 与 `tests/unit/` 复现

本文件汇总 E 在 Oracle 旁路审计过程中发现的、**需要其他成员决定或处理**的问题。按紧急度排序。

每条都标注了:**归属**、**是否阻塞**、**E 是否已处理**。

---

## 摘要

> **2026-08-23 修订说明**：2023/2024 盲标已落地（pass1 61 → 101）。原问题 4「Oracle validation 覆盖为 0」**已解决**；原问题 2 的数字**已作废并重算**；原问题 3 **已从预警引爆为事实**；原问题 5 **不受影响，且证据更强**；原问题 6 **已由 A 修复**。新增问题 8。

| # | 问题 | 归属 | 状态 |
|---|---|---|---|
| 1 | PR-E 的 development CV 是随机分折,不是时间感知 | **D** | 🔴 在飞分支上,建议合并前处理 |
| 2 | Oracle 真正可用队列是 **75 dev / 17 val**,不是 98 | D | 🔴 5 个 case 被 PR-D 硬拒 |
| 3 | Oracle artifact 身份字段取自标注 packet 而非权威 bridge | **A** / D | 🔴 **已引爆**,吃掉 2/19 个 validation |
| 8 | PR-A 冻结记录（Oracle 60）已与现实（98）不符 | **A** | 🔴 需决定是否重新物化 |
| 5 | 统计功效不足,两种协议都测不出来 | D | 🟡 E 已实现功效指标 |
| 7 | 缺依赖时测试是 collection 崩溃而非 skip | **A** | 🟢 非阻塞 |
| ~~4~~ | ~~Oracle 在 validation 上覆盖为 0~~ | — | ✅ **已解决**（补标注） |
| ~~6~~ | ~~ROADMAP / README 的 Gate 状态与代码不符~~ | — | ✅ **已解决**（A 已修） |

---

## 1. 🔴 PR-E 的 development CV 是随机分折,不是时间感知

**归属:D。位置:`origin/feature/v04-pr-e-baseline-diagnostic` 的 `src/ipo_risk/modeling/baselines.py`**

`evaluate_development_cv_baselines()` 使用:

```python
splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=PR_E_RANDOM_SEED)
```

整个文件中 **`cohort_year` 一次都没有出现**。因此折是在 2020/2021/2022 之间随机混合的 —— **一折可以用 2022 的样本训练,去预测 2020 的样本**。

### 为什么这重要

项目的切分治理是**时序**的,`expected_market_split()` 的 docstring 明写 *"with no exceptions"*。而 PR-E 的三个核心量里有两个要减去 M:

```text
Document Signal Ceiling ≈ OM − M
Production Increment    ≈ PM − M
Pipeline Gap            ≈ OM − PM
```

随机分折的乐观偏差**不是对称的**:市场特征(HSI 水平、IPO 市场温度)有强时间自相关,随机分折让模型看到同期市场环境,**对含 M 的臂(M / PM / OM)的抬升远大于纯文档臂(P / O)**。

后果是 `OM − M` 和 `PM − M` 会被**系统性低估**。也就是说:

> PR-E 可能得出「文档没有增量价值」的结论,而这个结论部分来自分折方式,不是来自数据。
> 这会直接影响 v0.5 是否重开 Retriever / LLM / Agent 优化的决策。

### 建议

改为 forward-chaining 分折:train 2020 → test 2021;train 2020–21 → test 2022,汇总 out-of-fold 预测。

E 已实现一份可直接参考的版本:`src/ipo_risk/modeling/oracle_baseline.py::train_time_aware_cv`,其中 `test_forward_chaining_folds_never_see_their_own_future` 把「任一折的训练年份严格早于测试年份」钉成了机器可验证的断言。

**E 不修改 PR-E 分支** —— PR-E 归 D。此处只报告。

---

## 2. 🔴 Oracle 真正可用队列是 75 dev / 17 val

**归属:D(PR-D / PR-E 的队列口径)**

补标注后 Oracle 在 official universe 内可构建 **98** 个,但「可构建」不等于「可建模」—— PR-C 与 PR-D 会各自拒绝一部分:

| split | Oracle 可构建 | − outcome 缺失<br>(PR-C 拒) | − 身份不符<br>(PR-D 拒) | **真正可用** |
|---|---:|---:|---:|---:|
| development | 79 | 1 | 3 | **75** |
| validation | 19 | 0 | **2** | **17** |
| **合计** | **98** | **1** | **5** | **92** |

- PR-C 拒绝理由:`unavailable PR-C target cannot enter PR-D modeling data`
- PR-D 拒绝理由:`canonical artifact identity mismatch: oracle.cohort_year`

**任何以 98 为前提的样本量或功效估算都要改成 75 / 17。**

复现:

```bash
.venv/bin/python scripts/audit_oracle_gold_coverage.py --root . --output-dir reports/oracle_gold_audit
```

---

## 3. 🔴 身份缺陷已引爆,吃掉 2 个 validation

**归属:A(是否解冻)/ D(消费侧规避)。这是问题 2 中那 5 个 case 的成因。**

`src/ipo_risk/modeling/oracle_document.py:158`:

```python
"cohort_year": int(meta["source_year"]),   # meta = 标注 case packet 的 metadata
```

取的是**文档年份**,不是**官方上市年份**。而 `join_oracle_outcome` 与 PR-D 的 `_identity_mismatches()` **都比较 `cohort_year` 与 `dataset_split`**,不符即硬失败。

| case | 不符字段 | 状态 |
|---|---|---|
| `ipo_2020_08489` | `cohort_year` | 首次审计即存在 |
| `ipo_2020_09600` | `cohort_year` | 首次审计即存在 |
| `ipo_2022_02450` | `cohort_year` | 首次审计即存在 |
| **`ipo_2023_02503`** | **`cohort_year` + `dataset_split`** | **本次新增(validation)** |
| **`ipo_2024_02410`** | **`dataset_split`** | **本次新增(validation)** |

首次审计(2026-08-22)把后两个标记为 *latent mismatch if annotated*,并写明:

> 「一旦团队按建议去标注 2024,这个缺陷就会精确地在那一刻引爆。」

**标注落地,缺陷如期引爆,而且打在最稀缺的 validation 臂上 —— 19 个里损失 2 个。**

细节:`ipo_2023_02503` 官方上市日为 **2024-01-09**(official split = `validation`),但 packet 写 `development`;`ipo_2024_02410` 的 packet 写 `development_exception` —— 该值**不在 `MarketDatasetSplit` 枚举(development / validation / blind)中**。

### E 为什么仍不直接修

从根修复要让 `oracle_document.py` 改查 official bridge,这会改变 artifact 的 `content_hash`,**使 PR-A 已冻结的 Oracle hash 失效**(而该记录本就已过时,见问题 8 —— 两件事应一并决定),并给 evaluation-only 模块引入对 providers 层的新依赖。都需要 A 的解冻决策。

**可选路径**:A 批准解冻从根修并重新物化(建议与问题 8 合并处理);或 D 在消费侧规避,canonical dataset builder 中 Oracle 侧身份一律以 official bridge 为准。

---

## 4. ✅ 已解决:Oracle 在 validation 上覆盖为 0

首次审计时 `expert_results/ipo_2023_*/pass1/` 与 `ipo_2024_*/pass1/` 是空目录,Oracle 只覆盖 development,导致 O / OM 臂无法按 PR-E 的 fit-dev / eval-val 协议评估。

**2023/2024 盲标已落地(pass1 61 → 101),该缺口关闭。** `train_holdout` 现在对 O / OM 可用。

原先那条故意写成会失败的断言 `test_oracle_has_no_validation_coverage` 如期触发,已替换为 `test_oracle_now_has_validation_coverage`。**trip-wire 机制按设计工作。**

但请注意:**这解决的是「协议不可执行」,没有解决「功效不足」** —— 见问题 5。

---

## 5. 🟡 统计功效不足:两种协议都测不出来

**归属:D(PR-E 结论表述)**

validation 恢复后有两种协议可用,但 **holdout 的功效反而更差**,因为 validation 只有 17 个而 development 有 75 个:

| 协议 | 评估集 n | **最小可检测 AUC 差异** | 诚实性 |
|---|---:|---:|---|
| `holdout`(fit development / eval 2024) | 17 | **0.417** | 真 out-of-sample,协议合规 |
| `development_only_time_aware_cv` | 58 | **0.221** | 乐观(development 曝光),但两臂同偏差 |

(CV 的 58 = 75 个可用 development 减去首年 2020 的 17 个 —— forward-chaining 下首年只训练不评估。)

完整功效表(Hanley-McNeil,假设 AUC = 0.70、正样本率 30%):

| 评估集 n | 最小可检测差异 | 对应场景 |
|---:|---:|---|
| **17** | **0.417** | 真实 validation 臂 |
| **58** | **0.221** | 真实 CV pooled 臂 |
| 92 | 0.174 | 假设身份缺陷修复后的全部可用 Oracle |
| 368 | 0.087 | 完整 development(Production 侧) |

这类信号的实际量级通常在 **0.03 – 0.10**。

> **补标注没有把这个诊断变得可用。** validation 臂只有 17 个,比补标注前用来做 CV 的队列还小。

### 对 PR-E 的三条要求

1. **两种协议都跑、都报**,而不是二选一;两臂必须同队列同协议,否则差值不是 pipeline gap;
2. **预先声明** O / OM 结论为 directional,所有点估计配 bootstrap 置信区间;
3. **不得**把「未发现显著差异」解读为「不存在差距」。

E 已把 `minimum_detectable_auc_difference()` 做成随每个结果一并输出的字段。**D 的 `baselines.py` 目前没有这个指标,建议补上。**

### 一个负面但有用的结论

如果 PR-E 跑完后 OM 与 PM 无法区分,正确的结论不是「Document pipeline 没有信息损失」,而是:

> **Oracle 诊断在当前样本量下功效不足,无法在统计上区分 OM 与 PM;因此 v0.5 是否重开 Retriever / LLM / Agent 优化不能依赖这个诊断,需要另找依据。**

---

## 6. ✅ 已解决:ROADMAP / README 的 Gate 状态与代码不符

首次审计时 `docs/ROADMAP.md` 与 `docs/README.md` 都写「PR-C — NEXT / NOT STARTED」,而 PR-C / PR-D 代码已合并。

**A 已修复。** 两份文档现在准确表述为:

```text
PR-C  FORMAL EXECUTION ACTIVE / GOVERNED MATERIALIZATION PENDING / NOT FROZEN
PR-D  ENGINEERING PREPARATION MERGED / FORMAL MATERIALIZATION BLOCKED BY PR-C
```

---

## 7. 🟢 缺依赖时测试是 collection 崩溃而非 skip

**归属:A(experiment reproducibility)**

仓库没有 `conftest.py`、没有注册 pytest marker、没有 `importorskip`。`tests/ranking/` 的两个文件硬 import lightgbm,缺失时是**整个 suite 中断**,不是跳过三个文件:

```text
!!! Interrupted: 2 errors during collection !!!
```

macOS 上还需要系统级 `brew install libomp`,`pip install lightgbm` 不够。

E **没有擅自修改**,因为「缺依赖时 skip 还是 hard-fail」是治理决策:若改成 skip 而 CI 某天掉了 extra,PR-F 的真实回归会静默变绿。建议 A 决定,并配一个「CI 确实装了预期 extra」的断言。

---

## 8. 🔴 PR-A 冻结记录已与现实不符

**归属:A(治理决策)**

`reports/frozen/v04_pr_a_document_materialization_manifest.json` 仍记录:

```text
oracle_materialized_count            = 60
no_reviewed_gold_count               = 378
production_oracle_intersection_count = 60
source_git_revision                  = 13e0281f...
```

现实为 **98 / 340**。

**这不是任一方的缺陷** —— PR-A 在 `13e0281f` 时点正确冻结了当时存在的内容,2023/2024 的标注是之后才补的。但冻结记录现在会误导任何以它为准的下游。

> **需要 A 决定:PR-A 的 Oracle 侧是否需要重新物化并重新冻结?**

建议与问题 3 的解冻决策**合并处理** —— 若要重新物化,正好一并把身份字段改从 official bridge 取,一次解决两个问题。

该分歧已由 `test_frozen_pr_a_record_no_longer_matches_reality` 固化为断言,避免被遗忘;若 PR-A 重新冻结,该测试需同步更新。

---

## 附:E 已交付的内容

| 交付 | 位置 |
|---|---|
| Oracle 覆盖审计(只读) | `scripts/audit_oracle_gold_coverage.py`、`reports/oracle_gold_audit/` |
| 审计报告 | `docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md` |
| 评估协议(时间感知 CV + 功效) | `src/ipo_risk/modeling/oracle_baseline.py` |
| Final Supervisor / Market context 契约(PR-G 准备,惰性未接线) | `docs/V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md` |
| Streamlit 七阶段骨架(PR-H 准备) | `app/pipeline_stages.py` |

本轮 re-audit 对应五人计划 §11 分配给 E 的 **`Oracle re-audit preparation + Final Supervisor / UI skeleton reconciliation`**。

E 未触碰任何冻结模块:`features.py`、`snapshot.py`、`materialization.py`、`oracle_document.py`、`canonical_dataset.py`、`pr_c_freeze.py`、`schemas/market.py`、`market/`。

### E 本轮主动删除的内容

E 上一轮曾自建 `feature_blocks.py` 解决 Production / Oracle 特征名的 19 处碰撞。**PR-D 合并后该模块已被取代并已删除** —— D 的 `project_model_matrix()` 在投影时给特征名加组件前缀(`production_document__…` / `oracle_document__…`),是更好的结构性解法。`oracle_baseline.py` 现直接消费 `V04CanonicalModelMatrix`,自身不再做任何列选择。
