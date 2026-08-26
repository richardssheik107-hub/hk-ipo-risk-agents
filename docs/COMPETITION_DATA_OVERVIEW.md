# Competition Data Overview

本文件记录比赛数据范围、split、Existing-Gold/Validation/Blind 边界、主要 materialization 状态与数据治理规则。当前 Gate 见 `V0.4_RELEASE_ACCEPTANCE.md`；指标口径见 `COMPETITION_METRIC_PROTOCOL.md`。

## 1. Official universe

正式 2020–2024 IPO universe：

```text
438 cases
```

chronological split：

```text
2020–2023  Development
2024       Validation
2025       Blind（feature-only / outcome 未授权前不可访问）
```

## 2. Metric-v2 Existing-Gold data governance

Protocol：

```text
v045_competition_metric_protocol_v2_existing_gold_only
```

M1/M2 唯一人工标准答案来源是比赛收尾前已经存在并冻结的 Expert Annotation / Oracle Gold：

```text
annotation inventory   101
valid annotations      100
official materialized   98
```

规则：

- 不新增人工 Gold；
- 不修改 Existing Gold；
- 不补低 support risk family；
- 不新增 negative annotation；
- 不人工重做 Evidence Group；
- Existing Gold 未明确判断的 risk unit = `UNJUDGED`，不当 negative；
- Development 可看错误并做代码/Prompt/LLM targeted remediation；
- Validation 只做冻结后的 one-shot confirmation；
- 2025 Blind y 未授权前不得访问。

`98 official materialized` 不等于 98 家 × 所有风险都有 Gold。M1/M2 evaluator 必须先只读扫描 Existing Gold，生成实际 evaluable support。

### Benchmark scope

正式 Development benchmark：

```text
ALL evaluable existing 2020–2023 Expert Gold
```

可为迭代速度从中固定小 debug subset，但不创建新的 20-case annotation target。

Validation：

```text
ALL evaluable existing 2024 Expert Gold
```

冻结代码 / Prompt / evaluator / source manifest 后一次性评价。

## 3. Document data

Production Document-X：

```text
438 / 438
100 positions
```

比赛真实案例当前已验证：

```text
ipo_2024_02410 / 2410.HK / 706 pages
ipo_2024_02460 / 2460.HK / 579 pages
ipo_2024_01318 / 1318.HK / 617 pages
```

三份均通过 frozen catalog 的 filename / SHA-256 / byte size / physical-page verification，并完成 offline competition E2E。

Role B 旧 10-case Development benchmark input validation：

```text
10/10 found
10/10 SHA
10/10 page
10/10 analyzed
```

这证明输入治理与 parser/runtime 能运行，不证明 M1/M2 达标。

## 4. Existing-Gold Risk Unit data

M1 evaluator 只能从旧 annotation 中确定性抽取 Existing-Gold Risk Unit：

```text
case_id
source_annotation_id / hash
risk_family
existing_gold_status
existing_required_attributes
existing_evidence_refs
split
evaluable
```

Primary：

```text
Existing-Gold Official-aligned Accuracy
= correct evaluable positive Existing-Gold Risk Units
  / all evaluable positive Existing-Gold Risk Units
```

`UNJUDGED` 不进入分母。

Competition-priority mapping 仍包括：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

但只有 Existing Gold 有 support 时评价；`support=0` 时报告 `NOT_EVALUABLE_FROM_EXISTING_GOLD`，不补标。

## 5. Existing-Gold Evidence data

M2 只使用旧 annotation 已经存在的 Evidence/page/span/table/anchor。

允许：

- deterministic schema normalization；
- identity/page standardization；
- exact duplicate anchor dedupe；
- 旧 Gold 本身已有的 grouping/equivalence。

禁止：

- 新增人工 Evidence；
- 人工重新定义 semantic Evidence Group；
- 为系统漏掉的证据补替代页。

Primary：

```text
Existing-Gold Evidence Coverage Recall
= covered evaluable existing Evidence Units
  / all evaluable existing Evidence Units
```

Recall@1/@3/@5/@10/@20 只作为 retrieval/ranking diagnostics。旧 10-case offline `Recall@5=20%` 保留原始事实，但不等于官方 M2 当前值。

## 6. Market-X

Frozen PR-B Core：

```text
438 / 438
30 positions = 15 raw + 15 missing indicators
PIT governed
```

Extended readiness：

```text
HSI features                438 / 438
HKEX turnover 20D           438 / 438
production industry return    0 / 438
```

industry return 缺失原因是没有历史时点有效的 authoritative company→industry mapping。禁止未来 classification、静态映射或 zero-fill 伪装 PIT。

## 7. Outcome data / M5

Frozen PR-C 5D governed outcome：

```text
official cases          438
available               424
unavailable              14
Development available   354
Validation available     70
```

已有 foundation 定义 1D / 5D / 20D / 60D 语义，但 final competition materialization 仍由 D 收口。

项目预先定义：

```text
significant_drop_5d = (return_5d <= -0.10)
```

D 不允许根据 2024 Validation 结果重新选 threshold、score inversion 或重训 frozen PR-F。

## 8. Oracle / modeling data

Frozen canonical dataset：

```text
424 model-ready
354 Development
70 Validation
```

Oracle v2 evaluation-only：

```text
98 materialized
96 strict usable
77 Development
19 Validation
142 features
```

注意：96/77/19 是原 Oracle/model evaluation 的 strict usable 口径；M1/M2 Document benchmark 不机械套用 outcome eligibility，而是从 98 official materialized Existing Gold 中只读判断实际可评价 Document units。

Oracle 仅用于 evaluation/diagnosis，不进入 production runtime。

## 9. Model artifacts

Frozen PR-E/PR-F 研究结果保持历史事实。Competition runtime 只有在 authentic frozen PR-F per-case runtime 或 hash-bound sanitized handoff 可用时展示 model score/driver；否则 Model Channel = unavailable，不重训替代。

## 10. 2024 Validation

可以用于：

- fixed workflow smoke；
- Evidence/Trace/Product validation；
- 不读取 outcome 的文档/市场/Agent 链路验证；
- Existing-Gold Development 闭合后的一次性 frozen evaluator confirmation。

不得用于：

- 看完结果后调 Prompt / Retriever / Verifier；
- 根据 2024 选择 Evidence K；
- 根据 2024 改 M1/M2 公式；
- 根据 2024 改 5D threshold；
- score inversion / model retraining。

## 11. 2025 Blind

- 可以准备 feature-only inputs；
- 未授权前不得读 outcome/target；
- schema/builder/validator 应 fail closed；
- formal artifact 保留 `blind_2025_accessed=false` 或等价声明。

## 12. Data → role ownership

- Existing Expert Gold：冻结只读，任何 lane 不得修改；
- A：Existing-Gold coverage audit / evaluator governance / source manifest / final audit；
- B：Prospectus / real-LLM Document optimization / M1/M2 benchmark；
- C：PIT market features / MarketContext；
- D：Outcome / model / evaluation；
- E：final case analysis/trace/review。

## 13. Current data-related blockers

1. Existing-Gold read-only evaluable manifest；
2. B real-LLM Development predictions + M1/M2 results；
3. D final 1D/5D/20D/60D result package；
4. final matrix Market Core validation；
5. real-provider Final Supervisor final matrix trace；
6. optional Evidence bbox。

明确不把新的 M1/M2 annotation、Gold 扩样、broad industry research 或 full new data acquisition 列为 blocker。
