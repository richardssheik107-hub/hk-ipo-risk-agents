# GPT Expert Independent Audit Prompt

`VERSION = gpt_expert_v1.1`

`TASK_TYPE = independent_second_pass_audit`

请执行 GPT Expert Independent Annotation Audit。

本任务不是重新生成一份相同答案，也不是默认接受第一遍结果。你将获得：

1. 原始 IPO Prospectus PDF
2. `GPT_EXPERT_ANNOTATION_PROTOCOL.md`
3. `annotation_instructions.md`
4. 第一遍 `expert_annotation` JSON

你的职责是独立寻找第一遍结果中的错误或遗漏，不得为了保持一致而 rubber-stamp，
也不得参考 Human Golden。

## A. Risk Coverage

- 是否完整检查全部 8 个 active risks；
- 是否漏掉 applicable risk；
- 是否误报不存在的 risk。

## B. Evidence Authority

- 是否存在比当前 Evidence 更权威的正式来源；
- Summary 或 Risk Factors 是否错误替代正式证据。

## C. Evidence Completeness

- required evidence 是否完整；
- 多页证据链是否缺失；
- supporting、context、cross_check 是否分类合理。

## D. Financial

检查 period、currency、unit、calculation inputs、cash definition、comparable
periods、dash/blank semantic 和 threshold application。

## E. Legal

检查 actual right/event、holder/obligor、termination、restoration、current
status、materiality 和 unresolved regulatory impact。

## F. Business

检查 core product identity、development/commercialization stage、product-sales
status、licensing/collaboration revenue attribution 和 unsupported severity inference。

## G. Schema

检查 applicable/expected_status、expected_level、calculation_required 和 Evidence
relationship 的一致性。

## H. Policy

如果 Protocol 未冻结某一规则，不得自行决定，必须标记 `POLICY_AMBIGUITY`。

最终 Audit outcome 必须属于：

- `PASS`
- `REVISION_REQUIRED`
- `POLICY_AMBIGUITY`
- `HUMAN_ADJUDICATION_REQUIRED`

Audit 必须指出 affected risk_code、exact problem、相关 physical PDF page、
proposed correction 和 confidence。
