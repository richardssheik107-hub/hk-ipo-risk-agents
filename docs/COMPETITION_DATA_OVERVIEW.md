# 赛事数据概览

> Audit snapshot: **2026-08-25**  
> Purpose: 描述原始赛事数据宇宙、当前 frozen baseline 与 Competition Final Sprint 的数据交付要求。  
> Measured readiness 以 [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) 为准。

## 1. Raw competition data universe

| 数据 | 规模 | 说明 |
| --- | ---: | --- |
| 招股书 | 565 份 | historical PDF corpus |
| 公司资料 | 4501 行 / 25 列 | supplemental company data |
| 证券资料 | 803 行 / 30 列 | supplemental security data |
| 日行情 | 4,117,539 行 / 22 列 | governed EOD source |
| 行情代码 | 3756 | `S_INFO_WINDCODE` |

Historical document `source_year` 不是 modeling split authority。

## 2. Official cohort / split

```text
2020–2023 official listing year → Development / Training
2024 official listing year      → Validation
2025 official listing year      → Blind Test
```

Official 2020–2024 universe: **438 cases**。

```text
2020  125
2021   97
2022   78
2023   68
2024   70
```

## 3. Frozen baseline coverage

```text
Production Document-X        438 / 438
Market-X Core                438 / 438
Governed EOD match            432 / 438 securities
5D Outcome                    424 / 438
Canonical model-ready         424 = 354 Dev + 70 Val
```

Frozen PR-A–PR-D artifacts 在 Final Sprint 中不原地重写。

## 4. Market readiness

### Available governed inputs

```text
HSI return / volatility readiness       438 / 438
HKEX Main Board + GEM turnover 20D      438 / 438
recent_ipo_1d_sample_count              438 / 438
recent_ipo_5d_sample_count              438 / 438
recent_ipo_break_rate                   244 / 438 available
recent_ipo_return_5d                    243 / 438 available
```

### Industry limitation

```text
production industry_return_5d             0 / 438
production industry_return_20d            0 / 438
```

原因仍为缺少 historical effective/listing-time company classification。禁止静态 current classification、proxy 或 neutral zero 冒充 PIT-safe feature。

## 5. Competition Market data priority

C 的 Final Sprint 只优先使用已经可治理、能直接支撑赛题的市场信息：

```text
HSI trend / volatility
HKEX turnover / activity
recent IPO count
recent IPO break rate
recent IPO 1D / 5D performance
IPO Heat
Market Regime
optional PIT-safe comparable context
```

每个 feature 必须记录：

```text
value
availability / missing_reason
as_of / cutoff
source / provenance
policy / feature version
```

## 6. Competition outcome requirement

赛题要求结合：

```text
上市首日
上市后 5 个交易日
上市后 20 个交易日
上市后 60 个交易日
```

因此 D 必须建立独立 versioned sidecar：

```text
return_1d
return_5d
return_20d
return_60d
```

建议同时：

```text
break_flag_1d
significant_drop_5d
max_drawdown_20d
max_drawdown_60d
```

Frozen PR-C 5D 保持历史不变；新 sidecar 只作为 Competition validation layer。

## 7. Document / LLM data boundary

LLM 只能读取已经进入其任务 scope 的 Evidence，不直接消费 Gold answer/page 或未来标签。

Production：

```text
real Prospectus
→ Parser / Retriever
→ Evidence
→ LLM semantic extraction
→ Risk / Verifier
```

Oracle：

```text
Reviewed Expert Gold
→ evaluation-only Oracle-X
```

Oracle 不能进入 Production runtime。

## 8. Final submission data artifacts

D/A 最终统一生成：

```text
evaluation/test_predictions.csv
evaluation/multi_horizon_results.csv
evaluation/risk_benchmark.*
evaluation/evidence_benchmark.*
evaluation/ai_vs_offline_report.*
traces/agent_reasoning_logs/
evidence/
reports/
```

`test_predictions.csv` 至少包含：

```text
case_id
stock_code
risk_score
risk_level
model_status
return_1d
return_5d
return_20d
return_60d
```

## 9. Source governance

- official membership controls eligibility；
- official listing year controls split；
- target IPO post-listing data cannot enter that IPO's X；
- prior IPO outcome may enter Market context only after it was observable before target cutoff；
- missing remains missing；
- 2025 Blind y remains closed until formally authorized。

## 10. Final data ownership

```text
A  identity / contracts / submission data packaging
B  Document Evidence / benchmark labels/results
C  MarketContext / PIT provenance
D  outcomes / ModelSignal / prediction/evaluation tables
E  trace / human-review / case product consumption
```
