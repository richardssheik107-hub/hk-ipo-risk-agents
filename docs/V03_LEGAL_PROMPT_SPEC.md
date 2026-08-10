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
when the Evidence is incomplete. Cite only supplied evidence_ids. Do not assess a
final risk score, risk level, verification status or investment recommendation.
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
closed/remediated status. Do not infer materiality, amount, regulator, counterparty
or case status unless explicit. Cite only supplied evidence_ids. Do not assess a
final risk score, risk level, verification status or investment recommendation.
```

## 当前接入状态

`OpenAICompatibleLLMProvider.generate_structured(...)`现通过内部、版本受控的
prompt registry按精确`(task_name, prompt_version)`解析本文件冻结的两份Legal
instruction，并把解析结果加入实际OpenAI-compatible请求的system message。JSON
schema和调用方提供的Evidence仍随请求传入；公共`generate_structured(...)`签名未变。

已知Legal task或Legal prompt version发生错配时，Provider在网络调用前安全失败，
不会回退到未版本化的通用Legal prompt。非Legal调用继续使用原有通用结构化生成
约束。Mock Provider复用相同Legal identity guard，并继续确定性返回配置payload。

```text
LEGAL_DOMAIN_PROMPT_RUNTIME_STATUS = INTEGRATED
PROMPT_REGISTRY = src/ipo_risk/providers/prompt_registry.py
PUBLIC_LLM_PROVIDER_SIGNATURE_CHANGED = false
```

Pydantic字段描述继续用于JSON schema语义，但不替代本文件中的跨字段、否定、历史
状态和禁止事项domain prompt。

## MEMBER_1_PROMPT_INTEGRATION_REQUEST

本请求已在`feat/v03-completion-one-shot`中按上述边界实现并通过网络隔离契约测试。
后续prompt版本必须新增显式registry映射和测试，不得原位覆盖v1或改变公共Provider签名。
