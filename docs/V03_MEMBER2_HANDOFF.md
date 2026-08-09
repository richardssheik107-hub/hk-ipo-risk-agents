# v0.3 2号成员交付与独立复跑报告

负责人：2号（数据工程、批量评测与技术备份）

分支：`feat/v03-catalog-provider-batch-eval`

对应路线棒次：V3-2（IPO基础信息Provider）、V3-10（批量运行与评测）、CI加固与独立复跑。

本报告按计划文件第九节「每个分支完成后的统一汇报」十问格式给出。

## 1. 创建了哪些文件

- `src/ipo_risk/providers/catalog.py`：`CatalogIPODataProvider` 与特殊证券治理常量 `SPECIAL_SECURITIES`、`governance_table()`。
- `src/ipo_risk/evaluation/batch.py`：批量分析核心（`run_batch`、选例、2025盲测保护、失败隔离、断点续跑、运行清单）。
- `src/ipo_risk/evaluation/golden_eval.py`：黄金案例评测核心（指标计算与六个产物文件）。
- `scripts/run_v03_batch_analysis.py`：批量运行 CLI。
- `scripts/evaluate_v03_golden_cases.py`：评测 CLI。
- 测试：`tests/unit/test_catalog_ipo_provider.py`、`tests/unit/test_v03_manifest_integrity.py`、`tests/integration/test_v03_batch_runner.py`、`tests/integration/test_v03_golden_eval.py`。
- `docs/V03_MEMBER2_HANDOFF.md`（本文件）。

## 2. 修改了哪些文件

- `src/ipo_risk/evaluation/v03_manifest.py`：新增 `validate_manifest_integrity()`（身份一致性、判断去重、2025盲测阻断，以及可选的招股书清单交叉核验）。既有 `validate_manifest()` 逐行契约保持不变。
- `scripts/validate_v03_golden_manifest.py`：新增 `--integrity`、`--prospectus-manifest`、`--data-root` 参数；不带参数时行为向后兼容。
- `.github/workflows/tests.yml`：在 CI 中加入 `validate_project.py`、`validate_competition_data.py`、黄金清单完整性校验、`compileall ... scripts`，以及 mock 模式的批量+评测冒烟。

**未修改任何受保护共享文件**：`schemas/__init__.py`、`domain/risk_codes.py`、`core/container.py`、`workflows/state.py`、`providers/base.py` 均未改动（契约第7条）。

## 3. 实现了哪些功能

- **CatalogIPODataProvider**：将 `ipo_official_master_bridge.csv` 转成统一 `IPOProfile`。562个匹配案例带完整发行事实；3个未匹配占位证券诚实降级（仅身份，不臆造财务字段）。支持 `get_by_case_id`、`get_by_stock_code`（Wind/原始/裸数字代码等价）、`get_by_stock_code_and_year`、`get_profile`（协议入口，未知身份返回 `not_in_catalog` 降级档）。公司名对占位行回退到招股书清单披露简称，并在 metadata 记录 PDF 相对路径/SHA/页数，供批量定位。
- **特殊证券治理**（写入 `IPOProfile.metadata.special_security`，不改公共 Schema）：
  - `2191.HK` 顺丰房托 → REIT 基金单位，保留代码，`ordinary_equity_eligible=false`、`market_label_eligible=true`；
  - `4801.HK`→`7801.HK`、`4841.HK`→`7841.HK` → SPAC 上市权证，关联 SPAC A 类股份，二者均不计入普通股与市场标签范围。
- **黄金案例数据校验**：在逐行标注契约之上增加目录级完整性检查（case 身份一致、判断去重、2025盲测阻断；可选交叉核验 split/SHA-256/PDF 路径）。
- **批量运行脚本**：按 case_id / split / 黄金清单选例；单案例失败隔离；断点续跑与 `--overwrite`；记录代码 SHA、配置、Python 版本、起止时间与各 Agent 状态；产出 `run_manifest.json`、`analysis_results.jsonl`、`case_summary.csv`、`failure_report.csv`。
- **2025盲测保护**：blind_test 案例默认跳过并标记 `protected`；要纳入必须同时给出 `--include-blind-test` 与精确令牌 `I_ACCEPT_FINAL_BLIND_TEST`，否则整批 fail-closed 拒绝执行。
- **评测脚本**：消费 `analysis_results.jsonl` 与黄金清单，产出 `analysis_results.jsonl`、`risk_items.csv`、`evidence_results.csv`、`case_summary.csv`、`failure_report.csv`、`evaluation_metrics.json`。指标涵盖 Evidence Recall@1/3/5、Risk Precision/Recall/F1、verified precision、Agent 失败率、partial 比例、案例完成率；金额/单位/期间准确率仅在黄金清单包含 `gold_amount/gold_unit/gold_period` 列时计算，否则标 `available:false`（不伪造）。

## 4. 是否影响公共接口

否。仅在 `providers/`、`evaluation/`、`scripts/` 下新增文件，并对既有评测校验器做带默认值的兼容扩展。公共 Schema、注册表、容器、工作流边界均未改动。批量运行通过**运行时注册** `ipo_data_provider="catalog"` 让工作流使用目录档案，无需改 `container.py`。

## 5. 输入和输出是什么

- 输入：`data/catalog/ipo_official_master_bridge.csv`、`data/catalog/ipo_prospectus_manifest.csv`、黄金清单 CSV、（真实模式下）本地招股书 PDF 根目录。
- 输出：`IPOProfile`；`reports/v03_batch/*`（运行清单与批量产物）；`reports/v03_eval/*`（六个评测文件）。

## 6. 执行了哪些测试

`pytest -q`、`validate_project.py`、`validate_competition_data.py`、`validate_v03_golden_manifest.py --integrity`、`compileall app src scripts`、`git diff --check`，以及批量+评测 CLI 端到端冒烟。

## 7. 测试结果是多少

- `pytest -q`：**320 passed**（在 292 基线上新增 28 项）。
- `validate_project.py`：`status=completed verified=3 pending=1`。
- `validate_competition_data.py`：`competition_data_validation=passed`。
- 黄金清单完整性：`valid`。
- `compileall`：退出 0；`git diff --check`：clean。
- 端到端冒烟：`--split development --limit 3` 三案例全部 `completed`，评测产物齐全。

## 8. 使用了哪些黄金案例

`tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv`（合成样例，3行）。评测脚本对该合成清单诚实报告：其 case_id 不在赛事目录中，故批量无法运行，评测显示 `evaluated:0 / missing_from_results:[...]`——这正确反映「尚无真实黄金案例」，待 3/4/5号提交真实标注后指标自动填充。

## 9. 当前有哪些已知限制

- 真实黄金案例尚未产出（V3-1 由 3/4/5号负责）；招股书原始 PDF 不入库，真实模式批量需本地 `--data-root`。
- 金额/单位/期间准确率待黄金清单补充 `gold_amount/gold_unit/gold_period` 列后方可计算。
- Evidence Recall 依赖真实 Agent 产出带页码证据；当前 mock/仅现金跑道下召回为 0 属预期。
- `CatalogIPODataProvider` 尚未登记进 `core/container.py`（属 1号文件），目前仅由批量运行器运行时注册。

## 10. 下一棒需要什么输入

- **给 1号**：在 `core/container.py` 注册 `registry.register("ipo_data_provider", "catalog", lambda: CatalogIPODataProvider())` 并在 `configs/*.yaml` 增加 `ipo_data_provider: catalog` 选项，使 Service/Streamlit 也能使用目录档案；special_security 元数据可用于前端标注与 v0.4 标签资格。
- **给 3/4/5号**：按 `V03_ANNOTATION_GUIDE` 用**真实** `ipo_YYYY_NNNNN` case_id 产出黄金清单；若要评金额准确率，追加 `gold_amount/gold_unit/gold_period` 列（评测脚本已前向兼容）。

---

## 独立环境复跑步骤

系统默认 `python3` 为 3.9，无法运行本项目；需 Python 3.11 虚拟环境。

```bash
# 1. 建立并激活 3.11 虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. 安装（可编辑 + 开发依赖）
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

# 3. 统一验收命令
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_v03_golden_manifest.py \
    tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv --integrity
python -m compileall -q app src scripts
git diff --check

# 4. 2号新增链路冒烟（mock 模式，无需 PDF）
python scripts/run_v03_batch_analysis.py \
    --case-ids ipo_2020_00368,ipo_2020_00589 --output-dir reports/v03_batch
python scripts/evaluate_v03_golden_cases.py \
    --results reports/v03_batch/analysis_results.jsonl \
    --golden-manifest tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv \
    --output-dir reports/v03_eval
```

真实文档批量（本地有招股书 PDF 时）：

```bash
python scripts/run_v03_batch_analysis.py \
    --golden-manifest <真实黄金清单.csv> \
    --config configs/real_pdf.yaml --data-root <招股书PDF根目录>
```
