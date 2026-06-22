"""Unit tests for app/services/event.py — AsyncSession and blockchain are mocked."""

from collections.abc import Sequence
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import AUTH_007, EVENT_001, STORE_001, AppException
from app.schemas.event import EventCreateReq
from app.services.event import (
    create_event,
    delete_event,
    get_event_or_404,
    list_event_applications,
    list_owner_events,
)


def _mock_store(owner_id: UUID | None = None) -> MagicMock:
    store = MagicMock()
    store.id = uuid4()
    store.owner_id = owner_id or uuid4()
    return store


def _mock_event(store_id: UUID | None = None) -> MagicMock:
    event = MagicMock()
    event.id = uuid4()
    event.store_id = store_id or uuid4()
    event.title = "Test Event"
    event.condition = "Post photo"
    event.reward = int(0.001 * 10**18)
    event.is_active = True
    event.contract_address = None
    return event


def _mock_application(
    event_id: UUID | None = None, reviewer_id: UUID | None = None
) -> MagicMock:
    app = MagicMock()
    app.id = uuid4()
    app.event_id = event_id or uuid4()
    app.reviewer_id = reviewer_id or uuid4()
    app.status = "PENDING"
    app.applied_at = datetime.now(UTC)
    return app


def _scalars_result(items: Sequence[object]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = items
    return result


@pytest.mark.asyncio
class TestGetEventOr404:
    async def test_raises_event_001_when_not_found(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = None
        with pytest.raises(AppException) as exc:
            await get_event_or_404(db, str(uuid4()))
        assert exc.value.code == EVENT_001.code
        assert exc.value.status_code == 404

    async def test_returns_event_when_found(self) -> None:
        event = _mock_event()
        db = AsyncMock()
        db.scalar.return_value = event
        result = await get_event_or_404(db, str(event.id))
        assert result is event


@pytest.mark.asyncio
class TestListOwnerEvents:
    async def test_returns_events_belonging_to_owner(self) -> None:
        owner_id = uuid4()
        events = [_mock_event() for _ in range(2)]
        db = AsyncMock()
        db.scalars.return_value = _scalars_result(events)
        result = await list_owner_events(db, str(owner_id))
        assert result == events

    async def test_returns_empty_list_when_no_events(self) -> None:
        db = AsyncMock()
        db.scalars.return_value = _scalars_result([])
        result = await list_owner_events(db, str(uuid4()))
        assert result == []


@pytest.mark.asyncio
class TestDeleteEvent:
    async def test_raises_event_001_when_event_not_found(self) -> None:
        db = AsyncMock()
        db.scalar.side_effect = [None]
        with pytest.raises(AppException) as exc:
            await delete_event(db, str(uuid4()), str(uuid4()))
        assert exc.value.code == EVENT_001.code

    async def test_raises_auth_007_when_store_not_found(self) -> None:
        event = _mock_event()
        db = AsyncMock()
        db.scalar.side_effect = [event, None]  # event found, store not found
        with pytest.raises(AppException) as exc:
            await delete_event(db, str(event.id), str(uuid4()))
        assert exc.value.code == AUTH_007.code

    async def test_raises_auth_007_when_requester_is_not_owner(self) -> None:
        owner_id = uuid4()
        other_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        event = _mock_event(store_id=store.id)
        db = AsyncMock()
        db.scalar.side_effect = [event, store]
        with pytest.raises(AppException) as exc:
            await delete_event(db, str(event.id), str(other_id))
        assert exc.value.code == AUTH_007.code

    async def test_deletes_event_and_commits_when_owner(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        event = _mock_event(store_id=store.id)
        db = AsyncMock()
        db.scalar.side_effect = [event, store]
        await delete_event(db, str(event.id), str(owner_id))
        db.delete.assert_called_once_with(event)
        db.commit.assert_awaited_once()


@pytest.mark.asyncio
class TestCreateEvent:
    async def test_raises_store_001_when_store_not_found(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = None
        data = EventCreateReq(
            storeId=str(uuid4()), title="E", condition="C", reward=0.001
        )
        with pytest.raises(AppException) as exc:
            await create_event(db, str(uuid4()), data)
        assert exc.value.code == STORE_001.code

    async def test_raises_auth_007_when_requester_is_not_owner(self) -> None:
        owner_id = uuid4()
        other_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        db = AsyncMock()
        db.scalar.return_value = store
        data = EventCreateReq(
            storeId=str(store.id), title="E", condition="C", reward=0.001
        )
        with pytest.raises(AppException) as exc:
            await create_event(db, str(other_id), data)
        assert exc.value.code == AUTH_007.code

    async def test_reward_converted_from_eth_to_wei(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        db = AsyncMock()
        db.scalar.return_value = store
        data = EventCreateReq(
            storeId=str(store.id), title="E", condition="C", reward=0.005
        )
        with patch(
            "app.services.event.blockchain_service.deploy_contract",
            new_callable=AsyncMock,
            return_value="0xAddr",
        ):
            await create_event(db, str(owner_id), data)
        added = db.add.call_args[0][0]
        assert added.reward == int(0.005 * 10**18)

    async def test_contract_address_is_set_from_deploy(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        db = AsyncMock()
        db.scalar.return_value = store
        data = EventCreateReq(
            storeId=str(store.id), title="E", condition="C", reward=0.001
        )
        with patch(
            "app.services.event.blockchain_service.deploy_contract",
            new_callable=AsyncMock,
            return_value="0xDeployedAddr",
        ):
            await create_event(db, str(owner_id), data)
        added = db.add.call_args[0][0]
        assert added.contract_address == "0xDeployedAddr"

    async def test_calls_deploy_contract_once(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        db = AsyncMock()
        db.scalar.return_value = store
        data = EventCreateReq(
            storeId=str(store.id), title="E", condition="C", reward=0.001
        )
        with patch(
            "app.services.event.blockchain_service.deploy_contract",
            new_callable=AsyncMock,
            return_value="0xAddr",
        ) as mock_deploy:
            await create_event(db, str(owner_id), data)
        mock_deploy.assert_awaited_once()

    async def test_event_is_committed_to_db(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        db = AsyncMock()
        db.scalar.return_value = store
        data = EventCreateReq(
            storeId=str(store.id), title="E", condition="C", reward=0.001
        )
        with patch(
            "app.services.event.blockchain_service.deploy_contract",
            new_callable=AsyncMock,
            return_value="0xAddr",
        ):
            await create_event(db, str(owner_id), data)
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()


@pytest.mark.asyncio
class TestListEventApplications:
    async def test_raises_event_001_when_event_not_found(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = None
        with pytest.raises(AppException) as exc:
            await list_event_applications(db, str(uuid4()), str(uuid4()), None, 0, 10)
        assert exc.value.code == EVENT_001.code

    async def test_raises_auth_007_when_store_not_found(self) -> None:
        event = _mock_event()
        db = AsyncMock()
        db.scalar.side_effect = [event, None]  # event found, store not found
        with pytest.raises(AppException) as exc:
            await list_event_applications(db, str(event.id), str(uuid4()), None, 0, 10)
        assert exc.value.code == AUTH_007.code

    async def test_raises_auth_007_when_not_event_owner(self) -> None:
        owner_id = uuid4()
        other_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        event = _mock_event(store_id=store.id)
        db = AsyncMock()
        db.scalar.side_effect = [event, store]
        with pytest.raises(AppException) as exc:
            await list_event_applications(db, str(event.id), str(other_id), None, 0, 10)
        assert exc.value.code == AUTH_007.code

    async def test_returns_empty_list_when_no_applications(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        event = _mock_event(store_id=store.id)
        db = AsyncMock()
        # event, store, count=0
        db.scalar.side_effect = [event, store, 0]
        db.scalars.return_value = _scalars_result([])
        summaries, total = await list_event_applications(
            db, str(event.id), str(owner_id), None, 0, 10
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
        db = AsyncMock()
        # event, store, count=1, then for each app: reviewer, has_submission
        db.scalar.side_effect = [event, store, 1, reviewer, None]
        db.scalars.return_value = _scalars_result([app])
        summaries, total = await list_event_applications(
            db, str(event.id), str(owner_id), None, 0, 10
        )
        assert total == 1
        assert len(summaries) == 1
        assert summaries[0].reviewerName == "reviewer_name"
        assert summaries[0].hasSubmission is False
