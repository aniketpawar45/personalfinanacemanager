from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ExpenseExtraction(BaseModel):
    """
    Schema for the AI-extracted data from raw text/voice.
    Ensures that amount and item_name are always available.
    """
    amount: Optional[float] = 0.0
    item_name: Optional[str] = ""

class TransactionRecord(BaseModel):
    """
    Schema for database operations.
    Used for creating and inserting records into the 'transactions' table.
    """
    user_id: str
    amount: float
    category_id: int
    description: str
    transaction_date: datetime

class AppUser(BaseModel):
    """
    Schema for user authentication and role management.
    """
    telegram_id: str
    role: str = "user"