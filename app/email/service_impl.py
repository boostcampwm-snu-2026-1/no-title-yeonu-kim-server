import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.exceptions import MAIL_001, AppException
from app.email.service import EmailSender

logger = logging.getLogger(__name__)


def _send_via_smtp(to: str, subject: str, body_html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_user, to, msg.as_string())


async def send_email(to: str, subject: str, body_html: str) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("[EMAIL] SMTP credentials not set — skipping send to %s", to)
        return
    try:
        await asyncio.to_thread(_send_via_smtp, to, subject, body_html)
    except smtplib.SMTPException as e:
        logger.error("[EMAIL] Failed to send email to %s: %s", to, e)
        raise AppException(MAIL_001) from e


class SmtpEmailSender(EmailSender):
    async def send(self, to: str, subject: str, body_html: str) -> None:
        await send_email(to, subject, body_html)
