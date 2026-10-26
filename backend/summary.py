from decimal import Decimal


def build_summary(transactions):
    category_totals = {}
    income = Decimal("0")
    refunds = Decimal("0")
    transfer_in = Decimal("0")
    transfer_out = Decimal("0")
    review_in = Decimal("0")
    review_out = Decimal("0")
    review_count = 0

    for transaction in transactions:
        amount = Decimal(transaction["amount"])
        kind = transaction["type"]
        category = transaction["category"]

        if transaction["needs_review"]:
            review_count += 1
            if amount > 0:
                review_in += amount
            else:
                review_out += abs(amount)
            continue

        if kind == "transfer":
            if amount > 0:
                transfer_in += amount
            else:
                transfer_out += abs(amount)

        elif kind == "income":
            income += amount

        elif kind in {"expense", "refund"}:
            category_totals.setdefault(category, Decimal("0"))
            category_totals[category] -= amount

            if kind == "refund":
                refunds += amount

    net_expenses = sum(category_totals.values(), Decimal("0"))

    return {
        "currency": transactions[0]["currency"] if transactions else None,
        "category_net_expenses": {
            category: format(total, ".2f")
            for category, total in sorted(category_totals.items())
        },
        "total_income": format(income, ".2f"),
        "total_refunds": format(refunds, ".2f"),
        "net_expenses": format(net_expenses, ".2f"),
        "transfers_in": format(transfer_in, ".2f"),
        "transfers_out": format(transfer_out, ".2f"),
        "needs_review_count": review_count,
        "unresolved_incoming": format(review_in, ".2f"),
        "unresolved_outgoing": format(review_out, ".2f"),
    }