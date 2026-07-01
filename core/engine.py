import os, json, re
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def parse_expense_text(text):
    try:
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": "Extract amount, category (Groceries, Dining, Transport, Utilities, Shopping, Other), description. Output ONLY JSON."}, {"role": "user", "content": text}],
            model="llama3-8b-8192", response_format={"type": "json_object"}
        )
        data = json.loads(re.search(r'\{.*\}', res.choices[0].message.content, re.DOTALL).group(0))
        return float(data.get("amount", 0)), data.get("category", "Other"), data.get("description", text)
    except:
        match = re.search(r'\d+(\.\d+)?', text)
        return float(match.group()), "Other", text if match else (0.0, "Other", text)