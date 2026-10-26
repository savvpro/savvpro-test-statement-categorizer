from .csv_parser import parse_csv
from .pdf_parser import parse_pdf
from .rows import CleanResult, CleanRow, Issue, ParsedFile, clean_rows
from .values import NeedsUserChoice, UnsupportedFile, ValueProblem


def read_statement(filename: str, data: bytes) -> ParsedFile:
    name = filename.lower()
    if name.endswith(".csv"):
        return parse_csv(data)
    if name.endswith(".pdf"):
        if not data.startswith(b"%PDF-"):
            raise UnsupportedFile("The file is named .pdf but isn't a PDF.")
        return parse_pdf(data)
    raise UnsupportedFile("Only .csv and .pdf bank statements are supported.")


__all__ = [
    "CleanResult", "CleanRow", "Issue", "NeedsUserChoice", "ParsedFile", "UnsupportedFile",
    "ValueProblem", "clean_rows", "read_statement",
]
