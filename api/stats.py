from core.analytics import parse_date_range, get_statistics_data

CATEGORY_EMOJIS = {
    "groceries": "🛒", "transport": "🚗", "utilities": "💡",
    "dining": "🍔", "shopping": "🛍️", "rent": "🏠",
    "entertainment": "🎬", "medical": "🏥", "other": "📦"
}


def generate_heatmap_bar(value: float, max_val: float) -> str:
    """Generates a dynamic progress bar based on user budget metrics."""
    if max_val <= 0: return "⬜⬜⬜⬜⬜"
    ratio = value / max_val
    block = "🔴" if ratio > 0.85 else ("🟡" if ratio > 0.50 else "🟢")
    filled_segments = min(5, max(1, int(ratio * 5)))
    return (block * filled_segments) + ("⬜" * (5 - filled_segments))


async def handle_statistics_command(bot, chat_id, command, uid):
    query = command.split(" ")[1] if " " in command else "month"
    try:
        start, end, label = parse_date_range(query)
        stats = get_statistics_data(uid, start, end)
    except ValueError as ve:
        await bot.send_message(chat_id, f"❌ {str(ve)}")
        return

    if not stats:
        await bot.send_message(chat_id, f"ℹ️ No data found for *{label}*.", parse_mode="Markdown")
        return

    currency = stats.get("preferred_currency", "INR")
    msg = f"📊 *FINANCIAL PULSE: {label.upper()}*\n"
    msg += f"{'─' * 24}\n"

    max_val = max(stats['categories'].values()) if stats['categories'] else 1.0
    sorted_categories = sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True)

    for cat, amt in sorted_categories:
        emoji = CATEGORY_EMOJIS.get(cat.lower().strip(), "📦")
        scrollbar = generate_heatmap_bar(amt, max_val)
        msg += f"{emoji} *{cat.upper()}*\n`  {scrollbar}  ` {currency} {amt:,.2f}\n\n"

    msg += f"{'─' * 24}\n"
    msg += f"💰 *TOTAL METRIC: {currency} {stats['total']:,.2f}*\n"

    # Render interactive budget usage warnings if limits are configured
    budget = stats.get("monthly_budget_limit", 0.0)
    if budget > 0:
        pct = (stats['total'] / budget) * 100
        progress_bar = generate_heatmap_bar(stats['total'], budget)
        msg += f"🎯 *Budget Limit:* {currency} {budget:,.2f}\n"
        msg += f"📈 *Usage Volume:* `{progress_bar}` ({pct:.1f}%)\n"
        if pct >= 100:
            msg += "\n🚨 *CRITICAL ALERT: You have exceeded your monthly budget allocation!*"
        elif pct >= 85:
            msg += "\n⚠️ *WARNING: High cash burn velocity detected.*"

    await bot.send_message(chat_id, msg, parse_mode="Markdown")