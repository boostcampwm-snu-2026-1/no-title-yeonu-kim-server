from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import require_login
from app.event.dependencies import get_event_service
from app.event.schemas import (
    EventApplicationsResp,
    EventCreateReq,
    EventListResp,
    EventResp,
)
from app.event.service import EventService

router = APIRouter(prefix="/event", tags=["Event"])


@router.get("/owner", response_model=EventListResp)
async def get_owner_events(
    owner_id: str = Depends(require_login),
    service: EventService = Depends(get_event_service),
) -> EventListResp:
    events = await service.list_owner_events(owner_id)
    return EventListResp(
        events=[
            EventResp(
                id=str(e.id),
                title=e.title,
                condition=e.condition,
                reward=e.reward / 10**18,
                isActive=e.is_active,
                contractAddress=e.contract_address,
            )
            for e in events
        ]
    )


@router.post("", response_model=EventResp)
async def create_event(
    body: EventCreateReq,
    owner_id: str = Depends(require_login),
    service: EventService = Depends(get_event_service),
) -> EventResp:
    event = await service.create_event(owner_id, body)
    return EventResp(
        id=str(event.id),
        title=event.title,
        condition=event.condition,
        reward=event.reward / 10**18,
        isActive=event.is_active,
        contractAddress=event.contract_address,
    )


@router.get("/{eventId}", response_model=EventResp)
async def get_event(
    eventId: str,
    service: EventService = Depends(get_event_service),
) -> EventResp:
    event = await service.get_event(eventId)
    return EventResp(
        id=str(event.id),
        title=event.title,
        condition=event.condition,
        reward=event.reward / 10**18,
        isActive=event.is_active,
        contractAddress=event.contract_address,
    )


@router.delete("/{eventId}", response_model=None)
async def delete_event(
    eventId: str,
    owner_id: str = Depends(require_login),
    service: EventService = Depends(get_event_service),
) -> None:
    await service.delete_event(eventId, owner_id)


@router.get("/{eventId}/applications", response_model=EventApplicationsResp)
async def get_event_applications(
    eventId: str,
    status: str | None = Query(default=None),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
    owner_id: str = Depends(require_login),
    service: EventService = Depends(get_event_service),
) -> EventApplicationsResp:
    applications, total = await service.list_event_applications(
        eventId,
        owner_id,
        status_filter=status,
        page=page,
        size=size,
    )
    total_pages = max(1, (total + size - 1) // size)
    return EventApplicationsResp(
        applications=applications,
        totalCount=total,
        currentPage=page,
        totalPages=total_pages,
        hasNext=(page + 1) < total_pages,
    )
