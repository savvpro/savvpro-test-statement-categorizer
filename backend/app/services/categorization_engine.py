from typing import Any

from app.services.category_rules import categorize_by_rules
from app.services.onnx_classifier import ONNXTransactionClassifier


class CategorizationEngine:
    """Apply deterministic rules first, then use ONNX as a fallback."""

    def __init__(
        self,
        classifier: ONNXTransactionClassifier | None = None,
        confidence_threshold: float = 0.80,
    ) -> None:
        self.classifier = classifier
        self.confidence_threshold = confidence_threshold

    def categorize(
        self,
        description: str,
        amount: float = 0.0,
    ) -> dict[str, Any]:
        description = description.strip()

        if not description:
            return {
                "category": "Needs Review",
                "status": "needs_review",
                "reason": "Transaction description is empty.",
                "confidence": 0.0,
                "exclude_from_spending": True,
            }

        # Clear, explainable rules always take priority.
        rule_result = categorize_by_rules(description, amount)

        if rule_result and rule_result["category"] != "Needs Review":
            return {
                **rule_result,
                "confidence": 1.0,
                "source": "rule",
            }

        # Unknown transactions are reviewed rather than blindly guessed.
        if self.classifier is None:
            return {
                **(rule_result or {}),
                "category": "Needs Review",
                "status": "needs_review",
                "reason": "No reliable rule matched; classifier unavailable.",
                "confidence": 0.0,
                "exclude_from_spending": True,
                "source": "none",
            }

        prediction = self.classifier.predict(description)
        confidence = prediction["confidence"]

        if confidence < self.confidence_threshold:
            return {
                "category": "Needs Review",
                "status": "needs_review",
                "reason": "Model prediction is below the confidence threshold.",
                "confidence": confidence,
                "exclude_from_spending": True,
                "source": "onnx",
                "suggested_category": prediction["category"],
            }

        return {
            "category": prediction["category"],
            "status": "categorized",
            "reason": "Suggested by the ONNX model; review if incorrect.",
            "confidence": confidence,
            "exclude_from_spending": prediction["category"] in {
                "Transfer",
                "Income",
            },
            "source": "onnx",
        }