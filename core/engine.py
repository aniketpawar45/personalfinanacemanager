import os, json, re, dateparser
from groq import Groq
from datetime import datetime

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def parse_expense_text(text):
    try:
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": "Extract amount (float), item_name, and potential date. Output ONLY valid JSON."}, {"role": "user", "content": text}],
            model="llama-3.1-8b-instant", response_format={"type": "json_object"}
        )
        data = json.loads(re.search(r'\{.*\}', res.choices[0].message.content, re.DOTALL).group(0))
        date = dateparser.parse(data.get("date") or text, settings={'PREFER_DATES_FROM': 'past'}) or datetime.now()
        return float(data.get("amount", 0)), data.get("item_name", text), date
    except:
        match = re.search(r'\d+(\.\d+)?', text)
        return float(match.group()) if match else 0.0, text, datetime.now()