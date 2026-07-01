import os
from fastapi import FastAPI, Request
from telegram import Bot
# We added get_user_stats to the import below:
from core.database import save_transaction, get_category_id, get_user_stats
from core.engine import parse_expense_text

app = FastAPI()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None


@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    """Receives updates from Telegram and processes them."""
    if not bot:
        return {"status": "error", "message": "Bot token not configured"}

    try:
        update = await request.json()

        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_id = update["message"]["from"]["id"]
            user_text = update["message"]["text"].strip()

            # --- 🚀 COMMAND ROUTING ---
            # 1. Handle /start command
            if user_text.startswith("/start"):
                welcome = "👋 Welcome to Finance Manager!\nJust type what you spent (e.g., 'Spent 500 on groceries') and I'll track it. Type /stats to see your spending."
                await bot.send_message(chat_id=chat_id, text=welcome)
                return {"status": "ok"}

            # 2. Handle /stats command
            if user_text.startswith("/stats"):
                stats_msg = get_user_stats(user_id)
                # We use parse_mode="Markdown" to make the text bold and pretty
                await bot.send_message(chat_id=chat_id, text=stats_msg, parse_mode="Markdown")
                return {"status": "ok"}
            # ---------------------------

            # --- 🧠 NATURAL LANGUAGE PROCESSING ---
            # If it's not a command, treat it as a new expense
            amount, category_name, description = parse_expense_text(user_text)

            if amount > 0:
                category_id = get_category_id(category_name)
                success = save_transaction(user_id, amount, category_id, description)

                if success:
                    msg = f"✅ Saved: ₹{amount} for {category_name}\n📝 {description}"
                else:
                    msg = "❌ Failed to save transaction to database."

                await bot.send_message(chat_id=chat_id, text=msg)
            else:
                await bot.send_message(chat_id=chat_id,
                                       text="⚠️ Could not understand the amount. Please try again (e.g., 'Milk 40').")

        return {"status": "ok"}

    except Exception as e:
        print(f"Webhook Error: {e}")
        return {"status": "error"}