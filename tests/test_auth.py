import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
