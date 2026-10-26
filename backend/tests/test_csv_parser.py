"""Tests for the CSV parser (csv_parser.py)."""


from app.parsing.csv_parser import _detect_column_type, _parse_amount, _parse_date, parse_csv


def _csv_bytes(lines):
    return "\n".join(lines).encode("utf-8")


class TestParseDate:
    def test_iso_date(self):
        assert _parse_date("2025-01-15").isoformat() == "2025-01-15"

    def test_us_date(self):
        assert _parse_date("01/15/2025").isoformat() == "2025-01-15"

    def test_empty(self):
        assert _parse_date("") is None

    def test_invalid(self):
        assert _parse_date("not-a-date") is None


class TestParseAmount:
    def test_plain_number(self):
        assert _parse_amount("1234.50") == 1234.50

    def test_with_dollar_sign(self):
        assert _parse_amount("$1,234.50") == 1234.50

    def test_parentheses_negative(self):
        assert _parse_amount("(45.00)") == -45.00

    def test_explicit_negative(self):
        assert _parse_amount("-45.00") == -45.00

    def test_empty(self):
        assert _parse_amount("") is None

    def test_invalid(self):
        assert _parse_amount("abc") is None


class TestDetectColumnType:
    def test_date_variants(self):
        assert _detect_column_type("Date") == "date"
        assert _detect_column_type("Transaction Date") == "date"

    def test_description_variants(self):
        assert _detect_column_type("Description") == "description"
        assert _detect_column_type("Details") == "description"

    def test_amount_debit_credit(self):
        assert _detect_column_type("Amount") == "amount"
        assert _detect_column_type("Debit") == "debit"
        assert _detect_column_type("Credit") == "credit"

    def test_unknown(self):
        assert _detect_column_type("Random Column") is None


class TestSingleAmountColumn:
    def test_basic_parsing(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,STARBUCKS,-5.50",
            "2025-01-16,ADOBE CREATIVE CLOUD,-29.99",
        ]))
        assert len(result["transactions"]) == 2
        assert result["transactions"][0] == {
            "date": "2025-01-15",
            "description": "STARBUCKS",
            "amount": -5.50,
            "is_duplicate": False,
            "row_number": 2,
        }
        assert result["warnings"] == []

    def test_positive_amount_is_income(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,CLIENT PAYMENT,1000.00",
        ]))
        assert result["transactions"][0]["amount"] == 1000.00

    def test_dollar_and_commas(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            '2025-01-15,STORE,"-$1,234.50"',
        ]))
        assert result["transactions"][0]["amount"] == -1234.50

    def test_parentheses_negative(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,STORE,(45.00)",
        ]))
        assert result["transactions"][0]["amount"] == -45.00

    def test_us_dates(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "01/15/2025,STARBUCKS,-5.50",
        ]))
        assert result["transactions"][0]["date"] == "2025-01-15"

    def test_empty_amount_skipped(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,STORE,",
        ]))
        assert len(result["transactions"]) == 0
        assert any("unparseable amount" in w for w in result["warnings"])


class TestDebitCreditColumns:
    def test_debit_is_negative(self):
        result = parse_csv(_csv_bytes([
            "Transaction Date,Details,Debit,Credit",
            "01/15/2025,STARBUCKS,$5.50,",
        ]))
        assert result["transactions"][0]["amount"] == -5.50

    def test_credit_is_positive(self):
        result = parse_csv(_csv_bytes([
            "Transaction Date,Details,Debit,Credit",
            '01/15/2025,CLIENT PAYMENT,,"$1,000.00"',
        ]))
        assert result["transactions"][0]["amount"] == 1000.00

    def test_both_debit_and_credit_uses_debit(self):
        result = parse_csv(_csv_bytes([
            "Transaction Date,Details,Debit,Credit",
            "01/15/2025,STORE,$10.00,$5.00",
        ]))
        assert result["transactions"][0]["amount"] == -10.00
        assert any("both debit and credit" in w for w in result["warnings"])



class TestHeaderVariants:
    def test_alternative_headers(self):
        result = parse_csv(_csv_bytes([
            "Posted Date,Payee,Amount",
            "2025-01-15,Joes Cafe,-12.00",
        ]))
        assert len(result["transactions"]) == 1

    def test_missing_date_column(self):
        result = parse_csv(_csv_bytes([
            "Description,Amount",
            "STORE,-10.00",
        ]))
        assert len(result["transactions"]) == 0
        assert any("No date column" in w for w in result["warnings"])

    def test_missing_amount_columns(self):
        result = parse_csv(_csv_bytes([
            "Date,Description",
            "2025-01-15,STORE",
        ]))
        assert len(result["transactions"]) == 0
        assert any("No amount" in w for w in result["warnings"])


class TestDuplicates:
    def test_duplicate_flagged(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,ADOBE CREATIVE CLOUD,-29.99",
            "2025-01-15,ADOBE CREATIVE CLOUD,-29.99",
        ]))
        assert len(result["transactions"]) == 2
        assert result["transactions"][0]["is_duplicate"] is False
        assert result["transactions"][1]["is_duplicate"] is True
        assert any("duplicate" in w.lower() for w in result["warnings"])

    def test_same_description_different_amount_not_duplicate(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,STARBUCKS,-5.50",
            "2025-01-15,STARBUCKS,-8.00",
        ]))
        assert result["transactions"][0]["is_duplicate"] is False
        assert result["transactions"][1]["is_duplicate"] is False


class TestEdgeCases:
    def test_blank_description(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "2025-01-20,,-45.00",
        ]))
        assert len(result["transactions"]) == 1
        assert result["transactions"][0]["description"] == ""
        assert any("blank description" in w for w in result["warnings"])

    def test_foreign_currency_warning(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "2025-01-21,FOREIGN CURRENCY FEE EUR,-3.50",
        ]))
        assert len(result["transactions"]) == 1
        assert any("foreign currency" in w.lower() for w in result["warnings"])

    def test_empty_file(self):
        result = parse_csv(b"")
        assert result["transactions"] == []
        assert any("Empty file" in w for w in result["warnings"])

    def test_header_only(self):
        result = parse_csv(_csv_bytes(["Date,Description,Amount"]))
        assert result["transactions"] == []
        assert result["warnings"] == []

    def test_skips_empty_rows(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "",
            "2025-01-15,STORE,-10.00",
            "   ,   ,  ",
        ]))
        assert len(result["transactions"]) == 1
        assert any("empty row" in w for w in result["warnings"])

    def test_bad_date_skipped(self):
        result = parse_csv(_csv_bytes([
            "Date,Description,Amount",
            "not-a-date,STORE,-10.00",
            "2025-01-16,GOOD,-5.00",
        ]))
        assert len(result["transactions"]) == 1
        assert result["transactions"][0]["description"] == "GOOD"
        assert any("unparseable date" in w for w in result["warnings"])

