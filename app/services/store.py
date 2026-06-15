from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AUTH_007, STORE_001, AppException
from app.models.event import Event
from app.models.store import Store
from app.schemas.store import StoreCreateReq, StoreEventSummary, StoreListItem


async def get_store_or_404(db: AsyncSession, store_id: str) -> Store:
    store = await db.scalar(select(Store).where(Store.id == UUID(store_id)))
    if not store:
        raise AppException(STORE_001)
    return store


async def _get_store_events(db: AsyncSession, store_id: UUID) -> list[Event]:
    result = await db.scalars(select(Event).where(Event.store_id == store_id))
    return list(result.all())


async def list_stores(
    db: AsyncSession,
    *,
    category: str | None,
    name: str | None,
    page: int,
    size: int,
) -> tuple[list[StoreListItem], int]:
    base_query = select(Store)
    if category:
        base_query = base_query.where(Store.category == category)
    if name:
        base_query = base_query.where(Store.name.ilike(f"%{name}%"))

    _total = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    total = _total if _total is not None else 0

    stores = (await db.scalars(base_query.offset((page - 1) * size).limit(size))).all()

    items: list[StoreListItem] = []
    for store in stores:
        events = await _get_store_events(db, store.id)
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
                        reward=e.reward,
                        isActive=e.is_active,
                    )
                    for e in events
                ],
                totalEventCount=len(events),
            )
        )

    return items, int(total)


async def create_store(db: AsyncSession, owner_id: str, data: StoreCreateReq) -> Store:
    store = Store(
        name=data.name,
        address=data.address,
        category=data.category,
        thumbnail_key=data.thumbnailUrl,
        description=data.description,
        owner_id=UUID(owner_id),
    )
    db.add(store)
    await db.commit()
    await db.refresh(store)
    return store


async def delete_store(db: AsyncSession, store_id: str, user_id: str) -> None:
    store = await get_store_or_404(db, store_id)
    if str(store.owner_id) != user_id:
        raise AppException(AUTH_007)
    await db.delete(store)
    await db.commit()


async def list_store_events(db: AsyncSession, store_id: str) -> list[StoreEventSummary]:
    await get_store_or_404(db, store_id)
    events = await _get_store_events(db, UUID(store_id))
    return [
        StoreEventSummary(
            id=str(e.id),
            title=e.title,
            condition=e.condition,
            reward=e.reward,
            isActive=e.is_active,
        )
        for e in events
    ]
