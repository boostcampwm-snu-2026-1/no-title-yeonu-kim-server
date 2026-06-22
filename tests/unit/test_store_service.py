"""Unit tests for app/services/store.py — AsyncSession is mocked."""

from collections.abc import Sequence
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import AUTH_007, STORE_001, AppException
from app.schemas.store import StoreCreateReq
from app.services.store import (
    create_store,
    delete_store,
    get_store_or_404,
    list_store_events,
    list_stores,
)


def _mock_store(owner_id: UUID | None = None) -> MagicMock:
    store = MagicMock()
    store.id = uuid4()
    store.owner_id = owner_id or uuid4()
    store.name = "Test Store"
    store.address = "123 Main St"
    store.category = "RESTAURANT"
    store.thumbnail_key = None
    store.description = None
    return store


def _mock_event(
    store_id: UUID | None = None, *, reward_eth: float = 0.001
) -> MagicMock:
    event = MagicMock()
    event.id = uuid4()
    event.store_id = store_id or uuid4()
    event.title = "Test Event"
    event.condition = "Post a photo"
    event.reward = int(reward_eth * 10**18)
    event.is_active = True
    return event


def _scalars_result(items: Sequence[object]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = items
    return result


@pytest.mark.asyncio
class TestGetStoreOr404:
    async def test_raises_store_001_when_not_found(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = None
        with pytest.raises(AppException) as exc:
            await get_store_or_404(db, str(uuid4()))
        assert exc.value.code == STORE_001.code
        assert exc.value.status_code == 404

    async def test_returns_store_when_found(self) -> None:
        store = _mock_store()
        db = AsyncMock()
        db.scalar.return_value = store
        result = await get_store_or_404(db, str(store.id))
        assert result is store


@pytest.mark.asyncio
class TestListStores:
    async def test_returns_empty_list_when_no_stores(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = 0
        db.scalars.return_value = _scalars_result([])
        items, total = await list_stores(db, category=None, name=None, page=0, size=10)
        assert items == []
        assert total == 0

    async def test_returns_store_with_correct_fields(self) -> None:
        store = _mock_store()
        db = AsyncMock()
        db.scalar.return_value = 1
        db.scalars.side_effect = [_scalars_result([store]), _scalars_result([])]
        items, total = await list_stores(db, category=None, name=None, page=0, size=10)
        assert total == 1
        assert len(items) == 1
        assert items[0].name == store.name
        assert items[0].address == store.address

    async def test_includes_events_for_each_store(self) -> None:
        store = _mock_store()
        event = _mock_event(store_id=store.id, reward_eth=0.005)
        db = AsyncMock()
        db.scalar.return_value = 1
        db.scalars.side_effect = [_scalars_result([store]), _scalars_result([event])]
        items, _ = await list_stores(db, category=None, name=None, page=0, size=10)
        assert len(items[0].events) == 1
        assert items[0].totalEventCount == 1
        assert abs(items[0].events[0].reward - 0.005) < 1e-12

    async def test_reward_is_converted_from_wei_to_eth(self) -> None:
        store = _mock_store()
        event = _mock_event(store_id=store.id, reward_eth=0.002)
        db = AsyncMock()
        db.scalar.return_value = 1
        db.scalars.side_effect = [_scalars_result([store]), _scalars_result([event])]
        items, _ = await list_stores(db, category=None, name=None, page=0, size=10)
        assert abs(items[0].events[0].reward - 0.002) < 1e-12


@pytest.mark.asyncio
class TestCreateStore:
    async def test_adds_to_session_commits_and_refreshes(self) -> None:
        db = AsyncMock()
        data = StoreCreateReq(name="My Shop", address="Seoul", category="CAFE")
        await create_store(db, str(uuid4()), data)
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    async def test_store_object_has_correct_name_and_address(self) -> None:
        db = AsyncMock()
        data = StoreCreateReq(name="My Shop", address="Seoul", category="CAFE")
        await create_store(db, str(uuid4()), data)
        added = db.add.call_args[0][0]
        assert added.name == "My Shop"
        assert added.address == "Seoul"

    async def test_store_object_has_correct_owner_id(self) -> None:
        db = AsyncMock()
        owner_id = uuid4()
        data = StoreCreateReq(name="Shop", address="Busan", category="ETC")
        await create_store(db, str(owner_id), data)
        added = db.add.call_args[0][0]
        assert added.owner_id == owner_id

    async def test_optional_fields_are_set_when_provided(self) -> None:
        db = AsyncMock()
        data = StoreCreateReq(
            name="Cafe",
            address="Incheon",
            category="CAFE",
            thumbnailUrl="thumb.jpg",
            description="Nice place",
        )
        await create_store(db, str(uuid4()), data)
        added = db.add.call_args[0][0]
        assert added.thumbnail_key == "thumb.jpg"
        assert added.description == "Nice place"

    async def test_optional_fields_are_none_when_omitted(self) -> None:
        db = AsyncMock()
        data = StoreCreateReq(name="Shop", address="Seoul", category="ETC")
        await create_store(db, str(uuid4()), data)
        added = db.add.call_args[0][0]
        assert added.thumbnail_key is None
        assert added.description is None


@pytest.mark.asyncio
class TestDeleteStore:
    async def test_raises_store_001_when_store_not_found(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = None
        with pytest.raises(AppException) as exc:
            await delete_store(db, str(uuid4()), str(uuid4()))
        assert exc.value.code == STORE_001.code

    async def test_raises_auth_007_when_requester_is_not_owner(self) -> None:
        owner_id = uuid4()
        other_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        db = AsyncMock()
        db.scalar.return_value = store
        with pytest.raises(AppException) as exc:
            await delete_store(db, str(store.id), str(other_id))
        assert exc.value.code == AUTH_007.code

    async def test_deletes_store_and_commits_when_owner(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        db = AsyncMock()
        db.scalar.return_value = store
        await delete_store(db, str(store.id), str(owner_id))
        db.delete.assert_called_once_with(store)
        db.commit.assert_awaited_once()


@pytest.mark.asyncio
class TestListStoreEvents:
    async def test_raises_store_001_when_store_not_found(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = None
        with pytest.raises(AppException) as exc:
            await list_store_events(db, str(uuid4()))
        assert exc.value.code == STORE_001.code

    async def test_returns_empty_list_when_no_events(self) -> None:
        store = _mock_store()
        db = AsyncMock()
        db.scalar.return_value = store
        db.scalars.return_value = _scalars_result([])
        summaries = await list_store_events(db, str(store.id))
        assert summaries == []

    async def test_returns_event_summaries_with_eth_conversion(self) -> None:
        store = _mock_store()
        event = _mock_event(store_id=store.id, reward_eth=0.005)
        db = AsyncMock()
        db.scalar.return_value = store
        db.scalars.return_value = _scalars_result([event])
        summaries = await list_store_events(db, str(store.id))
        assert len(summaries) == 1
        assert summaries[0].title == event.title
        assert abs(summaries[0].reward - 0.005) < 1e-12
        assert summaries[0].isActive == event.is_active

    async def test_returns_multiple_event_summaries(self) -> None:
        store = _mock_store()
        events = [_mock_event(store_id=store.id) for _ in range(3)]
        db = AsyncMock()
        db.scalar.return_value = store
        db.scalars.return_value = _scalars_result(events)
        summaries = await list_store_events(db, str(store.id))
        assert len(summaries) == 3
