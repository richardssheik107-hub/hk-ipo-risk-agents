# V04 PR-D — Canonical Model-ready Dataset Contract

> Status: **COMPLETE / FROZEN**  
> Owner: **D — Quant / ML Research**  
> Review: **A — identity / provenance / reproducibility / Blind Gate**

Formal freeze evidence：

- `docs/V04_PR_D_COMPLETION_REPORT.md`
- `reports/frozen/v04_pr_d_canonical_dataset_manifest.json`
- `reports/frozen/v04_pr_d_input_binding_manifest.json`

## 1. Purpose

PR-D 把已经冻结的 Production Document X、Market-X Core 和 5D Outcome Y 连接成正式 canonical modeling dataset，不修改历史 document-only dataset，也不把 optional Extended feature 静默插入 frozen Core order。

版本：

```text
dataset  v04_canonical_modeling_dataset_v1
matrix   v04_canonical_model_matrix_v1
```

## 2. Frozen result

```text
Official upstream cases       438
Model-ready                   424
Explicit target exclusions     14
Development                   354
Validation                     70
Generation failures             0
Silent drops                    0
Identity mismatch               0
Feature-order drift             0
Same-provenance resume         PASS
2025 Blind y accessed          NO
```

Exclusions：

```text
missing_base_price      12
no_eligible_session      2
```

Unavailable outcomes 始终保留 explicit exclusion record，不 zero-impute、不 silent drop。

## 3. Required input blocks

```text
Market Core          30 positions / required
Market Extended      optional / separately versioned
Production Document 100 positions / required
Oracle Document     evaluation-only / Oracle fair intersection only
```

PR-D 输入必须绑定：

```text
PR-A frozen Production Document-X
PR-B frozen Market-X Core
PR-C frozen FiveDayOutcomeTarget
corresponding frozen manifests / content hashes
```

任何 identity mismatch、manifest drift、artifact tampering、duplicate/orphan、unavailable target、Blind row 均 fail closed。

## 4. Full Production cohort

正式 full-production matrices：

```text
M   Market Core
P   Production Document
PM  Market + Production
```

Development / Validation 分开 materialize：

```text
354 / 70
```

## 5. Oracle role

PR-D 当时保留历史 Oracle v1 snapshot，不把它当 current formal ceiling。Oracle v2 已在 PR-D 之后独立刷新并冻结：

```text
98 materialized
96 strict usable
77 Development
19 Validation
```

formal PR-E 使用单独的 Oracle-v2 matrix builder，把 frozen PR-D Production matrices 与 frozen Oracle v2 features 对齐成公平的：

```text
M / P / O / PM / OM
× Development / Validation
```

Oracle 始终 `evaluation_only=true`，不进入 Production matrices。

## 6. Feature safety

所有 feature name 都必须 component-prefixed。以下内容只能做 provenance，不能进入 X：

```text
case_id
stock_code
document_id
Evidence ID
Gold page / Gold Evidence ID
target-derived identifiers
outcome identifiers
```

Missing value 使用显式 semantics / indicators；不得把 missing 解释为 safe zero。

## 7. Time governance

```text
2020–2023  Development
2024       Validation
2025       Blind Test
```

PR-D CLI 不接受 2025 outcome。Development 与 Validation 独立 materialize；target policy / threshold hash 必须一致并来自 frozen PR-C。

## 8. Frozen provenance anchors

```text
Production artifact-set hash
9197b0f4f90e6d43277586ac40160679d40f91e3b30223578d0853d9dc288bf3

Market artifact-set hash
6803424877560945de61a6647863365c4e91b786bc9f12f1451da4a25c3b2eb6

Outcome artifact-set hash
1f0ab1f8314a322abcaf4c88feead02e6cd114b478234b36388c27e33dc7ad90

PR-D input binding manifest hash
fca62fe4598f1f39adb9450c9b3e1bcecf45b0a968bc07cb46eaac3d8db1ab56

PR-D freeze manifest hash
f6900c707187c23c5d01fa98fc8d9d21d040ce2c3ffa0a2a6340a0947f78e80d
```

## 9. Canonical implementation

```text
src/ipo_risk/schemas/canonical_modeling.py
src/ipo_risk/modeling/canonical_dataset.py
src/ipo_risk/modeling/pr_d_input_binding.py
scripts/run_v04_pr_d.py
```

PR-D 已完成，不应再被描述为 preparation / formal materialization next。后续模型必须消费 frozen outputs，而不是自行重新 join PR-A/B/C。
