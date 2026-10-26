from decimal import Decimal
from typing import Any
from app.categorizer.categories import NOTSPENDING, NEEDSREVIEW, SALARIES, RENT, SALESINCOME, INVENTORY
from app.categorizer.cleaning import cleantext
from app.categorizer.rulesdata import NOTSPENDINGKEYWORDS, AMBIGUOUSMERCHANTS, AMOUNTRANGES
from app.categorizer.evidence import collectsignals
from app.categorizer.config import (
    FULLSCORE, REVIEWTHRESHOLD, NOTSPENDINGCONFIDENCE, AMBIGUOUSCAP, USERRULECONFIDENCE, CONFLICTCONFIDENCECAP
)
from app.categorizer.context import Context
from app.categorizer.conflicts import detectconflicts
from app.categorizer.refunds import isrefundtxn

def categorize(txn: dict[str, Any], context: Context) -> dict[str, Any]:
    rawdesc = txn["descriptionraw"]
    amount = txn["amount"]
    cleandesc = cleantext(rawdesc)
    
    isrefund = isrefundtxn(amount, cleandesc, context)
    
    decision = {
        "category": NEEDSREVIEW,
        "confidence": 0.0,
        "reason": "No rule matched",
        "route": "ambiguous",
        "signals": [],
        "conflicts": [],
        "suggestedcategory": None,
        "tworeasonsmet": False,
        "isrefund": isrefund,
        "isrecurring": cleandesc in context.recurring
    }

    if cleandesc in context.userrules:
        decision["category"] = context.userrules[cleandesc]
        decision["confidence"] = USERRULECONFIDENCE
        decision["reason"] = f"Matched your saved rule: {cleandesc}"
        decision["route"] = "userrule"
        decision["tworeasonsmet"] = True
        return decision
        
    if (cleandesc, amount) in context.reversals:
        if amount < 0:
            decision["category"] = SALESINCOME
            decision["reason"] = f"Exact reversal of earlier payment: {cleandesc}"
        else:
            decision["category"] = INVENTORY
            decision["reason"] = f"Exact reversal of earlier expense: {cleandesc}"
        decision["isrefund"] = True
        decision["confidence"] = 0.9
        decision["route"] = "refund"
        decision["tworeasonsmet"] = True
        return decision

    for kw in NOTSPENDINGKEYWORDS:
        if kw in cleandesc:
            decision["category"] = NOTSPENDING
            decision["confidence"] = NOTSPENDINGCONFIDENCE
            decision["reason"] = f"Matches Not Spending phrase: {kw}"
            decision["route"] = "notspending"
            decision["tworeasonsmet"] = True
            return decision

    for amb in AMBIGUOUSMERCHANTS:
        if amb in cleandesc:
            decision["category"] = NEEDSREVIEW
            decision["confidence"] = AMBIGUOUSCAP
            decision["reason"] = f"{amb} is used for both stock and personal purchases; please review."
            return decision

    scores = collectsignals(cleandesc, amount, context, isrefund)
    
    if not scores:
        if cleandesc in context.recurring:
            recamt = context.recurring[cleandesc]["median"]
            if AMOUNTRANGES[SALARIES][0] <= recamt <= AMOUNTRANGES[SALARIES][1]:
                decision["suggestedcategory"] = SALARIES
            else:
                decision["suggestedcategory"] = RENT
            decision["reason"] = f"Recurring pattern suggests {decision['suggestedcategory']}."
        else:
            role = context.counterparties.get(cleandesc, "none")
            decision["reason"] = f"No rule matched [Key: '{cleandesc}', Role: '{role}']."
        return decision

    bestcat = max(scores.items(), key=lambda x: x[1]["points"])
    catname = bestcat[0]
    catdata = bestcat[1]
    
    points = catdata["points"]
    confidence = min(max(points, 0) / FULLSCORE, 1.0)
    
    decision["signals"] = catdata["signals"]
    decision["suggestedcategory"] = catname
    decision["route"] = "scored"

    families = {sig["family"] for sig in catdata["signals"]}
    decision["tworeasonsmet"] = len(families) >= 2

    conflicts = detectconflicts(amount, catname, scores, context, cleandesc, isrefund)
    decision["conflicts"] = conflicts

    sigtexts = [s["text"] for s in catdata["signals"]]

    if conflicts:
        decision["category"] = NEEDSREVIEW
        decision["confidence"] = min(confidence, CONFLICTCONFIDENCECAP)
        decision["reason"] = "Conflict: " + "; ".join(conflicts)
        return decision

    if not decision["tworeasonsmet"]:
        decision["category"] = NEEDSREVIEW
        decision["confidence"] = confidence
        role = context.counterparties.get(cleandesc, "none")
        decision["reason"] = f"Score too low [Key: '{cleandesc}', Role: '{role}']. {catname} ({confidence:.2f}): " + ", ".join(sigtexts)
        return decision

    if confidence < REVIEWTHRESHOLD:
        decision["category"] = NEEDSREVIEW
        decision["confidence"] = confidence
        role = context.counterparties.get(cleandesc, "none")
        decision["reason"] = f"Score too low [Key: '{cleandesc}', Role: '{role}']. {catname} ({confidence:.2f}): " + ", ".join(sigtexts)
    else:
        decision["category"] = catname
        decision["confidence"] = confidence
        decision["reason"] = f"{catname} ({confidence:.2f}): " + ", ".join(sigtexts) + ". Two reasons met."

    return decision