"""Category taxonomy."""

from fastapi import APIRouter

from app.api.schemas import CategoryOut
from app.domain.taxonomy import TAXONOMY

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories() -> list[CategoryOut]:
    return [
        CategoryOut(
            code=i.code,
            label=i.label,
            kind=i.kind,
            schedule_e_line=i.schedule_e_line,
            allowed_directions=sorted(i.allowed_directions),
        )
        for i in TAXONOMY.values()
    ]
