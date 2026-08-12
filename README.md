# HK IPO Risk Agents

Evidence-backed multi-agent risk analysis for Hong Kong IPO prospectuses.

系统读取港股招股书 PDF，以共享 Evidence 为基础，协同运行 Financial、Legal、Business
三个专业 Agent，再由专用 Verifier、Supervisor 和确定性规则评分生成可审计报告。

> 输出中的分数是确定性规则分，不是下跌概率、上市失败概率或投资建议。

## 当前版本状态

```text
v0.2.0-real-document-slice = RELEASED
v0.3.0-multi-agent-risk-analysis = SOFTWARE COMPLETE / DEMO READY / RELEASE-READY
v0.3 Human Golden governance = PARTIAL (research-validation limitation)
v0.4 Market prediction work = NOT STARTED
```

v0.3 已完成真实 PDF、多专业 Agent、专用核验、跨域 Supervisor、`enhanced_v2`、
Service、Streamlit、Markdown/JSON 报告和故障降级。Financial 23 条与 Business 3 条
独立人工二审仍按 [Owner Waiver](docs/V03_OWNER_WAIVER_FOR_FINAL_TECHNICAL_COMPLETION.md)
延期，因此不声明正式跨域 Golden 指标；该限制不再阻塞软件版本验收。

稳定回退版本：[v0.2.0-real-document-slice](https://github.com/richardssheik107-hub/hk-ipo-risk-agents/releases/tag/v0.2.0-real-document-slice)。

## 产品能力

- PyMuPDF 按物理页解析真实招股书，保留繁简中文、英文、数字、括号、负号和单位；
- 财务、法务、业务简繁英查询族和稳定 Evidence ID；
- Financial：现金跑道、持续亏损、收入增长、客户集中度、供应商集中度；
- Legal：特殊股东权利、重大诉讼与合规；
- Business：未商业化及核心产品依赖；
- 金融计算由确定性 Python Skill 完成并关联 Evidence；
- 专用 Verifier 不允许无 Evidence 或缺少必要 Calculation 的风险进入 verified；
- Supervisor 去重、保留域所有权、识别语义冲突并输出跨域观察；
- `mvp_v1`、`enhanced_v2`、Mock、v0.2、v0.3 offline 和可选 AI 模式并存；
- Streamlit 展示 IPO Profile、总体规则分、三域风险、Evidence、Calculation、Verifier、
  Supervisor、诊断和结构化错误；
- 支持完整 Markdown 与 JSON 下载。

## 架构

```text
Prospectus PDF
      ↓
DocumentParser → DocumentChunk
      ↓
Shared DocumentRetriever → Evidence
      ↓
Financial Agent ─┐
Legal Agent ─────┼→ Specialized Verifier Router → V03 Supervisor
Business Agent ──┘                                  ↓
                                             RuleBasedPredictor
                                                     ↓
                                              V03 ReportGenerator
                                                     ↓
                                              IPOAnalysisService
                                                     ↓
                                     Streamlit / Markdown / JSON
```

项目采用模块化单体架构。Streamlit 只构造 `IPOAnalysisRequest`、调用
`IPOAnalysisService` 并展示 `IPOAnalysisResult`；不会直接调用 Agent、Parser、
Provider、Predictor 或 Repository。

## Quick Start

### Windows PowerShell

```powershell
python -m pip install -e ".[dev]"
$env:PYTHONPATH = "src"
pytest -q
python scripts/validate_project.py
start.bat
```

也可直接启动：

```powershell
$env:IPO_RISK_CONFIG = "configs/v03_offline.yaml"
python -m streamlit run app/streamlit_app.py
```

### Linux / macOS

```bash
python -m pip install -e '.[dev]'
export PYTHONPATH=src
pytest -q
python scripts/validate_project.py
./start.sh
```

也可直接启动：

```bash
export IPO_RISK_CONFIG=configs/v03_offline.yaml
python -m streamlit run app/streamlit_app.py
```

## 运行模式

| UI 场景 | 配置 | 网络/凭证 | 用途 |
| --- | --- | --- | --- |
| Mock architecture demo | `configs/mock.yaml` | 不需要 | 架构和降级演示 |
| v0.2 real cash-runway slice | `configs/real_pdf.yaml` | 不需要 | 2410.HK 现金跑道回归 |
| v0.3 enhanced offline | `configs/v03_offline.yaml` | 不需要 | 默认真实多 Agent 产品演示 |
| v0.3 enhanced AI | `configs/v03_ai.yaml` | 环境变量 | 可选结构化语义增强 |
| Predictor failure degradation | `configs/mock.yaml` | 不需要 | partial/错误日志演示 |

配置优先级：环境变量 `IPO_RISK_*` > `IPO_RISK_CONFIG` 指定的 YAML > 代码默认值。
密钥只允许来自环境变量；不得提交 `.env`、Token 或 API Key。AI 凭证不可用时会安全降级，
offline 路径仍完整可运行。

## 注册组件

- Parser：`mock`、`mock_alt`、`pymupdf`；
- Retriever：`mock`、`keyword`；
- Financial Agent：`mock`、`cash_runway`、`v03`；
- Legal Agent：`mock`、`disabled`、`v03`；
- Business Agent：`mock`、`disabled`、`v03`；
- Market Agent：`mock`、`disabled`；
- Verifier：`rule`、`specialized_v03`；
- Supervisor：`rule`、`v03`；
- Predictor：`rule_based`、`fault`；
- LLMProvider：`mock`、`openai_compatible`、`unavailable`；
- MarketDataProvider：`mock`、`unavailable`；
- IPODataProvider：`mock`、`request`、`catalog`；
- ReportGenerator：`mock`、`v03`；Repository：`json`。

## 风险结果如何理解

每条 `RiskItem` 包含风险码、域、等级、规则分、结论、Verification 状态和证据。

- `verified`：Evidence 与必需 Calculation 契约均通过；
- `needs_review`：证据、计算、语义或组件状态需要人工复核；
- `pending`：候选尚未完成正式核验；
- `rejected`：规则明确拒绝该候选。

含精确数字的风险会展示 `Calculation.inputs / formula / result / unit / evidence_ids`。
报告保留 PDF 物理页码和原文，便于逐条回查。

## 真实案例回归

本地放置 2410.HK 招股书后运行：

```powershell
$env:IPO_RISK_REAL_CASE_PDF = "data/local/real_case_001/prospectus.pdf"
python scripts/check_real_v02_e2e.py
```

```bash
export IPO_RISK_REAL_CASE_PDF=data/local/real_case_001/prospectus.pdf
python scripts/check_real_v02_e2e.py
```

冻结期望：706 个非空页/Chunk、0 个单页解析错误、现金页 563、经营现金流页 562、
现金跑道 2.76 个月、verified、规则分 90、critical。

## 方法与限制

- v0.3 是招股书证据驱动的文档风险系统，不包含市场收益预测；
- Market Agent、真实 MarketDataProvider、1/5/20/60 日标签、LightGBM、SHAP 和概率校准
  均属于 v0.4，当前未开始；
- 扫描型 PDF 的 OCR 和 PDF 格式报告导出不在本版范围；本版提供 Markdown/JSON；
- Financial/Business 正式人工 Golden 二审延期，不能据此宣称正式跨域准确率；
- 真实外部 LLM endpoint smoke 为可选项，未提供凭证时明确跳过；
- 2025 blind 数据未用于 Retriever、Prompt、规则或阈值调优。

## 项目文档

1. [项目主状态](docs/PROJECT_MASTER_CHECKLIST.md)
2. [项目规格](docs/PROJECT_SPEC.md)
3. [架构设计](docs/ARCHITECTURE.md)
4. [公共 Schema](docs/DATA_SCHEMA.md)
5. [Gate A / Golden 治理状态](docs/V03_GATE_A_CLOSEOUT.md)
6. [v0.3 页面验收](docs/V03_STREAMLIT_ACCEPTANCE_CHECKLIST.md)
7. [v0.3 报告模板](docs/V03_REPORT_TEMPLATE.md)
8. [版本路线](docs/ROADMAP.md)
9. [开发规则](AGENTS.md)

开发前必须阅读 `AGENTS.md`。公共 Schema、Protocol、WorkflowState 和
`IPOAnalysisService` 是受保护边界；本轮产品收口未改变这些公共接口。
