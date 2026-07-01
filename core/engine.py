import os
import json
from groq import Groq

api_key = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=api_key) if api_key else None

def parse_expense_text(text: str):
    """
    Uses Groq LLM to extract amount, category, and description from raw text.
    Expected return format: tuple(amount: float, category: str, description: str)
    """
    if not groq_client: return 0.0, "Other", text
    
    system_prompt = """
    You are a financial parsing assistant. Extract the transaction details from the user's text.
    Return ONLY a valid JSON object with these keys: 
    "amount" (float), "category" (string), "description" (string).
    Categories MUST be one of: Groceries, Dining, Transport, Utilities, Shopping, Other.
    """
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            model="llama3-8b-8192", 
            response_format={"type": "json_object"}
        )
        
        result = json.loads(chat_completion.choices[0].message.content)
        return float(result.get("amount", 0.0)), result.get("category", "Other"), result.get("description", text)
        
    except Exception as e:
        print(f"LLM Parsing Error: {e}")
        return 0.0, "Other", text
