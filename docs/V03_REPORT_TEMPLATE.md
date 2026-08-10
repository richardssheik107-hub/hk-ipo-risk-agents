# v0.3 IPO 风险分析报告模板（5号设计）

> 5号负责报告结构设计，1号负责 ReportGenerator 实现。
> 报告章节顺序固定，任何实现不得删减章节；无内容的章节必须显式标注"无"。

---

# {公司名称}（{股票代码}）IPO 风险分析报告

生成时间：{timestamp}　｜　代码版本：{git_sha}　｜　配置版本：{config_version}

> 本报告所有分数为确定性规则分，不是上市后下跌概率，不构成投资建议。

## 1. 公司与 IPO 基础信息

| 字段 | 值 | 来源 |
| --- | --- | --- |
| 公司名称 | | |
| 股票代码 | | |
| 上市日期 | | |
| 行业 | | |
| 最终发行价 | | |
| 募集/净募集资金 | | |
| 上市板块 | | |
| 证券类型 | | （REIT / SPAC 权证等特殊证券须在此标注） |
| 数据匹配状态 | | |

## 2. 系统运行状态

| 组件 | 模式（mock/real/unavailable） | 状态 |
| --- | --- | --- |
| DocumentParser | | |
| Retriever | | |
| Financial Agent | | |
| Legal Agent | | |
| Business Agent | | |
| Verifier | | |
| Supervisor | | |
| Predictor | | |
| LLMProvider | | （无 API 时降级模式须显式标注） |

## 3. 财务风险（Financial Agent）

每条风险按以下结构展示：

### 3.x {risk_code} — {level}（规则分 {score}）

- 结论：{conclusion}
- Verifier 状态：{verification_status} — {verification_notes}
- Calculation：公式 {formula}；输入 {inputs}；结果 {result}；单位 {unit}；报告期 {period}
- Evidence：
  - [{evidence_id}] 第 {page} 页：{原文}

覆盖风险码：cash_runway、continuous_loss、revenue_growth、customer_concentration、supplier_concentration。

## 4. 法律风险（Legal Agent）

结构同第 3 节。覆盖风险码：redemption_rights、material_litigation_compliance。

- 必须区分：历史上存在 vs 上市后仍有效；已终止/已整改事项不得表述为当前风险
- v0.3 法律风险等级为 provisional medium，不得表述为 high/critical

## 5. 业务风险（Business Agent）

结构同第 3 节。覆盖风险码：precommercial_product。

- 必须区分：产品销售收入 vs 授权/里程碑/研发服务等非产品收入
- 必须展示：核心产品名称、研发阶段、商业化状态、合作方依赖事实
- v0.3 业务风险等级为 provisional medium

## 6. 多 Agent 综合摘要（Supervisor）

- 重复风险合并说明
- 跨 Agent 冲突识别（含"不冲突"的明确说明，如授权收入 vs 未商业化）
- 相互支持的风险组合
- verified 与 needs_review 分层汇总

## 7. Evidence 索引

| Evidence ID | 页码 | 所属风险 | 摘要 |
| --- | --- | --- | --- |

## 8. Calculation 索引

| Calculation | 公式 | 输入来源 Evidence | 结果 | 所属风险 |
| --- | --- | --- | --- | --- |

## 9. 待人工复核事项

| 事项 | Agent | 诊断码 | 原因 | 相关 Evidence |
| --- | --- | --- | --- | --- |

诊断码范围：not_applicable / evidence_not_found / extraction_failed /
conflicting_values / unsupported_layout / needs_review / component_failure。

## 10. 已知限制

- 确定性提取依赖关键词检索，非常规版式可能漏检并降级为 needs_review
- v0.3 业务与法律风险等级为 provisional，不做高等级自动升级
- 规则分不是概率，不构成投资建议
- {运行时追加的其他限制}

---

## 附：演示案例要求（5号）

正式发布前至少准备两个演示案例：

1. **正例**：18A 未商业化生物科技公司（如 1167.HK 加科思），展示
   precommercial_product 从 Evidence → 提取 → 规则 → Verifier 的完整链路；
2. **负例**：已商业化公司（如 9633.HK 農夫山泉），展示"已商业化 →
   not_applicable 不生成风险"，以及授权收入不被误判为产品销售收入。
