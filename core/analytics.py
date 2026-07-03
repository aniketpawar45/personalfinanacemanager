import datetime
import calendar
import dateparser
import re
from core.database import get_scoped_client, supabase
from core.utils import get_ist_now, IST_TZ


def parse_date_range(query: str) -> tuple[datetime.datetime, datetime.datetime, str]:
    """Parses natural language strings into strict Indian Standard Time (IST) datetime boundaries."""
    now = get_ist_now()
    query = query.lower().strip()

    # 1. Empty or Today
    if query in ["", "today"]:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end, "Today"

    # 2. Yesterday
    if query == "yesterday":
        start = (now - datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end, "Yesterday"

    # 3. Explicit Relative Periods
    if query in ["month", "this month"]:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(now.year, now.month)[1]
        end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
        return start, end, "This Month"

    if query == "last month":
        first_day_this_month = now.replace(day=1)
        last_day_last_month = first_day_this_month - datetime.timedelta(days=1)
        target_month = last_day_last_month.month
        target_year = last_day_last_month.year
        start = now.replace(year=target_year, month=target_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(year=target_year, month=target_month, day=last_day_last_month.day, hour=23, minute=59,
                          second=59, microsecond=999999)
        return start, end, f"{calendar.month_name[target_month]} {target_year}"

    if query in ["year", "this year"]:
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        return start, end, "This Year"

    if query == "last year":
        target_year = now.year - 1
        start = now.replace(year=target_year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(year=target_year, month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        return start, end, f"Year {target_year}"

    # 4. Specific Year (e.g., "2026")
    if re.match(r'^\d{4}$', query):
        year = int(query)
        start = now.replace(year=year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(year=year, month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        return start, end, f"Year {year}"

    # 5. Specific Month Name
    months = ["january", "february", "march", "april", "may", "june",
              "july", "august", "september", "october", "november", "december",
              "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

    month_match = re.match(r'^([a-z]+)\s*(\d{4})?$', query)
    if month_match and month_match.group(1) in months:
        m_str = month_match.group(1)
        y_str = month_match.group(2)

        for i, m in enumerate(calendar.month_name):
            if m and (m.lower() == m_str or m.lower()[:3] == m_str[:3]):
                target_month = i
                break
        else:
            target_month = now.month

        target_year = int(y_str) if y_str else now.year

        start = now.replace(year=target_year, month=target_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(target_year, target_month)[1]
        end = now.replace(year=target_year, month=target_month, day=last_day, hour=23, minute=59, second=59,
                          microsecond=999999)
        return start, end, f"{calendar.month_name[target_month]} {target_year}"

    # Numeric Month Filter (1-12)
    if re.match(r'^(0?[1-9]|1[0-2])$', query):
        target_month = int(query)
        target_year = now.year
        start = now.replace(year=target_year, month=target_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(target_year, target_month)[1]
        end = now.replace(year=target_year, month=target_month, day=last_day, hour=23, minute=59, second=59,
                          microsecond=999999)
        return start, end, f"{calendar.month_name[target_month]} {target_year}"

    # Fallback to Dateparser
    parsed = dateparser.parse(
        query,
        settings={'RELATIVE_BASE': now, 'TIMEZONE': 'Asia/Kolkata', 'RETURN_AS_TIMEZONE_AWARE': True}
    )
    if not parsed:
        raise ValueError(f"Could not understand date formatting format: {query}")

    if parsed.tzinfo is None:
        parsed = IST_TZ.localize(parsed)

    start = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
    end = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end, start.strftime('%d %b %Y')


def get_report_data(user_id: str, start: datetime.datetime, end: datetime.datetime) -> list:
    """Fetches user transactions strictly within the selected date ranges."""
    client = get_scoped_client(user_id)
    response = client.table("transactions") \
        .select("amount, description, transaction_date, categories(category_name)") \
        .gte("transaction_date", start.isoformat()) \
        .lte("transaction_date", end.isoformat()) \
        .order("transaction_date", desc=True) \
        .execute()
    return response.data


def get_statistics_data(user_id: str, start: datetime.datetime, end: datetime.datetime) -> dict | None:
    """Aggregates transactional spend totals alongside user budgeting metrics."""
    data = get_report_data(user_id, start, end)

    # Securely retrieve the user's budget settings using our client layer
    user_client = get_scoped_client(user_id)
    user_profile = user_client.table("app_users").select("monthly_budget_limit, preferred_currency").eq("telegram_id",
                                                                                                        user_id).execute()

    budget_limit = 0.0
    currency = "INR"
    if user_profile.data:
        budget_limit = float(user_profile.data[0].get("monthly_budget_limit", 0.0))
        currency = user_profile.data[0].get("preferred_currency", "INR")

    if not data and budget_limit == 0.0:
        return None

    cat_map = {}
    total = 0.0
    for item in data:
        amt = float(item['amount'])
        cat = item['categories']['category_name'] if item.get('categories') else "Other"
        cat_map[cat] = cat_map.get(cat, 0.0) + amt
        total += amt

    return {
        "total": total,
        "categories": cat_map,
        "monthly_budget_limit": budget_limit,
        "preferred_currency": currency
    }