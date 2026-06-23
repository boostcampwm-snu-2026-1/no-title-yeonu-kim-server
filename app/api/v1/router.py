from fastapi import APIRouter

from app.api.v1.endpoints.application import router as application_router
from app.api.v1.endpoints.event import router as event_router
from app.api.v1.endpoints.store import router as store_router

router = APIRouter()
router.include_router(store_router)
router.include_router(event_router)
router.include_router(application_router)
