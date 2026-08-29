# v0.4.6 Role-C — Dynamic Market-X 泛化合同

> 状态日期：2026-08-29
> 关联岗位文档：`team/03_DYNAMIC_MARKET_X_OWNER.md`
> 目标：任何合法的新 PDF / 新 IPO 都进入统一 Market runtime，**有数据时真实计算，无数据时诚实降级并给出原因**。

## 1. 现在的运行语义

```text
case identity (case_id | stock_code + listing_date)
  ├─ 命中 frozen PR-B 2020–2024 universe
  │    → GovernedPRBMarketContextProvider   runtime_path = frozen
  └─ 未命中（2025 blind / 2026 / 完全新公司）
       → DynamicPITMarketContextProvider    runtime_path = dynamic_pit
            ├─ 有 PIT 覆盖 → AVAILABLE + 逐特征 missingness
            └─ 无 PIT 覆盖 → UNAVAILABLE / UNAVAILABLE_ERROR + reason_code
```

两条路径输出**同一个** Market-X Core 契约：15 个 raw feature、30 位向量、
同一个 `core_feature_manifest_hash`。因此模型侧可以对新案例构造与 frozen
模型完全一致的输入。

## 2. 全量 runtime 覆盖（Phase 1 + Phase 2 现状）

`scripts/run_market_runtime_audit.py --strict`（离线、无外部数据）：

```text
governed case count          562 / 565      （3 行为 manifest_only_placeholder，无官方 identity）
frozen runtime path          438
dynamic runtime path         124
error                          0
identity / hash / PIT 失败      0
missing-feature 被填 0          0
```

按上市年度：

| 上市年 | 15/15 available | partial | unavailable |
|---|---|---|---|
| 2020 | 41 | 74 | 10 |
| 2021 | 65 | 32 | 0 |
| 2022 | 40 | 38 | 0 |
| 2023 | 31 | 37 | 0 |
| 2024 | 31 | 39 | 0 |
| 2025 | 0 | 112 | 0 |
| 2026 | 0 | 0 | 12 |

2020 的 10 个 unavailable 与全部 partial 都不是缺陷：它们是 lookback 落在
universe 左边界之外、缺行业分类、或缺 prior-IPO outcome 源的**显式**结果，
每一个缺失都带 `missing_reason`。

产出物：`reports/v046_market_runtime/historical_market_runtime_audit.{json,csv}`
（`reports/` 未纳入 Git，跑一次即可重建）。

## 3. Dynamic 与 frozen 的一致性证明

对全部 438 个 frozen artifact 重放 dynamic builder，**offer-fact 家族
（7 个特征）438/438 逐值一致**：

```text
ipo_count_30d / ipo_count_60d
log_prior_ipo_funds_raised_30d / 60d
prior_ipo_funds_raised_30d_sample_count / 60d_sample_count
same_industry_ipo_count_180d
```

即 dynamic path 不是另一套口径，而是 frozen 口径在没有 artifact 时的
重算；两者唯一的差别在于 outcome 层是否配置（见 §5）。

## 4. PIT / 泄漏边界

- cutoff 只能来自 **target listing date**。没有 listing date 时 channel
  直接 `UNAVAILABLE`，`reason_code = new_case_identity_incomplete`；
  **绝不用当前日期兜底**（`_identity_incomplete`）。
- prior universe 只取 `listing_date < target listing_date`；恰好等于当日
  的上市不计入。
- prior IPO 的 1D/5D outcome 只有当 `target_session < target listing_date`
  才可用。
- target 自身按 `case_id` 与 `stock_code` 从 prior universe 中剔除。
- 从不读取 target 上市后的任何价格 / outcome：
  `provenance.target_post_listing_data_used = False`。
- 2025 Blind outcome 永远不进入任何特征：outcome pack 的 schema、builder 和
  loader 三处都对非 2020–2024 cohort **fail closed**。

### universe 的两个边界都被声明

`PriorIPOHistory` 同时携带左右边界：

```text
history_start_date = 首个 governed 上市日（2020-02-14）
history_end_date   = 最后一个 prospectus source year 的年末（2025-12-31）
```

右边界是这次新增的正确性修复。语料是「2020–2025 招股书」，2026 年的上市
只有已提交 2025 招股书的发行人才在册（12 家），因此 2026 覆盖天然不完整。
把 `max(listing_date)` 当成覆盖终点会让 2026 目标算出一个**偏低但看似有效**
的 `ipo_count_30d`。现在这种窗口一律返回
`prior_ipo_universe_right_boundary_incomplete`，落在覆盖终点之后的行也不参与
任何窗口计数。

## 5. 两层 prior-IPO history

| 层 | 内容 | 来源 | 是否入库 |
|---|---|---|---|
| offer facts | issuer identity、listing date、industry、funds raised | 已提交的 `data/catalog/ipo_official_master_bridge.csv` | 是（已在仓库） |
| outcomes | prior IPO 的 1D / 5D return 与 target session | licensed EOD 派生 | **否**，只提交 builder + schema |

没有 outcome pack 时，8 个 outcome 家族的 missing_reason 是
`prior_ipo_outcome_source_not_configured` —— 与「样本为空」是不同的事实，
也永远不是 0。

本地物化（需要授权 EOD）：

```bash
python scripts/build_prior_ipo_outcome_pack.py
```

默认写入 `data/competition/derived/prior_ipo_outcome_pack.json`；
`data/competition/` 整目录被 `.gitignore` 覆盖，所以派生数据不会被误提交。
然后启用：

```bash
export IPO_RISK_MARKET_DYNAMIC_OUTCOME_PACK=data/competition/derived/prior_ipo_outcome_pack.json
```

loader 对 pack 的校验（任一失败即整包拒绝，不做部分采纳）：

```text
schema_version → content_hash → official_bridge_sha256 谱系
→ case_id / stock_code / listing_date 三元 identity join
→ cohort year ∈ {2020..2024}
→ target session 不早于其自身上市日
```

## 6. missing_reason 词表

| reason_code | 含义 |
|---|---|
| `prior_ipo_universe_left_boundary_incomplete` | lookback 起点早于首个 governed 上市日 |
| `prior_ipo_universe_right_boundary_incomplete` | universe 覆盖终点早于目标上市前一日 |
| `missing_industry_classification` | 没有可用的行业分类，整个同业家族缺失 |
| `prior_ipo_outcome_source_not_configured` | 未配置 licensed-derived outcome pack |
| `prior_ipo_outcomes_withheld_blind_cohort` | 窗口内 prior IPO 全属 blind cohort，按政策不回读 |
| `no_prior_ipo_offer_amount_sample` | 窗口内没有任何披露募资额的 prior IPO |
| `no_recent_ipo_outcome_sample` | 窗口内没有已完成的 prior outcome |
| `no_same_industry_recent_outcome_sample` | 同业窗口内没有已完成的 prior outcome |

channel 级 `reason_code`：`dynamic_market_x_available`、
`dynamic_market_x_unavailable`、`new_case_identity_incomplete`、
`governed_history_invalid`。

## 7. 给 Model Owner 的 handoff

`ipo_risk.market.handoff.build_market_feature_handoff(view)` 对 frozen 与
dynamic 两条路径产出同一个 payload：

```text
schema_version = v046_market_feature_handoff_v1
case_id / stock_code / listing_date / dataset_split
market_runtime_path            frozen | dynamic_pit
core_feature_schema/policy/manifest_hash
feature_names / feature_values （30 位，含 __missing 指示位）
available_features / missing_features
missing_mask / missing_reasons
pit_cutoff_date / cutoff_semantics
source_provenance / artifact_content_hash
content_hash
```

Model 侧不重算 Market-X，只消费这个 payload；`missing_mask` 保证「值为 0」
与「值未知」在模型输入里不会被混淆。

## 8. 给 Frontend Owner 的合同

前端仍然只消费 `MarketContextView`：`status` / `reason` / `observations` /
`provenance`。新增可展示字段都在 `provenance` 里：`runtime_path`、
`identity_source`、`pit_cutoff_date`、`prior_ipo_universe_size`、
`prior_ipo_history_start_date` / `_end_date`、`outcome_history_available`、
`available_observation_count`。前端不需要读 bridge、outcome pack 或任何
builder 中间文件。

## 9. 配置

```yaml
market_context: governed_pr_b_core        # frozen 优先
market_dynamic_context: pit_bridge        # 非 frozen 案例走 dynamic PIT
market_dynamic_outcome_pack: ""           # 可选、本地、licensed-derived
```

已在 `configs/v045_competition_offline.yaml` 与
`configs/v045_competition_ai.yaml` 启用。`market_dynamic_context` 默认
`none`，因此所有既有 config 的 new-case 语义保持不变，直到显式启用。

## 10. 已知外部数据边界

以下仍然缺源，属于 Market-X **Extended** 契约，不在 Core 内，也不用代理值填补：

```text
HSI 指数历史            → hsi_return_5d / hsi_return_20d
行业指数历史 + PIT 映射  → industry_return_5d / industry_return_20d
全市场成交额            → market_turnover_20d_mean
基准波动率              → market_volatility_20d
```

在 dynamic path 下这些名字根本不出现在 observation 里（Core 15 名之外），
Market Regime Skill 因此返回 `INSUFFICIENT_DATA` 并列出 missingness——这是
诚实的能力声明，不是 bug。

## 11. 测试

```text
tests/unit/test_ipo_market_context_features.py   左/右边界、outcome 源缺失、每个缺失都有理由
tests/unit/test_prior_ipo_history.py             覆盖终点、unmatched 跳过、pack 六类 fail-closed、builder↔loader 一致
tests/unit/test_dynamic_market_context.py        新案例可用、无 listing date 不借用时钟、PIT 边界、
                                                 identity mismatch fail closed、缺行业、零填充禁令、
                                                 自我剔除、blind withheld、frozen→dynamic 组合
tests/unit/test_market_feature_handoff.py        两条路径同一 feature identity、mask 语义、content hash
tests/integration/test_v04_final_supervision_pipeline.py
                                                 竞赛 config 下 frozen 与 dynamic 两条路径的实际装配
```

回归基线未变：`scripts/check_v045_product_runtime.py` 仍为
`Market 3/3 × 15 observations`、`Model 3/3`。
