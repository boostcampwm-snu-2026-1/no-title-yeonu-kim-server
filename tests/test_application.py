from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.review_image import ReviewImage
from app.models.review_submission import ReviewSubmission
from tests.conftest import (
    auth_headers,
    create_application,
    create_event,
    create_store,
    create_user,
)


@pytest.mark.asyncio
class TestCreateApplication:
    async def test_reviewer_creates_application_returns_200(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        body = {
            "eventId": str(event.id),
            "walletAddress": "0xABCDEF1234567890",
            "imageKey": "reviews/apply.jpg",
        }
        res = await client.post(
            "/api/applications", json=body, headers=auth_headers(reviewer.id)
        )
        assert res.status_code == 200
        assert res.json() == {"status": 200, "data": None}

    async def test_application_saved_to_db(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        body = {
            "eventId": str(event.id),
            "walletAddress": "0xABC",
            "imageKey": "reviews/img.jpg",
        }
        await client.post(
            "/api/applications", json=body, headers=auth_headers(reviewer.id)
        )
        saved = await db.scalar(
            select(Application).where(
                Application.event_id == event.id,
                Application.reviewer_id == reviewer.id,
            )
        )
        assert saved is not None
        assert saved.wallet_address == "0xABC"
        assert saved.status == "PENDING"

    async def test_duplicate_application_returns_409(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        await create_application(db, event.id, reviewer.id)
        body = {
            "eventId": str(event.id),
            "walletAddress": "0xABC",
            "imageKey": "reviews/img.jpg",
        }
        res = await client.post(
            "/api/applications", json=body, headers=auth_headers(reviewer.id)
        )
        assert res.status_code == 409

    async def test_event_not_found_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        body = {
            "eventId": str(uuid4()),
            "walletAddress": "0xABC",
            "imageKey": "reviews/img.jpg",
        }
        res = await client.post(
            "/api/applications", json=body, headers=auth_headers(reviewer.id)
        )
        assert res.status_code == 404

    async def test_no_auth_returns_4xx(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        owner = await create_user(db, role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        body = {
            "eventId": str(event.id),
            "walletAddress": "0xABC",
            "imageKey": "reviews/img.jpg",
        }
        res = await client.post("/api/applications", json=body)
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestGetMyApplications:
    async def test_returns_my_applications(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        await create_application(db, event.id, reviewer.id)
        res = await client.get("/api/application", headers=auth_headers(reviewer.id))
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["totalCount"] == 1
        assert len(data["applications"]) == 1
        app_data = data["applications"][0]
        assert app_data["eventId"] == str(event.id)
        assert app_data["status"] == "PENDING"
        assert app_data["reviewSubmission"] is None
        assert "appliedAt" in app_data

    async def test_only_returns_own_applications(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer1 = await create_user(db, email="r1@example.com", role="REVIEWER")
        reviewer2 = await create_user(db, email="r2@example.com", role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event1 = await create_event(db, store.id, title="Event 1")
        event2 = await create_event(db, store.id, title="Event 2")
        await create_application(db, event1.id, reviewer1.id)
        await create_application(db, event2.id, reviewer2.id)
        res = await client.get("/api/application", headers=auth_headers(reviewer1.id))
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["totalCount"] == 1
        assert data["applications"][0]["eventId"] == str(event1.id)

    async def test_submission_included_in_response(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(db, event.id, reviewer.id)
        submission = ReviewSubmission(
            application_id=application.id, message="Great place!"
        )
        db.add(submission)
        await db.flush()
        db.add(
            ReviewImage(submission_id=submission.id, image_key="reviews/a.jpg", order=0)
        )
        db.add(
            ReviewImage(submission_id=submission.id, image_key="reviews/b.jpg", order=1)
        )
        await db.commit()

        res = await client.get("/api/application", headers=auth_headers(reviewer.id))
        assert res.status_code == 200
        app_data = res.json()["data"]["applications"][0]
        assert app_data["reviewSubmission"] is not None
        sub = app_data["reviewSubmission"]
        assert sub["message"] == "Great place!"
        assert len(sub["reviewImages"]) == 2
        assert "reviews/a.jpg" in sub["reviewImages"]

    async def test_returns_empty_when_no_applications(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        res = await client.get("/api/application", headers=auth_headers(reviewer.id))
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["totalCount"] == 0
        assert data["applications"] == []

    async def test_pagination(self, client: AsyncClient, db: AsyncSession) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        for i in range(5):
            event = await create_event(db, store.id, title=f"Event {i}")
            await create_application(db, event.id, reviewer.id)
        res = await client.get(
            "/api/application",
            params={"page": 1, "size": 2},
            headers=auth_headers(reviewer.id),
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["totalCount"] == 5
        assert len(data["applications"]) == 2
        assert data["currentPage"] == 1
        assert data["totalPages"] == 3
        assert data["hasNext"] is True

    async def test_no_auth_returns_4xx(self, client: AsyncClient) -> None:
        res = await client.get("/api/application")
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestCancelApplication:
    async def test_cancel_pending_application_returns_200(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(db, event.id, reviewer.id)
        res = await client.delete(
            f"/api/application/{application.id}",
            headers=auth_headers(reviewer.id),
        )
        assert res.status_code == 200
        assert res.json() == {"status": 200, "data": None}
        deleted = await db.scalar(
            select(Application).where(Application.id == application.id)
        )
        assert deleted is None

    async def test_cancel_non_pending_returns_400(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(
            db, event.id, reviewer.id, status="APPROVED"
        )
        res = await client.delete(
            f"/api/application/{application.id}",
            headers=auth_headers(reviewer.id),
        )
        assert res.status_code == 400

    async def test_cancel_not_own_returns_403(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, email="rev@example.com", role="REVIEWER")
        other = await create_user(db, email="other@example.com", role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(db, event.id, reviewer.id)
        res = await client.delete(
            f"/api/application/{application.id}",
            headers=auth_headers(other.id),
        )
        assert res.status_code == 403

    async def test_not_found_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db, role="REVIEWER")
        res = await client.delete(
            f"/api/application/{uuid4()}",
            headers=auth_headers(user.id),
        )
        assert res.status_code == 404

    async def test_no_auth_returns_4xx(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(db, event.id, reviewer.id)
        res = await client.delete(f"/api/application/{application.id}")
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestSubmitReview:
    async def test_submit_review_returns_200(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(db, event.id, reviewer.id)
        body = {"imageList": ["reviews/a.jpg", "reviews/b.jpg"], "comment": "Great!"}
        res = await client.post(
            f"/api/application/{application.id}/submission",
            json=body,
            headers=auth_headers(reviewer.id),
        )
        assert res.status_code == 200
        assert res.json() == {"status": 200, "data": None}

    async def test_submission_saved_to_db(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(db, event.id, reviewer.id)
        body = {"imageList": ["reviews/x.jpg"], "comment": "Nice!"}
        await client.post(
            f"/api/application/{application.id}/submission",
            json=body,
            headers=auth_headers(reviewer.id),
        )
        submission = await db.scalar(
            select(ReviewSubmission).where(
                ReviewSubmission.application_id == application.id
            )
        )
        assert submission is not None
        assert submission.message == "Nice!"
        images = (
            await db.scalars(
                select(ReviewImage).where(ReviewImage.submission_id == submission.id)
            )
        ).all()
        assert len(images) == 1
        assert images[0].image_key == "reviews/x.jpg"

    async def test_duplicate_submission_returns_409(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(db, event.id, reviewer.id)
        db.add(ReviewSubmission(application_id=application.id, message="First!"))
        await db.commit()
        body = {"imageList": [], "comment": "Second!"}
        res = await client.post(
            f"/api/application/{application.id}/submission",
            json=body,
            headers=auth_headers(reviewer.id),
        )
        assert res.status_code == 409

    async def test_not_own_returns_403(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, email="rev@example.com", role="REVIEWER")
        other = await create_user(db, email="other@example.com", role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(db, event.id, reviewer.id)
        body = {"imageList": [], "comment": "Hacked!"}
        res = await client.post(
            f"/api/application/{application.id}/submission",
            json=body,
            headers=auth_headers(other.id),
        )
        assert res.status_code == 403

    async def test_not_found_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db, role="REVIEWER")
        body = {"imageList": [], "comment": "X"}
        res = await client.post(
            f"/api/application/{uuid4()}/submission",
            json=body,
            headers=auth_headers(user.id),
        )
        assert res.status_code == 404

    async def test_no_auth_returns_4xx(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        reviewer = await create_user(db, role="REVIEWER")
        owner = await create_user(db, email="owner@example.com", role="OWNER")
        store = await create_store(db, owner.id)
        event = await create_event(db, store.id)
        application = await create_application(db, event.id, reviewer.id)
        body = {"imageList": [], "comment": "X"}
        res = await client.post(
            f"/api/application/{application.id}/submission", json=body
        )
        assert res.status_code in (401, 403)
