# Judge-facing frontend handoff

The judge-facing presentation is available on `main` and reuses the canonical
runtime, demo bundle and clone-ready preflight.

## Run

```powershell
START_JUDGE_DEMO.bat
```

macOS / Linux:

```bash
./start_judge_demo.sh
```

Both launchers fail fast when the governed demo bundle is not clone-ready.

## Product changes

- Business-facing Chinese navigation.
- Five judge-oriented workspaces:
  1. 风险总览
  2. 风险解释与证据
  3. 市场与模型
  4. 结论形成过程
  5. 专家复核与报告
- Four-part risk explanation:
  - 一句话结论
  - 为什么值得关注
  - 判断依据
  - 建议进一步核查
- Stronger risk-level colors.
- Provider/Prompt/raw sidecar/metadata hidden by default behind expert mode.
- Market/model missingness remains truthful; no zero-fill.
- Existing governed `IPOAnalysisService` and payload semantics are reused.

## Governance

This frontend does **not** modify:

- Retriever / Agent / Risk / Evidence / Verifier semantics
- Market-X / model calculations
- Validation / Blind
- Gold
- provider retry behavior

`app/judge_copy.py` contains only generic risk-family explanation copy. It does not
contain issuer/case/page/Gold-specific rules.
