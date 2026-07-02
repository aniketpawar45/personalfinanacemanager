import sys
import os
import dateparser
import logging
from datetime import datetime

# Path Injection to ensure Vercel sees the /core directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from core.database import (
    load_categories_into_cache,
    get_all_categories,
    get_report_data,
    save_transaction
)
from core.engine import transcribe_audio, parse_expense_text
from core.visuals import generate_neon_report_image
from core.models import TransactionRecord

logging.basicConfig(level=logging.INFO)
app = FastAPI()
bot = Bot(token=os.environ.get("TELEGRAM_BOT_TOKEN"))


@app.on_event("startup")
async def startup():
    load_categories_into_cache()
    await bot.set_my_commands([
        BotCommand("report", "Generate report"),
        BotCommand("allstats", "View statistics")
    ])


@app.post("/api/webhook")
async def webhook(req: Request):
    try:
        data = await req.json()
        if "callback_query" in data:
            q = data["callback_query"]
            cid = q["message"]["chat"]["id"]
            uid = str(q["from"]["id"])
            # Data format: cat:cat_id:amt:desc
            c_data = q["data"].split(":")
            save_transaction(TransactionRecord(
                user_id=uid,
                amount=float(c_data[2]),
                category_id=int(c_data[1]),
                description=c_data[3],
                transaction_date=datetime.now()
            ))
            await bot.answer_callback_query(q["id"], text="✅ Transaction Saved!")
            await bot.edit_message_text(chat_id=cid, message_id=q["message"]["message_id"],
                                        text=f"✅ Saved: {c_data[3]} (₹{c_data[2]})")

        elif "message" in data:
            msg = data["message"]
            cid = msg["chat"]["id"]
            uid = str(msg["from"]["id"])

            # ROUTE: REPORT
            if msg.get("text", "").startswith("/report"):
                text = msg["text"]
                is_img = "--image" in text
                q = text.replace("/report", "").replace("--image", "").strip()
                dt = dateparser.parse(q) or datetime.now()
                start, end = (datetime(dt.year, 1, 1), datetime(dt.year, 12, 31)) if q.isdigit() else (
                    dt.replace(hour=0, minute=0), dt.replace(hour=23, minute=59))

                d = get_report_data(uid, start, end)
                tot = sum(x['amount'] for x in d)

                if not is_img:
                    txt = f"🪩 *Report: {q or 'Today'}*\n🟣 *Total:* ₹{tot:,.2f}\n" + "".join(
                        [f"🔹 {x['description']}: ₹{x['amount']}\n" for x in d])
                    await bot.send_message(cid, txt, parse_mode="Markdown")
                else:
                    img = generate_neon_report_image(d, tot, f"REPORT: {q}")
                    await bot.send_photo(cid, photo=img)

            # ROUTE: TRANSACTION
            else:
                text = await transcribe_audio(msg.get("voice", {}).get("file_id"),
                                              os.environ.get("TELEGRAM_BOT_TOKEN")) if "voice" in msg else msg.get(
                    "text")
                if text:
                    amt, desc = await parse_expense_text(text)
                    cats = get_all_categories()
                    kb = InlineKeyboardMarkup(
                        [[InlineKeyboardButton(c['category_name'], callback_data=f"cat:{c['id']}:{amt}:{desc}")] for c
                         in cats])
                    await bot.send_message(cid, f"📝 *{desc}* - ₹{amt}\nSelect Category:", reply_markup=kb,
                                           parse_mode="Markdown")

        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Webhook Error: {e}", exc_info=True)
        return {"status": "ok"}