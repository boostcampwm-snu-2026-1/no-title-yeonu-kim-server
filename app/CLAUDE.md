# App — 도메인 패키지 구조 & DI 가이드

## 패키지 내 파일 구조

모든 도메인은 아래 8개 파일로 구성한다.

```
app/{domain}/
├── __init__.py
├── models.py          # SQLAlchemy ORM 모델
├── schemas.py         # Pydantic 요청·응답 스키마
├── repository.py      # ABC 인터페이스 (DB 무관)
├── repository_impl.py # SQLAlchemy 구현체
├── service.py         # ABC 인터페이스 (비즈니스 무관)
├── service_impl.py    # 비즈니스 로직 구현체
├── dependencies.py    # FastAPI DI 바인딩 (get_* 함수)
└── router.py          # FastAPI 라우터
```

---

## 1. models.py — SQLAlchemy ORM

`app/db/base.py`의 `Base` 상속. 패턴은 기존 `app/models/` 파일과 동일.

```python
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True)
```

새 모델을 추가하면 반드시 `app/db/base.py`에 import 추가 (Alembic autogenerate 필요).

---

## 2. schemas.py — Pydantic v2

패턴은 기존 `app/schemas/` 파일과 동일. 공통 타입(`SuccessResponse`, Enum 등)은 `app/schemas/common.py` 유지.

---

## 3. repository.py — ABC 인터페이스

DB 구현과 무관한 순수 인터페이스. `abstractmethod`만 선언하고 구현 없음.

```python
from abc import ABC, abstractmethod
from app.auth.models import User

class UserRepository(ABC):
    @abstractmethod
    async def find_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def find_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...
```

---

## 4. repository_impl.py — SQLAlchemy 구현체

`UserRepository`를 상속하고 `AsyncSession`을 생성자로 받는다.

```python
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.repository import UserRepository
from app.auth.models import User

class UserRepositoryImpl(UserRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_email(self, email: str) -> User | None:
        return await self.db.scalar(select(User).where(User.email == email))

    async def find_by_id(self, user_id: str) -> User | None:
        return await self.db.scalar(select(User).where(User.id == UUID(user_id)))

    async def save(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
```

SQLAlchemy 쿼리는 구현체에만. ABC 인터페이스에는 절대 포함하지 않는다.

---

## 5. service.py — ABC 인터페이스

레포지토리 ABC와 마찬가지로 메서드 시그니처만 선언.

```python
from abc import ABC, abstractmethod
from app.auth.models import User
from app.auth.schemas import RegisterReq

class AuthService(ABC):
    @abstractmethod
    async def register(self, data: RegisterReq) -> tuple[User, str, str]: ...

    @abstractmethod
    async def login(self, data: LoginReq) -> tuple[User, str, str]: ...
```

---

## 6. service_impl.py — 비즈니스 로직 구현체

`AuthService`를 상속하고 `UserRepository`를 생성자로 받는다.
DB 직접 접근 금지 — 반드시 레포지토리를 통한다.

```python
from app.auth.service import AuthService
from app.auth.repository import UserRepository
from app.auth.models import User
from app.auth.schemas import RegisterReq
from app.core.exceptions import USER_001, AppException
from app.core.security import get_password_hash, create_access_token, create_refresh_token

class AuthServiceImpl(AuthService):
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def register(self, data: RegisterReq) -> tuple[User, str, str]:
        if await self.repo.find_by_email(data.email):
            raise AppException(USER_001)
        user = User(
            username=data.username,
            email=data.email,
            password_hash=get_password_hash(data.password),
            role=data.role,
        )
        user = await self.repo.save(user)
        user_id = str(user.id)
        return user, create_access_token(user_id), create_refresh_token(user_id)
```

에러는 서비스에서 `AppException` raise. 라우터는 성공 경로만 처리한다.

---

## 7. dependencies.py — DI 바인딩

`get_*` 함수만 정의. 구현체 클래스를 직접 노출하지 않는다.
반환 타입은 반드시 ABC (인터페이스) 타입으로 선언한다.

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.auth.repository import UserRepository
from app.auth.repository_impl import UserRepositoryImpl
from app.auth.service import AuthService
from app.auth.service_impl import AuthServiceImpl

def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepositoryImpl(db)

def get_auth_service(
    repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthServiceImpl(repo)
```

---

## 8. router.py — FastAPI 라우터

`service`만 주입받는다. 레포지토리를 라우터에서 직접 받지 않는다.

```python
from fastapi import APIRouter, Depends, Response
from app.auth.service import AuthService
from app.auth.schemas import RegisterReq, AuthResp, UserInfo
from app.auth.dependencies import get_auth_service
from app.api.v1.deps import require_login

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/user", response_model=AuthResp)
async def register(
    body: RegisterReq,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> AuthResp:
    user, access_token, refresh_token = await service.register(body)
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True, samesite="lax"
    )
    return AuthResp(user=UserInfo(id=str(user.id), userRole=user.role), token=access_token)
```

---

## Cross-package 의존성 규칙

| 상황 | 규칙 |
|------|------|
| 다른 패키지의 ORM 모델 참조 | 직접 import 허용 (`from app.auth.models import User`) |
| 다른 패키지의 서비스 호출 | **금지** — 공통 로직은 `app/core/`로 분리 |
| 다른 패키지의 레포지토리 직접 사용 | **금지** — 서비스가 자신의 레포지토리만 사용 |

### 예시 — store가 User를 참조하는 경우

```python
# app/store/models.py
from app.auth.models import User  # 모델 import는 OK

class Store(Base):
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    owner: Mapped["User"] = relationship()
```

---

## Alembic — db/base.py 관리

새 패키지의 `models.py`를 추가할 때마다 `app/db/base.py`에 import 추가.

```python
# app/db/base.py
from app.auth.models import User, EmailVerification  # noqa: F401
from app.store.models import Store                   # noqa: F401
from app.event.models import Event                   # noqa: F401
from app.application.models import Application, ReviewSubmission, ReviewImage  # noqa: F401
from app.deposit.models import Deposit               # noqa: F401
```

---

## 이관 순서 (의존성 방향)

```
auth ──→ store ──→ event ──→ application
  └────────────────────────→ deposit
s3  (독립, 모델 없음)
```

| 순서 | 패키지 | 참조하는 외부 모델 |
|------|--------|--------------------|
| 1 | `auth` | 없음 |
| 2 | `store` | `auth.User` |
| 3 | `event` | `store.Store` |
| 4 | `application` | `event.Event`, `auth.User` |
| 5 | `deposit` | `auth.User` |
| 6 | `s3` | 없음 |

각 패키지는 독립적으로 PR을 올린다. 이관 중에는 기존 레이어 파일과 새 패키지가 공존해도 무방하며, 이관 완료 후 기존 파일(`app/models/`, `app/schemas/`, `app/services/`, `app/api/v1/endpoints/`)을 삭제한다.

---

## main.py 라우터 등록

이관 완료된 패키지는 `app/main.py`에서 직접 include.

```python
from app.auth.router import router as auth_router
from app.store.router import router as store_router

app.include_router(auth_router, prefix="/api")
app.include_router(store_router, prefix="/api")
```
