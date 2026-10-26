from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.db import getdb, Upload, Transaction, Rule
from app.parsers.csvparser import parsecontent
from app.categorizer.context import buildcontext
from app.categorizer.brain import categorize
from app.categorizer.categories import NOTSPENDING, NEEDSREVIEW, SALESINCOME
from pydantic import BaseModel
from decimal import Decimal

router = APIRouter()

class UploadResponse(BaseModel):
    uploadid: int
    rowcount: int
    skippedrows: list[dict]

@router.post("/api/uploads", response_model=UploadResponse)
def createupload(file: UploadFile = File(...), db: Session = Depends(getdb)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = file.file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        parsed = parsecontent(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    rawtxns = parsed["transactions"]
    skipped = parsed["skippedrows"]

    existing = db.query(Transaction.date, Transaction.descriptionraw, Transaction.amount).all()
    seen = set((t[0], t[1], t[2]) for t in existing)

    dbupload = Upload(filename=file.filename)
    db.add(dbupload)
    db.commit()
    db.refresh(dbupload)

    for txn in rawtxns:
        txnhash = (txn["date"], txn["descriptionraw"], txn["amount"])
        if txnhash in seen:
            txn["isduplicate"] = True
        else:
            txn["isduplicate"] = False
            seen.add(txnhash)

    userrules = [{"merchantkey": r.merchantkey, "category": r.category} for r in db.query(Rule).all()]
    context = buildcontext(rawtxns, userrules)

    for txn in rawtxns:
        decision = categorize(txn, context)
            
        dbtxn = Transaction(
            uploadid=dbupload.id, date=txn["date"], descriptionraw=txn["descriptionraw"],
            amount=txn["amount"], balance=txn["balance"], sourcerow=txn["sourcerow"],
            category=decision["category"], confidence=Decimal(decision["confidence"]),
            reason=decision["reason"], route=decision["route"], signals=decision["signals"],
            conflicts=decision["conflicts"], suggestedcategory=decision["suggestedcategory"],
            tworeasonsmet=decision["tworeasonsmet"], isrefund=decision["isrefund"],
            isduplicate=txn["isduplicate"], isrecurring=decision.get("isrecurring", False)
        )
        db.add(dbtxn)

    db.commit()
    return UploadResponse(uploadid=dbupload.id, rowcount=len(rawtxns), skippedrows=skipped)

@router.get("/api/uploads/{id}/summary")
def getsummary(id: int, db: Session = Depends(getdb)):
    txns = db.query(Transaction).filter(Transaction.uploadid == id).all()
    
    totals = {}
    totalincome = Decimal("0")
    totalspending = Decimal("0")
    needsreviewcount = 0
    excludedcount = 0
    
    for t in txns:
        if t.category == NEEDSREVIEW:
            needsreviewcount += 1
            continue
        if t.category == NOTSPENDING or t.isduplicate:
            excludedcount += 1
            continue
            
        if t.category not in totals:
            totals[t.category] = Decimal("0")
            
        if t.isrefund:
            if t.category == SALESINCOME:
                totalincome += t.amount
            else:
                totalspending += t.amount
            totals[t.category] += t.amount
        else:
            if t.amount > 0:
                totalincome += t.amount
            else:
                totalspending += t.amount
            totals[t.category] += abs(t.amount)
            
    return {
        "totalspercategory": totals,
        "totalincome": totalincome,
        "totalspending": totalspending,
        "needsreviewcount": needsreviewcount,
        "excludedcount": excludedcount
    }