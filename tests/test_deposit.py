import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from tests.conftest import auth_headers, create_user


@pytest.mark.asyncio
class TestDeposit:
    async def test_deposit_returns_balance_and_deposited_at(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db)
        res = await client.post(
            "/api/deposit",
            json={"amount": 5000},
            headers=auth_headers(user.id),
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["balance"] == 5000
        assert "depositedAt" in data

    async def test_deposit_accumulates_balance(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db)
        await client.post(
            "/api/deposit",
            json={"amount": 3000},
            headers=auth_headers(user.id),
        )
        res = await client.post(
            "/api/deposit",
            json={"amount": 2000},
            headers=auth_headers(user.id),
        )
        assert res.status_code == 200
        assert res.json()["data"]["balance"] == 5000

    async def test_deposit_saved_to_db(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db)
        await client.post(
            "/api/deposit",
            json={"amount": 10000},
            headers=auth_headers(user.id),
        )
        saved = await db.scalar(
            select(Deposit).where(Deposit.user_id == user.id)
        )
        assert saved is not None
        assert saved.amount == 10000
        assert saved.balance == 10000

    async def test_each_deposit_creates_a_record(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db)
        await client.post(
            "/api/deposit", json={"amount": 1000}, headers=auth_headers(user.id)
        )
        await client.post(
            "/api/deposit", json={"amount": 2000}, headers=auth_headers(user.id)
        )
        records = (
            await db.scalars(select(Deposit).where(Deposit.user_id == user.id))
        ).all()
        assert len(records) == 2
        amounts = {r.amount for r in records}
        assert amounts == {1000, 2000}

    async def test_no_auth_returns_4xx(self, client: AsyncClient) -> None:
        res = await client.post("/api/deposit", json={"amount": 1000})
        assert res.status_code in (401, 403)
