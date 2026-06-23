from uuid import UUID

from app.core.exceptions import AUTH_007, STORE_001, AppException
from app.store.models import Store
from app.store.repository import StoreRepository
from app.store.schemas import StoreCreateReq, StoreEventSummary, StoreListItem
from app.store.service import StoreService


class StoreServiceImpl(StoreService):
    def __init__(self, repo: StoreRepository) -> None:
        self.repo = repo

    async def get_store(self, store_id: str) -> Store:
        store = await self.repo.find_by_id(UUID(store_id))
        if not store:
            raise AppException(STORE_001)
        return store

    async def list_stores(
        self,
        *,
        category: str | None,
        name: str | None,
        page: int,
        size: int,
    ) -> tuple[list[StoreListItem], int]:
        stores, total = await self.repo.find_all(
            category=category, name=name, offset=page * size, limit=size
        )
        items: list[StoreListItem] = []
        for store in stores:
            events = await self.repo.find_events_by_store_id(store.id)
            items.append(
                StoreListItem(
                    id=str(store.id),
                    name=store.name,
                    address=store.address,
                    category=store.category,
                    thumbnailKey=store.thumbnail_key,
                    description=store.description,
                    events=[
                        StoreEventSummary(
                            id=str(e.id),
                            title=e.title,
                            condition=e.condition,
                            reward=e.reward / 10**18,
                            isActive=e.is_active,
                        )
                        for e in events
                    ],
                    totalEventCount=len(events),
                )
            )
        return items, total

    async def create_store(self, owner_id: str, data: StoreCreateReq) -> Store:
        store = Store(
            name=data.name,
            address=data.address,
            category=data.category,
            thumbnail_key=data.thumbnailUrl,
            description=data.description,
            owner_id=UUID(owner_id),
        )
        return await self.repo.save(store)

    async def delete_store(self, store_id: str, user_id: str) -> None:
        store = await self.get_store(store_id)
        if str(store.owner_id) != user_id:
            raise AppException(AUTH_007)
        await self.repo.delete(store)

    async def list_store_events(self, store_id: str) -> list[StoreEventSummary]:
        await self.get_store(store_id)
        events = await self.repo.find_events_by_store_id(UUID(store_id))
        return [
            StoreEventSummary(
                id=str(e.id),
                title=e.title,
                condition=e.condition,
                reward=e.reward / 10**18,
                isActive=e.is_active,
            )
            for e in events
        ]
