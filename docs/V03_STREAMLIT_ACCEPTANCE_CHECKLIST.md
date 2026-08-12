# v0.3 Streamlit 页面验收清单

> 页面代码由技术负责人维护；业务/产品成员可按本表独立复跑。Streamlit 只能调用
> `IPOAnalysisService`，不得在页面内重新执行 Agent、核验或金融计算。

## 1. 产品入口与 IPO Profile

- [x] 页面标题为 `HK IPO Risk Agents`，有中英文证据驱动多 Agent 定位；
- [x] 支持公司名称、股票代码、上市日期、PDF 和运行模式输入；
- [x] 展示公司、代码、上市日期、行业、发行价、发行规模；
- [x] 展示数据来源、匹配状态和特殊证券类别；
- [x] 展示 PDF 页/Chunk 数、Parser error、workflow、runtime、LLM 和分析状态；
- [x] 缺失字段显示 `Unavailable`，不猜测。

## 2. Overall Dashboard

- [x] 展示 Overall Rule Score 与 Rule Level；
- [x] 分别展示 verified / needs_review / pending / rejected 数量；
- [x] 固定提示规则分不是概率或投资/法律建议；
- [x] 展示组件模式与运行结果。

## 3. 三专业域

- [x] Financial、Legal、Business 是三个独立 Tab；
- [x] 每个 Tab 展示 Agent 状态、风险总数和四种核验状态数量；
- [x] 每个 Tab 只消费属于该 domain 的 `RiskItem`；
- [x] 单域失败通过结构化错误/诊断展示，不阻塞其他域；
- [x] Legal/Business 明确提示 v0.3 severity 为 provisional。

## 4. Risk Card、Evidence 与 Calculation

- [x] Risk card 展示人类可读标题、risk_code、level、规则分、核验状态和结论；
- [x] 展示 `verification_notes`；
- [x] Evidence 可展开并展示稳定 ID、物理 PDF 页码和原文；
- [x] 无 Evidence 风险明确提示不能视为 verified；
- [x] Calculation 展示 formula、inputs、result、unit 和 evidence_ids；
- [x] 结构化事实、期间和诊断 metadata 可展开查看。

## 5. Supervisor 与诊断

- [x] Supervisor 有独立 Tab；
- [x] 展示跨域 summary、duplicate groups、conflicts、composite findings；
- [x] 展示确定性 rule-score components；
- [x] 运行诊断展示 configuration、component status、governance、errors、Agent logs；
- [x] `needs_review` 与失败信息不会被静默隐藏。

## 6. 下载与报告

- [x] 支持完整 Markdown 报告下载；
- [x] 支持完整结构化 JSON 下载；
- [x] v0.3 Markdown/JSON 保留十章报告、风险、Evidence、Calculation、Verifier、
  Supervisor 和结构化 metadata；
- [x] 文件名经过安全规范化，不包含本地路径。

## 7. 运行模式

- [x] Mock 可无 PDF、无网络运行；
- [x] v0.2 real slice 可运行；
- [x] v0.3 offline 可在无 LLM 凭证下运行；
- [x] v0.3 AI 配置缺少凭证时安全降级；
- [x] Predictor 故障场景返回 partial，不使页面崩溃。

## 8. 本轮验收记录（2026-08-12）

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| Presenter / UI architecture tests | PASS | UI 只通过 Service 边界；Presenter JSON 可序列化 |
| 浏览器 Mock smoke | PASS | 3 verified、1 pending；三域页签与诊断可见 |
| 浏览器 v0.3 offline + 2410 PDF | PASS | completed、90/critical、十章报告、Supervisor 可见 |
| v0.2 真实回归 | PASS | 706、0 errors、563/562、2.76、verified、90/critical |
| v0.3 offline Service E2E | PASS | completed、10 sections、Supervisor present |
| v0.3 AI no-credentials degradation | PASS | `credentials_unavailable`、completed、无网络依赖 |
| PDF report | OUT OF SCOPE | v0.3 提供 Markdown 与 JSON |

页面人工验收完成不代表 Financial/Business Human Golden 二审完成；二者仍按 Owner
waiver 延期，不能用于正式跨域 Golden 指标声明。
