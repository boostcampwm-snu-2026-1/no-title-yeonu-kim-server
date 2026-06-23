from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.event.repository import EventRepository
from app.event.repository_impl import EventRepositoryImpl
from app.event.service import EventService
from app.event.service_impl import EventServiceImpl


def get_event_repository(db: AsyncSession = Depends(get_db)) -> EventRepository:
    return EventRepositoryImpl(db)


def get_event_service(
    repo: EventRepository = Depends(get_event_repository),
) -> EventService:
    return EventServiceImpl(repo)
