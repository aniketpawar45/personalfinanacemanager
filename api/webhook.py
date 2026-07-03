import os
import gc
import logging
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

from core.database import (
    save_transaction, get_all_categories, check_duplicate, 
    get_user_stats, get_global_stats, get_last_category, get_user_role,
    load_categories_into_cache
)
from core.engine import parse_expense_text, transcribe_audio
from core.models import TransactionRecord
from core.utils import get_ist_now, FinanceManagerException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_categories_into_cache()
    yield

app = FastAPI(title="Enterprise Personal Finance Manager", lifespan=lifespan)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN environment variable.")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.post("/api/webhook")
async def handle_webhook(request: Request):
    audio_bytes = None
    chat_id = None
    current_step = "Webhook Initialization"
    
    try:
        current_step = "Parsing Telegram Payload"
        update = await request.json()
        
        if "callback_query" in update:
            current_step = "Processing Callback Query"
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
                    record = TransactionRecord(user_id=uid, amount=float(amt), category_id=last_cat_id, description=desc, transaction_date=date)
                    save_transaction(record)
                    cats = get_all_categories()
                    cat_name = next((c['category_name'] for c in cats if c['id'] == last_cat_id), "Other")
                    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"✅ Saved: {desc} - {amt} ({cat_name})")
                else:
                    categories = get_all_categories()
                    buttons = [[InlineKeyboardButton(c['category_name'], callback_data=f"cat:{c['id']}:{amt}:{desc}:{date.isoformat()}")] for c in categories]
                    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Select a category:", reply_markup=InlineKeyboardMarkup(buttons))
            
            elif data == "no_future":
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ Entry cancelled.")
                
            elif data.startswith("cat:"):
                parts = data.split(":", 4)
                cat_id, amt, desc, d_str = int(parts[1]), float(parts[2]), parts[3], parts[4]
                date = datetime.fromisoformat(d_str)
                record = TransactionRecord(user_id=uid, amount=amt, category_id=cat_id, description=desc, transaction_date=date)
                save_transaction(record)
                cats = get_all_categories()
                cat_name = next((c['category_name'] for c in cats if c['id'] == cat_id), "Other")
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"✅ Saved: {desc} - {amt} ({cat_name})")

        elif "message" in update:
            msg = update["message"]
            uid = str(msg["from"]["id"])
            chat_id = msg["chat"]["id"]
            is_admin = (get_user_role(uid) == "admin")
            text = None
            
            if "text" in msg:
                current_step = "Processing Text Message"
                text = msg["text"].strip()
                
            elif "voice" in msg:
                current_step = "Downloading Voice File"
                await bot.send_chat_action(chat_id=chat_id, action='typing')
                file_id = msg["voice"]["file_id"]
                
                async with httpx.AsyncClient() as http_client:
                    file_info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
                    file_info = (await http_client.get(file_info_url)).json()
                    if not file_info.get("ok"):
                        raise FinanceManagerException("Voice Fetching Node", "Could not access Telegram voice file.", "Retry sending the voice note.")
                    file_path = file_info["result"]["file_path"]
                    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                    audio_bytes = (await http_client.get(download_url)).content
                
                current_step = "Transcribing Voice via AI"
                text = await transcribe_audio(audio_bytes)
                await bot.send_message(chat_id, f"🎙️ *Heard:* {text}", parse_mode="Markdown")
            
            else:
                await bot.send_message(chat_id, "⚠️ I only understand text and voice messages.")
                return {"status": "ok"}
                
            if text:
                current_step = "Executing Command/Extraction"
                await bot.send_chat_action(chat_id=chat_id, action='typing')
                if text.startswith("/start"):
                    await bot.send_message(chat_id, "Send an expense (e.g., 'Coffee 40') or a Voice Note!")
                elif text.startswith("/stats"):
                    await bot.send_message(chat_id, get_user_stats(uid), parse_mode="Markdown")
                elif text.startswith("/allstats"):
                    if not is_admin:
                        await bot.send_message(chat_id, "❌ Access Denied: Admin privileges required.")
                    else:
                        await bot.send_message(chat_id, get_global_stats(), parse_mode="Markdown")
                else:
                    amt, desc, date = await parse_expense_text(text)
                    if check_duplicate(uid, amt, desc):
                        await bot.send_message(chat_id, "⚠️ Duplicate prevented!")
                    elif date > get_ist_now():
                        kb = InlineKeyboardMarkup([
                            [InlineKeyboardButton("Yes", callback_data=f"yes_future:{amt}:{desc}:{date.isoformat()}"),
                             InlineKeyboardButton("No", callback_data="no_future")]
                        ])
                        await bot.send_message(chat_id, f"Future date detected: {date.strftime('%d-%m-%Y')}. Are you sure?", reply_markup=kb)
                    else:
                        last_cat_id = get_last_category(desc)
                        if last_cat_id:
                            record = TransactionRecord(user_id=uid, amount=amt, category_id=last_cat_id, description=desc, transaction_date=date)
                            save_transaction(record)
                            cats = get_all_categories()
                            cat_name = next((c['category_name'] for c in cats if c['id'] == last_cat_id), "Other")
                            await bot.send_message(chat_id, f"✅ Auto-Saved: {desc} - {amt} ({cat_name})")
                        else:
                            categories = get_all_categories()
                            buttons = [[InlineKeyboardButton(c['category_name'], callback_data=f"cat:{c['id']}:{amt}:{desc}:{date.isoformat()}")] for c in categories]
                            await bot.send_message(chat_id, "Select a category:", reply_markup=InlineKeyboardMarkup(buttons))

    except FinanceManagerException as fme:
        error_msg = f"❌ **System Failure at [{fme.step}]**\n⚠️ {fme.message}\n🔧 **Action:** {fme.action}"
        if chat_id:
            await bot.send_message(chat_id=chat_id, text=error_msg, parse_mode="Markdown")
            
    except Exception as e:
        error_msg = f"❌ **Unexpected Critical Failure at [{current_step}]**\n⚠️ Internal System Error\n🔧 **Action:** SUPPORT TEAM ACTION REQUIRED. Forward to admin."
        logger.error(f"Critical failure at {current_step}: {str(e)}", exc_info=True)
        if chat_id:
            await bot.send_message(chat_id=chat_id, text=error_msg, parse_mode="Markdown")

    finally:
        current_step = "Memory Deallocation"
        if audio_bytes is not None:
            del audio_bytes
            audio_bytes = None
        gc.collect()
        
        return {"status": "ok"}
