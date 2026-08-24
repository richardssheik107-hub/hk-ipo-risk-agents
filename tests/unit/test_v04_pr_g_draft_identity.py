"""The real-case PR-G/PR-H draft binds runtime identities deterministically."""

from __future__ import annotations

import ast
from pathlib import Path


def test_real_manifest_builder_sets_an_explicit_content_bound_request_id() -> None:
    source = Path("scripts/build_v04_pr_g_manifest.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    requests = [
        node for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == "IPOAnalysisRequest"
    ]
    assert len(requests) == 1
    keywords = {item.arg for item in requests[0].keywords}
    assert "request_id" in keywords
    assert "prospectus_sha256" in source
    assert "uuid5" in source
