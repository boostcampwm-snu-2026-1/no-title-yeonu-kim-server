# VLSI Server

상점 오너와 리뷰어를 연결하는 리뷰 이벤트 플랫폼의 백엔드 서버.
오너는 이벤트를 등록하고, 리뷰어는 이벤트에 신청해 리뷰를 제출하면 이더리움 스마트컨트랙트를 통해 보상을 받는다.

## Tech Stack

| 분류          | 라이브러리             |
| ------------- | ---------------------- |
| 웹 프레임워크 | FastAPI                |
| ORM           | SQLAlchemy 2.0 (async) |
| DB            | PostgreSQL (asyncpg)   |
| 마이그레이션  | Alembic                |
| 인증          | PyJWT + passlib/bcrypt |
| 파일 스토리지 | boto3 (S3)             |
| 블록체인      | web3.py (Ethereum)     |
| AI            | Anthropic SDK          |
| 스키마 검증   | Pydantic v2            |
| 패키지 관리   | uv                     |

## 주요 기능

### 인증 (Auth)

- 이메일 중복 확인 및 6자리 코드 인증
- 회원가입 시 bcrypt 비밀번호 해시 저장
- JWT 기반 인증: Access Token (Bearer) + Refresh Token (HttpOnly 쿠키)
- 비밀번호 변경 / 임시 비밀번호 이메일 발송

### 상점 (Store)

- 카테고리·이름 필터 및 페이지네이션 목록 조회
- OWNER 권한으로 상점 생성·삭제
- 상점별 이벤트 목록 조회

### 이벤트 (Event)

- OWNER가 상점에 리뷰 조건·보상금액을 지정한 이벤트 등록
- 이벤트별 신청 목록 조회 (상태 필터·페이지네이션)

### 신청 및 리뷰 (Application)

- REVIEWER가 이벤트에 지갑 주소·첨부 이미지와 함께 신청
- 동일 이벤트 중복 신청 방지 (DB UniqueConstraint)
- 리뷰 이미지·코멘트 제출
- 신청 취소 (PENDING 상태만 가능)

### 블록체인 리워드

- Solidity `ReviewReward` 스마트컨트랙트 (Foundry 빌드)
- 신청 승인 시 `release()` 호출로 리뷰어 지갑에 ETH 자동 지급
- 지급 완료 후 이메일 알림 발송
- BackgroundTask로 비동기 처리하여 API 응답 지연 없음

### 파일 업로드 (S3)

- Presigned URL 발급으로 클라이언트 직접 업로드
- 리뷰 이미지: private bucket / 상점 썸네일: public bucket

### 입금 (Deposit)

- 누적 잔액 관리 및 입금 이력 기록

## 디렉토리 구조

```
app/
├── api/v1/
│   ├── endpoints/   # 도메인별 라우터 (auth, store, event, application, deposit, s3)
│   ├── router.py
│   └── deps.py      # 공통 의존성 (require_login)
├── core/
│   ├── config.py    # 환경변수 (Settings)
│   ├── security.py  # 비밀번호 해시, JWT
│   ├── email.py     # 이메일 발송
│   └── exceptions.py
├── db/
│   ├── base.py      # DeclarativeBase
│   └── session.py   # AsyncSession 팩토리
├── models/          # SQLAlchemy ORM 모델
├── schemas/         # Pydantic 스키마
└── services/        # 비즈니스 로직
```

## API 응답 포맷

```json
// 성공
{ "status": 200, "data": { ... } }

// 실패
{ "status": 4xx, "data": { "timestamp": "...", "message": "...", "code": "..." } }
```

## 환경변수

`.env` 파일에 아래 항목을 설정한다.

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/db
SECRET_KEY=

# AWS S3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-northeast-2
S3_PRIVATE_BUCKET=
S3_PUBLIC_BUCKET=

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Blockchain
BLOCKCHAIN_RPC_URL=
SERVER_PRIVATE_KEY=
CONTRACT_ARTIFACT_PATH=out/ReviewReward.sol/ReviewReward.json

# Anthropic
ANTHROPIC_API_KEY=
```

## 실행

### Docker Compose

```bash
docker-compose up
```

### 로컬 개발

```bash
# 의존성 설치
uv sync

# DB 마이그레이션
uv run alembic upgrade head

# 개발 서버 실행
uv run uvicorn app.main:app --reload
```

## 개발 명령어

```bash
make check   # lint + format check + typecheck
make fix     # ruff 자동 수정
make test    # pytest

# 마이그레이션 생성
uv run alembic revision --autogenerate -m "설명"
```
