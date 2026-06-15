import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_verification import EmailVerification
from tests.conftest import create_user


@pytest.mark.asyncio
class TestCheckEmail:
    async def test_available_email_returns_200(self, client: AsyncClient) -> None:
        res = await client.post("/api/auth/email", json={"email": "new@example.com"})
        assert res.status_code == 200
        assert res.json()["status"] == 200

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_user(db, email="taken@example.com")
        res = await client.post("/api/auth/email", json={"email": "taken@example.com"})
        assert res.status_code == 409
        assert res.json()["status"] == 409


@pytest.mark.asyncio
class TestEmailVerify:
    async def test_creates_verification_record(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        res = await client.post(
            "/api/auth/email/verify", json={"email": "user@example.com"}
        )
        assert res.status_code == 200

        record = await db.scalar(
            select(EmailVerification).where(
                EmailVerification.email == "user@example.com"
            )
        )
        assert record is not None
        assert len(record.code) == 6
        assert record.code.isdigit()
        assert record.is_verified is False

    async def test_response_format(self, client: AsyncClient) -> None:
        res = await client.post(
            "/api/auth/email/verify", json={"email": "user@example.com"}
        )
        assert res.json() == {"status": 200, "data": None}
