# V04 Data Readiness — Current Reference Snapshot

> Audit snapshot: **2026-08-23**  
> Status: **PR-A / PR-B / PR-C / PR-D / PR-E COMPLETE / FROZEN; Oracle v2 COMPLETE / FROZEN; PR-F CURRENT**

本文件只记录已经通过真实 materialization / audit 支持的数据事实。计划、分支或代码存在本身不能修改 measured readiness。

## 1. Official modeling universe

Official 2020–2024 listing-year universe：**438 cases**。

```text
2020  125
2021   97
2022   78
2023   68
2024   70
```

该 universe 以 authoritative official listing identity 为准，不使用旧 document corpus `source_year` 定义 modeling cohort。

## 2. Production Document readiness — COMPLETE / FROZEN

```text
Official cases                 438
Production analyses            438 / 438
Authoritative snapshots        438 / 438
Production Document-X          438 / 438
Feature schema                 v04_document_features_v1
Feature dimension              100
Production failures            0
Silent drops                   0
A6 determinism                 438 checked / 0 mismatch / PASS
2025 Blind access              NO
```

PR-A source revision：

```text
13e0281f5e65a970caaf1255e56d08597e1ead70
```

Production artifact-set frozen hash：

```text
9197b0f4f90e6d43277586ac40160679d40f91e3b30223578d0853d9dc288bf3
```

## 3. Governed IPO EOD foundation

PR-B governed EOD store：

```text
rows                           433,776
target securities matched      432 / 438
missing EOD                       6
raw EOD SHA256                  190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152
official bridge SHA256          751de6968ad8935ad45a8cd2841adbdc498d2bce6bb87153a1930959f4f85198
```

EOD/session-ready coverage 与 target coverage 不能混用。某 case 即使存在 EOD，也可能因为缺官方 base price 而无法产生 5D target。

## 4. Market-X Core — COMPLETE / FROZEN

Frozen contract：

```text
schema   v04_ipo_market_context_features_v1
policy   ipo_market_context_policy_v1
15 raw + 15 missing indicators = 30 positions
```

Measured result：

```text
Official coverage              438 / 438
Core materialized              438 / 438
Failures / silent drops        0 / 0
PIT failures                   0
Development / Validation       368 / 70
Determinism                    438 checked / 0 mismatch / PASS
2025 Blind y accessed          NO
```

Market-X Core 使用目标上市前已经可得的 prior-IPO context；目标 IPO 的上市后事实不能进入该目标的 X。

## 5. Market-X Extended — source gaps remain

以下 source family 仍无受治理正式输入：

```text
HSI daily history
industry → benchmark authoritative mapping
industry-index histories
HK total-market turnover
```

这些是 optional Extended limitations，不是 PR-B Core failure。

禁止：

- Hang Seng Bank 代替 HSI；
- workbook industry name 直接冒充 authoritative benchmark mapping；
- 单证券 `S_DQ_AMOUNT` 冒充 HK total-market turnover；
- fake benchmark row；
- missing source 填 neutral zero。

## 6. PR-C 5D Outcome — COMPLETE / FROZEN

```text
Official coverage              438
Outcome available              424
Outcome unavailable             14
Development available          354 / 368
Validation available            70 / 70
missing_base_price              12
no_eligible_session              2
Development q25 threshold      -0.1000
Determinism                    438 checked / 0 mismatch / PASS
2025 Blind y accessed          NO
```

PR-C classification threshold 只使用 Development 拟合；Validation / Blind 不参与阈值定义。

Frozen hashes：

```text
policy       5f793de0df22679430bb0a7565ed2d9eabfe63f0153725babc7ebd121d369c67
threshold    5aac9625209e65ccd7337d713e714ae1e9bd7e2d8f24db510e46131608a6ec05
target set   5e0dedc8d207c8e73ca6439efb72f463c6b6f276c1c6c48e3ad7a989ad1533f4
```

## 7. PR-D Canonical Model-ready Dataset — COMPLETE / FROZEN

```text
Upstream official cases        438
Model-ready                     424
Explicit exclusions              14
Development                     354
Validation                       70
Schema                         v04_canonical_modeling_dataset_v1
Generation failures              0
Silent drops                     0
Identity mismatch                0
Feature-order drift              0
Same-provenance resume          PASS
2025 Blind y accessed           NO
```

PR-D binding independently verifies PR-A Production, PR-B Market Core and PR-C Outcome bulk contents before accepting canonical materialization。

Frozen anchors：

```text
PR-D freeze manifest hash
f6900c707187c23c5d01fa98fc8d9d21d040ce2c3ffa0a2a6340a0947f78e80d

input binding manifest hash
fca62fe4598f1f39adb9450c9b3e1bcecf45b0a968bc07cb46eaac3d8db1ab56
```

Full Production matrices exist for：

```text
M / P / PM
Development 354
Validation   70
```

## 8. Oracle readiness

### Oracle v1 — historical immutable snapshot

```text
materialized        60
current eligible    55
Development         55
Validation           0
```

Oracle v1 只保留历史冻结意义，不再作为 formal PR-E 当前 ceiling。

### Oracle v2 — COMPLETE / FROZEN

```text
annotation inventory       101
valid annotations          100
materialized                98
strict usable               96
Development usable          77
Validation usable           19
identity unresolved          0
feature count              142
evaluation_only            true
production_consumable      false
2025 Blind y accessed      false
```

Frozen hashes：

```text
artifact set
 e73dd7f478fd4c421f6794cfa0c7808403cfb5d57dd0678eae1146aaeeff09d6
strict usable set
 486a0c7d3977deacb5e3247e184064e96a684dbfdf8ef951b9df6cd32ce4da0f
feature manifest
 99eeb0366a50b11b94f6e92820b6f1ef8535d5979ca6266d2af4f78618b40c11
freeze manifest
 ddb175f48b7e8134c90c674e44d6173337dc2ea10e9eece103f70ae902e80294
```

Oracle v2 保持 evaluation-only，不进入 Production X。

## 9. Frozen PR-E execution

Formal PR-E 已使用以下冻结数据完成执行：

```text
Full Production:
354 Dev / 70 Val
M / P / PM

Oracle v2 fair intersection:
77 Dev / 19 Val
M / P / O / PM / OM
```

PR-E 已完成以下治理要求：

- 验证 frozen PR-D / Oracle v2 input binding；
- 使用 expanding-year Development forward chaining；
- 2024 Validation 不参与拟合；
- 报告 M/P/PM 与 M/P/O/PM/OM；
- 报告 PM-M / OM-M / OM-PM；
- 不把小样本 non-significance 解释成“无信号”；
- 2025 Blind y accessed = false。

## 10. Current source status table

| Source / artifact | Status | Use |
| --- | --- | --- |
| Official IPO identity | AVAILABLE 438/438 | identity / split |
| Prospectus | AVAILABLE 438/438 | Production Document |
| Production Document-X | FROZEN 438/438 | P / PM |
| Governed IPO EOD | 432/438 securities | Core / outcomes |
| Market-X Core | FROZEN 438/438 | M / PM |
| 5D Outcome | FROZEN 424/438 | y |
| Canonical Dataset | FROZEN 424 | model-ready |
| Oracle v1 | HISTORICAL | historical reference only |
| Oracle v2 | FROZEN 98 / 96 strict | O / OM research ceiling |
| HSI | MISSING | optional Extended |
| Industry benchmark | MISSING | optional Extended |
| HK total-market turnover | MISSING | optional Extended |

## 11. Gate state

```text
PR-A_DOCUMENT_GATE        PASS / FROZEN
PR-B_MARKET_CORE_GATE     PASS / FROZEN
PR-C_OUTCOME_GATE         PASS / FROZEN
PR-D_MODEL_READY_GATE     PASS / FROZEN
ORACLE_V2_GATE            PASS / FROZEN
PR-E_BASELINE_GATE        PASS / FROZEN
PR-F_LIGHTGBM_GATE        CURRENT / NOT FROZEN
2025_BLIND_Y              NOT ACCESSED
```
