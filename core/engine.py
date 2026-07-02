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
Return strictly valid JSON matching the exact schema requested. 
Do NOT include any conversational text.
"""


async def parse_expense_text(text: str) -> tuple[float, str, datetime]:
    # 🚀 NLP Pre-Processing: Intelligently separate squished letters and numbers
    # "milk6565" -> "milk 6565"
    processed_text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    # "150coffee" -> "150 coffee"
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

        amt = float(extraction.amount)
        item = extraction.item_name.title()
        date_str = extraction.date_str or processed_text

        parsed_date = dateparser.parse(
            date_str,
            settings={'PREFER_DATES_FROM': 'past', 'RELATIVE_BASE': datetime.now()}
        ) or datetime.now()

        if parsed_date.year != datetime.now().year:
            parsed_date = parsed_date.replace(year=datetime.now().year)

        return amt, item, parsed_date

    except Exception as e:
        logger.warning(f"AI parsing failed, falling back to regex: {str(e)}")
        # Hardened regex fallback using the pre-processed text
        match = re.search(r'\d+(\.\d+)?', processed_text)
        amt = float(match.group()) if match else 0.0

        # Strip the numeric amount out of the text to leave just the clean item name
        item_name = re.sub(r'\d+(\.\d+)?', '', processed_text).strip().title()

        return amt, item_name, datetime.now()