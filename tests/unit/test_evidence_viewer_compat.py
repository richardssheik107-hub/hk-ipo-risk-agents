from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "app" / "evidence_viewer_compat.py"


def _load_module():
    # The compatibility module imports the real Evidence Viewer, so load it only
    # after the app directory is importable in this isolated unit test.
    app_dir = str(MODULE_PATH.parent)
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    spec = importlib.util.spec_from_file_location(
        "evidence_viewer_compat_test", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_supports_current_replay_signature() -> None:
    module = _load_module()

    def viewer(payload, pdf_bytes, replay=None):
        return None

    assert module._supports_replay(viewer) is True


def test_detects_legacy_two_argument_signature() -> None:
    module = _load_module()

    def viewer(payload, pdf_bytes):
        return None

    assert module._supports_replay(viewer) is False


def test_forwards_replay_and_keyword_only_expert_to_current_viewer() -> None:
    module = _load_module()
    calls = []

    def viewer(payload, pdf_bytes, replay=None, *, expert=False):
        calls.append((payload, pdf_bytes, replay, expert))

    module._render_evidence_viewer = viewer
    payload = {"case": "current"}
    pdf_bytes = b"%PDF-current"
    replay = object()

    module.render_evidence_viewer(payload, pdf_bytes, replay, expert=True)

    assert calls == [(payload, pdf_bytes, replay, True)]


def test_legacy_three_argument_viewer_receives_replay_but_not_expert() -> None:
    module = _load_module()
    calls = []

    def viewer(payload, pdf_bytes, replay=None):
        calls.append((payload, pdf_bytes, replay))

    module._render_evidence_viewer = viewer
    payload = {"case": "legacy-replay"}
    pdf_bytes = b"%PDF-replay"
    replay = object()

    module.render_evidence_viewer(payload, pdf_bytes, replay, expert=True)

    assert calls == [(payload, pdf_bytes, replay)]


def test_legacy_two_argument_viewer_ignores_replay_and_expert() -> None:
    module = _load_module()
    calls = []

    def viewer(payload, pdf_bytes):
        calls.append((payload, pdf_bytes))

    module._render_evidence_viewer = viewer
    payload = {"case": "legacy-live"}
    pdf_bytes = b"%PDF-live"

    module.render_evidence_viewer(payload, pdf_bytes, object(), expert=True)

    assert calls == [(payload, pdf_bytes)]
