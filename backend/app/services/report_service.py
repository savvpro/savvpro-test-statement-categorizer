
from sqlalchemy.orm import Session

from app.db.models import Statement, Transaction


def generate_summary(db: Session, statement_id: int | None = None) -> dict:
    """Generate a financial summary for one statement, defaulting to the latest."""
    if statement_id is None:
        statement = (
            db.query(Statement)
            .order_by(Statement.id.desc())
            .first()
        )
        if statement is None:
            transactions = []
        else:
            statement_id = statement.id
            transactions = (
                db.query(Transaction)
                .filter(Transaction.statement_id == statement_id)
                .all()
            )
    else:
        transactions = (
            db.query(Transaction)
            .filter(Transaction.statement_id == statement_id)
            .all()
        )

    total_income = 0.0
    total_spending = 0.0
    total_refunds = 0.0
    review_count = 0

    for transaction in transactions:
        amount = transaction.amount
        category = transaction.category
        status = transaction.status

        if status == "needs_review":
            review_count += 1

        if category == "Income":
            if amount > 0:
                total_income += amount
        elif category == "Refund":
            total_refunds += abs(amount)
        elif category == "Transfer" or category == "Needs Review":
            continue
        elif amount < 0:
            total_spending += abs(amount)

    return {
        "statement_id": statement_id,
        "transaction_count": len(transactions),
        "total_income": round(total_income, 2),
        "total_spending": round(total_spending, 2),
        "total_refunds": round(total_refunds, 2),
        "net_spending": round(max(0.0, total_spending - total_refunds), 2),
        "needs_review_count": review_count,
    }
