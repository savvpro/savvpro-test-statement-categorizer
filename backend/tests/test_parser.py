from app.parser import parse_csv


def test_parse_csv_supports_credit_and_debit_rows():
    rows = b"Date,Description,Amount,Currency\n2026-01-02,CLIENT PAYMENT,1200,USD\n2026-01-03,ADOBE,-30,USD\n"
    result = parse_csv(rows)
    assert len(result) == 2
    assert result[0].direction == "income"
    assert result[1].direction == "expense"


def test_parse_expense_dataset_without_statement_metadata():
    rows = b"expense_id,amount,merchant,description,category\nSEED0,2713.64,Swiggy,bought groceries at dmart,Food & Dining\n"
    result = parse_csv(rows)
    assert result[0].date is None
    assert result[0].description == "Swiggy - bought groceries at dmart"
    assert result[0].direction == "expense"
