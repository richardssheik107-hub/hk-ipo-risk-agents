# Team Quickstart — v1.0.0

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Final product-surface freeze: `006c7f302be5c278680d136371f6ef0db45fecc0`

本页说明如何从 fresh clone 启动 v1.0.0 的稳定产品工作台与 Offline Replay，以及它与新 PDF 实时分析的区别。

Release / Gate 真相见：

```text
docs/V1_RELEASE_ACCEPTANCE.md
docs/FINAL_SUBMISSION_STATUS.md
```

## 1. Fresh clone

```bash
git clone <repository>
cd hk-ipo-risk-agents

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev,retrieval-research]"
python scripts/check_v045_team_clone_ready.py
```

Expected:

```text
TEAM_CLONE_READY = PASS
```

## 2. Canonical product UI

Windows:

```text
START_DEMO.bat
```

macOS / Linux:

```text
./start_demo.sh
```

## 3. Judge compatibility launchers

Windows:

```text
START_JUDGE_DEMO.bat
```

macOS / Linux:

```text
./start_judge_demo.sh
```

The judge commands are compatibility aliases. All four launch commands perform preflight and ultimately open:

```text
app/streamlit_app.py
```

There is no separate active judge UI implementation in the final release path.

## 4. Final information architecture

Top-level navigation:

```text
首页
新建分析
案例工作台
后台
```

Case workspace:

```text
案例概览
原文证据
市场与模型
综合结论与报告
```

Recommended judge flow:

```text
案例概览
→ 原文证据
→ 市场与模型
→ 综合结论与报告
```

Main message:

```text
有什么风险
为什么值得关注
证据在哪里
为什么这个结论可信
哪些地方系统会诚实地说“不足以判断”
```

## 5. Offline Demo Replay

Canonical replay cases:

```text
ipo_2024_02410 / 2410.HK
ipo_2024_02460 / 2460.HK
ipo_2024_01318 / 1318.HK
```

Offline Replay does **not** require:

- prospectus PDFs;
- API keys/provider credentials;
- network access;
- re-analysis.

It reads the hash-bound `reports/v045_demo_bundle`. The UI must clearly label it as a recorded run; replay is never presented as live inference.

## 6. Historical Governed IPO

For governed historical cases, the system can use the committed/governed runtime paths for Document, Market-X and frozen model signals subject to each channel's availability contract.

Do not manually fill unavailable Market/Model values.

## 7. Fresh New-IPO Analysis

A live new-PDF run requires:

- an authorized prospectus PDF;
- issuer/listing identity required by the runtime;
- provider credentials/network for real LLM paths;
- authorized/governed market inputs where required.

The system may return `AVAILABLE`, `PARTIAL`, `UNAVAILABLE` or an error state. Missingness is part of the product contract; it is not replaced with zero or guessed values.

## 8. Quick regression checks

```bash
python -m compileall -q app src scripts
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_competition_runtime.py
python scripts/validate_v045_role_d_receipt.py
python scripts/check_v045_product_runtime.py
python scripts/check_v045_team_clone_ready.py
python scripts/check_final_product_capabilities.py
```

The final product-surface commit `006c7f3...` passed the `tests`, `Role D runtime` and `Team demo runtime` GitHub Actions workflows.

## 9. Final metric reminder

| Mode | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | 70/102 = 68.63% | 103/191 = 53.93% |
| Real LLM gated | 79/79 | 61/102 = 59.80% | 93/191 = 48.69% |

v1.0.0 is the formal competition product release. The repository's self-defined G2 remains blocked and must not be presented as passed.
