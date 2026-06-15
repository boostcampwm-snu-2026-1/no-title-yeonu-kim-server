from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_login
from app.db.session import get_db
from app.schemas.common import SuccessResponse
from app.schemas.event import EventCreateReq, EventResp
from app.services import event as event_service

router = APIRouter(prefix="/event", tags=["Event"])


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
