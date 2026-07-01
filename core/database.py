import os
from supabase import create_client, Client

# Initialize safely (prevents crashes during Vercel build process if env vars are missing)
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

def get_category_id(category_name: str) -> int:
    """Fetches the category ID from the database, defaults to 'Other' if not found."""
    if not supabase: return None
    try:
        response = supabase.table("categories").select("id").eq("category_name", category_name.title()).execute()
        if response.data:
            return response.data[0]['id']
            
        # Fallback to 'Other'
        fallback = supabase.table("categories").select("id").eq("category_name", "Other").execute()
        return fallback.data[0]['id'] if fallback.data else None
    except Exception as e:
        print(f"Database Error (Category): {e}")
        return None

def save_transaction(user_id: str, amount: float, category_id: int, description: str) -> bool:
    """Inserts a new transaction into the Supabase database."""
    if not supabase: return False
    try:
        data = {
            "user_id": str(user_id),
            "amount": amount,
            "category_id": category_id,
            "description": description
        }
        supabase.table("transactions").insert(data).execute()
        return True
    except Exception as e:
        print(f"Database Error (Insert): {e}")
        return False


def get_user_stats(user_id: str) -> str:
    """Fetches and formats the user's expense statistics from Supabase."""
    if not supabase: return "Database connection error."
    try:
        # Fetch all transactions for this user, including the category name
        response = supabase.table("transactions").select("amount, categories(category_name)").eq("user_id",
                                                                                                 str(user_id)).execute()

        if not response.data:
            return "📊 You haven't logged any expenses yet."

        total = 0.0
        category_totals = {}

        # Calculate totals
        for row in response.data:
            amt = float(row.get("amount", 0))
            total += amt

            # Extract category name safely
            cat_data = row.get("categories")
            cat_name = cat_data.get("category_name", "Other") if isinstance(cat_data, dict) else "Other"

            category_totals[cat_name] = category_totals.get(cat_name, 0) + amt

        # Format the message
        msg = f"📊 **Your Expense Summary**\n\n"
        msg += f"**Total Spent:** ₹{total:,.2f}\n\n"
        msg += "📂 **By Category:**\n"

        # Sort categories by highest spent
        sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        for cat, amt in sorted_cats:
            msg += f"  • {cat}: ₹{amt:,.2f}\n"

        return msg
    except Exception as e:
        print(f"Stats Error: {e}")
        return "❌ Could not retrieve statistics."