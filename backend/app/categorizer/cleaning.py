import re
from app.categorizer.rulesdata import NOISETOKENS

def cleantext(raw: str) -> str:
    text = raw.upper()
    text = re.sub(r'\d{4,}', '', text)
    for token in NOISETOKENS:
        text = re.sub(rf'\b{token}\b', '', text)
    text = " ".join(text.split())
    return text