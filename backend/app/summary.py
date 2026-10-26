from decimal import Decimal

from .models import EXPENSE_CATEGORIES, Category, Summary, Transaction


def summarize(transactions: list[Transaction]) -> Summary:
    expenses = income = refunds = transfers_in = transfers_out = Decimal(0)
    unclassified_in = unclassified_out = net_movement = Decimal(0)
    expense_categories = {category: Decimal(0) for category in EXPENSE_CATEGORIES}
    for transaction in transactions:
        amount = Decimal(transaction.amount)
        category = transaction.category
        net_movement += amount
        if category == Category.TRANSFER:
            transfers_in += max(amount, Decimal(0))
            transfers_out += max(-amount, Decimal(0))
        elif category == Category.REFUND:
            refunds += amount
        elif category == Category.INCOME:
            income += amount
        elif category in EXPENSE_CATEGORIES:
            expenses -= amount
            expense_categories[category] -= amount
        elif amount > 0:
            unclassified_in += amount
        else:
            unclassified_out -= amount

    return Summary(
        expenses=f"{expenses:.2f}",
        income=f"{income:.2f}",
        refunds=f"{refunds:.2f}",
        transfers=f"{transfers_in + transfers_out:.2f}",
        transfers_in=f"{transfers_in:.2f}",
        transfers_out=f"{transfers_out:.2f}",
        unclassified_in=f"{unclassified_in:.2f}",
        unclassified_out=f"{unclassified_out:.2f}",
        net_movement=f"{net_movement:.2f}",
        review_count=sum(transaction.needs_review for transaction in transactions),
        transaction_count=len(transactions),
        expense_categories={
            category: f"{amount:.2f}" for category, amount in expense_categories.items()
        },
    )
