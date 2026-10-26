# backend/app/brain/normalize.py
import re

_NOISE = [
    r"\bPOS\b", r"\bPURCHASE\b", r"\bDEBIT\b", r"\bCARD\b",
    r"\*[\w]+",            # *TRIP, *XYZ123
    r"\b\d{2}/\d{2}\b",    # embedded dates
    r"\b\d{4,}\b",         # store/ref numbers
    r"#\d+",
]

def normalize(description: str) -> str:
    s = description.upper()
    for pat in _NOISE:
        s = re.sub(pat, " ", s)
    return re.sub(r"\s+", " ", s).strip()