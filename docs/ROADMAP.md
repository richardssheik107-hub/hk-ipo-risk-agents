# Roadmap — 从当前状态到 Competition Ready

> 状态日期：`2026-08-28`
>
> 详细版：`COMPETITION_CLOSURE_PLAN.md`

当前还剩 **4 个实质工作流 + 2 个收尾阶段**。

## 当前数字

```text
B fixed-10 M1 = 23.33%
B fixed-10 M2 = 18.75%
B v0.4.6 forensic/ablation + Evidence auditor = implementation ready; measured closure pending
D frozen PR-F: Recall 4.35%, F1 7.69%, ROC-AUC 0.4246
D v2 candidate: Recall 52.17%, F1 42.11%, PR-AUC 0.3812, ROC-AUC 0.4875
D v2 promotion = pending A review
C strict Market contract = 1/3
E real-provider accepted = 2/3
M3 = 3/3 exactly 1.0
M4 = 0/6
```

## 阶段 1 — B 全链路取证

- 跑通 matching structured smoke；
- 同一运行比较 offline / shadow / gated；
- 复用 read-only Evidence auditor检查 Evidence ID、页码、文本、Calculation、Index 与 provenance；
- 补齐 parser、retrieval、LLM、builder、reconciliation、verifier、binding lifecycle trace；
- 逐 Risk Unit / Evidence Unit 定位最早失败阶段；
- 形成按可恢复单元数排序的修复优先级。

完成标准：至少 90% 单元有 `PROVEN` 根因，且下一修复点唯一明确。

## 阶段 2 — B 指标与 Full Development

- 允许通用 Retriever、Prompt、Schema、non-destructive merge、reconciliation、Verifier 修复；
- 每个修复包必须有测试和消融；
- fixed-10 只是快速反馈，不设固定迭代次数；
- 达标后运行 ALL 79 Development 并冻结。

完成标准：

```text
M1 >=0.80
M2 >=0.85
real_llm_cases = 79
Validation=false
Blind input/outcome not used for optimization
```

## 阶段 3 — D / C / E 并行闭环

### D

- A 审核 frozen PR-F 与 v2 candidate；
- 若晋升 v2，创建 freeze/decision record，禁止再用 2024 调参；
- current-main strict revalidation；
- resume / fresh-directory determinism；
- final-three label-free handoff；
- 给出准确的业务价值和局限。

### C / E

- Market strict observation contract 3/3；
- Final Supervisor real-provider accepted 3/3；
- M3 保持 1.0；
- M4 完成 6 份独立真人评审。

## 阶段 4 — 赛题能力与产品交付

- 核心管线进度案例；
- 文本粉饰度切片案例；
- 关联交易案例；
- 同行估值比对 Skill 或可审计替代；
- Evidence bbox / 精确高亮截图；
- 单家与批量报告、API/UI 人机复核；
- 三个典型案例的演示脚本和静态备份。

无正式 Gold 时作为 qualitative capability demonstration，不混入 M1/M2。

## 阶段 5 — Freeze 与一次性 Validation

- 冻结 B 代码、Prompt、Retriever、Schema、Verifier、Evaluator；
- 冻结 D 正式模型与 alert policy；
- one-shot ALL 19 Validation；
- D/C/E final artifact 固化；
- latest-main CI；
- Blind、provenance、determinism、security 审计。

Validation 之后不再调参。

## 阶段 6 — Submission

- 源码与环境配置；
- 可运行原型或 API；
- 测试集预测表；
- Agent Trace；
- Evidence 与截图；
- 典型案例报告；
- 指标总表与 artifact index；
- 安全通过的 ZIP 和 SHA-256 manifest。

## 去掉的旧限制

- 固定最多 2–4 轮；
- Runner-only；
- Codex 只能看两个 summary；
- 全面禁止 Retriever / model / transport 对照；
- Evidence screenshot 只是 optional P2。

## 保留的硬边界

- Gold 不改、不泄漏；
- Validation 不调参；
- 2025 Blind 不用于后续优化；
- Evidence / Trace / PIT / Calculation fail closed；
- 无公司、case、页码特判；
- 无 Secret、PDF、raw EOD、绝对路径进入 Git 或 bundle。

## Competition Ready

只有 M1、M2、M3、M4、M5、Market、Final Supervisor、产品交付、one-shot Validation、CI 和 final package 全部真实通过，才能标记 `COMPETITION_READY`。
