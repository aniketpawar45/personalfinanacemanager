from core.analytics import parse_date_range, get_statistics_data

async def handle_statistics_command(bot, chat_id, command, uid):
    query = command.split(" ")[1] if " " in command else "month"
    start, end, label = parse_date_range(query)
    stats = get_statistics_data(uid, start, end)
    
    if not stats:
        await bot.send_message(chat_id, f"📭 No data for {label}.")
        return

    # NEON-AESTHETIC: High-contrast Emoji-Matrix styling
    # Symbols: 🔷 (Cyan), 🌸 (Pink/Magenta), ⚡ (Yellow/Gold)
    msg = f"✨ *NEON ANALYTICS: {label}*\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    
    max_val = max(stats['categories'].values()) if stats['categories'] else 1
    
    for cat, amt in stats['categories'].items():
        # High-Contrast Unicode bars
        width = 6
        filled = int((amt / max_val) * width) if max_val > 0 else 0
        bar = "▓" * filled + "░" * (width - filled)
        
        # Consistent colorful visual indicators
        msg += f"🔷 *{cat}*\n"
        msg += f"🌸 {bar} `₹{amt:,.0f}`\n"
    
    msg += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"⚡ *TOTAL EXPENDITURE: ₹{stats['total']:,.2f}*\n"
    
    await bot.send_message(chat_id, msg, parse_mode="Markdown")
