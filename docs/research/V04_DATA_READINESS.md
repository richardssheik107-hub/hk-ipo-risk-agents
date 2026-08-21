# V04 Data Readiness — Current Reference Snapshot

> Last real audit snapshot: **2026-08-21 PR-A A6 full determinism**  
> Documentation review: **2026-08-21**  
> Status: **PR-A COMPLETE / FROZEN / FULL MODEL-READY GATE STILL BLOCKED**

本文件记录当前**真实数据 readiness 审计结果**。计划文档更新不会虚构新的 coverage 数字；只有真实 materialization / source audit 后才允许修改这些统计。

PR-A 已完成 2020–2024 official 438-case Document materialization、Oracle coverage 与 A6 全量 determinism。完整 Market-X / model-ready gate 仍因 HSI、industry benchmark、total-market turnover 等 governed source 缺失而阻塞。

## 1. Official 2020–2024 modeling universe

已确认 official listing-year universe 为 **438 cases**：

- 2020：125
- 2021：97
- 2022：78
- 2023：68
- 2024：70

该 438-case universe 基于 authoritative official IPO metadata / listing year，不等于旧 565-document corpus 的 `source_year` 分组。

## 2. Official IPO metadata

`HK_Official_Merged_565_First_with_IPO.xlsx` 是 IPO identity、listing date、issue price、board、listing method、industry name 等 supplemental authoritative source。

`data/catalog/ipo_official_master_bridge.csv` 连接赛事文档与官方 IPO 主数据，并保留受控 provenance / checksum。

Security type 当前不是 eligibility gate：

```text
authoritative official IPO universe member -> eligible
security_type                                -> descriptive metadata
```

未知 security type 不自动转成 ordinary equity，也不使 official case 失去 eligibility。

## 3. Quarantined Security Master

现有 `hksharedescription.csv` 只覆盖较早历史记录，对 2020–2024 target universe 的多种 join route 均为 0 / 438。

因此它继续处于隔离 / descriptive-only 状态：

- 不决定 v0.4 eligibility；
- 不用于猜 listing date；
- 不用于猜 issue price；
- 不用于把 unknown security type 强行分类。

## 4. Governed IPO OHLCV

`CompetitionCSVMarketDataProvider` 已能从受控 bridge + 本地 `hkshareeodprices.csv` 读取 official target securities，并保留 source/version/checksum provenance。

最近一次真实市场数据审计：

- target IPOs：438；
- eligible：438；
- matched：432；
- missing：6；
- duplicate stock/date rows：0；
- conventionally invalid OHLCV rows：8,590；
- valid date coverage：2020-01-02 至 2026-05-22；
- valid 1D / 5D / 20D / 60D session coverage：432 cases。

6 个 outcome unavailable case：

```text
ipo_2020_01248
ipo_2020_06688
ipo_2020_06813
ipo_2021_01491
ipo_2022_06678
ipo_2022_07841
```

它们是 eligible but outcome unavailable，不得改写成 security-ineligible。

## 5. Reference-market inputs

### Available / partially usable

- authoritative IPO metadata；
- 432 / 438 governed IPO EOD histories；
- prior-IPO point-in-time context foundations；
- IPO structure features。

### Still missing

- governed HSI daily close history：`HSI_SOURCE_REQUIRED`；
- authoritative industry-to-index mapping：`INDUSTRY_INDEX_MAPPING_REQUIRED`；
- governed industry-index history：`INDUSTRY_INDEX_SOURCE_REQUIRED`；
- governed HKEX total-market turnover：`MARKET_TURNOVER_SOURCE_REQUIRED`。

注意：

- Hang Seng Bank ≠ Hang Seng Index；
- workbook industry name ≠ authoritative industry benchmark mapping；
- 单只证券 `S_DQ_AMOUNT` ≠ HKEX total-market turnover。

这些数据不能用不等价代理静默替代。

## 6. Production Document readiness — COMPLETE / FROZEN

所有 438 target cases 均有本地 prospectus，并已完成正式 PR-A materialization。

冻结 Production path：

```text
official case
→ enhanced_v2 IPOAnalysisResult
→ authoritative validation
→ V03DocumentRiskSnapshot
→ Production Document Feature Vector
```

`V04DocumentSnapshotMaterializer` 继续只接受 completed / partial `enhanced_v2` result，且要求：

```text
use_mock = false
parser = real
retriever = real
financial_agent = real
legal_agent = real
business_agent = real
cohort_year <= 2024
```

它拒绝 `mvp_v1`、Mock、未完成和 2025 blind result；不同 provenance / content 不允许静默覆盖。

PR-A 冻结结果：

```text
official cases                 = 438
Production analyses            = 438 / 438
authoritative snapshots        = 438 / 438
Production Document-X          = 438 / 438
feature schema                 = v04_document_features_v1
feature dimension              = 100
Production failures            = 0
silent drops                   = 0
2025 blind access              = NO
```

Document materialization source revision：

```text
13e0281f5e65a970caaf1255e56d08597e1ead70
```

A6 对 438 个 case 完成 `--resume --verify-determinism`：

```text
checked_case_count             = 438
passed                         = true
mismatch_count                 = 0
Production feature mismatch    = 0
Oracle feature mismatch        = 0
coverage_hash_ok               = true
```

A3 first-run coverage hash：

```text
47a15689789640f7abdf465b124f64742d96d8f4cb2a86b0a9d92107bf82dc42
```

A6 canonical resumed-state coverage hash：

```text
3b8201ea69f31804a7b99096d8392d3e32ca1bc60557dbf90e8050671eda2201
```

二者差异仅来自 resume 生命周期字段：`production_analysis_status: completed → skipped` 与 `production_snapshot_status: created → reused`；snapshot / Production feature / Oracle feature 等实质 hash 均未漂移。

## 7. Oracle readiness — MATERIALIZED / EVALUATION-ONLY

Oracle path：

```text
Reviewed Expert Gold
→ EffectiveRiskGoldView
→ Oracle Document Features
```

冻结结果：

- Oracle materialized：60；
- `no_reviewed_gold`：378；
- Production ∩ Oracle：60；
- missing Gold 不解释为零风险或负样本；
- Oracle 继续 `evaluation_only = true`；
- Oracle 不进入 Production runtime；
- Oracle 未读取 2025 blind y。

## 8. Current source manifest status

`data/catalog/v04_source_manifest.json` 使用 `v04_source_manifest_v1`，记录逻辑 source ID、portable relative path、source version、checksum、coverage、availability 与 provenance。

| Source | Required for | Status | Coverage / note |
|---|---|---|---|
| Official IPO metadata | identity | AVAILABLE | 438 / 438 |
| Official IPO universe | eligibility | AVAILABLE | 438 / 438 eligible |
| Security type | descriptive | OPTIONAL | unknown allowed |
| IPO OHLCV | outcomes / prior-IPO context | AVAILABLE | 432 / 438 |
| HSI closes | extended Market X | MISSING | 0 / 438 |
| Industry mapping | extended Market X | MISSING | 0 / 438 mapped |
| Industry-index closes | extended Market X | MISSING | not available |
| Total-market turnover | extended Market X | MISSING | not available |
| V03 authoritative snapshots | Production Document X | COMPLETE / FROZEN | 438 / 438 |
| Production Document-X | modeling input | COMPLETE / FROZEN | 438 / 438, 100 dimensions |
| Oracle Document-X | evaluation-only | MATERIALIZED | 60; 378 no reviewed Gold |

当前：

```text
PR-A_DOCUMENT_MATERIALIZATION_GATE = COMPLETE / FROZEN
PR-B_MARKET_X_GATE                  = NOT STARTED / NEXT
MODEL_READY_DATA_GATE               = BLOCKED
```

PR-A 已不再是 readiness blocker；当前 Model-ready blocker 来自后续 Market-X / Outcome / Dataset 里程碑。

## 9. PR-A completed changes

PR-A 已把 Document capability 转换为可复用的正式数据资产：

```text
438 official cases
→ Production analysis status
→ 438 authoritative snapshots
→ 438 Production feature vectors
→ Oracle inventory / 60 Oracle features
→ unified 438-row coverage
→ A6 deterministic rerun
```

正式冻结记录：

- `docs/V04_PR_A_COMPLETION_REPORT.md`
- `reports/frozen/v04_pr_a_document_materialization_manifest.json`

批量 runtime artifacts 保持本地且不进入 Git；对外打包前需要对本机绝对路径做 sanitized copy，不得修改 canonical frozen artifact。

## 10. External data still required for full Market-X

完整 Market-X 仍需要：

1. HSI history：date、close、stable index ID、source、version；
2. authoritative industry benchmark mapping：IPO industry → benchmark ID + effective dates + provenance；
3. industry-index history：benchmark ID、date、close、source、version；
4. HKEX total-market turnover：date、value、unit、market scope、source、version。

这些是下一正式里程碑 PR-B 的输入，不是 PR-A blocker。

正式 milestone / Gate / mainline merge 顺序继续保持：

```text
PR-A  COMPLETE / FROZEN
→ PR-B Market-X Core + Governed EOD Store
→ PR-C 5D Outcome Policy Freeze
→ PR-D Canonical Model-ready Dataset
→ PR-E Baseline + Oracle Diagnostic
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E
```

准备性研究可以提前进行，但不能越过正式 Gate 顺序合并。

## 11. Target governance

主研究对象仍是 5 trading-day weak-performance risk，但 classification threshold 尚未冻结。

任何 -5% / -10% / -15% / -20% 等候选阈值比较只能使用 2020–2023 Development outcome；2024 Validation 与 2025 Blind 不允许参与阈值选择。

在 PR-C 正式冻结 target policy 前，不把某个阈值写成最终标签定义。
