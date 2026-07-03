import os
import logging
from supabase import create_client, Client
from core.models import TransactionRecord

logger = logging.getLogger(__name__)

# Use SERVICE_ROLE_KEY for backend-authorized persistence
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Critical Security Error: Missing Service Role Key.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def save_transaction(record: TransactionRecord) -> bool:
    try:
        supabase.table("transactions").insert({
            "user_id": record.user_id,
            "amount": record.amount,
            "category_id": record.category_id,
            "description": record.description.title(),
            "transaction_date": record.transaction_date.isoformat()
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Secure save failed: {str(e)}")
        return False

# ... keep existing functions (get_user_role, get_all_categories, etc.) as they are ...