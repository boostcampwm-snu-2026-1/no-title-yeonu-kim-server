from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.event import Event
from app.models.review_image import ReviewImage
from app.models.review_submission import ReviewSubmission
from app.schemas.application import (
    ApplicationCreateReq,
    ApplicationItem,
    ReviewSubmissionDetail,
    ReviewSubmissionReq,
)


async def create_application(
    db: AsyncSession, reviewer_id: str, data: ApplicationCreateReq
) -> None:
    event = await db.scalar(select(Event).where(Event.id == UUID(data.eventId)))
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="이벤트를 찾을 수 없습니다.",
        )

    existing = await db.scalar(
        select(Application).where(
            Application.event_id == UUID(data.eventId),
            Application.reviewer_id == UUID(reviewer_id),
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 신청한 이벤트입니다.",
        )

    application = Application(
        event_id=UUID(data.eventId),
        reviewer_id=UUID(reviewer_id),
        wallet_address=data.walletAddress,
        image_key=data.imageKey,
    )
    db.add(application)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 신청한 이벤트입니다.",
        )


async def list_my_applications(
    db: AsyncSession, reviewer_id: str, page: int, size: int
) -> tuple[list[ApplicationItem], int]:
    base_query = select(Application).where(
        Application.reviewer_id == UUID(reviewer_id)
    )
    _total = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    total = _total if _total is not None else 0

    apps = (await db.scalars(base_query.offset((page - 1) * size).limit(size))).all()

    result: list[ApplicationItem] = []
    for app in apps:
        submission = await db.scalar(
            select(ReviewSubmission).where(
                ReviewSubmission.application_id == app.id
            )
        )
        submission_detail = None
        if submission:
            images = (
                await db.scalars(
                    select(ReviewImage)
                    .where(ReviewImage.submission_id == submission.id)
                    .order_by(ReviewImage.order)
                )
            ).all()
            submission_detail = ReviewSubmissionDetail(
                id=str(submission.id),
                message=submission.message,
                reviewImages=[img.image_key for img in images],
            )
        result.append(
            ApplicationItem(
                id=str(app.id),
                eventId=str(app.event_id),
                status=app.status,
                reviewSubmission=submission_detail,
                appliedAt=app.applied_at.isoformat(),
            )
        )
    return result, int(total)


async def cancel_application(
    db: AsyncSession, application_id: str, user_id: str
) -> None:
    application = await db.scalar(
        select(Application).where(Application.id == UUID(application_id))
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="신청을 찾을 수 없습니다.",
        )
    if str(application.reviewer_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인의 신청이 아닙니다.",
        )
    if application.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PENDING 상태의 신청만 취소할 수 있습니다.",
        )
    await db.delete(application)
    await db.commit()


async def submit_review(
    db: AsyncSession, application_id: str, user_id: str, data: ReviewSubmissionReq
) -> None:
    application = await db.scalar(
        select(Application).where(Application.id == UUID(application_id))
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="신청을 찾을 수 없습니다.",
        )
    if str(application.reviewer_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인의 신청이 아닙니다.",
        )
    existing = await db.scalar(
        select(ReviewSubmission).where(
            ReviewSubmission.application_id == UUID(application_id)
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 제출된 리뷰가 있습니다.",
        )

    submission = ReviewSubmission(
        application_id=UUID(application_id),
        message=data.comment,
    )
    db.add(submission)
    await db.flush()

    for i, image_key in enumerate(data.imageList):
        db.add(ReviewImage(submission_id=submission.id, image_key=image_key, order=i))

    await db.commit()
