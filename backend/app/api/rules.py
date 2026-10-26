from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.categorizer.categories import (
    BANKFEES,
    INVENTORY,
    MARKETING,
    NEEDSREVIEW,
    NOTSPENDING,
    RENT,
    SALARIES,
    SALESINCOME,
    SHIPPING,
    SOFTWARE,
)
from app.models.db import Rule, getdb

router = APIRouter()

@router.get("/api/categories")
def getcategories():
    return [INVENTORY, SHIPPING, SOFTWARE, MARKETING, RENT, SALARIES, BANKFEES, SALESINCOME, NOTSPENDING, NEEDSREVIEW]

@router.get("/api/rules")
def getrules(db: Session = Depends(getdb)):
    return db.query(Rule).all()

@router.delete("/api/rules/{id}")
def deleterule(id: int, db: Session = Depends(getdb)):
    rule = db.query(Rule).filter(Rule.id == id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"status": "deleted"}