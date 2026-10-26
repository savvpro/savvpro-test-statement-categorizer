import statistics
from decimal import Decimal
from typing import Any
from app.categorizer.config import MINRECURRENCES, AMOUNTTOLERANCE
from app.categorizer.cleaning import cleantext

def buildrecurring(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    groups = {}
    for txn in transactions:
        if txn.get("isduplicate", False):
            continue
        cd = cleantext(txn["descriptionraw"])
        isexp = txn["amount"] < 0
        key = f"{cd}_out" if isexp else f"{cd}_in"
        if key not in groups:
            groups[key] = []
        groups[key].append(txn)
    
    recurring = {}
    for key, txns in groups.items():
        unique_dates = sorted(list(set(t["date"] for t in txns)))
        if len(unique_dates) < MINRECURRENCES:
            continue
            
        amounts = [abs(t["amount"]) for t in txns]
        medianamt = Decimal(str(statistics.median(amounts)))
        
        if any(abs(a - medianamt) / medianamt > AMOUNTTOLERANCE for a in amounts):
            continue
        
        gaps = [(unique_dates[i+1] - unique_dates[i]).days for i in range(len(unique_dates)-1)]
        isweekly = all(5 <= g <= 9 for g in gaps)
        ismonthly = all(26 <= g <= 34 for g in gaps)
        
        if isweekly or ismonthly:
            cleandesc = key.replace("_out", "").replace("_in", "")
            recurring[cleandesc] = {
                "pattern": "weekly" if isweekly else "monthly",
                "median": medianamt
            }
    return recurring