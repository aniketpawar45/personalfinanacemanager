from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ExpenseExtraction(BaseModel):
    amount: float = Field(description="The numeric amount of the expense.")
    item_name: str = Field(description="The name of the item or service purchased.")
    date_str: Optional[str] = Field(default=None, description="The date mentioned, if any.")

class TransactionRecord(BaseModel):
    user_id: str
    amount: float
    category_id: int
    description: str
    transaction_date: datetime