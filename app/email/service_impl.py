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
    async def send_verification(self, to: str, code: str) -> None:
        subject = "[VLSI] 이메일 인증 코드"
        body = f"""
    <p>안녕하세요,</p>
    <p>아래 인증 코드를 입력해 주세요. 코드는 <strong>10분</strong> 후 만료됩니다.</p>
    <h2 style="letter-spacing:4px">{code}</h2>
    <p>본인이 요청하지 않은 경우 이 메일을 무시하세요.</p>
    """
        await send_email(to, subject, body)

    async def send_temp_password(self, to: str, temp_password: str) -> None:
        subject = "[VLSI] 임시 비밀번호 안내"
        body = f"""
    <p>안녕하세요,</p>
    <p>요청하신 임시 비밀번호입니다. 로그인 후 반드시 비밀번호를 변경해 주세요.</p>
    <h2 style="letter-spacing:4px">{temp_password}</h2>
    """
        await send_email(to, subject, body)

    async def send_reward(
        self,
        to: str,
        event_title: str,
        reward_wei: int,
        wallet_balance_wei: int,
    ) -> None:
        reward_eth = reward_wei / 10**18
        balance_eth = wallet_balance_wei / 10**18
        subject = "[VLSI] 리워드 지급 완료"
        body = f"""
    <p>안녕하세요,</p>
    <p>스마트컨트랙트를 통한 리워드 지급이 완료되었습니다.</p>
    <table style="border-collapse:collapse;margin-top:12px">
      <tr>
        <td style="padding:8px 16px 8px 0;color:#666">지급 이벤트</td>
        <td style="padding:8px 0"><strong>{event_title}</strong></td>
      </tr>
      <tr>
        <td style="padding:8px 16px 8px 0;color:#666">지급 금액</td>
        <td style="padding:8px 0"><strong>{reward_eth:.6f} ETH</strong></td>
      </tr>
      <tr>
        <td style="padding:8px 16px 8px 0;color:#666">현재 지갑 잔액</td>
        <td style="padding:8px 0"><strong>{balance_eth:.6f} ETH</strong></td>
      </tr>
    </table>
    <p style="margin-top:16px;color:#888;font-size:12px">
      본 메일은 자동 발송된 메일입니다.
    </p>
    """
        await send_email(to, subject, body)


async def send_reward_email(
    to: str,
    event_title: str,
    reward_wei: int,
    wallet_balance_wei: int,
) -> None:
    await SmtpEmailSender().send_reward(to, event_title, reward_wei, wallet_balance_wei)
