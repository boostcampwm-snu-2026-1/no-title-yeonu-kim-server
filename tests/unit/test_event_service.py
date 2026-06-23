"""Unit tests for app/event/service_impl.py.

EventRepository and blockchain are mocked.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import AUTH_007, EVENT_001, STORE_001, AppException
from app.event.schemas import EventCreateReq
from app.event.service_impl import EventServiceImpl


def _mock_repo() -> AsyncMock:
    return AsyncMock()


def _mock_store(owner_id: object = None) -> MagicMock:
    store = MagicMock()
    store.id = uuid4()
    store.owner_id = owner_id or uuid4()
    return store


def _mock_event(store_id: object = None) -> MagicMock:
    event = MagicMock()
    event.id = uuid4()
    event.store_id = store_id or uuid4()
    event.title = "Test Event"
    event.condition = "Post photo"
    event.reward = int(0.001 * 10**18)
    event.is_active = True
    event.contract_address = None
    return event


def _mock_application(event_id: object = None, reviewer_id: object = None) -> MagicMock:
    app = MagicMock()
    app.id = uuid4()
    app.event_id = event_id or uuid4()
    app.reviewer_id = reviewer_id or uuid4()
    app.status = "PENDING"
    app.applied_at = datetime.now(UTC)
    return app


@pytest.mark.asyncio
class TestGetEvent:
    async def test_raises_event_001_when_not_found(self) -> None:
        repo = _mock_repo()
        repo.find_by_id.return_value = None
        service = EventServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await service.get_event(str(uuid4()))
        assert exc.value.code == EVENT_001.code
        assert exc.value.status_code == 404

    async def test_returns_event_when_found(self) -> None:
        event = _mock_event()
        repo = _mock_repo()
        repo.find_by_id.return_value = event
        service = EventServiceImpl(repo)
        result = await service.get_event(str(event.id))
        assert result is event


@pytest.mark.asyncio
class TestListOwnerEvents:
    async def test_returns_events_belonging_to_owner(self) -> None:
        owner_id = uuid4()
        events = [_mock_event() for _ in range(2)]
        repo = _mock_repo()
        repo.find_by_owner_id.return_value = events
        service = EventServiceImpl(repo)
        result = await service.list_owner_events(str(owner_id))
        assert result == events

    async def test_returns_empty_list_when_no_events(self) -> None:
        repo = _mock_repo()
        repo.find_by_owner_id.return_value = []
        service = EventServiceImpl(repo)
        result = await service.list_owner_events(str(uuid4()))
        assert result == []


@pytest.mark.asyncio
class TestDeleteEvent:
    async def test_raises_event_001_when_event_not_found(self) -> None:
        repo = _mock_repo()
        repo.find_by_id.return_value = None
        service = EventServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await service.delete_event(str(uuid4()), str(uuid4()))
        assert exc.value.code == EVENT_001.code

    async def test_raises_auth_007_when_store_not_found(self) -> None:
        event = _mock_event()
        repo = _mock_repo()
        repo.find_by_id.return_value = event
        repo.find_store_by_id.return_value = None
        service = EventServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await service.delete_event(str(event.id), str(uuid4()))
        assert exc.value.code == AUTH_007.code

    async def test_raises_auth_007_when_requester_is_not_owner(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        event = _mock_event(store_id=store.id)
        repo = _mock_repo()
        repo.find_by_id.return_value = event
        repo.find_store_by_id.return_value = store
        service = EventServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await service.delete_event(str(event.id), str(uuid4()))
        assert exc.value.code == AUTH_007.code

    async def test_deletes_event_when_owner(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        event = _mock_event(store_id=store.id)
        repo = _mock_repo()
        repo.find_by_id.return_value = event
        repo.find_store_by_id.return_value = store
        service = EventServiceImpl(repo)
        await service.delete_event(str(event.id), str(owner_id))
        repo.delete.assert_awaited_once_with(event)


@pytest.mark.asyncio
class TestCreateEvent:
    async def test_raises_store_001_when_store_not_found(self) -> None:
        repo = _mock_repo()
        repo.find_store_by_id.return_value = None
        service = EventServiceImpl(repo)
        data = EventCreateReq(
            storeId=str(uuid4()), title="E", condition="C", reward=0.001
        )
        with pytest.raises(AppException) as exc:
            await service.create_event(str(uuid4()), data)
        assert exc.value.code == STORE_001.code

    async def test_raises_auth_007_when_requester_is_not_owner(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        repo = _mock_repo()
        repo.find_store_by_id.return_value = store
        service = EventServiceImpl(repo)
        data = EventCreateReq(
            storeId=str(store.id), title="E", condition="C", reward=0.001
        )
        with pytest.raises(AppException) as exc:
            await service.create_event(str(uuid4()), data)
        assert exc.value.code == AUTH_007.code

    async def test_reward_converted_from_eth_to_wei(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        saved: list[MagicMock] = []
        repo = _mock_repo()
        repo.find_store_by_id.return_value = store

        async def _save(event: MagicMock) -> MagicMock:
            saved.append(event)
            return event

        repo.save.side_effect = _save
        service = EventServiceImpl(repo)
        data = EventCreateReq(
            storeId=str(store.id), title="E", condition="C", reward=0.005
        )
        with patch(
            "app.event.service_impl.blockchain_service.deploy_contract",
            new_callable=AsyncMock,
            return_value="0xAddr",
        ):
            await service.create_event(str(owner_id), data)
        assert len(saved) == 1
        assert saved[0].reward == int(0.005 * 10**18)

    async def test_contract_address_is_set_from_deploy(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        saved: list[MagicMock] = []
        repo = _mock_repo()
        repo.find_store_by_id.return_value = store

        async def _save(event: MagicMock) -> MagicMock:
            saved.append(event)
            return event

        repo.save.side_effect = _save
        service = EventServiceImpl(repo)
        data = EventCreateReq(
            storeId=str(store.id), title="E", condition="C", reward=0.001
        )
        with patch(
            "app.event.service_impl.blockchain_service.deploy_contract",
            new_callable=AsyncMock,
            return_value="0xDeployedAddr",
        ):
            await service.create_event(str(owner_id), data)
        assert saved[0].contract_address == "0xDeployedAddr"

    async def test_calls_deploy_contract_once(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        repo = _mock_repo()
        repo.find_store_by_id.return_value = store
        repo.save.side_effect = lambda e: e
        service = EventServiceImpl(repo)
        data = EventCreateReq(
            storeId=str(store.id), title="E", condition="C", reward=0.001
        )
        with patch(
            "app.event.service_impl.blockchain_service.deploy_contract",
            new_callable=AsyncMock,
            return_value="0xAddr",
        ) as mock_deploy:
            await service.create_event(str(owner_id), data)
        mock_deploy.assert_awaited_once()


@pytest.mark.asyncio
class TestListEventApplications:
    async def test_raises_event_001_when_event_not_found(self) -> None:
        repo = _mock_repo()
        repo.find_by_id.return_value = None
        service = EventServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await service.list_event_applications(
                str(uuid4()), str(uuid4()), status_filter=None, page=0, size=10
            )
        assert exc.value.code == EVENT_001.code

    async def test_raises_auth_007_when_store_not_found(self) -> None:
        event = _mock_event()
        repo = _mock_repo()
        repo.find_by_id.return_value = event
        repo.find_store_by_id.return_value = None
        service = EventServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await service.list_event_applications(
                str(event.id), str(uuid4()), status_filter=None, page=0, size=10
            )
        assert exc.value.code == AUTH_007.code

    async def test_raises_auth_007_when_not_event_owner(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        event = _mock_event(store_id=store.id)
        repo = _mock_repo()
        repo.find_by_id.return_value = event
        repo.find_store_by_id.return_value = store
        service = EventServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await service.list_event_applications(
                str(event.id), str(uuid4()), status_filter=None, page=0, size=10
            )
        assert exc.value.code == AUTH_007.code

    async def test_returns_empty_list_when_no_applications(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        event = _mock_event(store_id=store.id)
        repo = _mock_repo()
        repo.find_by_id.return_value = event
        repo.find_store_by_id.return_value = store
        repo.find_applications_by_event_id.return_value = ([], 0)
        service = EventServiceImpl(repo)
        summaries, total = await service.list_event_applications(
            str(event.id), str(owner_id), status_filter=None, page=0, size=10
        )
        assert summaries == []
        assert total == 0

    async def test_returns_application_summaries(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        event = _mock_event(store_id=store.id)
        reviewer = MagicMock()
        reviewer.username = "reviewer_name"
        app = _mock_application(event_id=event.id)
        repo = _mock_repo()
        repo.find_by_id.return_value = event
        repo.find_store_by_id.return_value = store
        repo.find_applications_by_event_id.return_value = ([app], 1)
        repo.find_user_by_id.return_value = reviewer
        repo.find_submission_by_application_id.return_value = None
        service = EventServiceImpl(repo)
        summaries, total = await service.list_event_applications(
            str(event.id), str(owner_id), status_filter=None, page=0, size=10
        )
        assert total == 1
        assert len(summaries) == 1
        assert summaries[0].reviewerName == "reviewer_name"
        assert summaries[0].hasSubmission is False
