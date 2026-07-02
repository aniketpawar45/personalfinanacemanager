import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

from core.database import (
    save_transaction, get_all_categories, check_duplicate,
    get_user_stats, get_global_stats, get_last_category, get_user_role,
    load_categories_into_cache
)
from core.engine import parse_expense_text
from core.models import TransactionRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_categories_into_cache()
    yield


app = FastAPI(title="Enterprise Personal Finance Manager", lifespan=lifespan)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_SECRET_TOKEN = os.environ.get("TELEGRAM_SECRET_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN environment variable.")

bot = Bot(token=TELEGRAM_BOT_TOKEN)


def verify_telegram_token(x_telegram_bot_api_secret_token: str = Header(None)):
    if not TELEGRAM_SECRET_TOKEN:
        logger.warning("TELEGRAM_SECRET_TOKEN is not configured in environment.")
        return
    if x_telegram_bot_api_secret_token != TELEGRAM_SECRET_TOKEN:
        logger.error("Unauthorized webhook invocation attempt blocked.")
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/api/webhook", dependencies=[Depends(verify_telegram_token)])
async def handle_webhook(request: Request):
    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    chat_id = None

    try:
        if "callback_query" in update:
            q = update["callback_query"]
            chat_id = q["message"]["chat"]["id"]
            message_id = q["message"]["message_id"]
            uid = str(q["from"]["id"])
            data = q["data"]

            if data.startswith("yes_future:"):
                _, amt, desc, d_str = data.split(":", 3)
                date = datetime.fromisoformat(d_str)
                last_cat_id = get_last_category(desc)

                if last_cat_id:
                    record = TransactionRecord(user_id=uid, amount=float(amt), category_id=last_cat_id,
                                               description=desc, transaction_date=date)
                    if save_transaction(record):
                        cats = get_all_categories()
                        cat_name = next((c['category_name'] for c in cats if c['id'] == last_cat_id), "Other")
                        await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                                    text=f"✅ **Saved Successfully!**\n📝 {desc}\n💰 {amt}\n📁 {cat_name} 📅 {date.strftime('%d-%m-%Y')}",
                                                    parse_mode="Markdown")
                    else:
                        await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                                    text="⚠️ **I'm sorry, I couldn't save that to the database right now.** Please try again.",
                                                    parse_mode="Markdown")
                else:
                    categories = get_all_categories()
                    buttons = [[InlineKeyboardButton(c['category_name'],
                                                     callback_data=f"cat:{c['id']}:{amt}:{desc}:{date.isoformat()}")]
                               for c in categories]
                    await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                                text=f"🆕 **New item detected!**\n\n📝 **Item:** {desc}\n💰 **Amount:** {amt}\n\nPlease select a category:",
                                                reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

            elif data == "no_future":
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="🚫 Entry cancelled.")

            elif data.startswith("cat:"):
                parts = data.split(":", 4)
                cat_id, amt, desc, d_str = int(parts[1]), float(parts[2]), parts[3], parts[4]
                date = datetime.fromisoformat(d_str)

                record = TransactionRecord(user_id=uid, amount=amt, category_id=cat_id, description=desc,
                                           transaction_date=date)
                if save_transaction(record):
                    cats = get_all_categories()
                    cat_name = next((c['category_name'] for c in cats if c['id'] == cat_id), "Other")
                    await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                                text=f"✅ **Saved Successfully!**\n📝 {desc}\n💰 {amt}\n📁 {cat_name} 📅 {date.strftime('%d-%m-%Y')}",
                                                parse_mode="Markdown")
                else:
                    await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                                text="⚠️ **I'm sorry, I couldn't save that to the database right now.** Please try again.",
                                                parse_mode="Markdown")

        elif "message" in update and "text" in update["message"]:
            msg = update["message"]
            uid = str(msg["from"]["id"])
            chat_id = msg["chat"]["id"]
            text = msg["text"].strip()

            await bot.send_chat_action(chat_id=chat_id, action='typing')

            user_role = get_user_role(uid)
            is_admin = (user_role == "admin")

            if text.startswith("/start"):
                await bot.send_message(chat_id, "👋 Send expense (e.g., 'Coffee 40'). \nAdmins can use /allstats.")

            elif text.startswith("/stats"):
                stats_msg = get_user_stats(uid)
                await bot.send_message(chat_id, stats_msg, parse_mode="Markdown")

            elif text.startswith("/allstats"):
                if not is_admin:
                    await bot.send_message(chat_id,
                                           "⛔ **Access Denied:** I'm sorry, but you need admin privileges to view the global ledger.")
                else:
                    global_stats_msg = get_global_stats()
                    await bot.send_message(chat_id, global_stats_msg, parse_mode="Markdown")

            else:
                try:
                    amt, desc, date = await parse_expense_text(text)

                    if check_duplicate(uid, amt, desc):
                        await bot.send_message(chat_id,
                                               "⚠️ **Duplicate prevented!** It looks like you just saved this exact transaction.")
                    elif date > datetime.now():
                        kb = InlineKeyboardMarkup([
                            [InlineKeyboardButton("Yes", callback_data=f"yes_future:{amt}:{desc}:{date.isoformat()}"),
                             InlineKeyboardButton("No", callback_data="no_future")]
                        ])
                        await bot.send_message(chat_id,
                                               f"⏳ **Future date detected!**\nYou entered {date.strftime('%d-%m-%Y')}.\nAre you sure?",
                                               reply_markup=kb, parse_mode="Markdown")
                    else:
                        last_cat_id = get_last_category(desc)
                        if last_cat_id:
                            record = TransactionRecord(user_id=uid, amount=amt, category_id=last_cat_id,
                                                       description=desc, transaction_date=date)
                            if save_transaction(record):
                                cats = get_all_categories()
                                cat_name = next((c['category_name'] for c in cats if c['id'] == last_cat_id), "Other")
                                await bot.send_message(chat_id,
                                                       f"⚡ **Auto-Saved!**\n📝 {desc}\n💰 {amt}\n📁 {cat_name} 📅 {date.strftime('%d-%m-%Y')}",
                                                       parse_mode="Markdown")
                            else:
                                await bot.send_message(chat_id,
                                                       "⚠️ **I'm sorry, I encountered an issue saving your transaction.** Please try again.",
                                                       parse_mode="Markdown")
                        else:
                            categories = get_all_categories()
                            buttons = [[InlineKeyboardButton(c['category_name'],
                                                             callback_data=f"cat:{c['id']}:{amt}:{desc}:{date.isoformat()}")]
                                       for c in categories]
                            await bot.send_message(chat_id,
                                                   f"🆕 **New item detected!**\n\n📝 **Item:** {desc}\n💰 **Amount:** {amt}\n\nPlease select a category:",
                                                   reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

                except ValueError as ve:
                    await bot.send_message(chat_id, f"⚠️ {str(ve)}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Global webhook exception: {str(e)}", exc_info=True)
        if chat_id:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text="🛠️ **Oops! I ran into a tiny technical hiccup on my end while processing that.** Could you please try again?",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        return {"status": "ok"}