# Team Quickstart — Final-three Offline Replay

> 状态日期：`2026-08-29`

本页只说明如何从 fresh clone 打开已记录的 final-three 演示，以及它与新 PDF 实时分析的区别。
项目整体仍是 `NOT COMPETITION_READY`；B M1/M2、M4、one-shot Validation 等 Gate 以
`V0.4_RELEASE_ACCEPTANCE.md` 为准。

## Offline Replay

```bash
git clone <repository>
cd hk-ipo-risk-agents

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -e ".[dev,retrieval-research]"
python scripts/check_v045_team_clone_ready.py
```

checker 必须输出：

```text
TEAM_CLONE_READY = PASS
```

启动方式：

```text
Windows: START_DEMO.bat
Unix:    ./start_demo.sh
```

也可以直接运行：

```bash
python -m streamlit run app/streamlit_app.py
```

打开侧栏 `Demo replay`，依次选择：

```text
ipo_2024_02410 / 2410.HK
ipo_2024_02460 / 2460.HK
ipo_2024_01318 / 1318.HK
```

Offline Replay 不需要：

- 招股书 PDF；
- API key 或其他 provider credentials；
- provider 网络；
- 重新分析。

它读取 `reports/v045_demo_bundle`。环境变量 `IPO_RISK_DEMO_BUNDLE` 只用于显式覆盖；
未设置时应用只尝试 canonical path，缺失时明确显示 unavailable。

## Provenance

Replay 是真实 provider 成功运行的 hash-bound recording：

```text
recorded runtime SHA = 3d81e5d0d71aeb5ffc76e3f123e8eecb5c75af8d
runtime-equivalent release baseline = 802bf5095e0db6a604dcb762e1070563f8cb1b34
```

`reports/final_status/runtime_equivalence.json` 由 Git diff 生成，证明两者之间唯一文件差异是
Role-D CI workflow，runtime source/configuration 未变。Replay 中的 recorded SHA 没有被改写。

## Fresh Analysis

分析新的 PDF 是另一种模式，需要：

- 已获授权的招股书 PDF；
- 当前配置要求的 provider credentials；
- provider 网络连接。

Fresh Analysis 会重新执行 pipeline。Offline Replay 只展示已记录结果，二者不能混称。
