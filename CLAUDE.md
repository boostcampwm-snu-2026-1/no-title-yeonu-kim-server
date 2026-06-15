# VLSI Server

FastAPI 기반 백엔드 — 상점·이벤트·리뷰 신청 플랫폼

## Tech Stack

| 분류 | 라이브러리 |
|------|-----------|
| 웹 프레임워크 | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| DB | PostgreSQL (asyncpg) |
| 마이그레이션 | Alembic |
| 인증 | PyJWT (추가 필요) + passlib/bcrypt |
| 파일 스토리지 | boto3 (S3) |
| 스키마 검증 | Pydantic v2 |
| 패키지 관리 | uv |
| Lint/Format | ruff |
| 타입 검사 | mypy strict |

## 디렉토리 구조

```
app/
├── api/v1/
│   ├── endpoints/   # 도메인별 라우터 (auth, store, event, application, deposit, s3)
│   │   └── CLAUDE.md  ← API 명세 전체
│   ├── router.py
│   └── deps.py      # 공통 의존성 (require_login)
├── core/
│   ├── config.py    # 환경변수 (Settings)
│   └── security.py  # 비밀번호 해시, JWT
├── db/
│   ├── base.py      # DeclarativeBase
│   └── session.py   # AsyncSession 팩토리
├── models/          # SQLAlchemy ORM 모델  ← models/CLAUDE.md
├── schemas/         # Pydantic 스키마       ← schemas/CLAUDE.md
└── services/        # 비즈니스 로직         ← services/CLAUDE.md
```

## 개발 명령어

```bash
make check      # lint + format check + typecheck
make fix        # ruff 자동 수정
make test       # pytest

uv run uvicorn app.main:app --reload          # 개발 서버

uv run alembic revision --autogenerate -m "설명"  # 마이그레이션 생성
uv run alembic upgrade head                       # 마이그레이션 적용
```

## ⚠️ URL Prefix 주의

현재 `app/main.py`는 `prefix="/api/v1"`로 등록되어 있으나,
API 명세 경로는 `/api/auth/...`, `/api/store/...` 형태 (v1 없음).
**`prefix="/api"`로 변경**해야 명세와 일치한다.

## 공통 응답 포맷

모든 엔드포인트는 아래 래퍼를 사용한다. `app/schemas/common.py`에 정의할 것.

```
# 성공
{ "status": 200, "data": T }

# 실패
{ "status": 4xx|5xx, "data": { "timestamp": str, "message": str, "code": str } }
```

→ 구현 패턴 상세: `app/schemas/CLAUDE.md`

## 인증 방식

- **Access Token**: Bearer JWT, 헤더 `Authorization: Bearer {token}`
- **Refresh Token**: HttpOnly 쿠키 (`credentials: include`)
- `GET /api/auth/token` — 쿠키의 Refresh Token으로 Access Token 재발급
- `app/api/deps.py`의 `require_login` — 현재 헤더 형식만 확인, **JWT 디코딩 추가 필요**
  → 완성 후 `str(user_id)` 반환

## 새 도메인 추가 순서

1. `app/models/{domain}.py` — SQLAlchemy 모델 정의
2. `app/db/base.py`에 모델 import (Alembic autogenerate 필요)
3. `uv run alembic revision --autogenerate -m "add {domain}"`
4. `app/schemas/{domain}.py` — 요청·응답 Pydantic 스키마
5. `app/services/{domain}.py` — 비즈니스 로직
6. `app/api/v1/endpoints/{domain}.py` — 라우터
7. `app/api/v1/router.py` — `include_router` 추가

## 각 패키지 상세 지침

작업 대상 패키지의 CLAUDE.md를 함께 읽을 것.

| 작업 | 참조 파일 |
|------|----------|
| 모델 정의 | `app/models/CLAUDE.md` |
| 스키마 정의 | `app/schemas/CLAUDE.md` |
| 서비스 로직 | `app/services/CLAUDE.md` |
| 엔드포인트·API 명세 | `app/api/v1/endpoints/CLAUDE.md` |
