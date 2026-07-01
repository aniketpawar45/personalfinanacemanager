import os
from fastapi import FastAPI, Request
from telegram import Bot
from core.database import save_transaction, get_category_id
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
        
        # Check if the update is a standard text message
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_id = update["message"]["from"]["id"]
            user_text = update["message"]["text"]
            
            # 1. Parse text via Groq LLM
            amount, category_name, description = parse_expense_text(user_text)
            
            if amount > 0:
                # 2. Map category name to Supabase ID
                category_id = get_category_id(category_name)
                
                # 3. Save to Supabase
                success = save_transaction(user_id, amount, category_id, description)
                
                # 4. Notify User
                if success:
                    msg = f"✅ Saved: ₹{amount} for {category_name}\n📝 {description}"
                else:
                    msg = "❌ Failed to save transaction to database."
                
                await bot.send_message(chat_id=chat_id, text=msg)
            else:
                await bot.send_message(chat_id=chat_id, text="⚠️ Could not understand the amount. Please try again (e.g., 'Milk 40').")
                
        return {"status": "ok"}
        
    except Exception as e:
        print(f"Webhook Error: {e}")
        return {"status": "error"}
