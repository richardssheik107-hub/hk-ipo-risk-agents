# V04 Data Readiness — Current Reference Snapshot

> Last real audit snapshot: **2026-08-21 PR-B full 438 materialization + determinism**
> Documentation review: **2026-08-21**  
> Status: **PR-A COMPLETE / FROZEN; PR-B COMPLETE / FROZEN; PR-C NEXT / NOT STARTED; MODEL-READY GATE BLOCKED**

本文件记录当前**真实数据 readiness 审计结果**。计划/代码更新不会虚构新的 coverage 数字；只有真实 materialization / source audit 后才允许修改 measured statistics。

PR-A 已完成 2020–2024 official 438-case Document materialization、Oracle coverage 与 A6 全量 determinism。PR-B 已在 source revision `dd67a17a5d6cfb246f0cb956c43e94aaddbc58a7` 完成真实 438-case Core materialization、PIT 审计和 deterministic resume 验证。

Market-X Extended 所需 HSI、industry benchmark、total-market turnover 等 governed source 仍缺失；这些是 Extended limitations，不是 PR-B Core 可以用 proxy 填补的数据。

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

## 4. Governed IPO OHLCV — measured foundation

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

### 4.1 PR-B governed EOD builder — frozen measured result

当前分支已将 `scripts/build_v04_ipo_eod_store.py` 修正为：

```text
official_match_status == matched
AND official_listed_date.year in 2020–2024
```

不再使用 document `source_year` 选择 modeling cohort。

过滤产物保留 `OBJECT_ID` source-record provenance；`S_DQ_AMOUNT` 明确保留为 per-security 原始列，不能解释为 HKEX total-market turnover。

冻结 governed EOD 结果：

```text
target cases                  438
row count                     433776
distinct target securities    432
provider OHLCV matched         432
provider OHLCV missing         6
raw EOD SHA256                 190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152
official bridge SHA256         751de6968ad8935ad45a8cd2841adbdc498d2bce6bb87153a1930959f4f85198
```

## 5. Market-X Core vs Extended readiness

### 5.1 Market-X Core — COMPLETE / FROZEN

Current Core contract：

```text
v04_ipo_market_context_features_v1
ipo_market_context_policy_v1
15 raw prior-IPO context features
+ 15 adjacent missing indicators
= 30 positions
```

Core 可使用当前已受治理/可严格 PIT 的输入：

- authoritative IPO metadata；
- 432 / 438 governed IPO EOD histories；
- prior-IPO point-in-time context；
- prior IPO offer/funds-raised facts；
- prior IPO 1D/5D outcomes only when their target session occurred strictly before the target listing date。

Measured freeze result：

```text
source revision                 dd67a17a5d6cfb246f0cb956c43e94aaddbc58a7
official coverage               438 / 438
Core materialized               438 / 438
failed / silent drops           0 / 0
PIT failures                    0
Development / Validation        368 / 70
feature manifest hash           c2f4a1699e2bf9149f24cb35ea32dbc4851c017001ec509a0eaccd93720d729d
coverage hash                   768b027676453d02d0cb5db8599acffbc2d58d7f5dc6e373bd9f4ddb305c974e
determinism                     438 checked / 0 mismatches / PASS
full pytest                     1303 passed / 0 failed / 2 warnings
2025 blind y accessed           NO
```

### 5.2 Market-X Extended — source gaps remain

Available / partially usable：

- authoritative IPO metadata；
- governed IPO EOD；
- prior-IPO context foundation。

Still missing：

- governed HSI daily close history：`HSI_SOURCE_REQUIRED`；
- authoritative industry-to-index mapping：`INDUSTRY_INDEX_MAPPING_REQUIRED`；
- governed industry-index history：`INDUSTRY_INDEX_SOURCE_REQUIRED`；
- governed HKEX total-market turnover：`MARKET_TURNOVER_SOURCE_REQUIRED`。

注意：

- Hang Seng Bank ≠ Hang Seng Index；
- workbook industry name ≠ authoritative industry benchmark mapping；
- 单只证券 `S_DQ_AMOUNT` ≠ HKEX total-market turnover；
- 不得创建 fake benchmark row 只为让 Extended engine 产生 observation date；
- missing source 不得填 market-neutral zero。

这些缺口不能用不等价代理静默替代，但它们本身不否定 PR-B Core 的可实现性。

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

二者差异仅来自 resume 生命周期字段；snapshot / Production feature / Oracle feature 等实质 hash 均未漂移。

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
| Official IPO metadata | identity / Core | AVAILABLE | 438 / 438 |
| Official IPO universe | eligibility / Core | AVAILABLE | 438 / 438 eligible |
| Security type | descriptive | OPTIONAL | unknown allowed |
| IPO OHLCV | outcomes / prior-IPO Core context | AVAILABLE | 432 / 438 |
| HSI closes | Extended Market X | MISSING | 0 / 438 |
| Industry mapping | Extended Market X | MISSING | 0 / 438 mapped |
| Industry-index closes | Extended Market X | MISSING | not available |
| Total-market turnover | Extended Market X | MISSING | not available |
| V03 authoritative snapshots | Production Document X | COMPLETE / FROZEN | 438 / 438 |
| Production Document-X | modeling input | COMPLETE / FROZEN | 438 / 438, 100 dimensions |
| Oracle Document-X | evaluation-only | MATERIALIZED | 60; 378 no reviewed Gold |

Current Gate state：

```text
PR-A_DOCUMENT_MATERIALIZATION_GATE = COMPLETE / FROZEN
PR-B_CORE_CODE_READINESS            = COMPLETE / FROZEN
PR-B_CORE_REAL_MATERIALIZATION      = 438 / 438
PR-B_GATE                           = PASS / COMPLETE / FROZEN
MARKET_X_EXTENDED_SOURCES           = INCOMPLETE
MODEL_READY_DATA_GATE               = BLOCKED
```

PR-A 与 PR-B 已不再是 readiness blocker。当前 Model-ready blocker 来自 PR-C target policy 与 PR-D canonical dataset；Extended source families 仍是后续可增强的 source limitation。

## 9. PR-B frozen evidence

Canonical records：

- `docs/V04_PR_B_COMPLETION_REPORT.md`
- `reports/frozen/v04_pr_b_market_x_core_manifest.json`
- `docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`

## 10. External data still required for Market-X Extended

Full Extended reference-market enrichment still requires：

1. HSI history：date、close、stable index ID、source、version；
2. authoritative industry benchmark mapping：IPO industry → benchmark ID + effective dates + provenance；
3. industry-index history：benchmark ID、date、close、source、version；
4. HKEX total-market turnover：date、value、unit、market scope、source、version。

These are not reasons to fabricate inputs or to reopen PR-A. If/when supplied, they enter the existing versioned Extended contract with provenance/tests.

Formal milestone / Gate / mainline merge order remains：

```text
PR-A  COMPLETE / FROZEN
→ PR-B COMPLETE / FROZEN
→ PR-C 5D Outcome Policy Freeze / NEXT / NOT STARTED
→ PR-D Canonical Model-ready Dataset
→ PR-E Baseline + Oracle Diagnostic
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E
```

## 11. Target governance

主研究对象仍是 5 trading-day weak-performance risk，但 classification threshold 尚未冻结。

任何 -5% / -10% / -15% / -20% 等候选阈值比较只能使用 2020–2023 Development outcome；2024 Validation 与 2025 Blind 不允许参与阈值选择。

在 PR-C 正式冻结 target policy 前，不把某个阈值写成最终标签定义。
