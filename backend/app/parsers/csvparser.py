import csv
import decimal
import io
from typing import Any

from app.parsers.layouts import parselayouta, parselayoutb, parselayoutc


def detectlayout(headers: list[str]) -> str:
    headerslower = [h.strip().lower() for h in headers]
    if "narration" in headerslower and "debit" in headerslower:
        return "layouta"
    if "transaction date" in headerslower and "running balance" in headerslower:
        return "layoutb"
    if "value date" in headerslower and "withdrawal" in headerslower:
        return "layoutc"
    raise ValueError("unknown header format")

def parsecontent(content: bytes) -> dict[str, Any]:
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    
    try:
        headers = next(reader)
    except StopIteration:
        raise ValueError("empty file")
        
    if not headers:
        raise ValueError("empty file")
        
    layoutname = detectlayout(headers)
    headerslower = [h.strip().lower() for h in headers]
    
    transactions = []
    skippedrows = []
    
    for idx, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            skippedrows.append({"row": idx, "reason": "blank row"})
            continue
            
        rowdict = dict(zip(headerslower, row))
        try:
            if layoutname == "layouta":
                parsed = parselayouta(rowdict)
            elif layoutname == "layoutb":
                parsed = parselayoutb(rowdict)
            elif layoutname == "layoutc":
                parsed = parselayoutc(rowdict)
                
            parsed["sourcerow"] = idx
            transactions.append(parsed)
        except (ValueError, KeyError, decimal.InvalidOperation) as e:
            skippedrows.append({"row": idx, "reason": str(e)})
            
    return {"transactions": transactions, "skippedrows": skippedrows}