# 赛题来源与授权数据交接

状态：`SUPPLEMENTAL_PROVENANCE_ONLY`

本文把本机可确认、但不能随 Git 分发的赛题来源整理成可复用交接说明。它不替代 `V1_RELEASE_ACCEPTANCE.md`、`FINAL_SUBMISSION_STATUS.md` 或任何冻结 receipt，也不授权重新调参、打开 Validation 或读取 Blind outcome。

机器可读的脱敏清点记录位于：

```text
data/catalog/authorized_source_inventory_20260830.json
```

## 1. 赛题要求与仓库对应面

赛题原说明文档只保留哈希，不提交原文件。原文件包含联系人信息；本仓库仅保留以下去标识化需求映射。

| 赛题关注点 | 当前仓库对应面 |
|---|---|
| 长篇招股书解析、反幻觉、财务及非标准风险识别 | `PROJECT_SPEC.md`、`ARCHITECTURE.md`、Document Intelligence runtime |
| 法律合规、财务、市场情绪、最终决策的多智能体协作 | `ARCHITECTURE.md`、Agent Trace、Final Supervisor |
| 风险结论必须回到原文页码、段落与截图 | Evidence contract、`reports/v045_demo_bundle`、Evidence Viewer |
| 单案与批量报告、API、可交互界面 | canonical UI、API/report surface、`FRONTEND_JUDGE_FACING_HANDOFF.md` |
| 上市后 1D / 5D / 20D / 60D 验证，5D 高权重 | `ROLE_D_MODEL_DECISION.md`、Role-D receipt / handoff |
| M1 >= 80%、M2 >= 85%、Trace 100% | `COMPETITION_METRIC_PROTOCOL.md`、`V1_RELEASE_ACCEPTANCE.md` |

当前事实仍是：产品面已发布为 v1.0.0，但冻结的 Real-LLM Development 结果未达到项目 G2 门槛；本次数据交接不会把失败改写成通过。

## 2. 本机独有、但不能上传的原始来源

2026-08-30 的只读清点确认：

- 本机授权目录有 2020–2024 共 449 份招股书，合计 6,162,145,323 bytes；
- 年度数量为 138 / 88 / 87 / 63 / 73；
- 449 个相对路径、文件大小和 SHA-256 均与 `ipo_prospectus_manifest.csv` 一致，0 mismatch；
- 原始比赛容器还包含 2025 Blind 文档及原始市场 CSV；这些原始字节不进入 Git；
- `hkcompanyinfo.csv` 的 SHA-256 此前未写入 `v04_source_manifest.json`，本次已在独立 inventory 中补充，但未改动冻结 source manifest；
- 赛题 DOCX、原始 ZIP、PDF、CSV、Gold/Oracle、provider journal、`data/results` 和本地迭代目录均未上传。

这意味着本机真正独有的是“授权原始字节”，而团队可安全共享的目录、文件名、大小和哈希元数据已经得到补齐。

## 3. 团队成员如何复用授权数据

原始数据应通过赛事方或团队批准的受控存储单独取得，并放在仓库外。不要把个人绝对路径写进配置或提交记录。

历史招股书运行入口使用：

```powershell
$env:IPO_RISK_PROSPECTUS_ROOT = "<AUTHORIZED_PROSPECTUS_ROOT>"
```

完整比赛数据根目录的构建工具使用：

```powershell
$env:IPO_RISK_COMPETITION_DATA_ROOT = "<AUTHORIZED_FULL_COMPETITION_ROOT>"
```

只校验已提交 catalog，不读取原始数据：

```powershell
python scripts/validate_competition_data.py
```

在明确授权且拥有完整 565 案例根目录时，可附加校验源文件是否齐备：

```powershell
python scripts/validate_competition_data.py --data-root "<AUTHORIZED_FULL_COMPETITION_ROOT>"
```

仅有本机这份 2020–2024 的 449 案例子集时，带 `--data-root` 的完整校验会如实报告缺少 116 个 2025 Blind 文件。不得为了让命令变绿而在普通开发环境解包或复制 Blind。

## 4. 冻结期限制

- 不在当前 release branch 运行 `build_competition_manifest.py`；它会重写 catalog 和数据文档。
- 不上传原始 ZIP/PDF/CSV、API key、带原文片段的本地结果或 provider 请求/响应。
- 不使用 2024 Validation 做缺陷定位或调参。
- 不使用 2025 Blind 输入/outcome 做优化；本次清点没有读取 Blind 文档内容或 outcome，但历史 Blind 披露仍以 `COMPETITION_DATA_OVERVIEW.md` 为准。
- 不把 missing 值补零，不把 unavailable 通道解释为低风险。

## 5. 与 M1 可达性审计的关系

本机另有一项适合团队共享的纯治理结果：14 个 2022 案例存在 Catalog 中文版本与 Existing-Gold 英文证据版本的绑定差异。该结果不包含招股书原文，已整理为：

```text
docs/research/V046_ROLE_B_M1_REACHABILITY_PROOF.md
docs/research/v046_role_b_governance/m1_reachability_proof.json
```

它只解释冻结 Metric-v2 下的内部 G2 上限，不改变最终实测分数，也不授权在当前提交冻结后更换来源、修改 Gold 或继续调参。
