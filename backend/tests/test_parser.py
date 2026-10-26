import pytest

from backend.app.parser import StatementError, parse_csv


def parse(text, **options):
    return parse_csv(text.encode("utf-8"), **options)


def test_signed_amounts_preserve_cents_and_original_description():
    result = parse('date,description,amount,currency\n2026-10-01,"ADOBE, INC",-59.99,USD')
    assert result.currency == "USD"
    assert result.transactions[0].amount_cents == -5999
    assert result.transactions[0].description == "ADOBE, INC"


def test_bom_and_bank_header_aliases():
    result = parse(
        "\ufeffTransaction Date,Details,Debit,Credit\n01/10/2026,Software,59.99,",
        date_format="DMY",
        currency="PKR",
    )
    assert result.transactions[0].date == "2026-10-01"
    assert result.transactions[0].amount_cents == -5999
    assert result.currency == "PKR"


def test_explicit_positive_spending_convention():
    result = parse(
        "date,description,amount\n2026-10-01,ADOBE,59.99", amount_convention="positive_expense"
    )
    assert result.transactions[0].amount_cents == -5999


def test_credit_column_is_inflow():
    result = parse("date,description,debit,credit\n2026-10-01,Refund,,18.50")
    assert result.transactions[0].amount_cents == 1850


@pytest.mark.parametrize(
    "text,fragment",
    [
        ("date,amount\n2026-10-01,-1", "description"),
        ("date,description,amount\n2026-10-01,Thing,NaN", "amount"),
        ("date,description,amount\n2026-10-01,Thing,Infinity", "amount"),
        ("date,description,amount\n2026-10-01,Thing,1.001", "decimal"),
        ("date,description,amount\n2026-02-30,Thing,1", "date"),
        ("date,description,amount\n10/11/2026,Thing,1", "date"),
        ("date,description,amount\n2026-10-01,,1", "description"),
        ("date,description,amount\n2026-10-01,Thing,0", "zero"),
        ("date,description,debit,credit\n2026-10-01,Thing,1,2", "debit"),
        ("date,description,amount,currency\n2026-10-01,A,-1,USD\n2026-10-02,B,-1,EUR", "currency"),
        ("date,description,amount,currency\n2026-10-01,A,-1,XYZ", "currency"),
        ("date,description,amount\n2026-10-01,A,-1,extra", "columns"),
        ("date,description,amount,Amount\n2026-10-01,A,-1,-2", "duplicate"),
        ("date,description,amount\n", "transactions"),
        ('date,description,amount\n2026-10-01,A,"bad', "CSV"),
        ("date,description,amount\n2026-10-01,A,999999999999", "amount"),
    ],
)
def test_invalid_input_is_rejected_without_partial_import(text, fragment):
    with pytest.raises(StatementError, match=fragment):
        parse(text)


def test_thousands_separator_and_parentheses():
    result = parse('date,description,amount\n2026-10-01,A,"(1,234.56)"')
    assert result.transactions[0].amount_cents == -123456


def test_invalid_grouping_is_not_silently_changed():
    with pytest.raises(StatementError, match="amount"):
        parse('date,description,amount\n2026-10-01,A,"12,34"')


def test_possible_duplicates_retained_and_flagged():
    result = parse("date,description,amount\n2026-10-01,ADOBE,-10\n2026-10-01,adobe,-10")
    assert len(result.transactions) == 2
    assert result.transactions[1].duplicate_of == 2


def test_duplicate_source_ids_flagged_even_if_values_differ():
    result = parse("id,date,description,amount\nx,2026-10-01,A,-10\nx,2026-10-02,B,-20")
    assert result.transactions[1].duplicate_of == 2


def test_size_and_encoding_limits():
    with pytest.raises(StatementError, match="5 MB"):
        parse_csv(b"x" * (5 * 1024 * 1024 + 1))
    with pytest.raises(StatementError, match="UTF-8"):
        parse_csv(b"\xff\xfe")


def test_row_limit():
    with pytest.raises(StatementError, match="10,000"):
        parse("date,description,amount\n" + "2026-10-01,A,-1\n" * 10001)
