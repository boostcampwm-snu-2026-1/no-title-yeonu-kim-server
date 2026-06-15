from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.application import Application
from app.models.deposit import Deposit
from app.models.email_verification import EmailVerification
from app.models.event import Event
from app.models.store import Store
from app.models.user import User

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    _engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    await _engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


async def create_user(
    db: AsyncSession,
    *,
    email: str = "test@example.com",
    password: str = "password123",
    role: str = "REVIEWER",
    username: str = "testuser",
) -> User:
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        role=role,
        username=username,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_verification(
    db: AsyncSession,
    *,
    email: str = "test@example.com",
    code: str = "123456",
    expired: bool = False,
    is_verified: bool = False,
) -> EmailVerification:
    delta = timedelta(minutes=-1) if expired else timedelta(minutes=10)
    record = EmailVerification(
        email=email,
        code=code,
        expires_at=datetime.now(UTC) + delta,
        is_verified=is_verified,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


def auth_headers(user_id: UUID) -> dict[str, str]:
    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


async def create_store(
    db: AsyncSession,
    owner_id: UUID,
    *,
    name: str = "Test Store",
    address: str = "123 Main St",
    category: str = "RESTAURANT",
) -> Store:
    store = Store(name=name, address=address, category=category, owner_id=owner_id)
    db.add(store)
    await db.commit()
    await db.refresh(store)
    return store


async def create_event(
    db: AsyncSession,
    store_id: UUID,
    *,
    title: str = "Test Event",
    condition: str = "Post a photo review",
    reward: int = 5000,
) -> Event:
    event = Event(title=title, condition=condition, reward=reward, store_id=store_id)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def create_deposit(
    db: AsyncSession,
    user_id: UUID,
    *,
    amount: int = 100000,
) -> Deposit:
    deposit = Deposit(user_id=user_id, amount=amount, balance=amount)
    db.add(deposit)
    await db.commit()
    await db.refresh(deposit)
    return deposit


async def create_application(
    db: AsyncSession,
    event_id: UUID,
    reviewer_id: UUID,
    *,
    status: str = "PENDING",
) -> Application:
    application = Application(
        event_id=event_id,
        reviewer_id=reviewer_id,
        wallet_address="0x1234567890abcdef",
        image_key="reviews/test.jpg",
        status=status,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application
