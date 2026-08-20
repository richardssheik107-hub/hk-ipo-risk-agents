# V04 Data Readiness — Current Reference Snapshot

> Last real audit snapshot: **preserved from the latest completed readiness run**  
> Documentation review: **2026-08-20**  
> Status: **PR-A INPUT READY / FULL MODEL-READY GATE STILL BLOCKED**

本文件记录最近一次**真实数据 readiness 审计结果**。计划文档更新不会虚构新的 coverage 数字；只有真实 materialization / source audit 后才允许修改这些统计。

当前 PR-A 可以开始，因为 Document pipeline、438-case official universe、Production feature contract 和 Oracle path 都已存在。完整 Market-X / model-ready gate 仍因 HSI、industry benchmark、total-market turnover 等 governed source 缺失而阻塞。

## 1. Official 2020–2024 modeling universe

最近一次审计确认 official listing-year universe 为 **438 cases**：

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

最近一次真实审计：

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

## 6. Production Document readiness

所有 438 target cases 均有本地 prospectus。

当前已有：

```text
CatalogIPODataProvider
run_batch
IPOAnalysisService
configs/v03_offline.yaml
V04DocumentSnapshotMaterializer
DOCUMENT_FEATURE_MANIFEST_V1
vectorize_document_snapshot(...)
```

Production path：

```text
official case
→ enhanced_v2 IPOAnalysisResult
→ authoritative validation
→ V03DocumentRiskSnapshot
→ Production Document Feature Vector
```

`V04DocumentSnapshotMaterializer` 只接受 completed / partial `enhanced_v2` result，且要求：

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

最近一次 readiness audit 时：

```text
authoritative snapshots = 0 / 438 existing
```

这表示**尚未执行全量 materialization**，不是 pipeline unavailable。

一个 development smoke 曾成功完成、生成 deterministic snapshot，并在第二次 materialization 复用相同 hash。历史约 16 秒 / case 仅作为容量参考，不是 SLA。

## 7. Oracle readiness

当前已有：

```text
scripts/index_oracle_gold.py
scripts/build_oracle_document_features.py
src/ipo_risk/modeling/oracle_document.py
```

Oracle path 只使用 reviewed expert annotation / explicit audit overlay，保留完整 provenance，并且 `evaluation_only = true`。

Oracle 不要求覆盖全部 438，也不能进入 Production runtime。

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
| V03 authoritative snapshots | Production Document X | PIPELINE AVAILABLE / NOT MATERIALIZED | 0 / 438 at latest audit |

当前：

```text
MODEL_READY_DATA_GATE = BLOCKED
```

但：

```text
PR-A_DOCUMENT_MATERIALIZATION_GATE = READY TO IMPLEMENT / RUN
```

二者不能混为一谈。

## 9. What PR-A must change

PR-A 不负责补 HSI / industry / turnover，也不训练模型。

PR-A 只需要把现有 Document capability 变成真实资产：

```text
438 official cases
→ Production analysis status
→ authoritative snapshots
→ Production feature vectors
→ Oracle inventory / features
→ unified coverage
→ deterministic rerun
```

因此下一次允许修改本文件核心 readiness 数字的事件是：

- PR-A 完成真实 Production / Oracle materialization；或
- 新 governed market source 被正式审计接入。

## 10. External data still required for full Market-X

完整 Market-X 仍需要：

1. HSI history：date、close、stable index ID、source、version；
2. authoritative industry benchmark mapping：IPO industry → benchmark ID + effective dates + provenance；
3. industry-index history：benchmark ID、date、close、source、version；
4. HKEX total-market turnover：date、value、unit、market scope、source、version。

这些是 PR-B / 后续完整 Market-X 的输入，不是 PR-A 的前置阻塞。

## 11. Target governance

主研究对象仍是 5 trading-day weak-performance risk，但 classification threshold 尚未冻结。

任何 -5% / -10% / -15% / -20% 等候选阈值比较只能使用 2020–2023 Development outcome；2024 Validation 与 2025 Blind 不允许参与阈值选择。

在 PR-C 正式冻结 target policy 前，不把某个阈值写成最终标签定义。
