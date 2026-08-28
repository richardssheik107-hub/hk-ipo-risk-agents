from ipo_risk.core.container import default_registry
from ipo_risk.core.config import load_settings
from ipo_risk.retrieval.hybrid_bm25 import HybridBM25DocumentRetriever


def test_hybrid_bm25_is_an_additive_opt_in_registry_component() -> None:
    retriever = default_registry().create("retriever", "hybrid_bm25")
    assert isinstance(retriever, HybridBM25DocumentRetriever)


def test_competition_ai_and_offline_use_the_same_candidate_policy() -> None:
    ai = load_settings("configs/v045_competition_ai.yaml")
    offline = load_settings("configs/v045_competition_offline.yaml")
    assert ai.retriever == offline.retriever == "hybrid_bm25"
