# Roadmap

| 版本 | 目标 | 状态 |
| --- | --- | --- |
| v0.1.0 | 架构级 MVP | 已完成并发布 |
| v0.2.0 | 真实文档纵向闭环与赛事数据治理 | 代码和自动验收完成，待团队独立复跑、Tag与Release |
| v0.3.0 | Financial、Legal、Business真实Agent与多案例评测 | 范围已冻结，待v0.2正式发布后启动 |
| v0.4.0 | 市场数据与预测模型 | 计划中 |
| v0.5.0 | 评测体系与人工标注 | 计划中 |
| v1.0.0 | 正式参赛版本 | 计划中 |

## v0.2.0 范围

支持一份真实港股招股书：保留 PDF 页码，检索原文 Evidence，提取现金及经营活动现金流，
完成现金跑道 Calculation，并在 Streamlit 展示真实证据。Mock 模式与 v0.1.0 测试必须继续可用。

赛事数据治理已形成565份招股书manifest、555/10行情覆盖和562/3官方IPO主数据桥接。审核基线`fbeb279`的284项自动化测试、项目校验、赛事数据校验、编译检查与2410.HK真实E2E均已通过。

## v0.3.0 范围

- 三个真实专业Agent：Financial、Legal、Business；
- 八类正式风险：现金跑道、持续亏损、收入增长、客户集中度、供应商集中度、特殊股东权利、重大诉讼与合规、未商业化及核心产品依赖；
- 五至十份黄金案例、结构化诊断码、专用Verifier、Supervisor与`enhanced_v2`；
- 保留`mvp_v1`、Mock模式、v0.2回归及无API Key确定性运行能力；
- 不在v0.3训练市场预测模型，不使用2025盲测集调试。

完整计划见[PROJECT_MASTER_CHECKLIST.md](PROJECT_MASTER_CHECKLIST.md)。
