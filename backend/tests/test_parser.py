import pytest
from app.services.parser import _parse_csv


def test_parse_valid_csv():
    content = b"date,description,amount\n2024-01-01,ADOBE,54.99\n"
    rows = _parse_csv(content)
    assert len(rows) == 1
    assert rows[0]["description"] == "ADOBE"
    assert rows[0]["amount"] == 54.99


def test_parse_missing_column():
    content = b"date,description\n2024-01-01,ADOBE\n"
    with pytest.raises(ValueError, match="Missing columns"):
        _parse_csv(content)