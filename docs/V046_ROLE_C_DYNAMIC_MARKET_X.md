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

按上市年度（`15/15` 列给出未配置 / 已配置 outcome pack 两种情形）：

| 上市年 | Core 15/15 available | partial | unavailable |
|---|---|---|---|
| 2020 | 41 | 74 | 10 |
| 2021 | 65 | 32 | 0 |
| 2022 | 40 | 38 | 0 |
| 2023 | 31 | 37 | 0 |
| 2024 | 31 | 39 | 0 |
| 2025 | 0 → **3** | 112 → 109 | 0 |
| 2026 | 0 | 0 | 12 |

2025 只有 3 家能拿到 15/15，不是缺陷而是 blind 政策的正确结果：只有 60 天
lookback 仍能回溯到 2024 outcome cohort 的年初案例才有 prior outcome；其余
112 家窗口内全是 blind cohort，返回 `prior_ipo_outcomes_withheld_blind_cohort`。
2025 全年缺失理由分布：

```text
302  prior_ipo_outcomes_withheld_blind_cohort
102  no_same_industry_recent_outcome_sample
 10  missing_industry_classification
```

2020 的 10 个 unavailable 与全部 partial 都不是缺陷：它们是 lookback 落在
universe 左边界之外、缺行业分类、或缺 prior-IPO outcome 源的**显式**结果，
每一个缺失都带 `missing_reason`。

产出物：`reports/v046_market_runtime/historical_market_runtime_audit.{json,csv}`
（`reports/` 未纳入 Git，跑一次即可重建）。

## 3. Dynamic 与 frozen 的一致性证明

对全部 438 个 frozen artifact 重放 dynamic builder：

```text
未配置 outcome pack   offer-fact 7 个特征     438/438 逐值一致
已配置 outcome pack   全部 15 个 Core 特征    438/438 逐值一致，0 例不一致
```

**dynamic path 不是另一套口径，而是 frozen 口径在没有 artifact 时的重算。**

谱系也是可校验的，不是口头声明：outcome pack 的 `ipo_eod_sha256` 与 438 个
frozen artifact 的 `source_provenance.ipo_eod_sha256` 相同
（`190e45ff…c007152`），即两者派生自同一份 EOD 抽取。

这条等价性已固化为回归测试
`tests/integration/test_dynamic_market_x_frozen_equivalence.py`：
offer-fact 部分在干净 checkout 里就能跑；15/15 部分与谱系校验在 pack 缺席时
skip，物化后自动生效。

唯一的语义差异：约 10 个 2020 年初案例的所有特征都落在 universe 左边界之外，
frozen 报 `AVAILABLE`（一个校验通过、15 个值全为 null 的 artifact），dynamic 报
`UNAVAILABLE`（什么都算不出来）。**observation 层面的事实完全一致**，
两者都不是 error。

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

本机已物化一次（授权 EOD 位于仓库外，未复制进仓库，用 `--data-root` 指过去）：

```text
record_count             438        （= 2020–2024 outcome cohort，无一条 2025）
content_hash             9db11d85d06aed940e8e48e2fa0698fedbf79fb875b6eb8a9c552b0b41deff92
ipo_eod_sha256           190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152
blind_outcomes_included  false
```

`ipo_eod_sha256` 与 frozen artifact 记录的一致，见 §3。

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

### 7.1 payload

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

### 7.2 与冻结模型身份的绑定

Model owner 不应该被要求「相信」一个 dynamic 案例。
`verify_market_handoff_binding(handoff, frozen_dir=...)` 把 handoff 对
`reports/frozen/v04_pr_b_market_x_core_manifest.json` 逐项核对，**任何不符即
抛错，不降级为 warning**：

| check | 含义 |
|---|---|
| `core_feature_schema_version` | 与冻结 Market-X 同一 schema |
| `core_feature_policy_version` | 同一口径策略 |
| `core_feature_manifest_hash` | 同一 feature manifest（`c2f4a169…`） |
| `feature_position_count` | 向量宽度 = 冻结的 30 位 |
| `ipo_eod_sha256` | 同一份 EOD 抽取（handoff 声明时才校验） |
| `prior_ipo_history_start_date` | 同一个 prior universe 左边界 |

外加链路检查：`v04_pr_d_input_binding_manifest.json` 声明的上游 PR-B 哈希必须
仍指向这份 manifest，否则说明模型的 input binding 建在另一份 Market-X 之上。

实测（本机，配置 outcome pack 后）：

```text
frozen  ipo_2024_02410  2024-08-20  → 6/6 checks match，pr_d_input_binding match
dynamic ipo_2024_02530  2025-01-10  → 6/6 checks match，pr_d_input_binding match
        （blind split，15/15 特征可用，missing_mask 全 0）
```

一个 blind cohort 的 2025 案例，**完全由 dynamic 重算**，能证明自己与冻结模型
用的是同一个 feature 身份、同一份 EOD、同一个 universe 左边界。

### 7.3 物化产物

```bash
python scripts/build_market_feature_handoff.py --case-id ipo_2024_02530
python scripts/build_market_feature_handoff.py --stock-code 9999.HK --listing-date 2025-06-02
```

每个案例写出 `{handoff, model_binding}`；**绑定失败的案例不写盘，只在
`skipped` 里报告原因**。全 universe 统计（见 §2 audit）：

```text
model handoff bound            550 / 562
not projectable                 12       （2026 上市：Core 越过覆盖终点，channel unavailable）
```

### 7.4 一个真实发现：CRLF 让冻结链路看起来是断的

PR-D 记录的上游 PR-B 哈希（`640190d3…`）是在 Windows checkout 下算的，
Git 存的是 LF 版本（`76a631fd…`）。用朴素的 `sha256(file)` 去校验这条链，
会得出「模型的 input binding 建在另一份 Market-X 上」的错误结论。

仓库里本来就有同类处理（official bridge 的 CRLF 容忍），本 PR 把它统一成
`ipo_risk.market.prior_ipo_history.line_ending_agnostic_hashes`，
`market_context` / `outcome_pack` / `handoff` 三处共用一份实现。
容忍的只有换行表示，任何字段、行序或其它字节差异仍然 fail closed。

## 8. 给 Frontend Owner 的合同

前端仍然只消费 `MarketContextView`：`status` / `reason` / `observations` /
`provenance`。新增可展示字段都在 `provenance` 里：`runtime_path`、
`identity_source`、`pit_cutoff_date`、`prior_ipo_universe_size`、
`prior_ipo_history_start_date` / `_end_date`、`outcome_history_available`、
`extended_status`、`available_observation_count`。前端不需要读 bridge、
outcome pack 或任何 builder 中间文件。

### 8.1 运行路径必须可见

「Market-X 可用 15/15」这句话，冻结产物和动态重算读起来完全一样——而对一份
本项目从没见过的招股书，**这恰恰是读者最需要知道的一件事**。把它留在默认折叠的
provenance JSON 里，等于技术上存在、实际上不可见。

`app.competition_ui.market_runtime_summary(payload)` 把 provenance 投影成一张
小表，Streamlit 市场面板在标题行与观测表之间渲染它：

```text
运行路径          冻结 PR-B 产物 | 动态 PIT 重算
PIT 截止时点      2025-02-12
数据集划分        开发集 / 验证集 / 盲测集
身份解析          官方目录 case_id | 股票代码+上市日 | 调用方提供（不在目录内）
前序 IPO 样本量   446
前序结果数据层    已配置 | 未配置（结果族显式缺失，不补零）
Extended 市场环境 已配置 | 未配置 | 读取失败
```

后四行只在 `runtime_path = dynamic_pit` 时出现。**provenance 里没有的字段不产生
行**，因此这张表不会声称 Market 通道没有主张过的来源。七阶段视图的 Market
Features 同样区分两条路径：dynamic 案例的 summary 明说「不在冻结 universe 内、
按同一 PIT 契约重算」，并多出一个 `Market runtime path` 指标；frozen 案例的措辞
一字未改。

## 9. 配置

```yaml
market_context: governed_pr_b_core            # frozen 优先
market_dynamic_context: pit_bridge            # 非 frozen 案例走 dynamic PIT
market_dynamic_outcome_pack: ""               # 可选、本地、licensed-derived
market_dynamic_extended_hsi_csv: ""           # 可选、本地、licensed（CSMAR HSI）
market_dynamic_extended_turnover_csv: ""      # 可选、本地、licensed（HKEX 成交额）
```

Extended 两个路径必须同时配置才生效：只有其中一个不算「半个源」。

已在 `configs/v045_competition_offline.yaml` 与
`configs/v045_competition_ai.yaml` 启用。`market_dynamic_context` 默认
`none`，因此所有既有 config 的 new-case 语义保持不变，直到显式启用。

## 10. Market-X Extended 与它真正的边界

Extended 的四类源**早已由 C 线接入并通过治理验收**，不是缺源。按
`docs/research/V04_C_INDUSTRY_TURNOVER_INTEGRATION.md` 与
`data/catalog/v04_c_extended_readiness_summary.json` 记录的实测：

| Extended 特征 | 源 | 438 家可用数 | 状态 |
|---|---|---|---|
| `hsi_return_5d` / `hsi_return_20d` | CSMAR 恒生指数日行情 | 438 / 438 | ACCEPT |
| `market_volatility_20d` | 同上（基准已实现波动率） | 438 / 438 | ACCEPT |
| `market_turnover_20d_mean` | HKEX 官方全市场成交额 | 438 / 438 | ACCEPT |
| `industry_return_5d` / `industry_return_20d` | 恒生综合行业指数 12 条 series | **0 / 438** | 源 ACCEPT、**分类映射 PIT-blocked** |

`pit_detail: HSI/HSCI/HKEX are strict-before; unsafe industry mapping is blocked`。

行业两项为 0 **不是缺源，是治理主动阻断**：交付的 HSICS 静态分类没有
`effective_from` / `effective_to`，无法证明它是上市时点的分类，接进 production
会破坏 PIT。C 线因此记录 `INDUSTRY_MAPPING_PIT_BLOCKED` 并明确否决了
「买 HKD 1,000 历史产品」的方案——补历史修不好分类的时点问题。
**本 PR 不解除这个阻断。**

真正的边界是另外三件事：

1. 逐案产物 `v04_c_extended_readiness_438.csv`（438 行，
   sha256 `9fc6b5c1…`）按授权约定不入库，发布 config 里
   `market_extended_readiness: ""`，所以默认运行时那 6 个名字不出现。
2. 该 CSV **按 `case_id` 索引**，天然只能服务 frozen 的 438 家，
   给不了新 IPO——这正是本 PR §10.1 要补的缺口。
3. CSMAR HSI 的授权声明是「仅供西安交通大学使用；原始与 normalized 数据
   不得提交公开仓库」，所以 Extended 与 outcome pack 一样，**仓库只提交
   builder / provider / schema，数据留在本地**。

### 10.1 Dynamic Extended：让新 IPO 也拿到市场状态

`PreListingMarketFeatureEngine` 本身**不按 case_id 索引**，它只要一个
`listing_date` 作为 exclusive cutoff。缺的只是一个能按任意上市日取数的组合层，
本 PR 补上 `ipo_risk.market.dynamic_extended.DynamicExtendedMarketSource`：

```text
CSMARHSIProvider            → hsi_return_5d / hsi_return_20d / market_volatility_20d
OfficialHKEXTurnoverProvider→ market_turnover_20d_mean
行业两项                     → 恒定 INDUSTRY_MAPPING_PIT_BLOCKED（不解除阻断）
```

配置后，dynamic path 的 observation 从 15 个 Core 扩展到 21 个
（Core 15 + Extended 6），与 frozen + extended_readiness 的形状一致，
Market Regime Skill 因此能给出真实 regime 而不是 `INSUFFICIENT_DATA`。

```yaml
market_dynamic_extended_hsi_csv: <本地 normalized HSI csv>
market_dynamic_extended_turnover_csv: <本地 normalized HKEX turnover csv>
```

未配置时这 6 个名字仍然完全不出现——不是填 0，也不是伪造 unavailable。

已知剩余边界：`PreListingMarketFeatureContext` 校验 `dataset_split` 必须匹配
`expected_market_split(cohort_year)`，后者只认 2020–2025。因此 2026 及以后的
上市日会得到 6 个 `listing_year_outside_governed_market_split` 的显式缺失。
放宽它属于改动冻结的 split 治理契约，不在本 PR 范围内。

## 11. 测试

```text
tests/unit/test_ipo_market_context_features.py   左/右边界、outcome 源缺失、每个缺失都有理由
tests/unit/test_prior_ipo_history.py             覆盖终点、unmatched 跳过、pack 六类 fail-closed、builder↔loader 一致
tests/unit/test_dynamic_market_context.py        新案例可用、无 listing date 不借用时钟、PIT 边界、
                                                 identity mismatch fail closed、缺行业、零填充禁令、
                                                 自我剔除、blind withheld、frozen→dynamic 组合
tests/unit/test_market_feature_handoff.py        两条路径同一 feature identity、mask 语义、content hash、
                                                 与冻结 manifest 的 6 项绑定、manifest 漂移 / universe 边界不符 /
                                                 PR-D 建在另一份 manifest 上均 fail closed、真实仓库链路（含 CRLF）
tests/unit/test_dynamic_extended_market.py       新上市日拿到 HSI/turnover、行业保持 PIT-blocked、
                                                 benchmark 严格早于上市日、split 外显式缺失、
                                                 缓存缺失是 error 不是空序列、Core+Extended 21 个 observation、
                                                 Extended 读取失败不拖垮 Core、未配置时一个名字都不出现
tests/integration/test_dynamic_market_x_frozen_equivalence.py
                                                 438 个 frozen artifact 逐值重放；无 pack 时比 7 个 offer-fact 特征，
                                                 有 pack 时比全部 15 个，并校验 EOD 谱系哈希
tests/integration/test_v04_final_supervision_pipeline.py
                                                 竞赛 config 下 frozen 与 dynamic 两条路径的实际装配
```

回归基线未变：`scripts/check_v045_product_runtime.py` 仍为
`Market 3/3 × 15 observations`、`Model 3/3`。
