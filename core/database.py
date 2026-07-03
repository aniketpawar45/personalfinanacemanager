import os
import logging
from supabase import create_client, Client
from datetime import timedelta
from core.models import TransactionRecord
from core.utils import get_ist_now, FinanceManagerException

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
# CRITICAL FIX: Switch to a restricted public/anon key for standard user data flows.
# If an administrative action is required (e.g., global syncs), it must be explicitly restricted.
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Critical Security Error: Missing Supabase credentials in environment configurations.")

# Instantiate base client
_base_supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
_CATEGORY_CACHE = []

def get_scoped_client(telegram_id: str) -> Client:
    """
    Architectural Fix: Returns a Supabase client instance scoped to the
    active user session by injecting custom session headers that enforce PostgreSQL RLS.
    """
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # CRITICAL FIX: Direct header injection without calling non-existent auth methods
    client.postgrest.headers.update({
        "X-Telegram-User-Id": str(telegram_id)
    })
    return client

def load_categories_into_cache():
    global _CATEGORY_CACHE
    try:
        response = _base_supabase.table("categories").select("id, category_name").execute()
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
        response = _base_supabase.table("app_users").select("role").eq("telegram_id", telegram_id).execute()
        if response.data:
            return response.data[0]['role']
        return "unauthenticated"
    except Exception:
        return "unauthenticated"

def get_last_category(telegram_id: str, description: str) -> int | None:
    try:
        client = get_scoped_client(telegram_id)
        response = client.table("transactions")\
            .select("category_id")\
            .eq("description", description.title())\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        return response.data[0]['category_id'] if response.data else None
    except Exception:
        return None

def check_duplicate(telegram_id: str, amount: float, description: str) -> bool:
    try:
        client = get_scoped_client(telegram_id)
        ten_seconds_ago = (get_ist_now() - timedelta(seconds=10)).isoformat()
        response = client.table("transactions")\
            .select("id")\
            .eq("amount", amount)\
            .eq("description", description.title())\
            .gt("created_at", ten_seconds_ago)\
            .execute()
        return len(response.data) > 0
    except Exception:
        return False

def save_transaction(record: TransactionRecord) -> bool:
    try:
        client = get_scoped_client(record.user_id)
        data = {
            "user_id": record.user_id,
            "amount": record.amount,
            "category_id": record.category_id,
            "description": record.description.title(),
            "transaction_date": record.transaction_date.isoformat(),
            "remarks": record.remarks
        }
        client.table("transactions").insert(data).execute()
        return True
    except Exception as e:
        raise FinanceManagerException(
            step="Database Insertion Node",
            message=f"Failed to commit transaction: {str(e)}",
            action="SUPPORT TEAM ACTION REQUIRED: Verify Supabase schema structures and RLS configurations."
        )

def get_user_stats(telegram_id: str) -> str:
    try:
        client = get_scoped_client(telegram_id)
        response = client.rpc("get_user_statistics", {"p_user_id": telegram_id}).execute()
        data = response.data
        if not data:
            return "No personal expenses logged."
        total = sum(float(row['total_spent']) for row in data)
        msg = f"**Personal Total Spent: ₹{total:,.2f}**\n\n**Breakdown:**\n"
        for row in data:
            msg += f"• {row.get('category_name', 'Other')}: ₹{float(row.get('total_spent', 0)):,.2f}\n"
        return msg
    except Exception as e:
        raise FinanceManagerException(step="Database Fetch Node", message=str(e), action="Retry later.")

def get_global_stats(admin_telegram_id: str) -> str:
    if get_user_role(admin_telegram_id) != "admin":
        return "Access Denied: Admin privileges required."
    try:
        response = _base_supabase.rpc("get_global_statistics").execute()
        data = response.data
        if not data:
            return "No expenses logged in the global ledger."
        total = sum(float(row['total_spent']) for row in data)
        msg = f"**GLOBAL LEDGER Total: ₹{total:,.2f}**\n\n**Breakdown:**\n"
        for row in data:
            msg += f"• {row.get('category_name', 'Other')}: ₹{float(row.get('total_spent', 0)):,.2f}\n"
        return msg
    except Exception as e:
        raise FinanceManagerException(step="Database Fetch Node", message=str(e), action="Retry later.")