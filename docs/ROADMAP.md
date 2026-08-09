# Roadmap

| 版本 | 目标 | 状态 |
| --- | --- | --- |
| v0.1.0 | 架构级 MVP | 已完成并发布 |
| v0.2.0 | 真实文档纵向闭环与赛事数据治理 | 已完成并发布 |
| v0.3.0 | Financial、Legal、Business真实Agent与多案例评测 | IN PROGRESS — Gate A |
| v0.4.0 | 市场数据与预测模型 | 计划中 |
| v0.5.0 | 评测体系与人工标注 | 计划中 |
| v1.0.0 | 正式参赛版本 | 计划中 |

## v0.3.0 范围

- 三个真实专业Agent：Financial、Legal、Business；
- 八类正式风险：现金跑道、持续亏损、收入增长、客户集中度、供应商集中度、特殊股东权利、重大诉讼与合规、未商业化及核心产品依赖；
- 五至十份黄金案例、结构化诊断码、专用Verifier、Supervisor与`enhanced_v2`；
- 保留`mvp_v1`、Mock模式、v0.2回归及无API Key确定性运行能力；
- 不在v0.3训练市场预测模型，不使用2025盲测集调试。

完整计划见[PROJECT_MASTER_CHECKLIST.md](PROJECT_MASTER_CHECKLIST.md)。

## v0.3 当前路线

| Workstream | Status | Main evidence | Remaining gate |
| --- | --- | --- | --- |
| V3-1 Golden Cases | PARTIAL | 6个真实Financial案例、23行真实草稿已进入main | 第二人复核；补齐Legal/Business真实正负例 |
| V3-2 Catalog Provider | MERGED | PR #20 | 全局ComponentRegistry与共享Service集成 |
| V3-3 Retriever | COMPLETED / MERGED | PR #23 | 在复核后的真实黄金集上执行指标评测 |
| V3-4 LLMProvider | COMPLETED / MERGED | PR #24 | Legal/Business消费；可选安全外部smoke |
| V3-5 Financial core | MERGED / STANDALONE-READY | PR #22 | 共享Container/Workflow/Service集成与黄金复核 |
| V3-6 Legal | PENDING | `DisabledLegalAgent`仍为共享实现 | 两类风险最小闭环及真实正负例 |
| V3-7 Business | PENDING | `DisabledBusinessAgent`仍为共享实现 | `precommercial_product`最小闭环及真实正负例 |
| V3-8 Specialized Verifier | BLOCKED | Financial verifier模块已存在 | 等待Legal、Business最小闭环与关键金标复核 |
| V3-9 Supervisor / enhanced_v2 | PENDING | 稳定工作流仍为`mvp_v1` | 三Agent、Verifier和Catalog共享装配完成 |
| Real golden batch evaluation | PENDING | V3-10基础设施已由PR #20合并 | 复核后的真实黄金案例与共享工作流 |
| V3-11 UI / Report | PENDING | v0.2 UI仍可用 | `enhanced_v2` Service输出稳定 |
| V3-12 Hardening / Release | PENDING | 尚未启动 | 前述门槛全部完成 |

当前统一阶段为 **Gate A — Professional Agent Completion & Golden Review**。V3-8不得在Legal、Business最小闭环和关键黄金案例第二人复核前启动。
