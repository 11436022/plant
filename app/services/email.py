import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_email(*, to_email: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
    """透過 SMTP 寄送信件（具備短逾時保護與雲端網路封鎖防護）。"""

    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        print("[EMAIL] SMTP_HOST 或 SMTP_FROM_EMAIL 未設定，略過寄信。")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    smtp_cls = smtplib.SMTP_SSL if settings.SMTP_USE_SSL else smtplib.SMTP
    try:
        # 逾時縮短為 3 秒，避免雲端環境因防火牆封鎖 SMTP 端口時阻塞伺服器請求
        with smtp_cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=3) as server:
            if not settings.SMTP_USE_SSL and settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
            server.send_message(message)
            return True
    except Exception as exc:
        print(f"[EMAIL WARN] 郵件寄送未成功 ({exc})，已啟用備援機制確保流程不中斷。")
        return False
