# Competition Data Overview

> 状态日期：`2026-08-28`

## 1. 数据宇宙与 split

```text
2020–2023  Development
2024       Validation
2025       Blind
```

正式 2020–2024 IPO universe：438 cases。

未来开发纪律：

- 仅 Development 用于定位错误、选择规则、Prompt、Retriever、模型与阈值；
- Validation 在系统冻结后 one-shot；
- 2025 Blind 输入与 outcome 不再用于缺陷定位或参数选择；
- 正式 Blind 推理只在冻结和授权后运行。

历史 `CHANGELOG.md` 保留了一次使用 2025 Blind 文档定位解析缺陷的记录。该记录不表示 outcome/y 被访问，但意味着不能再宣称 Blind 输入从未被观察。最终治理报告应如实披露；从本规则生效起停止任何 Blind-input optimization。

## 2. Existing Gold

```text
annotation inventory = 101
valid = 100
official materialized = 98
evaluable Development = 79
evaluable Validation = 19
primary positive Risk Units = 128
primary Evidence Units = 217
```

规则：

- 不新增或修改人工 Gold；
- 不补 negative；
- 不人工重组 Evidence Group；
- `UNJUDGED` 不当 negative；
- Gold 不进入 runtime；
- support=0 报 `NOT_EVALUABLE_FROM_EXISTING_GOLD`。

## 3. Document data

- 438/438 招股书治理目录；
- final-three：2410.HK 706 页、2460.HK 579 页、1318.HK 617 页；
- 三份均有 filename、SHA-256、size、physical page verification；
- fixed-10 是从 Existing-Gold Development 冻结选择的诊断子集。

输入完整不等于 M1/M2 达标。

## 4. Risk / Evidence evaluation

M1：正确 positive Existing-Gold Risk Units / 全部可评价 positive units。

M2：最终覆盖 Existing-Gold Evidence Units / 全部可评价 Evidence units。

Recall@K 是 retrieval/ranking 诊断。M2 还受风险生成、Verifier、Evidence retention、page 和 anchor matching 影响。

## 5. Market data

Market-X Core 438/438，PIT governed。Extended HSI 与 turnover 已有覆盖；production industry return 缺少历史时点有效 company→industry mapping 时保持 unavailable。

禁止未来 classification、zero fill 或未经证明的 proxy。

## 6. Outcome / M5

```text
model-ready = 424
Development = 354
Validation = 70
```

已有 1D / 5D / 20D / 60D 正式物化和 hash-bound receipt。完整 frozen runtime 与授权 EOD 不进入 Git，发布前需 live strict revalidation。

当前 5D 结果业务效果弱，不能仅凭 artifact PASS 宣称预警有效。

## 7. Oracle / model data

Oracle 仅用于 evaluation/diagnosis，不进入 production runtime。Authentic frozen PR-F handoff 不可用时 Model Channel = unavailable，不训练替代品冒充正式模型。

## 8. Final-three data

三个案例用于：

- offline E2E；
- real-provider Final Supervisor；
- Market strict validation；
- Trace / M4；
- Evidence screenshots；
- D→E label-free model handoff；
- 典型案例报告。

不得把真实上市后 outcome 反馈给同一次分析链。

## 9. Role ownership

- A：data/metric governance、final audit；
- B：Prospectus / Existing-Gold M1/M2；
- C：PIT market；
- D：Outcome / business value；
- E：final case / trace / review / product。

## 10. 当前数据相关缺口

1. v0.4.6 B full forensic run；
2. ALL 79 Development results；
3. D current-main strict revalidation；
4. C final-three strict metadata；
5. Evidence bbox / screenshot manifest；
6. one-shot Validation 与 final submission artifacts。
