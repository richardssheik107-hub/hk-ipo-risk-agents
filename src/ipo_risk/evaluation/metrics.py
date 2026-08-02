"""Small deterministic metrics for future labelled evaluation sets."""
def precision_recall_f1(predicted: set[str], expected: set[str]) -> tuple[float, float, float]:
    hits = len(predicted & expected)
    precision = hits / len(predicted) if predicted else 0.0
    recall = hits / len(expected) if expected else 0.0
    return precision, recall, 2 * precision * recall / (precision + recall) if precision + recall else 0.0
