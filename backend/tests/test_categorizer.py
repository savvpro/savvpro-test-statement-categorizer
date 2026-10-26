from categorizer import categorize_transaction


def test_adobe_is_software():
    result = categorize_transaction(
        "ADOBE CREATIVE CLOUD",
        -5000,
    )

    assert result["category"] == "Software"
    assert result["needs_review"] is False


def test_uber_is_travel():
    result = categorize_transaction(
        "UBER TRIP",
        -850,
    )

    assert result["category"] == "Travel"


def test_unknown_requires_review():
    result = categorize_transaction(
        "RANDOM MERCHANT XYZ",
        -700,
    )

    assert result["category"] == "Needs Review"
    assert result["needs_review"] is True


def test_transfer():
    result = categorize_transaction(
        "TRANSFER TO SAVINGS",
        -10000,
    )

    assert result["category"] == "Transfer / Not Expense"


def test_refund():
    result = categorize_transaction(
        "REFUND ADOBE",
        5000,
    )

    assert result["category"] == "Refund"