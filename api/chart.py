import aiohttp
import json
import urllib.parse
from core.analytics import parse_date_range, get_statistics_data

async def handle_chart_command(bot, chat_id, command, uid):
    query = command.split(" ")[1] if " " in command else "month"
    start, end, label = parse_date_range(query)
    stats = get_statistics_data(uid, start, end)
    
    if not stats:
        await bot.send_message(chat_id, "📭 No data available for chart.")
        return

    labels = list(stats['categories'].keys())
    data = list(stats['categories'].values())
    
    # PREMIUM HIGH-CONTRAST NEON PALETTE
    # Each neon color is explicitly selected for maximum vibrancy against dark/light interfaces
    neon_colors = [
        "#00E5FF",  # Electric Cyan
        "#FF007F",  # Neon Rose / Magenta
        "#FFD700",  # Neon Gold / Yellow
        "#39FF14",  # Neon Green
        "#9D00FF",  # Neon Purple
        "#FF5722"   # Neon Orange
    ]
    
    # Constructing QuickChart config with explicit font weights and custom label overrides
    chart_config = {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": data,
                "backgroundColor": neon_colors[:len(labels)],
                "borderColor": "#121212",
                "borderWidth": 2
            }]
        },
        "options": {
            "title": {
                "display": True,
                "text": f"EXPENDITURE PROFILE: {label.upper()}",
                "fontColor": "#FFFFFF",
                "fontSize": 16,
                "fontStyle": "bold"
            },
            "legend": {
                "position": "bottom",
                "labels": {
                    "fontColor": "#E0E0E0",
                    "fontSize": 12,
                    "boxWidth": 12
                }
            },
            "plugins": {
                "datalabels": {
                    "display": True,
                    "color": "#000000",  # Dark text overlay for perfect readability on neon backgrounds
                    "font": {
                        "weight": "bold",
                        "size": 13
                    }
                }
            }
        }
    }
    
    # URL Encode the configuration string safely
    json_config = json.dumps(chart_config)
    encoded_config = urllib.parse.quote(json_config)
    
    # We include a dark background canvas wrapper (&bkg=1e1e1e) to isolate and make neon colors pop
    chart_url = f"https://quickchart.io/chart?c={encoded_config}&bkg=1E1E1E"
    
    await bot.send_photo(
        chat_id, 
        photo=chart_url, 
        caption=f"📊 *Visual Report: {label}*\n💰 *Total Metric: ₹{stats['total']:,.2f}*"
    )
