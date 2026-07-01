import os, logging
from fastapi import FastAPI, Request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from core.database import save_transaction, get_all_categories, check_duplicate, get_user_stats
from core.engine import parse_expense_text

# Security: Mute logs to prevent token leakage
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI()
bot = Bot(token=os.environ.get("TELEGRAM_BOT_TOKEN"))

def get_icon(cat):
    return {"Groceries": "🟢", "Dining": "🍽️", "Transport": "🚗", "Utilities": "💡", "Shopping": "🛍️", "Other": "📦"}.get(cat, "📦")

@app.post("/api/webhook")
async def handle(request: Request):
    update = await request.json()
    
    # CALLBACK: User selected a category
    if "callback_query" in update:
        q = update["callback_query"]
        if q["data"].startswith("cat:"):
            # FIX: Use maxsplit=4 to keep the date string intact even if it has colons
            parts = q["data"].split(":", 4)
            cat_id, amt, desc, d_str = parts[1], parts[2], parts[3], parts[4]
            
            date = datetime.fromisoformat(d_str)
            cat_name = next((c['category_name'] for c in get_all_categories() if str(c['id']) == cat_id), "Other")
            
            save_transaction(q["from"]["id"], float(amt), int(cat_id), desc, date)
            
            await bot.edit_message_text(
                chat_id=q["message"]["chat"]["id"], 
                message_id=q["message"]["message_id"], 
                text=f"✅ **Saved Successfully!**\n🛒 {desc}\n💰 ₹{amt}\n📂 {get_icon(cat_name)} {cat_name}\n📅 {date.strftime('%d-%m-%Y')}", 
                parse_mode="Markdown"
            )

    # TEXT: User sent an item
    elif "message" in update and "text" in update["message"]:
        msg, uid, cid = update["message"], update["message"]["from"]["id"], update["message"]["chat"]["id"]
        text = msg["text"].strip()
        
        if text.startswith("/start"):
            await bot.send_message(cid, "👋 Send expense (e.g., 'Milk 40') or /stats.")
        elif text.startswith("/stats"):
            await bot.send_message(cid, get_user_stats(uid), parse_mode="Markdown")
        else:
            amt, desc, date = parse_expense_text(text)
            if amt <= 0:
                await bot.send_message(cid, "⚠️ Could not parse amount.")
            elif check_duplicate(uid, amt, desc):
                await bot.send_message(cid, "⚠️ Duplicate detected! Please wait 10 seconds.")
            else:
                categories = get_all_categories()
                buttons = [[InlineKeyboardButton(c['category_name'], callback_data=f"cat:{c['id']}:{amt}:{desc}:{date.isoformat()}")] for c in categories]
                kb = InlineKeyboardMarkup(buttons)
                await bot.send_message(cid, f"❓ Please select category for **{desc}** (₹{amt}):", reply_markup=kb, parse_mode="Markdown")
    return {"status": "ok"}
