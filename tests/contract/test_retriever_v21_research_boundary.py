from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ipo_risk.core.container import ComponentConfigurationError, default_registry
from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21
from ipo_risk.schemas import DocumentChunk, Evidence


def test_candidate_preserves_existing_retriever_shape() -> None:
    result = DomainAwareRetrieverV21().retrieve(
        [DocumentChunk(document_id="case", chunk_id="case:page:1", page=1, text="cash and cash equivalents")],
        "cash and cash equivalents",
        limit=1,
    )
    assert all(isinstance(item, Evidence) for item in result)


def test_v21_is_not_registered() -> None:
    registry = default_registry()
    with pytest.raises(ComponentConfigurationError, match="Unregistered retriever"):
        registry.create("retriever", "domain_aware_v21_candidate")


def test_v21_has_no_downstream_or_registry_imports() -> None:
    tree = ast.parse(Path("src/ipo_risk/retrieval/domain_aware_v21.py").read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    forbidden = ("ipo_risk.agents", "ipo_risk.providers", "ipo_risk.workflows", "ipo_risk.services", "ipo_risk.core.container")
    assert not any(name.startswith(forbidden) for name in imported)
