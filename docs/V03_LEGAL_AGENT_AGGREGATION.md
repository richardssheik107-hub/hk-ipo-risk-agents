# v0.3 Legal Agent 聚合与失败隔离

实现文件：`src/ipo_risk/agents/legal.py`

## 1. 公共契约

`LegalAgent`保持冻结的Agent接口：

```text
LegalAgent.analyze(
    profile: IPOProfile,
    chunks: list[DocumentChunk],
    market: MarketSnapshot | None = None,
) -> list[RiskItem]
```

一次调用按固定顺序处理：

1. `redemption_rights`；
2. `material_litigation_compliance`。

返回值仍然只包含`list[RiskItem]`。候选初始状态只能是`pending`或`needs_review`，Agent不得设置`verified`。每个候选必须携带真实招股书Evidence。

## 2. 失败隔离

两个风险链路分别执行Retriever、Extractor和Builder，并分别捕获异常。任何一条链路失败只影响对应风险码：

```text
ShareholderRights Retriever / Extractor / Builder失败
→ 记录redemption_rights诊断
→ 继续运行material_litigation_compliance

Litigation Retriever / Extractor / Builder失败
→ 记录material_litigation_compliance诊断
→ 保留已经生成的redemption_rights结果
```

每个风险组件只调用一次正式query family。该调用异常时，对应组件停止生成候选，因为不完整检索可能漏掉后页的终止、豁免、恢复、结案或整改条款；另一个风险组件仍继续。

## 3. Diagnostics

Agent通过现有可选通道`last_diagnostics: list[ComponentDiagnostic]`报告结果。每次`analyze`结束后恰好包含两个诊断，每个风险码一个，避免`return []`无法解释原因。

公共诊断码使用如下：

| 场景 | `DiagnosticCode` |
|---|---|
| 生成候选风险 | `risk_generated` |
| 明确不适用、历史已终止或事项已解决 | `not_applicable` |
| Retriever没有结果 | `evidence_not_found` |
| LLM结构化抽取失败 | `extraction_failed` |
| 事实或状态冲突 | `conflicting_values` |
| 不支持的版式 | `unsupported_layout` |
| 状态、重大性或条款不完整 | `needs_review` |
| Retriever或Builder异常 | `component_failure` |

更细的法务原因保存在`diagnostic.metadata.internal_issue_codes`，无需扩展冻结的公共枚举。当前包括：

- `termination_clause_not_found`；
- `restoration_clause_ambiguous`；
- `negation_detected`；
- `historical_right_only`；
- `historical_matter_only`；
- `matter_resolved`；
- `materiality_unclear`；
- `llm_structured_output_invalid`；
- `llm_provider_unavailable`；
- 以及Extractor和Builder已有的稳定issue code。

诊断还保留阶段、Evidence数量、Evidence ID、页码、异常类型和`failure_isolated=true`。不得把异常原文、API Key或原始LLM响应写入诊断。

## 4. 无LLM配置

未传入`llm_provider`时，Agent使用V3-4公共`UnavailableLLMProvider`：

- 需要LLM理解的真实复杂条款返回`extraction_failed`，内部原因包含`llm_provider_unavailable`；
- 明确否定、一般未来风险或模板文本仍可由诉讼抽取器的确定性L6分类器短路为`not_applicable`；
- Retriever无结果仍返回`evidence_not_found`；
- 不生成Mock事实，也不把不可用解释为无风险。

公共`LLMProviderError`会记录安全的`failure_kind`和`attempts`，但不记录异常消息或远端原始响应。`UNAVAILABLE`和`RESPONSE_VALIDATION`映射为`extraction_failed`；`AUTHENTICATION`、`REQUEST`和`TRANSPORT`映射为结构化`component_failure`，且仍保持双风险失败隔离。

## 5. 1号集成边界

本实现没有替换`MockLegalAgent`、没有修改工作流、服务容器、Retriever公共接口或公共Verifier。1号集成时负责：

1. 在v0.3真实模式中注册`LegalAgent`；
2. 注入正式Retriever和配置好的LLMProvider；
3. 将`last_diagnostics`接入工作流诊断汇总；
4. 将两个候选风险分别交给`LegalRightsVerifier`和`LitigationComplianceVerifier`；
5. 保留v0.2 Mock和现金跑道回归行为。

不得把`LegalAgent`的空列表直接解释为“无法律风险”，必须同时读取两个组件诊断。
