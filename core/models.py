from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ExpenseExtraction(BaseModel):
    amount: Optional[float] = Field(default=0.0)
    item_name: Optional[str] = Field(default="")
    date_str: Optional[str] = Field(default=None)

class TransactionRecord(BaseModel):
    user_id: str
    amount: float
    category_id: int
    description: str
    transaction_date: datetime