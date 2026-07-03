from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ExpenseExtraction(BaseModel):
    amount: Optional[float] = Field(default=0.0, description="The numeric amount of the expense.")
    item_name: Optional[str] = Field(default="", description="The name of the item or service.")
    date_str: Optional[str] = Field(default=None, description="The date mentioned, if any.")
    category_name: Optional[str] = Field(default="", description="The exact category name from the provided list, if highly confident.")

class ExpenseBatch(BaseModel):
    items: List[ExpenseExtraction] = Field(default_factory=list, description="Array of extracted expenses.")

class TransactionRecord(BaseModel):
    user_id: str
    amount: float
    category_id: int
    description: str
    transaction_date: datetime
    remarks: str = ""
