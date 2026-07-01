import os, json, re, dateparser
from groq import Groq
from datetime import datetime

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def parse_expense_text(text):
    try:
        # Prompt AI to extract fields
        res = client.chat.completions.create(
            messages=[{"role": "system",
                       "content": "Extract 'amount' (float), 'item_name' (string), and 'date' (string, if present). Output ONLY valid JSON."},
                      {"role": "user", "content": text}],
            model="llama-3.1-8b-instant", response_format={"type": "json_object"}
        )
        data = json.loads(re.search(r'\{.*\}', res.choices[0].message.content, re.DOTALL).group(0))

        amt = float(data.get("amount", 0))
        item = data.get("item_name", text).title()  # Normalized to Title Case

        # Enforce Year 2026
        date_str = data.get("date") or text
        date = dateparser.parse(
            date_str,
            settings={'PREFER_DATES_FROM': 'past', 'RELATIVE_BASE': datetime(2026, 1, 1)}
        ) or datetime.now()

        return amt, item, date
    except:
        match = re.search(r'\d+(\.\d+)?', text)
        return float(match.group()) if match else 0.0, text.title(), datetime.now()