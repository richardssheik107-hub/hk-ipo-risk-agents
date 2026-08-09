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

## MEMBER_1_LEGAL_SEVERITY_POLICY_QUESTION

Case A和Case E的draft `expected_level=high`，但v0.3没有冻结Legal high/medium映射。当前Builder保持provisional `medium/50`、`level_is_provisional=true`、`score_is_probability=false`。请成员1确认v0.3是否统一采用provisional level，以及draft golden的`expected_level`应标为provisional、空值还是另设非评分字段。

## Member-2 handoff

成员2需要：组织8个案例人工二审；复核上述物理页和相邻页；仲裁Case C；等待Legal severity policy答复后处理Case A/E；仅在人工流程完成后决定是否并入正式canonical golden manifest。
