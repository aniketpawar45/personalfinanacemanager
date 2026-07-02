import os
import logging
from supabase import create_client, Client
from datetime import datetime, timedelta
from core.models import TransactionRecord

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
_CATEGORY_CACHE = []

def load_categories_into_cache():
    global _CATEGORY_CACHE
    res = supabase.table("categories").select("id, category_name").execute()
    _CATEGORY_CACHE = res.data

def get_all_categories(): return _CATEGORY_CACHE

def get_user_role(telegram_id: str):
    res = supabase.table("app_users").select("role").eq("telegram_id", telegram_id).execute()
    return res.data[0]['role'] if res.data else "unauthenticated"

def get_last_category(description: str):
    res = supabase.table("transactions").select("category_id").eq("description", description.title()).order("created_at", desc=True).limit(1).execute()
    return res.data[0]['category_id'] if res.data else None

def save_transaction(record: TransactionRecord):
    data = {"user_id": record.user_id, "amount": record.amount, "category_id": record.category_id, "description": record.description.title(), "transaction_date": record.transaction_date.isoformat()}
    return supabase.table("transactions").insert(data).execute()

def get_report_data(user_id: str, start: datetime, end: datetime):
    res = supabase.table("transactions").select("description, amount, transaction_date").eq("user_id", user_id).gte("transaction_date", start.isoformat()).lte("transaction_date", end.isoformat()).execute()
    return res.data

def get_user_stats(user_id: str):
    res = supabase.rpc("get_user_statistics", {"p_user_id": user_id}).execute()
    return f"📊 *Total:* ₹{sum(float(r['total_spent']) for r in res.data):,.2f}\n" + "".join([f"🔹 {r['category_name']}: ₹{float(r['total_spent']):,.2f}\n" for r in res.data]) if res.data else "📉 No data."