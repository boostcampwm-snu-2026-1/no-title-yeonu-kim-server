from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_login
from app.db.session import get_db
from app.schemas.application import (
    ApplicationCreateReq,
    ApplicationListResp,
    ReviewSubmissionReq,
)
from app.services import application as application_service

router = APIRouter(tags=["Application"])


@router.post("/applications", response_model=None)
async def create_application(
    body: ApplicationCreateReq,
    db: AsyncSession = Depends(get_db),
    reviewer_id: str = Depends(require_login),
) -> None:
    await application_service.create_application(db, reviewer_id, body)


@router.get("/application", response_model=ApplicationListResp)
async def get_my_applications(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
    db: AsyncSession = Depends(get_db),
    reviewer_id: str = Depends(require_login),
) -> ApplicationListResp:
    applications, total = await application_service.list_my_applications(
        db, reviewer_id, page, size
    )
    total_pages = max(1, (total + size - 1) // size)
    return ApplicationListResp(
        applications=applications,
        totalCount=total,
        currentPage=page,
        totalPages=total_pages,
        hasNext=(page + 1) < total_pages,
    )


@router.delete("/application/{applicationId}", response_model=None)
async def cancel_application(
    applicationId: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_login),
) -> None:
    await application_service.cancel_application(db, applicationId, user_id)


@router.post("/application/{applicationId}/submission", response_model=None)
async def submit_review(
    applicationId: str,
    body: ReviewSubmissionReq,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_login),
) -> None:
    await application_service.submit_review(db, applicationId, user_id, body)
