from abc import ABC, abstractmethod

from app.event.models import Event
from app.event.schemas import ApplicationSummary, EventCreateReq


class EventService(ABC):
    @abstractmethod
    async def get_event(self, event_id: str) -> Event: ...

    @abstractmethod
    async def list_owner_events(self, owner_id: str) -> list[Event]: ...

    @abstractmethod
    async def create_event(self, owner_id: str, data: EventCreateReq) -> Event: ...

    @abstractmethod
    async def delete_event(self, event_id: str, owner_id: str) -> None: ...

    @abstractmethod
    async def list_event_applications(
        self,
        event_id: str,
        owner_id: str,
        *,
        status_filter: str | None,
        page: int,
        size: int,
    ) -> tuple[list[ApplicationSummary], int]: ...
