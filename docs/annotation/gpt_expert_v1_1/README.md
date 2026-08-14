# GPT Expert v1.1 Blind Annotation Workspace

这是 Git tracked 的盲标协作目录，只包含协议、空白模板、Case 身份和分工状态。

当前状态：Phase 0.6B.1 Expert Golden 100 taskset finalized。尚未开始 Phase 0.6C
实际标注。

## 安全边界

本目录不包含：原始 PDF、本地绝对路径、Human Golden、Human review working files、
Retriever/Agent 输出、真实 LLM baseline 原始结果、第一轮 2410 GPT 答案或任何旧
Golden label/page。

正式任务集为 `expert_golden_100_v1`：100 家公司、800 个风险检查任务，按
2020—2024 每年 20 家固定分布。2020—2023 为 development，2024 包含 19 家
locked validation 和 2410.HK development exception。每个空白 JSON 覆盖全部
8 个 active risk codes，所有判断字段为空。

## 使用入口

1. 阅读 [GPT_EXPERT_ANNOTATION_PROTOCOL.md](GPT_EXPERT_ANNOTATION_PROTOCOL.md)；
2. 阅读 [PRIMARY_BLIND_ANNOTATION_PROMPT.md](PRIMARY_BLIND_ANNOTATION_PROMPT.md)
   和 [TEAM_ANNOTATION_WORKFLOW.md](TEAM_ANNOTATION_WORKFLOW.md)；
3. 在 [team_case_assignment.csv](team_case_assignment.csv) 中领取 Case；
4. 从本地赛事数据按 [source_manifest.csv](source_manifest.csv) 的 SHA 定位 PDF；
5. 使用对应 `case_packets/<case_id>/blank_annotation.json`；
6. 通过 importer 将原始 JSON 和独立验证记录保存到本地被忽略的 results 目录；
7. 只在 `annotation/gpt-expert-results` 结果分支保存答案，不把答案提交到本分支。

结果目录、不可覆盖规则和分支边界详见
[RESULT_STORAGE_POLICY.md](RESULT_STORAGE_POLICY.md)。Git 分支不是访问控制；同一仓库成员
仍可能主动查看结果分支。严格盲法要求未完成 Primary Pass 的成员不访问结果分支，或将
结果迁移到具有独立权限控制的私有存储。

第一轮 2410 结果状态为 `PILOT_DIAGNOSTIC_ONLY`，未放入本目录。

Document Expert Label 与 Market Outcome Label 严格分离。上市日以及 5/20/60 日
收益属于未来 Market Outcome Labels，不得向 Primary Annotator 提供，也不得用于
反向决定招股书事实标签，以避免 outcome leakage、label contamination 和
confirmation bias。

`2025_BLIND_ACCESSED = false`

`2025_BLIND_USED = false`

`DO_NOT_AUTO_ANNOTATE = true`

`DO_NOT_USE_CODEX_AS_GOLD_REVIEWER = true`
