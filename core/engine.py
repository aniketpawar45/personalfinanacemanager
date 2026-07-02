import os
import json
import logging
import dateparser
import re
from datetime import datetime
from groq import AsyncGroq
from core.models import ExpenseExtraction

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY environment variable.")

client = AsyncGroq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """
You are a highly precise financial extraction tool. 
Extract the 'amount' (numeric float), 'item_name' (string), and 'date_str' (string, if mentioned).
If no valid amount is found, return 0.0.
If no valid item is found, return "".
Return strictly valid JSON matching the exact schema requested. 
Do NOT include any conversational text.
"""

async def parse_expense_text(text: str) -> tuple[float, str, datetime]:
    # NLP Pre-Processing: Intelligently separate squished letters and numbers
    processed_text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    processed_text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', processed_text)
    
    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": processed_text}
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        raw_json = response.choices[0].message.content
        extraction = ExpenseExtraction.model_validate_json(raw_json)
        
        amt = float(extraction.amount) if extraction.amount is not None else 0.0
        item = str(extraction.item_name).title().strip() if extraction.item_name else ""
        
        # 🚀 EXPLICIT VALIDATION: No more silent failures
        if amt <= 0:
            raise ValueError(f"I couldn't find a valid price in '{text}'. Please include an amount (e.g., 'Milk 40').")
        if not item or item == str(amt):
            raise ValueError(f"I couldn't identify the item name in '{text}'. Please tell me what the expense was for.")
            
        date_str = extraction.date_str or processed_text
        parsed_date = dateparser.parse(
            date_str,
            settings={'PREFER_DATES_FROM': 'past', 'RELATIVE_BASE': datetime.now()}
        ) or datetime.now()
        
        if parsed_date.year != datetime.now().year:
            parsed_date = parsed_date.replace(year=datetime.now().year)
            
        return amt, item, parsed_date

    except ValueError as ve:
        # Pass explicit user-facing errors straight up to the webhook
        raise ve
    except Exception as e:
        logger.warning(f"AI parsing failed completely: {str(e)}")
        
        # Hardened Regex Fallback with STRICT validation
        match = re.search(r'\d+(\.\d+)?', processed_text)
        if not match:
             raise ValueError(f"I couldn't understand the format of '{text}'. Please use a standard format like 'Uber 200'.")
             
        amt = float(match.group())
        if amt <= 0:
             raise ValueError(f"The amount must be greater than zero. You entered: '{text}'.")
             
        item_name = re.sub(r'\d+(\.\d+)?', '', processed_text).strip().title()
        if not item_name:
             raise ValueError(f"I found the amount ({amt}), but I couldn't find the item name in '{text}'.")
             
        return amt, item_name, datetime.now()