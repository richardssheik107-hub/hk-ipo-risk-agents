# GPT Expert v1.1 Blind Annotation Workspace

这是 Git tracked 的安全协作目录，只包含协议、空白模板、Case 身份和分工状态。

当前状态：Phase 0.6B collaboration setup。尚未开始 Phase 0.6C 实际标注。

## 安全边界

本目录不包含：原始 PDF、本地绝对路径、Human Golden、Human review working files、
Retriever/Agent 输出、真实 LLM baseline 原始结果、第一轮 2410 GPT 答案或任何旧
Golden label/page。

14 个 Case 均来自 `development` / `development_exception`，每个空白 JSON 覆盖
全部 8 个 active risk codes，所有判断字段为空。

## 使用入口

1. 阅读 [GPT_EXPERT_ANNOTATION_PROTOCOL.md](GPT_EXPERT_ANNOTATION_PROTOCOL.md)；
2. 阅读 [TEAM_ANNOTATION_WORKFLOW.md](TEAM_ANNOTATION_WORKFLOW.md)；
3. 在 [team_case_assignment.csv](team_case_assignment.csv) 中领取 Case；
4. 从本地赛事数据按 [source_manifest.csv](source_manifest.csv) 的 SHA 定位 PDF；
5. 使用对应 `case_packets/<case_id>/blank_annotation.json`；
6. 在本地运行 validator，验证通过后再通过 importer 保存到被忽略的 reports 目录。

第一轮 2410 结果状态为 `PILOT_DIAGNOSTIC_ONLY`，未放入本目录。

`2025_BLIND_ACCESSED = false`

`2025_BLIND_USED = false`
