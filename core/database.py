import os
from supabase import create_client
from datetime import datetime, timedelta

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

def get_all_categories():
    return supabase.table("categories").select("id, category_name").execute().data

def get_last_category(description):
    res = supabase.table("transactions").select("category_id").eq("description", description.title()).order("created_at", desc=True).limit(1).execute()
    return res.data[0]['category_id'] if res.data else None

def check_duplicate(user_id, amount, description):
    ten_seconds_ago = (datetime.now() - timedelta(seconds=10)).isoformat()
    res = supabase.table("transactions").select("id").eq("user_id", str(user_id)).eq("amount", amount).eq("description", description.title()).gt("created_at", ten_seconds_ago).execute()
    return len(res.data) > 0

def save_transaction(user_id, amount, category_id, description, trans_date):
    data = {
        "user_id": str(user_id),
        "amount": amount,
        "category_id": category_id,
        "description": description.title(),
        "transaction_date": trans_date.isoformat()
    }
    return supabase.table("transactions").insert(data).execute()

def get_user_stats(user_id):
    try:
        data = supabase.table("transactions").select("amount, categories(category_name)").eq("user_id", str(user_id)).execute().data
        if not data: return "📊 No expenses logged."
        total, cats = 0.0, {}
        for row in data:
            amt = float(row['amount'])
            total += amt
            cat = row['categories']['category_name'] if row['categories'] else "Other"
            cats[cat] = cats.get(cat, 0) + amt
        msg = f"📊 **Total Spent: ₹{total:,.2f}**\n\n📂 **Breakdown:**\n"
        for c, a in sorted(cats.items(), key=lambda x: x[1], reverse=True):
            msg += f"• {c}: ₹{a:,.2f}\n"
        return msg
    except: return "❌ Error fetching stats."