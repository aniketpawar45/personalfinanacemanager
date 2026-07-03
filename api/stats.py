from core.analytics import parse_date_range, get_statistics_data

# UX Mapping: Custom signatures for primary categories
CATEGORY_EMOJIS = {
    "groceries": "🥑",
    "transport": "🚀",
    "utilities": "⚡",
    "dining": "🍔",
    "shopping": "🛍️",
    "rent": "🏠",
    "entertainment": "🎬",
    "medical": "💊",
    "other": "📦"
}

def generate_heatmap_bar(value, max_val):
    """Generates a dynamic 5-segment colored scrollbar based on intensity."""
    if max_val <= 0:
        return "🟩🟩🟩🟩🟩"
        
    ratio = value / max_val
    # Determine the indicator block color based on velocity thresholds
    if ratio > 0.70:
        block = "🟥"  # Neon Red Alert
    elif ratio > 0.35:
        block = "🟨"  # Neon Yellow Warning
    else:
        block = "🟩"  # Neon Green Baseline
        
    filled_segments = max(1, int(ratio * 5))
    return (block * filled_segments) + ("░" * (5 - filled_segments))

async def handle_statistics_command(bot, chat_id, command, uid):
    query = command.split(" ")[1] if " " in command else "month"
    start, end, label = parse_date_range(query)
    stats = get_statistics_data(uid, start, end)
    
    if not stats:
        await bot.send_message(chat_id, f"📭 No data found for {label}.")
        return

    msg = f"✨ *NEON ANALYTICS PULSE: {label}*\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    
    max_val = max(stats['categories'].values()) if stats['categories'] else 1
    
    # Sort categories by highest expenditure first for optimal visual flow
    sorted_categories = sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True)
    
    for cat, amt in sorted_categories:
        # Dynamic Emoji lookup with fallback
        lookup_key = cat.lower().strip()
        emoji = CATEGORY_EMOJIS.get(lookup_key, "🔹")
        
        # Generate the color-coded usage scrollbar
        heatmap_scrollbar = generate_heatmap_bar(amt, max_val)
        
        # Render the high-contrast data block
        msg += f"{emoji} *{cat.upper()}*\n"
        msg += f" {heatmap_scrollbar}   `₹{amt:,.2f}`\n\n"
    
    msg += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🔮 *TOTAL METRIC: ₹{stats['total']:,.2f}*\n"
    msg += f"🚦 _Legend: 🟥 High Burn | 🟨 Warning | 🟩 Stable_"
    
    await bot.send_message(chat_id, msg, parse_mode="Markdown")
