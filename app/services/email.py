import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_email(*, to_email: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    """透過 SMTP 寄送信件。"""

    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise RuntimeError("SMTP is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    smtp_cls = smtplib.SMTP_SSL if settings.SMTP_USE_SSL else smtplib.SMTP
    with smtp_cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        # 一般 SMTP 伺服器多半採用 STARTTLS，保留 SSL 直連選項方便部署。
        if not settings.SMTP_USE_SSL and settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
        server.send_message(message)