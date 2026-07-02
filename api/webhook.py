import os, dateparser
from fastapi import FastAPI, Request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from core.database import *
from core.engine import *
from core.visuals import generate_neon_report_image

app = FastAPI()
bot = Bot(token=os.environ.get("TELEGRAM_BOT_TOKEN"))


@app.post("/api/webhook")
async def webhook(req: Request):
    data = await req.json()
    if "message" in data:
        msg = data["message"]
        cid, uid = msg["chat"]["id"], str(msg["from"]["id"])

        # 1. REPORT GENERATION ROUTE
        if "text" in msg and msg["text"].startswith("/report"):
            cmd = msg["text"]
            is_img = "--image" in cmd
            q = cmd.replace("/report", "").replace("--image", "").strip()
            # Date logic
            dt = dateparser.parse(q) or datetime.now()
            start, end = (datetime(dt.year, 1, 1), datetime(dt.year, 12, 31)) if q.isdigit() else (
                dt.replace(hour=0, minute=0), dt.replace(hour=23, minute=59))

            rep_data = get_report_data(uid, start, end)
            total = sum(d['amount'] for d in rep_data)

            if not is_img:
                await bot.send_message(cid, f"🪩 *Report {q or 'Today'}*\n🟣 *Total:* ₹{total:,.2f}\n" + "".join(
                    [f"🔹 {d['description']}: ₹{d['amount']}\n" for d in rep_data]), parse_mode="Markdown")
            else:
                l = await bot.send_message(cid, "✨ *0%* `[░░░░░░░░░░]`", parse_mode="Markdown")
                await bot.edit_message_text(chat_id=cid, message_id=l.message_id, text="✨ *50%* `[█████░░░░░]`",
                                            parse_mode="Markdown")
                img = generate_neon_report_image(rep_data, total, f"REPORT: {q}")
                await bot.edit_message_text(chat_id=cid, message_id=l.message_id, text="✨ *100%* `[██████████]`",
                                            parse_mode="Markdown")
                await bot.send_photo(cid, photo=img)

        # 2. TRANSACTION ROUTE (Text or Voice)
        else:
            text = await transcribe_audio(msg["voice"]["file_id"],
                                          os.environ.get("TELEGRAM_BOT_TOKEN")) if "voice" in msg else msg.get("text")
            if text:
                amt, desc, date = await parse_expense_text(text)
                cats = get_all_categories()
                kb = InlineKeyboardMarkup([[InlineKeyboardButton(c['category_name'],
                                                                 callback_data=f"cat:{c['id']}:{amt}:{desc}:{date.isoformat()}")]
                                           for c in cats])
                await bot.send_message(cid, f"📝 *{desc}* - ₹{amt}\nSelect Category:", reply_markup=kb,
                                       parse_mode="Markdown")
    return {"status": "ok"}