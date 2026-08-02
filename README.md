# 港股 IPO 风险预警 MVP

这是面向“基于多智能体协同的港股 IPO 招股书解析与上市后风险预警”赛题的最小可运行版本。它先用**模拟数据 + 确定性规则**跑通：输入公司 → 三类 Agent → 证据链 → 5 日风险概率 → 人工复核标记。

不接入真实行情、招股书、LLM 或数据库，因而可在任意安装 Python 3.10+ 的环境运行；真实能力后续以替换模块的方式接入。

## 快速运行

```bash
python app.py
python app.py SIM-001
python -m unittest discover -s tests
```

## 当前模块与五人分工接口

| 负责人 | 当前 MVP 模块 | 后续替换目标 | 验收接口 |
| --- | --- | --- | --- |
| 1 总控/架构 | `risk_mvp/service.py` | 工作流编排、冲突仲裁、日志版本 | `evaluate(case) -> RiskReport` 保持兼容 |
| 2 文档法务 | `governance_agent` | PDF/OCR、法务规则、页码/bbox 证据 | `Evidence` 数据契约 |
| 3 财务穿透 | `financial_agent` | 表格抽取、单位统一、现金消耗与集中度 | `financial_score, evidence` |
| 4 市场量化 | `market_agent` | 点时行情、特征仓、校准概率模型 | `market_score` 和风险概率替换点 |
| 5 产品交付 | `app.py` | API、页面、报告下载、回归演示 | JSON 报告字段不破坏 |

## 共同契约

- `Evidence` 强制携带证据 ID、来源、页码、结论、风险类型、严重度、置信度和责任模块。
- `RiskReport` 是所有 UI/API/评测的唯一输出；字段增加可以，改名或删除需全员评审。
- 当前所有案例均位于 `data/simulated_ipo_cases.json`，明确为模拟数据，不得作为任何投资结论。

## 下一步最小升级顺序

1. 用 30 份真实招股书建立字段级金标和 PDF 页码证据。
2. 将 `data/` 替换为带 `available_at` 的点时数据集。
3. 用时间外切分验证基线模型，并替换 `service.py` 的演示概率公式。
4. 最后接入 Web 界面和 Agent/LLM；LLM 只负责检索与解释，不直接给最终概率。
