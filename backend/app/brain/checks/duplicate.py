def duplicate_key(txn) -> tuple:
    return (txn.date, txn.description, txn.amount, txn.currency)