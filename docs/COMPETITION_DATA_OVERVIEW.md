# 赛事数据概览

> Status snapshot: **2026-08-20**  
> 本文件描述**原始赛事数据宇宙与来源治理**。v0.4 市场建模的 official 438-case cohort / split 以 `research/V04_DATA_READINESS.md` 和 Market Foundation 为准，不能把旧文档语料切分直接当成 v0.4 modeling split。

## 1. 数据规模

| 数据 | 规模 | 编码/形式 |
|---|---:|---|
| 招股书 | 565份 | 按年份目录存放的 PDF |
| 公司资料 | 4501行，25列 | GB18030 CSV |
| 证券资料 | 803行，30列 | GB18030 CSV；隔离使用 |
| 日行情 | 4117539行，22列 | GB18030 CSV |
| 行情代码 | 3756个 | `S_INFO_WINDCODE` |

## 2. 招股书语料年度分布

| 年份 | 数量 | 语料用途 |
|---:|---:|---|
| 2020 | 138 | 历史开发语料 |
| 2021 | 88 | 历史开发语料 |
| 2022 | 87 | 历史开发语料 |
| 2023 | 63 | 历史开发语料 |
| 2024 | 73 | 历史验证语料 |
| 2025 | 116 | 受保护盲测语料 |

历史文档语料切分为：

- 2020–2023：376份；
- 2024：72份；
- 历史 v0.2 开发例外：2410.HK 1份；
- 2025：116份 blind corpus。

**重要：2410.HK 的 v0.2 development exception 只属于旧文档链路回归历史，不进入 v0.4 市场建模 split policy。**

## 3. v0.4 Modeling Cohort 与旧语料切分的区别

v0.4 不直接用 `source_year` 决定 market modeling cohort，而是使用 authoritative official listing date / official IPO universe。

当前 frozen v0.4 split：

```text
2020–2023 official listing year  -> Development / Training
2024 official listing year       -> Validation
2025 official listing year       -> Blind Test
```

当前 2020–2024 official modeling universe 为 **438 cases**。它不是“565 份招股书减去若干文件”的简单子集，而是经过 official IPO metadata / listing-year governance 后形成的建模 cohort。

因此：

- `source_year` 只描述招股书来源年份；
- `official_listed_date.year` 才是 v0.4 modeling cohort 的权威年度依据；
- 旧 376 / 72 / 1 exception 数字不能用于推导 v0.4 Development / Validation 样本数；
- 2025 blind policy 继续严格保护，不允许用 outcome 调参。

## 4. 原始覆盖与可用性

在完整 565-document corpus 层：

- 有日行情覆盖：555 / 565；
- 无日行情覆盖：10，仅用于文档链路和降级测试；
- 抽样可识别文本的 PDF：565 / 565；
- 早期 B1 的 `parser_status=not_run` 只表示当时尚未批量运行 production Parser，不代表当前 Parser 不可用。

在 v0.4 official 438-case modeling universe 层，当前 governed IPO OHLCV coverage 为 **432 / 438**；6 个 eligible case outcome unavailable。最新口径见 `research/V04_DATA_READINESS.md`。

## 5. 关联规则

- 招股书股票代码来自受控文件名，原始五位代码保存在 `stock_code_raw`；
- 只有通过五位数字校验后才生成 `stock_code_wind`，匹配失败不会伪装为成功；
- `disclosure_date` 来自招股书文件名，不得当作上市日期；
- 证券资料文件疑似截断并已隔离，不允许用它猜测 2020–2024 的上市日期、发行价或 security type；
- v0.4 eligibility 由 authoritative official IPO universe membership 决定，而不是由隔离 Security Master 是否匹配决定。

## 6. IPO 官方主数据桥接

- `HK_Official_Merged_565_First_with_IPO.xlsx` 作为只读原始输入；
- 桥接目录：`data/catalog/ipo_official_master_bridge.csv`；
- 招股书案例与官方主数据：562 / 565 `matched`，另有 3 个 `manifest_only_placeholder`，不得补猜公司、上市日期或发行信息；
- `official_listed_date` 是来源工作簿提供的上市日期；必须结合 `first_eod_trade_date` 与 `listed_date_eod_relation` 使用；
- 有 2 个已匹配案例的日行情早于工作簿上市日期，进入建模标签或时间窗前必须遵守现有治理检查，不可静默改日期。

## 7. 当前 source of truth

数据语义发生冲突时按以下顺序：

1. `END_TO_END_CLOSED_LOOP_MASTER_PLAN.md` — 当前执行与 Gate；
2. `research/V04_DATA_READINESS.md` — 最近一次真实 readiness / coverage 审计；
3. `research/V04_MARKET_FOUNDATION.md` — v0.4 market cohort、label、blind 契约；
4. 本文件 — 原始赛事数据宇宙与历史语料背景。

本文件不再承担“当前下一步计划”或“模型是否 ready”的判断职责。
