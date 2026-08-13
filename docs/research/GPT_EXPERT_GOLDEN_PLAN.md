# GPT Expert Golden 重建计划

## 状态

- 研究版本：`v0.3.5-evidence-intelligence`
- 当前阶段：Phase 0.6B — Protocol Hardening + Collaboration Setup
- v0.3：Released / Frozen
- v0.4：Not Started

## 为什么先重建 Golden

Phase 0.5 的真实 Responses API 基线已经完成。真实 API、2410.HK gate 和
14-case A/B 均完成；Precision 改善，但 Risk Recall 没有改善，Evidence
Recall@3 仍然偏低。静态共享检索覆盖是主要瓶颈，LLM 抽取/运行稳定性是次要
瓶颈，Legal downstream verifier 也是额外瓶颈。

进一步审查发现，现有 Human Golden 还混合了 risk instance 与 evidence row，
并存在 evidence role、主证据权威性和评测语义不一致。因此当前暂停直接调优
Retriever，先建立可审计的 Expert Golden v2。

## 方法

```text
Original Prospectus
        -> GPT Expert Blind Annotation
        -> Deterministic Validation
        -> Independent GPT Audit / Second Pass
        -> Conflict Detection
        -> Selective Human Adjudication
        -> Expert Golden v2
```

GPT Expert 是高能力 evidence investigator，负责全文证据发现、语义理解、事实
抽取、缺失事实和冲突识别；确定性层负责会计定义、可比期间、Calculation、阈值、
severity 和状态一致性。GPT 输出本身不等于 Golden。

## 阶段

| 阶段 | 目标 | 状态 |
|---|---|---|
| Phase 0.6A | 三案例盲包、evaluation-only schema、validator、importer | COMPLETED |
| Phase 0.6B | Protocol v1.1 加固、14-case 安全协作材料 | CURRENT |
| Phase 0.6C | 2410 Financial、2517 Legal、1167 Business 三案例 Pilot | NOT STARTED |
| Phase 0.6D | Risk/Evidence/relationship/calculation/confidence/policy provenance Golden v2 | NOT STARTED |

第一轮 2410 GPT 输出仅为 `PILOT_DIAGNOSTIC_ONLY`，用于发现协议问题，不进入
共享盲包、Retriever 调优目标或 canonical Expert Golden。

## 数据隔离

- 只使用 `development` 与 `development_exception`；
- 不向 annotator 提供 Human Golden、旧评测、Retriever 或 Agent 输出；
- 每个新 ChatGPT 对话只处理一个 Case；
- 2025 blind 不访问、不使用；
- 原始 PDF 和 GPT answer 不提交 Git。

## 完成条件

Phase 0.6D 只有在 deterministic validation、独立 audit、冲突识别和必要的人类
仲裁完成后，才能宣布 Expert Golden v2 建立。未解决政策见
[EXPERT_GOLDEN_OPEN_POLICY_ITEMS.md](EXPERT_GOLDEN_OPEN_POLICY_ITEMS.md)。
