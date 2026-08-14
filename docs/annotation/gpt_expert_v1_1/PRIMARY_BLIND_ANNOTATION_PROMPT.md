# GPT Expert Primary Blind Annotation Prompt

`VERSION = gpt_expert_v1.1`

`TASK_TYPE = primary_blind_annotation`

请执行 GPT Expert Blind Annotation。

这是一次严格的独立盲标任务。请完整阅读并遵守我上传的：

1. `GPT_EXPERT_ANNOTATION_PROTOCOL.md`
2. `annotation_instructions.md`
3. `blank_annotation.json`

然后仅依据我上传的原始 IPO 招股书 PDF，对 `blank_annotation.json` 中列出的全部 8 个启用风险进行完整、独立标注。

核心要求：

- 不参考、不猜测任何现有 Human Golden、Retriever 或 Agent 输出。
- 不假定任何风险一定存在或不存在；必须自行阅读整份招股书并寻找最权威证据。
- 优先正式财务报表、会计师报告、Business、Legal、Corporate Structure、Pre-IPO Investment 等正式披露。
- Summary 和 Risk Factors 原则上只作为 supporting、context 或 cross_check，除非不存在更正式来源。
- 一个风险可以有多条 Evidence，并明确区分 evidence_role 与 requirement。
- Financial 风险必须记录 period、currency、unit 和 calculation inputs。
- 不得自行创造 threshold、accounting definition、severity policy 或 risk definition。
- 如 Protocol 中某项政策尚未冻结，必须显式报告 `POLICY_AMBIGUITY`，不得自行拍板。
- 所有正式结论必须可追溯到原始 PDF 的物理页码。
- 必须检查全部 8 个风险，不得因初步未找到证据而跳过。

输出契约：

- 最终输出必须是一个可被 `ExpertAnnotationBundle.model_validate()` 直接接受的 JSON 对象。
- 风险级和 Evidence 级 `confidence` 都必须是 `0.0` 至 `1.0`（含端点）的 JSON 数字；不得使用百分数、字符串或 `80` 这类数值。
- 每个 `applicable=true` 的风险必须至少有一条同 `risk_code` 的 Evidence。
- 不得添加 Schema 未定义的字段。

Evidence Object 必须严格使用以下完整结构：

```json
{
  "case_id": "ipo_YYYY_NNNNN",
  "risk_code": "one active risk code",
  "page": 1,
  "evidence_role": "primary",
  "requirement": "required",
  "source_authority": "financial_information",
  "exact_text": "verbatim prospectus text",
  "evidence_reason": "why this evidence supports the assessment",
  "confidence": 0.85
}
```

枚举约束：

- `evidence_role`: `primary`, `supporting`, `context`, `cross_check`
- `requirement`: `required`, `alternative`, `supporting_only`
- `source_authority`: `audited_financial_statement`, `accountants_report`, `financial_information`, `business_section`, `legal_disclosure`, `corporate_structure`, `pre_ipo_investment`, `summary`, `risk_factors`, `other`

Evidence Object 中不得加入 `evidence_id`、`document_id`、`chunk_id`、`section` 或 `metadata`。

完成第一遍后必须自行复核：

1. 是否遗漏任何风险；
2. 是否存在比当前 Evidence 更权威的正式来源；
3. 多页 Evidence 是否完整；
4. applicable、status、level 是否符合 Protocol；
5. Financial calculation inputs 是否完整；
6. 是否把 dash 或 blank 无依据解释为 zero；
7. 是否存在事实冲突或 policy ambiguity；
8. Evidence 物理页码是否准确可追溯；
9. 最终 JSON 是否可以直接通过 `ExpertAnnotationBundle`。

最终只输出一个完整、合法的 JSON 对象，不要使用 Markdown 代码围栏，不要输出表格、比较、说明或 JSON 之外的任何文字。
