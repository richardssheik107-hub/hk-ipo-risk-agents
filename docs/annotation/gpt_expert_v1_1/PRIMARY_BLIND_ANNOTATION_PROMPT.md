# GPT Expert Primary Blind Annotation Prompt

`VERSION = gpt_expert_v1.1`

`TASK_TYPE = primary_blind_annotation`

请执行 GPT Expert Blind Annotation。

这是一次严格的独立盲标任务。请严格阅读并遵守我上传的：

1. `GPT_EXPERT_ANNOTATION_PROTOCOL.md`
2. `annotation_instructions.md`
3. `blank_annotation.json`

然后从我上传的原始 IPO 招股书 PDF 本身出发，对
`blank_annotation.json` 中列出的全部 8 个启用风险进行完整、独立标注。

核心要求：

- 不参考、不猜测任何现有 Human Golden；
- 不假定任何风险一定存在或不存在；
- 必须自行在整份招股书中寻找最权威证据；
- 优先正式财务报表、会计师报告、Business、Legal、Corporate Structure、
  Pre-IPO Investment 等正式披露；
- Summary 和 Risk Factors 原则上只能作为 supporting、context 或 cross_check，
  除非不存在更正式来源；
- 一个风险可以有多条 Evidence；
- 明确区分 primary、supporting、context、cross_check；
- 明确区分 required、alternative、supporting_only；
- Financial 风险必须记录 period、currency、unit 和 calculation inputs；
- 不得自行创造新的 threshold、accounting definition、severity policy 或 risk definition；
- 如果 Protocol 中某项 policy 尚未冻结，必须显式报告 `POLICY_AMBIGUITY`，不得自行拍板；
- 所有正式结论必须能够追溯到原始 PDF physical page；
- GPT 在本任务中是 Expert Evidence Investigator，不是项目当前已有 Agent，
  不要模仿当前 Agent 的检索限制；
- 必须检查全部 8 个风险，不得因为初步没有找到证据而跳过任何风险。

完成第一遍后必须自行复核：

1. 是否漏掉任何风险；
2. 是否存在比当前 Evidence 更权威的正式来源；
3. 多页 Evidence 是否完整；
4. applicable、status、level 是否符合 Protocol；
5. Financial calculation inputs 是否完整；
6. 是否把 dash 或 blank 无依据解释为 zero；
7. 是否存在事实冲突或 policy ambiguity；
8. Evidence physical page 是否准确可追溯。

最终只输出一个完整、合法 JSON，且必须满足项目 Expert Annotation Schema。

不要输出 Markdown 表格。不要输出 Human-vs-GPT comparison。不要猜测旧 Golden。
不要附加 JSON 之外的解释文字。
