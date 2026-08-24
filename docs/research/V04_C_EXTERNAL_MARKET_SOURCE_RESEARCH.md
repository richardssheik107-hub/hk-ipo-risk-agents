# V0.4 C — External Market Source Research

## 结论

截至 2026-08-23，HSI 已由 CSMAR 权威交付解决。本轮新增完成：

- 恒生行业分类（HSICS）识别与 12 个行业基准的证据化映射草案；
- 12/12 个 HSCI 行业价格指数的恒生官网公开日收盘暂存，覆盖 2021-08-19 至 2025-12-30；
- HKEX Main Board + GEM 全市场每日成交额，覆盖 2019-01-02 至 2025-12-31。

HSCI 的 2019-01-01 至 2021-08-18 仍缺失。恒生官网目录把更长的每日历史列为付费历史数据产品，公开图表端点只提供滚动五年，因此没有用代理或推算补洞。

## 1. 现有数据审计

未重复寻找 listing date、issue price、个股 EOD、HSI 或公司基本信息。官方合并工作簿为：

`HK_Official_Merged_565_First_with_IPO.xlsx`

- SHA-256：`2cc214e1f027f44de582eddb02b13dfc2f43f57cc8c530250431ad36ed222e25`
- 项目 2020–2024 正式 438 个案例由 `data/catalog/ipo_official_master_bridge.csv` 连接。

字段覆盖：

| 字段 | 非空 | 唯一值 | 覆盖率 | 结论 |
|---|---:|---:|---:|---|
| `IndustryCode` | 432 | 11 | 98.6301% | HSICS 顶层两位行业代码 |
| `INDUSTRYNAME` | 432 | 11 | 98.6301% | HSICS 顶层行业中文名 |
| `IndustryCode2` | 432 | 90 | 98.6301% | 工作簿字段字典明确标注“恒生行业代码”；值形态对应 HSICS 更低层六位代码 |
| `IndustryName2` | 432 | 90 | 98.6301% | 工作簿字段字典明确标注“恒生行业” |
| `SectorIndName` | 438 | 106 | 100% | 未在工作簿字段字典中获得权威体系说明，不用于 HSCI 映射 |

`IndustryCode` / `INDUSTRYNAME` 的 11 个实际组合（正式 438 案例）：

| Code | Name | Count |
|---|---|---:|
| 00 | 能源業 | 3 |
| 05 | 原材料業 | 11 |
| 10 | 工業 | 44 |
| 23 | 非必需性消費 | 89 |
| 25 | 必需性消費 | 25 |
| 28 | 醫療保健業 | 107 |
| 35 | 電訊業 | 2 |
| 40 | 公用事業 | 3 |
| 50 | 金融業 | 17 |
| 60 | 地產建築業 | 78 |
| 70 | 資訊科技業 | 53 |

6 个案例的四个恒生行业字段为空，但 `SectorIndName` 非空；由于后者体系未确认，保持行业基准缺失。正式样本没有 `80 Conglomerates` 案例，不代表官方分类体系不存在该行业。

## 2. Taxonomy 与 mapping 的权威证据

[Hang Seng Industry Classification System 官方页面](https://origin-www.hsi.com.hk/eng/our-services/hsics)说明 HSICS 是面向香港市场的三层分类，包含 12 个 industries、31 个 sectors 和 112 个 subsectors；IPO 分类在上市前依据招股书完成。

[Hang Seng Composite Index Series Methodology（Sep 2025, Version 2.5）](https://www.hsi.com.hk/static/uploads/contents/en/dl_centre/methodologies/IM_industrye.pdf)进一步给出：

- 第 9 页：12 个 HSCI Industry Index 的官方行业代码 `00, 05, 10, 23, 25, 28, 35, 40, 50, 60, 70, 80`；
- 第 15 页：12 个价格指数的 Refinitiv vendor codes（例如 `.HSCIE`、`.HSCIIG`、`.HSCICD`）；
- 第 13 页：这些序列是 price indexes，不含现金股息调整；
- 第 11–12 页：行业重分类按半年审查并在相应生效日切换。

因此，工作簿顶层 `IndustryCode` 与 HSCI 行业基准的 taxonomy/code/name 对应关系成立，mapping 草案保存于 `data/catalog/v04_c_hsics_benchmark_mapping_draft.csv`。但该结论不等于 IPO 时点安全：四个行业字段均来自 `Institution` 静态记录，合并工作簿创建于 2026-08-05，且 438 家中 398 家的同记录 `DeclareDate` 晚于上市日。工作簿没有分类生效日，也没有声明这些值是上市时快照。因此 `effective_from` / `effective_to` 保持空值，mapping 状态为 `EVIDENCE_BACKED_DRAFT / PIT_BLOCKED`，不得接入 production 行业特征。

## 3. HSCI 行业指数历史

### ACCEPT_PARTIAL_COVERAGE — PRIMARY_OFFICIAL

恒生官网公开目录：

`https://origin-www.hsi.com.hk/data/eng/index-series/directory.json`

目录把 12 个目标指数逐一关联到内部代码 `00011.01` 至 `00011.14`（中间代码按官方序列定义并非连续）。每个指数的公开图表端点为：

`https://origin-www.hsi.com.hk/data/eng/indexes/<internal_index_code>/chart.json`

验收结果：

- 目标：12；找到：12；接受：12；
- 每序列 1,072 行，合计 12,864 行；
- 目标窗口内覆盖：2021-08-19 至 2025-12-30；
- 字段：`benchmark_id`, `trading_date`, `close`；
- 频率：daily；类型：price index；
- 重复日期 0、缺失 close 0、`close <= 0` 0、非有限值 0、排序错误 0；
- 未插值、未 forward fill、未以 HSC/HSF/HSP/HSU 替代。

暂存文件（ignored）：

`data/competition/market_reference/normalized/hsci_industry_daily_close_official_public_5y.csv`

SHA-256：`b0aa7c3ac1d1cbf9e466acbf7f3bfcc33fead9891c992676a2c4a5d8f9f2ac21`

### 缺口与访问限制

公开 `chart.json` 是滚动五年窗口。恒生目录的 `historicalDataProductTypes` 将 daily 历史列为最长 60 个月、价格 HKD 1,000 的历史数据产品；Index360 页面也要求账户才能解锁更广数据。因此 2019-01-01 至 2021-08-18 标记为 `MANUAL_ACCESS_REQUIRED`，未绕过登录或付费限制。

官网公开 `dailyClose` API 被按页面代码原样请求后返回 HTTP 200 但 `data: null`，不能作为可下载数据源。Investing.com 能检索到多个目标代码的历史页面，但直接无登录请求返回 403，且没有获得稳定、可审计、无需规避限制的批量端点，故未接受也未下载。

## 4. HKEX 全市场日成交额

### ACCEPT — PRIMARY_OFFICIAL

官方页面：

- [Securities Statistics Archive — Main Board](https://www.hkex.com.hk/Market-Data/Statistics/Consolidated-Reports/Securities-Statistics-Archive/Trading_Value_Volume_And_Number_Of_Deals?sc_lang=en)
- [Securities Statistics Archive — GEM](https://www.hkex.com.hk/Market-Data/Statistics/Consolidated-Reports/Securities-Statistics-Archive-GEM/Trading_Value_Volume_And_Number_Of_Deals?sc_lang=en)

页面公开 JSON 分片提供每日 `Total trading value (HKD)`。本地按同一交易日严格相加 Main Board 与 GEM：

- `market_scope`：Main Board + GEM；HKEX archive 中的全部证券；
- 不是 equities-only；可包含该市场日报覆盖的 ETF、REIT、权证、CBBC 等证券；
- `currency`：HKD；`unit`：HKD（不是千港元或百万港元）；
- 2019-01-02 至 2025-12-31，共 1,722 行；
- Main Board/GEM 在目标窗口内日历不匹配 0；
- 重复日期 0、空值 0、非正值 0、排序错误 0。

逐日汇总校验：2019 年合计 `21,440,049.157119` HKD million，与 HKEX Fact Book 披露 `21,440,049.16` 一致至披露舍入精度；2020 年合计 `32,110,147.881754` HKD million，与披露 `32,110,147.90` 同样一致。

暂存文件（ignored）：

`data/competition/market_reference/normalized/hkex_total_market_daily_turnover_2019_2025.csv`

SHA-256：`056a18b2a640bf2e6572c39ef6436b3966fd263d5a08086d15695a8d91ece4c6`

这不是 `S_DQ_AMOUNT`、项目股票求和、HSI 成分股求和或任何其他 proxy。

## 5. Source acceptance audit

| Source | Owner | Dataset / Series | Frequency | Coverage | Access | Authority | PIT | Decision |
|---|---|---|---|---|---|---|---|---|
| HSCI methodology | Hang Seng Indexes | HSCI Series / HSICS mapping | methodology | Sep 2025 v2.5 | public PDF | PRIMARY_OFFICIAL | n/a | ACCEPT |
| HSI directory | Hang Seng Indexes | 12 HSCI price-index identities | metadata | current snapshot | public JSON | PRIMARY_OFFICIAL | yes | ACCEPT |
| 12 chart JSONs | Hang Seng Indexes | HSCIE…HSCIC | daily | 2021-08-19–2025-12-30 in target | public JSON | PRIMARY_OFFICIAL | yes | ACCEPT_PARTIAL_COVERAGE |
| Historical Data Product / Index360 | Hang Seng Indexes | older HSCI daily | daily | required old segment | account / paid | PRIMARY_OFFICIAL | potentially | MANUAL_REVIEW |
| HKEX Main Board archive | HKEX | Total trading value | daily | 2019–2025 used | public JSON | PRIMARY_OFFICIAL | yes | ACCEPT |
| HKEX GEM archive | HKEX | Total trading value | daily | 2019–2025 used | public JSON | PRIMARY_OFFICIAL | yes | ACCEPT |
| Investing.com pages | Investing.com | HSCI historical pages | daily | visually selectable | direct request 403; no accepted bulk method | SECONDARY_PUBLIC_SOURCE | unknown | REJECT |
| Existing HSC/HSF/HSP/HSU | CSMAR | other Hang Seng series | daily | local | licensed local | PRIMARY_VENDOR_EXPORT | yes | REJECT_AS_HSCI_PROXY |

字段化验收说明：

- HSCI chart：`SOURCE_NAME=HSI public chart JSON`；`DATASET_NAME=Hang Seng Composite Industry Indexes`；`SERIES_ID=00011.01...00011.14`；`FIELDS=trading_date, close`；`UNIT=index points`；`DOWNLOADABLE=YES`；`LICENSE/ACCESS_NOTE=publicly readable, copyright reserved, no open-data licence asserted; local research staging only`。
- HKEX Main Board/GEM archive：`SOURCE_NAME=HKEX Securities Statistics Archive`；`DATASET_NAME=Daily trading value, volume and number of deals`；`FIELDS=trading_date, total trading value, total trading volume, number of deals`；`UNIT=HKD / shares / count`；`DOWNLOADABLE=YES`；`LICENSE/ACCESS_NOTE=publicly readable official archive, no open-data licence asserted; local research staging only`。
- HSI Historical Data Product：`DOWNLOADABLE=NO without account/purchase`；`LICENSE/ACCESS_NOTE=paid official product`；`DECISION=MANUAL_REVIEW`。
- Investing.com：`AUTHORITATIVE_LEVEL=SECONDARY_PUBLIC_SOURCE`；`DOWNLOADABLE=NO by accepted direct method`；`DECISION=REJECT`。

完整下载文件 URL、时间戳、SHA-256、字节数和逐序列审计位于 ignored 本地文件：

`data/competition/market_reference/audit/v04_c_external_market_source_audit.json`

版本化摘要位于 `data/catalog/v04_c_external_market_source_manifest.json`。所有 raw/normalized 数据均由 `.gitignore` 排除。

## 6. PIT 与可用特征

本轮只完成 ingestion-ready staging，没有修改 frozen Core、PR-D dataset、训练、threshold 或标签。

后续行业与成交额特征必须在每个 IPO 快照中严格筛选：

`trading_date < listing_date`

不能使用上市日 close；不能因未来新增行改变历史快照。当前数据按原始交易日保存，未插值或填充，因此可用于后续 strict-before provider 和 future-row poisoning test。

正式解锁：

- 2019–2025 HKEX total-market turnover 的 20-session 均值，438/438 可用。

仍阻塞：

- production `industry_return_5d` / `industry_return_20d`：分类字段历史时点语义未证明；
- 2019-01-01 至 2021-08-18 的 HSCI 行业日收盘；
- 6 个无 HSICS 字段案例的行业特征；
- `SectorIndName` 到 HSICS 的任何映射（无权威证据）。

条件性研究覆盖（仅用于衡量历史回补价值，不是 production X）：静态 mapping 下 5D 为 243/438、20D 为 242/438；缺少旧历史影响 190 家，全部位于 2020–2021。2022–2024 的行业历史窗口已覆盖，只有 2022 年 1 家缺分类。

## 7. Reproduction

```powershell
python scripts/prepare_v04_c_external_market_sources.py
python scripts/run_v04_c_extended_readiness.py <local governed source arguments>
python -m pytest tests/unit/test_v04_c_external_market_sources.py tests/unit/test_v04_c_official_market_sources.py tests/unit/test_v04_c_extended_readiness.py -q
```

脚本会重新下载官方公开 JSON/PDF、校验 series ID、日期、重复值、非正 close、市场日历与排序，并重建 ignored normalized CSV 和完整审计 JSON。
