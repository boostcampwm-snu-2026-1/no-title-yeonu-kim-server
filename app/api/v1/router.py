from fastapi import APIRouter

from app.api.v1.endpoints.application import router as application_router

router = APIRouter()
router.include_router(application_router)
