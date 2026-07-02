import os, re, dateparser, logging, httpx
from datetime import datetime
from groq import AsyncGroq
from core.models import ExpenseExtraction

client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
logger = logging.getLogger(__name__)

async def transcribe_audio(file_id: str, bot_token: str) -> str:
    async with httpx.AsyncClient() as http:
        file_info = (await http.get(f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}")).json()
        path = file_info["result"]["file_path"]
        audio = (await http.get(f"https://api.telegram.org/file/bot{bot_token}/{path}")).content
        res = await client.audio.transcriptions.create(file=("v.ogg", audio, "audio/ogg"), model="whisper-large-v3")
        return res.text.strip()

async def parse_expense_text(text: str):
    processed = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text))
    res = await client.chat.completions.create(messages=[{"role":"system","content":"Extract amount and item name as JSON."}, {"role":"user","content":processed}], model="llama-3.1-8b-instant", response_format={"type": "json_object"})
    ext = ExpenseExtraction.model_validate_json(res.choices[0].message.content)
    if not ext.item_name or ext.amount <= 0: raise ValueError("I couldn't identify the item or amount.")
    return ext.amount, ext.item_name, datetime.now()