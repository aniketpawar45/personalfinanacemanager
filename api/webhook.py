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
    load_categories_into_cache, supabase
)
from core.engine import parse_expense_text, transcribe_audio
from core.models import TransactionRecord
from core.utils import get_ist_now, FinanceManagerException, IST_TZ
from api.reports import handle_report_command, handle_csv_export
from api.stats import handle_statistics_command
from api.chart import handle_chart_command

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

def extract_remarks(q: dict) -> str:
    try:
        raw_text = q["message"]["reply_to_message"]["text"]
        if raw_text.startswith("🎙️ Heard: "):
            return raw_text.replace("🎙️ Heard: ", "", 1).strip()
        return raw_text.strip()
    except KeyError:
        return "Manual override save"

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
            
            if data.startswith("csv:"):
                _, start_ts, end_ts = data.split(":")
                await handle_csv_export(bot, chat_id, uid, float(start_ts), float(end_ts))
                await bot.answer_callback_query(q["id"], "Generating CSV...")
            
            elif data.startswith("confirm_unk:"):
                _, amt, d_ts = data.split(":")
                date = datetime.fromtimestamp(float(d_ts), tz=IST_TZ)
                categories = get_all_categories()
                buttons = [[InlineKeyboardButton(c['category_name'], callback_data=f"cat:{c['id']}:{amt}:Unk:{date.timestamp()}")] for c in categories]
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Select a category for this unknown item:", reply_markup=InlineKeyboardMarkup(buttons))
            
            elif data == "cancel_unk":
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ Entry cancelled. Please resend with the item name.")
                
            elif data.startswith("yes_future:"):
                _, amt, desc, d_str = data.split(":", 3)
                date = datetime.fromisoformat(d_str)
                remarks = extract_remarks(q)
                last_cat_id = get_last_category(desc)
                
                if last_cat_id:
                    record = TransactionRecord(user_id=uid, amount=float(amt), category_id=last_cat_id, description=desc, transaction_date=date, remarks=remarks)
                    save_transaction(record)
                    cats = get_all_categories()
                    cat_name = next((c['category_name'] for c in cats if c['id'] == last_cat_id), "Other")
                    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"✅ Saved: {desc} - {amt} ({cat_name})")
                else:
                    categories = get_all_categories()
                    buttons = [[InlineKeyboardButton(c['category_name'], callback_data=f"cat:{c['id']}:{amt}:{desc[:10]}:{date.timestamp()}")] for c in categories]
                    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"Select a category for {desc}:", reply_markup=InlineKeyboardMarkup(buttons))
            
            elif data == "no_future":
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ Entry cancelled.")
                
            elif data.startswith("cat:"):
                parts = data.split(":", 4)
                cat_id, amt, desc, d_ts = int(parts[1]), float(parts[2]), parts[3], float(parts[4])
                date = datetime.fromtimestamp(d_ts, tz=IST_TZ)
                remarks = extract_remarks(q)
                
                record = TransactionRecord(user_id=uid, amount=amt, category_id=cat_id, description=desc, transaction_date=date, remarks=remarks)
                save_transaction(record)
                cats = get_all_categories()
                cat_name = next((c['category_name'] for c in cats if c['id'] == cat_id), "Other")
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"✅ Saved: {desc} - {amt} ({cat_name})\n📝 *Remarks:* {remarks[:50]}...", parse_mode="Markdown")

        elif "message" in update:
            msg = update["message"]
            msg_id = msg["message_id"]
            active_msg_id = msg_id
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
                heard_msg = await bot.send_message(chat_id, f"🎙️ Heard: {text}", reply_to_message_id=msg_id)
                active_msg_id = heard_msg.message_id
            
            else:
                await bot.send_message(chat_id, "⚠️ I only understand text and voice messages.")
                return {"status": "ok"}
                
            if text:
                current_step = "Executing Command/Extraction"
                await bot.send_chat_action(chat_id=chat_id, action='typing')
                
                # ENTERPRISE FIREWALL: Strict Command Routing
                if text.startswith("/start"):
                    await bot.send_message(chat_id, "Send expenses (e.g., 'Coffee 40, Bread 30') or a Voice Note!")
                elif text.startswith("/stats"):
                    await bot.send_message(chat_id, get_user_stats(uid), parse_mode="Markdown")
                elif text.startswith("/subscribe"):
                    try:
                        parts = text.split(maxsplit=2)
                        if len(parts) < 3:
                            raise ValueError("Format: /subscribe <daily|weekly|monthly|yearly> <email1,email2>")
                        freq, emails = parts[1].lower(), parts[2]
                        if freq not in ['daily', 'weekly', 'monthly', 'yearly']:
                            raise ValueError("Frequency must be daily, weekly, monthly, or yearly.")

                        # Corrected namespace usage
                        sched_data = {
                            "telegram_id": uid,
                            "frequency": freq,
                            "emails": emails,
                            "scheduled_hour": 9
                        }
                        supabase.table("report_schedules").insert(sched_data).execute()
                        await bot.send_message(chat_id,
                                               f"✅ Subscribed successfully!\n📅 Frequency: {freq.capitalize()}\n📧 To: {emails}\n⏰ Time: 09:00 AM IST")
                    except Exception as e:
                        logger.error(f"Subscription Error: {str(e)}")
                        await bot.send_message(chat_id, f"❌ Database Insert Failed: {str(e)}")
                elif text.startswith("/chart"):
                    await handle_chart_command(bot, chat_id, text, uid)
                elif text.startswith("/statistics"):
                    await handle_statistics_command(bot, chat_id, text, uid)
                elif text.startswith("/report"):
                    await handle_report_command(bot, chat_id, text, uid)
                elif text.startswith("/allstats"):
                    if not is_admin:
                        await bot.send_message(chat_id, "❌ Access Denied: Admin privileges required.")
                    else:
                        await bot.send_message(chat_id, get_global_stats(), parse_mode="Markdown")
                elif text.startswith("/"):
                    await bot.send_message(chat_id, "⚠️ Unknown command. Use /report to see your ledger.")
                
                # AI EXTRACTION: Only executes if no '/' command was detected
                else:
                    categories = get_all_categories()
                    valid_cat_names = [c['category_name'] for c in categories]
                    extracted_items = await parse_expense_text(text, valid_cat_names)
                    
                    for amt, desc, date, ai_category in extracted_items:
                        try:
                            if amt <= 0:
                                raise FinanceManagerException("AI Extraction Node", f"No valid price found for '{desc}'.", "Include an amount.")
                                
                            if desc == "Unknown Item":
                                kb = InlineKeyboardMarkup([
                                    [InlineKeyboardButton("Yes, save it", callback_data=f"confirm_unk:{amt}:{date.timestamp()}")],
                                    [InlineKeyboardButton("No, cancel", callback_data="cancel_unk")]
                                ])
                                await bot.send_message(chat_id, f"⚠️ I found an amount (₹{amt}) but no item name.\nDo you want to save this anyway?", reply_markup=kb, reply_to_message_id=active_msg_id)
                                
                            elif check_duplicate(uid, amt, desc):
                                await bot.send_message(chat_id, f"⚠️ Duplicate prevented for: {desc} - ₹{amt}", reply_to_message_id=active_msg_id)
                                
                            elif date > get_ist_now():
                                kb = InlineKeyboardMarkup([
                                    [InlineKeyboardButton("Yes", callback_data=f"yes_future:{amt}:{desc[:10]}:{date.isoformat()}"),
                                     InlineKeyboardButton("No", callback_data="no_future")]
                                ])
                                await bot.send_message(chat_id, f"Future date detected for '{desc}': {date.strftime('%d-%m-%Y')}. Are you sure?", reply_markup=kb, reply_to_message_id=active_msg_id)
                                
                            else:
                                cat_id_to_use = None
                                cat_name_to_display = "Other"
                                
                                last_cat_id = get_last_category(desc)
                                if last_cat_id:
                                    cat_id_to_use = last_cat_id
                                    cat_name_to_display = next((c['category_name'] for c in categories if c['id'] == last_cat_id), "Other")
                                elif ai_category:
                                    for c in categories:
                                        if c['category_name'].lower() == ai_category.lower():
                                            cat_id_to_use = c['id']
                                            cat_name_to_display = c['category_name']
                                            break
                                            
                                if cat_id_to_use:
                                    record = TransactionRecord(user_id=uid, amount=amt, category_id=cat_id_to_use, description=desc, transaction_date=date, remarks=text)
                                    save_transaction(record)
                                    await bot.send_message(chat_id, f"✅ Auto-Saved: {desc} - ₹{amt} ({cat_name_to_display})", reply_to_message_id=active_msg_id)
                                else:
                                    buttons = [[InlineKeyboardButton(c['category_name'], callback_data=f"cat:{c['id']}:{amt}:{desc[:10]}:{date.timestamp()}")] for c in categories]
                                    await bot.send_message(chat_id, f"🤖 Unsure of category.\nSelect a category for '{desc}' (₹{amt}):", reply_markup=InlineKeyboardMarkup(buttons), reply_to_message_id=active_msg_id)
                                    
                        except FinanceManagerException as fme:
                            error_msg = f"❌ **Error processing '{desc}'**\n⚠️ {fme.message}\n🔧 **Action:** {fme.action}"
                            await bot.send_message(chat_id=chat_id, text=error_msg, parse_mode="Markdown", reply_to_message_id=active_msg_id)

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
