import aiohttp
import json
import urllib.parse
import datetime
from core.analytics import parse_date_range, get_statistics_data


def resolve_flexible_bounds(query_str):
    """Converts flexible strings like 'June' or integers into proper date ranges."""
    query_clean = query_str.lower().strip()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))  # IST

    # 1. Try standard parser first
    try:
        start, end, label = parse_date_range(query_clean)
        if start and end:
            return start, end, label
    except Exception:
        pass

    # 2. Match month names explicitly
    months_map = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
        "november": 11, "nov": 11, "december": 12, "dec": 12
    }

    if query_clean in months_map:
        target_month = months_map[query_clean]
        year = now.year
        start = datetime.datetime(year, target_month, 1, 0, 0, 0, tzinfo=now.tzinfo)
        if target_month == 12:
            end = datetime.datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=now.tzinfo) - datetime.timedelta(microseconds=1)
        else:
            end = datetime.datetime(year, target_month + 1, 1, 0, 0, 0, tzinfo=now.tzinfo) - datetime.timedelta(
                microseconds=1)
        return start, end, query_str.capitalize()

    # 3. Fallback to Numeric Days (e.g., /chart 5 -> last 5 days)
    if query_clean.isdigit():
        days = int(query_clean)
        start = (now - datetime.timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now, f"Last {days} Days"

    # Default fallback to current month lookups
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now, "Current Month"


async def handle_chart_command(bot, chat_id, command, uid):
    parts = command.split(maxsplit=1)
    query_param = parts[1] if len(parts) > 1 else "month"

    # Resolve the dates safely via our flexible wrapper
    start, end, label = resolve_flexible_bounds(query_param)
    stats = get_statistics_data(uid, start, end)

    if not stats or not stats.get('categories'):
        await bot.send_message(bot, chat_id,
                               f"⚠️ *No data found within the filter:* `{label}`\n_Try logging a transaction first!_")
        return

    labels = list(stats['categories'].keys())
    data = list(stats['categories'].values())
    currency = stats.get("preferred_currency", "INR")

    dark_neon_colors = ["#00B0FF", "#FFAB00", "#00E676", "#AA00FF", "#FF3D00", "#00E5FF"]

    chart_config = {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": data,
                "backgroundColor": dark_neon_colors[:len(labels)],
                "borderColor": "#121212",
                "borderWidth": 2
            }]
        },
        "options": {
            "title": {
                "display": True,
                "text": f"EXPENDITURE PROFILE: {label.upper()} ({currency})",
                "fontColor": "#FFFFFF",
                "fontSize": 16,
                "fontStyle": "bold"
            },
            "legend": {
                "position": "bottom",
                "labels": {"fontColor": "#B0BEC5", "fontSize": 12, "fontStyle": "bold"}
            },
            "plugins": {
                "datalabels": {
                    "display": True,
                    "color": "#FFFFFF",
                    "font": {"weight": "bold", "size": 13}
                }
            }
        }
    }

    json_config = json.dumps(chart_config)
    encoded_config = urllib.parse.quote(json_config)
    chart_url = f"https://quickchart.io/chart?c={encoded_config}&bkg=0A0A0A"

    await bot.send_photo(
        chat_id,
        photo=chart_url,
        caption=f"📊 **Visual Report: {label}**\n💰 **Total Metric: {currency} {stats['total']:,.2f}**"
    )