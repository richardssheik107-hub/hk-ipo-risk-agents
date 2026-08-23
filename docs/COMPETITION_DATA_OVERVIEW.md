# 赛事数据概览

> Audit snapshot: **2026-08-23**  
> Purpose: 描述原始赛事数据宇宙与来源治理；当前建模 readiness 以 `research/V04_DATA_READINESS.md` 为准。

## 1. Raw competition data universe

| 数据 | 规模 | 说明 |
| --- | ---: | --- |
| 招股书 | 565 份 | PDF corpus |
| 公司资料 | 4501 行 / 25 列 | GB18030 CSV |
| 证券资料 | 803 行 / 30 列 | 已隔离，不作为 v0.4 eligibility gate |
| 日行情 | 4,117,539 行 / 22 列 | GB18030 CSV |
| 行情代码 | 3756 | `S_INFO_WINDCODE` |

历史 document corpus 年度分布不等于 v0.4 modeling split。`source_year` 只描述文档来源目录，不是 authoritative listing year。

## 2. Historical document corpus

```text
2020  138
2021   88
2022   87
2023   63
2024   73
2025  116
```

历史 v0.2/v0.3 的 2410.HK development exception 只用于旧文档链路回归，不进入 v0.4 market/model split policy。

## 3. v0.4 official modeling cohort

v0.4 使用 authoritative official listing identity / listing date：

```text
2020–2023 official listing year  → Development / Training
2024 official listing year       → Validation
2025 official listing year       → Blind Test
```

2020–2024 official modeling universe：**438 cases**。

年度：

```text
2020  125
2021   97
2022   78
2023   68
2024   70
```

因此旧 565-document corpus 数量不能直接推导 438-case modeling cohort，也不能用 `source_year` 代替 `official_listed_date.year`。

## 4. Official metadata bridge

`HK_Official_Merged_565_First_with_IPO.xlsx` 是只读 authoritative supplemental source；受控 bridge：

```text
data/catalog/ipo_official_master_bridge.csv
```

它提供 / 连接：

```text
case identity
stock code
listing date
issue price
board / listing method
industry metadata
source provenance
```

`disclosure_date` 不是 listing date。隔离的 Security Master / description 不能用来猜测缺失 listing date、issue price 或 eligibility。

## 5. EOD coverage vs outcome coverage

这是最容易混淆的两个口径：

```text
Governed EOD securities matched     432 / 438
5D outcome available                424 / 438
5D outcome unavailable               14
```

6 个 EOD-unmatched case 不等于只有 6 个 outcome-unavailable case。5D target 还要求 authoritative base price；最终 PR-C unavailable 为：

```text
missing_base_price      12
no_eligible_session      2
```

所以所有后续 modeling / coverage 文档必须使用 PR-C frozen 424/14 target contract，而不是 PR-B 432/6 EOD coverage。

## 6. Current frozen data chain

```text
Prospectus / official identity
→ PR-A Production Document-X       438 / 438

Governed metadata / IPO EOD
→ PR-B Market-X Core               438 / 438

Official issue price + sessions
→ PR-C 5D Outcome                  424 / 438

Document + Market + Outcome
→ PR-D Canonical Dataset           424 = 354 Dev + 70 Val
```

Oracle v2 是独立 evaluation-only research sidecar：

```text
98 materialized
96 strict usable
77 Dev / 19 Val
```

## 7. Source governance rules

- official universe membership 决定 v0.4 eligibility；
- `official_listed_date.year` 决定 modeling cohort；
- target IPO 上市后数据不能进入该 IPO 的 X；
- prior IPO outcomes 只有在对应 target session 已发生且早于目标 listing 时才能进入 prior-IPO context；
- missing HSI / industry benchmark / total-market turnover 不允许用 fake proxy 或 neutral zero 填补；
- 2025 Blind y 在正式开放前禁止访问。

## 8. Source-of-truth order

数据口径冲突时：

1. frozen manifests / validators；
2. completion reports；
3. `research/V04_DATA_READINESS.md`；
4. `research/V04_MARKET_FOUNDATION.md`；
5. 本文件提供原始 corpus 背景。

本文件不决定“当前下一 Gate”；当前进度见 `ROADMAP.md`。
