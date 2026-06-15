from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.event import router as event_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(event_router)
