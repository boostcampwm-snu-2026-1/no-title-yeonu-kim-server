from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import EmailVerification, User
from app.auth.repository import EmailVerificationRepository, UserRepository


class UserRepositoryImpl(UserRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_email(self, email: str) -> User | None:
        return cast(
            User | None,
            await self.db.scalar(select(User).where(User.email == email)),
        )

    async def find_by_id(self, user_id: str) -> User | None:
        return cast(
            User | None,
            await self.db.scalar(select(User).where(User.id == UUID(user_id))),
        )

    async def save(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user


class EmailVerificationRepositoryImpl(EmailVerificationRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save(self, verification: EmailVerification) -> None:
        self.db.add(verification)
        await self.db.commit()

    async def find_latest_unverified(
        self, email: str, code: str
    ) -> EmailVerification | None:
        return cast(
            EmailVerification | None,
            await self.db.scalar(
                select(EmailVerification)
                .where(
                    EmailVerification.email == email,
                    EmailVerification.code == code,
                    EmailVerification.is_verified.is_(False),
                    EmailVerification.expires_at > datetime.now(UTC),
                )
                .order_by(EmailVerification.created_at.desc())
            ),
        )

    async def update(self, verification: EmailVerification) -> None:
        await self.db.commit()
