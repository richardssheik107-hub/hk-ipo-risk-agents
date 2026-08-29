# Competition Submission Runbook

> 状态日期：`2026-08-29`
>
> Metric protocol：`v045_competition_metric_protocol_v2_existing_gold_only`

本 Runbook 描述从当前 main 到最终封包的可重复步骤。实时状态见 `V0.4_RELEASE_ACCEPTANCE.md`，执行顺序见 `COMPETITION_CLOSURE_PLAN.md`。

## 1. 基本原则

- fixed10 不是正式比赛 PASS；
- `COMPETITION_READY` 只能由真实 active Gate 得出；
- Gold immutable；
- Validation one-shot after freeze；
- 2025 Blind 不用于优化；
- fallback 不计 real-provider accepted；
- Market missing 不补零；
- uncalibrated score 不称 probability；
- PDF、raw EOD、Secret、raw journal、绝对路径不进入 Git/bundle；
- **Human Review / M4 不再是 Release Gate，不要求 6 份真人 review。**

## 2. 当前稳定团队基线

PR #185 后已验证：

```text
Gate E1 = 3/3
real-provider first-attempt = 3/3
M3 = 1.0 x 3
Market / frozen Model = 3/3
recheck = 17/17
budget-skipped = 0
seven-stage = 7/7 x 3
Evidence screenshot = 17/17 precise
canonical bundle = 66 files / 7,528,749 bytes
bundle verify = PASS
TEAM_CLONE_READY = PASS
fresh clone = PASS
Streamlit smoke = PASS
CI = PASS
```

Canonical replay：`reports/v045_demo_bundle`。

## 3. 安装与基础校验

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
python scripts/check_v045_product_runtime.py
python scripts/check_v045_team_clone_ready.py
```

## 4. Role-B Development closure

当前 checkpoint：

```text
fixed-journal M1 = 12/30 = 40.00%
fixed-journal M2 = 18/48 = 37.50%
fresh gated M1 = 11/30
fresh gated M2 = 17/48
structured valid = 38/40
```

当前优先根因：

```text
deterministic_fact_missing
→ retrieval_candidate_miss
→ numeric extraction / genuine conflict
→ LLM / Evidence variance
```

执行规则：

- 每个修复包只处理 proven root；
- fixed10 用于快速诊断；
- 稳定后扩大 Development；
- 最终跑 ALL79；
- M1 `>=0.80`、M2 `>=0.85` 后 freeze；
- 在 A 授权前不运行 Validation。

常用入口：

```bash
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
python scripts/run_v046_role_b_ablation.py --subset-only
python scripts/check_v046_role_b_structured_smoke.py
python scripts/run_v046_role_b_ablation.py --run-id <RUN_ID> --modes all --execute
```

## 5. Role-D model decision

先读：

```text
docs/ROLE_D_MODEL_DECISION.md
docs/V045_ROLE_D_FINAL_CLOSURE.md
```

A 做一次 promote/retain 决议：

- promote v2：创建新的 versioned freeze/receipt/handoff，不再按 2024 调参；
- retain PR-F：保留弱辅助 signal，并完成 strict revalidation / dynamic inference contract。

V2 的 builder/checker/frozen binding 已版本化实现。持有授权 PR-C targets 时重建：

```bash
python scripts/build_v045_role_d_v2_release.py \
  --target-dir <AUTHORIZED_PR_C_TARGET_DIR>/targets \
  --base-main-commit <BASE_MAIN_SHA>
python scripts/check_v045_role_d_v2_release.py
```

输出使用 `reports/v045_role_d_v2`、独立 V2 freeze/receipt 和独立 handoff；不得手工改写或覆盖旧 frozen PR-F artifact。再验证 `--resume` 与新空目录重建 byte-identical。

V2 runtime 使用 `reports/v045_role_d_v2_product_handoff_final3`。缺不可变输入时状态为 `BLOCKED_EXTERNAL_IMMUTABLE_INPUTS`，不得重训或换行情绕过。

验证现有 frozen receipt：

```bash
python scripts/validate_v045_role_d_receipt.py
python scripts/check_v045_product_runtime.py
```

使用授权行情 ZIP 重建 438 frozen Market-X：

```bash
python scripts/prepare_v045_market_runtime.py \
  --eod-archive <hkshareeodprices.zip>
```

## 6. Dynamic New-IPO runtime

### Phase 1 — historical universe

要求：非 final-three 的 frozen historical case 也能：

```text
Market-X artifact
→ frozen model inference
→ native SHAP
→ Final Supervisor / report
```

验收必须使用未参与实现的 historical holdout cases，禁止 company/case-specific code。

### Phase 2 — arbitrary new IPO

```text
new PDF
→ Document pipeline
→ issuer/listing identity
→ governed pre-listing history
→ Dynamic PIT Market-X
→ frozen model inference
→ SHAP
→ Supervisor / report
```

外部市场历史不足时明确 partial/unavailable，不 fake-fill。

## 7. Final-three replay / regression check

后续任何大改都要保护 canonical baseline：

```bash
python scripts/check_v045_product_runtime.py
python scripts/check_v045_team_clone_ready.py
python scripts/build_v045_demo_bundle.py \
  --output-dir reports/v045_demo_bundle \
  --verify
```

必须保持：

```text
E1 3/3
M3 1.0 x 3
Market / Model 3/3
recheck 17/17
seven-stage 7/7 x 3
Evidence 17/17 precise
bundle verify PASS
```

Recorded provenance：

```text
recorded runtime SHA = 3d81e5d0d71aeb5ffc76e3f123e8eecb5c75af8d
runtime-equivalent release SHA = 802bf5095e0db6a604dcb762e1070563f8cb1b34
team-ready merge SHA = 732c5fd7b609b1a6589630b6e6a559c117206747
```

不得修改 replay 内的 recorded SHA 伪装成后来 commit。

## 8. Competition capability cases

准备真实、可审计案例：

- core pipeline progress；
- text embellishment；
- related-party transaction；
- comparable IPO valuation；
- Dynamic New-IPO proof；
- Evidence screenshot；
- single/batch report；
- API/UI。

无正式 Existing Gold 时标记 `QUALITATIVE DEMONSTRATION`，不混入 M1/M2。

Human Review UI 可以展示，但不需要真人评分。

## 9. Evidence screenshot export

对新的真实运行：

```bash
python scripts/build_v045_evidence_screenshots.py \
  --input-dir <RUN_DIR> \
  --prospectus-root <AUTHORIZED_ROOT>
```

必须绑定 source PDF hash、physical page、bbox source、match count、screenshot path/hash。多重/无匹配明确 unavailable，不画假框。

## 10. One-shot Validation

只有 B Full Development 达标、B/D 身份冻结后：

```text
ALL19 evaluable 2024 Existing-Gold cases
one execution under frozen identity
```

执行后不得根据 Validation 调 Prompt、Retriever、Verifier、threshold、model 或 evaluator。

## 11. Final readiness

最终 readiness 只检查当前 active Gate：

```text
B ALL79 + M1/M2
D formal model decision / strict identity
C/E/M3 stable baseline
Dynamic New-IPO / product coverage
competition capability cases
one-shot Validation
latest-main CI
Blind / provenance / determinism / security
final package
```

**不检查 M4 6 human reviews。**

Human Review artifact 若存在，可以作为 optional artifact；没有真人 review 不得导致 readiness FAIL。

## 12. Final package

只有 active readiness 全部通过后运行 packager。

Bundle 必须包含：

```text
source / environment / scripts
prototype / API / UI
prediction table
Agent / Tool / Evidence trace
Evidence screenshots
canonical 3 case reports / replay
Dynamic New-IPO proof
metrics / audits / artifact index / release note
```

Human Review export 可选；不要求 review scores。

Bundle 必须拒绝：PDF、raw licensed data、Secret/private key/token、本机路径、raw journal、未授权模型、Validation/Blind leakage。

## 13. Final checklist

```text
[ ] ALL79 Development
[ ] M1 >=80%
[ ] M2 >=85%
[ ] D A-owned promotion PR merge
[x] D V2 strict revalidation / determinism / final identity（promotion package）
[x] C/E final-three baseline
[x] E accepted 3/3
[x] M3 =100%
[x] Evidence screenshots 17/17 precise
[x] canonical replay / team clone
[ ] Dynamic New-IPO Phase 1
[ ] Dynamic New-IPO Phase 2 or governed external-data limitation documented
[ ] competition capability cases
[ ] frozen one-shot Validation
[ ] latest-main CI after final freeze
[ ] Blind / provenance / determinism / security
[ ] artifact index / ZIP / SHA manifest
```
