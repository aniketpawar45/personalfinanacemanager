import os
import re
import logging
import dateparser
from datetime import datetime
from groq import AsyncGroq
from core.models import ExpenseBatch
from core.utils import get_ist_now, FinanceManagerException, IST_TZ

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY environment variable.")

client = AsyncGroq(api_key=GROQ_API_KEY)

async def transcribe_audio(audio_bytes: bytes) -> str:
    try:
        file_tuple = ("voice_message.ogg", audio_bytes, "audio/ogg")
        response = await client.audio.transcriptions.create(
            file=file_tuple,
            model="whisper-large-v3"
        )
        return response.text.strip()
    except Exception as e:
        raise FinanceManagerException(
            step="Audio Transcription Node",
            message=f"Groq API transcription failed: {str(e)}",
            action="USER ACTION REQUIRED: Please try typing out your expense instead."
        )

async def parse_expense_text(text: str, valid_categories: list) -> list[tuple[float, str, datetime, str]]:
    processed_text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    processed_text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', processed_text)
    
    cat_list_str = ", ".join(valid_categories)
    
    # ENTERPRISE PROMPT: Injecting Dynamic Database Context
    system_prompt = f"""You are a highly precise financial extraction tool. Extract a list of expenses from the input. 
Return strict JSON with a single key 'items' containing an array of objects. 
Each object must have 'amount' (number), 'item_name' (string), and 'date_str' (string).
You MUST also include a 'category_name' (string). Choose the MOST LOGICAL category EXACTLY as it appears in this list: [{cat_list_str}]. 
If you are NOT highly confident, return an empty string for category_name. If no valid amount, return 0.0."""
    
    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": processed_text}
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        raw_json = response.choices[0].message.content
        batch = ExpenseBatch.model_validate_json(raw_json)
        
        results = []
        for extraction in batch.items:
            amt = float(extraction.amount) if extraction.amount is not None else 0.0
            item = str(extraction.item_name).title().strip() if extraction.item_name else ""
            ai_category = str(extraction.category_name).strip() if extraction.category_name else ""
            
            if amt <= 0:
                match = re.search(r'\d+(\.\d+)?', item)
                if match:
                    amt = float(match.group())
                    item = re.sub(r'\d+(\.\d+)?', '', item).strip().title()
            
            if not item or item == str(amt) or item == "0.0":
                fallback_item = re.sub(r'\d+(\.\d+)?', '', processed_text).strip().title() if len(batch.items) == 1 else "Unknown Item"
                item = fallback_item if fallback_item else "Unknown Item"
                
            date_str = extraction.date_str or processed_text
            
            parsed_date = dateparser.parse(
                date_str,
                settings={
                    'PREFER_DATES_FROM': 'past', 
                    'RELATIVE_BASE': get_ist_now(), 
                    'TIMEZONE': 'Asia/Kolkata',
                    'RETURN_AS_TIMEZONE_AWARE': True
                }
            )
            
            if not parsed_date:
                parsed_date = get_ist_now()
            if parsed_date.tzinfo is None:
                parsed_date = IST_TZ.localize(parsed_date)
            
            current_year = get_ist_now().year
            if parsed_date.year != current_year:
                parsed_date = parsed_date.replace(year=current_year)
                
            results.append((amt, item, parsed_date, ai_category))
            
        if not results:
            raise FinanceManagerException(step="AI Extraction Node", message="No expenses identified in the text.", action="Ensure your message contains items and prices.")
            
        return results
        
    except FinanceManagerException:
        raise
    except Exception as e:
        raise FinanceManagerException(
            step="AI Parsing Engine",
            message=f"Extraction failure: {str(e)}",
            action="USER ACTION REQUIRED: Use standard format (e.g., 'Milk 40, Bread 30')."
        )
