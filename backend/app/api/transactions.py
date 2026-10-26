from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.categorizer.brain import categorize
from app.categorizer.categories import NEEDSREVIEW
from app.categorizer.cleaning import cleantext
from app.categorizer.context import buildcontext
from app.models.db import Rule, Transaction, getdb

router = APIRouter()

class PatchTransaction(BaseModel):
    category: str
    createrule: bool = True

@router.get("/api/uploads/{id}/transactions")
def gettransactions(id: int, status: str = "all", db: Session = Depends(getdb)):
    query = db.query(Transaction).filter(Transaction.uploadid == id)
    if status == "review":
        query = query.filter(Transaction.category == NEEDSREVIEW)
    elif status == "confident":
        query = query.filter(Transaction.category != NEEDSREVIEW)
    return query.all()

@router.patch("/api/transactions/{id}")
def updatetransaction(id: int, payload: PatchTransaction, db: Session = Depends(getdb)):
    txn = db.query(Transaction).filter(Transaction.id == id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    txn.category = payload.category
    txn.confidence = 1.0
    txn.reason = "Manually categorized by user"
    txn.route = "userrule"
    db.commit()

    updatedids = [txn.id]

    if payload.createrule:
        cleandesc = cleantext(txn.descriptionraw)
        merchantkey = " ".join(cleandesc.split()[:3])
        
        rule = db.query(Rule).filter(Rule.merchantkey == merchantkey).first()
        if rule:
            rule.category = payload.category
        else:
            db.add(Rule(merchantkey=merchantkey, category=payload.category))
        db.commit()

        userrules = [{"merchantkey": r.merchantkey, "category": r.category} for r in db.query(Rule).all()]
        
        alltxns = db.query(Transaction).filter(Transaction.uploadid == txn.uploadid).all()
        dicttxns = [{"date": t.date, "descriptionraw": t.descriptionraw, "amount": t.amount, "balance": t.balance, "isduplicate": t.isduplicate} for t in alltxns]
        
        context = buildcontext(dicttxns, userrules)
        
        for othertxn in alltxns:
            if othertxn.id != txn.id and othertxn.category == NEEDSREVIEW and not othertxn.isduplicate:
                dicttxn = {"date": othertxn.date, "descriptionraw": othertxn.descriptionraw, "amount": othertxn.amount, "balance": othertxn.balance}
                decision = categorize(dicttxn, context)
                if decision["category"] != NEEDSREVIEW:
                    othertxn.category = decision["category"]
                    othertxn.confidence = decision["confidence"]
                    othertxn.reason = decision["reason"]
                    othertxn.route = decision["route"]
                    updatedids.append(othertxn.id)
        db.commit()
        
    return db.query(Transaction).filter(Transaction.id.in_(updatedids)).all()