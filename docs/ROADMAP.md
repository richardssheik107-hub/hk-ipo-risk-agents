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

完整计划见[PROJECT_MASTER_CHECKLIST.md](PROJECT_MASTER_CHECKLIST.md)，当前Gate A强制门槛见[V03_GATE_A_CLOSEOUT.md](V03_GATE_A_CLOSEOUT.md)。

## v0.3 当前路线

| Workstream | Status | Main evidence | Remaining gate |
| --- | --- | --- | --- |
| V3-1 Golden Cases | PARTIAL | canonical中已有Financial/Business真实draft；Legal A—H为独立draft | 独立二审、Legal仲裁与canonical并表 |
| V3-2 Catalog Provider | MERGED / INTEGRATION-PENDING | PR #20 | 全局ComponentRegistry与共享Service集成 |
| V3-3 Retriever | COMPLETED / MERGED | PR #23 | 在复核后的真实黄金集上执行指标评测 |
| V3-4 LLMProvider | COMPLETED / MERGED | PR #24 | Legal domain prompt runtime routing；可选安全外部smoke |
| V3-5 Financial core | MERGED / STANDALONE-READY / GOLDEN-SECOND-REVIEW-PENDING / SHARED-INTEGRATION-PENDING | PR #22 | 真实金标二审与共享装配 |
| V3-6 Legal | MERGED / STANDALONE-READY / GATE-A-CLOSEOUT-PENDING / SHARED-INTEGRATION-PENDING | PR #26 | contract、severity、Retriever、runtime prompt、A—H复核与并表 |
| V3-7 Business | MERGED / STANDALONE-READY / GOLDEN-SECOND-REVIEW-PENDING / SHARED-INTEGRATION-PENDING | PR #28 | 三条真实Golden独立二审与共享装配 |
| V3-8 Specialized Verifier | BLOCKED BY GATE A | [Gate A收口验收表](V03_GATE_A_CLOSEOUT.md) | 全部mandatory Gate A criteria通过 |
| V3-9 Supervisor / enhanced_v2 | PENDING | 稳定工作流仍为`mvp_v1` | 三Agent、Verifier和Catalog共享装配完成 |
| Real golden batch evaluation | PENDING | V3-10基础设施已由PR #20合并 | 复核后的真实黄金案例与共享工作流 |
| V3-11 UI / Report | PENDING | v0.2 UI仍可用 | `enhanced_v2` Service输出稳定 |
| V3-12 Hardening / Release | PENDING | 尚未启动 | 前述门槛全部完成 |

当前统一阶段为 **Gate A — Professional Agent Completion & Golden Review**。三个专业Agent的standalone core均已进入`main`，但`standalone-ready`不等于共享集成完成。Financial与Business canonical draft已存在；Legal A—H仍需人工review、Case C adjudication及canonical merge。V3-8在全部mandatory Gate A criteria通过前不得启动。
