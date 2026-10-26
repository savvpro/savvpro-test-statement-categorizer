from pydantic import BaseModel


class Transaction(BaseModel):
    date: str
    description: str
    amount: float


class CategorizedTransaction(Transaction):
    category: str
    confidence: float
    needs_review: bool