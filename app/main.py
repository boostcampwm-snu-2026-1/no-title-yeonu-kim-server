from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.api.v1.router import router as api_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.db.seed import reset_and_seed
from app.db.session import engine
from app.s3.router import router as s3_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if settings.seed_db:
        await reset_and_seed(engine)
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.include_router(auth_router, prefix="/api")
app.include_router(s3_router, prefix="/api")
app.include_router(api_router, prefix="/api")


@app.exception_handler(AppException)
async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "data": {
                "timestamp": datetime.now(UTC).isoformat(),
                "message": exc.message,
                "code": exc.code,
            },
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "data": {
                "timestamp": datetime.now(UTC).isoformat(),
                "message": str(exc.detail),
                "code": str(exc.status_code),
            },
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
