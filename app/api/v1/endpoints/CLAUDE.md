# Endpoints — app/api/v1/endpoints/

도메인별 FastAPI 라우터. **이 파일이 API 명세 전체의 참조 원본이다.**

## 라우터 등록

각 파일 내에서 prefix 설정 후 `app/api/v1/router.py`에 include:

```python
# endpoint 파일
router = APIRouter(prefix="/auth", tags=["Auth"])

# app/api/v1/router.py
from app.api.v1.endpoints.auth import router as auth_router
router.include_router(auth_router)
```

⚠️ `app/main.py`의 prefix를 `/api/v1` → `/api`로 변경해야 명세와 일치한다.

---

## 1. Auth — `app/api/v1/endpoints/auth.py`

`router = APIRouter(prefix="/auth", tags=["Auth"])`

### POST /api/auth/email — 이메일 중복 확인
```
인증: 불필요
Request:  { email: str }
Response: SuccessResponse[None]
에러: 409 이미 가입된 이메일
```

### POST /api/auth/email/verify — 인증 이메일 발송
```
인증: 불필요
Request:  { email: str }
Response: SuccessResponse[None]
동작: 6자리 코드 생성 → EmailVerification 저장 → 이메일 발송 (MVP: 콘솔 출력)
```

### POST /api/auth/email/validate — 인증 코드 검증
```
인증: 불필요
Request:  { email: str, code: str }
Response: SuccessResponse[{ verificationToken: str }]
에러: 400 코드 불일치 또는 만료
동작: 검증 성공 → JWT verificationToken 발급
```

### POST /api/auth/user — 회원가입
```
인증: 불필요
Request:  { role: "OWNER"|"REVIEWER", username: str, email: str, password: str }
Response: SuccessResponse[{ user: { id: str, userRole: str }, token: str }]
동작: password bcrypt 해시 저장
      Access Token 반환 (token 필드)
      Refresh Token → HttpOnly 쿠키 Set-Cookie
```

### POST /api/auth/user/session — 로그인
```
인증: 불필요
Request:  { role: "OWNER"|"REVIEWER", mail: str, password: str }
Response: SuccessResponse[{ user: { id: str, userRole: str }, token: str }]
에러: 401 이메일·비밀번호 불일치, 400 role 불일치
동작: Refresh Token → HttpOnly 쿠키 Set-Cookie
```

### GET /api/auth/token — 액세스 토큰 재발급
```
인증: 쿠키 (refresh_token)
Response: SuccessResponse[{ accessToken: str }]
에러: 401 쿠키 없음 또는 만료
```

### DELETE /api/auth/user/session — 로그아웃
```
인증: Bearer Token
Response: SuccessResponse[None]
동작: Set-Cookie: refresh_token=; Max-Age=0; HttpOnly
```

### PATCH /api/auth/password — 비밀번호 변경
```
인증: Bearer Token
Request:  { oldPassword: str, newPassword: str }
Response: SuccessResponse[None]
에러: 400 oldPassword 불일치
```

### POST /api/auth/password — 비밀번호 초기화
```
인증: 불필요
Request:  { email: str }
Response: SuccessResponse[None]
동작: 임시 비밀번호 생성 → 해시 저장 → 이메일 발송
에러: 404 가입되지 않은 이메일
```

---

## 2. Store — `app/api/v1/endpoints/store.py`

`router = APIRouter(prefix="/store", tags=["Store"])`

### GET /api/store — 상점 목록 (페이지네이션)
```
인증: 불필요
Query:  category?: StoreType, name?: str, page?: int=1, size?: int=20
Response: SuccessResponse[{
  stores: [{
    id, name, address, category,
    thumbnailKey?: str,
    description?: str,
    events: [{ id, title, condition, reward, isActive }],
    totalEventCount: int
  }],
  totalCount, currentPage, totalPages, hasNext
}]
```

### POST /api/store — 상점 생성
```
인증: Bearer Token (OWNER)
Request:  { name, address, category: StoreType, thumbnailUrl?: str, description?: str }
Response: SuccessResponse[{ id, name, address, category, thumbnailKey?: str, description?: str }]
주의: Request는 thumbnailUrl, Response는 thumbnailKey (필드명 다름)
     thumbnailUrl → S3 key 파싱 또는 그대로 저장 후 key로 반환
```

### GET /api/store/{storeId} — 상점 상세
```
인증: 불필요
Response: SuccessResponse[{ id, name, address }]
에러: 404
```

### DELETE /api/store/{storeId} — 상점 삭제
```
인증: Bearer Token
Response: SuccessResponse[None]
에러: 403 본인 소유 아님, 404
```

### GET /api/store/{storeId}/events — 상점의 이벤트 목록
```
인증: 불필요
Response: SuccessResponse[{ events: [{ id, title, condition, reward, isActive }] }]
에러: 404 상점 없음
```

---

## 3. Event — `app/api/v1/endpoints/event.py`

`router = APIRouter(prefix="/event", tags=["Event"])`

⚠️ **라우터 순서 중요**: `/owner` 고정 경로를 `/{eventId}` 동적 경로보다 먼저 등록.

### POST /api/event — 이벤트 생성
```
인증: Bearer Token (OWNER)
Request:  { title, condition, reward: int }
Response: SuccessResponse[{ id, title, condition, reward, isActive }]
주의: 명세에 storeId 없음 — 구현 시 Request에 storeId 포함하거나
     OWNER의 상점에 자동 연결하는 방식으로 프론트엔드와 협의 필요
```

### GET /api/event/owner — 내 이벤트 목록
```
인증: Bearer Token (OWNER)
Response: SuccessResponse[{ events: [{ id, title, condition, reward, isActive }] }]
```

### GET /api/event/{eventId} — 이벤트 상세
```
인증: 불필요
Response: SuccessResponse[{ id, title, condition, reward, isActive }]
에러: 404
```

### DELETE /api/event/{eventId} — 이벤트 삭제
```
인증: Bearer Token
Response: SuccessResponse[None]
에러: 403 본인 소유 아님, 404
```

### GET /api/event/{eventId}/applications — 이벤트별 신청 목록
```
인증: Bearer Token (OWNER)
Query:  status?: "pending"|"approved"|"rejected", page?: int=1, size?: int=20
        (소문자로 받아 DB 비교 시 대문자로 변환)
Response: SuccessResponse[{
  applications: [{
    id, reviewerId, reviewerName,
    status: "PENDING"|"APPROVED"|"REJECTED",
    appliedAt, hasSubmission
  }],
  totalCount, currentPage, totalPages, hasNext
}]
```

---

## 4. Application — `app/api/v1/endpoints/application.py`

⚠️ **생성은 `/applications` (복수), 조회·삭제는 `/application` (단수)**
prefix 없이 경로를 직접 지정:

```python
router = APIRouter(tags=["Application"])

@router.post("/applications")   # POST /api/applications
@router.get("/application")     # GET  /api/application
@router.delete("/application/{applicationId}")
@router.post("/application/{applicationId}/submission")
```

### POST /api/applications — 이벤트 신청 생성
```
인증: 불필요 (명세 기준 — 실제 구현 시 REVIEWER 인증 추가 검토)
Request:  { eventId: str, walletAddress: str, imageKey: str }
Response: SuccessResponse[None]
에러: 409 동일 이벤트 중복 신청
```

### GET /api/application — 내 신청 목록
```
인증: Bearer Token (REVIEWER)
Response: SuccessResponse[{
  applications: [{
    id, eventId,
    status: "PENDING"|"APPROVED"|"REJECTED",
    reviewSubmission?: { id, message, reviewImages: [str] },
    appliedAt
  }],
  totalCount, currentPage, totalPages, hasNext
}]
```

### DELETE /api/application/{applicationId} — 신청 취소
```
인증: Bearer Token
Response: SuccessResponse[None]
에러: 403 본인 신청 아님
     400 PENDING이 아닌 상태에서 취소 불가
```

### POST /api/application/{applicationId}/submission — 리뷰 제출
```
인증: Bearer Token
Request:  { imageList: [str], comment: str }
          imageList = S3 key 배열
Response: SuccessResponse[None]
에러: 409 이미 제출됨
     403 본인 신청 아님
```

---

## 5. S3 — `app/api/v1/endpoints/s3.py` (기존 파일 수정)

`router = APIRouter(prefix="/s3", tags=["S3"])`

⚠️ 현재 `S3FileType`이 `COMPANY_THUMBNAIL`이나 명세는 `STORE` — 스키마·서비스 함께 수정.
⚠️ 현재 POST에 `require_login` 걸려있으나 명세상 인증 불필요 — 제거 가능.

### POST /api/s3 — Presigned Upload URL 발급
```
인증: 불필요 (명세 기준)
Request:  { fileName: str, fileType: "REVIEW"|"STORE" }
Response: SuccessResponse[{ url: str, s3Key: str }]
동작: REVIEW → private bucket / STORE → public bucket
```

현재 코드의 GET /api/s3 (다운로드 URL) 엔드포인트는 명세에 없음 — 유지 여부 확인.

---

## 6. Deposit — `app/api/v1/endpoints/deposit.py` (신규 파일)

`router = APIRouter(prefix="/deposit", tags=["Deposit"])`

### POST /api/deposit — 입금
```
인증: Bearer Token
Request:  { amount: int }
Response: SuccessResponse[{ balance: int, depositedAt: str }]
동작: 기존 잔액 합산 → Deposit 레코드 생성
     depositedAt: ISO 8601 문자열
```
