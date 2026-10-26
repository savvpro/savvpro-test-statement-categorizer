import re


def normalize(text: str) -> str:
    """Uppercase, strip digits/special chars, collapse spaces."""
    text = text.upper()
    text = re.sub(r'[^A-Z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text