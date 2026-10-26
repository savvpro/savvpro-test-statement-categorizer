from pydantic import BaseModel, ConfigDict

from app.brain.models import CategoryKind


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    kind: CategoryKind
    schedule_c_line: str | None
    deductible_pct: int
    description: str
