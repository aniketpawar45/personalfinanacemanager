import io
import csv
import logging
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from core.analytics import parse_date_range, get_report_data
from core.utils import IST_TZ

logger = logging.getLogger(__name__)

async def handle_report_command(bot: Bot, chat_id: int, command: str, uid: str):
    """Decoupled entry point for all reporting requests."""
    try:
        parts = command.split(" ", 1)
        query = parts[1] if len(parts) > 1 else "today"
        
        start, end, label = parse_date_range(query)
        data = get_report_data(uid, start, end)
        
        if not data:
            await bot.send_message(chat_id, f"📭 No expenses found for *{label}*.", parse_mode="Markdown")
            return
            
        total = sum(float(item['amount']) for item in data)
        
        # Build Enterprise Visual Report
        msg = f"📊 *Financial Report: {label}*\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"`{'Item':<13} | {'Amt':<6} | {'Cat'}`\n"
        msg += f"──────────────────────\n"
        
        for item in data:
            amt = float(item['amount'])
            desc = item['description'][:13]
            cat = item['categories']['category_name'] if item.get('categories') else "Other"
            
            # Anomaly/Alert Detection: High spend relative to period total
            alert = "🔴" if amt > (total * 0.3) and total > 0 else "🔹"
            
            msg += f"`{desc:<13} | {amt:<6.0f} |` {alert} {cat}\n"
            
        msg += f"━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💰 *Total Spent: ₹{total:,.2f}*\n\n"
        msg += f"💡 _Tip: 🔴 indicates high-impact spending (>30% of period total)._"
        
        # Stateless export buttons passing timestamps
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download CSV", callback_data=f"csv:{start.timestamp()}:{end.timestamp()}")]
        ])
        
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", reply_markup=kb)
        
    except ValueError as ve:
        await bot.send_message(chat_id, f"⚠️ {str(ve)}")
    except Exception as e:
        logger.error(f"Reporting Error: {str(e)}", exc_info=True)
        await bot.send_message(chat_id, "❌ An error occurred while generating the report.")

async def handle_csv_export(bot: Bot, chat_id: int, uid: str, start_ts: float, end_ts: float):
    """Generates and transmits a CSV using Zero-Persistence memory buffers."""
    try:
        start = datetime.fromtimestamp(start_ts, tz=IST_TZ)
        end = datetime.fromtimestamp(end_ts, tz=IST_TZ)
        
        data = get_report_data(uid, start, end)
        if not data:
            await bot.send_message(chat_id, "⚠️ No data available for export.")
            return
            
        # ZERO-PERSISTENCE: Memory Buffer Creation
        mem_file = io.StringIO()
        writer = csv.writer(mem_file)
        writer.writerow(["Date", "Item Description", "Category", "Amount (INR)"])
        
        for item in data:
            cat = item['categories']['category_name'] if item.get('categories') else "Other"
            dt_obj = datetime.fromisoformat(item['transaction_date'])
            writer.writerow([dt_obj.strftime("%Y-%m-%d %H:%M"), item['description'], cat, item['amount']])
            
        # Move to beginning of buffer and encode to bytes for Telegram API
        mem_file.seek(0)
        byte_stream = io.BytesIO(mem_file.getvalue().encode('utf-8'))
        byte_stream.name = f"Expense_Report_{start.strftime('%Y%m%d')}.csv"
        
        await bot.send_document(chat_id=chat_id, document=byte_stream, caption="📁 Here is your requested report.")
        
    except Exception as e:
        logger.error(f"CSV Generation Error: {str(e)}", exc_info=True)
        await bot.send_message(chat_id, "❌ Failed to generate the export file.")
    finally:
        # STRICT MEMORY DEALLOCATION
        if 'mem_file' in locals():
            mem_file.close()
        if 'byte_stream' in locals():
            byte_stream.close()

async def handle_subscribe_command(bot, chat_id, text, uid):
    """Handles the /subscribe command to save email reports to the database."""
    parts = text.split(" ")
    if len(parts) < 2 or "@" not in parts[1]:
        await bot.send_message(
            chat_id, 
            "❌ *Invalid Format*\n🔧 *Action:* Use `/subscribe your_email@gmail.com`"
        )
        return
        
    email = parts[1].strip().lower()
    
    try:
        from core.supabase_client import supabase
        # Upsert or insert the subscription state for this user id
        data, count = supabase.table("report_schedules").upsert({
            "user_id": uid,
            "email": email,
            "is_active": True
        }, on_conflict="user_id").execute()
        
        await bot.send_message(
            chat_id, 
            f"✅ *Subscription Active!*\n📬 Daily financial summaries will be routed to `{email}` automatically."
        )
    except Exception as e:
        await bot.send_message(chat_id, f"❌ Failed to register subscription: {str(e)}")
