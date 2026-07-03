import os
import logging
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from telegram import Bot
from datetime import datetime
from core.database import (
    save_transaction, get_all_categories, check_duplicate,
    get_user_stats, get_global_stats, get_last_category, get_user_role
)
from core.engine import parse_expense_text
from core.models import TransactionRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise Personal Finance Manager")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.post("/api/webhook")
async def handle_webhook(request: Request):
    try:
        update = await request.json()
        if "message" in update and "text" in update["message"]:
            msg = update["message"]
            uid = str(msg["from"]["id"])
            cid = msg["chat"]["id"]
            text = msg["text"].strip()

            if text.startswith("/start"):
                await bot.send_message(cid, "Send expense (e.g., 'Coffee 40').")
            elif text.startswith("/stats"):
                await bot.send_message(cid, get_user_stats(uid), parse_mode="Markdown")
            else:
                amt, desc, date = await parse_expense_text(text)
                if amt <= 0:
                    await bot.send_message(cid, "Could not parse a valid amount.")
                elif check_duplicate(uid, amt, desc):
                    await bot.send_message(cid, "Duplicate entry prevented.")
                else:
                    last_cat_id = get_last_category(desc)
                    record = TransactionRecord(
                        user_id=uid, 
                        amount=amt, 
                        category_id=last_cat_id or 0, 
                        description=desc, 
                        transaction_date=date
                    )
                    save_transaction(record)
                    await bot.send_message(cid, f"✅ *Saved:* {desc} - ₹{amt:,.2f}", parse_mode="Markdown")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {"status": "error"}