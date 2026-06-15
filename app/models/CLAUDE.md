# Models — app/models/

SQLAlchemy 2.0 async ORM 모델 정의.

## 패턴

- `app/db/base.py`의 `Base` 상속
- 기본 키: UUID, `default=uuid4`
- 타임스탬프: `DateTime(timezone=True)`, `server_default=func.now()`
- 타입 어노테이션 기반 컬럼 (`Mapped[str]`, `Mapped[Optional[str]]`)
- 모델 추가 후 반드시 `app/db/base.py`에 import (Alembic autogenerate 필요)

```python
# 예시
from uuid import UUID, uuid4
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50))
```

---

## 도메인별 모델

### User — `app/models/user.py`
테이블: `users`

| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| username | String(50) | |
| email | String(255) | unique, index |
| password_hash | String | bcrypt |
| role | Enum("OWNER","REVIEWER") | |
| created_at | DateTime(tz) | server_default |

관계: `stores` (1:N), `events` (1:N, OWNER 기준), `applications` (1:N, REVIEWER 기준)

---

### EmailVerification — `app/models/email_verification.py`
테이블: `email_verifications`

| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| email | String(255) | index |
| code | String(6) | 6자리 인증 코드 |
| verification_token | String | 검증 완료 후 발급, nullable |
| is_verified | Boolean | default False |
| expires_at | DateTime(tz) | 코드 만료 시각 |
| created_at | DateTime(tz) | server_default |

---

### Store — `app/models/store.py`
테이블: `stores`

| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| name | String(100) | index |
| address | String(255) | |
| category | Enum(StoreType) | RESTAURANT/CAFE/FASHION/BEAUTY/ETC |
| thumbnail_key | String | nullable, S3 키 |
| description | Text | nullable |
| owner_id | UUID | FK users.id |
| created_at | DateTime(tz) | server_default |

관계: `owner` (N:1 User), `events` (1:N Event)

---

### Event — `app/models/event.py`
테이블: `events`

| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| title | String(200) | |
| condition | Text | 리뷰 조건 |
| reward | Integer | 보상 금액 |
| is_active | Boolean | default True |
| store_id | UUID | FK stores.id |
| created_at | DateTime(tz) | server_default |

관계: `store` (N:1 Store), `applications` (1:N Application)

⚠️ API 명세의 `POST /api/event` Request에 `storeId`가 없음 — 실제 구현 시 Request에 포함하거나 OWNER의 대표 상점에 자동 연결하도록 협의 필요.

---

### Application — `app/models/application.py`
테이블: `applications`

| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| event_id | UUID | FK events.id |
| reviewer_id | UUID | FK users.id |
| wallet_address | String | 암호화폐 지갑 주소 |
| image_key | String | S3 키 (신청 시 첨부 이미지) |
| status | Enum("PENDING","APPROVED","REJECTED") | default PENDING |
| applied_at | DateTime(tz) | server_default |

관계: `event` (N:1 Event), `reviewer` (N:1 User), `submission` (1:1 ReviewSubmission, optional)

UniqueConstraint: `(event_id, reviewer_id)` — 동일 이벤트 중복 신청 방지

---

### ReviewSubmission — `app/models/review_submission.py`
테이블: `review_submissions`

| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| application_id | UUID | FK applications.id, unique |
| message | Text | 리뷰 본문 (comment) |
| created_at | DateTime(tz) | server_default |

관계: `application` (1:1 Application), `images` (1:N ReviewImage)

---

### ReviewImage — `app/models/review_image.py`
테이블: `review_images`

| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| submission_id | UUID | FK review_submissions.id |
| image_key | String | S3 키 |
| order | Integer | 이미지 순서 (0-based) |

---

### Deposit — `app/models/deposit.py`
테이블: `deposits`

| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| user_id | UUID | FK users.id |
| amount | Integer | 입금액 |
| balance | Integer | 입금 후 누적 잔액 |
| deposited_at | DateTime(tz) | server_default |

관계: `user` (N:1 User)
