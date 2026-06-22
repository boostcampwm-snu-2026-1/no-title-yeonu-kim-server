from abc import ABC, abstractmethod

from app.auth.models import EmailVerification, User


class UserRepository(ABC):
    @abstractmethod
    async def find_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def find_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...


class EmailVerificationRepository(ABC):
    @abstractmethod
    async def save(self, verification: EmailVerification) -> None: ...

    @abstractmethod
    async def find_latest_unverified(
        self, email: str, code: str
    ) -> EmailVerification | None: ...

    @abstractmethod
    async def update(self, verification: EmailVerification) -> None: ...
