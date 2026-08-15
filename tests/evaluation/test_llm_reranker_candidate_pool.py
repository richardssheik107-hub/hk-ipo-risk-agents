from ipo_risk.retrieval.llm_reranker import _excerpt


def test_excerpt_is_bounded_and_deterministic():
    text = "x" * 3000 + " revenue " + "y" * 3000
    first = _excerpt(text, ["revenue"])
    assert first == _excerpt(text, ["revenue"])
    assert len(first[0]) == 2400
    assert "revenue" in first[0]
    assert first[3] is True
