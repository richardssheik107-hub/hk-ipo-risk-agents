# V0.4 C — Governed Industry Benchmark + HKEX Turnover Integration

## Gate 结论

本阶段将两个官方 source family 分别接入现有 Market-X Extended 接口，未修改冻结的 `v04_prelisting_market_features_v1` / `v04_market_features_v1`，特征顺序仍为 10 raw + 10 adjacent missing indicators = 20 positions。

> Official HSCI source integration complete; production industry-return feature remains intentionally blocked pending PIT-valid historical classification evidence. HKEX turnover production integration is complete.

```text
HSCI_SOURCE_STATUS = ACCEPT_PARTIAL_COVERAGE
HSCI_SERIES_ACCEPTED = 12 / 12
INDUSTRY_MAPPING_STATUS = EVIDENCE_BACKED_DRAFT
INDUSTRY_MAPPING_PIT_STATUS = INDUSTRY_MAPPING_PIT_BLOCKED
TURNOVER_SOURCE_STATUS = ACCEPT
TURNOVER_20D_AVAILABLE = 438 / 438
```

## Industry mapping 时点裁决

逐项验收结果：

```text
FIELD_SOURCE_SEMANTICS = Institution static merged record
TAXONOMY_MATCH = PASS
TOP_LEVEL_CODE_MATCH = PASS
NAME_MATCH = PASS
TEMPORAL_SEMANTICS = NO_CLASSIFICATION_EFFECTIVE_DATE_OR_LISTING_TIME_SNAPSHOT_ASSERTION
PIT_SAFE = NO
```

`IndustryCode`、`INDUSTRYNAME`、`IndustryCode2`、`IndustryName2` 均由工作簿字段字典标为 `Institution` 来源。交付工作簿创建于 2026-08-05；438 家中 398 家的同一静态记录 `DeclareDate` 晚于上市日、37 家早于上市日、3 家无法解析。`IndustryCode2` 与顶层 `IndustryCode` 的前缀冲突为 0，说明 taxonomy 层级一致，但不能证明各 IPO 上市时使用的是当时分类。

因此不伪造 `effective_from` / `effective_to`，也不把静态 mapping 接入 production。6 家缺官方 HSICS 分类；`SectorIndName` 不作替代。

## 438 家实测 coverage

Production 行业特征因 mapping PIT Gate 阻断：

```text
industry_return_5d = 0 / 438
industry_return_20d = 0 / 438

MISSING_INDUSTRY_CLASSIFICATION = 6 per feature
INDUSTRY_MAPPING_PIT_BLOCKED = 432 per feature
```

为判断是否值得购买旧历史，另做了明确标记为 non-production 的静态 mapping 条件性测算：

| 上市年 | cases | 静态 mapping | 条件性 5D | 条件性 20D | 历史缺口 5D | 历史缺口 20D | 缺分类 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 125 | 122 | 0 | 0 | 122 | 122 | 3 |
| 2021 | 97 | 95 | 28 | 27 | 67 | 68 | 2 |
| 2022 | 78 | 77 | 77 | 77 | 0 | 0 | 1 |
| 2023 | 68 | 68 | 68 | 68 | 0 | 0 | 0 |
| 2024 | 70 | 70 | 70 | 70 | 0 | 0 | 0 |
| 合计 | 438 | 432 | 243 | 242 | 189 | 190 | 6 |

条件性缺失原因进一步分解：历史尚未开始 187 家；5D 初始窗口不足 2 家；20D 初始窗口不足 3 家；unknown mapping 0；source error 0。

## HKEX turnover

正式定义冻结为：

```text
market_scope = Main Board + GEM; all securities in HKEX archive
measure = daily trading value / turnover
currency = HKD
unit = HKD
frequency = daily
aggregation = main_board_turnover_hkd + gem_turnover_hkd
coverage = 2019-01-02 ... 2025-12-31
rows = 1,722
```

`market_turnover_20d_mean` 使用上市日前 20 个 observed sessions，不使用 20 calendar days、上市日或未来数据。438/438 可用。

## Extended readiness 与 recent IPO

真实 438 家 raw feature availability：

```text
hsi_return_5d = 438
hsi_return_20d = 438
industry_return_5d = 0
industry_return_20d = 0
recent_ipo_break_rate = 244
recent_ipo_return_5d = 243
recent_ipo_1d_sample_count = 438
recent_ipo_5d_sample_count = 438
market_turnover_20d_mean = 438
market_volatility_20d = 438

FULL_10_RAW_AVAILABLE = 0 / 438
PARTIAL_AVAILABLE = 438 / 438
```

两个 recent IPO sample-count 特征全部 materialize。break rate 的 194 个缺失和 5D return 的 195 个缺失均为合法 `no_recent_ipo_sample`，不是 HSI/source failure。

## HSCI 历史回补决策

```text
AFFECTED_CASES = 190
AFFECTED_YEARS = 2020, 2021
PERCENT_OF_438 = 43.3790%
DEVELOPMENT_SET_IMPACT = 190
VALIDATION_SET_IMPACT = 0
TEMPORAL_MISSINGNESS_RISK = HIGH
PURCHASE_RECOMMENDED = NO
```

HKD 1,000 历史产品确实会补齐静态 mapping 条件下 190 家早期 Development 案例，并消除明显年份偏差；但它不能解决更前置的分类 PIT 问题。当前购买不会解锁任何 production industry feature。应先取得 listing-time 或带历史生效日的 HSICS 分类源；若该 Gate 以后通过，再重新评估购买，此时 190/438 的受影响规模足以支持 `OPTIONAL/YES` 的新决策。

## 治理与复现

两个 loader 均验证 manifest、SHA-256、精确 series/字段、重复日期、正值、排序、scope/currency/unit 与确定性。438 家以 provider strict cutoff、包含未来行的 poisoning 输入、再次 strict rebuild 三次运行，结果完全一致。

```text
PIT = PASS for HSI/HSCI bars/HKEX turnover; industry mapping BLOCKED
FUTURE_ROW_POISONING = PASS
DETERMINISM = PASS
SILENT_DROPS = 0
2025_BLIND_Y_ACCESSED = NO
```

详细 438 行文件位于 ignored 本地目录 `data/competition/market_reference/audit/`。版本化聚合证据为 `data/catalog/v04_c_extended_readiness_summary.json`。

```text
PR_B_CORE_CHANGED = NO
PR_C_POLICY_CHANGED = NO
PR_D_DATASET_CHANGED = NO
PR_G_AGENT_CONTRACT_CHANGED = NO
RAW_DATA_COMMITTED = NO
```
