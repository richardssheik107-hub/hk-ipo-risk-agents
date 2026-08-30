# Judge-facing Frontend — v1.0.0 Final Handoff

> Release: `v1.0.0`  
> Status: **G5 PASS / FROZEN**  
> Final product-surface freeze: `006c7f302be5c278680d136371f6ef0db45fecc0`

The judge-facing launch commands open the same canonical reader workspace as the standard launch commands. This prevents a second presentation shell from overriding the user-approved frontend while preserving the governed runtime, demo bundle and clone-ready preflight.

## Run

Windows:

```powershell
START_JUDGE_DEMO.bat
```

macOS / Linux:

```bash
./start_judge_demo.sh
```

Both commands are compatibility aliases for `app/streamlit_app.py` and fail fast when the governed runtime/demo prerequisites are not ready.

## Judge-facing information architecture

Top-level product navigation:

1. 首页
2. 新建分析
3. 案例工作台
4. 后台

Case workspace tabs:

1. 案例概览
2. 原文证据
3. 市场与模型
4. 综合结论与报告

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

## Release validation

On `006c7f302be5c278680d136371f6ef0db45fecc0`:

```text
tests = SUCCESS
Role D runtime = SUCCESS
Team demo runtime = SUCCESS
```

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
