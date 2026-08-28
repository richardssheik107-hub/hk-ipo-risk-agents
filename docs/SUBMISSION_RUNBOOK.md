# Competition Submission Runbook

> 状态日期：`2026-08-28`

本 Runbook 只描述从当前状态到最终封包的可重复步骤。状态见 `V0.4_RELEASE_ACCEPTANCE.md`，顺序见 `COMPETITION_CLOSURE_PLAN.md`。

## 1. 基本原则

- fixed-10 不是正式比赛 PASS；
- `COMPETITION_READY` 只能由真实 Gate 得出；
- Gold immutable；
- Validation one-shot after freeze；
- 2025 Blind 不用于后续优化；
- fallback 不计 real-provider accepted；
- Market missing 不补零；
- uncalibrated score 不称 probability；
- PDF、raw EOD、model bulk、Secret、raw journal、绝对路径不进入 Git 或 bundle。

## 2. 安装与基础校验

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,retrieval-research]"

python -m compileall -q app src scripts
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_competition_runtime.py
python scripts/validate_v045_role_d_receipt.py
```

## 3. Role-B forensic baseline

```bash
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
python scripts/run_v046_role_b_ablation.py --subset-only
python scripts/check_v046_role_b_structured_smoke.py
python scripts/run_v046_role_b_ablation.py \
  --run-id <RUN_ID> \
  --modes all \
  --execute
```

要求：matching provider/model/Prompt/Schema smoke 通过；offline/shadow/gated 同身份；shadow 不改变 canonical result；gated 无额外网络调用。

在进入优化前补齐 Risk/Evidence root-cause matrix。完整规则见 `ROLE_B_M1_M2_PLAN.md`。

## 4. Role-B Development closure

- 根据 proven root cause 做通用修复；
- 每个修复包有测试与消融；
- fixed-10 达标后运行 ALL 79 Development；
- 达到 M1/M2 门槛后冻结完整身份；
- 不运行 Validation，直到 A 批准 one-shot。

冻结清单：code SHA、Gold/subset manifest、Prompt、Retriever、Schema、normalization、reconciliation、Verifier、Evaluator、provider/model/transport/config。

## 5. Role-D release revalidation

先验证 recorded receipt：

```bash
python scripts/validate_v045_role_d_receipt.py
```

持有 SHA 匹配的 frozen PR-E/PR-F runtime 与授权 EOD 时：

```bash
python scripts/build_v045_role_d_m5.py --output-dir reports/v045_role_d
python scripts/check_v045_role_d_m5.py \
  --role-d-dir reports/v045_role_d \
  --output reports/v045_role_d_acceptance/acceptance.json
```

再验证 `--resume` 与新空目录重建 byte-identical。

Final-three handoff：

```bash
python scripts/build_v04_pr_f_product_handoff.py \
  --source-pr-f-dir reports/v04_pr_f \
  --case-list configs/v045_demo_cases.json \
  --output-dir reports/v045_pr_f_product_handoff_final3
```

缺不可变输入时状态为 `BLOCKED_EXTERNAL_IMMUTABLE_INPUTS`，不得重训或换行情绕过。

D 的最终报告必须同时给出性能、基准和限制，不把文件齐全等同于业务效果强。

## 6. Final-three offline / AI / Market / M3

Offline：

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_offline.yaml \
  --prospectus-root <AUTHORIZED_ROOT> \
  --output-dir reports/v045_role_e_offline_final
```

AI：

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_ai.yaml \
  --prospectus-root <AUTHORIZED_ROOT> \
  --output-dir reports/v045_role_e_ai_final
```

验收：2410/2460/1318 real-provider accepted 3/3、scope PASS、severity floor、complete call trace；M3 每案 1.0；Market strict contract 3/3。

## 7. M4 Human Review

每案至少两名独立真人，共 6 份。LLM reviewer 只能 advisory。

评审材料至少包含 case report、Agent log、Evidence、Conflict/Recheck、Final Supervisor、Market/Model status。

## 8. Competition capability cases

为以下能力准备真实案例和可审计产物：

- core pipeline progress；
- text embellishment；
- related-party transaction；
- comparable IPO valuation；
- Evidence screenshot。

无正式 Gold 时标为 qualitative demonstration，不混入 M1/M2。

## 9. Evidence screenshot export

每个关键 Evidence 绑定 source PDF hash、physical page、bbox source、match count、screenshot path/hash。

只接受 upstream bbox 或唯一 exact quote match。多重/无匹配时明确 unavailable，不画假框。

## 10. One-shot Validation

只有 B Full Development 通过且完整 freeze 后：

```text
ALL 19 evaluable 2024 Existing-Gold cases
one execution under frozen identity
```

运行后不再调整 Prompt、Retriever、Verifier、threshold 或 evaluator。

## 11. Final readiness

所有 lane artifact 到齐后运行现有 readiness builder，并检查：

- B M1/M2；
- D strict acceptance / final-three；
- C/E/M3/M4；
- capability cases / screenshots；
- latest-main CI；
- Blind / provenance / determinism / security；
- artifact index。

`--latest-main-ci-passed` 只能在 CI 实际通过时使用。

## 12. Final package

只有 `submission_readiness.json.competition_ready=true` 才运行 packager。

Bundle 必须包含：

- source / environment / run scripts；
- runnable prototype or API；
- prediction table；
- Agent logs；
- Evidence / screenshot manifest；
- three case reports；
- M4 reviews；
- metrics / audits / artifact index / release note。

Bundle 必须拒绝 PDF、raw licensed data、Secret/private key/token、本机路径、raw journal、未授权模型和 reviewer 私有工作文件。

## 13. Final checklist

```text
[ ] B forensic baseline
[ ] ALL 79 Development
[ ] M1 >=80%
[ ] M2 >=85%
[ ] D strict revalidation / determinism / final-three
[ ] D business-value conclusion
[ ] C strict 3/3
[ ] E accepted 3/3
[ ] M3 =100%
[ ] M4 6 reviews
[ ] capability cases
[ ] Evidence screenshots
[ ] frozen one-shot Validation
[ ] latest-main CI
[ ] Blind / provenance / determinism / security
[ ] artifact index / ZIP / SHA manifest
```
