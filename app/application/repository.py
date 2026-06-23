from abc import ABC, abstractmethod
from uuid import UUID

from app.application.models import Application, ReviewImage, ReviewSubmission
from app.auth.models import User
from app.event.models import Event


class ApplicationRepository(ABC):
    @abstractmethod
    async def find_event_by_id(self, event_id: UUID) -> Event | None: ...

    @abstractmethod
    async def find_by_id(self, application_id: UUID) -> Application | None: ...

    @abstractmethod
    async def find_by_event_and_reviewer(
        self, event_id: UUID, reviewer_id: UUID
    ) -> Application | None: ...

    @abstractmethod
    async def find_by_reviewer_id(
        self, reviewer_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[Application], int]: ...

    @abstractmethod
    async def find_user_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def find_submission_by_application_id(
        self, application_id: UUID
    ) -> ReviewSubmission | None: ...

    @abstractmethod
    async def find_images_by_submission_id(
        self, submission_id: UUID
    ) -> list[ReviewImage]: ...

    @abstractmethod
    async def save_application(self, application: Application) -> None: ...

    @abstractmethod
    async def delete(self, application: Application) -> None: ...

    @abstractmethod
    async def save_review(
        self, application_id: UUID, message: str, image_keys: list[str]
    ) -> None: ...
