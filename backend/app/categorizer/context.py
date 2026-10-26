from dataclasses import dataclass
from typing import Any
from decimal import Decimal
from app.categorizer.counterparties import buildcounterparties
from app.categorizer.recurring import buildrecurring
from app.categorizer.cleaning import cleantext

@dataclass
class Context:
    userrules: dict[str, str]
    counterparties: dict[str, str]
    recurring: dict[str, Any]
    reversals: set[tuple[str, Decimal]]

def buildcontext(transactions: list[dict[str, Any]], userrules: list[dict[str, str]]) -> Context:
    rulesdict = {r["merchantkey"]: r["category"] for r in userrules}
    cps = buildcounterparties(transactions)
    recs = buildrecurring(transactions)
    
    seenamts = {}
    reversals = set()
    for txn in transactions:
        if txn.get("isduplicate", False):
            continue
            
        cd = cleantext(txn["descriptionraw"])
        amt = txn["amount"]
        opposite = -amt
        
        if opposite in seenamts:
            for prevcd in seenamts[opposite]:
                if set(cd.split()) & set(prevcd.split()):
                    reversals.add((cd, amt))
        
        if amt not in seenamts:
            seenamts[amt] = []
        seenamts[amt].append(cd)

    return Context(userrules=rulesdict, counterparties=cps, recurring=recs, reversals=reversals)