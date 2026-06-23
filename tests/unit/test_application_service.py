"""Unit tests for app/application/service_impl.py."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.application.repository import ApplicationRepository
from app.application.schemas import ApplicationCreateReq, ReviewSubmissionReq
from app.application.service_impl import ApplicationServiceImpl
from app.blockchain.service import BlockchainService
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
from app.ocr.service import OCRService
from app.s3.service import S3Service


def _make_repo() -> AsyncMock:
    return AsyncMock(spec=ApplicationRepository)


def _make_blockchain() -> AsyncMock:
    return AsyncMock(spec=BlockchainService)


def _make_s3() -> AsyncMock:
    return AsyncMock(spec=S3Service)


def _make_ocr() -> AsyncMock:
    return AsyncMock(spec=OCRService)


def _mock_event(
    *, is_active: bool = True, contract_address: str | None = None
) -> MagicMock:
    event = MagicMock()
    event.id = uuid4()
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
    app.status = status
    return app


_VALID_WALLET = "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12"


@pytest.mark.asyncio
class TestCancelApplication:
    async def test_raises_application_002_when_not_found(self) -> None:
        repo = _make_repo()
        repo.find_by_id.return_value = None
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        with pytest.raises(AppException) as exc:
            await service.cancel_application(str(uuid4()), str(uuid4()))
        assert exc.value.code == APPLICATION_002.code
        assert exc.value.status_code == 404

    async def test_raises_application_001_when_requester_is_not_reviewer(self) -> None:
        reviewer_id = uuid4()
        other_id = uuid4()
        app = _mock_application(reviewer_id=reviewer_id)
        repo = _make_repo()
        repo.find_by_id.return_value = app
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        with pytest.raises(AppException) as exc:
            await service.cancel_application(str(app.id), str(other_id))
        assert exc.value.code == APPLICATION_001.code

    async def test_raises_gen_003_status_when_application_not_pending(self) -> None:
        reviewer_id = uuid4()
        app = _mock_application(status="APPROVED", reviewer_id=reviewer_id)
        repo = _make_repo()
        repo.find_by_id.return_value = app
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        with pytest.raises(AppException) as exc:
            await service.cancel_application(str(app.id), str(reviewer_id))
        assert exc.value.code == GEN_003_STATUS.code

    async def test_deletes_application_when_owner_and_pending(self) -> None:
        reviewer_id = uuid4()
        app = _mock_application(status="PENDING", reviewer_id=reviewer_id)
        repo = _make_repo()
        repo.find_by_id.return_value = app
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        await service.cancel_application(str(app.id), str(reviewer_id))
        repo.delete.assert_awaited_once_with(app)


@pytest.mark.asyncio
class TestSubmitReview:
    async def test_raises_application_002_when_application_not_found(self) -> None:
        repo = _make_repo()
        repo.find_by_id.return_value = None
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ReviewSubmissionReq(imageList=[], comment="x")
        with pytest.raises(AppException) as exc:
            await service.submit_review(str(uuid4()), str(uuid4()), data)
        assert exc.value.code == APPLICATION_002.code

    async def test_raises_application_001_when_requester_is_not_reviewer(self) -> None:
        reviewer_id = uuid4()
        other_id = uuid4()
        app = _mock_application(reviewer_id=reviewer_id)
        repo = _make_repo()
        repo.find_by_id.return_value = app
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ReviewSubmissionReq(imageList=[], comment="x")
        with pytest.raises(AppException) as exc:
            await service.submit_review(str(app.id), str(other_id), data)
        assert exc.value.code == APPLICATION_001.code

    async def test_raises_application_003_when_submission_already_exists(self) -> None:
        reviewer_id = uuid4()
        app = _mock_application(reviewer_id=reviewer_id)
        repo = _make_repo()
        repo.find_by_id.return_value = app
        repo.find_submission_by_application_id.return_value = MagicMock()
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ReviewSubmissionReq(imageList=[], comment="x")
        with pytest.raises(AppException) as exc:
            await service.submit_review(str(app.id), str(reviewer_id), data)
        assert exc.value.code == APPLICATION_003_SUBMIT.code

    async def test_calls_save_review_with_correct_args(self) -> None:
        reviewer_id = uuid4()
        app = _mock_application(reviewer_id=reviewer_id)
        repo = _make_repo()
        repo.find_by_id.return_value = app
        repo.find_submission_by_application_id.return_value = None
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ReviewSubmissionReq(imageList=["img1.jpg", "img2.jpg"], comment="Great!")
        await service.submit_review(str(app.id), str(reviewer_id), data)
        repo.save_review.assert_awaited_once()
        args = repo.save_review.call_args.args
        assert args[1] == "Great!"
        assert args[2] == ["img1.jpg", "img2.jpg"]

    async def test_calls_save_review_with_empty_images(self) -> None:
        reviewer_id = uuid4()
        app = _mock_application(reviewer_id=reviewer_id)
        repo = _make_repo()
        repo.find_by_id.return_value = app
        repo.find_submission_by_application_id.return_value = None
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ReviewSubmissionReq(imageList=[], comment="Just text!")
        await service.submit_review(str(app.id), str(reviewer_id), data)
        repo.save_review.assert_awaited_once()


@pytest.mark.asyncio
class TestCreateApplication:
    async def test_raises_gen_005_on_invalid_wallet_address(self) -> None:
        from fastapi import BackgroundTasks

        repo = _make_repo()
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ApplicationCreateReq(
            eventId=str(uuid4()),
            walletAddress="not-a-wallet",
            imageKey="img.jpg",
        )
        with pytest.raises(AppException) as exc:
            await service.create_application(str(uuid4()), data, BackgroundTasks())
        assert exc.value.code == GEN_005.code
        repo.find_event_by_id.assert_not_awaited()

    async def test_raises_gen_005_on_wallet_without_0x_prefix(self) -> None:
        from fastapi import BackgroundTasks

        repo = _make_repo()
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ApplicationCreateReq(
            eventId=str(uuid4()),
            walletAddress="AbCdEf1234567890AbCdEf1234567890AbCdEf12",
            imageKey="img.jpg",
        )
        with pytest.raises(AppException) as exc:
            await service.create_application(str(uuid4()), data, BackgroundTasks())
        assert exc.value.code == GEN_005.code

    async def test_raises_event_001_when_event_not_found(self) -> None:
        from fastapi import BackgroundTasks

        repo = _make_repo()
        repo.find_event_by_id.return_value = None
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ApplicationCreateReq(
            eventId=str(uuid4()),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        with pytest.raises(AppException) as exc:
            await service.create_application(str(uuid4()), data, BackgroundTasks())
        assert exc.value.code == EVENT_001.code

    async def test_raises_gen_003_when_event_is_not_active(self) -> None:
        from fastapi import BackgroundTasks

        event = _mock_event(is_active=False)
        repo = _make_repo()
        repo.find_event_by_id.return_value = event
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ApplicationCreateReq(
            eventId=str(event.id),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        with pytest.raises(AppException) as exc:
            await service.create_application(str(uuid4()), data, BackgroundTasks())
        assert exc.value.code == GEN_003_CLOSED.code

    async def test_raises_application_003_when_already_applied(self) -> None:
        from fastapi import BackgroundTasks

        event = _mock_event(is_active=True)
        repo = _make_repo()
        repo.find_event_by_id.return_value = event
        repo.find_by_event_and_reviewer.return_value = MagicMock()
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ApplicationCreateReq(
            eventId=str(event.id),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        with pytest.raises(AppException) as exc:
            await service.create_application(str(uuid4()), data, BackgroundTasks())
        assert exc.value.code == APPLICATION_003_APPLY.code

    async def test_creates_application_with_approved_status(self) -> None:
        from fastapi import BackgroundTasks

        event = _mock_event(is_active=True)
        repo = _make_repo()
        repo.find_event_by_id.return_value = event
        repo.find_by_event_and_reviewer.return_value = None
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ApplicationCreateReq(
            eventId=str(event.id),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        with patch.object(
            ApplicationServiceImpl, "_validate_image_condition", new_callable=AsyncMock
        ):
            await service.create_application(str(uuid4()), data, BackgroundTasks())
        repo.save_application.assert_awaited_once()
        saved = repo.save_application.call_args.args[0]
        assert saved.status == "APPROVED"

    async def test_schedules_payout_when_contract_address_set(self) -> None:
        from fastapi import BackgroundTasks

        contract = "0xDeAdBeEf00000000000000000000000000001234"
        event = _mock_event(is_active=True, contract_address=contract)
        reviewer = MagicMock()
        reviewer.email = "rev@example.com"
        reviewer_id = uuid4()
        repo = _make_repo()
        repo.find_event_by_id.return_value = event
        repo.find_by_event_and_reviewer.return_value = None
        repo.find_user_by_id.return_value = reviewer
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ApplicationCreateReq(
            eventId=str(event.id),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        bg = BackgroundTasks()
        with patch.object(
            ApplicationServiceImpl, "_validate_image_condition", new_callable=AsyncMock
        ):
            await service.create_application(str(reviewer_id), data, bg)
        assert len(bg.tasks) == 1

    async def test_no_payout_scheduled_when_no_contract_address(self) -> None:
        from fastapi import BackgroundTasks

        event = _mock_event(is_active=True, contract_address=None)
        reviewer_id = uuid4()
        repo = _make_repo()
        repo.find_event_by_id.return_value = event
        repo.find_by_event_and_reviewer.return_value = None
        service = ApplicationServiceImpl(
            repo, _make_blockchain(), _make_s3(), _make_ocr()
        )
        data = ApplicationCreateReq(
            eventId=str(event.id),
            walletAddress=_VALID_WALLET,
            imageKey="img.jpg",
        )
        bg = BackgroundTasks()
        with patch.object(
            ApplicationServiceImpl, "_validate_image_condition", new_callable=AsyncMock
        ):
            await service.create_application(str(reviewer_id), data, bg)
        assert len(bg.tasks) == 0
