from fastapi import APIRouter, Depends, HTTPException

from app.brain.rules_loader import load_rules
from app.schemas import Transaction, UpdateCategoryRequest, UpdateResponse
from app.services.store import StatementStore, get_store
from app.services.summary import build_summary

router = APIRouter()


@router.get("/categories")
def list_categories() -> list[str]:
    return list(load_rules()["categories"].keys())


@router.get("/transactions", response_model=list[Transaction])
def list_transactions(store: StatementStore = Depends(get_store)):
    return store.all()


@router.patch("/transactions/{txn_id}", response_model=UpdateResponse)
def update_category(
    txn_id: str,
    body: UpdateCategoryRequest,
    store: StatementStore = Depends(get_store),
):
    rules = load_rules()
    if body.category not in rules["categories"]:
        raise HTTPException(400, f"Unknown category '{body.category}'")
    txn = store.get(txn_id)
    if txn is None:
        raise HTTPException(404, "Transaction not found")

    txn.category = body.category
    txn.confidence = "high"
    txn.reason = "Set by user"
    txn.user_overridden = True
    txn.tax_deductible = rules["categories"][body.category]

    return UpdateResponse(transaction=txn, summary=build_summary(store.all(), rules))