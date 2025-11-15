import httpx
import os
from config import MAILERSEND_API_KEY, MAILERSEND_SENDER

async def send_email(to: str, subject: str, html_body: str):
    if not MAILERSEND_API_KEY or not MAILERSEND_SENDER:
        raise Exception("Faltan variables de entorno para MailerSend")

    url = "https://api.mailersend.com/v1/email"

    payload = {
        "from": {"email": MAILERSEND_SENDER},
        "to": [{"email": to}],
        "subject": subject,
        "html": html_body
    }

    headers = {
        "Authorization": f"Bearer {MAILERSEND_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload, headers=headers)

        if res.status_code >= 400:
            raise Exception(f"MailerSend error: {res.text}")