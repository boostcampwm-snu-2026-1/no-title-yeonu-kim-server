# Services — app/services/

비즈니스 로직 레이어. 엔드포인트에서 DB를 직접 다루지 않고 서비스 함수를 호출한다.

## 패턴

- **함수형** (클래스 없이 async 함수)
- 첫 번째 인자: `db: AsyncSession`
- SQLAlchemy 2.0 스타일: `select()` + `session.execute()` + `.scalar()` / `.scalars()`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.store import Store

async def get_store_or_404(db: AsyncSession, store_id: str) -> Store:
    store = await db.scalar(select(Store).where(Store.id == store_id))
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store

async def create_store(db: AsyncSession, owner_id: str, data: StoreCreateReq) -> Store:
    store = Store(owner_id=owner_id, **data.model_dump(exclude_none=True))
    db.add(store)
    await db.commit()
    await db.refresh(store)
    return store
```

## 에러 처리

도메인 에러는 서비스에서 `HTTPException` raise — 엔드포인트는 성공 경로만 처리.

| 상황 | 상태 코드 |
|------|----------|
| 리소스 없음 | 404 Not Found |
| 권한 없음 (본인 아님) | 403 Forbidden |
| 인증 실패 | 401 Unauthorized |
| 중복 (이메일, 신청 등) | 409 Conflict |
| 잘못된 요청 | 400 Bad Request |

## 트랜잭션

여러 insert/update가 함께 커밋되어야 할 때:

```python
async with db.begin():
    db.add(entity1)
    db.add(entity2)
# 블록 종료 시 자동 commit
```

단순 단건 insert는 `db.add()` → `await db.commit()` → `await db.refresh()`.

## 페이지네이션 패턴

```python
from sqlalchemy import select, func

async def list_stores(db: AsyncSession, page: int, size: int, ...) -> tuple[list[Store], int]:
    base_query = select(Store).where(...)
    total = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    stores = (await db.scalars(base_query.offset((page - 1) * size).limit(size))).all()
    return list(stores), total or 0
```

## JWT — app/core/security.py (추가 필요)

PyJWT 의존성 추가 후:

```python
import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings

def create_access_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=30)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def decode_token(token: str) -> str:  # returns user_id
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    return str(payload["sub"])
```

`app/api/deps.py`의 `require_login`에서 `decode_token` 호출하여 user_id 반환.

## 파일별 구성

| 파일 | 담당 |
|------|------|
| `auth.py` | 회원가입, 로그인, 이메일 인증, 비밀번호 관련 |
| `store.py` | 상점 CRUD, 페이지네이션 |
| `event.py` | 이벤트 CRUD, 신청 목록 조회 |
| `application.py` | 신청 생성/조회/취소, 리뷰 제출 |
| `s3.py` | S3 presigned URL 생성 (기존 파일) |
| `deposit.py` | 입금 처리, 잔액 계산 |

## 이메일 발송 (auth.py)

MVP 단계에서는 콘솔 출력으로 대체:

```python
async def send_verification_email(email: str, code: str) -> None:
    # TODO: AWS SES 또는 SMTP 연동
    print(f"[DEV] Verification code for {email}: {code}")
```

config에 `smtp_*` 또는 `ses_*` 환경변수 추가 후 실제 발송 구현.
