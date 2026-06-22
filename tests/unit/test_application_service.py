"""Unit tests for app/services/application.py — AsyncSession is mocked."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import (
    APPLICATION_001,
    APPLICATION_002,
    APPLICATION_003_APPLY,
    APPLICATION_003_SUBMIT,
    EVENT_001,
    GEN_003_CLOSED,
    GEN_003_STATUS,
    GEN_005,
    AppException,
)
from app.schemas.application import ApplicationCreateReq, ReviewSubmissionReq
from app.services.application import (
    cancel_application,
    create_application,
    submit_review,
)


def _mock_event(
    *, is_active: bool = True, contract_address: str | None = None
) -> MagicMock:
    event = MagicMock()
    event.id = uuid4()
    event.store_id = uuid4()
    event.title = "Test Event"
    event.condition = "Post a photo"
    event.reward = int(0.001 * 10**18)
    event.is_active = is_active
    event.contract_address = contract_address
    return event


def _mock_application(
    *, status: str = "PENDING", reviewer_id: UUID | None = None
) -> MagicMock:
    app = MagicMock()
    app.id = uuid4()
    app.reviewer_id = reviewer_id or uuid4()
    app.event_id = uuid4()
    app.status = status
    return app


_VALID_WALLET = "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12"


@pytest.mark.asyncio
class TestCancelApplication:
    async def test_raises_application_002_when_not_found(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = None
        with pytest.raises(AppException) as exc:
            await cancel_application(db, str(uuid4()), str(uuid4()))
        assert exc.value.code == APPLICATION_002.code
        assert exc.value.status_code == 404

    async def test_raises_application_001_when_requester_is_not_reviewer(self) -> None:
        reviewer_id = uuid4()
        other_id = uuid4()
        app = _mock_application(reviewer_id=reviewer_id)
        db = AsyncMock()
        db.scalar.return_value = app
        with pytest.raises(AppException) as exc:
            await cancel_application(db, str(app.id), str(other_id))
        assert exc.value.code == APPLICATION_001.code

    async def test_raises_gen_003_status_when_application_not_pending(self) -> None:
        reviewer_id = uuid4()
        app = _mock_application(status="APPROVED", reviewer_id=reviewer_id)
        db = AsyncMock()
        db.scalar.return_value = app
        with pytest.raises(AppException) as exc:
            await cancel_application(db, str(app.id), str(reviewer_id))
        assert exc.value.code == GEN_003_STATUS.code

    async def test_deletes_application_when_owner_and_pending(self) -> None:
        reviewer_id = uuid4()
        app = _mock_application(status="PENDING", reviewer_id=reviewer_id)
        db = AsyncMock()
        db.scalar.return_value = app
        await cancel_application(db, str(app.id), str(reviewer_id))
        db.delete.assert_called_once_with(app)
        db.commit.assert_awaited_once()


@pytest.mark.asyncio
class TestSubmitReview:
    async def test_raises_application_002_when_application_not_found(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = None
        data = ReviewSubmissionReq(imageList=[], comment="x")
        with pytest.raises(AppException) as exc:
            await submit_review(db, str(uuid4()), str(uuid4()), data)
        assert exc.value.code == APPLICATION_002.code

    async def test_raises_application_001_when_requester_is_not_reviewer(self) -> None:
        reviewer_id = uuid4()
        other_id = uuid4()
        app = _mock_application(reviewer_id=reviewer_id)
        db = AsyncMock()
        db.scalar.return_value = app
        data = ReviewSubmissionReq(imageList=[], comment="x")
        with pytest.raises(AppException) as exc:
            await submit_review(db, str(app.id), str(other_id), data)
        assert exc.value.code == APPLICATION_001.code

    async def test_raises_application_003_when_submission_already_exists(self) -> None:
        reviewer_id = uuid4()
        app = _mock_application(reviewer_id=reviewer_id)
        existing = MagicMock()
        db = AsyncMock()
        db.scalar.side_effect = [app, existing]
        data = ReviewSubmissionReq(imageList=[], comment="x")
        with pytest.raises(AppException) as exc:
            await submit_review(db, str(app.id), str(reviewer_id), data)
        assert exc.value.code == APPLICATION_003_SUBMIT.code

    async def test_creates_submission_and_images(self) -> None:
        reviewer_id = uuid4()
        app = _mock_application(reviewer_id=reviewer_id)
        db = AsyncMock()
        db.scalar.side_effect = [app, None]  # app found, no existing submission
        data = ReviewSubmissionReq(imageList=["img1.jpg", "img2.jpg"], comment="Great!")
        await submit_review(db, str(app.id), str(reviewer_id), data)
        assert db.add.call_count == 3  # 1 ReviewSubmission + 2 ReviewImage
        db.flush.assert_awaited_once()
        db.commit.assert_awaited_once()

    async def test_creates_submission_with_no_images(self) -> None:
        reviewer_id = uuid4()
        app = _mock_application(reviewer_id=reviewer_id)
        db = AsyncMock()
        db.scalar.side_effect = [app, None]
        data = ReviewSubmissionReq(imageList=[], comment="Just text!")
        await submit_review(db, str(app.id), str(reviewer_id), data)
        assert db.add.call_count == 1  # only ReviewSubmission


@pytest.mark.asyncio
class TestCreateApplication:
    async def test_raises_gen_005_on_invalid_wallet_address(self) -> None:
        db = AsyncMock()
        data = ApplicationCreateReq(
            eventId=str(uuid4()),
            walletAddress="not-a-wallet",
            imageKey="img.jpg",
        )
        from fastapi import BackgroundTasks

        with pytest.raises(AppException) as exc:
            await create_application(db, str(uuid4()), data, BackgroundTasks())
        assert exc.value.code == GEN_005.code
        db.scalar.assert_not_awaited()

    async def test_raises_gen_005_on_wallet_without_0x_prefix(self) -> None:
        db = AsyncMock()
        data = ApplicationCreateReq(
            eventId=str(uuid4()),
            walletAddress="AbCdEf1234567890AbCdEf1234567890AbCdEf12",
            imageKey="img.jpg",
        )
        from fastapi import BackgroundTasks

        with pytest.raises(AppException) as exc:
            await create_application(db, str(uuid4()), data, BackgroundTasks())
        assert exc.value.code == GEN_005.code

    async def test_raises_event_001_when_event_not_found(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = None
        data = ApplicationCreateReq(
            eventId=str(uuid4()),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        from fastapi import BackgroundTasks

        with pytest.raises(AppException) as exc:
            await create_application(db, str(uuid4()), data, BackgroundTasks())
        assert exc.value.code == EVENT_001.code

    async def test_raises_gen_003_when_event_is_not_active(self) -> None:
        event = _mock_event(is_active=False)
        db = AsyncMock()
        db.scalar.return_value = event
        data = ApplicationCreateReq(
            eventId=str(event.id),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        from fastapi import BackgroundTasks

        with pytest.raises(AppException) as exc:
            await create_application(db, str(uuid4()), data, BackgroundTasks())
        assert exc.value.code == GEN_003_CLOSED.code

    async def test_raises_application_003_when_already_applied(self) -> None:
        event = _mock_event(is_active=True)
        existing = MagicMock()
        db = AsyncMock()
        db.scalar.side_effect = [event, existing]
        data = ApplicationCreateReq(
            eventId=str(event.id),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        from fastapi import BackgroundTasks

        with pytest.raises(AppException) as exc:
            await create_application(db, str(uuid4()), data, BackgroundTasks())
        assert exc.value.code == APPLICATION_003_APPLY.code

    async def test_creates_application_with_approved_status(self) -> None:
        event = _mock_event(is_active=True)
        reviewer_id = uuid4()
        db = AsyncMock()
        db.scalar.side_effect = [event, None]  # event found, no duplicate
        data = ApplicationCreateReq(
            eventId=str(event.id),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        from fastapi import BackgroundTasks

        with patch(
            "app.services.application._validate_image_condition",
            new_callable=AsyncMock,
        ):
            await create_application(db, str(reviewer_id), data, BackgroundTasks())
        added = db.add.call_args[0][0]
        assert added.status == "APPROVED"

    async def test_schedules_payout_when_contract_address_set(self) -> None:
        contract = "0xDeAdBeEf00000000000000000000000000001234"
        event = _mock_event(is_active=True, contract_address=contract)
        reviewer = MagicMock()
        reviewer.email = "rev@example.com"
        reviewer_id = uuid4()
        db = AsyncMock()
        db.scalar.side_effect = [event, None, reviewer]  # event, no dup, reviewer
        data = ApplicationCreateReq(
            eventId=str(event.id),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        from fastapi import BackgroundTasks

        bg = BackgroundTasks()
        with patch(
            "app.services.application._validate_image_condition",
            new_callable=AsyncMock,
        ):
            await create_application(db, str(reviewer_id), data, bg)
        assert len(bg.tasks) == 1

    async def test_no_payout_scheduled_when_no_contract_address(self) -> None:
        event = _mock_event(is_active=True, contract_address=None)
        reviewer_id = uuid4()
        db = AsyncMock()
        db.scalar.side_effect = [event, None]
        data = ApplicationCreateReq(
            eventId=str(event.id),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        from fastapi import BackgroundTasks

        bg = BackgroundTasks()
        with patch(
            "app.services.application._validate_image_condition",
            new_callable=AsyncMock,
        ):
            await create_application(db, str(reviewer_id), data, bg)
        assert len(bg.tasks) == 0
