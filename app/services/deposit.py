from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.schemas.deposit import DepositReq, DepositResp


async def create_deposit(
    db: AsyncSession, user_id: str, data: DepositReq
) -> DepositResp:
    current_balance = await db.scalar(
        select(func.coalesce(func.max(Deposit.balance), 0)).where(
            Deposit.user_id == UUID(user_id)
        )
    )
    new_balance = (current_balance or 0) + data.amount

    deposit = Deposit(
        user_id=UUID(user_id),
        amount=data.amount,
        balance=new_balance,
    )
    db.add(deposit)
    await db.commit()
    await db.refresh(deposit)

    return DepositResp(
        balance=deposit.balance,
        depositedAt=deposit.deposited_at.isoformat(),
    )
