import datetime
import calendar
import dateparser
from core.database import supabase
from core.utils import get_ist_now, IST_TZ

def parse_date_range(query: str) -> tuple[datetime.datetime, datetime.datetime, str]:
    """Parses natural language into strict IST datetime boundaries."""
    now = get_ist_now()
    query = query.lower().strip()
    
    if query in ["", "today"]:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end, "Today"
        
    elif query == "yesterday":
        start = (now - datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end, "Yesterday"
        
    elif query == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(now.year, now.month)[1]
        end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
        return start, end, "This Month"
        
    elif query == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        return start, end, "This Year"
        
    else:
        # Fallback to dateparser for custom dates (e.g., "August 2023", "12th Jan")
        parsed = dateparser.parse(
            query, 
            settings={'RELATIVE_BASE': now, 'TIMEZONE': 'Asia/Kolkata', 'RETURN_AS_TIMEZONE_AWARE': True}
        )
        if not parsed:
            raise ValueError(f"Could not understand the date format: {query}")
            
        if parsed.tzinfo is None:
            parsed = IST_TZ.localize(parsed)
            
        start = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
        end = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end, start.strftime('%d %b %Y')

def get_report_data(user_id: str, start: datetime.datetime, end: datetime.datetime) -> list:
    """Fetches transactions strictly within the temporal boundaries."""
    response = supabase.table("transactions")\
        .select("amount, description, transaction_date, categories(category_name)")\
        .eq("user_id", user_id)\
        .gte("transaction_date", start.isoformat())\
        .lte("transaction_date", end.isoformat())\
        .order("transaction_date", desc=True)\
        .execute()
    return response.data
