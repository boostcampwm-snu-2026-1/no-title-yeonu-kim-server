from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import EmailVerificationRepository, UserRepository
from app.auth.repository_impl import EmailVerificationRepositoryImpl, UserRepositoryImpl
from app.auth.service import AuthService
from app.auth.service_impl import AuthServiceImpl
from app.db.session import get_db


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepositoryImpl(db)


def get_email_verification_repository(
    db: AsyncSession = Depends(get_db),
) -> EmailVerificationRepository:
    return EmailVerificationRepositoryImpl(db)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    ev_repo: EmailVerificationRepository = Depends(get_email_verification_repository),
) -> AuthService:
    return AuthServiceImpl(user_repo, ev_repo)
