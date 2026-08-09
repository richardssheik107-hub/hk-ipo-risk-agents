# v0.3 Legal 词典与 Retriever 查询需求

正式运行时查询族：`src/ipo_risk/retrieval/query_families.py`

Legal领域补充词只作为需求交接记录在`docs/V03_LEGAL_RETRIEVAL_GAP_REPORT.md`，不再维护第二套运行时YAML词典。

负责人边界：法务成员维护专业词典和查询需求；Retriever 框架、公共接口、排序实现及集成由1号技术负责人修改。

## 1. 使用边界

词典只服务于 Evidence 召回，不作风险判断。关键词命中不得直接生成 `RiskItem`、决定风险等级、设置 `verified` 或进入最终评分。

Retriever 输出继续遵守现有公共接口：

```text
retrieve(list[DocumentChunk], query, limit) -> list[Evidence]
```

没有匹配时必须返回空列表，不得回退到第一页、随机片段或一般性风险章节。

## 2. 查询族

### 2.1 redemption_rights

查询分为三组：

1. 权利名称：赎回、清算优先、反摊薄、优先认购、回购、否决、董事提名、特殊权利及对赌安排；
2. 生命周期状态：终止、失效、豁免、恢复、重新生效及对应英文表达；
3. 上市上下文：上市、首次公开发售、股东协议和Pre-IPO投资。

排序时，权利词与状态词在同一片段或相邻页共同出现，应明显高于单独的权利词。出现“上市时终止”但没有恢复条件的片段仍应召回，供 Legal Agent 和 Verifier 判断为不适用或已终止，不能因为它看起来是负例而过滤掉。

### 2.2 material_litigation_compliance

查询覆盖诉讼、仲裁、行政处罚、监管调查、不合规、牌照许可、税务、环境处罚和数据隐私，并配套：

- 状态词：未决、进行中、已解决、已和解、已结案、已整改；
- 重大性词：重大、重大性、significant、potential impact等。

事项词与状态词、重大性词共同出现时应优先排序。`license/licence/permit`、`tax`、`litigation`等宽泛词单独出现时只能形成低优先级候选，不能被解释为已发生重大事项。

## 3. 规范化与匹配要求

1. 支持简体、繁体、英文，不把简繁转换后的文本写回 Evidence；
2. 英文匹配忽略大小写，并兼容连字符、换行和PDF空格差异；
3. `anti-dilution`、`pre-emptive`、`non-compliance`等应兼容常见连字符版式；
4. `VAM`作为完整缩写匹配，不能匹配英文单词中的普通子串；
5. 多词短语完整命中优先于单个宽泛词；
6. Evidence 必须保留真实 `document_id`、`chunk_id`、物理页码、连续原文和稳定ID；
7. 同一页重复命中应聚合，跨查询重复 Evidence 应按稳定ID去重；
8. 不按公司名、股票代码或固定页码写特例。

## 4. 排序需求

建议按以下信号组合排序，具体权重由1号实现并版本化：

1. 完整法律短语命中；
2. 权利/事项词与状态词共同出现；
3. 重大性、潜在影响、金额或监管机构等上下文；
4. Pre-IPO投资、股东协议、诉讼、监管、牌照等实际事项章节；
5. 同一事项的相邻页状态补充。

以下内容应降权但不能简单删除：

- 一般性法律或监管规定概要；
- 组织章程模板；
- 仅描述未来可能发生事项的通用风险提示；
- 已终止、已结案、已和解或已整改事项。

这些片段可能是重要负证据，Legal Agent和Verifier仍需看到其原文和状态。

## 5. Agent与Verifier交接

Retriever 只返回候选 Evidence。股东权利链路固定为：

```text
Retriever（最多取前10段候选Evidence）
→ LLMProvider.generate_structured(..., response_model=ShareholderRightCandidate)
→ deterministic normalization
→ ShareholderRightsFact
→ Python Rule
→ pending/needs_review RiskItem
→ Verifier
```

`ShareholderRightsExtractor` 使用任务名 `shareholder_rights_extract` 和Prompt版本 `legal_shareholder_rights_v1`。LLM只填写已有的 `ShareholderRightCandidate`，包括权利类型、主体、当前有效性、终止事件及时点、恢复条款及条件、对公众股东的潜在影响、Evidence ID和不确定性原因。确定性归一化负责：

- 将简体、繁体和英文权利名称映射为稳定类型；
- 校验LLM给出的Evidence ID确实来自本次Retriever结果；
- 统一上市、上市申请及相关终止时点；
- 保留“未判断”状态，不把缺失恢复条款机械改写为`false`；
- 将冲突、缺字段和条款不完整转成`needs_review/not_found`事实状态。

`ShareholderRightsFact`是结构化事实，不是`RiskItem`。LLM不得输出风险码、风险等级、评分或最终核验状态，抽取器也不得调用`verified`判断。

`RedemptionRightsRiskBuilder`随后执行冻结的 `effective_or_restorable_rights_require_review` 规则：

1. 只有带可核验Evidence的明确“无特殊权利”事实返回`not_applicable`；`evidence_not_found`不得解释为无风险；
2. 权利明确在上市后继续有效时，生成`pending`风险候选；
3. 权利虽已终止但存在明确恢复条款和触发条件时，生成`pending`条件风险候选，交Verifier结合上市结果核验；
4. 权利在上市时或此前明确终止、明确不会恢复时返回`not_applicable`，不生成当前高风险；
5. 上市后状态、终止条件、恢复状态或恢复触发条件不清时，生成`needs_review`候选；
6. Builder不输出`verified`，也不把“进入核验”自动映射为`high`。由于公共`RiskItem`要求等级和分数，v0.3在核验前统一使用`medium/50`占位，并通过`level_is_provisional=true`和`score_is_probability=false`明确其非最终性质。

诉讼合规链路统一使用一个 `LitigationComplianceExtractor`，不为诉讼、处罚、牌照、税务、环境或隐私分别建立Agent：

```text
Retriever（最多取前10段候选Evidence）
→ LLMProvider.generate_structured(..., response_model=LitigationComplianceCandidate)
→ deterministic normalization
→ LegalMatterObservation
→ Python Rule
→ pending/needs_review RiskItem
→ Verifier
```

统一事项类型包括`litigation`、`arbitration`、`administrative_penalty`、`regulatory_investigation`、`non_compliance`、`license_permit`、`tax`、`environmental_penalty`和`data_privacy`。Observation至少保留：

- 事项类型、事项主体及对手方或监管机构；
- 发生日期、金额、币种和金额单位；
- 当前状态，以及是否未决、已结案或已整改；
- 管理层重大性判断、潜在影响及牌照运营影响；
- Evidence ID和不确定性原因。

抽取器统一状态词并检查布尔状态冲突、金额币种关系和Evidence来源。没有精确发生日期、金额、管理层重大性或潜在影响时不得编造值，应保留`None/空值`；是否进入`needs_review`由冻结规则所需字段决定，不能把所有辅助字段都升级为硬门槛。明确“无实际事项”可形成`matter_type=none`的负面事实；没有Evidence仍是`not_found`，二者不得混淆。LLM输出风险等级、评分或最终状态会被Pydantic模型拒绝。

在调用LLM前，`LegalMatterEvidenceClassifier`先对候选Evidence进行确定性分类。判定优先级为：局部语法否定 > 明确实际事项 > 明确否定 > 一般未来风险 > 监管或章节模板 > 语义不清。局部语法否定优先用于避免把`not currently subject to`、`no proceedings remain pending`等句子误判为实际事项；若不同Evidence同时包含实际事项和否定声明，实际事项仍阻止整批候选被短路。该分类只用于阻止明显负例被抽成已发生事项，不替代LLM处理复杂事实：

- `The Group is not involved in any material litigation.`、`董事确认本集团不存在任何重大诉讼。`属于明确否定；
- `We may be exposed to litigation in the future.`属于一般未来风险；
- 只描述日常经营中可能不时发生诉讼的制式文本属于模板声明；
- `The company is currently subject to...`、`Proceedings remain pending...`、`The regulator imposed a penalty...`、`The licence has not yet been renewed...`属于实际事项候选。

当本批Evidence全部是明确否定、未来假设或模板声明时，抽取器不得调用LLM猜测事项，而应输出带真实Evidence的`matter_type=none/current_status=not_applicable`结构化事实。只要存在实际事项信号或语义不清片段，仍进入结构化抽取，避免用关键词规则提前下结论。

`MaterialLitigationComplianceRiskBuilder`随后执行确定性规则：

1. 明确否定、未来假设或纯模板声明不生成`material_litigation_compliance`风险；
2. 真实事项明确不重大且无持续经营或牌照影响时返回`not_applicable`，不能因为金额等非决策字段缺失重新升级；
3. 重大或可能影响经营/牌照的事项仍未解决时生成`pending`风险候选；
4. 已结案诉讼在结案状态明确时返回`not_applicable`；监管处罚及合规事项还必须明确已整改，许可事项还必须明确牌照影响已经消除；
5. 重大性或结案状态不清时返回`needs_review`；处罚整改状态不清或核心牌照影响不清也进入`needs_review`；金额和发生日期属于可选支持事实，未披露本身不阻塞明确重大未决事项；
6. Builder按“真实事项 → 重大性/影响 → 当前状态 → 候选完整性”执行，Evidence缺失、Evidence ID错误、状态冲突和LLM主动报告的不确定性始终优先进入复核；
7. Builder仅输出供Verifier核验的候选，不输出`verified`，也不自动判为`high`。

对应决策树为：

```text
发现真实事项？
├─ 否 → not_applicable
└─ 是
   └─ 是否重大或可能影响经营/牌照？
      ├─ 明确否 → not_applicable
      └─ 是/可能
         └─ 当前是否仍未解决？
            ├─ 是 → pending RiskItem，交Verifier核验
            ├─ 已结案/已整改/影响已消除 → not_applicable
            └─ 不确定 → needs_review
```

Legal Agent 使用归一化事实，经确定性规则转换为状态为 `pending/needs_review` 的 `RiskItem`。

- `redemption_rights`必须提取权利类型、权利主体、触发/终止条件、上市后是否持续及恢复条件；
- `material_litigation_compliance`必须提取事项类型、对手方或监管机构、当前状态、潜在影响和披露的重大性；
- Evidence 不足时不生成正式风险，记录 `evidence_not_found`、`extraction_failed`或`needs_review`诊断；
- 只有 Verifier 可以给出 `verified/rejected/needs_review`。

## 6. Retriever验收用例

1号实现查询族时至少覆盖：

1. 简体、繁体和英文同义词均能召回；
2. 权利有效、上市时终止、终止后可恢复三个状态案例排序正确；
3. 重大未决诉讼高于一般性诉讼风险提示；
4. 已结案、已和解、已整改片段可以召回且保留状态词；
5. 单独出现`license`、`tax`或`permit`不会获得最高排序；
6. 无匹配返回空列表；
7. 重复运行的排序和Evidence ID稳定；
8. 原文和物理页码可追溯；
9. 不破坏现有现金跑道Retriever回归；
10. 测试不访问真实外部API，也不使用2025盲测集调权重。
