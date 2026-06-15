from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.store import Store
from app.schemas.event import EventCreateReq


async def _get_store_or_404(db: AsyncSession, store_id: str) -> Store:
    store = await db.scalar(select(Store).where(Store.id == UUID(store_id)))
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="상점을 찾을 수 없습니다.",
        )
    return store


async def list_owner_events(db: AsyncSession, owner_id: str) -> list[Event]:
    result = await db.scalars(
        select(Event)
        .join(Store, Event.store_id == Store.id)
        .where(Store.owner_id == UUID(owner_id))
    )
    return list(result.all())


async def create_event(db: AsyncSession, owner_id: str, data: EventCreateReq) -> Event:
    store = await _get_store_or_404(db, data.storeId)
    if str(store.owner_id) != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인 소유의 상점이 아닙니다.",
        )
    event = Event(
        store_id=UUID(data.storeId),
        title=data.title,
        condition=data.condition,
        reward=data.reward,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
