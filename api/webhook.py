import os, logging
from fastapi import FastAPI, Request
from telegram import Bot
from core.database import save_transaction, get_category_id, get_user_stats
from core.engine import parse_expense_text

# Mute httpx logs to prevent token leakage
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI()
bot = Bot(token=os.environ.get("TELEGRAM_BOT_TOKEN"))


@app.post("/api/webhook")
async def handle(request: Request):
    update = await request.json()
    if "message" in update and "text" in update["message"]:
        msg = update["message"]
        text = msg["text"].strip()
        uid = msg["from"]["id"]
        cid = msg["chat"]["id"]

        if text.startswith("/start"):
            await bot.send_message(cid, "👋 Type expense (e.g., 'Milk 40') or /stats.")
        elif text.startswith("/stats"):
            await bot.send_message(cid, get_user_stats(uid), parse_mode="Markdown")
        else:
            amt, cat, desc = parse_expense_text(text)
            if amt > 0:
                save_transaction(uid, amt, get_category_id(cat), desc)
                await bot.send_message(cid, f"✅ Saved: ₹{amt} ({cat})")
            else:
                await bot.send_message(cid, "⚠️ Could not parse amount.")
    return {"status": "ok"}