from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import EmailCheckReq
from app.schemas.common import SuccessResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/email", response_model=SuccessResponse[None])
async def check_email(
    body: EmailCheckReq,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[None]:
    await auth_service.check_email_duplicate(db, body.email)
    return SuccessResponse(data=None)
