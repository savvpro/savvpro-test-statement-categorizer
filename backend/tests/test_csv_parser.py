from app.parsers.csv_parser import CSVParser

def test_parses_sample():
    with open("../sample_data/sample_statement.csv", "rb") as f:
        rows = CSVParser().parse(f.read())
    assert len(rows) == 10
    assert rows[0].description == "SHOPIFY PAYOUT 8821"