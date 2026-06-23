from abc import ABC, abstractmethod

from app.store.models import Store
from app.store.schemas import StoreCreateReq, StoreEventSummary, StoreListItem


class StoreService(ABC):
    @abstractmethod
    async def get_store(self, store_id: str) -> Store: ...

    @abstractmethod
    async def list_stores(
        self,
        *,
        category: str | None,
        name: str | None,
        page: int,
        size: int,
    ) -> tuple[list[StoreListItem], int]: ...

    @abstractmethod
    async def create_store(self, owner_id: str, data: StoreCreateReq) -> Store: ...

    @abstractmethod
    async def delete_store(self, store_id: str, user_id: str) -> None: ...

    @abstractmethod
    async def list_store_events(self, store_id: str) -> list[StoreEventSummary]: ...
