from collections.abc import Generator
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.review_submission import ReviewSubmission
from tests.conftest import (
    auth_headers,
    create_application,
    create_deposit,
    create_event,
    create_store,
    create_user,
)

DEPLOYED_ADDRESS = "0xDeAdBeEf00000000000000000000000000001234"


@pytest.mark.asyncio
class TestCreateEvent:
    @pytest.fixture(autouse=True)
    def mock_deploy(self) -> Generator[None, None, None]:
        with patch(
            "app.services.event.blockchain_service.deploy_contract",
            new_callable=AsyncMock,
            return_value=DEPLOYED_ADDRESS,
        ):
            yield

    async def test_owner_creates_event_returns_200(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        await create_deposit(db, owner.id, amount=10000)
        body = {
            "storeId": str(store.id),
            "title": "Summer Promo",
            "condition": "Post a photo",
            "reward": 0.01,
        }
        res = await client.post("/api/event", json=body, headers=auth_headers(owner.id))
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Summer Promo"
        assert data["reward"] == pytest.approx(0.01)
        assert data["isActive"] is True
        assert "id" in data
        assert data["contractAddress"] == DEPLOYED_ADDRESS

    async def test_event_saved_to_db(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        await create_deposit(db, owner.id, amount=10000)
        body = {
            "storeId": str(store.id),
            "title": "DB Test Event",
            "condition": "Leave a review",
            "reward": 0.003,
        }
        res = await client.post("/api/event", json=body, headers=auth_headers(owner.id))
        assert res.status_code == 200
        event_id = res.json()["id"]
        event = await db.scalar(select(Event).where(Event.id == UUID(event_id)))
        assert event is not None
        assert event.title == "DB Test Event"
        assert event.store_id == store.id
        assert event.contract_address == DEPLOYED_ADDRESS

    async def test_no_auth_returns_4xx(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        body = {"storeId": str(store.id), "title": "x", "condition": "y", "reward": 0.001}
        res = await client.post("/api/event", json=body)
        assert res.status_code in (401, 403)

    async def test_not_your_store_returns_403(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, email="o1@example.com", role="OWNER")
        other = await create_user(db, email="o2@example.com", role="OWNER")
        store = await create_store(db, other.id)
        body = {"storeId": str(store.id), "title": "x", "condition": "y", "reward": 0.001}
        res = await client.post("/api/event", json=body, headers=auth_headers(owner.id))
        assert res.status_code == 403

    async def test_store_not_found_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        body = {
            "storeId": str(uuid4()),
            "title": "x",
            "condition": "y",
            "reward": 0.001,
        }
        res = await client.post("/api/event", json=body, headers=auth_headers(owner.id))
        assert res.status_code == 404


@pytest.mark.asyncio
class TestGetOwnerEvents:
    async def test_returns_owner_events(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        await create_event(db, store.id, title="Event A")
        await create_event(db, store.id, title="Event B")
        res = await client.get("/api/event/owner", headers=auth_headers(owner.id))
        assert res.status_code == 200
        data = res.json()
        assert "events" in data
        assert len(data["events"]) == 2
        titles = {e["title"] for e in data["events"]}
        assert titles == {"Event A", "Event B"}

    async def test_only_returns_own_events(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, email="own@example.com", role="OWNER")
        other = await create_user(db, email="oth@example.com", role="OWNER")
        own_store = await create_store(db, owner.id)
        other_store = await create_store(db, other.id)
        await create_event(db, own_store.id, title="My Event")
        await create_event(db, other_store.id, title="Other Event")
        res = await client.get("/api/event/owner", headers=auth_headers(owner.id))
        assert res.status_code == 200
        data = res.json()["events"]
        assert len(data) == 1
        assert data[0]["title"] == "My Event"

    async def test_returns_empty_list_when_no_events(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        res = await client.get("/api/event/owner", headers=auth_headers(owner.id))
        assert res.status_code == 200
        assert res.json()["events"] == []

    async def test_no_auth_returns_4xx(self, client: AsyncClient) -> None:
        res = await client.get("/api/event/owner")
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestGetEvent:
    async def test_returns_event_detail(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id, title="Detail Event", reward=0.002)
        res = await client.get(f"/api/event/{event.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == str(event.id)
        assert data["title"] == "Detail Event"
        assert data["reward"] == pytest.approx(0.002)
        assert "isActive" in data

    async def test_no_auth_required(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        res = await client.get(f"/api/event/{event.id}")
        assert res.status_code == 200

    async def test_not_found_returns_404(self, client: AsyncClient) -> None:
        res = await client.get(f"/api/event/{uuid4()}")
        assert res.status_code == 404


@pytest.mark.asyncio
class TestDeleteEvent:
    async def test_owner_deletes_event(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        res = await client.delete(
            f"/api/event/{event.id}", headers=auth_headers(owner.id)
        )
        assert res.status_code == 200
        assert res.json() is None
        deleted = await db.scalar(select(Event).where(Event.id == event.id))
        assert deleted is None

    async def test_non_owner_returns_403(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        other = await create_user(db, email="other@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        res = await client.delete(
            f"/api/event/{event.id}", headers=auth_headers(other.id)
        )
        assert res.status_code == 403

    async def test_not_found_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db, role="OWNER")
        res = await client.delete(
            f"/api/event/{uuid4()}", headers=auth_headers(user.id)
        )
        assert res.status_code == 404

    async def test_no_auth_returns_4xx(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        res = await client.delete(f"/api/event/{event.id}")
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestGetEventApplications:
    async def test_returns_applications(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        reviewer = await create_user(
            db, email="rev@example.com", role="REVIEWER", username="rev_user"
        )
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        await create_application(db, event.id, reviewer.id)
        res = await client.get(
            f"/api/event/{event.id}/applications",
            headers=auth_headers(owner.id),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["totalCount"] == 1
        assert len(data["applications"]) == 1
        app_data = data["applications"][0]
        assert app_data["reviewerId"] == str(reviewer.id)
        assert app_data["reviewerName"] == "rev_user"
        assert app_data["status"] == "PENDING"
        assert app_data["hasSubmission"] is False

    async def test_has_submission_true(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        reviewer = await create_user(db, email="rev@example.com", role="REVIEWER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(db, event.id, reviewer.id)
        db.add(ReviewSubmission(application_id=application.id, message="Great place!"))
        await db.commit()
        res = await client.get(
            f"/api/event/{event.id}/applications",
            headers=auth_headers(owner.id),
        )
        assert res.status_code == 200
        assert res.json()["applications"][0]["hasSubmission"] is True

    async def test_status_filter(self, client: AsyncClient, db: AsyncSession) -> None:
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        reviewer1 = await create_user(db, email="r1@example.com", role="REVIEWER")
        reviewer2 = await create_user(db, email="r2@example.com", role="REVIEWER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        await create_application(db, event.id, reviewer1.id, status="PENDING")
        await create_application(db, event.id, reviewer2.id, status="APPROVED")
        res = await client.get(
            f"/api/event/{event.id}/applications",
            params={"status": "pending"},
            headers=auth_headers(owner.id),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["totalCount"] == 1
        assert data["applications"][0]["status"] == "PENDING"

    async def test_pagination(self, client: AsyncClient, db: AsyncSession) -> None:
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        for i in range(5):
            reviewer = await create_user(db, email=f"r{i}@example.com", role="REVIEWER")
            await create_application(db, event.id, reviewer.id)
        res = await client.get(
            f"/api/event/{event.id}/applications",
            params={"page": 1, "size": 2},
            headers=auth_headers(owner.id),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["totalCount"] == 5
        assert len(data["applications"]) == 2
        assert data["currentPage"] == 1
        assert data["totalPages"] == 3
        assert data["hasNext"] is True

    async def test_no_auth_returns_4xx(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        res = await client.get(f"/api/event/{event.id}/applications")
        assert res.status_code in (401, 403)

    async def test_non_owner_returns_403(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        other = await create_user(db, email="other@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        res = await client.get(
            f"/api/event/{event.id}/applications",
            headers=auth_headers(other.id),
        )
        assert res.status_code == 403

    async def test_event_not_found_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        res = await client.get(
            f"/api/event/{uuid4()}/applications",
            headers=auth_headers(owner.id),
        )
        assert res.status_code == 404
