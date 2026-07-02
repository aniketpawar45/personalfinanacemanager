import os
import json
import logging
import dateparser
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
Return strictly valid JSON matching the exact schema requested. 
Do NOT include any conversational text.
"""

async def parse_expense_text(text: str) -> tuple[float, str, datetime]:
    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        raw_json = response.choices[0].message.content
        extraction = ExpenseExtraction.model_validate_json(raw_json)
        
        amt = float(extraction.amount)
        item = extraction.item_name.title()
        date_str = extraction.date_str or text
        
        parsed_date = dateparser.parse(
            date_str,
            settings={'PREFER_DATES_FROM': 'past', 'RELATIVE_BASE': datetime.now()}
        ) or datetime.now()
        
        if parsed_date.year != datetime.now().year:
            parsed_date = parsed_date.replace(year=datetime.now().year)
            
        return amt, item, parsed_date

    except Exception as e:
        logger.warning(f"AI parsing failed, falling back to regex: {str(e)}")
        import re
        match = re.search(r'\d+(\.\d+)?', text)
        amt = float(match.group()) if match else 0.0
        return amt, text.title(), datetime.now()