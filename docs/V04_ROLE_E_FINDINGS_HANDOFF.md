# v0.4 Role E 发现清单与交接

> Status: **FINDINGS / ADVISORY —— 不构成任何正式 Gate 的启动或通过**
> Owner: **E — Oracle / Product Integration**
> Date: **2026-08-22**
> Base revision: `c638f00`（PR-B FROZEN / PR-C 已合并 / PR-D 已合并 / PR-E 分支在飞）
> 全部结论可由 `scripts/audit_oracle_gold_coverage.py` 与 `tests/unit/` 复现

本文件汇总 E 在 Oracle 旁路审计过程中发现的、**需要其他成员决定或处理**的问题。按紧急度排序。

每条都标注了:**归属**、**是否阻塞**、**E 是否已处理**。

---

## 摘要

| # | 问题 | 归属 | 状态 |
|---|---|---|---|
| 1 | PR-E 的 development CV 是随机分折,不是时间感知 | **D** | 🔴 在飞分支上,建议合并前处理 |
| 2 | Oracle 交集队列实际是 **56**,不是 60 | D | 🔴 活的阻塞,3 个 case 已被 PR-D 硬拒 |
| 3 | Oracle artifact 身份字段取自标注 packet 而非权威 bridge | **A** / D | 🔴 问题 2 的成因,需解冻决策 |
| 4 | Oracle 在 validation 上覆盖为 0 | D | 🟡 E 已给出协议方案 |
| 5 | 统计功效不足,任何方案都可能测不出来 | D | 🟡 E 已实现功效指标 |
| 6 | ROADMAP / README 的 Gate 状态与代码不符 | **A** | 🟡 文档失真 |
| 7 | 缺依赖时测试是 collection 崩溃而非 skip | **A** | 🟢 非阻塞 |

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

## 2. 🔴 Oracle 交集队列实际是 56,不是 60

**归属:D(PR-D / PR-E 的队列口径)**

PR-A 冻结记录的 `oracle_materialized_count = 60` 是正确的,但那 60 个里有 4 个进不了建模:

```text
Oracle 可构建                          60
  − ipo_2020_06688   outcome 不可得    −1   ← PR-C 拒绝:
                                             "unavailable PR-C target cannot enter PR-D modeling data"
  − ipo_2020_08489  ┐
  − ipo_2020_09600  ├ cohort_year 不符  −3   ← PR-D 抛:
  − ipo_2022_02450  ┘                        "canonical artifact identity mismatch: oracle.cohort_year"
  ─────────────────────────────────────
  = 真正能进 Oracle intersection cohort  56
```

任何以 60 为前提的样本量估算、功效计算或队列声明都要改成 **56**。

复现:

```bash
.venv/bin/python scripts/audit_oracle_gold_coverage.py --root . --output-dir reports/oracle_gold_audit
```

---

## 3. 🔴 Oracle artifact 的身份字段取自标注 packet,而非权威 bridge

**归属:A(是否解冻)/ D(消费侧规避)。这是问题 2 中那 3 个 case 的成因。**

`src/ipo_risk/modeling/oracle_document.py:158`:

```python
"cohort_year": int(meta["source_year"]),   # meta = 标注 case packet 的 metadata
```

取的是**文档年份(source_year)**,不是**官方上市年份**。而 PR-D 的 `_identity_mismatches()` 以 Production-X 的身份为准逐字段比对,`join_artifacts()` 遇到不符即硬失败。

| 类别 | 数量 | case | 字段 |
|---|---:|---|---|
| 已物化且身份不符 | 3 | `ipo_2020_08489`、`ipo_2020_09600`、`ipo_2022_02450` | `cohort_year` |
| 尚未标注、一旦标注即不符 | 2 | `ipo_2023_02503` | `cohort_year` + `dataset_split` |
| | | `ipo_2024_02410` | `dataset_split` |

`ipo_2023_02503` 官方上市日是 **2024-01-09**(official split = `validation`),但 packet 写 `development`;`ipo_2024_02410` 的 packet 写 `development_exception` —— **这个值根本不在 `MarketDatasetSplit` 枚举(development / validation / blind)里**。

### 为什么 E 没有直接修

从根修复要让 `oracle_document.py` 改查 official bridge,这会:

1. 改变受影响 artifact 的 `content_hash`,**使 PR-A 已冻结的 Oracle hash 失效**;
2. 给 evaluation-only 的 Oracle 模块引入对 providers 层的新依赖。

两者都需要 A 的解冻决策,超出 E 的准备性工作边界。

### 两条可选路径

- **A 批准解冻** → 从根修 `oracle_document.py`,重新物化 Oracle,更新 PR-A 冻结记录;
- **D 在消费侧规避** → canonical dataset builder 里 Oracle 侧身份一律以 official bridge 为准,不采信 artifact 自带的 `cohort_year` / `dataset_split`。

无论走哪条,**都要在标注 2024 之前定** —— 否则新标注的 2024 case 会带着错误的 `dataset_split` 进库。

---

## 4. 🟡 Oracle 在 validation 上覆盖为 0

**归属:D(PR-E 范围)。E 已给出协议方案。**

```text
official split   Production-X   Oracle-X
development           368            56   （2020–2023）
validation             70             0   （2024）
```

`expert_results/ipo_2023_*/pass1/` 与 `expert_results/ipo_2024_*/pass1/` 是**空目录** —— 五年的 case packet 都已备好(各 20 个),但 2023/2024 的盲标从未进行。

因此 O / OM 臂无法按 PR-E 既定的 fit-on-development / eval-on-validation 协议评估;而 `OM − PM` 必须在交集队列上算,该队列的 validation 同样为 0。

### 已采纳的方案:development-only 时间感知 CV

`OM − PM` 是一个**差值**。差值有效只需要两臂使用**完全相同的协议与完全相同的队列**,不需要那个队列是 2024。

实现:`src/ipo_risk/modeling/oracle_baseline.py`

| 函数 | 协议 | 用于 |
|---|---|---|
| `train_holdout` | `holdout` | M / P / PM |
| `train_time_aware_cv` | `development_only_time_aware_cv` | O / OM,以及与之相减的 PM |
| `assert_comparable` | — | 相减前的前置校验 |

三条约束由类型强制,无法省略:

- `comparability_warning` 是**必带字段**,CV 数字不可能被当作 holdout 数字阅读;
- `minimum_detectable_auc_difference` 随每个结果输出;
- `assert_comparable()` 要求两臂的 `source_dataset_hash` / `cohort` / `dataset_split` / `target_policy_hash` / `target_threshold_hash` 与 `case_ids` **完全一致**,只允许 feature group 不同。

**明确不采纳:「从 development 里抠 10 个当 validation」** —— 那会得到随机 holdout 而非时间 holdout,与用真 2024 的 M / P / PM 不可比,需要修改冻结的 `expected_market_split()`,且功效为零(见下)。

---

## 5. 🟡 统计功效不足:这个诊断在任何方案下都可能测不出来

**归属:D(PR-E 结论表述)**

Hanley-McNeil,假设真实 AUC = 0.70、正样本率 30%,两臂比较的最小可检测差异:

| 评估集 n | 正 / 负 | SE(AUC) | **可区分的最小 AUC 差异** | 对应场景 |
|---:|---:|---:|---:|---|
| 10 | 3 / 7 | 0.198 | **0.550** | 从 dev 抠 10 个 |
| 19 | 6 / 13 | 0.138 | **0.383** | 标注 2024 的 19 个 packet |
| **56** | 17 / 39 | 0.080 | **0.222** | **真实 Oracle intersection 队列** |
| 70 | 21 / 49 | 0.072 | **0.199** | 完整 2024 validation |
| 368 | 110 / 258 | 0.031 | **0.087** | 完整 development |

这类信号的实际量级通常在 **0.03–0.10**。因此:

> 即使 Oracle 覆盖满整个 development(368 个),也刚好处在可检测边缘;在 56 个上做诊断,只有当 pipeline 差距大到 **0.222** 才能被统计上区分。

### 对 PR-E 的两条要求

1. **预先声明** O / OM 结论为 directional,所有点估计配 bootstrap 置信区间;
2. **不得**把「未发现显著差异」解读为「不存在差距」。

E 已把 `minimum_detectable_auc_difference()` 做成随每个结果一并输出的字段,使功效不足无法被当作 null finding 阅读。**D 的 `baselines.py` 目前没有这个指标**,建议补上。

### 一个负面但有用的结论

如果 PR-E 跑完后 OM 与 PM 无法区分,正确的结论不是「Document pipeline 没有信息损失」,而是:

> **Oracle 诊断在当前样本量下功效不足,无法在统计上区分 OM 与 PM;因此 v0.5 是否重开 Retriever / LLM / Agent 优化不能依赖这个诊断,需要另找依据。**

这个结论今天就能得出,不需要任何额外标注。

---

## 6. 🟡 ROADMAP / README 的 Gate 状态与代码不符

**归属:A(文档治理)**

| 文件 | 写的是 | 实际 |
|---|---|---|
| `docs/ROADMAP.md:6` | PR-C — **NEXT / NOT STARTED** | PR-C 代码已合并(#82 `f792879`、#83 `b1dcc45`) |
| `docs/README.md:6` | 同上 | PR-D canonical dataset 也已合并(#84 `413793a`) |

这两份是文档优先级第 1 和第 5 的活文档。`docs/README.md` 自己写着目标是让新成员「几分钟内回答现在做到哪里」,状态失真会直接误导。

注:`V04_5D_OUTCOME_POLICY.md` 与 `V04_CANONICAL_MODELING_DATASET.md` 的表述是准确的(`IMPLEMENTED / AWAITING FREEZE`、`ENGINEERING PREPARATION / BLOCKED BY FORMAL PR-C FREEZE`)。需要同步的是顶层两份索引。

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

## 附:E 已交付的内容

| 交付 | 位置 |
|---|---|
| Oracle 覆盖审计(只读) | `scripts/audit_oracle_gold_coverage.py`、`reports/oracle_gold_audit/` |
| 审计报告 | `docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md` |
| 评估协议(时间感知 CV + 功效) | `src/ipo_risk/modeling/oracle_baseline.py` |
| Final Supervisor / Market context 契约(PR-G 准备,惰性未接线) | `docs/V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md` |
| Streamlit 七阶段骨架(PR-H 准备) | `app/pipeline_stages.py` |

E 未触碰任何冻结模块:`features.py`、`snapshot.py`、`materialization.py`、`oracle_document.py`、`canonical_dataset.py`、`pr_c_freeze.py`、`schemas/market.py`、`market/`。

### E 本轮主动删除的内容

E 上一轮曾自建 `feature_blocks.py` 解决 Production / Oracle 特征名的 19 处碰撞。**PR-D 合并后该模块已被取代并已删除** —— D 的 `project_model_matrix()` 在投影时给特征名加组件前缀(`production_document__…` / `oracle_document__…`),是更好的结构性解法。`oracle_baseline.py` 现直接消费 `V04CanonicalModelMatrix`,自身不再做任何列选择。
