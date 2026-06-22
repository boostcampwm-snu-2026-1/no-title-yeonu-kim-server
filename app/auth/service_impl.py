import random
import string
from datetime import UTC, datetime, timedelta

from app.auth.models import EmailVerification, User
from app.auth.repository import EmailVerificationRepository, UserRepository
from app.auth.schemas import LoginReq, RegisterReq, ResetPasswordReq
from app.auth.service import AuthService
from app.core.email import send_temp_password_email, send_verification_email
from app.core.exceptions import (
    AUTH_001,
    AUTH_002,
    USER_001,
    USER_002,
    USER_006,
    AppException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class AuthServiceImpl(AuthService):
    def __init__(
        self,
        user_repo: UserRepository,
        ev_repo: EmailVerificationRepository,
    ) -> None:
        self.user_repo = user_repo
        self.ev_repo = ev_repo

    async def check_email_duplicate(self, email: str) -> None:
        if await self.user_repo.find_by_email(email):
            raise AppException(USER_001)

    async def send_verification_code(self, email: str) -> None:
        code = "".join(random.choices(string.digits, k=6))
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        verification = EmailVerification(email=email, code=code, expires_at=expires_at)
        await self.ev_repo.save(verification)
        await send_verification_email(email, code)

    async def validate_verification_code(self, email: str, code: str) -> str:
        record = await self.ev_repo.find_latest_unverified(email, code)
        if not record:
            raise AppException(USER_006)
        token = create_verification_token(email)
        record.is_verified = True
        record.verification_token = token
        await self.ev_repo.update(record)
        return token

    async def register(self, data: RegisterReq) -> tuple[User, str, str]:
        if await self.user_repo.find_by_email(data.email):
            raise AppException(USER_001)
        user = User(
            username=data.username,
            email=data.email,
            password_hash=get_password_hash(data.password),
            role=data.role,
        )
        user = await self.user_repo.save(user)
        user_id = str(user.id)
        return user, create_access_token(user_id), create_refresh_token(user_id)

    def refresh_access_token(self, refresh_token: str) -> str:
        try:
            user_id = decode_token(refresh_token)
        except Exception as e:
            raise AppException(AUTH_001) from e
        return create_access_token(user_id)

    async def login(self, data: LoginReq) -> tuple[User, str, str]:
        user = await self.user_repo.find_by_email(data.mail)
        if not user or not verify_password(data.password, user.password_hash):
            raise AppException(AUTH_002)
        if user.role != data.role:
            raise AppException(AUTH_002)
        user_id = str(user.id)
        return user, create_access_token(user_id), create_refresh_token(user_id)

    async def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> None:
        user = await self.user_repo.find_by_id(user_id)
        if not user or not verify_password(old_password, user.password_hash):
            raise AppException(AUTH_002)
        user.password_hash = get_password_hash(new_password)
        await self.user_repo.save(user)

    async def reset_password(self, data: ResetPasswordReq) -> None:
        user = await self.user_repo.find_by_email(data.email)
        if not user:
            raise AppException(USER_002)
        temp_password = "".join(
            random.choices(string.ascii_letters + string.digits, k=12)
        )
        user.password_hash = get_password_hash(temp_password)
        await self.user_repo.save(user)
        await send_temp_password_email(data.email, temp_password)
