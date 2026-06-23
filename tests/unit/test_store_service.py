"""Unit tests for StoreServiceImpl — StoreRepository is mocked."""

from collections.abc import Sequence
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import AUTH_007, STORE_001, AppException
from app.store.schemas import StoreCreateReq
from app.store.service_impl import StoreServiceImpl


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


def _make_repo(
    *,
    store: MagicMock | None = None,
    stores: Sequence[MagicMock] | None = None,
    total: int = 0,
    events: Sequence[MagicMock] | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.find_by_id = AsyncMock(return_value=store)
    repo.find_all = AsyncMock(return_value=(list(stores or []), total))
    repo.save = AsyncMock(side_effect=lambda s: s)
    repo.delete = AsyncMock()
    repo.find_events_by_store_id = AsyncMock(return_value=list(events or []))
    return repo


@pytest.mark.asyncio
class TestGetStore:
    async def test_raises_store_001_when_not_found(self) -> None:
        repo = _make_repo(store=None)
        svc = StoreServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await svc.get_store(str(uuid4()))
        assert exc.value.code == STORE_001.code
        assert exc.value.status_code == 404

    async def test_returns_store_when_found(self) -> None:
        store = _mock_store()
        repo = _make_repo(store=store)
        svc = StoreServiceImpl(repo)
        result = await svc.get_store(str(store.id))
        assert result is store


@pytest.mark.asyncio
class TestListStores:
    async def test_returns_empty_list_when_no_stores(self) -> None:
        repo = _make_repo(stores=[], total=0)
        svc = StoreServiceImpl(repo)
        items, total = await svc.list_stores(category=None, name=None, page=0, size=10)
        assert items == []
        assert total == 0

    async def test_returns_store_with_correct_fields(self) -> None:
        store = _mock_store()
        repo = _make_repo(stores=[store], total=1)
        svc = StoreServiceImpl(repo)
        items, total = await svc.list_stores(category=None, name=None, page=0, size=10)
        assert total == 1
        assert len(items) == 1
        assert items[0].name == store.name
        assert items[0].address == store.address

    async def test_includes_events_for_each_store(self) -> None:
        store = _mock_store()
        event = _mock_event(store_id=store.id, reward_eth=0.005)
        repo = _make_repo(stores=[store], total=1, events=[event])
        svc = StoreServiceImpl(repo)
        items, _ = await svc.list_stores(category=None, name=None, page=0, size=10)
        assert len(items[0].events) == 1
        assert items[0].totalEventCount == 1
        assert abs(items[0].events[0].reward - 0.005) < 1e-12

    async def test_reward_is_converted_from_wei_to_eth(self) -> None:
        store = _mock_store()
        event = _mock_event(store_id=store.id, reward_eth=0.002)
        repo = _make_repo(stores=[store], total=1, events=[event])
        svc = StoreServiceImpl(repo)
        items, _ = await svc.list_stores(category=None, name=None, page=0, size=10)
        assert abs(items[0].events[0].reward - 0.002) < 1e-12


@pytest.mark.asyncio
class TestCreateStore:
    async def test_calls_save_and_returns_store(self) -> None:
        repo = _make_repo()
        svc = StoreServiceImpl(repo)
        data = StoreCreateReq(name="My Shop", address="Seoul", category="CAFE")
        await svc.create_store(str(uuid4()), data)
        repo.save.assert_awaited_once()

    async def test_store_object_has_correct_name_and_address(self) -> None:
        repo = _make_repo()
        svc = StoreServiceImpl(repo)
        data = StoreCreateReq(name="My Shop", address="Seoul", category="CAFE")
        await svc.create_store(str(uuid4()), data)
        saved = repo.save.call_args[0][0]
        assert saved.name == "My Shop"
        assert saved.address == "Seoul"

    async def test_store_object_has_correct_owner_id(self) -> None:
        repo = _make_repo()
        svc = StoreServiceImpl(repo)
        owner_id = uuid4()
        data = StoreCreateReq(name="Shop", address="Busan", category="ETC")
        await svc.create_store(str(owner_id), data)
        saved = repo.save.call_args[0][0]
        assert saved.owner_id == owner_id

    async def test_optional_fields_are_set_when_provided(self) -> None:
        repo = _make_repo()
        svc = StoreServiceImpl(repo)
        data = StoreCreateReq(
            name="Cafe",
            address="Incheon",
            category="CAFE",
            thumbnailUrl="thumb.jpg",
            description="Nice place",
        )
        await svc.create_store(str(uuid4()), data)
        saved = repo.save.call_args[0][0]
        assert saved.thumbnail_key == "thumb.jpg"
        assert saved.description == "Nice place"

    async def test_optional_fields_are_none_when_omitted(self) -> None:
        repo = _make_repo()
        svc = StoreServiceImpl(repo)
        data = StoreCreateReq(name="Shop", address="Seoul", category="ETC")
        await svc.create_store(str(uuid4()), data)
        saved = repo.save.call_args[0][0]
        assert saved.thumbnail_key is None
        assert saved.description is None


@pytest.mark.asyncio
class TestDeleteStore:
    async def test_raises_store_001_when_store_not_found(self) -> None:
        repo = _make_repo(store=None)
        svc = StoreServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await svc.delete_store(str(uuid4()), str(uuid4()))
        assert exc.value.code == STORE_001.code

    async def test_raises_auth_007_when_requester_is_not_owner(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        repo = _make_repo(store=store)
        svc = StoreServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await svc.delete_store(str(store.id), str(uuid4()))
        assert exc.value.code == AUTH_007.code

    async def test_deletes_store_when_owner(self) -> None:
        owner_id = uuid4()
        store = _mock_store(owner_id=owner_id)
        repo = _make_repo(store=store)
        svc = StoreServiceImpl(repo)
        await svc.delete_store(str(store.id), str(owner_id))
        repo.delete.assert_awaited_once_with(store)


@pytest.mark.asyncio
class TestListStoreEvents:
    async def test_raises_store_001_when_store_not_found(self) -> None:
        repo = _make_repo(store=None)
        svc = StoreServiceImpl(repo)
        with pytest.raises(AppException) as exc:
            await svc.list_store_events(str(uuid4()))
        assert exc.value.code == STORE_001.code

    async def test_returns_empty_list_when_no_events(self) -> None:
        store = _mock_store()
        repo = _make_repo(store=store, events=[])
        svc = StoreServiceImpl(repo)
        summaries = await svc.list_store_events(str(store.id))
        assert summaries == []

    async def test_returns_event_summaries_with_eth_conversion(self) -> None:
        store = _mock_store()
        event = _mock_event(store_id=store.id, reward_eth=0.005)
        repo = _make_repo(store=store, events=[event])
        svc = StoreServiceImpl(repo)
        summaries = await svc.list_store_events(str(store.id))
        assert len(summaries) == 1
        assert summaries[0].title == event.title
        assert abs(summaries[0].reward - 0.005) < 1e-12
        assert summaries[0].isActive == event.is_active

    async def test_returns_multiple_event_summaries(self) -> None:
        store = _mock_store()
        events = [_mock_event(store_id=store.id) for _ in range(3)]
        repo = _make_repo(store=store, events=events)
        svc = StoreServiceImpl(repo)
        summaries = await svc.list_store_events(str(store.id))
        assert len(summaries) == 3
