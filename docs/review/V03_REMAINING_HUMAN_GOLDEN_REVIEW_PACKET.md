# v0.3 剩余人工 Golden 复核入口

> **SUPERSEDED / HISTORICAL MATERIAL**
>
> Independent second review is no longer a required Gate or formal-Golden
> condition. The permanent policy is `single_named_human_review_v1`; see
> `docs/V03_ANNOTATION_GUIDE.md` and `docs/V03_GATE_A_CLOSEOUT.md`. This file
> is retained only as historical audit material and must not be treated as an
> active blocker or required workflow.

状态核验基线：`main@885afe7b6584886433f5ed584aa85f2a805f270e`。

本文件只管理当前仍未关闭的人工 Golden 门槛。Legal A—H 已完成真实人工 primary、独立 second review、必要仲裁及 canonical promotion；其正式结果见 [V03_LEGAL_FORMAL_REVIEW_AUDIT.md](V03_LEGAL_FORMAL_REVIEW_AUDIT.md)，不再列入待复核范围。

## 当前剩余门槛

```text
GATE_A_03 = FAIL
GATE_A_04 = FAIL
formal_financial_second_review_complete = false
formal_business_second_review_complete = false
GATE_A_OVERALL_STATUS = BLOCKED
V3_8_START_STATUS = BLOCKED
```

| Gate | 范围 | 当前事实 | 独立性要求 |
| --- | --- | --- | --- |
| A03 | Financial | 23条真实draft；primary=`member-3`；`second_reviewer`为空 | second reviewer必须是真实人工且不同于`member-3` |
| A04 | Business | 3条真实draft；primary=`member-5`；`second_reviewer`为空 | second reviewer必须是真实人工且不同于`member-5` |

仓库当前没有指派具体second reviewer。不得自行填入`member-1`、`member-2`或任何其他身份，也不得将Codex/AI记录为reviewer或adjudicator。

## 盲审材料

- 人工说明与证据定位：[V03_A03_A04_HUMAN_SECOND_REVIEW_PACKET.md](V03_A03_A04_HUMAN_SECOND_REVIEW_PACKET.md)
- Financial空白录入模板：[templates/v03_financial_second_review.csv](templates/v03_financial_second_review.csv)
- Business空白录入模板：[templates/v03_business_second_review.csv](templates/v03_business_second_review.csv)

这些材料只包含定位字段，不包含primary的`applicable`、`exact_text`、`expected_status`、`expected_level`、原因、备注或结论。

## 强制流程

1. 独立复核人收到盲审包并自行打开原始招股书PDF。
2. 独立完成证据、适用性、状态和等级判断，填写对应CSV模板。
3. 只有在独立判断完成后，才与primary结果做机械比较。
4. 一致时，经数据治理校验后标记`double_reviewed`。
5. 不一致时保留双方意见，交给真实第三人仲裁。
6. 仲裁完成后才标记`adjudicated`。

Codex/AI可以执行机械比较、格式校验和完整性检查，但不得代替人工二审，也不得决定分歧。

## 数据保护

- 本准备阶段不修改canonical Golden判断字段。
- 不填充`second_reviewer`或`review_status`。
- 不访问、不检索、不解析、不评测2025 blind数据。
- A03/A04完成且通过合并后，才可重新审计Gate A；当前不得启动V3-8。
