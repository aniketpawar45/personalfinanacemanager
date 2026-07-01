import os, logging
from fastapi import FastAPI, Request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from core.database import save_transaction, get_category_id, check_duplicate, get_user_stats
from core.engine import parse_expense_text

# Security: Mute logs to prevent token leakage
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI()
bot = Bot(token=os.environ.get("TELEGRAM_BOT_TOKEN"))


def get_icon(cat):
    return {"Groceries": "🟢", "Dining": "🍽️", "Transport": "🚗", "Utilities": "💡", "Shopping": "🛍️", "Other": "📦"}.get(
        cat, "📦")


@app.post("/api/webhook")
async def handle(request: Request):
    update = await request.json()

    # Callback Query (Buttons)
    if "callback_query" in update:
        q = update["callback_query"]
        if q["data"].startswith("confirm:"):
            _, amt, cat, desc, d_str = q["data"].split(":")
            date = datetime.fromisoformat(d_str)
            save_transaction(q["from"]["id"], float(amt), get_category_id(cat), desc, date)
            await bot.edit_message_text(chat_id=q["message"]["chat"]["id"], message_id=q["message"]["message_id"],
                                        text=f"✅ **Saved Successfully!**\n🛒 {desc}\n💰 ₹{amt}\n📂 {get_icon(cat)} {cat}\n📅 {date.strftime('%d-%m-%Y')}",
                                        parse_mode="Markdown")

    # Text Messages
    elif "message" in update and "text" in update["message"]:
        msg, uid, cid = update["message"], update["message"]["from"]["id"], update["message"]["chat"]["id"]
        text = msg["text"].strip()

        if text.startswith("/start"):
            await bot.send_message(cid, "👋 Send expense (e.g., 'Milk 40') or /stats.")
        elif text.startswith("/stats"):
            await bot.send_message(cid, get_user_stats(uid), parse_mode="Markdown")
        else:
            amt, cat, desc, date = parse_expense_text(text)
            if amt <= 0:
                await bot.send_message(cid, "⚠️ Could not parse amount.")
            elif check_duplicate(uid, amt, desc):
                await bot.send_message(cid, "⚠️ Duplicate detected! Please wait 10 seconds.")
            else:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm",
                                                                 callback_data=f"confirm:{amt}:{cat}:{desc}:{date.isoformat()}")],
                                           [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])
                await bot.send_message(cid,
                                       f"❓ Confirm entry?\n🛒 {desc}\n💰 ₹{amt}\n📂 {get_icon(cat)} {cat}\n📅 {date.strftime('%d-%m-%Y')}",
                                       reply_markup=kb, parse_mode="Markdown")
    return {"status": "ok"}