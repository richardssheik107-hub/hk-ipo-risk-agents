# Person 2 — Frontend / Product Owner — CLOSED

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Final status: **G5 PASS / PRODUCT UI CLOSED**  
> Final product-surface freeze: `006c7f302be5c278680d136371f6ef0db45fecc0`

## Final responsibility

The frontend track is complete for the competition release. No additional feature development is planned for v1.0.0.

The product is designed around one question: can a reviewer quickly understand **what the risk is, why it matters, where the Evidence is, and why the system's conclusion is trustworthy**.

## Final supported modes

```text
Offline Demo Replay
Historical Governed IPO
Fresh New-IPO Analysis
```

All modes preserve runtime truth. `AVAILABLE / PARTIAL / UNAVAILABLE / ERROR` are backend states; the UI does not invent Market, Model or Evidence values.

## Canonical product surface

The final competition release intentionally uses one active Streamlit workspace:

```text
app/streamlit_app.py
```

All launch commands converge on it:

```text
Windows standard: START_DEMO.bat
Windows judge:    START_JUDGE_DEMO.bat
Unix standard:    ./start_demo.sh
Unix judge:       ./start_judge_demo.sh
```

The judge commands are compatibility aliases, not a second product shell. Launchers run preflight checks and fail closed instead of showing a stale or half-working checkout.

## Final information architecture

Top-level navigation:

```text
首页
新建分析
案例工作台
后台
```

Case workspace tabs:

```text
案例概览
原文证据
市场与模型
综合结论与报告
```

Risk explanations remain evidence-first:

```text
一句话结论
→ 为什么值得关注
→ 判断依据 / 原文 Evidence
→ 建议进一步核查
```

Original Evidence remains in the source language; explanatory UI copy defaults to clear Simplified Chinese.

## Final product surfaces

- case overview and risk inventory;
- risk explanation + original Evidence;
- Market-X and frozen Model/SHAP state;
- conclusion formation / trace;
- integrated conclusion and report;
- Evidence screenshot / physical-page navigation;
- single-case and batch outputs;
- standard and judge compatibility launchers into the canonical workspace.

## G5 truth

Machine source:

```text
reports/final_status/product_acceptance.json
```

Final product acceptance:

```text
status = pass
truthful_channel_states = true
Offline Demo Replay = pass
Historical Governed IPO = pass
Fresh New-IPO Analysis = pass
```

Final product-surface CI on `006c7f3...`:

```text
tests = SUCCESS
Role D runtime = SUCCESS
Team demo runtime = SUCCESS
```

## Governance

Frontend code must not:

- change Retriever / Agent / Risk / Evidence / Verifier semantics;
- manufacture Market/Model/Evidence values;
- turn model errors into a low-risk interpretation;
- edit Gold or Validation/Blind outcomes;
- hide a replay as if it were a live run;
- display uncalibrated model scores as probabilities.

## Post-release rule

Only fatal launch/rendering defects or truthful-presentation bugs may be fixed in the competition release line. New product features belong to a later version.
