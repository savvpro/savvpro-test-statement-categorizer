"""Small synthetic demonstration of the Phase 1 categorization engine.

Demonstrates deterministic classification, confidence scoring, explanations,
and manual review flagging for independent developers and freelancers.
"""

from decimal import Decimal
from app.schemas.transaction import TransactionInput
from app.services.categorizer import CategorizationEngine


def main() -> None:
    engine = CategorizationEngine()

    synthetic_statement = [
        ("IDE SOFTWARE SUBSCRIPTION", Decimal("-15.00")),
        ("GITHUB-COPILOT MONTHLY", Decimal("-10.00")),
        ("AWS*BILLING SERVICES", Decimal("-45.20")),
        ("DIGITALOCEAN DROPLET", Decimal("-12.00")),
        ("COMCAST INTERNET BILL", Decimal("-69.99")),
        ("MONTHLY SERVICE FEE", Decimal("-12.00")),
        ("CLIENT PAYMENT - ACME CONSULTING", Decimal("1850.00")),
        ("INVOICE #2048 SETTLEMENT", Decimal("950.00")),
        ("REFUND CLOUDHOST SERVICES", Decimal("25.00")),
        ("TRANSACTION REVERSED BY ISSUER", Decimal("50.00")),
        ("TRANSFER TO SAVINGS ACCT", Decimal("-300.00")),
        ("WIRE TRANSFER TO SUPPLIER", Decimal("-450.00")),
        ("AMAZON.COM*RETAIL STORE", Decimal("-38.50")),
        ("JOE'S CAFE LUNCH", Decimal("-14.25")),
        ("UBER *TRIP AIRPORT", Decimal("-28.40")),
        ("MYSTERY STORE #441", Decimal("-18.75")),
        ("VERIFICATION HOLD", Decimal("0.00")),
    ]

    print("=" * 95)
    print(" LedgerLens -- Phase 1 Categorization Engine Demonstration")
    print("=" * 95)
    print(f"{'Original Description':<32} | {'Amount':>10} | {'Category':<16} | {'Score':>5} | {'Review?':<7} | {'Reason'}")
    print("-" * 95)

    for desc, amt in synthetic_statement:
        tx = TransactionInput(original_description=desc, amount=amt)
        result = engine.categorize(tx)
        rev_str = "YES" if result.review_required else "No"
        print(f"{desc:<32} | {str(amt):>10} | {result.category:<16} | {result.confidence_score:>5.2f} | {rev_str:<7} | {result.explanation}")

    print("=" * 95)


if __name__ == "__main__":
    main()
