
from app.services.onnx_classifier import ONNXTransactionClassifier

classifier = ONNXTransactionClassifier()

transactions = [
    "[debit] ADOBE CREATIVE CLOUD",
    "[debit] UBER *TRIP",
    "[credit] SALARY PAYMENT",
    "[debit] TRANSFER TO SAVINGS",
    "[credit] REFUND AMAZON",
    "[debit] JOES CAFE 9921",
]

for transaction in transactions:
    result = classifier.predict(transaction)
    print(
        "{} -> {} ({:.1%})".format(
            transaction,
            result["category"],
            result["confidence"],
        )
    )
