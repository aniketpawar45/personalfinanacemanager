import aiohttp
from core.analytics import parse_date_range, get_statistics_data

async def handle_chart_command(bot, chat_id, command, uid):
    query = command.split(" ")[1] if " " in command else "month"
    start, end, label = parse_date_range(query)
    stats = get_statistics_data(uid, start, end)
    
    if not stats:
        await bot.send_message(chat_id, "📭 No data available for chart.")
        return

    # Prepare data for QuickChart
    labels = list(stats['categories'].keys())
    data = list(stats['categories'].values())
    
    # Construct QuickChart URL (Neon Theme)
    chart_config = {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{"data": data, "backgroundColor": ["#00FFFF", "#FF00FF", "#FFFF00", "#00FF00", "#FF4500"]}]
        },
        "options": {"title": {"display": True, "text": f"Expenditure: {label}"}}
    }
    
    import json
    encoded_config = json.dumps(chart_config)
    chart_url = f"https://quickchart.io/chart?c={encoded_config}"
    
    await bot.send_photo(chat_id, photo=chart_url, caption=f"📊 *Visual Report: {label}*\n💰 *Total: ₹{stats['total']:,.2f}*")
