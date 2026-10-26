import json
import os
import smtplib
import urllib.request
from email.message import EmailMessage

from app.core.config import settings


def send_email(*, to_email: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
    """透過 HTTPS Webhook (Google Mail Relay / Resend) 或標準 SMTP 寄送信件。
    
    支援雲端對外 SMTP 端口遭封鎖之環境，走標準 HTTPS (443) 由使用者真實 Gmail 寄達。
    """

    # 🌟 優先方式 1：Google Apps Script Webhook (走 HTTPS Port 443，由使用者自己的 Gmail 帳號發出真實信件，100% 繞過雲端端口封鎖)
    webhook_url = os.getenv("MAIL_WEBHOOK_URL") or getattr(settings, "MAIL_WEBHOOK_URL", None)
    if webhook_url:
        try:
            payload = {
                "to": to_email,
                "subject": subject,
                "body": text_body,
                "html": html_body or text_body,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_text = resp.read().decode("utf-8")
                print(f"[EMAIL] 成功透過 Google Webhook (HTTPS) 將真實信件寄送至 {to_email}！回應: {resp_text}")
                return True
        except Exception as e:
            print(f"[EMAIL WARN] Google Webhook 寄信未成功: {e}")

    # 🌟 優先方式 2：Resend API (走 HTTPS Port 443)
    resend_key = os.getenv("RESEND_API_KEY") or getattr(settings, "RESEND_API_KEY", None)
    if resend_key:
        try:
            payload = {
                "from": f"{settings.SMTP_FROM_NAME} <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "text": text_body,
                "html": html_body or text_body,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {resend_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_text = resp.read().decode("utf-8")
                print(f"[EMAIL] 成功透過 Resend API (HTTPS) 寄送真實信件至 {to_email}！回應: {resp_text}")
                return True
        except Exception as e:
            print(f"[EMAIL WARN] Resend API 寄信未成功: {e}")

    # 🌟 方式 3：標準 SMTP (本地電腦測試或未封鎖 SMTP 端口之環境)
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
        with smtp_cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5) as server:
            if not settings.SMTP_USE_SSL and settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
            server.send_message(message)
            print(f"[EMAIL] 成功透過 SMTP 將真實信件寄送至 {to_email}！")
            return True
    except Exception as exc:
        print(f"[EMAIL WARN] SMTP 寄送未成功 ({exc})。")
        return False
