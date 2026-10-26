# Below this confidence a match is not trusted: the row goes to Needs Review and the
# rule's category is kept only as a suggestion.
CONFIDENCE_THRESHOLD = 0.8

DEFAULT_RULE_CONFIDENCE = 0.95
DEFAULT_KEYWORD_CONFIDENCE = 0.75

# Positive amount on a card with no rule matched: most likely money back from a merchant.
CARD_REFUND_CONFIDENCE = 0.85
