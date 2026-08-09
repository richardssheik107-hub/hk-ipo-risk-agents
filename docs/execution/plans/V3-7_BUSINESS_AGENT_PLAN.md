---
plan_id: V3-7
title: Implement Standalone Real Business Agent for Precommercial Product Risk
status: APPROVED
revision: 1
base_commit: 47e3a0779054101d96250a881654a41d33f7bc32
branch: feat/v03-business-agent
owner: business-product
planner: web-chatgpt
executor: codex
report_path: docs/execution/reports/V3-7_BUSINESS_AGENT_EXECUTION_REPORT.md
---

# V3-7 Real Business Agent — Precommercial Product Risk

## Goal

在不修改 v0.3 冻结公共接口、LLMProvider、Retriever、风险注册表、Container、Workflow 或 Service 的前提下，实现一个可独立调用、可测试、可追溯 Evidence 的真实 `V03BusinessAgent`，只负责：

- `precommercial_product`

该 Agent 必须能够区分：

- 直接产品销售收入；
- 授权 / licensing 收入；
- milestone / 里程碑收入或付款；
- R&D / 研发服务收入；
- collaboration / 合作收入；
- 尚未产生产品销售收入；
- 产品已获批但尚未上市销售；
- 产品已实际商业化并产生直接产品销售收入；
- 产品阶段或收入归属不清。

核心规则保持冻结语义：

```text
core product not commercialized
AND
no direct product sales revenue
=> generate precommercial_product candidate for later Verifier review
```

Agent 只生成 `pending` 风险候选或结构化诊断，不自行产生 `verified` 结论。

本 Plan 的目标是 V3-7 **standalone core closure**，不是共享系统集成。`V03BusinessAgent` 的 ComponentRegistry、Container、Workflow、Service、Verifier 和 UI 接入统一留给后续技术负责人 Integration / V3-8 / V3-9 / V3-11 棒次。

## Background

当前功能主线基线为：

```text
main@47e3a0779054101d96250a881654a41d33f7bc32
```

当前状态：

- V3-3 Retriever 查询族已合并；
- 已存在 `commercialization_status` 和 `core_product_pipeline` 查询族；
- V3-4 LLMProvider 已合并；
- 已存在 Mock、OpenAI-compatible、Unavailable Provider；
- `LLMProvider.generate_structured(...)` 只接收 Retriever 选择后的 `Evidence`，并通过调用方 Pydantic model 验证；
- `CommercializationCandidate` 与 `CoreProductCandidate` 已冻结在 `business_models.py`；
- `precommercial_product` 已进入 v0.3 风险注册表，唯一 owner 为 Business；
- `precommercial_product` 不要求 Calculation；
- 当前共享 Container 仍使用 `DisabledBusinessAgent` / Mock Business Agent；
- 当前黄金 Manifest 没有真实 Business 案例；
- V3-1 仍为 PARTIAL；
- 当前统一阶段是 Gate A — Professional Agent Completion & Golden Review。

### Important Provider constraint

冻结的 `LLMProvider.generate_structured(...)` 没有业务 prompt 文本参数，V3-4 也明确没有实现 prompt-specific business logic。

因此本 Plan 不修改 Provider，也不创建一个实际上不会被 Provider 消费的“假 prompt 文件”。V3-7 使用：

1. 已有 Retriever Evidence；
2. 确定性 Business 文本规则作为最低可运行能力；
3. 已冻结 Pydantic candidate models；
4. 可选 LLM structured extraction 作为候选事实增强；
5. 确定性 reconciliation 和 risk rule 作为最终 Agent-side decision。

LLM 不得覆盖明确的产品销售收入语义，也不得直接输出最终 RiskItem、verification status 或最终评分。

如果实际实现证明没有 prompt registry 就无法安全完成最低 Business 闭环，必须停止并提出 Plan Change Request，不得在本棒私自修改 LLMProvider。

## Project Rules

执行前必须阅读并遵守：

- AGENTS.md
- docs/PROJECT_SPEC.md
- docs/ARCHITECTURE.md
- docs/DATA_SCHEMA.md
- docs/PROJECT_MASTER_CHECKLIST.md
- docs/V03_DEVELOPMENT_CONTRACT.md
- docs/V03_RISK_RULES.md
- docs/V03_ANNOTATION_GUIDE.md
- docs/V03_LLM_PROVIDER_SPEC.md
- docs/execution/README.md

冻结契约版本：

```text
v03_contract_v1
```

冻结标注契约：

```text
v03_annotation_v1
```

冻结 LLMProvider 接口版本：

```text
v03_llm_provider_v1
```

## Inputs

必须检查并以当前仓库实现为事实源：

- src/ipo_risk/agents/base.py
- src/ipo_risk/agents/business_models.py
- src/ipo_risk/agents/disabled.py
- src/ipo_risk/agents/mock.py
- src/ipo_risk/agents/financial_v03.py
- src/ipo_risk/agents/financial_builders.py
- src/ipo_risk/agents/financial_policy.py
- src/ipo_risk/retrieval/keyword.py
- src/ipo_risk/retrieval/query_families.py
- src/ipo_risk/providers/base.py
- src/ipo_risk/providers/mock.py
- src/ipo_risk/providers/llm.py
- src/ipo_risk/schemas/__init__.py
- src/ipo_risk/domain/risk_codes.py
- configs/v03_risk_rules.yaml
- tests/contract/test_v03_agent_contract.py
- tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv

冻结 Business candidate models：

```python
class CommercializationCandidate(BaseModel):
    product_name: str
    development_stage: str
    has_product_revenue: bool | None = None
    commercialization_dependency: str = ""
    evidence_ids: list[str] = Field(min_length=1)

class CoreProductCandidate(BaseModel):
    product_name: str
    is_core_product: bool
    approval_status: str = ""
    launch_status: str = ""
    evidence_ids: list[str] = Field(min_length=1)
```

不得修改这些字段。

冻结 Business 风险所有权：

```text
precommercial_product -> business
```

Business 可以提取客户 / 供应商依赖事实，但本 Plan 不生成：

```text
customer_concentration
supplier_concentration
```

这两个风险码继续属于 Financial。

## Allowed Files

本 Plan 只允许创建或修改：

- src/ipo_risk/agents/business_v03.py
- src/ipo_risk/agents/business_extraction.py
- src/ipo_risk/agents/business_policy.py
- tests/unit/test_business_extraction_v03.py
- tests/unit/test_business_agent_v03.py
- tests/contract/test_business_agent_v03_contract.py
- tests/regression/test_v03_business_golden_values.py
- tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv
- scripts/check_v03_business_agent.py
- docs/execution/reports/V3-7_BUSINESS_AGENT_EXECUTION_REPORT.md

Manifest 只允许新增或修正 `risk_code=precommercial_product` 的 Business 行；不得修改现有 Financial、Legal synthetic 或其他风险记录。

## Forbidden Files

禁止修改：

- docs/execution/plans/V3-7_BUSINESS_AGENT_PLAN.md
- src/ipo_risk/agents/business_models.py
- src/ipo_risk/agents/base.py
- src/ipo_risk/agents/disabled.py
- src/ipo_risk/agents/mock.py
- src/ipo_risk/agents/financial*
- src/ipo_risk/agents/legal*
- src/ipo_risk/schemas/
- src/ipo_risk/retrieval/
- src/ipo_risk/providers/
- src/ipo_risk/core/
- src/ipo_risk/domain/
- src/ipo_risk/workflows/
- src/ipo_risk/services/
- src/ipo_risk/reporting/
- src/ipo_risk/predictors/
- src/ipo_risk/skills/
- app/
- prompts/
- configs/
- data/
- docs/V03_DEVELOPMENT_CONTRACT.md
- docs/V03_RISK_RULES.md
- docs/V03_ANNOTATION_GUIDE.md
- docs/V03_LLM_PROVIDER_SPEC.md
- docs/DATA_SCHEMA.md
- .env.example
- pyproject.toml
- .github/workflows/

不得新增第三方依赖。

## Tasks

### 1. Establish standalone Business Agent contract

- [ ] 新增 `V03BusinessAgent`，`name = "business"`。
- [ ] 保持统一方法：

```python
analyze(
    profile: IPOProfile,
    chunks: list[DocumentChunk],
    market: MarketSnapshot | None = None,
) -> list[RiskItem]
```

- [ ] `analyze()` 永远返回 `list[RiskItem]`，无风险时返回 `[]`。
- [ ] Agent 只允许生成 `precommercial_product`。
- [ ] Agent 实现 `last_diagnostics: list[ComponentDiagnostic]`。
- [ ] 每次 `analyze()` 开始前重置 diagnostics，禁止残留上一案例状态。
- [ ] 本棒不注册到 ComponentRegistry，不修改 Container / Workflow / Service。

### 2. Use only existing Retriever capability

- [ ] 使用已有 `KeywordDocumentRetriever` 或注入的兼容 Retriever。
- [ ] 仅使用现有 V3-3 Query Families / aliases，不修改 Retriever。
- [ ] Business Evidence 至少覆盖两类意图：

```text
commercialization_status
core_product_pipeline
```

- [ ] 每类查询最多保留 5 条 Evidence。
- [ ] 合并去重后发送给单次 LLM 调用的 Evidence 必须保持小规模；不得发送完整招股书或完整 `DocumentChunk` 集合。
- [ ] Evidence 去重至少基于：

```text
document_id + chunk_id + page
```

- [ ] 无匹配时返回结构化 `evidence_not_found`，不得把“未找到”当成“已商业化”或“不适用”。
- [ ] 如果真实 Business 案例证明现有 Query Family 无法召回主证据，需要修改 Retriever，则停止本 Plan，提出独立 Retriever follow-up。

### 3. Implement deterministic Business fact extraction

在 `business_extraction.py` 中建立纯 Python、无网络、可独立测试的最小事实提取能力。

- [ ] 归一化简体、繁体、英文及常见 PDF 空白 / 换行。
- [ ] 提取或识别核心产品名称与“核心产品”身份。
- [ ] 识别开发阶段，至少覆盖：

```text
preclinical / 临床前
phase I / I期 / 一期
phase II / II期 / 二期
phase III / III期 / 三期
registration / NDA / BLA / NMPA submission
approved / marketing approval
launched / commercialized / commercial sales
```

- [ ] 识别产品批准状态与上市 / 销售状态。
- [ ] 明确区分“获批”与“已商业化”：
  - 获批但明确尚未上市 / 尚未销售，不得自动视为 commercialized；
  - 只有批准信息、没有上市或销售状态时，若无法确定商业化状态，应进入 `needs_review`。

### 4. Enforce revenue attribution semantics

`has_product_revenue=True` 只能表示 **直接产品销售收入**。

- [ ] 以下收入可以作为公司存在收入的事实，但不得计为产品销售收入：

```text
licensing / 授权收入
milestone / 里程碑付款或收入
R&D service / 研发服务收入
collaboration / 合作收入
other service revenue / 其他服务收入
```

- [ ] generic `revenue` / `收入` 如果没有产品销售归属，不得推断 `has_product_revenue=True`。
- [ ] 明确“尚未产生产品销售收入 / no revenue from product sales”时，应支持 `has_product_revenue=False`。
- [ ] 明确产品销售 / commercial sales / sales of product 并能与核心产品或商业化产品关联时，才支持 `has_product_revenue=True`。
- [ ] 同一 Evidence 集同时出现明确“无产品销售收入”和明确“已有直接产品销售收入”时，视为冲突，不得静默选择一方。
- [ ] 将识别到的非产品收入类型记录到内部 decision / RiskItem metadata，例如：

```text
revenue_source_types = ["licensing", "milestone", "rd_service", "collaboration"]
```

不得为此修改冻结 candidate model。

### 5. Produce frozen Business candidate models

确定性 extractor 必须尽量映射为现有：

- `CommercializationCandidate`
- `CoreProductCandidate`

- [ ] `evidence_ids` 必须来自 Retriever 实际返回的 Evidence。
- [ ] candidate 不得引用不存在或未检索的 Evidence ID。
- [ ] candidate 中的 product name / stage / approval / launch status 必须能由选中 Evidence 支持。
- [ ] 不得新增新的公共 candidate schema 来绕过冻结模型。

### 6. Optionally consume V3-4 LLMProvider

`V03BusinessAgent` 允许通过构造函数注入已存在的 `LLMProvider`。

- [ ] 默认没有显式 Provider 时，不得偷偷发起网络请求；默认使用确定性路径或 zero-network unavailable 行为。
- [ ] 允许以下稳定 structured task names：

```text
business_precommercial_commercialization_extract
business_precommercial_core_product_extract
```

- [ ] 使用固定：

```text
prompt_version = business_precommercial_v1
```

- [ ] LLM structured output 只能使用冻结的 `CommercializationCandidate` / `CoreProductCandidate` 验证。
- [ ] 每个 candidate 的 `evidence_ids` 必须是本次 Provider 输入 Evidence 的子集。
- [ ] Provider 输出不得直接成为 RiskItem。
- [ ] Provider 输出不得直接决定 verified / final score。
- [ ] `UnavailableLLMProvider` 或 Provider failure 在确定性事实足够时，不得阻断整个 Business Agent。
- [ ] 确定性事实不足且 LLM 也不可用 / 失败时，返回结构化 `needs_review` 或 `component_failure`，不得虚构结论。
- [ ] 不在 diagnostics / RiskItem metadata 中记录 raw response、API Key、Authorization header 或底层敏感异常文本。
- [ ] 可记录安全元数据，例如 provider name、prompt version、request ID、response hash、failure kind。

### 7. Reconcile deterministic and LLM candidates

- [ ] 明确文本事实优先于无证据 LLM 推断。
- [ ] LLM 与确定性结果一致时，可作为交叉验证并记录安全 metadata。
- [ ] LLM 与确定性结果在以下字段发生实质冲突时，返回 `conflicting_values`，不生成正式风险：

```text
has_product_revenue
core product identity
development / approval / launch state
```

- [ ] LLM 引用越界 Evidence ID 时，视为 candidate invalid，进入 `needs_review`，不得自动补造 Evidence。
- [ ] Generic marketing / risk-factor language 不得覆盖 Business factual section 的明确状态。

### 8. Apply deterministic precommercial rule

实现并严格验证冻结规则：

```text
core_product_not_commercialized
AND
has_product_revenue == False
=> precommercial_product candidate
```

Decision semantics：

#### Generate risk candidate

满足全部条件：

- 有明确核心产品；
- 核心产品明确尚未商业化 / 未上市销售；
- 明确无直接产品销售收入；
- Evidence ID、Document ID、Chunk ID、物理页码可追溯；
- 无相互冲突的商业化 / 收入事实。

输出：

```text
risk_code = precommercial_product
category = business
agent_name = business
verification_status = pending
calculation = None
```

本 v0.3 候选暂采用单级确定性展示严重度：

```text
level = medium
score = 60
```

并记录：

```text
rule_version = v03_contract_v1
severity_policy = business_candidate_medium_v1
score_is_rule_based = true
score_is_probability = false
```

不得基于 Phase I / II / III 自行发明新的 high / critical 阈值。若需要阶段化 severity，必须另行修改规则合同并提出 Plan Change Request。

#### Not applicable

以下情况至少之一明确成立：

- 核心产品已实际上市 / 商业销售；
- 有直接产品销售收入且与商业化产品对应；
- 现有证据明确证明该规则不成立。

无 RiskItem，写 `not_applicable` diagnostic。

#### Needs review

以下情况不得硬判：

- 产品是否核心不清；
- 开发 / 批准 / 上市状态不清；
- generic revenue 无法判断是否产品销售；
- 产品收入归属不清；
- Evidence 身份不完整；
- LLM / deterministic candidate 无法安全 reconciliation。

无 RiskItem，写 `needs_review` diagnostic。

#### Conflicting values

明确相互冲突的产品收入或商业化状态：

无 RiskItem，写 `conflicting_values` diagnostic。

### 9. Preserve Evidence identity and stable risk identity

- [ ] 正式候选 RiskItem 的所有 Evidence 必须为 `prospectus` source。
- [ ] 每个 Evidence 必须可映射回对应 `DocumentChunk`：

```text
document_id
chunk_id
page
```

必须一致。

- [ ] 不允许不存在的 chunk / page。
- [ ] RiskItem 的 `risk_id` 必须使用稳定确定性方法生成，例如 UUID5，输入至少包含：

```text
risk_code
evidence_ids
product_name
development_stage
has_product_revenue
```

相同输入重复运行应得到相同 risk_id。

### 10. Implement typed diagnostics and failure isolation

`last_diagnostics` 至少对 `precommercial_product` 输出一条结果。

允许：

```text
risk_generated
not_applicable
evidence_not_found
extraction_failed
conflicting_values
unsupported_layout
needs_review
component_failure
```

- [ ] Agent 内 Retriever、deterministic extractor、LLM Provider 任一失败，不得泄漏原始异常 payload。
- [ ] 可恢复失败不得击穿整个 Python 调用；用 diagnostics 表达。
- [ ] 如果所有可用检索尝试均因组件异常失败，使用 `component_failure`，不是 `evidence_not_found`。
- [ ] 如果检索成功但文本无法映射为可信候选，使用 `extraction_failed` / `needs_review`。
- [ ] 不得以空 Evidence 生成 `precommercial_product` RiskItem。

### 11. Add Business real-case draft annotations

在 `tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv` 中只新增 `precommercial_product` 真实 Business 行。

最低要求：

- [ ] 至少 1 个 2020—2023 development-set 正例：`applicable=true`；
- [ ] 至少 1 个 2020—2023 development-set 负例：`applicable=false`；
- [ ] 优先复用 Manifest 已存在的真实 development-set 公司，减少数据面扩张；
- [ ] 18A / biotech 案例可以作为正例候选，但必须先核对真实招股书，禁止按公司类型猜结论；
- [ ] 商业化成熟公司可以作为负例候选，但必须以招股书中的直接产品销售 / 商业化证据为准；
- [ ] 至少一个真实正例或单元 / 回归案例必须体现“存在 licensing / milestone / R&D service / collaboration 收入，但没有直接产品销售收入不等于已经商业化”的语义；
- [ ] `gold_page` 必须是 PDF 物理页码；
- [ ] `exact_text` 只保留验证所需最短原文；
- [ ] `reviewer` 使用真实项目角色标识，例如 `member-5`；
- [ ] Codex 不得伪造第二复核人：没有真实第二人工复核时 `second_reviewer` 留空；
- [ ] 没有真实第二人工复核时 `review_status=draft`；
- [ ] 不得把 draft 写成 `double_reviewed`；
- [ ] 不得读取、选择、标注或调优任何 2025 blind case。

如果执行环境没有至少一个可验证正例和一个可验证负例的 2020—2023 原始招股书访问能力，则代码实现可以继续，但本 Plan 最终状态必须为 `BLOCKED`，不得声称 V3-7 Gate A closure 完成。

### 12. Add network-free tests

#### `tests/unit/test_business_extraction_v03.py`

至少覆盖：

- [ ] 简体 / 繁体 / English 商业化表达；
- [ ] preclinical / Phase I / II / III / approval / launch；
- [ ] 明确无产品销售收入；
- [ ] 明确直接产品销售收入；
- [ ] licensing-only 不计产品销售；
- [ ] milestone-only 不计产品销售；
- [ ] R&D-service-only 不计产品销售；
- [ ] collaboration-only 不计产品销售；
- [ ] generic revenue 归属不清；
- [ ] 产品收入冲突；
- [ ] 获批但尚未销售；
- [ ] risk-factor 泛化语句不应被当成已发生事实。

#### `tests/unit/test_business_agent_v03.py`

至少覆盖：

- [ ] clean positive -> one pending `precommercial_product`；
- [ ] clean negative -> empty risks + `not_applicable`；
- [ ] licensing / milestone / R&D service / collaboration revenue 不能将 positive 错判为 commercialized；
- [ ] ambiguous revenue -> no risk + `needs_review`；
- [ ] conflicting revenue -> no risk + `conflicting_values`；
- [ ] no evidence -> `evidence_not_found`；
- [ ] Retriever failure -> `component_failure`；
- [ ] invalid Evidence identity -> no risk；
- [ ] MockLLMProvider valid candidate；
- [ ] LLM candidate Evidence ID 越界；
- [ ] LLM / deterministic conflict；
- [ ] Unavailable LLM + sufficient deterministic facts still works；
- [ ] LLM failure + insufficient deterministic facts degrades honestly；
- [ ] repeated analyze resets diagnostics；
- [ ] identical input produces stable risk_id；
- [ ] no Calculation is attached；
- [ ] RiskItem score metadata states rule score, not probability。

#### `tests/contract/test_business_agent_v03_contract.py`

至少覆盖：

- [ ] exact `RiskAgent.analyze()` signature；
- [ ] return type list；
- [ ] `agent.name == "business"`；
- [ ] only owned risk code；
- [ ] no Financial / Legal / Market risk code；
- [ ] candidate models remain unchanged；
- [ ] `CommercializationCandidate` and `CoreProductCandidate` retain exact frozen fields；
- [ ] output RiskItem is pending, never verified；
- [ ] typed `ComponentDiagnostic`；
- [ ] `precommercial_product` requires Evidence but no Calculation；
- [ ] no public Schema / Provider protocol change。

#### `tests/regression/test_v03_business_golden_values.py`

- [ ] 使用本棒新增的短真实 Business `exact_text` 或等价最小固定文本做无 PDF、无网络回归；
- [ ] 至少一个正例；
- [ ] 至少一个负例；
- [ ] 若真实正例包含 non-product revenue，则锁定“非产品收入不等于产品销售收入”的语义；
- [ ] draft annotation 只用于回归，不得宣称 double-reviewed precision。

### 13. Add a safe local Business smoke script

新增：

```text
scripts/check_v03_business_agent.py
```

要求：

- [ ] 从环境变量或命令行接收本地 PDF 路径，不硬编码用户绝对路径；
- [ ] 使用现有 PyMuPDF Parser 和 Keyword Retriever；
- [ ] 直接实例化 `V03BusinessAgent`，不修改 Container；
- [ ] 可使用现有 runtime LLM configuration 创建 Provider，但无凭证时必须安全降级；
- [ ] 输出只包含：
  - parsed page / chunk count
  - risk count
  - diagnostic code
  - risk_code
  - verification_status
  - evidence page / Evidence ID
  - provider / prompt version 等安全 metadata
- [ ] 不打印：
  - API Key
  - Authorization header
  - 完整 Evidence 原文
  - 完整 LLM raw response
  - 本地绝对路径

### 14. Generate execution report

生成：

```text
docs/execution/reports/V3-7_BUSINESS_AGENT_EXECUTION_REPORT.md
```

报告必须明确：

- Plan compliance；
- created / modified files；
- deterministic extraction behavior；
- LLM path / no-key path behavior；
- real Business draft annotation rows；
- tests and validation；
- manual Business cases；
- whether real external LLM was NOT_TESTED / PASS / FAIL；
- known limitations；
- human second-review status；
- exact `Next Action`。

## Acceptance Criteria

### Public contract

- `RiskAgent.analyze(...) -> list[RiskItem]` 不变。
- `agents/base.py` 不变。
- `business_models.py` 不变。
- `schemas/` 不变。
- `LLMProvider` protocol 和实现不变。
- Retriever interface / query families 不变。
- risk registry / frozen YAML 不变。

### Business ownership

- `V03BusinessAgent` 只生成 `precommercial_product`。
- 不生成 customer / supplier concentration。
- 不生成 Legal / Market 风险。

### Evidence

- 正式 candidate risk 必须有真实 Evidence。
- Evidence ID、Document ID、Chunk ID、物理页码一致。
- 无 Evidence 不得生成风险。
- LLM 不得引用 Retriever 输入集合外的 Evidence。

### Revenue semantics

- 直接产品销售收入可以支持 `has_product_revenue=True`。
- licensing 不得被当作产品销售收入。
- milestone 不得被当作产品销售收入。
- R&D service 不得被当作产品销售收入。
- collaboration revenue 不得被当作产品销售收入。
- generic revenue 归属不明必须 needs_review，不得猜测。

### Commercialization semantics

- Phase / clinical-stage 不自动等于商业化。
- 获批不自动等于已商业化。
- 明确获批但尚未上市销售且无产品销售收入，可以满足 precommercial rule。
- 明确 launched / commercial sales / direct product revenue 的案例不应产生 precommercial risk。
- 模板化 risk-factor 文本不得单独触发正式风险。

### Risk behavior

Clean positive：

```text
one RiskItem
risk_code = precommercial_product
category = business
level = medium
score = 60
verification_status = pending
calculation = None
```

Clean negative：

```text
[]
last_diagnostics contains not_applicable
```

Ambiguous / conflicting：

```text
[]
last_diagnostics contains needs_review or conflicting_values
```

- Agent 不得自证 verified。
- Score 必须标记为 deterministic rule score，不得称为 probability。
- 相同输入 risk_id 稳定。

### LLM behavior

- 测试默认不访问真实网络。
- LLM 只处理 Retriever-selected Evidence。
- LLM structured output 使用冻结 candidate models 验证。
- LLM failure 在确定性路径足够时不会导致整个 Agent 失败。
- LLM failure 在信息不足时诚实降级。
- 不泄漏 secret / raw response / sensitive exception text。

### Golden cases

- 至少 1 个真实 2020—2023 positive Business draft row。
- 至少 1 个真实 2020—2023 negative Business draft row。
- 没有真实第二复核时保持 `draft`。
- 不伪造 `double_reviewed`。
- 2025 blind set 未被读取或用于调优。
- Manifest integrity validation 通过。

### Scope

- 不修改 Container。
- 不修改 Workflow。
- 不修改 Service。
- 不实现 V3-8 Verifier。
- 不实现 V3-9 Supervisor / enhanced_v2。
- 不实现 V3-11 UI。
- 不引入新的第三方依赖。
- 不修改其他成员业务代码。

### Regression

- Mock 模式不回归。
- v0.2 2410.HK 真实现金跑道回归不变。
- 完整测试集通过。

## Required Validation

必须执行：

```text
pytest -q tests/unit/test_business_extraction_v03.py
pytest -q tests/unit/test_business_agent_v03.py
pytest -q tests/contract/test_business_agent_v03_contract.py
pytest -q tests/contract/test_v03_agent_contract.py
pytest -q tests/regression/test_v03_business_golden_values.py
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_v03_golden_manifest.py tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv --integrity
python -m compileall -q app src scripts
python scripts/check_execution_scope.py docs/execution/plans/V3-7_BUSINESS_AGENT_PLAN.md
git diff --check
```

不得通过删除、弱化、skip、xfail 有效测试来获取通过。

## Manual Validation

### A. Existing v0.2 regression

如果本地 2410.HK fixture 可用，运行：

```text
python scripts/check_real_v02_e2e.py
```

期望继续保持：

- parsed chunks/pages: 706
- parser errors: 0
- Evidence pages: 563 / 562
- cash runway: 2.76 months
- verification: verified
- prediction: 90 / critical

如果真实 fixture 不可用，记录 `NOT_TESTED`，不得伪造 PASS。

### B. Real Business positive case

使用一个 2020—2023 development-set 招股书：

- Retriever 找到核心产品 / pipeline Evidence；
- 找到商业化 / 产品收入 Evidence；
- 核对 PDF 物理页码；
- 明确核心产品尚未商业化；
- 明确没有直接产品销售收入；
- 如存在 licensing / milestone / R&D service / collaboration 收入，确认它没有被当作产品销售；
- Agent 输出 pending `precommercial_product`；
- Evidence 可追溯；
- 不要求本棒把它 verified。

### C. Real Business negative case

使用另一个 2020—2023 development-set 招股书：

- 真实证据明确产品已商业化 / 有直接产品销售收入；
- Agent 不生成 `precommercial_product`；
- diagnostic 为 `not_applicable`。

### D. LLM mode

无真实凭证时：

- Mock LLM path 必须通过；
- Unavailable LLM path 必须通过；
- deterministic path 必须仍可运行。

如果存在安全的本地新凭证，可选运行真实 Provider smoke；它不是 CI requirement，也不得为了完成本 Plan 把密钥写入仓库、报告或聊天。

## Stop Conditions

出现以下任一情况，停止并返回 `PLAN_CHANGE_REQUIRED`：

- 必须修改 `business_models.py` 才能表达最低安全事实；
- 必须修改公共 Schema；
- 必须修改 `RiskAgent` 返回类型；
- 必须修改 LLMProvider protocol / implementation；
- 必须新增 prompt registry Provider capability 才能安全运行；
- 必须修改 Retriever / Query Families 才能完成真实案例主证据召回；
- 必须修改 `configs/v03_risk_rules.yaml` 或 `risk_codes.py`；
- 必须修改 Container、Workflow 或 Service；
- 必须实现 Business Verifier 才能让 Agent 本身成立；
- 必须发明 Phase-based high / critical severity 规则；
- 必须新增第三方依赖；
- 必须修改 Allowed Files 之外的文件；
- 通过测试需要删除、弱化、skip 或 xfail 现有测试；
- 测试必须访问真实外部网络；
- 发现与本 Plan 无关的 dirty worktree；
- 工作实质扩张到 V3-8、V3-9 或 V3-11。

出现以下情况，停止并返回 `BLOCKED`：

- 无法访问至少一个可验证的 2020—2023 Business 正例原始招股书；
- 无法访问至少一个可验证的 2020—2023 Business 负例原始招股书；
- 可用案例只有 2025 blind set；
- 本地依赖 / 数据前提缺失且无法在 Allowed Files 内解决。

如果发现任何 API Key、Token、密码、用户绝对路径、原始大 PDF、ZIP、缓存或生成结果准备进入 diff，立即停止，不得提交。

## Expected Deliverables

- `V03BusinessAgent`
- deterministic Business fact extraction
- revenue attribution classification
- frozen candidate model mapping
- optional structured LLM candidate consumption
- Evidence traceability and stable risk identity
- typed Business diagnostics
- deterministic `precommercial_product` decision
- safe no-key / unavailable degradation
- at least one real Business positive draft annotation
- at least one real Business negative draft annotation
- Business unit tests
- Business contract tests
- Business real-text regression tests
- safe local Business smoke script
- `docs/execution/reports/V3-7_BUSINESS_AGENT_EXECUTION_REPORT.md`

This Plan explicitly does **not** authorize:

- modifying the Plan itself
- changing frozen candidate models
- changing public Schema
- changing LLMProvider
- changing Retriever
- changing risk registry or frozen YAML rules
- ComponentRegistry / Container integration
- Workflow integration
- Service integration
- V3-8 Business Verifier
- V3-9 Supervisor / enhanced_v2
- V3-11 UI / report implementation
- Market Agent work
- 2025 blind-set analysis or tuning
- commit
- push
- Pull Request creation
- merge
- tag
- release

## Notes

- 本棒由用户接手 5号业务/产品职责，但仍按原 5号 ownership 边界执行，不因为用户同时承担技术负责人职责而扩大本 Plan 的共享文件权限。
- Business Agent 的共享注册与系统集成属于后续技术负责人 Integration Task；当前目标是 standalone-ready。
- 真实 Business 黄金行在没有第二人工复核前只能是 draft。V3-7 core code 可以完成，但 Gate A 最终退出仍需要后续 human second review。
- 如果后续希望引入真正的 versioned business prompt registry，应单独设计 Provider / prompt-loading contract，不能在 V3-7 暗中绕过冻结 LLMProvider。
