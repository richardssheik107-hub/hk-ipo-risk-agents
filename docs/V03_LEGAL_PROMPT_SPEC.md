# v0.3 Legal Prompt Specification

## A. Shareholder Rights

- `task_name`: `shareholder_rights_extract`
- `prompt_version`: `legal_shareholder_rights_v1`
- `response_model`: `ShareholderRightCandidate`

模型必须：只依据输入Evidence；不使用外部知识；不虚构holder、termination或restoration；区分历史与当前权利；区分上市前、上市时和上市后；区分termination与restoration；缺失字段返回`null`或空值；`evidence_ids`只能引用输入Evidence。

模型禁止：输出risk level、score、verified状态、最终风险结论或投资建议。

建议任务指令：

```text
Extract only shareholder-right facts explicitly supported by the supplied Evidence.
Distinguish historical from current rights and before-listing, on-listing and
after-listing timing. Treat termination and restoration as separate facts. Never
invent a holder, termination event or restoration condition. Use null/empty values
when the Evidence is incomplete. Cite only supplied evidence_ids. Do not assess risk
level, verification status or investment merit.
```

## B. Litigation and Compliance

- `task_name`: `litigation_compliance_extract`
- `prompt_version`: `legal_litigation_compliance_v1`
- `response_model`: `LitigationComplianceCandidate`

模型必须：区分actual matter与generic future risk；识别明确否定；区分历史与当前；识别pending、resolved、settled、closed和remediated；只有Evidence明确支持时才填写重大性；不虚构amount、regulator、counterparty或case status；`evidence_ids`只能引用输入Evidence。

模型禁止：输出最终risk level、score、verified状态或投资建议。

建议任务指令：

```text
Extract only actual litigation or compliance facts supported by the supplied
Evidence. Distinguish actual events from generic future-risk language and explicit
negative statements. Preserve historical/current and pending/resolved/settled/
remediated status. Do not infer materiality, amount, regulator, counterparty or case
status unless explicit. Cite only supplied evidence_ids. Do not assess final risk
level, verification status or investment merit.
```

## 当前接入状态

当前`OpenAICompatibleLLMProvider.generate_structured(...)`只把`task_name`、`prompt_version`、JSON schema和Evidence放入请求，system prompt仅要求返回匹配schema的JSON。不存在正式prompt registry或prompt resolver。因此，Legal domain prompt现在**没有真正进入real LLM请求**；存在`prompt_version`字符串不等于Prompt已接入。

Pydantic字段描述可以改善JSON schema语义，但不足以替代跨字段、否定、历史状态和禁止事项的完整domain prompt。

## MEMBER_1_PROMPT_INTEGRATION_REQUEST

建议成员1在不改变冻结`generate_structured(...)`签名的前提下增加内部prompt registry：以`(task_name, prompt_version)`解析受版本控制的domain instruction，并由Provider在通用JSON约束之外加入对应system/developer message。未知版本应安全失败，不应静默回退为通用抽取。成员4提供本文件中的两份规范和后续prompt测试；Provider实现仍由成员1维护。
