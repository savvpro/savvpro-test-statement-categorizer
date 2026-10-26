from fastapi import APIRouter

from app.brain.taxonomy import all_categories
from app.schemas import CategoryOut

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories() -> list[CategoryOut]:
    return [CategoryOut.model_validate(category) for category in all_categories()]
