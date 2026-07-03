import os
import re
import logging
import dateparser
from datetime import datetime
from groq import AsyncGroq
from core.models import ExpenseExtraction
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

SYSTEM_PROMPT = """You are a highly precise financial extraction tool. Extract 'amount' (number), 'item_name' (string), and 'date_str' (string) into strict JSON. The amount is the cost or price mentioned. If no valid amount, return 0.0. If no valid item, return empty string."""

async def parse_expense_text(text: str) -> tuple[float, str, datetime]:
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
        
        # ENTERPRISE HOTFIX: Hybrid Regex Fallback for missing amounts
        if amt <= 0:
            match = re.search(r'\d+(\.\d+)?', processed_text)
            if match:
                amt = float(match.group())
            else:
                raise FinanceManagerException(step="AI Extraction Node", message="No valid price found.", action="Include an amount (e.g., 'Milk 40').")
        
        # Hybrid Regex Fallback for missing or conflated item names
        if not item or item == str(amt) or item == "0.0":
            fallback_item = re.sub(r'\d+(\.\d+)?', '', processed_text).strip().title()
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
            
        return amt, item, parsed_date
        
    except FinanceManagerException:
        raise
    except Exception as e:
        raise FinanceManagerException(
            step="AI Parsing Engine",
            message=f"Extraction failure: {str(e)}",
            action="USER ACTION REQUIRED: Use standard format (e.g., 'Uber 200')."
        )
