# v0.3 LLMProvider 规范

接口版本：`v03_llm_provider_v1`

## 1. 使用范围

LLM 只用于非确定性的结构化候选事实抽取和文本归纳。金额计算、增长率、集中度、现金跑道、阈值判断、Verifier 和最终评分必须由确定性代码完成。

## 2. 公共方法

```python
generate_structured(
    *,
    task_name: str,
    prompt_version: str,
    evidence: list[Evidence],
    response_model: type[BaseModel],
) -> BaseModel
```

`complete(prompt) -> str` 在 v0.3 保留以兼容旧组件，新 Agent 不得将自由文本结果直接当作跨模块接口。

## 3. 输入输出约束

- 输入必须是已检索 Evidence，不得把整份招股书无选择发送给 Provider；
- Provider 必须使用调用方给出的 Pydantic `response_model` 校验输出；
- JSON 解析或模型校验失败必须重试或产生结构化失败，禁止返回半结构化字典；
- Provider 不生成最终 `RiskItem`，Agent 负责把候选事实转换为风险候选；
- 日志只记录摘要和哈希，不记录 API Key，不默认保存完整原文或原始响应。

## 4. 调用元数据

每次调用记录 `LLMCallMetadata`：

```text
provider_name, model_name, prompt_version, latency_ms, token_usage,
request_id, raw_response_hash
```

## 5. 配置与密钥

```text
IPO_RISK_LLM_PROVIDER
IPO_RISK_LLM_API_KEY
IPO_RISK_LLM_BASE_URL
IPO_RISK_LLM_MODEL
IPO_RISK_LLM_TIMEOUT_SECONDS
IPO_RISK_LLM_MAX_RETRIES
```

优先级仍为环境变量 > YAML > 代码默认值。火山 Agent Plan 的 Base URL、模型名和新密钥必须从当前控制台示例取得并通过环境变量注入，仓库不提供可能过期的硬编码地址。任何曾出现在聊天、日志或提交中的密钥都视为已泄露，必须先吊销并轮换。

## 6. Mock、重试与降级

- `MockLLMProvider` 根据 `task_name` 返回预置结构化 payload，并使用同一 Pydantic 模型验证；
- 仅对限流、超时和 5xx 等可恢复错误重试，最多使用配置次数；
- 认证失败、请求无效和多次结构校验失败不盲目重试；
- 最终失败转换为 `ComponentDiagnostic`/`AnalysisError`，相关风险进入 needs_review 或不生成，其他 Agent 继续；
- 测试不得访问真实外部 API。
