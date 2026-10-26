from decimal import Decimal
from typing import Any
from app.categorizer.categories import SALESINCOME, INVENTORY
from app.categorizer.rulesdata import CATEGORYRULES, AMOUNTRANGES
from app.categorizer.fuzzy import getfuzzyscore
from app.categorizer.context import Context
from app.categorizer.config import (
    ALIASPOINTS, KEYWORDPOINTS, FUZZYHIGHPOINTS, FUZZYLOWPOINTS, INRANGEPOINTS, 
    OUTOFRANGEPENALTY, HARDCONFLICTMULTIPLE, COUNTERPARTYPOINTS, RECURRINGPOINTS
)

def collectsignals(desc: str, amount: Decimal, context: Context, isrefund: bool) -> dict[str, Any]:
    scores = {}
    isexpense = amount < 0
    if isrefund:
        isexpense = not isexpense
        
    absamount = abs(amount)

    strongnamecats = set()
    for c, rules in CATEGORYRULES.items():
        if any(desc == alias for alias in rules["aliases"]) or any(kw in desc for kw in rules["keywords"]):
            strongnamecats.add(c)

    for cat, rules in CATEGORYRULES.items():
        if (cat == SALESINCOME and isexpense) or (cat != SALESINCOME and not isexpense):
            continue

        catpoints = 0
        signals = []
        matchedname = False
        
        for alias in rules["aliases"]:
            if desc == alias:
                catpoints += ALIASPOINTS
                signals.append({"family": "Name", "name": "merchantalias", "points": ALIASPOINTS, "text": f"exact alias {alias}"})
                matchedname = True
                break
        
        if not matchedname:
            for kw in rules["keywords"]:
                if kw in desc:
                    catpoints += KEYWORDPOINTS
                    signals.append({"family": "Name", "name": "keyword", "points": KEYWORDPOINTS, "text": f"keyword {kw}"})
                    matchedname = True
                    break

        if not matchedname:
            bestfuzzy = 0
            bestalias = ""
            for alias in rules["aliases"]:
                score = getfuzzyscore(desc, alias)
                if score > bestfuzzy:
                    bestfuzzy = score
                    bestalias = alias
            if bestfuzzy >= 90:
                catpoints += FUZZYHIGHPOINTS
                signals.append({"family": "Name", "name": "fuzzy", "points": FUZZYHIGHPOINTS, "text": f"fuzzy match {bestalias}"})
            elif 80 <= bestfuzzy < 90:
                catpoints += FUZZYLOWPOINTS
                signals.append({"family": "Name", "name": "fuzzy", "points": FUZZYLOWPOINTS, "text": f"weak fuzzy match {bestalias}"})

        hasname = catpoints > 0
        hashistory = False

        role = context.counterparties.get(desc, "")
        isrec = desc in context.recurring
        
        if cat == INVENTORY and role in ("supplier", "twoway"):
            if not (strongnamecats - {INVENTORY}):
                hashistory = True
                catpoints += COUNTERPARTYPOINTS
                signals.append({"family": "Behaviour", "name": "counterparty", "points": COUNTERPARTYPOINTS, "text": "known supplier"})
                
        if cat == SALESINCOME and role in ("customer", "twoway"):
            if not (strongnamecats - {SALESINCOME}):
                hashistory = True
                catpoints += COUNTERPARTYPOINTS
                signals.append({"family": "Behaviour", "name": "counterparty", "points": COUNTERPARTYPOINTS, "text": "known customer"})
            
        if isrec and matchedname:
            hashistory = True
            catpoints += RECURRINGPOINTS
            signals.append({"family": "Behaviour", "name": "recurring", "points": RECURRINGPOINTS, "text": "recurring pattern"})

        if not (hasname or hashistory):
            continue

        minamt, maxamt = AMOUNTRANGES.get(cat, (0, 0))
        if minamt <= absamount <= maxamt:
            catpoints += INRANGEPOINTS
            signals.append({"family": "Context", "name": "inrange", "points": INRANGEPOINTS, "text": "in typical range"})
        elif absamount > maxamt and absamount <= maxamt * HARDCONFLICTMULTIPLE:
            catpoints += OUTOFRANGEPENALTY
            signals.append({"family": "Context", "name": "outofrange", "points": OUTOFRANGEPENALTY, "text": "above typical range"})
            
        if catpoints > 0:
            scores[cat] = {"points": catpoints, "signals": signals}

    return scores