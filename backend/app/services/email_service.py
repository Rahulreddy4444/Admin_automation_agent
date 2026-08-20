import smtplib
from email.message import EmailMessage
from typing import Dict, Any
from app.config import settings

def send_email_direct(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Sends an email directly via Gmail SMTP (bypassing Twilio restrictions) matching notebook logic.
    Honors DRY_RUN safety setting.
    """
    if settings.DRY_RUN:
        return {
            "success": True,
            "status": "SIMULATED (DRY_RUN=True)",
            "message": f"Simulated email send to {recipient} with subject '{subject}'"
        }

    if not settings.SMTP_EMAIL or not settings.SMTP_APP_PASSWORD:
        return {
            "success": False,
            "error": "SMTP_EMAIL or SMTP_APP_PASSWORD not configured."
        }

    try:
        msg = EmailMessage()
        msg["From"] = settings.SMTP_EMAIL
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(settings.SMTP_EMAIL, settings.SMTP_APP_PASSWORD)
            server.send_message(msg)

        return {"success": True, "status": "SENT via SMTP"}
    except Exception as e:
        return {"success": False, "error": str(e)}
