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
    
    # DARK-THEMED NEON PALETTE (STRICTLY NO PINK)
    # Deep, highly saturated electric tones engineered for ultimate contrast
    dark_neon_colors = [
        "#00B0FF",  # Electric Cyan / Deep Blue
        "#FFAB00",  # Saturated Amber / Gold
        "#00E676",  # Neon Emerald Green
        "#AA00FF",  # Deep Violet / Purple
        "#FF3D00",  # Electric Dark Orange
        "#00E5FF"   # Bright Turquoise
    ]
    
    # Configuration optimizing internal text visibility using absolute white bold metrics
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
                "text": f"EXPENDITURE PROFILE: {label.upper()}",
                "fontColor": "#FFFFFF",
                "fontSize": 16,
                "fontStyle": "bold"
            },
            "legend": {
                "position": "bottom",
                "labels": {
                    "fontColor": "#B0BEC5",  # High-contrast light gray text for legends
                    "fontSize": 12,
                    "boxWidth": 12,
                    "fontStyle": "bold"
                }
            },
            "plugins": {
                "datalabels": {
                    "display": True,
                    "color": "#FFFFFF",  # CRITICAL: High-contrast white text over deep neon slices
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
    
    # Using an ultra-dark canvas block (&bkg=0A0A0A) to make deep neon tones pop intensely
    chart_url = f"https://quickchart.io/chart?c={encoded_config}&bkg=0A0A0A"
    
    await bot.send_photo(
        chat_id, 
        photo=chart_url, 
        caption=f"📊 **Visual Report: {label}**\n💰 **Total Metric: ₹{stats['total']:,.2f}**"
    )
