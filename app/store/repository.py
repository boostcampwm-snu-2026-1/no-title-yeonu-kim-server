from abc import ABC, abstractmethod
from uuid import UUID

from app.models.event import Event
from app.store.models import Store


class StoreRepository(ABC):
    @abstractmethod
    async def find_by_id(self, store_id: UUID) -> Store | None: ...

    @abstractmethod
    async def find_all(
        self,
        *,
        category: str | None,
        name: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Store], int]: ...

    @abstractmethod
    async def save(self, store: Store) -> Store: ...

    @abstractmethod
    async def delete(self, store: Store) -> None: ...

    @abstractmethod
    async def find_events_by_store_id(self, store_id: UUID) -> list[Event]: ...
