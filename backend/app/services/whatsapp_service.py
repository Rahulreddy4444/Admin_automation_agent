from typing import Dict, Any
from app.config import settings

def send_whatsapp_via_twilio(recipient_phone: str, message: str) -> Dict[str, Any]:
    """
    Sends a WhatsApp message via Twilio matching notebook logic.
    Honors DRY_RUN safety setting.
    """
    if settings.DRY_RUN:
        return {
            "success": True,
            "status": "SIMULATED (DRY_RUN=True)",
            "message": f"Simulated WhatsApp send to {recipient_phone}: '{message}'"
        }

    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return {
            "success": False,
            "error": "TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not configured."
        }

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        target_phone = str(recipient_phone).strip()
        if not target_phone.startswith("whatsapp:"):
            target_phone = f"whatsapp:{target_phone}"

        result = client.messages.create(
            from_=settings.TWILIO_FROM_WHATSAPP,
            to=target_phone,
            body=message
        )
        return {"success": True, "sid": result.sid, "status": "SENT via Twilio"}
    except Exception as e:
        return {"success": False, "error": str(e)}
