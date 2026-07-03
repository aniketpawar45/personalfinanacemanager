import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from core.analytics import parse_date_range
from core.database import get_deletable_entries
from core.utils import get_ist_now


def build_deletion_keyboard(entries: list, selected_ids: list, query_str: str) -> InlineKeyboardMarkup:
    """Generates a high-contrast checklist interface for tracking selections dynamically."""
    buttons = []

    # Item Rows with Selection States
    for item in entries:
        t_id = item['id']
        is_selected = t_id in selected_ids
        checkbox = "✅" if is_selected else "⬜"

        dt = datetime.datetime.fromisoformat(item['transaction_date'])
        date_lbl = dt.strftime("%d-%b")

        btn_text = f"{checkbox} [{date_lbl}] {item['description'][:12]} - ₹{float(item['amount']):,.0f}"
        csv_ids = ",".join(map(str, selected_ids)) if selected_ids else "none"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"del_tgl:{t_id}:{csv_ids}:{query_str}")])

    # Super Action Utilities (BA Enhancement)
    all_ids = [e['id'] for e in entries]
    csv_all = ",".join(map(str, all_ids))

    action_row = [
        InlineKeyboardButton("✨ Select All", callback_data=f"del_all:{csv_all}:{query_str}"),
        InlineKeyboardButton("🔄 Clear All", callback_data=f"del_clr:{query_str}")
    ]
    buttons.append(action_row)

    # Submission Layer
    if selected_ids:
        csv_selected = ",".join(map(str, selected_ids))
        buttons.append([InlineKeyboardButton("🔥 Confirm Deletion 🔥", callback_data=f"del_cmt:{csv_selected}")])

    return InlineKeyboardMarkup(buttons)


async def handle_delete_command(bot: Bot, chat_id: int, command: str, uid: str):
    """Entry point for /delete parsing expressions via flexible boundaries."""
    parts = command.split(" ", 1)
    query_param = parts[1].strip().lower() if len(parts) > 1 else ""

    try:
        if not query_param:
            now = get_ist_now()
            start = now - datetime.timedelta(days=90)
            end = now
            label = "Last 90 Days"
            query_param = "rolling_90"
        else:
            start, end, label = parse_date_range(query_param)
    except Exception:
        await bot.send_message(chat_id,
                               "⚠️ **Invalid Time Window**\nCould not extract date limits. Try: `/delete 03 may` or `/delete may`")
        return

    entries = get_deletable_entries(uid, start, end, limit=5)

    if not entries:
        await bot.send_message(chat_id, f"🔍 **No entries found** within the specified cluster frame: `{label}`")
        return

    msg = (
        f"🗑️ **Ledger Management Module: {label.upper()}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Select the items you want to permanently scrub from your ledger logs using the buttons below:"
    )

    reply_markup = build_deletion_keyboard(entries, [], query_param)
    await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", reply_markup=reply_markup)