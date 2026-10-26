from pydantic import BaseModel

class RowOut(BaseModel):
    id: str
    date: str
    description: str
    amount: str
    category: str
    confidence: float
    reason: str

class UpdateCategoryIn(BaseModel):
    category: str