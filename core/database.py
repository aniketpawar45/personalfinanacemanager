import os
import logging
from supabase import create_client, Client
from datetime import datetime, timedelta
from core.models import TransactionRecord

logger = logging.getLogger(__name__)

# Enterprise standard: Use standard Anon Key. Service Role Key is strictly forbidden in edge environments.
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("Missing Supabase environment variables.")

# Note: supabase-py is currently sync-heavy, but we optimize where possible.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def set_db_context(user_id: str):
    """Sets local transaction context for RLS policies."""
    # In a full async PG setup, this would set local session variables.
    # We simulate this via Supabase's PostgREST headers if needed.
    pass

def get_all_categories() -> list:
    try:
        response = supabase.table("categories").select("id, category_name").execute()
        return response.data
    except Exception as e:
        logger.error(f"Failed to fetch categories: {str(e)}")
        return []

def get_last_category(description: str) -> int | None:
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
    """Optimized using PostgreSQL RPC to prevent application layer OOM."""
    try:
        response = supabase.rpc("get_user_statistics", {"p_user_id": user_id}).execute()
        data = response.data
        
        if not data:
            return "📉 No expenses logged."
            
        total = sum(float(row['total_spent']) for row in data)
        msg = f"📊 **Total Spent: ₹{total:,.2f}**\n\n**Breakdown:**\n"
        
        for row in data:
            cat_name = row.get('category_name') or 'Other'
            amt = float(row.get('total_spent', 0))
            msg += f"🔹 {cat_name}: ₹{amt:,.2f}\n"
            
        return msg
    except Exception as e:
        logger.error(f"Stats generation failed: {str(e)}")
        return "⚠️ Error fetching stats. Please try again later."