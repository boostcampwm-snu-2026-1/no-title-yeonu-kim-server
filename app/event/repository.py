from abc import ABC, abstractmethod
from uuid import UUID

from app.application.models import Application, ReviewSubmission
from app.auth.models import User
from app.event.models import Event
from app.store.models import Store


class EventRepository(ABC):
    @abstractmethod
    async def find_by_id(self, event_id: UUID) -> Event | None: ...

    @abstractmethod
    async def find_by_owner_id(self, owner_id: UUID) -> list[Event]: ...

    @abstractmethod
    async def find_store_by_id(self, store_id: UUID) -> Store | None: ...

    @abstractmethod
    async def save(self, event: Event) -> Event: ...

    @abstractmethod
    async def delete(self, event: Event) -> None: ...

    @abstractmethod
    async def find_applications_by_event_id(
        self,
        event_id: UUID,
        *,
        status_filter: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Application], int]: ...

    @abstractmethod
    async def find_user_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def find_submission_by_application_id(
        self, application_id: UUID
    ) -> ReviewSubmission | None: ...
