from abc import ABC, abstractmethod

from app.auth.models import User
from app.auth.schemas import LoginReq, RegisterReq, ResetPasswordReq


class AuthService(ABC):
    @abstractmethod
    async def check_email_duplicate(self, email: str) -> None: ...

    @abstractmethod
    async def send_verification_code(self, email: str) -> None: ...

    @abstractmethod
    async def validate_verification_code(self, email: str, code: str) -> str: ...

    @abstractmethod
    async def register(self, data: RegisterReq) -> tuple[User, str, str]: ...

    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> str: ...

    @abstractmethod
    async def login(self, data: LoginReq) -> tuple[User, str, str]: ...

    @abstractmethod
    async def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> None: ...

    @abstractmethod
    async def reset_password(self, data: ResetPasswordReq) -> None: ...
