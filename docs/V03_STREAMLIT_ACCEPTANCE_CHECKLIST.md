# v0.3 Streamlit 页面验收清单（5号）

> 5号负责页面需求与人工验收，代码集成由1号负责。
> 本清单是 v0.3 发布前页面验收的唯一标准，逐项人工核对，
> 任何一项不通过即视为页面验收未完成。

## 1. IPO 基础信息

- [ ] 展示公司名称、股票代码、上市日期、行业、发行信息（来自 IPOProfile）
- [ ] 数据来源和匹配状态可见（catalog 匹配 / 手工输入 / 缺失）
- [ ] 特殊证券（REIT、SPAC 权证）有明确标记，不与普通股混同

## 2. 三个 Agent 页签

- [ ] 存在 Financial、Legal、Business 三个独立页签
- [ ] 每个页签只展示本 Agent 拥有的风险码：
  - Financial：cash_runway、continuous_loss、revenue_growth、customer_concentration、supplier_concentration
  - Legal：redemption_rights、material_litigation_compliance
  - Business：precommercial_product
- [ ] 每个页签展示 Agent 执行状态（completed / partial / failed / skipped）
- [ ] 单个 Agent 失败时页面仍正常渲染其他页签，不整页崩溃

## 3. 风险条目展示

- [ ] 每条风险展示风险码、风险等级（critical/high/medium/low）和规则分
- [ ] 规则分有固定提示：分数为确定性规则分，不是下跌概率，不构成投资建议
- [ ] verified、pending、needs_review、rejected 分层展示，不混在一起
- [ ] v0.3 中 Business 与 Legal 风险标注 provisional 等级（medium），不出现 high/critical

## 4. Evidence 展开（核心验收项）

- [ ] 每条风险均可展开查看全部 Evidence
- [ ] 每条 Evidence 展示物理 PDF 页码
- [ ] 每条 Evidence 展示原文完整上下文（不是截断片段）
- [ ] Evidence ID 稳定，同一页面多次运行结果一致
- [ ] 评委能从 Evidence 原文直接看出风险结论的来源

## 5. Calculation 展示

- [ ] 财务风险展示 Calculation：公式、输入、结果、单位、报告期
- [ ] Calculation 引用的 Evidence ID 与风险 Evidence 一致
- [ ] 不可比期间（季度对全年、3个月对6个月）明确进入 needs_review，不强行出数

## 6. Verifier 与诊断状态

- [ ] 每条风险展示 Verifier 状态与 verification_notes
- [ ] Agent 诊断区分展示：not_applicable / evidence_not_found / extraction_failed /
  conflicting_values / unsupported_layout / needs_review / component_failure
- [ ] needs_review 事项有独立汇总区域，不被当作"没有风险"

## 7. 综合摘要与规则分

- [ ] 展示 Supervisor 综合摘要（重复风险、跨 Agent 冲突、相互支持风险）
- [ ] 展示综合规则分的构成（哪些风险贡献了分数），可追溯
- [ ] Financial "公司有收入" 与 Business "尚未商业化" 并存时不被误判为冲突

## 8. 下载

- [ ] 支持 JSON 或 Markdown 报告下载
- [ ] 下载内容包含报告模板（V03_REPORT_TEMPLATE.md）的全部章节

## 9. 运行模式

- [ ] Mock 演示模式可无 PDF、无网络运行
- [ ] 真实 PDF 模式可上传招股书并返回结果
- [ ] 无 LLM API 时系统降级运行并在页面可见降级状态

## 10. 当前差距记录（2026-08-10 5号自查）

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 三页签结构 | 未实现 | 当前页面为单页 JSON 堆叠，无 Financial/Legal/Business 页签 |
| Evidence 展开 | 部分 | JSON 中包含 evidence 字段，但无逐条展开交互 |
| Agent 页签级状态 | 未实现 | 仅展示整体 component_modes |
| 下载 | 未实现 | 无 JSON/Markdown 下载按钮 |
| Business Agent 接入 | 未实现 | V03BusinessAgent 尚未接入 Workflow/Service（1号集成任务） |

> 差距项均为 1号集成范围，5号负责在集成完成后按本清单逐项验收。
