import os
import logging
from supabase import create_client
from core.models import TransactionRecord

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

_CATEGORY_CACHE = []


def load_categories_into_cache():
    global _CATEGORY_CACHE
    try:
        res = supabase.table("categories").select("id, category_name").execute()
        _CATEGORY_CACHE = res.data
    except Exception as e:
        logging.error(f"Error loading categories: {e}")
        _CATEGORY_CACHE = []


def get_all_categories(): return _CATEGORY_CACHE


def get_user_role(telegram_id: str):
    try:
        res = supabase.table("app_users").select("role").eq("telegram_id", telegram_id).execute()
        return res.data[0]['role'] if res.data else "unauthenticated"
    except Exception:
        return "unauthenticated"


def get_last_category(description: str):
    """Fetches the last used category for a specific item to suggest it to the user."""
    try:
        res = supabase.table("transactions").select("category_id") \
            .eq("description", description.title()) \
            .order("created_at", desc=True).limit(1).execute()
        return res.data[0]['category_id'] if res.data else None
    except Exception:
        return None


def save_transaction(rec: TransactionRecord):
    data = {
        "user_id": rec.user_id, "amount": rec.amount, "category_id": rec.category_id,
        "description": rec.description.title(), "transaction_date": rec.transaction_date.isoformat()
    }
    return supabase.table("transactions").insert(data).execute()


def get_report_data(uid, start, end):
    try:
        return supabase.table("transactions").select("description, amount, transaction_date") \
            .eq("user_id", uid).gte("transaction_date", start.isoformat()) \
            .lte("transaction_date", end.isoformat()).execute().data
    except Exception:
        return []


def get_user_stats(user_id: str):
    """Executes a database RPC call to get aggregated spend by category."""
    try:
        res = supabase.rpc("get_user_statistics", {"p_user_id": user_id}).execute()
        if not res.data: return "📉 No spending data found."

        total = sum(float(r['total_spent']) for r in res.data)
        stats_str = f"📊 *Total Spent:* ₹{total:,.2f}\n"
        stats_str += "".join([f"🔹 {r['category_name']}: ₹{float(r['total_spent']):,.2f}\n" for r in res.data])
        return stats_str
    except Exception as e:
        logging.error(f"Error fetching stats: {e}")
        return "⚠️ Could not retrieve statistics."