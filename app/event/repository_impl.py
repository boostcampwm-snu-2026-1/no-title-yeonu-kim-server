from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.event.models import Event
from app.event.repository import EventRepository
from app.models.application import Application
from app.models.review_submission import ReviewSubmission
from app.models.user import User
from app.store.models import Store


class EventRepositoryImpl(EventRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_id(self, event_id: UUID) -> Event | None:
        return cast(
            Event | None,
            await self.db.scalar(select(Event).where(Event.id == event_id)),
        )

    async def find_by_owner_id(self, owner_id: UUID) -> list[Event]:
        q = (
            select(Event)
            .join(Store, Event.store_id == Store.id)
            .where(Store.owner_id == owner_id)
        )
        return list((await self.db.scalars(q)).all())

    async def find_store_by_id(self, store_id: UUID) -> Store | None:
        return cast(
            Store | None,
            await self.db.scalar(select(Store).where(Store.id == store_id)),
        )

    async def save(self, event: Event) -> Event:
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def delete(self, event: Event) -> None:
        await self.db.delete(event)
        await self.db.commit()

    async def find_applications_by_event_id(
        self,
        event_id: UUID,
        *,
        status_filter: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Application], int]:
        q = select(Application).where(Application.event_id == event_id)
        if status_filter:
            q = q.where(Application.status == status_filter.upper())
        count_q = select(func.count()).select_from(q.subquery())
        total = await self.db.scalar(count_q) or 0
        apps = list((await self.db.scalars(q.offset(offset).limit(limit))).all())
        return apps, int(total)

    async def find_user_by_id(self, user_id: UUID) -> User | None:
        return cast(
            User | None,
            await self.db.scalar(select(User).where(User.id == user_id)),
        )

    async def find_submission_by_application_id(
        self, application_id: UUID
    ) -> ReviewSubmission | None:
        return cast(
            ReviewSubmission | None,
            await self.db.scalar(
                select(ReviewSubmission).where(
                    ReviewSubmission.application_id == application_id
                )
            ),
        )
