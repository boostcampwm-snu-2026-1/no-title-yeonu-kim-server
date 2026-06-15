import random
import string
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.email_verification import EmailVerification
from app.models.user import User
from app.schemas.auth import LoginReq, RegisterReq, ResetPasswordReq


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


def refresh_access_token(refresh_token: str) -> str:
    try:
        user_id = decode_token(refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 리프레시 토큰입니다.",
        ) from e
    return create_access_token(user_id)


async def login(db: AsyncSession, data: LoginReq) -> tuple[User, str, str]:
    user = await db.scalar(select(User).where(User.email == data.mail))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )
    if user.role != data.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="계정 역할이 일치하지 않습니다.",
        )
    user_id = str(user.id)
    return user, create_access_token(user_id), create_refresh_token(user_id)


async def change_password(
    db: AsyncSession, user_id: str, old_password: str, new_password: str
) -> None:
    user = await db.scalar(select(User).where(User.id == UUID(user_id)))
    if not user or not verify_password(old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다.",
        )
    user.password_hash = get_password_hash(new_password)
    await db.commit()


async def reset_password(db: AsyncSession, data: ResetPasswordReq) -> None:
    user = await db.scalar(select(User).where(User.email == data.email))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="가입되지 않은 이메일입니다.",
        )
    temp_password = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    user.password_hash = get_password_hash(temp_password)
    await db.commit()
    print(f"[DEV] Temporary password for {data.email}: {temp_password}")


async def check_email_duplicate(db: AsyncSession, email: str) -> None:
    exists = await db.scalar(select(User).where(User.email == email))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 가입된 이메일입니다.",
        )
