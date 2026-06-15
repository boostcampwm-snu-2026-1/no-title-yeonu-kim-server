import random
import string
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_verification import EmailVerification
from app.models.user import User


async def send_verification_code(db: AsyncSession, email: str) -> None:
    code = "".join(random.choices(string.digits, k=6))
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    verification = EmailVerification(email=email, code=code, expires_at=expires_at)
    db.add(verification)
    await db.commit()
    print(f"[DEV] Verification code for {email}: {code}")


async def check_email_duplicate(db: AsyncSession, email: str) -> None:
    exists = await db.scalar(select(User).where(User.email == email))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 가입된 이메일입니다.",
        )
