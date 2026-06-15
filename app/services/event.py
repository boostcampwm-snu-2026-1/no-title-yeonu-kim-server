from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AUTH_007,
    DEPOSIT_001,
    EVENT_001,
    STORE_001,
    AppException,
)
from app.models.application import Application
from app.models.deposit import Deposit
from app.models.event import Event
from app.models.review_submission import ReviewSubmission
from app.models.store import Store
from app.models.user import User
from app.schemas.event import ApplicationSummary, EventCreateReq


async def _get_store_or_404(db: AsyncSession, store_id: str) -> Store:
    store = await db.scalar(select(Store).where(Store.id == UUID(store_id)))
    if not store:
        raise AppException(STORE_001)
    return store


async def list_owner_events(db: AsyncSession, owner_id: str) -> list[Event]:
    result = await db.scalars(
        select(Event)
        .join(Store, Event.store_id == Store.id)
        .where(Store.owner_id == UUID(owner_id))
    )
    return list(result.all())


async def get_event_or_404(db: AsyncSession, event_id: str) -> Event:
    event = await db.scalar(select(Event).where(Event.id == UUID(event_id)))
    if not event:
        raise AppException(EVENT_001)
    return event


async def delete_event(db: AsyncSession, event_id: str, owner_id: str) -> None:
    event = await get_event_or_404(db, event_id)
    store = await db.scalar(select(Store).where(Store.id == event.store_id))
    if not store or str(store.owner_id) != owner_id:
        raise AppException(AUTH_007)
    await db.delete(event)
    await db.commit()


async def list_event_applications(
    db: AsyncSession,
    event_id: str,
    owner_id: str,
    status_filter: str | None,
    page: int,
    size: int,
) -> tuple[list[ApplicationSummary], int]:
    event = await get_event_or_404(db, event_id)
    store = await db.scalar(select(Store).where(Store.id == event.store_id))
    if not store or str(store.owner_id) != owner_id:
        raise AppException(AUTH_007)

    base_query = select(Application).where(Application.event_id == UUID(event_id))
    if status_filter:
        base_query = base_query.where(Application.status == status_filter.upper())

    _total = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    total = _total if _total is not None else 0

    apps = (await db.scalars(base_query.offset((page - 1) * size).limit(size))).all()

    result: list[ApplicationSummary] = []
    for app in apps:
        reviewer = await db.scalar(select(User).where(User.id == app.reviewer_id))
        has_submission = bool(
            await db.scalar(
                select(ReviewSubmission).where(
                    ReviewSubmission.application_id == app.id
                )
            )
        )
        result.append(
            ApplicationSummary(
                id=str(app.id),
                reviewerId=str(app.reviewer_id),
                reviewerName=reviewer.username if reviewer else "",
                status=app.status,
                appliedAt=app.applied_at.isoformat(),
                hasSubmission=has_submission,
            )
        )

    return result, int(total)


async def create_event(db: AsyncSession, owner_id: str, data: EventCreateReq) -> Event:
    store = await _get_store_or_404(db, data.storeId)
    if str(store.owner_id) != owner_id:
        raise AppException(AUTH_007)

    _balance = await db.scalar(
        select(func.coalesce(func.max(Deposit.balance), 0)).where(
            Deposit.user_id == UUID(owner_id)
        )
    )
    balance = int(_balance) if _balance is not None else 0
    if data.reward > balance:
        raise AppException(DEPOSIT_001)

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
