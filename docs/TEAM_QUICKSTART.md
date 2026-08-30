# Team Quickstart — v1.0.0

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`

本页说明如何从 fresh clone 启动 v1.0.0 的稳定 Offline Replay / Judge Demo，以及它与新 PDF 实时分析的区别。

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

## 2. Standard product UI

Windows:

```text
START_DEMO.bat
```

macOS / Linux:

```text
./start_demo.sh
```

## 3. Judge-facing UI

Windows:

```text
START_JUDGE_DEMO.bat
```

macOS / Linux:

```text
./start_judge_demo.sh
```

Both launch paths run preflight checks before Streamlit starts.

## 4. Offline Demo Replay

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

## 5. Historical Governed IPO

For governed historical cases, the system can use the committed/governed runtime paths for Document, Market-X and frozen model signals subject to each channel's availability contract.

Do not manually fill unavailable Market/Model values.

## 6. Fresh New-IPO Analysis

A live new-PDF run requires:

- an authorized prospectus PDF;
- issuer/listing identity required by the runtime;
- provider credentials/network for real LLM paths;
- authorized/governed market inputs where required.

The system may return `AVAILABLE`, `PARTIAL`, `UNAVAILABLE` or an error state. Missingness is part of the product contract; it is not replaced with zero or guessed values.

## 7. Quick regression checks

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

## 8. What to show judges first

Recommended flow:

```text
风险总览
→ 风险解释与证据
→ 原 PDF Evidence
→ Market / Model 状态
→ 结论形成过程
→ Final Supervisor / Report
```

Main message:

```text
有什么风险
为什么值得关注
证据在哪里
为什么这个结论可信
哪些地方系统会诚实地说“不足以判断”
```

## 9. Final metric reminder

| Mode | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | 70/102 = 68.63% | 103/191 = 53.93% |
| Real LLM gated | 79/79 | 61/102 = 59.80% | 93/191 = 48.69% |

v1.0.0 is the formal competition product release. The repository's self-defined G2 remains blocked and must not be presented as passed.
