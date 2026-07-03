import os
import logging
from supabase import create_client, Client
from datetime import datetime, timedelta
from core.models import TransactionRecord

logger = logging.getLogger(__name__)

# Trusted Backend Operations
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Critical Security Error: Missing Supabase Service Role Key or URL.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Global In-Memory Cache
_CATEGORY_CACHE = []

def load_categories_into_cache():
    """Fetches categories from DB into Vercel RAM during app boot."""
    global _CATEGORY_CACHE
    try:
        response = supabase.table("categories").select("id, category_name").execute()
        if response.data:
            _CATEGORY_CACHE = response.data
            logger.info("✅ Categories successfully loaded into memory cache.")
    except Exception as e:
        logger.error(f"Failed to load categories into cache: {str(e)}")

def get_all_categories() -> list:
    """O(1) Memory Lookup."""
    global _CATEGORY_CACHE
    if not _CATEGORY_CACHE:
        load_categories_into_cache()
    return _CATEGORY_CACHE

def get_user_role(telegram_id: str) -> str:
    """Enterprise RBAC: Identifies user privileges."""
    try:
        response = supabase.table("app_users").select("role").eq("telegram_id", telegram_id).execute()
        if response.data:
            return response.data[0]['role']
        return "unauthenticated"
    except Exception as e:
        logger.error(f"Failed to fetch user role: {str(e)}")
        return "unauthenticated"

def get_last_category(description: str) -> int | None:
    """Historical lookup to auto-categorize recurring items."""
    try:
        response = supabase.table("transactions")\
            .select("category_id")\
            .eq("description", description.title())\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        return response.data[0]['category_id'] if response.data else None
    except Exception as e:
        logger.error(f"Failed to fetch last category: {str(e)}")
        return None

def check_duplicate(user_id: str, amount: float, description: str) -> bool:
    try:
        ten_seconds_ago = (datetime.now() - timedelta(seconds=10)).isoformat()
        response = supabase.table("transactions")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("amount", amount)\
            .eq("description", description.title())\
            .gt("created_at", ten_seconds_ago)\
            .execute()
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Duplicate check failed: {str(e)}")
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
        logger.error(f"Transaction save failed: {str(e)}")
        return False

def get_user_stats(user_id: str) -> str:
    try:
        response = supabase.rpc("get_user_statistics", {"p_user_id": user_id}).execute()
        data = response.data
        if not data:
            return "📉 No personal expenses logged."
            
        total = sum(float(row['total_spent']) for row in data)
        msg = f"📊 **Personal Total Spent: ₹{total:,.2f}**\n\n**Breakdown:**\n"
        for row in data:
            cat_name = row.get('category_name') or 'Other'
            amt = float(row.get('total_spent', 0))
            msg += f"🔹 {cat_name}: ₹{amt:,.2f}\n"
        return msg
    except Exception as e:
        logger.error(f"Stats generation failed: {str(e)}")
        return "⚠️ Error fetching personal stats."

def get_global_stats() -> str:
    try:
        response = supabase.rpc("get_global_statistics").execute()
        data = response.data
        if not data:
            return "📉 No expenses logged in the global ledger."
            
        total = sum(float(row['total_spent']) for row in data)
        msg = f"🌍 **GLOBAL LEDGER Total: ₹{total:,.2f}**\n\n**Breakdown:**\n"
        for row in data:
            cat_name = row.get('category_name') or 'Other'
            amt = float(row.get('total_spent', 0))
            msg += f"🔹 {cat_name}: ₹{amt:,.2f}\n"
        return msg
    except Exception as e:
        logger.error(f"Global stats generation failed: {str(e)}")
        return "⚠️ Error fetching global stats."