from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from tests.conftest import (
    auth_headers,
    create_event,
    create_store,
    create_user,
)


@pytest.mark.asyncio
class TestListStores:
    async def test_returns_empty_list(self, client: AsyncClient) -> None:
        res = await client.get("/api/store")
        assert res.status_code == 200
        data = res.json()
        assert data["stores"] == []
        assert data["totalCount"] == 0
        assert data["currentPage"] == 0
        assert data["totalPages"] == 1
        assert data["hasNext"] is False

    async def test_returns_stores(self, client: AsyncClient, db: AsyncSession) -> None:
        owner = await create_user(db, role="OWNER")
        await create_store(db, owner.id, name="Store A")
        await create_store(db, owner.id, name="Store B")
        res = await client.get("/api/store")
        assert res.status_code == 200
        data = res.json()
        assert data["totalCount"] == 2
        names = {s["name"] for s in data["stores"]}
        assert names == {"Store A", "Store B"}

    async def test_category_filter(self, client: AsyncClient, db: AsyncSession) -> None:
        owner = await create_user(db, role="OWNER")
        await create_store(db, owner.id, name="Ramen", category="RESTAURANT")
        await create_store(db, owner.id, name="Brew", category="CAFE")
        res = await client.get("/api/store", params={"category": "CAFE"})
        assert res.status_code == 200
        data = res.json()
        assert data["totalCount"] == 1
        assert data["stores"][0]["name"] == "Brew"

    async def test_name_filter(self, client: AsyncClient, db: AsyncSession) -> None:
        owner = await create_user(db, role="OWNER")
        await create_store(db, owner.id, name="Pizza Palace")
        await create_store(db, owner.id, name="Burger Barn")
        res = await client.get("/api/store", params={"name": "pizza"})
        assert res.status_code == 200
        data = res.json()
        assert data["totalCount"] == 1
        assert data["stores"][0]["name"] == "Pizza Palace"

    async def test_pagination(self, client: AsyncClient, db: AsyncSession) -> None:
        owner = await create_user(db, role="OWNER")
        for i in range(5):
            await create_store(db, owner.id, name=f"Store {i}")
        res = await client.get("/api/store", params={"page": 1, "size": 2})
        assert res.status_code == 200
        data = res.json()
        assert data["totalCount"] == 5
        assert len(data["stores"]) == 2
        assert data["totalPages"] == 3
        assert data["hasNext"] is True

    async def test_includes_events(self, client: AsyncClient, db: AsyncSession) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        await create_event(db, store.id, title="Event X", reward=0.001)
        await create_event(db, store.id, title="Event Y", reward=0.002)
        res = await client.get("/api/store")
        assert res.status_code == 200
        store_data = res.json()["stores"][0]
        assert store_data["totalEventCount"] == 2
        assert len(store_data["events"]) == 2
        titles = {e["title"] for e in store_data["events"]}
        assert titles == {"Event X", "Event Y"}

    async def test_no_auth_required(self, client: AsyncClient) -> None:
        res = await client.get("/api/store")
        assert res.status_code == 200


@pytest.mark.asyncio
class TestCreateStore:
    async def test_owner_creates_store_returns_200(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        body = {
            "name": "My Cafe",
            "address": "Seoul, Korea",
            "category": "CAFE",
            "description": "A cozy cafe",
        }
        res = await client.post("/api/store", json=body, headers=auth_headers(owner.id))
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "My Cafe"
        assert data["address"] == "Seoul, Korea"
        assert data["category"] == "CAFE"
        assert data["description"] == "A cozy cafe"
        assert data["thumbnailKey"] is None
        assert "id" in data

    async def test_creates_store_with_thumbnail(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        body = {
            "name": "Photo Store",
            "address": "Busan",
            "category": "FASHION",
            "thumbnailUrl": "stores/thumb.jpg",
        }
        res = await client.post("/api/store", json=body, headers=auth_headers(owner.id))
        assert res.status_code == 200
        assert res.json()["thumbnailKey"] == "stores/thumb.jpg"

    async def test_store_saved_to_db(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        body = {"name": "DB Store", "address": "Incheon", "category": "ETC"}
        res = await client.post("/api/store", json=body, headers=auth_headers(owner.id))
        assert res.status_code == 200
        from uuid import UUID

        store_id = UUID(res.json()["id"])
        store = await db.scalar(select(Store).where(Store.id == store_id))
        assert store is not None
        assert store.name == "DB Store"
        assert store.owner_id == owner.id

    async def test_no_auth_returns_4xx(self, client: AsyncClient) -> None:
        body = {"name": "x", "address": "y", "category": "ETC"}
        res = await client.post("/api/store", json=body)
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestGetStore:
    async def test_returns_store_detail(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id, name="Detail Store", address="Seoul")
        res = await client.get(f"/api/store/{store.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == str(store.id)
        assert data["name"] == "Detail Store"
        assert data["address"] == "Seoul"

    async def test_no_auth_required(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        res = await client.get(f"/api/store/{store.id}")
        assert res.status_code == 200

    async def test_not_found_returns_404(self, client: AsyncClient) -> None:
        res = await client.get(f"/api/store/{uuid4()}")
        assert res.status_code == 404


@pytest.mark.asyncio
class TestDeleteStore:
    async def test_owner_deletes_store(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        res = await client.delete(
            f"/api/store/{store.id}", headers=auth_headers(owner.id)
        )
        assert res.status_code == 200
        assert res.json() is None
        deleted = await db.scalar(select(Store).where(Store.id == store.id))
        assert deleted is None

    async def test_non_owner_returns_403(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        other = await create_user(db, email="other@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        res = await client.delete(
            f"/api/store/{store.id}", headers=auth_headers(other.id)
        )
        assert res.status_code == 403

    async def test_not_found_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db, role="OWNER")
        res = await client.delete(
            f"/api/store/{uuid4()}", headers=auth_headers(user.id)
        )
        assert res.status_code == 404

    async def test_no_auth_returns_4xx(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        res = await client.delete(f"/api/store/{store.id}")
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestGetStoreEvents:
    async def test_returns_store_events(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        await create_event(db, store.id, title="Event A")
        await create_event(db, store.id, title="Event B")
        res = await client.get(f"/api/store/{store.id}/events")
        assert res.status_code == 200
        data = res.json()
        assert "events" in data
        assert len(data["events"]) == 2
        titles = {e["title"] for e in data["events"]}
        assert titles == {"Event A", "Event B"}

    async def test_event_fields(self, client: AsyncClient, db: AsyncSession) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        await create_event(db, store.id, title="Check Fields", reward=0.009)
        res = await client.get(f"/api/store/{store.id}/events")
        assert res.status_code == 200
        event = res.json()["events"][0]
        assert "id" in event
        assert event["title"] == "Check Fields"
        assert event["reward"] == pytest.approx(0.009)
        assert event["isActive"] is True
        assert "condition" in event

    async def test_returns_empty_when_no_events(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        res = await client.get(f"/api/store/{store.id}/events")
        assert res.status_code == 200
        assert res.json()["events"] == []

    async def test_store_not_found_returns_404(self, client: AsyncClient) -> None:
        res = await client.get(f"/api/store/{uuid4()}/events")
        assert res.status_code == 404

    async def test_no_auth_required(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        res = await client.get(f"/api/store/{store.id}/events")
        assert res.status_code == 200
