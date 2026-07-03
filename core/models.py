from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ExpenseExtraction(BaseModel):
    amount: Optional[float] = Field(default=0.0, description="The numeric amount of the expense. Return 0.0 if not found.")
    item_name: Optional[str] = Field(default="", description="The name of the item or service. Return empty string if not found.")
    date_str: Optional[str] = Field(default=None, description="The date mentioned, if any.")

class TransactionRecord(BaseModel):
    user_id: str
    amount: float
    category_id: int
    description: str
    transaction_date: datetime
    remarks: str = ""
