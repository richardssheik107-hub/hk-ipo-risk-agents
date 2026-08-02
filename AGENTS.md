# Codex与团队开发规则

## 1. 项目目标

本项目构建一个基于证据驱动多智能体协同的港股IPO招股书解析与上市后风险预警系统。

当前第一阶段的目标是完成架构级MVP。

架构级MVP要求：

1. 模块边界清晰；
2. 公共接口稳定；
3. Mock流程可运行；
4. 后续真实模块可替换；
5. 项目支持五人并行开发；
6. 不依赖单个大型Python文件。

## 2. 开始任务前

执行任何代码任务前必须：

1. 阅读docs/PROJECT_SPEC.md；
2. 阅读docs/ARCHITECTURE.md；
3. 阅读docs/DATA_SCHEMA.md；
4. 阅读本AGENTS.md；
5. 检查当前仓库结构；
6. 检查现有测试；
7. 说明准备修改的文件；
8. 说明是否影响公共接口。

面对较大任务时，先提交实施计划，再开始编码。

## 3. 架构规则

1. 采用模块化单体架构；
2. 不建立微服务；
3. 不引入Kafka；
4. 不引入Redis任务队列；
5. 不引入Neo4j；
6. 不引入Kubernetes；
7. 不引入与当前阶段无关的复杂基础设施；
8. 不得将主要业务逻辑集中在app.py或streamlit_app.py；
9. 前端只能调用IPOAnalysisService；
10. Agent不得直接操作前端；
11. Parser不得依赖Agent；
12. Skill不得依赖Agent；
13. schemas不得依赖具体业务实现。

## 4. 公共接口

以下内容属于公共接口，修改前必须明确说明影响：

```text
src/ipo_risk/schemas/
src/ipo_risk/agents/base.py
src/ipo_risk/parsers/base.py
src/ipo_risk/retrieval/base.py
src/ipo_risk/predictors/base.py
src/ipo_risk/providers/
src/ipo_risk/workflows/state.py
src/ipo_risk/services/analysis_service.py
```

未经明确任务要求，不得随意：

1. 重命名公共字段；
2. 删除公共字段；
3. 改变字段含义；
4. 改变Agent统一返回类型；
5. 改变Parser统一返回类型；
6. 改变Predictor统一返回类型。

## 5. Schema规则

1. 所有跨模块数据使用Pydantic模型；
2. Parser返回list[DocumentChunk]；
3. Retriever返回Evidence或DocumentChunk；
4. 专业Agent返回list[RiskItem]；
5. Predictor返回PredictionResult；
6. AnalysisService返回IPOAnalysisResult；
7. Skill返回SkillResult或明确的Pydantic结果；
8. 禁止使用结构不稳定的任意字典作为公共接口。

## 6. Agent规则

1. 所有专业Agent实现统一RiskAgent接口；
2. Agent必须具有明确职责；
3. Agent不得自行定义公共Schema；
4. Agent不得直接修改数据库；
5. Agent不得直接调用Streamlit；
6. Agent不得使用LLM完成精确金融计算；
7. Agent不得将无证据结论标记为verified；
8. Agent发生错误时必须写入AgentLog；
9. 不确定风险应标记为pending或needs_review；
10. 新增Agent必须增加契约测试。

## 7. Skill规则

1. 精确金融计算必须放入skills模块；
2. Skill应尽量使用纯Python确定性实现；
3. Skill必须可独立测试；
4. Skill必须处理缺失值；
5. Skill不得静默吞掉错误；
6. Skill输入中的关键数据应关联Evidence；
7. Skill结果必须记录版本；
8. 新增Skill必须增加单元测试。

## 8. Evidence规则

1. 所有正式风险必须有Evidence；
2. Evidence必须包含页码和原文；
3. 包含具体数字的结论必须具有Calculation；
4. Calculation必须说明输入、公式、结果和单位；
5. 无Evidence风险进入pending_risks；
6. Verifier可以将风险标记为verified、rejected或needs_review；
7. 不得使用不存在的页码或虚构原文。

## 9. 前端规则

Streamlit只能：

1. 构造IPOAnalysisRequest；
2. 调用IPOAnalysisService；
3. 展示IPOAnalysisResult；
4. 展示错误信息。

Streamlit不得：

1. 直接调用LLM；
2. 直接调用Agent；
3. 直接解析PDF；
4. 直接访问Repository；
5. 直接运行Predictor；
6. 直接进行财务计算。

## 10. 配置和敏感信息

1. API Key只能通过环境变量读取；
2. 不得提交.env；
3. 必须提供.env.example；
4. 不得提交密码；
5. 不得提交Token；
6. 不得提交用户本地绝对路径；
7. 模型名称和Provider通过配置管理；
8. Mock和真实实现通过配置切换。

## 11. 代码质量

1. 使用类型标注；
2. 公共函数添加简短docstring；
3. 使用清晰的模块名；
4. 避免循环依赖；
5. 对文件、模型和网络调用增加异常处理；
6. 不得通过except Exception后完全忽略错误；
7. 日志中不得泄漏敏感信息；
8. 避免无必要的全局变量；
9. 避免在导入阶段执行耗时操作；
10. 保持函数职责单一。

## 12. 测试要求

项目测试至少包括：

1. Schema测试；
2. Skill单元测试；
3. Agent契约测试；
4. Parser契约测试；
5. Predictor契约测试；
6. Service集成测试；
7. Mock端到端测试；
8. 黄金案例回归测试。

提交代码前必须运行相关测试。

如果仓库已配置完整测试命令，应运行完整测试。

不得：

1. 删除有效测试；
2. 弱化断言以掩盖问题；
3. 修改预期结果来迁就错误实现；
4. 声称测试通过但未执行测试。

## 13. 修改任务的标准流程

每次任务应遵循：

1. 阅读规格文件；
2. 检查现有实现；
3. 提交修改计划；
4. 列出新增和修改文件；
5. 实现最小必要修改；
6. 添加或更新测试；
7. 运行测试；
8. 修复失败；
9. 总结修改内容；
10. 列出剩余限制。

## 14. Git规则

1. 不直接向main提交未经测试的代码；
2. 每个功能使用独立分支；
3. Commit信息应说明修改内容；
4. Pull Request应说明测试结果；
5. 公共Schema修改必须由组长审核；
6. 不提交大型原始PDF和敏感数据；
7. 不提交模型缓存和临时文件；
8. 不自动执行git push，除非用户明确要求；
9. 不自动创建Pull Request，除非用户明确要求；
10. 不自动提交Commit，除非用户明确要求。

## 15. 完成任务后的汇报格式

完成代码任务后必须说明：

1. 创建了哪些文件；
2. 修改了哪些文件；
3. 实现了哪些功能；
4. 是否改变公共接口；
5. 运行了哪些测试；
6. 测试结果；
7. 如何启动；
8. 当前仍使用哪些Mock模块；
9. 已知限制；
10. 下一阶段建议。

