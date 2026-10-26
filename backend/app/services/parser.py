import io
import pandas as pd
import pdfplumber
from fastapi import UploadFile


REQUIRED_COLUMNS = {"date", "description", "amount"}


async def parse_statement(file: UploadFile) -> list[dict]:
    content = await file.read()

    if file.filename.endswith(".csv"):
        return _parse_csv(content)
    elif file.filename.endswith(".pdf"):
        return _parse_pdf(content)
    else:
        raise ValueError("Only CSV and PDF files are supported.")


def _parse_csv(content: bytes) -> list[dict]:
    df = pd.read_csv(io.BytesIO(content))
    df.columns = df.columns.str.strip().str.lower()

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["date"] = df["date"].astype(str).str.strip()
    df["description"] = df["description"].astype(str).str.strip()

    return df[["date", "description", "amount"]].to_dict(orient="records")


def _parse_pdf(content: bytes) -> list[dict]:
    rows = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) >= 3:
                        rows.append({
                            "date": str(row[0]).strip(),
                            "description": str(row[1]).strip(),
                            "amount": _to_float(row[2]),
                        })
    if not rows:
        raise ValueError("No table data found in PDF.")
    return rows


def _to_float(value) -> float:
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except Exception:
        return 0.0