from datetime import datetime
from decimal import Decimal
from typing import Any


def cleandecimal(val: str) -> Decimal:
    cleaned = val.replace(",", "").strip().upper()
    if not cleaned:
        return Decimal("0.00")
    if cleaned.endswith("DR"):
        return -Decimal(cleaned.replace("DR", "").strip())
    if cleaned.endswith("CR"):
        return Decimal(cleaned.replace("CR", "").strip())
    return Decimal(cleaned)

def parselayouta(row: dict[str, str]) -> dict[str, Any]:
    dt = datetime.strptime(row["date"].strip(), "%d/%m/%Y").date()
    desc = row["narration"].strip()
    debitstr = row.get("debit", "").strip()
    creditstr = row.get("credit", "").strip()
    
    if debitstr:
        amt = -abs(cleandecimal(debitstr))
    elif creditstr:
        amt = abs(cleandecimal(creditstr))
    else:
        amt = Decimal("0.00")
        
    balstr = row.get("balance", "").strip()
    bal = cleandecimal(balstr) if balstr else None
    return {"date": dt, "descriptionraw": desc, "amount": amt, "balance": bal}

def parselayoutb(row: dict[str, str]) -> dict[str, Any]:
    if row.get("status", "").strip().lower() == "pending":
        raise ValueError("status pending")
    dt = datetime.strptime(row["transaction date"].strip(), "%d-%b-%Y").date()
    desc = row["description"].strip()
    amt = cleandecimal(row["amount"])
    balstr = row.get("running balance", "").strip()
    bal = cleandecimal(balstr) if balstr else None
    return {"date": dt, "descriptionraw": desc, "amount": amt, "balance": bal}

def parselayoutc(row: dict[str, str]) -> dict[str, Any]:
    dt = datetime.strptime(row["value date"].strip(), "%Y-%m-%d").date()
    desc = row["transaction details"].strip()
    withdrawalstr = row.get("withdrawal", "").strip()
    depositstr = row.get("deposit", "").strip()
    
    if withdrawalstr:
        amt = -abs(cleandecimal(withdrawalstr))
    elif depositstr:
        amt = abs(cleandecimal(depositstr))
    else:
        amt = Decimal("0.00")
        
    balstr = row.get("balance", "").strip()
    bal = cleandecimal(balstr) if balstr else None
    return {"date": dt, "descriptionraw": desc, "amount": amt, "balance": bal}