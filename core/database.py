import os
from supabase import create_client, Client

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

def get_category_id(category_name: str) -> int:
    try:
        response = supabase.table("categories").select("id").eq("category_name", category_name.title()).execute()
        return response.data[0]['id'] if response.data else supabase.table("categories").select("id").eq("category_name", "Other").execute().data[0]['id']
    except: return 1

def save_transaction(user_id, amount, category_id, description):
    try:
        supabase.table("transactions").insert({"user_id": str(user_id), "amount": amount, "category_id": category_id, "description": description}).execute()
        return True
    except: return False

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
        msg = f"📊 **Total: ₹{total:,.2f}**\n\n📂 **Breakdown:**\n"
        for c, a in sorted(cats.items(), key=lambda x: x[1], reverse=True):
            msg += f"• {c}: ₹{a:,.2f}\n"
        return msg
    except: return "❌ Error fetching stats."