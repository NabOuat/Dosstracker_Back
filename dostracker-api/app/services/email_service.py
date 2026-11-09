"""Envoi d'emails via SMTP (Brevo, Gmail, Mailjet, OVH...). Config par variables d'environnement."""
import os
import smtplib
import ssl
from email.message import EmailMessage
from logger import get_logger

logger = get_logger()


class EmailService:
    def __init__(self):
        self.host = os.getenv("SMTP_HOST")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        self.sender = os.getenv("SMTP_FROM") or self.user
        self.enabled = bool(self.host and self.sender)

    def send(self, to: str, subject: str, html: str, text: str = "") -> bool:
        if not self.enabled:
            logger.warning("SMTP non configuré (SMTP_HOST/SMTP_FROM): email non envoyé")
            return False
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.sender, to, subject
        msg.set_content(text or "Ouvrez ce message dans un client compatible HTML.")
        msg.add_alternative(html, subtype="html")
        try:
            ctx = ssl.create_default_context()
            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=15, context=ctx) as s:
                    if self.user:
                        s.login(self.user, self.password)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=15) as s:
                    s.starttls(context=ctx)
                    if self.user:
                        s.login(self.user, self.password)
                    s.send_message(msg)
            logger.info(f"Email envoyé à {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Échec envoi email à {to}: {e}")
            return False


email_service = EmailService()
