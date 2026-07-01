import os, json, re, dateparser
from groq import Groq
from datetime import datetime

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def parse_expense_text(text):
    try:
        # Prompt AI to extract fields clearly
        res = client.chat.completions.create(
            messages=[{"role": "system",
                       "content": "Extract 'amount' (float), 'item_name', and 'date' (if mentioned). Output ONLY valid JSON."},
                      {"role": "user", "content": text}],
            model="llama-3.1-8b-instant", response_format={"type": "json_object"}
        )
        data = json.loads(re.search(r'\{.*\}', res.choices[0].message.content, re.DOTALL).group(0))

        amt = float(data.get("amount", 0))
        item = data.get("item_name", text).title()

        # Parse and force current year with DMY order
        date_str = data.get("date") or text
        parsed_date = dateparser.parse(
            date_str,
            settings={
                'PREFER_DATES_FROM': 'past',
                'RELATIVE_BASE': datetime.now(),
                'DATE_ORDER': 'DMY'  # <-- THIS FIXES THE 23-05 ISSUE
            }
        ) or datetime.now()

        # Ensure it stays in the current year
        if parsed_date.year != datetime.now().year:
            parsed_date = parsed_date.replace(year=datetime.now().year)

        return amt, item, parsed_date, ""
    except:
        match = re.search(r'\d+(\.\d+)?', text)
        return float(match.group()) if match else 0.0, text.title(), datetime.now(), ""