import pytz
from datetime import datetime

IST_TZ = pytz.timezone('Asia/Kolkata')

def get_ist_now() -> datetime:
    """Returns the current time strictly in Indian Standard Time."""
    return datetime.now(IST_TZ)

class FinanceManagerException(Exception):
    """Enterprise exception mapping exact failure nodes."""
    def __init__(self, step: str, message: str, action: str):
        self.step = step
        self.message = message
        self.action = action
        super().__init__(self.message)
