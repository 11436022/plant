import smtplib
from email.message import EmailMessage

from app.core.config import (
    SMTP_FROM_EMAIL,
    SMTP_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_SSL,
    SMTP_USE_TLS,
    SMTP_USERNAME,
)


def send_email(*, to_email: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    """透過 SMTP 寄送信件。"""

    if not SMTP_HOST or not SMTP_FROM_EMAIL:
        raise RuntimeError("SMTP is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    smtp_cls = smtplib.SMTP_SSL if SMTP_USE_SSL else smtplib.SMTP
    with smtp_cls(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        # 一般 SMTP 伺服器多半採用 STARTTLS，保留 SSL 直連選項方便部署。
        if not SMTP_USE_SSL and SMTP_USE_TLS:
            server.starttls()
        if SMTP_USERNAME:
            server.login(SMTP_USERNAME, SMTP_PASSWORD or "")
        server.send_message(message)
