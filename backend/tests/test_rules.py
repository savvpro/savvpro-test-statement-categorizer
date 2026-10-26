from app import rules


def test_keywords_are_uppercase():
    all_lists = [rules.NOT_SPENDING, rules.REFUND_WORDS,
                 rules.INCOME_WORDS, rules.AMBIGUOUS]
    all_lists += list(rules.CATEGORIES.values())
    for words in all_lists:
        for w in words:
            assert w == w.upper(), f"keyword must be uppercase: {w}"


def test_no_keyword_in_two_categories():
    seen = {}
    for cat, words in rules.CATEGORIES.items():
        for w in words:
            assert w not in seen, f"{w} is in both {seen[w]} and {cat}"
            seen[w] = cat


def test_threshold_is_sane():
    assert 0 < rules.CONFIDENCE_THRESHOLD < 1