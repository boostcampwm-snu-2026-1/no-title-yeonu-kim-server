from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.event.models import Event
from app.store.models import Store
from app.store.repository import StoreRepository


class StoreRepositoryImpl(StoreRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_id(self, store_id: UUID) -> Store | None:
        return cast(
            Store | None,
            await self.db.scalar(select(Store).where(Store.id == store_id)),
        )

    async def find_all(
        self,
        *,
        category: str | None,
        name: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Store], int]:
        q = select(Store)
        if category:
            q = q.where(Store.category == category)
        if name:
            q = q.where(Store.name.ilike(f"%{name}%"))
        count_q = select(func.count()).select_from(q.subquery())
        total = await self.db.scalar(count_q) or 0
        stores = list((await self.db.scalars(q.offset(offset).limit(limit))).all())
        return stores, int(total)

    async def save(self, store: Store) -> Store:
        self.db.add(store)
        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def delete(self, store: Store) -> None:
        await self.db.delete(store)
        await self.db.commit()

    async def find_events_by_store_id(self, store_id: UUID) -> list[Event]:
        q = select(Event).where(Event.store_id == store_id)
        return list((await self.db.scalars(q)).all())
