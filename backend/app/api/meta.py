from fastapi import APIRouter

from app.core.domain import CATEGORIES, KINDS
from app.schemas import CategoriesOut

router = APIRouter(tags=["meta"])


@router.get("/categories", response_model=CategoriesOut)
def categories() -> CategoriesOut:
    return CategoriesOut(categories=list(CATEGORIES), kinds=list(KINDS))
