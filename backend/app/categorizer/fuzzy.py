from rapidfuzz import fuzz


def getfuzzyscore(text: str, target: str) -> int:
    return int(fuzz.token_set_ratio(text, target))