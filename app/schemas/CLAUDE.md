# Schemas — app/schemas/

Pydantic v2 기반 요청·응답 스키마.

## 공통 응답 래퍼 — app/schemas/common.py (생성 필요)

```python
from datetime import datetime, timezone
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class SuccessResponse(BaseModel, Generic[T]):
    status: int = 200
    data: T

class ErrorDetail(BaseModel):
    timestamp: str
    message: str
    code: str

class ErrorResponse(BaseModel):
    status: int
    data: ErrorDetail
```

### 전역 예외 핸들러 (app/main.py에 추가)

```python
from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "data": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": str(exc.detail),
                "code": str(exc.status_code),
            },
        },
    )
```

### 엔드포인트에서 사용

```python
from app.schemas.common import SuccessResponse

@router.post("", response_model=SuccessResponse[StoreResponse])
async def create_store(...) -> SuccessResponse[StoreResponse]:
    result = await store_service.create(db, owner_id, body)
    return SuccessResponse(data=result)
```

---

## 공통 Enum (app/schemas/common.py에 함께 정의)

```python
from enum import Enum

class UserRole(str, Enum):
    OWNER = "OWNER"
    REVIEWER = "REVIEWER"

class StoreType(str, Enum):
    RESTAURANT = "RESTAURANT"
    CAFE = "CAFE"
    FASHION = "FASHION"
    BEAUTY = "BEAUTY"
    ETC = "ETC"

class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class S3FileType(str, Enum):
    REVIEW = "REVIEW"
    STORE = "STORE"
```

---

## 패턴

- 필드명은 **camelCase** (프론트엔드 명세 기준)
- UUID는 응답에서 `str`로 반환
- nullable 필드: `field: str | None = None`
- 요청 스키마는 `Req` 접미사, 응답은 `Resp` 또는 도메인명 그대로

```python
from pydantic import BaseModel

class StoreCreateReq(BaseModel):
    name: str
    address: str
    category: StoreType
    thumbnailUrl: str | None = None
    description: str | None = None

class StoreResp(BaseModel):
    id: str
    name: str
    address: str
    category: StoreType
    thumbnailKey: str | None = None
    description: str | None = None
```

---

## 파일별 구성

| 파일 | 내용 |
|------|------|
| `common.py` | SuccessResponse, ErrorDetail, 공통 Enum |
| `auth.py` | 인증 요청·응답 |
| `store.py` | 상점 요청·응답 |
| `event.py` | 이벤트 요청·응답 |
| `application.py` | 신청·리뷰 제출 요청·응답 |
| `s3.py` | S3 업로드 요청·응답 (기존 파일 수정) |
| `deposit.py` | 입금 요청·응답 |

---

## s3.py 수정 사항

현재 `S3FileType`에 `COMPANY_THUMBNAIL`이 있으나 명세는 `STORE`.
`common.py`의 `S3FileType`으로 교체하거나 s3.py Enum을 수정:

```python
# 변경 전: COMPANY_THUMBNAIL = "COMPANY_THUMBNAIL"
# 변경 후: STORE = "STORE"
```

서비스(`app/services/s3.py`)의 버킷 분기 로직도 함께 수정.
