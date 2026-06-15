from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import AsyncSessionLocal
from app.models.application import Application as Application  # noqa: F401
from app.models.deposit import Deposit as Deposit  # noqa: F401
from app.models.email_verification import (
    EmailVerification as EmailVerification,  # noqa: F401
)
from app.models.event import Event
from app.models.review_image import ReviewImage as ReviewImage  # noqa: F401
from app.models.review_submission import (
    ReviewSubmission as ReviewSubmission,  # noqa: F401
)
from app.models.store import Store
from app.models.user import User


async def reset_and_seed(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # --- 사장님 계정 ---
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

        # --- 가게 ---
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

        # --- 이벤트 ---
        session.add_all(
            [
                Event(
                    id=uuid4(),
                    title="삼겹살 맛집 블로그 리뷰 모집",
                    condition="네이버 블로그 사진 5장 이상, 300자 이상 리뷰 작성",
                    reward=10000,
                    is_active=True,
                    store_id=store1.id,
                ),
                Event(
                    id=uuid4(),
                    title="삼겹살집 인스타그램 리뷰",
                    condition="인스타그램에 해시태그 #맛있는삼겹살 포함 게시물 업로드",
                    reward=5000,
                    is_active=True,
                    store_id=store1.id,
                ),
                Event(
                    id=uuid4(),
                    title="카페 브루잉 음료 리뷰",
                    condition="네이버 지도 리뷰 작성 및 별점 4점 이상",
                    reward=3000,
                    is_active=True,
                    store_id=store2.id,
                ),
                Event(
                    id=uuid4(),
                    title="에이블 패션 스타일링 후기",
                    condition="구매 후 착용샷과 함께 SNS 게시 (팔로워 500명 이상)",
                    reward=15000,
                    is_active=True,
                    store_id=store3.id,
                ),
                Event(
                    id=uuid4(),
                    title="글로우 뷰티살롱 시술 후기",
                    condition="카카오맵 리뷰 200자 이상 + 사진 3장 이상 첨부",
                    reward=8000,
                    is_active=False,
                    store_id=store4.id,
                ),
            ]
        )
        await session.commit()
