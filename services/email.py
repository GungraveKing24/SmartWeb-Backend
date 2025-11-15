import httpx
from config import BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME

async def send_email(to: str, subject: str, html_body: str):
    if not BREVO_API_KEY or not BREVO_SENDER_EMAIL:
        raise Exception("Faltan variables de entorno para Brevo")

    url = "https://api.brevo.com/v3/smtp/email"

    payload = {
        "sender": {
            "email": BREVO_SENDER_EMAIL,
            "name": BREVO_SENDER_NAME
        },
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html_body
    }

    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload, headers=headers)

    if res.status_code >= 400:
        raise Exception(f"Brevo error: {res.text}")
