# 公共数据Schema设计

## 1. 设计原则

所有跨模块数据必须通过Pydantic模型传递。

禁止不同模块自行定义含义相近但字段不同的字典。

公共Schema应满足：

1. 字段含义明确；
2. 类型明确；
3. 支持校验；
4. 支持序列化；
5. 支持版本管理；
6. 尽量向后兼容；
7. 新增字段应优先提供默认值。

## 2. DocumentChunk

表示PDF解析后的一个文档片段。

字段：

* document_id: 文档唯一标识；
* chunk_id: 文档片段唯一标识；
* page: PDF页码；
* section: 所属章节；
* text: 文本内容；
* block_type: text、table、title或其他类型；
* bbox: 文本在页面中的坐标；
* metadata: 其他扩展信息。

建议约束：

1. page必须大于等于1；
2. text不能为空；
3. chunk_id在同一文档中唯一；
4. bbox允许为空；
5. metadata默认为空字典。

## 3. Evidence

表示支持风险结论的证据。

字段：

* evidence_id: 证据唯一标识；
* document_id: 来源文档；
* chunk_id: 来源片段；
* page: PDF页码；
* section: 所属章节；
* text: 原文内容；
* bbox: 页面坐标；
* source_type: prospectus、market_data、ipo_data或calculation；
* relevance_score: 证据与风险的相关性；
* metadata: 扩展信息。

## 4. Calculation

表示风险结论中的确定性计算过程。

字段：

* skill_name: 使用的Skill；
* skill_version: Skill版本；
* inputs: 输入数据；
* formula: 计算公式；
* result: 计算结果；
* unit: 单位；
* evidence_ids: 输入数据对应的证据；
* success: 是否计算成功；
* error: 错误信息。

## 5. RiskItem

表示一个Agent识别出的风险。

字段：

* risk_id: 风险实例唯一标识；
* risk_code: 标准风险代码；
* category: financial、legal、business或market；
* risk_type: 风险名称；
* level: low、medium、high或critical；
* score: 0到100的风险分；
* conclusion: 风险结论；
* evidence: Evidence列表；
* calculation: Calculation或空值；
* agent_name: 生成该风险的Agent；
* confidence: 0到1的置信度；
* verification_status: pending、verified、rejected或needs_review；
* verification_notes: 核验说明；
* created_at: 创建时间；
* metadata: 扩展信息。

## 6. AgentLog

表示Agent或Skill的执行记录。

字段：

* log_id: 日志唯一标识；
* task_id: 分析任务ID；
* step: 执行顺序；
* agent_name: Agent名称；
* action: 执行动作；
* tool_name: 调用的Skill或工具；
* status: started、success、failed或skipped；
* input_summary: 输入摘要；
* output_summary: 输出摘要；
* evidence_ids: 使用的证据ID；
* error: 错误信息；
* started_at: 开始时间；
* finished_at: 结束时间；
* duration_ms: 执行耗时；
* metadata: 扩展信息。

## 7. RiskFactor

表示影响预测结果的一个因素。

字段：

* feature_name: 特征名称；
* feature_value: 特征值；
* contribution: 对风险的贡献；
* direction: increase或decrease；
* explanation: 解释；
* source: feature、risk_item或market_data。

## 8. PredictionResult

表示上市后风险预测结果。

字段：

* model_name: 模型名称；
* model_version: 模型版本；
* target: 预测目标；
* risk_score: 0到100的风险分；
* risk_level: low、medium、high或critical；
* probabilities: 各类别概率；
* top_factors: RiskFactor列表；
* explanation: 模型解释；
* feature_snapshot: 本次使用的特征；
* created_at: 创建时间；
* metadata: 扩展信息。

第一阶段的target建议为：

```text
five_day_significant_decline_risk
```

第一阶段RuleBasedPredictor输出的是风险评分，不应直接描述为经过校准的真实概率。

## 9. MarketSnapshot

表示上市前的市场环境。

字段：

* observation_date: 观察日期；
* hsi_return_5d: 恒生指数五日收益；
* hsi_return_20d: 恒生指数二十日收益；
* industry_return_5d: 行业五日收益；
* industry_return_20d: 行业二十日收益；
* recent_ipo_break_rate: 近期IPO破发率；
* recent_ipo_return_5d: 近期IPO五日平均收益；
* market_turnover: 市场成交额；
* market_volatility: 市场波动率；
* sentiment_score: 市场情绪分；
* source: 数据来源；
* metadata: 扩展信息。

## 10. IPOAnalysisRequest

表示一次完整分析请求。

字段：

* request_id: 请求唯一标识；
* company_name: 公司名称；
* stock_code: 股票代码；
* listing_date: 上市日期；
* prospectus_path: 招股书路径；
* workflow_version: 工作流版本；
* parser_name: Parser实现；
* predictor_name: Predictor实现；
* market_snapshot: MarketSnapshot或空值；
* use_mock: 是否使用Mock；
* options: 其他配置；
* created_at: 创建时间。

## 11. ReportSection

表示最终报告中的一个章节。

字段：

* section_id: 章节ID；
* title: 标题；
* summary: 摘要；
* risks: RiskItem列表；
* evidence_ids: 关联证据；
* order: 展示顺序；
* metadata: 扩展信息。

## 12. IPOAnalysisResult

表示完整分析结果。

字段：

* analysis_id: 分析任务ID；
* request_id: 请求ID；
* company_name: 公司名称；
* stock_code: 股票代码；
* workflow_version: 工作流版本；
* schema_version: Schema版本；
* verified_risks: 已核验RiskItem列表；
* pending_risks: 待核验RiskItem列表；
* rejected_risks: 被拒绝RiskItem列表；
* prediction: PredictionResult；
* agent_logs: AgentLog列表；
* report_sections: ReportSection列表；
* status: pending、running、completed、partial或failed；
* errors: 错误信息列表；
* started_at: 开始时间；
* finished_at: 完成时间；
* metadata: 扩展信息。

## 13. SkillResult

表示Skill执行结果。

字段：

* skill_name: Skill名称；
* skill_version: Skill版本；
* success: 是否成功；
* value: 返回值；
* evidence_ids: 使用的证据；
* error: 错误信息；
* metadata: 扩展信息。

## 14. 兼容性要求

1. 公共字段不得随意重命名；
2. 删除字段前必须进行版本升级；
3. 新增字段应尽量提供默认值；
4. 所有跨模块结果必须经过Pydantic校验；
5. Repository保存结果时必须记录schema_version；
6. Mock实现和真实实现必须使用相同Schema；
7. 测试必须验证Schema兼容性。

## 15. 补充Schema

### AnalysisError

表示一次可追踪的结构化失败，字段包括stage、component、code、message、recoverable、context和occurred_at。

### DocumentParseRequest

表示Parser输入，字段包括document_id、prospectus_path和options。

### IPOProfile

表示IPO基础信息，字段包括company_name、stock_code、listing_date、industry、issue_price、issue_size和metadata。

### ReportContext

表示ReportGenerator输入，只包含analysis_id、IPOProfile、三类风险列表、PredictionResult、日志摘要和选项。

### VerificationResult 与 SupervisionResult

VerificationResult 将风险分为 verified_risks、pending_risks 和 rejected_risks；
SupervisionResult 返回去重后的 verified_risks 及摘要。它们分别是 Verifier 与
Supervisor 的结构化输入输出边界，同时保持 IPOAnalysisResult 的对外结构兼容。

## 16. 当前契约与降级语义

风险是否需要 Evidence 或 Calculation 由 domain 风险注册表定义，包含
requires_evidence 与 requires_calculation 元数据；不得通过解析 conclusion 中是否出现
数字来判断。

对于 requires_evidence 的风险，Evidence 为空时不得进入 verified_risks。对于
requires_calculation 的风险，Calculation 缺失、失败，或其 evidence_ids 不能引用该风险
的 Evidence 时，不得进入 verified_risks。规则型、条款型风险不因没有 Calculation 而被
拒绝。

IPOAnalysisResult.status 可为 partial：表示部分节点失败但结果仍可返回。
预测失败时 prediction 允许为空；报告生成失败时 report_sections 允许为空；两类失败均必须
在 errors 中记录结构化 AnalysisError，并在 agent_logs 中记录失败日志。

---
