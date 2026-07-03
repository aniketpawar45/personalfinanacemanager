import os
import re
import logging
import dateparser
from datetime import datetime
from groq import AsyncGroq
from core.models import ExpenseExtraction
from core.utils import get_ist_now, FinanceManagerException

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

SYSTEM_PROMPT = """You are a highly precise financial extraction tool. Extract 'amount', 'item_name', and 'date_str' into strict JSON. If no valid amount, return 0.0. If no valid item, return empty string."""

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
        
        if amt <= 0:
            raise FinanceManagerException(step="AI Extraction Node", message="No valid price found.", action="Include an amount (e.g., 'Milk 40').")
        if not item or item == str(amt) or item == "0.0":
            raise FinanceManagerException(step="AI Extraction Node", message="No item name identified.", action="Specify what the expense was for.")
            
        date_str = extraction.date_str or processed_text
        parsed_date = dateparser.parse(
            date_str,
            settings={'PREFER_DATES_FROM': 'past', 'RELATIVE_BASE': get_ist_now(), 'TIMEZONE': 'Asia/Kolkata'}
        ) or get_ist_now()
        
        if parsed_date.year != get_ist_now().year:
            parsed_date = parsed_date.replace(year=get_ist_now().year)
            
        return amt, item, parsed_date
        
    except FinanceManagerException:
        raise
    except Exception as e:
        raise FinanceManagerException(
            step="AI Parsing Engine",
            message=f"Extraction failure: {str(e)}",
            action="USER ACTION REQUIRED: Use standard format (e.g., 'Uber 200')."
        )
