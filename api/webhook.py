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

        if data.startswith("yes_future:"):
            _, amt, desc, d_str = data.split(":", 3)
            date = datetime.fromisoformat(d_str)
            last_cat_id = get_last_category(desc)
            if last_cat_id:
                save_transaction(q["from"]["id"], float(amt), last_cat_id, desc, date)
                cats = get_all_categories()
                cat_name = next((c['category_name'] for c in cats if c['id'] == last_cat_id), "Other")
                await bot.edit_message_text(chat_id=q["message"]["chat"]["id"], message_id=q["message"]["message_id"],
                                            text=f"✅ **Saved!**\n🛒 {desc}\n💰 ₹{amt}\n📂 {cat_name}\n📅 {date.strftime('%d-%m-%Y')}",
                                            parse_mode="Markdown")
            else:
                categories = get_all_categories()
                buttons = [[InlineKeyboardButton(c['category_name'],
                                                 callback_data=f"cat:{c['id']}:{amt}:{desc}:{date.isoformat()}")] for c
                           in categories]
                await bot.edit_message_text(chat_id=q["message"]["chat"]["id"], message_id=q["message"]["message_id"],
                                            text=f"🏷️ New item! **{desc}** (₹{amt}). Select category:",
                                            reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

        elif data == "no_future":
            await bot.edit_message_text(chat_id=q["message"]["chat"]["id"], message_id=q["message"]["message_id"],
                                        text="❌ Entry cancelled.")

        elif data.startswith("cat:"):
            parts = data.split(":", 4)
            cat_id, amt, desc, d_str = parts[1], parts[2], parts[3], parts[4]
            date = datetime.fromisoformat(d_str)
            save_transaction(q["from"]["id"], float(amt), int(cat_id), desc, date)
            await bot.edit_message_text(chat_id=q["message"]["chat"]["id"], message_id=q["message"]["message_id"],
                                        text=f"✅ Saved Successfully!\n🛒 {desc}\n💰 ₹{amt}")

        # --- NEW DELETE LOGIC ---
        elif data.startswith("del_item:"):
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
                                            text="🗑️ No more records to show.")

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

    elif "message" in update and "text" in update["message"]:
        msg, uid, cid = update["message"], update["message"]["from"]["id"], update["message"]["chat"]["id"]
        text = msg["text"].strip()

        if text.startswith("/start"):
            await bot.send_message(cid, "👋 Send expense (e.g., 'Milk 40') or /stats. Use /delete to manage records.")
        elif text.startswith("/stats"):
            await bot.send_message(cid, get_user_stats(uid), parse_mode="Markdown")

        # --- NEW DELETE COMMAND ---
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
                await bot.send_message(cid, "Select an item to delete:",
                                       reply_markup=get_delete_keyboard(txs, date_str, 0))

        else:
            amt, desc, date = parse_expense_text(text)
            if amt <= 0:
                await bot.send_message(cid, "⚠️ Could not parse amount.")
            elif check_duplicate(uid, amt, desc):
                await bot.send_message(cid, "⚠️ Duplicate entry prevented.")
            elif date > datetime.now():
                kb = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Yes", callback_data=f"yes_future:{amt}:{desc}:{date.isoformat()}"),
                      InlineKeyboardButton("No", callback_data="no_future")]])
                await bot.send_message(cid, f"⚠️ Future date detected! Are you sure?", reply_markup=kb,
                                       parse_mode="Markdown")
            else:
                last_cat_id = get_last_category(desc)
                if last_cat_id:
                    save_transaction(uid, amt, last_cat_id, desc, date)
                    await bot.send_message(cid, f"✅ Auto-Saved!\n🛒 {desc}\n💰 ₹{amt}")
                else:
                    categories = get_all_categories()
                    buttons = [[InlineKeyboardButton(c['category_name'],
                                                     callback_data=f"cat:{c['id']}:{amt}:{desc}:{date.isoformat()}")]
                               for c in categories]
                    await bot.send_message(cid, f"🏷️ New item! **{desc}** (₹{amt}). Select category:",
                                           reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    return {"status": "ok"}