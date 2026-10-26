import re


def normalize(description: str) -> str:
    """'UBER *TRIP 8821' -> 'UBER TRIP' so rules match one clean form."""
    text = (description or "").upper()
    text = re.sub(r"[^A-Z\s&]", " ", text)  # drop digits, *, #, codes
    return re.sub(r"\s+", " ", text).strip()
