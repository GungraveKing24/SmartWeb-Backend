from fastapi_mail import ConnectionConfig
from fastapi_mail import FastMail, MessageSchema, MessageType

mail_config = ConnectionConfig(
    MAIL_USERNAME="gungraveheat123@gmail.com",
    MAIL_PASSWORD="nryc ffut zqjz xskp",
    MAIL_FROM="gungraveheat123@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_email(to: str, subject: str, body: str):
    message = MessageSchema(
        subject=subject,
        recipients=[to],
        body=body,
        subtype=MessageType.html  # puedes usar HTML si quieres
    )
    fm = FastMail(mail_config)
    await fm.send_message(message)