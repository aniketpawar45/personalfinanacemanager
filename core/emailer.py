import os
import smtplib
import logging
from email.message import EmailMessage
from core.utils import FinanceManagerException

logger = logging.getLogger(__name__)

SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

def send_report_email(recipients: list, subject: str, body_text: str, csv_filename: str, csv_bytes: bytes):
    """Dispatches an email with a Zero-Persistence attachment via Gmail SMTP."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.error("SMTP credentials missing.")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"Enterprise Finance Bot <{SMTP_EMAIL}>"
    msg['To'] = ", ".join(recipients)
    msg.set_content(body_text)
    
    # Attach CSV from memory
    msg.add_attachment(csv_bytes, maintype='text', subtype='csv', filename=csv_filename)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
            smtp.send_message(msg)
            logger.info(f"Report successfully dispatched to {msg['To']}")
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP Auth Error: Check if SMTP_PASSWORD is a valid 16-char App Password.")
        raise FinanceManagerException("SMTP Node", "Gmail Auth Failed.", "Verify your App Password.")
    except Exception as e:
        logger.error(f"SMTP Dispatch Failed: {str(e)}")
        raise FinanceManagerException("SMTP Node", f"Dispatch failed: {str(e)}", "Check SMTP settings.")
