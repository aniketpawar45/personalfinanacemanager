import os, json, re
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
# Updated to a stable, current model
MODEL_NAME = "openai/gpt-oss-20b"

def parse_expense_text(text):
    try:
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": "Extract amount (as float), category (Groceries, Dining, Transport, Utilities, Shopping, Other), and description. Output ONLY valid JSON."}, {"role": "user", "content": text}],
            model=MODEL_NAME, response_format={"type": "json_object"}
        )
        data = json.loads(re.search(r'\{.*\}', res.choices[0].message.content, re.DOTALL).group(0))
        return float(data.get("amount", 0)), data.get("category", "Other"), data.get("description", text)
    except:
        match = re.search(r'\d+(\.\d+)?', text)
        if match:
            return float(match.group()), "Other", text
        return 0.0, "Other", text