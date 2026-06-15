from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_login
from app.db.session import get_db
from app.schemas.common import SuccessResponse
from app.schemas.deposit import DepositReq, DepositResp
from app.services import deposit as deposit_service

router = APIRouter(prefix="/deposit", tags=["Deposit"])


@router.post("", response_model=SuccessResponse[DepositResp])
async def create_deposit(
    body: DepositReq,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_login),
) -> SuccessResponse[DepositResp]:
    result = await deposit_service.create_deposit(db, user_id, body)
    return SuccessResponse(data=result)
