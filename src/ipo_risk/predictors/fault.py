"""Deliberately failing predictor for resilience and UI verification."""


class FaultPredictor:
    name = "fault_predictor"

    def predict(self, risks, market):
        raise RuntimeError("Injected predictor failure for resilience verification")
