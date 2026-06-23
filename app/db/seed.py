import logging
from typing import cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.auth.models import User
from app.blockchain.service import BlockchainService
from app.core.security import get_password_hash
from app.db.base import Base
from app.event.models import Event
from app.store.models import Store

logger = logging.getLogger(__name__)


class Seeder:
    def __init__(
        self,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
        blockchain_service: BlockchainService | None,
    ) -> None:
        self._engine = engine
        self._sessions = session_factory
        self._blockchain = blockchain_service

    async def run(self) -> None:
        await self._reset()
        await self._seed()

    async def _reset(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def _deploy_contract(self) -> str | None:
        if not self._blockchain:
            return None
        try:
            return await self._blockchain.deploy_contract()
        except Exception:
            logger.exception("[SEED] contract deploy failed, skipping")
            return None

    async def _fund_contract(self, contract_address: str, amount_wei: int) -> None:
        if not self._blockchain:
            return
        try:
            await self._blockchain.fund_contract(contract_address, amount_wei)
        except Exception:
            logger.exception(
                "[SEED] contract fund failed contract=%s", contract_address
            )

    async def _seed(self) -> None:
        async with self._sessions() as session:
            owner1 = User(
                id=uuid4(),
                username="김철수",
                email="owner1@test.com",
                password_hash=get_password_hash("password123"),
                role="OWNER",
            )
            owner2 = User(
                id=uuid4(),
                username="이영희",
                email="owner2@test.com",
                password_hash=get_password_hash("password123"),
                role="OWNER",
            )
            session.add_all([owner1, owner2])
            await session.flush()

            store1 = Store(
                id=uuid4(),
                name="맛있는 삼겹살",
                address="서울시 강남구 테헤란로 1길 10",
                category="RESTAURANT",
                description="신선한 국내산 돼지고기 전문점",
                owner_id=owner1.id,
            )
            store2 = Store(
                id=uuid4(),
                name="카페 브루잉",
                address="서울시 마포구 홍익로 5길 3",
                category="CAFE",
                description="스페셜티 원두를 직접 로스팅하는 카페",
                owner_id=owner1.id,
            )
            store3 = Store(
                id=uuid4(),
                name="에이블 패션",
                address="서울시 중구 명동길 20",
                category="FASHION",
                description="트렌디한 여성 의류 편집샵",
                owner_id=owner2.id,
            )
            store4 = Store(
                id=uuid4(),
                name="글로우 뷰티살롱",
                address="서울시 서초구 반포대로 8길 15",
                category="BEAUTY",
                description="피부 관리 및 네일 전문 뷰티샵",
                owner_id=owner2.id,
            )
            session.add_all([store1, store2, store3, store4])
            await session.flush()

            event_specs = [
                dict(
                    title="삼겹살 맛집 블로그 리뷰 모집",
                    condition="네이버 블로그 사진 5장 이상, 300자 이상 리뷰 작성",
                    reward=10_000_000_000_000_000,  # 0.01 ETH
                    is_active=True,
                    store_id=store1.id,
                ),
                dict(
                    title="삼겹살집 인스타그램 리뷰",
                    condition="인스타그램에 해시태그 #맛있는삼겹살 포함 게시물 업로드",
                    reward=5_000_000_000_000_000,  # 0.005 ETH
                    is_active=True,
                    store_id=store1.id,
                ),
                dict(
                    title="카페 브루잉 음료 리뷰",
                    condition="네이버 지도 리뷰 작성",
                    reward=3_000_000_000_000_000,  # 0.003 ETH
                    is_active=True,
                    store_id=store2.id,
                ),
                dict(
                    title="에이블 패션 스타일링 후기",
                    condition="구매 후 착용샷과 함께 SNS 게시",
                    reward=15_000_000_000_000_000,  # 0.015 ETH
                    is_active=True,
                    store_id=store3.id,
                ),
                dict(
                    title="글로우 뷰티살롱 시술 후기",
                    condition="카카오맵 리뷰 200자 이상 + 사진 3장 이상 첨부",
                    reward=8_000_000_000_000_000,  # 0.008 ETH
                    is_active=False,
                    store_id=store4.id,
                ),
            ]
            for spec in event_specs:
                contract_address = await self._deploy_contract()
                if contract_address:
                    await self._fund_contract(
                        contract_address, cast(int, spec["reward"])
                    )
                session.add(
                    Event(id=uuid4(), contract_address=contract_address, **spec)
                )
            await session.commit()
