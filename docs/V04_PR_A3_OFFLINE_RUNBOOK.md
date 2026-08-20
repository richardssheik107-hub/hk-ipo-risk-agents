# V04 PR-A3 Offline Runbook

本 Runbook 只用于 PR-A 的离线验证与后续 438-case 无人值守物化。它不启动
PR-B/PR-C/PR-D，不读取 2025 Blind outcome，也不允许 dirty source tree。

## 1. 冻结前提

执行前确认：

```powershell
git switch docs/v04-five-person-execution-plan-20260820
git pull --ff-only origin docs/v04-five-person-execution-plan-20260820
git status --short
python --version
```

工作区必须为空，Python 必须是项目已验证的 3.12 环境。`configs/v03_offline.yaml`
必须保持 `runtime_mode: offline` 与 `llm_provider: unavailable`。编排脚本和两个
runner 都会 fail closed；它们不会打印、保存或删除用户的系统级凭证。

## 2. Windows 长时间运行准备

- 电脑接通电源；
- 在 Windows 电源设置中临时把“睡眠”设为“从不”；
- 如启用了休眠，临时调整为不会在运行期间触发；
- 屏幕可以自动关闭，Python 进程仍会继续；
- 不依赖浏览器、Codex 或在线会话维持 worker；
- 本文只提供操作说明，runner 不会永久修改电源设置。

## 3. 真正断网的 3-case Smoke

固定案例：

- `ipo_2020_00368`：验证 reviewed Oracle；
- `ipo_2020_00589`、`ipo_2020_00873`：验证 `no_reviewed_gold`。

先联网完成依赖安装与 Git 同步，再关闭 Wi-Fi、Ethernet、VPN 和 hotspot。在普通
PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_v04_pr_a_offline_smoke.ps1 `
  -DataRoot "<LOCAL_PROSPECTUS_ROOT>"
```

runner 会自行完成首轮真实分析以及第二轮 `--resume --verify-determinism`。默认输出：

```text
reports/v04_pr_a_offline_smoke_<short_sha>/
reports/v04_pr_a_offline_smoke_<short_sha>_logs/
```

日志位于 output sibling，不会在首次 CLI 启动前污染 output directory。成功标准：

```text
selected = 3
Production materialized = 3
Oracle materialized = 1
Production failures = 0
determinism passed = true
mismatch_count = 0
coverage_hash_ok = true
```

## 4. 438-case 无人值守 runner（本阶段不要启动）

Owner 批准 A3 后才可运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_v04_pr_a_unattended.ps1 `
  -DataRoot "<LOCAL_PROSPECTUS_ROOT>" `
  -RestartDelaySeconds 30 `
  -MaxRestarts 3
```

默认不并发。一个 output directory 只允许一个 runner；失败后等待并用相同
`--resume` 命令重启，不删除旧 artifact、不 overwrite、不绕过 provenance conflict。
默认输出和日志均绑定当前 short SHA。

## 5. 进度、停止与恢复

检查进度：

```powershell
Get-Content reports/v04_pr_a_<short_sha>_logs/attempt_01.log -Tail 50
Get-Content reports/v04_pr_a_<short_sha>/coverage_summary.json
```

人工停止：在 runner 所在终端按 `Ctrl+C`。不要删除已生成 artifact。

恢复：重新执行完全相同的 unattended runner 命令和 `OutputDir`；runner 会继续调用
同一 `--resume` 路径。若出现 provenance conflict，应停止并审计，不得 force。

## 6. 发布前审计

离线 smoke 恢复联网后检查：

- `execution_context.json`
- `production_status.json`
- `oracle_status.json`
- `coverage.csv`
- `coverage_summary.json`
- `determinism_report.json`
- sibling logs

不得提交真实 PDF、runtime reports、日志、API key 或本地绝对路径。
