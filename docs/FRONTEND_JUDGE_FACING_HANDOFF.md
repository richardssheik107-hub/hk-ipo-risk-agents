# Judge-facing Frontend — v1.0.0 Final Handoff

> Release: `v1.0.0`  
> Status: **G5 PASS / FROZEN**

The judge-facing presentation is part of the v1.0.0 competition product and reuses the canonical runtime, demo bundle and clone-ready preflight.

## Run

Windows:

```powershell
START_JUDGE_DEMO.bat
```

macOS / Linux:

```bash
./start_judge_demo.sh
```

Both launchers fail fast when the governed runtime/demo prerequisites are not ready.

## Judge-facing information architecture

1. 风险总览
2. 风险解释与证据
3. 市场与模型
4. 结论形成过程
5. 专家复核与报告

Risk explanations use four layers:

```text
一句话结论
→ 为什么值得关注
→ 判断依据 / 原文 Evidence
→ 建议进一步核查
```

Provider/Prompt/raw diagnostics stay behind expert mode. Original Evidence text remains in its source language; judge-facing explanation defaults to clear Simplified Chinese.

## Truthfulness

- Market/model missingness remains truthful; no zero-fill.
- `unavailable_error` is shown as an error/unavailable condition, not a low-risk signal.
- Replay is clearly labeled as a recorded run.
- The UI consumes governed runtime values; it does not recompute Risk, Market or Model results.

## Governance

This frontend does **not** modify:

- Retriever / Agent / Risk / Evidence / Verifier semantics;
- Market-X / model calculations;
- Gold;
- Validation / Blind outcomes;
- provider retry behavior;
- frozen benchmark metrics.

`app/judge_copy.py` contains generic risk-family presentation logic only; it does not contain issuer/case/page/Gold-specific rules.

Post-v1.0 changes are limited to fatal launch/rendering or truthful-presentation fixes.
