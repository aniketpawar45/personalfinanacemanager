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
