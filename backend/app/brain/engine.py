# backend/app/brain/engine.py
from .models import Transaction, Decision, Category, CONFIDENCE_THRESHOLD
from .normalize import normalize
from .rules import refund, transfer, income, merchants

# Priority order — do not reorder casually.
LAYERS = [refund, transfer, income, merchants]

def categorize(tx: Transaction) -> Decision:
    tx.normalized = normalize(tx.description)
    for layer in LAYERS:
        d = layer.match(tx)
        if d is None:
            continue
        if d.confidence >= CONFIDENCE_THRESHOLD:
            return d
        # matched but unsure → Needs Review, keep the reason
        return Decision(Category.NEEDS_REVIEW, d.confidence,
                        f"Low confidence ({d.confidence:.2f}): {d.reason}")
    return Decision(Category.NEEDS_REVIEW, 0.0,
                    f"No rule matched ({tx.normalized})")