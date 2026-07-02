import os
import re
import httpx
import logging
from groq import AsyncGroq
from core.models import ExpenseExtraction

# Initialize Groq client
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))


async def transcribe_audio(file_id: str, token: str) -> str:
    """Fetches audio from Telegram and transcribes using Whisper."""
    try:
        async with httpx.AsyncClient() as h:
            # 1. Get file path from Telegram
            file_info = (await h.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}")).json()
            path = file_info["result"]["file_path"]

            # 2. Download audio file
            audio_content = (await h.get(f"https://api.telegram.org/file/bot{token}/{path}")).content

            # 3. Transcribe via Groq
            res = await client.audio.transcriptions.create(
                file=("audio.ogg", audio_content, "audio/ogg"),
                model="whisper-large-v3"
            )
            return res.text.strip()
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        return ""


async def parse_expense_text(text: str):
    """Uses LLM to extract amount and description from unstructured text."""
    try:
        # Normalize text to separate numbers and words (e.g., "milk50" -> "milk 50")
        processed = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text))

        system_prompt = (
            "Extract the amount (float) and item name (string) from the user input. "
            "Return valid JSON only. If no amount is found, default to 0.0."
        )

        res = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": processed}
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )

        # Validate with Pydantic model
        ext = ExpenseExtraction.model_validate_json(res.choices[0].message.content)

        if not ext.item_name or ext.amount <= 0:
            raise ValueError("Could not extract valid item or amount.")

        return ext.amount, ext.item_name
    except Exception as e:
        logging.error(f"Parsing error: {e}")
        raise e