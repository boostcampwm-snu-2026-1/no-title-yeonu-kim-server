from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_login
from app.db.session import get_db
from app.schemas.common import SuccessResponse
from app.schemas.event import (
    EventApplicationsResp,
    EventCreateReq,
    EventListResp,
    EventResp,
)
from app.services import event as event_service

router = APIRouter(prefix="/event", tags=["Event"])


@router.get("/owner", response_model=SuccessResponse[EventListResp])
async def get_owner_events(
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(require_login),
) -> SuccessResponse[EventListResp]:
    events = await event_service.list_owner_events(db, owner_id)
    return SuccessResponse(
        data=EventListResp(
            events=[
                EventResp(
                    id=str(e.id),
                    title=e.title,
                    condition=e.condition,
                    reward=e.reward,
                    isActive=e.is_active,
                )
                for e in events
            ]
        )
    )


@router.get("/{eventId}", response_model=SuccessResponse[EventResp])
async def get_event(
    eventId: str,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[EventResp]:
    event = await event_service.get_event_or_404(db, eventId)
    return SuccessResponse(
        data=EventResp(
            id=str(event.id),
            title=event.title,
            condition=event.condition,
            reward=event.reward,
            isActive=event.is_active,
        )
    )


@router.get(
    "/{eventId}/applications", response_model=SuccessResponse[EventApplicationsResp]
)
async def get_event_applications(
    eventId: str,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1),
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(require_login),
) -> SuccessResponse[EventApplicationsResp]:
    applications, total = await event_service.list_event_applications(
        db, eventId, owner_id, status, page, size
    )
    total_pages = max(1, (total + size - 1) // size)
    return SuccessResponse(
        data=EventApplicationsResp(
            applications=applications,
            totalCount=total,
            currentPage=page,
            totalPages=total_pages,
            hasNext=page < total_pages,
        )
    )


@router.delete("/{eventId}", response_model=SuccessResponse[None])
async def delete_event(
    eventId: str,
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(require_login),
) -> SuccessResponse[None]:
    await event_service.delete_event(db, eventId, owner_id)
    return SuccessResponse(data=None)


@router.post("", response_model=SuccessResponse[EventResp])
async def create_event(
    body: EventCreateReq,
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(require_login),
) -> SuccessResponse[EventResp]:
    event = await event_service.create_event(db, owner_id, body)
    return SuccessResponse(
        data=EventResp(
            id=str(event.id),
            title=event.title,
            condition=event.condition,
            reward=event.reward,
            isActive=event.is_active,
        )
    )
