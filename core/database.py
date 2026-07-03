import os
import logging
from supabase import create_client, Client
from datetime import timedelta
from core.models import TransactionRecord
from core.utils import get_ist_now, FinanceManagerException

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Critical Security Error: Missing Supabase Service Role Key or URL.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
_CATEGORY_CACHE = []

def load_categories_into_cache():
    global _CATEGORY_CACHE
    try:
        response = supabase.table("categories").select("id, category_name").execute()
        if response.data:
            _CATEGORY_CACHE = response.data
    except Exception as e:
        logger.error(f"Failed to load categories into cache: {str(e)}")

def get_all_categories() -> list:
    global _CATEGORY_CACHE
    if not _CATEGORY_CACHE:
        load_categories_into_cache()
    return _CATEGORY_CACHE

def get_user_role(telegram_id: str) -> str:
    try:
        response = supabase.table("app_users").select("role").eq("telegram_id", telegram_id).execute()
        if response.data:
            return response.data[0]['role']
        return "unauthenticated"
    except Exception:
        return "unauthenticated"

def get_last_category(description: str) -> int | None:
    try:
        response = supabase.table("transactions")\
            .select("category_id")\
            .eq("description", description.title())\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        return response.data[0]['category_id'] if response.data else None
    except Exception:
        return None

def check_duplicate(user_id: str, amount: float, description: str) -> bool:
    try:
        ten_seconds_ago = (get_ist_now() - timedelta(seconds=10)).isoformat()
        response = supabase.table("transactions")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("amount", amount)\
            .eq("description", description.title())\
            .gt("created_at", ten_seconds_ago)\
            .execute()
        return len(response.data) > 0
    except Exception:
        return False

def save_transaction(record: TransactionRecord) -> bool:
    try:
        data = {
            "user_id": record.user_id,
            "amount": record.amount,
            "category_id": record.category_id,
            "description": record.description.title(),
            "transaction_date": record.transaction_date.isoformat()
        }
        supabase.table("transactions").insert(data).execute()
        return True
    except Exception as e:
        raise FinanceManagerException(
            step="Database Insertion Node",
            message=f"Failed to commit transaction: {str(e)}",
            action="SUPPORT TEAM ACTION REQUIRED: Verify Supabase connectivity and schema constraints."
        )

def get_user_stats(user_id: str) -> str:
    try:
        response = supabase.rpc("get_user_statistics", {"p_user_id": user_id}).execute()
        data = response.data
        if not data:
            return "No personal expenses logged."
        total = sum(float(row['total_spent']) for row in data)
        msg = f"**Personal Total Spent: ₹{total:,.2f}**\n\n**Breakdown:**\n"
        for row in data:
            msg += f"{row.get('category_name', 'Other')}: ₹{float(row.get('total_spent', 0)):,.2f}\n"
        return msg
    except Exception as e:
        raise FinanceManagerException(step="Database Fetch Node", message=str(e), action="Retry later.")

def get_global_stats() -> str:
    try:
        response = supabase.rpc("get_global_statistics").execute()
        data = response.data
        if not data:
            return "No expenses logged in the global ledger."
        total = sum(float(row['total_spent']) for row in data)
        msg = f"**GLOBAL LEDGER Total: ₹{total:,.2f}**\n\n**Breakdown:**\n"
        for row in data:
            msg += f"{row.get('category_name', 'Other')}: ₹{float(row.get('total_spent', 0)):,.2f}\n"
        return msg
    except Exception as e:
        raise FinanceManagerException(step="Database Fetch Node", message=str(e), action="Retry later.")
