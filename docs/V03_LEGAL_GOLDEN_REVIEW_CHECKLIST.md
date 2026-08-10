# v0.3 Legal Draft Golden Review Checklist

适用文件：`tests/fixtures/v03_golden_cases/v03_legal_golden_case_manifest.csv`

状态：8个案例均为`preselection / draft`，全部来自development，不含2025 blind-test。不得用于正式precision/recall，不得自动填写`second_reviewer`，不得自动改为`double_reviewed`或`adjudicated`。

## 人工第二复核步骤

- 独立打开CSV所列PDF物理页，并检查必要相邻页；
- 核对`document_id`、股票代码、物理页码和`exact_text`；
- 权利案例检查holder、完整termination、waiver、restoration及上市时点；
- 诉讼案例检查actual/negative/template、重大性、pending/resolved/settled/remediated；
- 独立填写适用性、expected status和理由后再与draft比对；
- 分歧由人工仲裁，保留仲裁说明和复核人身份；
- 正式并表由成员2维护，不由本分支改canonical manifest。

## 8个预选案例

| Case | 风险 | 当前状态 | 人工重点页/问题 |
|---|---|---|---|
| A | redemption_rights | draft | 页300；上市后持续，但severity未冻结 |
| B | redemption_rights | draft | 页207；确认全部特殊权利已终止 |
| C | redemption_rights | draft | 页152；明确conditional restoration与draft needs_review争议 |
| D | redemption_rights | draft | 页78及外引工具条款；termination不完整 |
| E | material_litigation_compliance | draft | 页26；重大未决，但severity未冻结 |
| F | material_litigation_compliance | draft | 页298；已结案并支付 |
| G | material_litigation_compliance | draft | 页222；明确否定重大诉讼 |
| H | material_litigation_compliance | draft | 页44；一般未来风险因素 |

## LEGAL_GOLDEN_ADJUDICATION_REQUIRED

Case C的draft为`needs_review`，但冻结规则规定“存在明确restoration condition时进入Verifier”，现有Builder因此输出`BUILT + PENDING`。不得为了draft CSV修改Builder；请第二复核人决定gold status应表达“候选进入核验”还是“条款仍需人工判断”。

## v0.3 Legal severity review guidance

Case A和Case E的draft `expected_level=high`是severity policy冻结前的建议，不是v0.3
权威等级。v0.3已经冻结为provisional `medium / 50`，并要求
`level_is_provisional=true`、`score_is_rule_based=true`、
`score_is_probability=false`。人工复核必须依据该政策处理A/E的draft差异，记录分歧和
仲裁理由；本治理任务不修改CSV，不伪造second reviewer，也不改变review status。

## Legal Golden review ownership

Legal A—H必须经过真实人工primary review和independent second review。
`codex_preselection`不是人工primary review；primary reviewer与second reviewer必须是
真实、相互独立的人类复核人，不得由同一人自审，也不得自动填写复核人姓名或状态。

4号法务成员承担Legal专业复核职责，并参与Case C的专业仲裁；复核时依据已冻结的
Legal severity policy处理Case A/E。2号技术备份／数据成员仅负责manifest完整性检查、
reviewed rows的数据治理与canonical并表支持、batch/evaluation技术复跑及独立复现记录。
2号成员不替代Legal专业人工复核责任。
