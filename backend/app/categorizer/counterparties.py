from decimal import Decimal
from typing import Any
from app.categorizer.config import SUPPLIERMINCOUNT, SUPPLIERMINTOTAL, CUSTOMERMINCOUNT
from app.categorizer.cleaning import cleantext

GENERICCOUNTERPARTIES = [
    "CASH DEPOSIT", "COD SETTLEMENT", "COD REMITTANCE", "CUSTOMER PAYMENT",
    "COD SETTLEMENT LEOPARDS", "COD SETTLEMENT TCS", "CUSTOMER PAYMENT CASH"
]

def buildcounterparties(transactions: list[dict[str, Any]]) -> dict[str, str]:
    memory = {}
    for txn in transactions:
        if txn.get("isduplicate", False):
            continue
            
        cd = cleantext(txn["descriptionraw"])
        if cd in GENERICCOUNTERPARTIES:
            continue
            
        amt = txn["amount"]
        if cd not in memory:
            memory[cd] = {"incount": 0, "intotal": Decimal("0"), "outcount": 0, "outtotal": Decimal("0")}
            
        if amt < 0:
            memory[cd]["outcount"] += 1
            memory[cd]["outtotal"] += abs(amt)
        else:
            memory[cd]["incount"] += 1
            memory[cd]["intotal"] += amt
    
    result = {}
    for cd, stats in memory.items():
        issupplier = stats["outcount"] >= SUPPLIERMINCOUNT and stats["outtotal"] >= SUPPLIERMINTOTAL
        iscustomer = stats["incount"] >= CUSTOMERMINCOUNT
        istwoway = stats["outcount"] > 0 and stats["incount"] > 0
        
        if istwoway:
            result[cd] = "twoway"
        elif issupplier:
            result[cd] = "supplier"
        elif iscustomer:
            result[cd] = "customer"
    return result