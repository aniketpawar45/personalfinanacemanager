import os, logging, dateparser
from fastapi import FastAPI, Request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from core.database import (save_transaction, get_all_categories, check_duplicate, get_user_stats,
                           get_last_category, get_user_transactions, delete_transaction)
from core.engine import parse_expense_text

logging.getLogger("httpx").setLevel(logging.WARNING)
app = FastAPI()
bot = Bot(token=os.environ.get("TELEGRAM_BOT_TOKEN"))


def get_delete_keyboard(transactions, date_str, offset):
    buttons = []
    for tx in transactions:
        buttons.append([InlineKeyboardButton(f"❌ {tx['description']} - ₹{tx['amount']}",
                                             callback_data=f"del_item:{tx['id']}:{date_str}:{offset}")])

    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"del_nav:{date_str}:{offset - 5}"))
    nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"del_nav:{date_str}:{offset + 5}"))
    buttons.append(nav_buttons)
    return InlineKeyboardMarkup(buttons)


@app.post("/api/webhook")
async def handle(request: Request):
    update = await request.json()

    if "callback_query" in update:
        q = update["callback_query"]
        data = q["data"]

        if data.startswith("del_item:"):
            _, tx_id, date_str, offset = data.split(":")
            delete_transaction(tx_id)
            await bot.answer_callback_query(q["id"], text="Deleted!")
            target_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str != "None" else None
            txs = get_user_transactions(q["from"]["id"], date=target_date, limit=5, offset=int(offset))
            if txs:
                await bot.edit_message_reply_markup(chat_id=q["message"]["chat"]["id"],
                                                    message_id=q["message"]["message_id"],
                                                    reply_markup=get_delete_keyboard(txs, date_str, int(offset)))
            else:
                await bot.edit_message_text(chat_id=q["message"]["chat"]["id"], message_id=q["message"]["message_id"],
                                            text="🗑️ No more records.")

        elif data.startswith("del_nav:"):
            _, date_str, offset = data.split(":")
            target_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str != "None" else None
            txs = get_user_transactions(q["from"]["id"], date=target_date, limit=5, offset=int(offset))
            if txs:
                await bot.edit_message_reply_markup(chat_id=q["message"]["chat"]["id"],
                                                    message_id=q["message"]["message_id"],
                                                    reply_markup=get_delete_keyboard(txs, date_str, int(offset)))
            else:
                await bot.answer_callback_query(q["id"], text="No more records.")
        # ... (rest of your existing logic for yes_future, cat, etc.) ...

    elif "message" in update and "text" in update["message"]:
        # ... (other handlers) ...
        elif text.startswith("/delete"):
        parts = text.split(" ", 1)
        target_date = None
        date_str = "None"
        if len(parts) > 1:
            target_date = dateparser.parse(parts[1])
            if target_date: date_str = target_date.strftime('%Y-%m-%d')

        txs = get_user_transactions(uid, date=target_date, limit=5, offset=0)
        if not txs:
            await bot.send_message(cid, "No records found.")
        else:
            await bot.send_message(cid, "Select an item to delete:", reply_markup=get_delete_keyboard(txs, date_str, 0))


return {"status": "ok"}