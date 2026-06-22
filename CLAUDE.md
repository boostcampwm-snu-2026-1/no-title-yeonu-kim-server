# VLSI Server

FastAPI 기반 백엔드 — 상점·이벤트·리뷰 신청 플랫폼

## Tech Stack

| 분류          | 라이브러리                         |
| ------------- | ---------------------------------- |
| 웹 프레임워크 | FastAPI                            |
| ORM           | SQLAlchemy 2.0 (async)             |
| DB            | PostgreSQL (asyncpg)               |
| 마이그레이션  | Alembic                            |
| 인증          | PyJWT (추가 필요) + passlib/bcrypt |
| 파일 스토리지 | boto3 (S3)                         |
| 스키마 검증   | Pydantic v2                        |
| 패키지 관리   | uv                                 |
| Lint/Format   | ruff                               |
| 타입 검사     | mypy strict                        |

## 디렉토리 구조

도메인 패키지 단위로 구성. 각 패키지가 모델·스키마·레포지토리·서비스·라우터를 모두 소유한다.

```
app/
├── auth/            # 인증·사용자 도메인
├── store/           # 상점 도메인
├── event/           # 이벤트 도메인
├── application/     # 신청·리뷰 도메인
├── deposit/         # 입금 도메인
├── s3/              # 파일 업로드 도메인
├── core/
│   ├── config.py    # 환경변수 (Settings)
│   ├── security.py  # 비밀번호 해시, JWT
│   ├── exceptions.py
│   └── email.py
├── db/
│   ├── base.py      # DeclarativeBase + 전 도메인 모델 import
│   └── session.py   # AsyncSession 팩토리
└── main.py
```

각 도메인 패키지의 내부 구조 및 DI 패턴 → `app/CLAUDE.md`
API 명세 전체 → `app/api/v1/endpoints/CLAUDE.md` (이관 완료까지 유지)

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

1. `app/{domain}/models.py` — SQLAlchemy 모델 정의
2. `app/db/base.py`에 모델 import (Alembic autogenerate 필요)
3. `uv run alembic revision --autogenerate -m "add {domain}"`
4. `app/{domain}/schemas.py` — 요청·응답 Pydantic 스키마
5. `app/{domain}/repository.py` — ABC 인터페이스
6. `app/{domain}/repository_impl.py` — SQLAlchemy 구현체
7. `app/{domain}/service.py` — ABC 인터페이스
8. `app/{domain}/service_impl.py` — 비즈니스 로직
9. `app/{domain}/dependencies.py` — FastAPI DI 바인딩
10. `app/{domain}/router.py` — 라우터
11. `app/main.py` — `include_router` 추가

각 단계의 구현 패턴 → `app/CLAUDE.md`

## 각 패키지 상세 지침

| 작업                  | 참조 파일       |
| --------------------- | --------------- |
| 도메인 패키지 구조·DI | `app/CLAUDE.md` |
