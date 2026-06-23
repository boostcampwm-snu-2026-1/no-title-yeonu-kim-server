from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.api.v1.deps import require_login
from app.application.dependencies import get_application_service
from app.application.schemas import (
    ApplicationCreateReq,
    ApplicationListResp,
    ReviewSubmissionReq,
)
from app.application.service import ApplicationService

router = APIRouter(tags=["Application"])


@router.post("/applications", response_model=None)
async def create_application(
    body: ApplicationCreateReq,
    background_tasks: BackgroundTasks,
    reviewer_id: str = Depends(require_login),
    service: ApplicationService = Depends(get_application_service),
) -> None:
    await service.create_application(reviewer_id, body, background_tasks)


@router.get("/application", response_model=ApplicationListResp)
async def get_my_applications(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
    reviewer_id: str = Depends(require_login),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationListResp:
    applications, total = await service.list_my_applications(reviewer_id, page, size)
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
    user_id: str = Depends(require_login),
    service: ApplicationService = Depends(get_application_service),
) -> None:
    await service.cancel_application(applicationId, user_id)


@router.post("/application/{applicationId}/submission", response_model=None)
async def submit_review(
    applicationId: str,
    body: ReviewSubmissionReq,
    user_id: str = Depends(require_login),
    service: ApplicationService = Depends(get_application_service),
) -> None:
    await service.submit_review(applicationId, user_id, body)
