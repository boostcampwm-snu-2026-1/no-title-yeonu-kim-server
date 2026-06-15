import random
import string
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_verification_token,
    get_password_hash,
)
from app.models.email_verification import EmailVerification
from app.models.user import User
from app.schemas.auth import RegisterReq


async def send_verification_code(db: AsyncSession, email: str) -> None:
    code = "".join(random.choices(string.digits, k=6))
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    verification = EmailVerification(email=email, code=code, expires_at=expires_at)
    db.add(verification)
    await db.commit()
    print(f"[DEV] Verification code for {email}: {code}")


async def validate_verification_code(db: AsyncSession, email: str, code: str) -> str:
    record = await db.scalar(
        select(EmailVerification)
        .where(
            EmailVerification.email == email,
            EmailVerification.code == code,
            EmailVerification.is_verified.is_(False),
            EmailVerification.expires_at > datetime.now(UTC),
        )
        .order_by(EmailVerification.created_at.desc())
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="코드가 일치하지 않거나 만료되었습니다.",
        )
    token = create_verification_token(email)
    record.is_verified = True
    record.verification_token = token
    await db.commit()
    return token


async def register(db: AsyncSession, data: RegisterReq) -> tuple[User, str, str]:
    exists = await db.scalar(select(User).where(User.email == data.email))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 가입된 이메일입니다.",
        )
    user = User(
        username=data.username,
        email=data.email,
        password_hash=get_password_hash(data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    user_id = str(user.id)
    return user, create_access_token(user_id), create_refresh_token(user_id)


async def check_email_duplicate(db: AsyncSession, email: str) -> None:
    exists = await db.scalar(select(User).where(User.email == email))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 가입된 이메일입니다.",
        )
