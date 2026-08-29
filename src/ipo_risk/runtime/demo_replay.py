"""The demo bundle: a recorded run that can be shown again without re-running it.

A live demonstration of this system needs the licensed prospectus, provider
credentials and a network -- three things that can each fail in front of an
audience, and none of which prove anything the recorded run did not already
prove.  This module packages what a case run actually produced into a
self-contained bundle, and loads that bundle back for display.

A replay is labelled a replay.  Every payload loaded here carries the identity of
the run that produced it -- its config, its analysis id, the SHA-256 of the
prospectus it read, the code base it ran from -- so the screen can say "this is a
recording of that run" instead of implying a fresh analysis is happening now.
Nothing is re-derived on load: what was not recorded is reported missing.

The bundle is hash-bound for the same reason the screenshots are.  Every file is
listed with its SHA-256 so the copy on the demo machine can be proven to be the
artifacts the run wrote, and ``verify_demo_bundle`` re-checks them before anyone
puts it on a screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import shutil

DEMO_BUNDLE_SCHEMA_VERSION = "v045_role_e_demo_bundle_v1"

MANIFEST_NAME = "demo_manifest.json"
DEMO_SCRIPT_NAME = "DEMO_SCRIPT.md"
SCREENSHOT_DIR_NAME = "screenshots"

# The recorded run itself.  Without the analysis result there is no case to
# replay, so its absence disqualifies the case rather than producing a thin one.
REQUIRED_CASE_FILES = ("analysis_result.json",)
OPTIONAL_CASE_FILES = (
    "final_supervision.json",
    "conflicts.json",
    "rechecks.json",
    "trace_sidecar.json",
    "traceability.json",
    "prospectus_verification.json",
    "agent_reasoning_log.json",
    "agent_reasoning_log.md",
    "case_report.md",
    "gate_e1_evidence.json",
    "evidence_export.json",
    "evidence_export.csv",
    "human_review_export.json",
    "screenshot_manifest.json",
)
MATRIX_FILES = (
    "summary.json",
    "batch_report.json",
    "batch_report.md",
    "screenshot_summary.json",
)

STATUS_BUNDLED = "bundled"
STATUS_UNAVAILABLE_SOURCE = "unavailable_source_dir"
STATUS_NO_CASES = "no_replayable_case"


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


@dataclass(frozen=True)
class RecordedCase:
    """One recorded case run, as loaded for display.

    ``result`` is the analysis payload exactly as the run wrote it. The rest are
    the sidecars, each of which may be ``None``; a missing sidecar is shown as
    missing rather than reconstructed.
    """

    case_id: str
    directory: Path
    result: dict[str, Any]
    provenance: dict[str, Any]
    screenshots: dict[str, Any] | None = None
    gate_e1: dict[str, Any] | None = None
    human_review: dict[str, Any] | None = None
    case_report_markdown: str | None = None
    missing: tuple[str, ...] = ()

    @property
    def company_name(self) -> str:
        return str(self.result.get("company_name") or self.case_id)

    @property
    def stock_code(self) -> str:
        return str(self.result.get("stock_code") or "")


def _provenance(
    case_id: str,
    case_dir: Path,
    result: Mapping[str, Any],
    verification: Mapping[str, Any] | None,
    matrix: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Which run this is a recording of."""

    matrix = matrix or {}
    return {
        "is_replay": True,
        "case_id": case_id,
        "directory_name": case_dir.name,
        "analysis_id": result.get("analysis_id"),
        "workflow_version": result.get("workflow_version"),
        "schema_version": result.get("schema_version"),
        "completed_at": result.get("completed_at") or result.get("created_at"),
        "config": matrix.get("config"),
        "code_base_sha": matrix.get("code_base_sha"),
        "code_base_dirty": matrix.get("code_base_dirty"),
        "cases_manifest_sha256": matrix.get("cases_manifest_sha256"),
        "config_sha256": matrix.get("config_sha256"),
        "prospectus_sha256": (verification or {}).get("sha256"),
        "prospectus_page_count": (verification or {}).get("pdf_page_count"),
        # The licensed archive path is not part of a portable bundle.
        "path_recorded": False,
        "statement": (
            "这是对一次已记录运行的回放，不是正在进行的分析。所有结论、Evidence、"
            "截图与通道状态都来自上面这次运行，界面不会为回放补任何内容。"
        ),
    }


def load_recorded_case(case_dir: Path, matrix: Mapping[str, Any] | None = None) -> RecordedCase:
    """Load one recorded case for display, or refuse it.

    ``FileNotFoundError`` is raised when the analysis result is absent: a case
    with no recorded run has nothing to replay, and an empty workspace would
    look like a run that found nothing.
    """

    result = _load_json(case_dir / "analysis_result.json")
    if result is None:
        raise FileNotFoundError(
            f"{case_dir.name} has no readable analysis_result.json, so there is no recorded run to replay"
        )
    missing = [
        name for name in OPTIONAL_CASE_FILES if not (case_dir / name).is_file()
    ]
    return RecordedCase(
        case_id=case_dir.name,
        directory=case_dir,
        result=result,
        provenance=_provenance(
            case_dir.name,
            case_dir,
            result,
            _load_json(case_dir / "prospectus_verification.json"),
            matrix,
        ),
        screenshots=_load_json(case_dir / "screenshot_manifest.json"),
        gate_e1=_load_json(case_dir / "gate_e1_evidence.json"),
        human_review=_load_json(case_dir / "human_review_export.json"),
        case_report_markdown=(
            (case_dir / "case_report.md").read_text(encoding="utf-8")
            if (case_dir / "case_report.md").is_file()
            else None
        ),
        missing=tuple(missing),
    )


def available_recorded_cases(root: Path) -> list[Path]:
    """Case directories under ``root`` that carry a recorded analysis result."""

    if not root.is_dir():
        return []
    return [
        path
        for path in sorted(root.iterdir())
        if path.is_dir() and (path / "analysis_result.json").is_file()
    ]


@dataclass(frozen=True)
class ReplayScreenshots:
    """The exported images a replay can show instead of re-rendering a PDF."""

    directory: Path
    index: dict[str, dict[str, Any]]

    def record(self, evidence_id: str) -> dict[str, Any] | None:
        return self.index.get(str(evidence_id))

    def image_path(self, evidence_id: str) -> Path | None:
        record = self.record(evidence_id)
        if record is None:
            return None
        path = self.directory / str(record["filename"])
        return path if path.is_file() else None


def replay_screenshots(case: RecordedCase) -> ReplayScreenshots:
    """The screenshot side of one recorded case, empty when it exported none."""

    return ReplayScreenshots(
        directory=case.directory / SCREENSHOT_DIR_NAME,
        index=screenshot_index(case.screenshots),
    )


def screenshot_index(manifest: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Evidence id -> its exported screenshot record, for the offline viewer.

    Only rendered items are indexed. An Evidence item the export refused stays
    absent here, so the viewer says it has no image instead of showing another
    item's page.
    """

    index: dict[str, dict[str, Any]] = {}
    for item in (manifest or {}).get("items", []) or []:
        if not isinstance(item, dict) or item.get("status") != "rendered":
            continue
        screenshot = item.get("screenshot") or {}
        evidence_id = str(item.get("evidence_id") or "")
        if not evidence_id or not screenshot.get("filename"):
            continue
        index[evidence_id] = {
            "filename": screenshot["filename"],
            "sha256": screenshot.get("sha256"),
            "page": item.get("page"),
            "granularity": (item.get("localisation") or {}).get("granularity"),
            "precise": (item.get("localisation") or {}).get("precise_snippet_localisation"),
            "highlight_drawn": item.get("highlight_drawn"),
        }
    return index


def build_demo_bundle(
    *,
    source_dir: Path,
    output_dir: Path,
    case_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Copy a matrix run's artifacts into a self-contained, hash-bound bundle.

    Only files the run actually wrote are copied; a case missing an optional
    sidecar is bundled with that name recorded as missing, so the demo machine
    can tell "this run did not produce it" from "the copy lost it".
    """

    if not source_dir.is_dir():
        return {
            "schema_version": DEMO_BUNDLE_SCHEMA_VERSION,
            "status": STATUS_UNAVAILABLE_SOURCE,
            "reason": "no matrix artifact directory to bundle; run the case matrix first",
            "source_dir_name": source_dir.name,
            "cases": [],
            "files": [],
        }

    matrix = _load_json(source_dir / "summary.json") or {}
    wanted = set(case_ids or [])
    case_dirs = [
        path
        for path in available_recorded_cases(source_dir)
        if not wanted or path.name in wanted
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []

    def _record(source: Path, logical: str) -> bool:
        target = output_dir / logical
        if not source.is_file():
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        digest = _sha256_file(target)
        if digest is None:
            return False
        files.append(
            {"logical_path": logical, "sha256": digest, "byte_size": target.stat().st_size}
        )
        return True

    cases: list[dict[str, Any]] = []
    for case_dir in case_dirs:
        case_id = case_dir.name
        missing: list[str] = []
        for name in REQUIRED_CASE_FILES + OPTIONAL_CASE_FILES:
            if not _record(case_dir / name, f"{case_id}/{name}"):
                missing.append(name)
        screenshots = sorted((case_dir / SCREENSHOT_DIR_NAME).glob("*.png")) if (
            case_dir / SCREENSHOT_DIR_NAME
        ).is_dir() else []
        for image in screenshots:
            _record(image, f"{case_id}/{SCREENSHOT_DIR_NAME}/{image.name}")
        result = _load_json(case_dir / "analysis_result.json") or {}
        manifest = _load_json(case_dir / "screenshot_manifest.json")
        cases.append(
            {
                "case_id": case_id,
                "company_name": result.get("company_name"),
                "stock_code": result.get("stock_code"),
                "status": result.get("status"),
                "verified_risk_count": len(result.get("verified_risks") or []),
                "pending_risk_count": len(result.get("pending_risks") or []),
                "screenshot_count": len(screenshots),
                "screenshot_manifest_status": (manifest or {}).get("status"),
                "replayable": "analysis_result.json" not in missing,
                "missing_files": missing,
            }
        )

    for name in MATRIX_FILES:
        _record(source_dir / name, name)

    replayable = [case for case in cases if case["replayable"]]
    return {
        "schema_version": DEMO_BUNDLE_SCHEMA_VERSION,
        "status": STATUS_BUNDLED if replayable else STATUS_NO_CASES,
        # A bundle is identified by the run it copies, not by where that run sat
        # on someone's disk.
        "source_dir_name": source_dir.name,
        "matrix_identity": {
            "config": matrix.get("config"),
            "demo_version": matrix.get("demo_version"),
            "code_base_sha": matrix.get("code_base_sha"),
            "code_base_dirty": matrix.get("code_base_dirty"),
            "cases_manifest_sha256": matrix.get("cases_manifest_sha256"),
            "config_sha256": matrix.get("config_sha256"),
        },
        "case_count": len(cases),
        "replayable_case_count": len(replayable),
        "file_count": len(files),
        "total_byte_size": sum(int(item["byte_size"]) for item in files),
        "requires_network": False,
        "requires_provider_credentials": False,
        "requires_prospectus_pdf": False,
        "statement": (
            "Every file here was written by the recorded run. Opening this bundle replays that "
            "run; it does not re-analyse anything, and it cannot produce a result the run did "
            "not already produce."
        ),
        "cases": cases,
        "files": files,
    }


def verify_demo_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Re-hash every listed file before the bundle is put on a screen."""

    manifest = _load_json(bundle_dir / MANIFEST_NAME)
    if manifest is None:
        return {
            "passed": False,
            "reason": f"no {MANIFEST_NAME} in this directory, so nothing can be verified",
            "checked_file_count": 0,
            "mismatched": [],
            "missing": [],
        }
    mismatched: list[str] = []
    missing: list[str] = []
    for item in manifest.get("files", []) or []:
        path = bundle_dir / str(item.get("logical_path") or "")
        if not path.is_file():
            missing.append(str(item.get("logical_path")))
            continue
        if _sha256_file(path) != item.get("sha256"):
            mismatched.append(str(item.get("logical_path")))
    return {
        "passed": not mismatched and not missing,
        "reason": None if not (mismatched or missing) else "bundle contents do not match the manifest",
        "checked_file_count": len(manifest.get("files", []) or []),
        "mismatched": mismatched,
        "missing": missing,
    }


def render_demo_script(manifest: Mapping[str, Any], cases: Sequence[RecordedCase]) -> str:
    """A walkthrough built from the recorded runs, not from a wish list.

    Each step names what is on the screen and what it is honest to say about it,
    including the channels that were not available -- those lines are the ones a
    demo most often skips.
    """

    identity = manifest.get("matrix_identity") or {}
    lines = [
        "# 演示脚本 — 三案例静态备份",
        "",
        f"- 来源运行：`{manifest.get('source_dir_name')}` · config `{identity.get('config') or '—'}`",
        f"- 代码版本 `{identity.get('code_base_sha') or '—'}`"
        + ("（工作树有未提交改动）" if identity.get("code_base_dirty") else ""),
        f"- 可回放案例 {manifest.get('replayable_case_count')}/{manifest.get('case_count')}"
        f" · 文件 {manifest.get('file_count')} 个",
        "- **本备份不需要网络、不需要模型凭证、不需要招股书 PDF**：所有内容都是那次运行写下的产物。",
        "",
        "> 演示时请始终说明这是**已记录运行的回放**。回放不会重新分析，也不会产生那次运行没有产生的结论。",
        "",
        "## 开场（约 1 分钟）",
        "",
        "1. 打开界面，选择「演示备份」并载入案例；顶部会显示回放标识、来源运行 config 与代码版本。",
        "2. 说明产品链路：文档解析 → 文档风险特征 → 市场特征 → 预测 → Evidence/可解释 → "
        "Final Supervisor → 最终报告；缺失的可选通道会在页面内如实显示。",
        "",
    ]
    for index, case in enumerate(cases, start=1):
        provenance = case.provenance
        screenshots = case.screenshots or {}
        verified = case.result.get("verified_risks") or []
        pending = case.result.get("pending_risks") or []
        channels = {
            item.get("channel"): item.get("status")
            for item in ((case.result.get("metadata") or {}).get("final_supervision") or {}).get(
                "channel_states", []
            )
            if isinstance(item, dict)
        }
        gate = case.gate_e1 or {}
        lines += [
            f"## 案例 {index}：{case.company_name}（{case.stock_code}）",
            "",
            f"- 载入 `{case.case_id}`；招股书 SHA-256 `{provenance.get('prospectus_sha256') or '—'}`"
            f"（{provenance.get('prospectus_page_count') or '—'} 页）",
            f"- 分析标识 `{provenance.get('analysis_id') or '—'}` · workflow "
            f"`{provenance.get('workflow_version') or '—'}`",
            "",
            "**要展示的**：",
        ]
        if verified:
            for risk in verified:
                evidence = risk.get("evidence") or []
                pages = sorted({str(item.get("page")) for item in evidence if item.get("page")})
                lines.append(
                    f"- 已验证风险 **{risk.get('risk_code')}**（{risk.get('level')}）"
                    f"：{len(evidence)} 条 Evidence，原文页 {('、'.join(pages)) or '—'}"
                    + ("；有确定性 Calculation 支撑数值" if risk.get("calculation") else "")
                )
        else:
            lines.append(
                "- 本案文档通道**没有**提出正式风险。这一条要照实说：系统不会为了好看补一个风险。"
            )
        if pending:
            lines.append(
                "- 待复核："
                + "、".join(f"{risk.get('risk_code')}（{risk.get('level')}）" for risk in pending)
                + "，说明证据不足以定案，进入人工复核而不是被强行下结论。"
            )
        if screenshots.get("screenshot_count"):
            lines.append(
                f"- Evidence 截图 {screenshots.get('screenshot_count')} 张"
                f"（精确定位 {screenshots.get('precise_localisation_count')}）"
                "：红框来自 PyMuPDF 在原页上的真实坐标，页级回退会在图注中标明。"
            )
        else:
            lines.append("- 本案没有截图产物；界面会显示无图，不用其它案例的页面顶替。")
        lines += ["", "**要照实说的**："]
        unavailable = [f"`{name}`={state}" for name, state in sorted(channels.items()) if state != "available"]
        lines.append(
            "- 通道缺失：" + ("、".join(unavailable) if unavailable else "无") + (
                "；缺失通道不贡献任何事实，页面照常完成但不补数。" if unavailable else "。"
            )
        )
        lines.append(
            "- Final Supervisor："
            + ("real provider 仲裁成功" if gate.get("successful_llm_arbitration") else "未由真实 provider 仲裁")
            + ("，Gate E1 满足。" if gate.get("satisfied") else "，Gate E1 未满足，未满足项已记录。")
        )
        reviews = (case.human_review or {}).get("review_count", 0)
        lines.append(
            f"- 人工复核 {reviews} 条"
            + ("。" if reviews else "：未复核不等于已认可，这一条不要略过。")
        )
        if case.missing:
            lines.append(f"- 该案缺少的产物：{'、'.join(case.missing)}（缺什么说什么）。")
        lines.append("")
    lines += [
        "## 收尾",
        "",
        "- 批量报告页展示跨案例排查顺序，并当场读出排序规则：**这是对已记录风险计数的排序，"
        "不是分数、不是概率、不是上市后表现预测**。",
        "- 如被问到指标：M1/M2/M4、模型晋升与 one-shot Validation 尚未关闭，以 "
        "`docs/V0.4_RELEASE_ACCEPTANCE.md` 为准，不在演示中宣称 COMPETITION_READY。",
        "",
    ]
    return "\n".join(lines)


__all__ = [
    "DEMO_BUNDLE_SCHEMA_VERSION",
    "DEMO_SCRIPT_NAME",
    "MANIFEST_NAME",
    "MATRIX_FILES",
    "OPTIONAL_CASE_FILES",
    "REQUIRED_CASE_FILES",
    "RecordedCase",
    "ReplayScreenshots",
    "SCREENSHOT_DIR_NAME",
    "STATUS_BUNDLED",
    "STATUS_NO_CASES",
    "STATUS_UNAVAILABLE_SOURCE",
    "available_recorded_cases",
    "build_demo_bundle",
    "load_recorded_case",
    "render_demo_script",
    "replay_screenshots",
    "screenshot_index",
    "verify_demo_bundle",
]
