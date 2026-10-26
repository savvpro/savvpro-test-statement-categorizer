"""OCR for scanned pages. Optional: the app runs without Tesseract and says so."""

from functools import lru_cache

from .layout import Word

try:
    import pytesseract
    from pytesseract import Output
except ImportError:  # pragma: no cover - pytesseract is in requirements.txt
    pytesseract = None


@lru_cache(maxsize=1)
def ocr_available() -> bool:
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001 - any failure here just means "not installed"
        return False


def ocr_image(image) -> list[Word]:
    gray = image.convert("L")
    width, height = gray.size
    # psm 11 ("sparse text") finds each word on its own. On statement tables it stops
    # tesseract from gluing neighbouring words together ("CAREEMRIDE"), and layout.py
    # rebuilds the lines from word positions anyway.
    data = pytesseract.image_to_data(gray, output_type=Output.DICT, config="--psm 11")
    words = []
    for i, raw in enumerate(data["text"]):
        text = (raw or "").strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:
            continue
        left, top = data["left"][i], data["top"][i]
        words.append(Word(
            text=text,
            x0=left / width,
            x1=(left + data["width"][i]) / width,
            top=top / height,
            bottom=(top + data["height"][i]) / height,
            conf=conf,
        ))
    return words
