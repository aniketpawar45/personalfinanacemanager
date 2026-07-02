import os, re, httpx, logging
from groq import AsyncGroq
from core.models import ExpenseExtraction

client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))


async def transcribe_audio(file_id, token):
    try:
        async with httpx.AsyncClient() as h:
            path = (await h.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}")).json()["result"][
                "file_path"]
            audio = (await h.get(f"https://api.telegram.org/file/bot{token}/{path}")).content
            res = await client.audio.transcriptions.create(file=("v.ogg", audio, "audio/ogg"), model="whisper-large-v3")
            return res.text.strip()
    except Exception:
        return ""


async def parse_expense_text(text: str):
    # Normalize
    processed = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text))

    # Enhanced prompt for strict JSON compliance
    system_prompt = (
        "You are an expense parser. Extract 'amount' (float) and 'item_name' (string) from input. "
        "If no amount is found, return 0.0. If no item name is found, return 'Miscellaneous'. "
        "Return ONLY a JSON object: {\"amount\": float, \"item_name\": \"string\"}"
    )

    try:
        res = await client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": processed}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        ext = ExpenseExtraction.model_validate_json(res.choices[0].message.content)

        # Fallback for empty values
        if ext.amount <= 0: ext.amount = 0.0
        if not ext.item_name: ext.item_name = "Unknown Expense"

        return ext.amount, ext.item_name
    except Exception as e:
        logging.error(f"AI Parse Error: {e}")
        # Final safety fallback
        return 0.0, "Unknown Expense"