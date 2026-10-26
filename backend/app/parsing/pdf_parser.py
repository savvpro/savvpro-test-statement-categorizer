import io
import logging

import pdfplumber

from .layout import Word, rows_from_pages
from .ocr import ocr_available, ocr_image
from .rows import ParsedFile
from .values import UnsupportedFile, currency_hint

log = logging.getLogger(__name__)

MAX_PAGES = 30
MIN_TEXT_CHARS = 30  # less text than this on a page means it is probably a scan
OCR_RESOLUTION = 300


def parse_pdf(data: bytes) -> ParsedFile:
    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001 - pdfminer raises many different errors
        raise UnsupportedFile("The PDF couldn't be opened. It may be damaged or password-protected.") from exc

    pages: list[list[Word]] = []
    used_ocr = False
    with pdf:
        if len(pdf.pages) > MAX_PAGES:
            raise UnsupportedFile(f"The PDF has {len(pdf.pages)} pages. The limit is {MAX_PAGES}.")
        for page in pdf.pages:
            width, height = float(page.width), float(page.height)
            raw_words = page.extract_words(x_tolerance=1.5, keep_blank_chars=False)
            if sum(len(w["text"]) for w in raw_words) >= MIN_TEXT_CHARS:
                pages.append([
                    Word(w["text"], w["x0"] / width, w["x1"] / width, w["top"] / height, w["bottom"] / height)
                    for w in raw_words
                ])
                continue
            if not ocr_available():
                raise UnsupportedFile(
                    "This PDF looks like a scanned image. Reading scans needs Tesseract OCR, which isn't "
                    "installed on this machine. See the README, or upload the CSV export instead."
                )
            used_ocr = True
            pages.append(ocr_image(page.to_image(resolution=OCR_RESOLUTION).original))

    rows, has_balance = rows_from_pages(pages)
    if not rows:
        raise UnsupportedFile(
            "No transaction table was found in this PDF. The app reads statements with a header line "
            "containing Date, Description and Debit/Credit (or Amount) columns."
        )
    log.info("pdf parsed: pages=%d rows=%d ocr=%s", len(pages), len(rows), used_ocr)

    first_page_text = " ".join(w.text for w in pages[0]) if pages else ""
    notes = []
    if used_ocr:
        notes.append("Some pages were scanned images and were read with OCR. Check flagged rows carefully.")
    return ParsedFile(
        rows=rows,
        source_kind="ocr" if used_ocr else "pdf",
        has_balance=has_balance,
        currency_hint=currency_hint(first_page_text),
        notes=notes,
    )
