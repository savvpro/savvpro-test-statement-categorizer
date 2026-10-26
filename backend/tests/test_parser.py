from app.parser.statement_parser import parse_statement_csv


SAMPLE = """Transaction Date,Description,Amount
01/15/2025,ADOBE CREATIVE CLOUD,-52.99
01/16/2025,UBER *TRIP,-18.40
01/17/2025,TRANSFER TO SAVINGS,-500.00
"""


def test_parse_standard_csv():
    txs = parse_statement_csv(SAMPLE)
    assert len(txs) == 3
    assert txs[0].description == "ADOBE CREATIVE CLOUD"
    assert txs[0].amount == -52.99


def test_parse_debit_credit_columns():
    sample = """Date,Memo,Debit,Credit
2025-01-01,STAPLES OFFICE,-24.00,
2025-01-02,REFUND ADOBE,,52.99
"""
    txs = parse_statement_csv(sample)
    assert len(txs) == 2
    assert txs[0].amount == -24.0
    assert txs[1].amount == 52.99


def test_parse_parentheses_amount():
    sample = """Date,Description,Amount
01/01/2025,TEST MERCHANT,(10.00)
"""
    txs = parse_statement_csv(sample)
    assert txs[0].amount == -10.0
