from decimal import Decimal
from typing import Any
from app.categorizer.config import MINMARGIN, HARDCONFLICTMULTIPLE
from app.categorizer.rulesdata import AMOUNTRANGES, CATEGORYRULES
from app.categorizer.categories import SALESINCOME, INVENTORY
from app.categorizer.context import Context

def detectconflicts(amount: Decimal, bestcat: str, scores: dict[str, Any], context: Context, cleandesc: str, isrefund: bool) -> list[str]:
    conflicts = []
    absamount = abs(amount)
    
    maxamt = AMOUNTRANGES.get(bestcat, (0, 0))[1]
    if absamount > maxamt * HARDCONFLICTMULTIPLE:
        conflicts.append("amount exceeds expected range")

    sortedcats = sorted(scores.items(), key=lambda x: x[1]["points"], reverse=True)
    if len(sortedcats) >= 2 and sortedcats[0][1]["points"] - sortedcats[1][1]["points"] < MINMARGIN:
        conflicts.append("evidence disagrees")
        
    if not isrefund:
        isexpense = amount < 0
        if isexpense:
            for kw in CATEGORYRULES[SALESINCOME]["keywords"] + CATEGORYRULES[SALESINCOME]["aliases"]:
                if kw in cleandesc:
                    conflicts.append("direction conflict")
                    break
        else:
            hasincomekw = False
            for kw in CATEGORYRULES[SALESINCOME]["keywords"] + CATEGORYRULES[SALESINCOME]["aliases"]:
                if kw in cleandesc:
                    hasincomekw = True
                    break
            if not hasincomekw:
                conflictfound = False
                for cat, rules in CATEGORYRULES.items():
                    if cat != SALESINCOME:
                        for kw in rules["keywords"] + rules["aliases"]:
                            if kw in cleandesc:
                                conflicts.append("direction conflict")
                                conflictfound = True
                                break
                    if conflictfound:
                        break
                    
    role = context.counterparties.get(cleandesc)
    if role:
        strongname = False
        if bestcat in scores:
            for sig in scores[bestcat]["signals"]:
                if sig["name"] in ("merchantalias", "keyword"):
                    strongname = True
                    break
                    
        if not strongname:
            if role == "supplier" and bestcat != INVENTORY:
                conflicts.append("name versus history")
            elif role == "customer" and bestcat != SALESINCOME:
                conflicts.append("name versus history")

    return conflicts