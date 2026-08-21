# V04-3 Pre-listing Market Features

> Contract status: **MERGED / FROZEN FOR v0.4 — EXTENDED CONTRACT**  
> Documentation review: **2026-08-21**

## 1. Scope

V04-3 defines the deterministic, point-in-time **Market-X Extended** contract used above V04-1 Market Foundation and V04-2 Document Feature Contract.

它不训练模型，也不改变 Document Risk 语义。PR-B 后新增并冻结的 30-position Market-X Core 是独立的 versioned artifact，不由本文件的 20-position Extended contract 取代或吸收。

所有 canonical Market-X 必须在目标 IPO 上市前可获得：

```text
market_data_date <= observation_date < listing_date
```

目标 IPO 的 post-listing `MarketOutcomeLabel` 永远不能用于构造该 IPO 的 pre-listing X。

## 2. Architecture

```text
V03DocumentRiskSnapshot
→ 100-position Production Document Vector

Governed pre-listing reference / prior IPO data
→ PreListingMarketFeatureEngine
→ 20-position Extended Market Vector

Historical Extended-only join:
Document X + Extended Market X + non-blind Outcome
→ V04MarketAugmentedModelingDataset
```

`MarketReferenceDataProvider` 与 V04-1 per-security `MarketDataProvider` 分离。纯 feature engine 不依赖 network、clock、random、LLM、Retriever 或 Agent。

PR-B Core 的 canonical implementation / materialization 位于 `src/ipo_risk/market/ipo_market_context_features.py` 与 `scripts/run_v04_pr_b.py`，不属于本 Extended engine 的 schema。

## 3. Observation cutoff

Policy `v04_prelisting_market_features_v1` 要求：

- `observation_date` 为目标 IPO 上市日前最后一个可用 reference session；
- 上市日及之后的数据在计算前被排除；
- 修改 T / T+N 数据不能改变合法历史 feature snapshot；
- 无合法历史 observation 时，对应 feature family 显式 unavailable。

## 4. Return / volatility formulas

HSI / industry return 使用 observed sessions：

```text
return_5d  = close(t) / close(t-5)  - 1
return_20d = close(t) / close(t-20) - 1
```

20D volatility 使用 21 个 close 生成 20 个单期 log return，再计算 population standard deviation (`ddof=0`)，不做年化。

Industry benchmark ID 必须来自 authoritative mapping；不允许根据公司名、股票代码或 LLM 猜行业指数。

## 5. Turnover semantics

`market_turnover_20d_mean` 只能使用 governed total-market turnover。

禁止：

- 用单股 volume 替代；
- 用单股 `S_DQ_AMOUNT` 替代；
- 在 source 缺失时填 0。

无 source 时保持：

```text
unavailable / missing_turnover_source
```

## 6. Recent IPO context

V1 recent-IPO universe：最多取目标上市日前 60 calendar days 内、且 listing date 不晚于 observation date 的最近 20 个 eligible official IPO。

目标 case / stock 必须排除。

已知 prior-IPO outcome 还需满足：

```text
prior_label.target_trading_date <= target_observation_date
```

也就是说，即使 prior IPO 已经上市，如果其 5D outcome 在目标 IPO 的 observation date 当时还没有形成，也不能使用。

核心 feature：

```text
recent_ipo_break_rate
recent_ipo_return_5d
recent_ipo_1d_sample_count
recent_ipo_5d_sample_count
```

零有效样本返回 `None` + sample_count=0，而不是把 return / break rate 填成 0。

## 7. Current real-data correction

旧版本文档曾写“recent IPO labels cannot be materialized until governed price history exists”。该表述已经过时。

当前 readiness 已经确认：

```text
Governed IPO OHLCV coverage = 432 / 438
PR-B Market-X Core          = 438 / 438 materialized / COMPLETE / FROZEN
```

因此 recent-IPO point-in-time context **已有真实 governed IPO EOD foundation**，并且 PR-B Core 已使用严格的可得性边界完成全量物化。

当前真正仍缺的是 Extended reference-market source：

```text
HSI history
industry benchmark mapping
industry-index history
total-market turnover
```

所以当前状态应理解为：

- PR-B Market-X Core：**COMPLETE / FROZEN**；
- recent IPO context foundation：**available**；
- 本文件定义的 HSI / industry / turnover Extended families：**source incomplete / missing**；
- full 20-position Extended Market-X 在完整真实源层面尚未全覆盖。

## 8. Missing-data contract

每个 raw feature 都保留：

- value；
- availability；
- missing reason；
- provenance。

Missing reason 区分：

- insufficient history；
- missing benchmark；
- missing industry mapping；
- missing industry series；
- no recent IPO sample；
- missing turnover source；
- generic unavailable source。

缺失不得转换为 market-neutral zero。

## 9. Feature manifest

`v04_market_features_v1` 冻结 10 个 raw positions：

1. `hsi_return_5d`
2. `hsi_return_20d`
3. `industry_return_5d`
4. `industry_return_20d`
5. `recent_ipo_break_rate`
6. `recent_ipo_return_5d`
7. `recent_ipo_1d_sample_count`
8. `recent_ipo_5d_sample_count`
9. `market_turnover_20d_mean`
10. `market_volatility_20d`

每个 raw feature 紧跟一个 `__missing` indicator，共 20 个 ordered numeric positions。

Manifest 有 deterministic SHA-256 hash；legacy `MarketSnapshot.sentiment_score` 不属于该 manifest。

## 10. Historical Extended-only combined modeling contract

现有 `V04MarketAugmentedModelingDataset` 的历史 Extended-only 组合顺序保持：

```text
[100 Production Document features]
+
[20 Extended Market features]
=
120 positions
```

这个 120-position 顺序是**既有历史 contract**，不是 PR-D 即将冻结的 canonical model-ready dataset contract。

PR-B 已新增并冻结独立的：

```text
Market-X Core
15 raw + 15 missing indicators
= 30 positions
```

因此 PR-D 必须显式决定新的 versioned dataset contract 如何组合：

```text
Production Document X (100)
+ Market-X Core (30)
+ optional Market-X Extended (20)
+ PR-C frozen Outcome Y
```

不得把 30-position Core 静默插入、替换或重排现有 120-position historical join；任何新的 canonical feature-group order 都必须有明确 schema/version/hash 与契约测试。

Development 只接受 2020–2023；Validation 只接受 2024。

2025 只允许 feature-only export，不得包含 outcome / target / label horizon。

## 11. Current limitations

- governed HSI series 尚未接入；
- authoritative industry-to-index mapping / series 尚未接入；
- governed total-market turnover 尚未接入；
- recent IPO context 受 432 / 438 IPO EOD coverage 和 point-in-time outcome availability 限制；
- exchange calendar 仍采用 supplied observed sessions，而非完整独立 HKEX calendar source；
- sentiment 不属于当前 frozen Market-X contract。

这些限制在 PR-B 完成后继续作为 **Market-X Extended 的显式 source limitations** 保留；它们不重开 PR-B，也不允许用 proxy 填补。PR-D 只负责显式、versioned 地决定 Core 与 optional Extended 如何进入 canonical dataset。

## 12. Out of scope

V04-3 不实现：

- Market Agent；
- Logistic / LightGBM training；
- SHAP / calibration；
- 2025 outcome evaluation；
- Parser / Retriever / Agent / Verifier / Supervisor 调优；
- PR-C outcome policy；
- PR-D canonical Core/Extended dataset contract。

当前执行顺序以 `../END_TO_END_CLOSED_LOOP_MASTER_PLAN.md` 为准。
